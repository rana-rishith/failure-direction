"""Disjoint-segment control: is "matched" performance sample replay or recording-level?

Each MarVEN noise type is one source recording. Three of them (rainfall,
lightning, ship) are shorter than most utterances and loop, so every matched
test utterance replays exactly the noise samples the model heard in training.
This control splits each recording's timeline into two halves:

    A = [0, L/2)    heard in training
    B = [L/2, L)    never heard; same recording, same mic, same conditions

The manifest's `noise_offset_sec` gives the recording position of every sample:
pos(t) = (round(offset * SR) + t) mod L. Training draws 3 s crops whose noise
lies entirely in A. Evaluation runs on 3 s windows of the fold's test_matched
utterances whose noise lies entirely in A or entirely in B, through two models:

    seg   trained on half A only (this module)
    full  the existing <model>_<fold>_best.pt, which heard both halves

Primary statistic (thresholds pre-committed in configs/gate.yaml `segment`):

    R_seg = score(seg on B) / score(full on B)
    S_A   = score(seg on A) / score(full on A)       sanity: seg is not undertrained

score() = median per-window SI-SDR improvement within each SNR, then mean over
SNR strata (same as src.confound). Normalising by `full` on the identical
windows removes any difference in difficulty between the two halves.

Loop lengths were measured from the data: the within-utterance residual
(noisy - clean) autocorrelates at exactly 1.0000 at these lags and at 0.88-0.99
one sample either side. `--verify-loops` repeats that check. Hurricane and
bubble_curtain never wrap (offset + duration <= recording length for every
row), so their length is taken from the manifest and positions need no modulo.

Usage, from the repo root, after env.ps1:
    python -m src.segment --verify-loops
    python -m src.segment --model b3 --fold weather --smoke
    python -m src.segment --model b3 --fold weather
    python -m src.segment --model b3 --fold anthro
    python -m src.segment --report
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from torch.utils.data import DataLoader, Dataset

import config as C
from src import data as D
from src import metrics as MT
from src.models import MODELS, load_model

LOOP_SAMPLES = {"rainfall": 176_811, "lightning": 121_174, "large_commercial_ship": 160_086}
NO_WRAP = ("hurricane", "bubble_curtain")
WIN = 3 * C.SR             # train crop and eval window; lightning's half-loop is 3.79 s
GUARD = int(0.05 * C.SR)   # offsets are rounded to 0.1 ms; 50 ms keeps halves strictly apart
HALVES = ("A", "B")
OUT = C.RAW_EVAL.parent / "segment"
GATE_PATH = Path(__file__).resolve().parents[1] / "configs" / "gate.yaml"


# ------------------------------------------------------------ positions ---
def loop_lengths(df: pd.DataFrame) -> dict[str, int]:
    L = dict(LOOP_SAMPLES)
    for t in NO_WRAP:
        d = df[df.noise_type == t]
        end = int(np.ceil(((d.noise_offset_sec + d.duration_sec) * C.SR).max()))
        L[t] = end + GUARD
    return L


def half_bounds(L: int, half: str) -> tuple[int, int]:
    mid = L // 2
    return (GUARD, mid - GUARD) if half == "A" else (mid + GUARD, L - GUARD)


def valid_starts(p0: int, n: int, L: int, half: str, w: int = WIN) -> list[tuple[int, int]]:
    """Inclusive [lo, hi] ranges of window starts t (in utterance samples) such that
    recording positions (p0 + t .. p0 + t + w - 1) mod L all lie inside `half`."""
    a, b = half_bounds(L, half)
    if b - a < w or n < w:
        return []
    out = []
    for k in range(-1, n // L + 2):
        lo = max(a - p0 + k * L, 0)
        hi = min(b - w - p0 + k * L, n - w)
        if lo <= hi:
            out.append((lo, hi))
    return out


def attach_segments(frame: pd.DataFrame, L: dict[str, int]) -> pd.DataFrame:
    f = frame.copy()
    p0 = np.rint(f.noise_offset_sec.values * C.SR).astype(int)
    n = np.rint(f.duration_sec.values * C.SR).astype(int)
    for h in HALVES:
        f[f"seg_{h}"] = [valid_starts(int(p), int(m), L[t], h)
                         for p, m, t in zip(p0, n, f.noise_type)]
    for t in NO_WRAP:
        m = (f.noise_type == t).values
        assert (p0[m] + n[m] <= L[t]).all(), f"{t}: a row wraps; NO_WRAP assumption broken"
    return f


def centre_start(ranges: list[tuple[int, int]], n: int, w: int = WIN) -> int:
    """Deterministic eval window: the valid start closest to centring it in the utterance."""
    target = (n - w) // 2
    return min((min(max(target, lo), hi) for lo, hi in ranges), key=lambda s: abs(s - target))


# ------------------------------------------------------------- dataset ----
class SegWindows(Dataset):
    """train=True: random 3 s crop whose noise lies in `half`.
    train=False: the centred valid window (validation)."""

    def __init__(self, frame, half="A", train=True, seed=C.SEED, root=None):
        col = f"seg_{half}"
        self.f = frame[frame[col].map(len) > 0].reset_index(drop=True)
        self.col, self.train, self.seed = col, train, seed
        self.root = C.ROOT if root is None else root

    def __len__(self):
        return len(self.f)

    def __getitem__(self, i):
        r = self.f.iloc[i]
        x, y = D.read_pair(r, self.root)
        ranges = r[self.col]
        if self.train:
            g = torch.Generator().manual_seed(self.seed + i + torch.initial_seed() % (2**31))
            sizes = np.array([hi - lo + 1 for lo, hi in ranges], dtype=float)
            j = int(torch.multinomial(torch.tensor(sizes / sizes.sum()), 1, generator=g))
            lo, hi = ranges[j]
            s = lo + int(torch.randint(0, hi - lo + 1, (1,), generator=g))
        else:
            s = centre_start(ranges, len(x))
        s = min(s, len(x) - WIN)
        return (torch.from_numpy(np.ascontiguousarray(x[s:s + WIN])),
                torch.from_numpy(np.ascontiguousarray(y[s:s + WIN])),
                int(r.target_snr_db), str(r.noise_type), str(r.uid))


def _seg_loader(frame, root=None, batch_size=C.BATCH_SIZE, train=True, workers=0, seed=C.SEED):
    """Drop-in for data.make_loader while training the seg model: half A only."""
    return DataLoader(SegWindows(frame, "A", train, seed, root),
                      batch_size=batch_size if train else 1, shuffle=train,
                      num_workers=workers, drop_last=train,
                      pin_memory=(C.device() == "cuda"),
                      generator=torch.Generator().manual_seed(seed) if train else None)


# ---------------------------------------------------------------- fold ----
def seg_fold(df: pd.DataFrame, family: str) -> dict[str, pd.DataFrame]:
    fold = D.make_fold(df, family)          # same speakers, same leakage asserts
    L = loop_lengths(df)
    return {k: attach_segments(v, L) for k, v in fold.items()}


def train_seg(key: str, fold: dict, tag: str, steps: int) -> None:
    from src import train as T
    original = T.D.make_loader
    T.D.make_loader = _seg_loader
    try:
        tr = fold["train"][fold["train"].seg_A.map(len) > 0]
        va = fold["val"][fold["val"].seg_A.map(len) > 0]
        print(f"[{tag}] half-A rows: train {len(tr)}/{len(fold['train'])}, "
              f"val {len(va)}/{len(fold['val'])}")
        T.train(key, {"train": tr, "val": va}, tag, steps=steps,
                val_every=min(C.VAL_EVERY, max(steps // 2, 1)))
    finally:
        T.D.make_loader = original


# ---------------------------------------------------------------- eval ----
@torch.no_grad()
def run_window(model, x, y, win):
    with C.autocast():
        est, mask = model(x)
    est, mask = est.float(), mask.float()
    mn = torch.stft(x, C.N_FFT, C.HOP, window=win, return_complex=True).abs()
    mc = torch.stft(y, C.N_FFT, C.HOP, window=win, return_complex=True).abs()
    e = MT.energy_decomposition(mask, mn, mc)
    return MT.si_sdr(est[0], y[0]), e["e_over"] / e["e_clean"], e["e_under"] / e["e_clean"]


@torch.no_grad()
def evaluate_windows(models: dict, frame: pd.DataFrame, out: Path, limit=None) -> pd.DataFrame:
    if limit:
        frame = frame.sample(n=min(limit, len(frame)), random_state=0).reset_index(drop=True)
    expect = int(sum((frame[f"seg_{h}"].map(len) > 0).sum() for h in HALVES))
    if out.exists():
        prev = pd.read_csv(out)
        if len(prev) == expect:
            print(f"skip {out.name} (n={len(prev)})")
            return prev
    dev = C.device()
    win = torch.hann_window(C.N_FFT, device=dev)
    for m in models.values():
        m.eval().to(dev)
    rows, t0 = [], time.time()
    for i, r in enumerate(frame.itertuples()):
        x, y = D.read_pair(r)
        for h in HALVES:
            ranges = getattr(r, f"seg_{h}")
            if not ranges:
                continue
            s = min(centre_start(ranges, len(x)), len(x) - WIN)
            xt = torch.from_numpy(np.ascontiguousarray(x[s:s + WIN]))[None].to(dev)
            yt = torch.from_numpy(np.ascontiguousarray(y[s:s + WIN]))[None].to(dev)
            rec = {"uid": r.uid, "noise_type": r.noise_type, "snr": int(r.target_snr_db),
                   "half": h, "start": s, "si_sdr_in": MT.si_sdr(xt[0], yt[0])}
            for name, m in models.items():
                so, ro, ru = run_window(m, xt, yt, win)
                rec.update({f"si_sdr_out_{name}": so, f"r_over_{name}": ro, f"r_under_{name}": ru})
            rows.append(rec)
        if (i + 1) % 200 == 0:
            print(f"  {out.stem} {i+1}/{len(frame)} {(time.time()-t0)/60:.1f}m", flush=True)
    d = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False)
    print(f"wrote {out.name} n={len(d)} {(time.time()-t0)/60:.1f}m")
    return d


# ------------------------------------------------------------- scoring ----
def score(d: pd.DataFrame, name: str) -> float:
    imp = d[f"si_sdr_out_{name}"] - d.si_sdr_in
    return float(imp.groupby(d.snr).median().mean())


def summarize(d: pd.DataFrame, key: str, fold: str, by_type: bool = True) -> pd.DataFrame:
    groups = [("all", d)] + ([(t, g) for t, g in d.groupby("noise_type")] if by_type else [])
    rows = []
    for t, g in groups:
        A, B = g[g.half == "A"], g[g.half == "B"]
        r = {"model": key, "fold": fold, "noise_type": t, "n_A": len(A), "n_B": len(B),
             "seg_A": score(A, "seg"), "full_A": score(A, "full"),
             "seg_B": score(B, "seg"), "full_B": score(B, "full")}
        r["S_A"] = r["seg_A"] / r["full_A"]
        r["R_seg"] = r["seg_B"] / r["full_B"]
        rows.append(r)
    return pd.DataFrame(rows).round(3)


def verdict(row: pd.Series, gate: dict) -> str:
    if row.S_A < gate["sanity_S_A"]:
        return f"INCONCLUSIVE: S_A={row.S_A:.2f} < {gate['sanity_S_A']} (seg model undertrained)"
    if row.R_seg >= gate["recording_level"]:
        return (f"RECORDING-LEVEL: R_seg={row.R_seg:.2f} >= {gate['recording_level']}. "
                "Matched performance does not depend on replaying heard samples.")
    if row.R_seg <= gate["sample_level"]:
        return (f"SAMPLE-LEVEL: R_seg={row.R_seg:.2f} <= {gate['sample_level']}. "
                "Matched performance is mostly replay of heard samples.")
    return f"PARTIAL: R_seg={row.R_seg:.2f}. Report, no framing claim."


# ------------------------------------------------------------ checks ------
def verify_loops(df: pd.DataFrame, per_type: int = 3) -> None:
    for t, L in LOOP_SAMPLES.items():
        d = df[(df.noise_type == t) & (df.duration_sec * C.SR > L + 2 * C.SR)]
        for r in d.sample(min(per_type, len(d)), random_state=0).itertuples():
            x, y = D.read_pair(r)
            e = (x - y).astype(np.float64)
            c = [float(e[:-l] @ e[l:] / math.sqrt((e[:-l] @ e[:-l]) * (e[l:] @ e[l:])))
                 for l in (L - 1, L, L + 1)]
            ok = c[1] > 0.999 and c[1] > max(c[0], c[2])
            print(f"{t:22s} {r.uid:40s} corr@L-1,L,L+1 = {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}"
                  f"  {'ok' if ok else 'FAIL'}")
            assert ok, f"loop length for {t} does not match the data"
    L = loop_lengths(df)
    for t in NO_WRAP:
        print(f"{t:22s} no wrap, recording length >= {L[t] / C.SR:.3f} s")


# ---------------------------------------------------------------- main ----
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", choices=["b1", "b3"], default="b3")
    ap.add_argument("--fold", choices=list(C.FAMILIES), default="weather")
    ap.add_argument("--smoke", action="store_true", help="500 steps, 40 test rows")
    ap.add_argument("--report", action="store_true", help="score saved CSVs, no training")
    ap.add_argument("--verify-loops", action="store_true")
    a = ap.parse_args(argv)

    with open(GATE_PATH) as fh:
        gate = yaml.safe_load(fh)["segment"]
    df = D.load_manifest()

    if a.verify_loops:
        verify_loops(df)
        return

    if a.report:
        parts = []
        for p in sorted(OUT.glob("*_seg_*__windows.csv")):
            if "smoke" in p.stem:
                continue
            key, fold = p.stem.split("__")[0].split("_seg_")
            parts.append(summarize(pd.read_csv(p), key, fold))
        if not parts:
            print(f"no window CSVs in {OUT}")
            return
        s = pd.concat(parts, ignore_index=True)
        s.to_csv(OUT / "segment_summary.csv", index=False)
        print(s.to_string(index=False))
        for _, r in s[s.noise_type == "all"].iterrows():
            print(f"\n{r.model}/{r.fold}: {verdict(r, gate)}")
        return

    steps, limit, sfx = (500, 40, "_smoke") if a.smoke else (gate["steps"], None, "")
    tag = f"{a.model}_seg_{a.fold}{sfx}"
    fold = seg_fold(df, a.fold)
    tm = fold["test_matched"]
    print(f"test_matched windows: A {int((tm.seg_A.map(len) > 0).sum())}, "
          f"B {int((tm.seg_B.map(len) > 0).sum())} of {len(tm)} rows")

    if (C.CKPT / f"{tag}_best.pt").exists():
        print(f"reuse {tag}_best.pt (no retrain)")
    else:
        train_seg(a.model, fold, tag, steps)

    models = {"seg": load_model(a.model, tag, kind="best"),
              "full": load_model(a.model, f"{a.model}_{a.fold}", kind="best")}
    out = OUT / f"{tag}__windows.csv"
    d = evaluate_windows(models, tm, out, limit)
    s = summarize(d, a.model, a.fold)
    print("\n" + s.to_string(index=False))
    if a.smoke:
        print("\nsmoke run: wiring only, no verdict")
    else:
        print("\nVERDICT:", verdict(s.iloc[0], gate))


if __name__ == "__main__":
    main()
