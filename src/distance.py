"""Does distance to the nearest training noise predict how a model fails?

Stage 5 found transfer close to all-or-nothing per (model, test noise): the
model either removes almost all of a noise or almost none of it. This module
tests the account that the failure mode is set by how far the test noise lies
from the nearest noise the model was trained on.

Distance
--------
Each noise source is described by the frames of a 64-band log-mel spectrogram
(n_fft 1024, hop 256, 60-8000 Hz) of RMS-normalised audio, so level plays no
part. A Gaussian is fitted to the frames and two sources are compared with the
Frechet distance between their Gaussians (as in Frechet Audio Distance, on
log-mel features). A model's distance to a test noise is the minimum over its
training sources. LTAS distance (RMS difference of the mean log-mel vectors,
dB) is computed as a secondary feature.

Noise audio
-----------
MarVEN mixing is exact (measured SNR == target), so the noise in a row is
noisy - clean. Training-side MarVEN features use train-split rows, test-side
features use test-split rows. DEMAND features use the same regions as
src.diverse: dem_A = first 80% of a training environment, dem_B = last 20%,
held-out environments whole.

Models and training sources
---------------------------
    b1_weather   MarVEN rainfall, lightning, hurricane
    b1_anthro    MarVEN bubble_curtain, large_commercial_ship
    b1_demand    the 14 DEMAND training environments, region A

Outcomes come from results/diverse/<tag>.csv (src.diverse --eval): medians at
SNR <= 0 dB of noise_removed and SI-SDR gain, output-STFT basis.

Units (pre-committed in configs/gate_universal.yaml, D2_distance)
------------------------------------------------------------------
UNSEEN pairs only enter the primary test: a test source the model never
trained on. For the MarVEN models each DEMAND environment is one unit (all its
dem_* rows pooled; whole-recording feature). For b1_demand the units are the
five marine types and the three held-out environments. Seen pairs (matched
MarVEN types; b1_demand on dem_A / dem_B) are reported separately.

Usage, from the repo root with FAILDIR_ROOT / FAILDIR_DEMAND set:
    python -m src.distance
"""
from __future__ import annotations

import argparse
import math

import config as C  # noqa: I001  (must precede torch)

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from scipy import linalg, stats

from src import data as D
from src import diverse as V

OUT = C.EVAL / "distance"
TAGS = ("b1_weather", "b1_anthro", "b1_demand")
N_FFT_F, HOP_F, N_MELS, FMIN, FMAX = 1024, 256, 64, 60.0, 8000.0
ROWS_PER_TYPE = 40          # MarVEN rows per (type, split) for features
SEGS_PER_REGION = 24        # DEMAND 10 s segments per (env, region)
SEG_LEN = 10 * C.SR
FRAME_STRIDE = 2            # keep every 2nd frame
LOW_SNR = 0
ACTIVE_NR = 0.9
N_BOOT, SEED = 2000, C.SEED


# ------------------------------------------------------------ features -----
def mel_filterbank(sr=C.SR, n_fft=N_FFT_F, n_mels=N_MELS, fmin=FMIN, fmax=FMAX) -> np.ndarray:
    def hz2mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel2hz(m):
        return 700.0 * (10 ** (m / 2595.0) - 1.0)

    freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    pts = mel2hz(np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2))
    fb = np.zeros((n_mels, len(freqs)))
    for m in range(n_mels):
        lo, ce, hi = pts[m], pts[m + 1], pts[m + 2]
        up = (freqs - lo) / (ce - lo)
        down = (hi - freqs) / (hi - ce)
        fb[m] = np.clip(np.minimum(up, down), 0, None)
    if (fb.sum(1) == 0).any():
        raise ValueError("empty mel filter; lower N_MELS or raise N_FFT_F")
    return fb


FB = torch.from_numpy(mel_filterbank()).float()


def logmel_frames(x: np.ndarray) -> np.ndarray:
    """(frames, N_MELS) log-mel of RMS-normalised audio."""
    x = x.astype(np.float64)
    x = x - x.mean()
    rms = math.sqrt(float(np.mean(x ** 2)))
    if rms < 1e-9:
        return np.zeros((0, N_MELS))
    xt = torch.from_numpy((x / rms).astype(np.float32))
    S = torch.stft(xt, N_FFT_F, HOP_F, window=torch.hann_window(N_FFT_F),
                   return_complex=True).abs() ** 2
    mel = FB @ S                                     # (mels, frames)
    return (10 * torch.log10(mel + 1e-10)).T.numpy()[::FRAME_STRIDE]


