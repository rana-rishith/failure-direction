"""Diversity control: the B1/B3 architectures trained on diverse non-marine noise.

Question
--------
On unseen marine noise, B1/B3 trained on one MarVEN family go inert (median
d about -0.9, ~16% of the noise excess removed), while DeepFilterNet3 and
SGMSE+ trained on diverse noise over-suppress (d +0.2 to +0.8, 80-99.9%
removed). Those pretrained models differ from B1/B3 in architecture and scale
as well as in training-noise diversity. This module holds the architecture,
protocol and clean speech fixed and changes only the noise: it trains the
same B1 (or B3) on LibriSpeech speech from the MarVEN train split mixed on
the fly with DEMAND noise, then evaluates it on MarVEN.

    B1-demand over-suppresses on MarVEN  -> training-noise diversity is the cause
    B1-demand stays inert on MarVEN      -> architecture/scale, not diversity

Everything except the noise matches src.train: same model classes, 20,000
steps, batch 8, lr 2e-4, 4 s crops, SI-SDR loss, seed 1234, MarVEN train/val/
test speaker split, atomic resumable checkpoints.

DEMAND layout
-------------
Extract the 16 kHz zips so that the folder holds <ENV>/ch01.wav .. ch16.wav,
e.g. DEMAND_16k/OHALLWAY/ch01.wav. Set FAILDIR_DEMAND to that folder, or put
it at <MarVEN parent>/DEMAND (dataset)/DEMAND_16k.

Noise conditions (time split is identical on every channel)
-----------------------------------------------------------
    dem_A   training environments, first 80% of each recording   (training noise)
    dem_B   training environments, last 20% of each recording    (unheard segment)
    dem_H   held-out environments, whole recording               (unheard environment)
    marven  MarVEN test split, all five marine types             (unheard, far)

For B1-demand these are rungs R1, R2, R4-near and R4-far. For the existing
MarVEN-trained models, marven_m / marven_u are their R1 / R4 and every dem_*
condition is unseen.

Usage, from the repo root, with FAILDIR_ROOT / FAILDIR_CKPT / FAILDIR_DEMAND set:
    python -m src.diverse --check
    python -m src.diverse --train --model b1 --smoke       # 500 steps, tag b1_demand_smoke
    python -m src.diverse --train --model b1               # 20,000 steps, tag b1_demand
    python -m src.diverse --eval b1_demand
    python -m src.diverse --eval b1_weather b1_anthro      # same metrics for the old models
    python -m src.diverse --report
"""
from __future__ import annotations

import argparse
import math
import os
import time
from pathlib import Path

import config as C  # noqa: I001  (must precede torch: sets KMP_DUPLICATE_LIB_OK)

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from torch.utils.data import DataLoader, Dataset

from src import data as D
from src import models as M
from src.lowcut import lowcut_sisdr
from src.metrics import si_sdr_loss
from src.train import load_ckpt, save_ckpt

DEMAND = Path(os.environ.get("FAILDIR_DEMAND", C.ROOT.parent / "DEMAND (dataset)" / "DEMAND_16k"))
OUT = C.EVAL / "diverse"
HOLDOUT = ("DLIVING", "OOFFICE", "TCAR")      # one domestic, one office, one transport
TRAIN_FRAC = 0.8                               # dem_A = [0, 0.8 L), dem_B = [0.8 L, L)
K0 = int(math.ceil(C.DECOMP_MIN_HZ * C.N_FFT / C.SR))   # first STFT bin kept (DC bins excluded)
N_DEM_EVAL = 400                               # mixtures per dem_* condition (50 per SNR)
N_VAL = 200
VAL_LEN = 6 * C.SR
COND_ID = {"dem_A": 1, "dem_B": 2, "dem_H": 3}
G_MIN, G_MAX = 0.1, 10.0                       # clamp for the level-aligned split   # fixed seeds; str hash() is salted per run


