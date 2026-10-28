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

Each run also scores one window per test_unseen utterance (`<tag>__unseen.csv`),
which is gate U1's R4 rung: A windows are R1, B windows R2, unseen types R4.

Usage, from the repo root, after env.ps1:
    python -m src.segment --verify-loops
    python -m src.segment --model b3 --fold weather --smoke
    python -m src.segment --model b1 --fold weather     # also cm
    python -m src.segment --model b3 --fold anthro
    python -m src.segment --report
    python -m src.segment --fold weather --export-windows D       # file-based enhancer (U2)
    python -m src.segment --fold weather --score-windows D --tag dfn3
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
from src import diverse as DV
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


def attach_full_window(frame: pd.DataFrame) -> pd.DataFrame:
    """R4 windows. An unseen noise type was never heard, so it has no A/B halves and
    any window qualifies; `seg_U` is the whole utterance."""
    f = frame.copy()
    n = np.rint(f.duration_sec.values * C.SR).astype(int)
    f["seg_U"] = [[(0, int(m) - WIN)] if m >= WIN else [] for m in n]
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


def train_seg(key: str, fold: dict, tag: str, steps: int, fresh: bool = False) -> None:
    from src import train as T
    original = T.D.make_loader
    T.D.make_loader = _seg_loader
    try:
        tr = fold["train"][fold["train"].seg_A.map(len) > 0]
        va = fold["val"][fold["val"].seg_A.map(len) > 0]
        print(f"[{tag}] half-A rows: train {len(tr)}/{len(fold['train'])}, "
              f"val {len(va)}/{len(fold['val'])}")
        T.train(key, {"train": tr, "val": va}, tag, steps=steps, fresh=fresh,
                val_every=min(C.VAL_EVERY, max(steps // 2, 1)))
    finally:
        T.D.make_loader = original


# ---------------------------------------------------------------- eval ----
@torch.no_grad()
def evaluate_windows(models: dict, frame: pd.DataFrame, out: Path, limit=None,
                     halves=HALVES) -> pd.DataFrame:
    """One row per (utterance, half), with src.diverse.analyse for every model, its keys
    suffixed by the model name. analyse is the repo's canonical split, so r_over_<name> is
    the output-STFT basis the gates use and r_over_i_<name> the mask-intent one this
    module reported before U1; si_sdr_in / si_sdr_out_<name> keep their old names."""
    if limit:
        frame = frame.sample(n=min(limit, len(frame)), random_state=0).reset_index(drop=True)
    expect = int(sum((frame[f"seg_{h}"].map(len) > 0).sum() for h in halves))
    if out.exists():
        prev = pd.read_csv(out)
        if len(prev) == expect and all(f"r_over_g_{n}" in prev.columns for n in models):
            print(f"skip {out.name} (n={len(prev)})")
            return prev
    dev = C.device()
    for m in models.values():
        m.eval().to(dev)
    rows, t0 = [], time.time()
    for i, r in enumerate(frame.itertuples()):
        x, y = D.read_pair(r)
        for h in halves:
            ranges = getattr(r, f"seg_{h}")
            if not ranges:
                continue
            s = min(centre_start(ranges, len(x)), len(x) - WIN)
            xw = np.ascontiguousarray(x[s:s + WIN])
            yw = np.ascontiguousarray(y[s:s + WIN])
            rec = {"uid": r.uid, "noise_type": r.noise_type, "snr": int(r.target_snr_db),
                   "half": h, "start": s}
            for name, m in models.items():
                a = DV.analyse(m, xw, yw, dev)
                rec.update({f"{k}_{name}": v for k, v in a.items()})
                rec[f"si_sdr_out_{name}"] = a["sisdr_out"]
            rec["si_sdr_in"] = a["sisdr_in"]
            rows.append(rec)
        if (i + 1) % 200 == 0:
            print(f"  {out.stem} {i+1}/{len(frame)} {(time.time()-t0)/60:.1f}m", flush=True)
    d = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False)
    print(f"wrote {out.name} n={len(d)} {(time.time()-t0)/60:.1f}m")
    return d


def ensure_windows(arch: str, fold_name: str, steps: int, limit=None, sfx: str = "",
                   fresh: bool = False) -> tuple[Path, Path]:
    """Half-A model (trained if absent), then the window CSVs U1 needs: A/B windows of
    test_matched (rungs R1/R2) and one window per test_unseen utterance (rung R4)."""
    df = D.load_manifest()
    fold = seg_fold(df, fold_name)
    tag = f"{arch}_seg_{fold_name}{sfx}"
    if (C.CKPT / f"{tag}_best.pt").exists() and not fresh:
        print(f"reuse {tag}_best.pt (no retrain)")
    else:
        train_seg(arch, fold, tag, steps, fresh)
    models = {"seg": load_model(arch, tag, kind="best"),
              "full": load_model(arch, f"{arch}_{fold_name}", kind="best")}
    matched, unseen = OUT / f"{tag}__windows.csv", OUT / f"{tag}__unseen.csv"
    evaluate_windows(models, fold["test_matched"], matched, limit)
    evaluate_windows({"seg": models["seg"]}, attach_full_window(fold["test_unseen"]),
                     unseen, limit, halves=("U",))
    return matched, unseen


# ------------------------------------------- file-based enhancers (U2) ----
def _windows(fold_name: str, limit=None):
    """The exact windows evaluate_windows() scores, as (row, half, start, noisy, clean):
    A/B halves of test_matched, one window per test_unseen utterance."""
    df = D.load_manifest()
    fold = seg_fold(df, fold_name)
    for frame, halves in ((fold["test_matched"], HALVES),
                          (attach_full_window(fold["test_unseen"]), ("U",))):
        if limit:
            frame = frame.sample(n=min(limit, len(frame)), random_state=0).reset_index(drop=True)
        for r in frame.itertuples():
            x, y = D.read_pair(r)
            for h in halves:
                ranges = getattr(r, f"seg_{h}")
                if not ranges:
                    continue
                s = min(centre_start(ranges, len(x)), len(x) - WIN)
                yield r, h, s, np.ascontiguousarray(x[s:s + WIN]), np.ascontiguousarray(y[s:s + WIN])


def export_windows(fold_name: str, out_dir: Path, limit=None) -> int:
    """Write each window's noisy audio for an enhancer that runs as a separate process
    (DFN3, SGMSE+). Clean is not written: index.csv records each window's start, so
    score_windows slices the same window out of the manifest's own clean file.

    Files are named w00000.wav and index.csv maps them back to (half, start, uid).
    The uid cannot go in the file name: MarVEN uids look like
    "19-198-0001|hurricane|-15" and Windows forbids '|' in a path."""
    import soundfile as sf
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (r, h, s, x, _) in enumerate(_windows(fold_name, limit)):
        name = f"w{i:05d}.wav"
        p = d / name
        if not p.exists():
            sf.write(str(p), x, C.SR, subtype="FLOAT")
        rows.append({"name": name, "half": h, "start": s, "uid": r.uid,
                     "noise_type": r.noise_type, "snr": int(r.target_snr_db)})
    pd.DataFrame(rows).to_csv(d / "index.csv", index=False)
    print(f"{len(rows)} windows + index.csv -> {d}")
    return len(rows)


def export_plan(fold_name: str, out: Path, splits=("train", "val")) -> Path:
    """Half-A crop plan for a trainer that cannot import this module. DFN3 lives in the
    dfnet env, which has no pyyaml, so instead of exporting audio this writes one row per
    usable utterance with its valid half-A start ranges in samples. The trainer draws its
    own random crop inside them, so the 3 s random-crop protocol is unchanged and no
    audio is duplicated on disk."""
    df = D.load_manifest()
    fold = seg_fold(df, fold_name)
    rows = []
    for split in splits:
        f = fold[split]
        for r in f[f.seg_A.map(len) > 0].itertuples():
            rows.append({"split": split, "uid": r.uid, "noise_type": r.noise_type,
                         "snr": int(r.target_snr_db), "win": WIN,
                         "noisy": str(C.ROOT / r.noisy_path),
                         "clean": str(C.ROOT / r.clean_path),
                         "ranges": ";".join(f"{lo}:{hi}" for lo, hi in r.seg_A)})
    out.parent.mkdir(parents=True, exist_ok=True)
    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    print(f"plan: {len(d)} rows ({d.split.value_counts().to_dict()}) -> {out}")
    return out


def ext_metrics(x: np.ndarray, y: np.ndarray, e: np.ndarray) -> dict:
    """Output-STFT energy split of one enhanced window, in src.diverse.analyse's basis
    and column names, via the numpy STFT in src.pilot_level (the same composition
    src.xcorpus.ext_score uses). There is no mask, so no mask-intent ("_i") split."""
    from src.pilot_level import G_MAX, G_MIN, mag, ratios, si_sdr
    e = np.pad(e, (0, max(0, len(x) - len(e))))[:len(x)]    # DFN3 pads; SGMSE+ can trim
    X, Cm, Y = mag(x), mag(y), mag(e)
    yc = y.astype(np.float64) - y.mean()
    g = float((e.astype(np.float64) - e.mean()) @ yc / (yc @ yc + 1e-12))
    ro, ru, ra = ratios(Y, Cm, X)
    rog, rug, rag = ratios(Y / np.clip(g, G_MIN, G_MAX), Cm, X)
    rob, rub, _ = ratios(X, Cm, X)
    return {"sisdr_in": si_sdr(x, y), "sisdr_out": si_sdr(e, y),
            "r_over": ro, "r_under": ru, "r_add": ra,
            "r_over_b4": rob, "r_under_b4": rub,
            "g": g, "r_over_g": rog, "r_under_g": rug, "r_add_g": rag}


def score_windows(tag: str, fold_name: str, enh_dir: Path, limit=None) -> pd.DataFrame:
    """Score a file-based enhancer's outputs on the exported windows into the CSVs gate
    U1 reads, so U2 is u1_verdict() on `tag` with no further glue.

    R1 (half A) against R2 (half B) only carries meaning if this enhancer was fine-tuned
    on half A alone, the way the b*_seg models were. A model that saw both halves, or
    neither, has R1 == R2 by construction and its U1 unit is empty, not passing."""
    import soundfile as sf
    enh = Path(enh_dir)
    idx = enh / "index.csv"
    if not idx.exists():
        raise SystemExit(f"{idx} missing: it must sit beside the enhanced wavs "
                         "(scripts/dfn_seg.py enhance copies it from the input dir)")
    ix = pd.read_csv(idx)
    index = dict(zip(ix["name"], zip(ix["half"], ix["start"].astype(int), ix["uid"])))
    want = {(h, s, r.uid): (r, x, y) for r, h, s, x, y in _windows(fold_name, limit)}
    rows = []
    for f in sorted(enh.glob("*.wav")):
        key = index.get(f.name)
        if key is None:
            print(f"  skip {f.name}: not in index.csv")
            continue
        h, s, uid = key
        if key not in want:
            print(f"  unmatched {f.name} ({h} {s} {uid})")
            continue
        r, x, y = want[key]
        e, sr = sf.read(str(f), dtype="float32")
        assert sr == C.SR, f"{f}: {sr} Hz"
        if e.ndim > 1:
            e = e.mean(axis=1)
        m = ext_metrics(x, y, e)
        rows.append({"uid": uid, "noise_type": r.noise_type, "snr": int(r.target_snr_db),
                     "half": h, "start": int(s),
                     **{f"{k}_seg": v for k, v in m.items()}})
    if not rows:
        raise SystemExit(f"no enhanced windows matched in {enh_dir}")
    d = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, halves in (("windows", HALVES), ("unseen", ("U",))):
        part = d[d.half.isin(halves)]
        if part.empty:
            print(f"  no {name} rows ({'/'.join(halves)}); U1 cannot score that rung")
            continue
        p = OUT / f"{tag}_seg_{fold_name}__{name}.csv"
        part.to_csv(p, index=False)
        print(f"wrote {p.name} n={len(part)}")
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
    ap.add_argument("--model", choices=["b1", "b3", "cm"], default="b3")
    ap.add_argument("--fold", choices=list(C.FAMILIES), default="weather")
    ap.add_argument("--smoke", action="store_true", help="500 steps, 40 test rows")
    ap.add_argument("--report", action="store_true", help="score saved CSVs, no training")
    ap.add_argument("--verify-loops", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="retrain from scratch")
    ap.add_argument("--export-windows", metavar="DIR",
                    help="write the windows as wavs for a file-based enhancer (U2)")
    ap.add_argument("--score-windows", metavar="DIR",
                    help="score a file-based enhancer's outputs in DIR; needs --tag")
    ap.add_argument("--tag", help="name of the file-based enhancer, e.g. dfn3")
    ap.add_argument("--export-plan", metavar="CSV",
                    help="half-A crop plan for a trainer in another env (U2, DFN3)")
    a = ap.parse_args(argv)

    with open(GATE_PATH) as fh:
        gate = yaml.safe_load(fh)["segment"]
    df = D.load_manifest()

    if a.verify_loops:
        verify_loops(df)
        return

    limit = 40 if a.smoke else None
    if a.export_plan:
        export_plan(a.fold, Path(a.export_plan))
        return

    if a.export_windows:
        export_windows(a.fold, Path(a.export_windows), limit)
        return

    if a.score_windows:
        if not a.tag:
            ap.error("--score-windows needs --tag")
        score_windows(a.tag, a.fold, Path(a.score_windows), limit)
        return

    if a.report:
        parts = []
        for p in sorted(OUT.glob("*_seg_*__windows.csv")):
            d = pd.read_csv(p)
            if "smoke" in p.stem or "si_sdr_out_full" not in d.columns:
                continue    # file-based enhancers (U2) have no `full` model to normalise by
            key, fold = p.stem.split("__")[0].split("_seg_")
            parts.append(summarize(d, key, fold))
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
    matched, _ = ensure_windows(a.model, a.fold, steps, limit, sfx, a.fresh)
    d = pd.read_csv(matched)
    s = summarize(d, a.model, a.fold)
    print("\n" + s.to_string(index=False))
    if a.smoke:
        print("\nsmoke run: wiring only, no verdict")
    else:
        print("\nVERDICT:", verdict(s.iloc[0], gate))


if __name__ == "__main__":
    main()