def gaussian(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return frames.mean(0), np.cov(frames, rowvar=False)


def frechet(a, b) -> float:
    (m1, s1), (m2, s2) = a, b
    eps = 1e-6 * np.eye(len(m1))           # keeps sqrtm stable for near-singular covariances
    covmean = linalg.sqrtm((s1 + eps) @ (s2 + eps))
    if isinstance(covmean, tuple):          # older scipy returns (sqrtm, err) for disp=False
        covmean = covmean[0]
    covmean = np.real(covmean)
    return float(((m1 - m2) ** 2).sum() + np.trace(s1 + s2 - 2 * covmean))


def ltas(a, b) -> float:
    return float(np.sqrt(np.mean((a[0] - b[0]) ** 2)))


def marven_source(df: pd.DataFrame, ntype: str, split: str) -> tuple:
    rows = df[(df.noise_type == ntype) & (df.split == split)]
    rows = rows.sample(min(ROWS_PER_TYPE, len(rows)), random_state=SEED)
    frames = []
    for r in rows.itertuples():
        x, y = D.read_pair(r)
        frames.append(logmel_frames(x - y))
    return gaussian(np.concatenate(frames))


def demand_source(idx: pd.DataFrame, env: str, region: str) -> tuple:
    """region: 'A' = [0, 0.8 L), 'B' = [0.8 L, L), 'all' = whole recording."""
    rng = np.random.default_rng([SEED, sum(map(ord, env)), ord(region[0])])
    sub = idx[idx.env == env]
    frames = []
    for _ in range(SEGS_PER_REGION):
        r = sub.iloc[int(rng.integers(len(sub)))]
        cut = int(V.TRAIN_FRAC * r.n)
        lo, hi = {"A": (0, cut), "B": (cut, r.n), "all": (0, r.n)}[region]
        start = int(rng.integers(lo, hi - SEG_LEN + 1))
        x, _ = sf.read(r.path, start=start, frames=SEG_LEN, dtype="float32")
        frames.append(logmel_frames(x if x.ndim == 1 else x.mean(1)))
    return gaussian(np.concatenate(frames))


# ------------------------------------------------------------- outcomes ----
def outcomes(tag: str) -> pd.DataFrame:
    f = V.derive(pd.read_csv(V.OUT / f"{tag}.csv"))
    return f[f.snr <= LOW_SNR]


def unit_table(tag: str, holdout) -> pd.DataFrame:
    """One row per (tag, unit): unit name, test-feature key, seen flag, outcomes."""
    f = outcomes(tag)
    fam = V.tag_family(tag)
    hold = set(holdout)
    rows = []

    def add(sub, unit, feat, seen, group):
        rows.append({"tag": tag, "unit": unit, "group": group, "feat": feat, "seen": seen,
                     "noise_removed": float(sub.noise_removed.median()),
                     "gain": float(sub.sisdr_gain.median()), "n": len(sub)})

    mar = f[f.cond.str.startswith("marven")]
    for t, sub in mar.groupby("noise"):
        seen = (fam is not None) and (t in (C.WEATHER if fam == "weather" else C.ANTHRO))
        add(sub, t, ("marven", t, "test"), seen, "marine")
    dem = f[f.cond.str.startswith("dem_")]
    if fam is not None:                       # MarVEN model: every DEMAND env unseen, pooled
        for env, sub in dem.groupby("noise"):
            add(sub, env, ("demand", env, "all"), False, "demand")
    else:                                     # b1_demand
        for (cond, env), sub in dem.groupby(["cond", "noise"]):
            if cond == "dem_H":
                add(sub, env, ("demand", env, "all"), False, "demand")
            else:
                region = "A" if cond == "dem_A" else "B"
                add(sub, f"{env}:{region}", ("demand", env, region), env not in hold, "demand")
    return pd.DataFrame(rows)


def training_sources(tag: str, idx, holdout) -> list[tuple]:
    fam = V.tag_family(tag)
    if fam == "weather":
        return [("marven", t, "train") for t in C.WEATHER]
    if fam == "anthro":
        return [("marven", t, "train") for t in C.ANTHRO]
    if tag.split("_")[1] == "demand":
        hold = set(holdout)
        return [("demand", e, "A") for e in sorted(set(idx.env)) if e not in hold]
    raise ValueError(f"no training-source rule for {tag}")


# ------------------------------------------------------------- analysis ----
def cluster_boot_rho(t: pd.DataFrame, x: str, y: str) -> tuple[float, float]:
    units = t.unit.str.split(":").str[0].unique()
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(N_BOOT):
        pick = rng.choice(units, size=len(units), replace=True)
        s = pd.concat([t[t.unit.str.split(":").str[0] == u] for u in pick])
        if s[x].nunique() > 1 and s[y].nunique() > 1:
            vals.append(stats.spearmanr(s[x], s[y]).statistic)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def auc_lower_is_active(dist, active) -> float:
    a, b = dist[active], dist[~active]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float(np.mean([(ai < bj) + 0.5 * (ai == bj) for ai in a for bj in b]))


def run(tags=TAGS, holdout=V.HOLDOUT) -> pd.DataFrame:
    df = D.load_manifest()
    idx = V.demand_index()
    cache = {}

    def feat(key):
        if key not in cache:
            src, name, part = key
            cache[key] = (marven_source(df, name, part) if src == "marven"
                          else demand_source(idx, name, part))
        return cache[key]

    tables = []
    for tag in tags:
        t = unit_table(tag, holdout)
        trains = training_sources(tag, idx, holdout)
        fd, lt, near = [], [], []
        for key in t.feat:
            d = [(frechet(feat(key), feat(tr)), ltas(feat(key), feat(tr)), tr[1]) for tr in trains]
            best = min(d)
            fd.append(max(best[0], 0.0))
            lt.append(min(x[1] for x in d))
            near.append(best[2])
        t["dist_fd"], t["dist_ltas"], t["nearest"] = fd, lt, near
        tables.append(t)
        print(f"[{tag}] {len(t)} units, {int((~t.seen).sum())} unseen", flush=True)
    t = pd.concat(tables, ignore_index=True).drop(columns="feat")
    t["log_fd"] = np.log10(t.dist_fd.clip(lower=1e-6))   # self-distance can round to -0.0
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "pairs.csv", index=False)

    u = t[~t.seen]
    rho = stats.spearmanr(u.log_fd, u.noise_removed).statistic
    lo, hi = cluster_boot_rho(u, "log_fd", "noise_removed")
    rho_g = stats.spearmanr(u.log_fd, u.gain).statistic
    rho_l = stats.spearmanr(u.dist_ltas, u.noise_removed).statistic
    active = (u.noise_removed >= ACTIVE_NR).values
    auc = auc_lower_is_active(u.log_fd.values, active)
    passed = (rho <= -0.5) and (hi < 0)

    pd.set_option("display.width", 200)
    print("\nPer-pair table (unseen first):")
    cols = ["tag", "unit", "seen", "nearest", "dist_fd", "dist_ltas", "noise_removed", "gain", "n"]
    print(t.sort_values(["seen", "tag", "dist_fd"])[cols].round(3).to_string(index=False))
    print(f"\nPRIMARY (unseen pairs, n={len(u)}): Spearman rho(log FD, noise_removed) = {rho:+.3f}, "
          f"cluster-bootstrap 95% CI [{lo:+.3f}, {hi:+.3f}]")
    print(f"  pre-committed rule: rho <= -0.5 AND CI upper < 0  ->  {'PASS' if passed else 'FAIL'}")
    print(f"secondary: rho(log FD, gain) = {rho_g:+.3f} | rho(LTAS, noise_removed) = {rho_l:+.3f} | "
          f"AUC active (nr >= {ACTIVE_NR}) = {auc:.3f} ({int(active.sum())} active of {len(u)})")
    for tag, s in u.groupby("tag"):
        if len(s) > 2:
            print(f"  {tag}: n={len(s)} rho(log FD, nr) = "
                  f"{stats.spearmanr(s.log_fd, s.noise_removed).statistic:+.3f}")
    s = t[t.seen]
    print(f"seen pairs (not in primary): n={len(s)}, median FD {s.dist_fd.median():.2f}, "
          f"median noise_removed {s.noise_removed.median():.3f}")
    summary = pd.DataFrame([{"n_unseen": len(u), "rho_nr": rho, "ci_lo": lo, "ci_hi": hi,
                             "rho_gain": rho_g, "rho_ltas_nr": rho_l, "auc_active": auc,
                             "n_active": int(active.sum()), "verdict": "PASS" if passed else "FAIL"}])
    summary.to_csv(OUT / "summary.csv", index=False)
    print(f"\nsaved {OUT / 'pairs.csv'} and summary.csv")
    return t


def main(argv=None):
    p = argparse.ArgumentParser(description="Distance-to-training-noise analysis")
    p.add_argument("--tags", nargs="+", default=list(TAGS))
    p.add_argument("--holdout", default=",".join(V.HOLDOUT))
    a = p.parse_args(argv)
    run(a.tags, tuple(h.strip().upper() for h in a.holdout.split(",") if h.strip()))


if __name__ == "__main__":
    main()