# ------------------------------------------------------------- DEMAND ------
def demand_index(root: Path = DEMAND) -> pd.DataFrame:
    files = sorted(root.glob("*/ch*.wav"))
    if not files:
        raise FileNotFoundError(
            f"no DEMAND channels under FAILDIR_DEMAND={root}. Expected <ENV>/ch01.wav ... "
            "Extract the *_16k.zip files there (see module docstring)."
        )
    rows = []
    for f in files:
        info = sf.info(str(f))
        if info.samplerate != C.SR:
            raise ValueError(f"{f}: {info.samplerate} Hz, expected {C.SR}. Use the _16k zips.")
        rows.append({"env": f.parent.name.upper(), "ch": f.stem, "path": str(f), "n": int(info.frames)})
    return pd.DataFrame(rows)


def noise_pool(idx: pd.DataFrame, cond: str, holdout=HOLDOUT) -> list[tuple[str, str, int, int]]:
    """(env, path, lo, hi) regions for one condition. hi is exclusive."""
    hold = set(h.upper() for h in holdout)
    out = []
    for r in idx.itertuples():
        cut = int(TRAIN_FRAC * r.n)
        if cond == "dem_A" and r.env not in hold:
            out.append((r.env, r.path, 0, cut))
        elif cond == "dem_B" and r.env not in hold:
            out.append((r.env, r.path, cut, r.n))
        elif cond == "dem_H" and r.env in hold:
            out.append((r.env, r.path, 0, r.n))
    if not out:
        raise ValueError(f"empty noise pool for {cond} (holdout={sorted(hold)})")
    return out


def pick_noise(pool, length: int, rng: np.random.Generator):
    """Uniform over environments, then channel, then start; returns (audio, env, ch, start)."""
    envs = sorted({p[0] for p in pool})
    env = envs[int(rng.integers(len(envs)))]
    cands = [p for p in pool if p[0] == env and p[3] - p[2] >= length]
    if not cands:
        raise ValueError(f"{env}: no region long enough for {length} samples")
    _, path, lo, hi = cands[int(rng.integers(len(cands)))]
    start = int(rng.integers(lo, hi - length + 1))
    x, _ = sf.read(path, start=start, frames=length, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    return np.ascontiguousarray(x), env, Path(path).stem, start


def power(x: np.ndarray) -> float:
    x = x.astype(np.float64)
    return float(np.mean((x - x.mean()) ** 2))


def mix(clean: np.ndarray, noise: np.ndarray, snr_db: float, ps_ref: float | None = None):
    """noisy = clean + g * noise with 10 log10(Ps / (g^2 Pn)) = snr_db.

    Powers are mean-removed, so a DC offset in the clean file does not count as
    speech power. ps_ref (the whole utterance) is used when the crop itself is
    near-silent.
    """
    ps = power(clean)
    if ps < 1e-10 and ps_ref:
        ps = ps_ref
    pn = max(power(noise), 1e-12)
    g = math.sqrt(ps / (pn * 10 ** (snr_db / 10)))
    return (clean + g * noise).astype(np.float32), g


def clean_paths(df: pd.DataFrame, split: str) -> list[str]:
    """One clean file per utterance. MarVEN stores a clean file per noisy row, so
    each utterance has two clean paths; deduplicate on the LibriSpeech key."""
    f = df[df.split == split].sort_values("clean_path").drop_duplicates("key")
    return sorted(f.clean_path)


# ------------------------------------------------------------- training ----
class DiverseMix(Dataset):
    """4 s clean crop from the MarVEN split + a dem_A noise crop at one of the
    eight MarVEN SNRs. Draws depend on (seed, epoch, i), so a resumed run
    repeats the same data stream and workers>0 cannot duplicate crops."""

    def __init__(self, cleans, pool, seed: int = C.SEED, crop: int = C.CROP):
        self.cleans, self.pool, self.seed, self.crop = list(cleans), pool, seed, crop
        self.epoch = 0

    def __len__(self):
        return len(self.cleans)

    def __getitem__(self, i):
        rng = np.random.default_rng([self.seed, self.epoch, i])
        y = D.read_mono(self.cleans[i])
        ps_ref = power(y)
        n = len(y)
        if n < self.crop:
            y = np.pad(y, (0, self.crop - n))
        else:
            s = int(rng.integers(0, n - self.crop + 1))
            y = y[s:s + self.crop]
        noise, *_ = pick_noise(self.pool, self.crop, rng)
        snr = float(C.SNR_LEVELS[int(rng.integers(len(C.SNR_LEVELS)))])
        x, _ = mix(y, noise, snr, ps_ref)
        return torch.from_numpy(x), torch.from_numpy(np.ascontiguousarray(y))


def build_val(df, pool, seed: int = C.SEED):
    """Fixed in-domain validation: 200 val-split utterances, centred 6 s, dem_A noise."""
    rng = np.random.default_rng([seed, 99])
    out = []
    for k, p in enumerate(clean_paths(df, "val")[:N_VAL]):
        y = D.read_mono(p)
        if len(y) > VAL_LEN:
            s = (len(y) - VAL_LEN) // 2
            y = y[s:s + VAL_LEN]
        noise, *_ = pick_noise(pool, len(y), rng)
        x, _ = mix(y, noise, float(C.SNR_LEVELS[k % len(C.SNR_LEVELS)]))
        out.append((torch.from_numpy(x)[None], torch.from_numpy(np.ascontiguousarray(y))[None]))
    return out


@torch.no_grad()
def validate(model, val, dev) -> float:
    was = model.training
    model.eval()
    losses = []
    for x, y in val:
        with C.autocast():
            est, _ = model(x.to(dev))
        losses.append(float(si_sdr_loss(est, y.to(dev))))
    if was:
        model.train()
    return float(np.mean(losses))


def train(model_key: str, tag: str, steps: int = C.TRAIN_STEPS, bs: int = C.BATCH_SIZE,
          lr: float = C.LR, val_every: int = C.VAL_EVERY, ckpt_every: int = C.CKPT_EVERY,
          workers: int = 0, seed: int = C.SEED, fresh: bool = False, holdout=HOLDOUT) -> Path:
    dev = C.device()
    C.ensure_dirs()
    C.set_seed(seed)
    C.tune_backends()

    df = D.load_manifest()
    pool = noise_pool(demand_index(), "dem_A", holdout)
    ds = DiverseMix(clean_paths(df, "train"), pool, seed)
    val = build_val(df, pool, C.SEED)   # same validation set for every seed (identical at seed 1234)

    last_p, best_p = C.CKPT / f"{tag}_last.pt", C.CKPT / f"{tag}_best.pt"
    if fresh:
        for p in (last_p, best_p):
            if p.exists():
                p.rename(p.with_name(p.stem + "_old.pt"))
    model = M.MODELS[model_key]().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    scaler = torch.amp.GradScaler(dev, enabled=(dev == "cuda"))
    step, best, epoch = 0, float("inf"), 0
    if last_p.exists() and not fresh:
        step, best, epoch = load_ckpt(last_p, model, opt, scaler, dev)
        print(f"[{tag}] resumed at step {step}/{steps}, best {best:.3f}")
        if step >= steps:
            print(f"[{tag}] already complete")
            return best_p

    envs = sorted({p[0] for p in pool})
    print(f"[{tag}] {model_key} {M.n_params(model):,} params | dev={dev} | "
          f"{len(ds)} train utterances | {len(envs)} noise envs (holdout {', '.join(holdout)}) | "
          f"steps {steps} bs {bs} lr {lr}", flush=True)

    model.train()
    t0 = time.time()
    try:
        while step < steps:
            ds.epoch = epoch
            dl = DataLoader(ds, batch_size=bs, shuffle=True, num_workers=workers, drop_last=True,
                            pin_memory=(dev == "cuda"),
                            generator=torch.Generator().manual_seed(seed + epoch))
            epoch += 1
            for x, y in dl:
                if step >= steps:
                    break
                x, y = x.to(dev), y.to(dev)
                with C.autocast():
                    est, _ = model(x)
                loss = si_sdr_loss(est, y)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                step += 1
                if step % ckpt_every == 0:
                    save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
                if step % val_every == 0 or step == steps:
                    v = validate(model, val, dev)
                    print(f"[{tag}] {step}/{steps}  val {v:.3f}  {(time.time() - t0) / 60:.1f}m",
                          flush=True)
                    if v < best:
                        best = v
                        save_ckpt(best_p, model, opt, scaler, step, best, epoch - 1)
                    save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
    except KeyboardInterrupt:
        save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
        print(f"\n[{tag}] interrupted at step {step}; rerun the same command to resume")
        return last_p

    save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
    sd = M.torch_load(best_p, map_location="cpu", weights_only=False)["model"] \
        if best_p.exists() else model.state_dict()
    torch.save(sd, C.CKPT / f"{tag}.pt")
    print(f"[{tag}] done. best val {best:.3f}; weights-only export {tag}.pt")
    return best_p


# ----------------------------------------------------------- evaluation ----
def _ratios(Y, Cm, X, sl):
    e_clean = (Cm[sl] ** 2).sum()
    ro = ((Cm[sl] - Y[sl]).clamp(min=0) ** 2).sum() / e_clean
    ru = ((Y[sl] - Cm[sl]).clamp(min=0) ** 2).sum() / e_clean
    ra = ((Y[sl] - X[sl]).clamp(min=0) ** 2).sum() / e_clean
    return float(ro), float(ru), float(ra)


def _si_sdr(est: np.ndarray, ref: np.ndarray, eps: float = 1e-8) -> float:
    est, ref = est.astype(np.float64), ref.astype(np.float64)
    est, ref = est - est.mean(), ref - ref.mean()
    t = (est @ ref) / (ref @ ref + eps) * ref
    return float(10 * np.log10((t @ t) / (((est - t) @ (est - t)) + eps)))


@torch.no_grad()
def analyse(model, x: np.ndarray, y: np.ndarray, dev: str) -> dict:
    """Energy split on the mask's intended magnitude (M*|X|, "_i") and on the
    output waveform's STFT ("_o"), plus the passthrough floor ("_b4")."""
    xt = torch.from_numpy(x)[None].to(dev)
    est, Mk = model(xt)
    est = est[0].float()
    X = M.magnitude(xt)[0]
    Cm = M.magnitude(torch.from_numpy(y)[None].to(dev))[0]
    Yo = M.magnitude(est[None])[0]
    Yi = Mk[0].float() * X
    sl = (slice(K0, None),)
    ro_i, ru_i, _ = _ratios(Yi, Cm, X, sl)
    ro_o, ru_o, ra_o = _ratios(Yo, Cm, X, sl)
    ro_b, ru_b, _ = _ratios(X, Cm, X, sl)
    e = est.cpu().numpy()
    # Level-aligned split ("_g"). SI-SDR training leaves the output level free;
    # an unbounded mask can settle at any gain, and the plain split then counts
    # extra level as energy beyond clean. g is the level of the clean component
    # in the output; dividing by g puts that component at the clean level.
    # For the noisy input g ~ 1, so the passthrough floor is unchanged.
    yc = y.astype(np.float64) - y.mean()
    g = float(np.dot(e.astype(np.float64) - e.mean(), yc) / (np.dot(yc, yc) + 1e-12))
    g_used = float(np.clip(g, G_MIN, G_MAX))
    ro_g, ru_g, ra_g = _ratios(Yo / g_used, Cm, X, sl)
    return {"sisdr_in": _si_sdr(x, y), "sisdr_out": _si_sdr(e, y),
            "r_over_i": ro_i, "r_under_i": ru_i,
            "r_over": ro_o, "r_under": ru_o, "r_add": ra_o,
            "r_over_b4": ro_b, "r_under_b4": ru_b,
            "g": g, "r_over_g": ro_g, "r_under_g": ru_g, "r_add_g": ra_g,
            **lowcut_sisdr(e, x, y)}


def tag_family(tag: str) -> str | None:
    for fam in C.FAMILIES:
        if tag.endswith("_" + fam):
            return fam
    return None


def evaluate(tag: str, holdout=HOLDOUT, n_dem: int = N_DEM_EVAL, seed: int = C.SEED) -> Path:
    dev = C.device()
    arch = tag.split("_")[0]
    model = M.load_model(arch, tag, kind="best", device=dev)
    df = D.load_manifest()
    fam = tag_family(tag)
    rows = []
    t0 = time.time()

    test = df[df.split == "test"].reset_index(drop=True)
    for k, r in enumerate(test.itertuples()):
        x, y = D.read_pair(r)
        cond = "marven" if fam is None else ("marven_m" if r.family == fam else "marven_u")
        rows.append({"tag": tag, "cond": cond, "uid": r.uid, "noise": r.noise_type,
                     "snr": int(r.target_snr_db), **analyse(model, x, y, dev)})
        if (k + 1) % 500 == 0:
            print(f"  marven {k + 1}/{len(test)}  {(time.time() - t0) / 60:.1f}m", flush=True)

    idx = demand_index()
    cleans = clean_paths(df, "test")
    pick = np.random.default_rng([seed, 7]).choice(len(cleans), size=min(n_dem, len(cleans)),
                                                   replace=False)
    for cond in ("dem_A", "dem_B", "dem_H"):
        pool = noise_pool(idx, cond, holdout)
        for k, ci in enumerate(sorted(pick)):
            rng = np.random.default_rng([seed, COND_ID[cond], k])
            y = D.read_mono(cleans[ci])
            noise, env, ch, start = pick_noise(pool, len(y), rng)
            snr = int(C.SNR_LEVELS[k % len(C.SNR_LEVELS)])
            x, _ = mix(y, noise, snr)
            rows.append({"tag": tag, "cond": cond, "uid": f"{cleans[ci]}|{env}/{ch}@{start}",
                         "noise": env, "snr": snr, **analyse(model, x, y, dev)})
        print(f"  {cond} done  {(time.time() - t0) / 60:.1f}m", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{tag}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{tag}] {len(rows)} rows -> {out}")
    return out


# --------------------------------------------------------------- report ----
def derive(f: pd.DataFrame, basis: str = "") -> pd.DataFrame:
    """basis "" = plain output-STFT split; "_g" = level-aligned split."""
    f = f.copy()
    ro, ru = f["r_over" + basis], f["r_under" + basis]
    f["d"] = (ro - ru) / (ro + ru + 1e-8)
    f["over_x_floor"] = ro / f.r_over_b4
    f["noise_removed"] = 1 - ru / f.r_under_b4
    f["sisdr_gain"] = f.sisdr_out - f.sisdr_in
    return f


def report() -> pd.DataFrame:
    files = sorted(OUT.glob("*.csv"))
    files = [p for p in files if not p.name.startswith("summary")]
    if not files:
        raise FileNotFoundError(f"no evaluation CSVs in {OUT}; run --eval first")
    raw = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    f = derive(raw)
    cols = ["d", "noise_removed", "over_x_floor", "sisdr_gain"]
    pd.set_option("display.width", 200)
    low = f[f.snr <= 0]
    s_low = low.groupby(["tag", "cond"])[cols].median().round(3)
    s_low["n"] = low.groupby(["tag", "cond"]).size()
    print("\nMedians at SNR <= 0 dB (output STFT):")
    print(s_low.to_string())
    if "r_over_g" in raw.columns:
        fg = derive(raw.dropna(subset=["r_over_g"]), "_g")
        lowg = fg[fg.snr <= 0]
        s_g = lowg.groupby(["tag", "cond"])[cols + ["g"]].median().round(3)
        print("\nMedians at SNR <= 0 dB (LEVEL-ALIGNED output STFT; g = output level of the clean component):")
        print(s_g.to_string())
        s_g.to_csv(OUT / "summary_low_snr_levelaligned.csv")
    piv = f.pivot_table(index=["tag", "cond"], columns="snr", values="d", aggfunc="median").round(2)
    print("\nMedian d by SNR:")
    print(piv.to_string())
    s_all = f.groupby(["tag", "cond", "snr"])[cols].median().round(4)
    s_all.to_csv(OUT / "summary_by_snr.csv")
    s_low.to_csv(OUT / "summary_low_snr.csv")
    print(f"\nsaved {OUT / 'summary_low_snr.csv'} and summary_by_snr.csv")
    return s_low


# ---------------------------------------------------------------- check ----
def check(holdout=HOLDOUT) -> None:
    print(C.summary())
    print(f"DEMAND    {DEMAND}")
    idx = demand_index()
    g = idx.groupby("env").agg(channels=("ch", "count"), seconds=("n", lambda s: s.min() / C.SR))
    print(g.to_string())
    missing = sorted(set(h.upper() for h in holdout) - set(idx.env))
    assert not missing, f"holdout environments not found: {missing}"
    for cond in ("dem_A", "dem_B", "dem_H"):
        pool = noise_pool(idx, cond, holdout)
        mins = sum(hi - lo for _, path, lo, hi in pool if Path(path).stem == "ch01") / C.SR / 60
        print(f"{cond}: {len({p[0] for p in pool})} envs, {mins:.1f} min of audio per channel")
    df = D.load_manifest()
    print(f"clean utterances: train {len(clean_paths(df, 'train'))}, "
          f"val {len(clean_paths(df, 'val'))}, test {len(clean_paths(df, 'test'))}")
    ds = DiverseMix(clean_paths(df, "train"), noise_pool(idx, "dem_A", holdout))
    t0 = time.time()
    errs = []
    n_try = min(20, len(ds))
    for i in range(n_try):
        x, y = ds[i]
        errs.append(x.shape[0] == C.CROP and bool(torch.isfinite(x).all()))
    print(f"{n_try} training examples in {time.time() - t0:.2f}s; shapes/finite ok: {all(errs)}")
    y = D.read_mono(clean_paths(df, "test")[0])
    noise, *_ = pick_noise(noise_pool(idx, "dem_B", holdout), len(y), np.random.default_rng(0))
    for snr in (-15, 0, 20):
        x, gain = mix(y, noise, snr)
        meas = 10 * math.log10(power(y) / power(gain * noise))
        print(f"mix check: target {snr:+d} dB, measured {meas:+.3f} dB")


def main(argv=None):
    p = argparse.ArgumentParser(description="Diversity control (DEMAND-trained B1/B3)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--train", action="store_true")
    g.add_argument("--eval", nargs="+", metavar="TAG")
    g.add_argument("--report", action="store_true")
    p.add_argument("--model", choices=["b1", "b3", "cm"], default="b1")
    p.add_argument("--steps", type=int, default=C.TRAIN_STEPS)
    p.add_argument("--smoke", action="store_true", help="500 steps, tag <model>_demand_smoke")
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--holdout", default=",".join(HOLDOUT))
    p.add_argument("--seed", type=int, default=C.SEED)
    p.add_argument("--suffix", default="", help="tag suffix for seed replicates, e.g. _s2")
    a = p.parse_args(argv)
    holdout = tuple(h.strip().upper() for h in a.holdout.split(",") if h.strip())

    if a.check:
        check(holdout)
    elif a.train:
        tag = f"{a.model}_demand{a.suffix}" + ("_smoke" if a.smoke else "")
        steps = 500 if a.smoke else a.steps
        train(a.model, tag, steps=steps, val_every=250 if a.smoke else C.VAL_EVERY,
              workers=a.workers, seed=a.seed, fresh=a.fresh, holdout=holdout)
    elif a.eval:
        for t in a.eval:
            evaluate(t, holdout)
    else:
        report()


if __name__ == "__main__":
    main()
