"""Level-aligned Claim 3 labels for ACTIVE models (configs/gate_claim3_active.yaml).

The target is computed from the output WAVEFORM, so one definition covers bounded
masks (b1, b3), the complex mask (cm) and DeepFilterNet3. It is the same quantity
as src.labels_level `e_over_lv`: |STFT(output)| / g against |STFT(clean)|, bins
>= DECOMP_MIN_HZ, g clipped to [G_MIN, G_MAX].

Subcommands (faildir env, FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.labels_active harness          # must pass before anything else
    python -m src.labels_active list             # rows_dfn.csv for src/dfn_marven.py
    python -m src.labels_active internal --tags b1_fsd b3_fsd cm_fsd ...
    python -m src.labels_active dfn --dfn-dir <dir with DFN3 outputs>

Output: results/labels_active/<tag>__<fold>__<split>.csv. Resumable: the internal
pass reads each file once for all tags and writes 1000-row chunks under _chunks/.
"""
from __future__ import annotations

import argparse
import math
import sys
import time

import config as C  # noqa: I001

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from scipy.stats import spearmanr

from src import data as D
from src import models as M

OUT = C.EVAL / "labels_active"
CHUNKS = OUT / "_chunks"
SPLITS = ("train", "val", "test_matched")
K0 = int(math.ceil(C.DECOMP_MIN_HZ * C.N_FFT / C.SR))
G_MIN, G_MAX = 0.1, 10.0          # same as src.labels_level
CHUNK = 1000
META = ["uid", "noise_type", "speaker_id", "chapter_id", "utterance_id", "duration_sec"]


def si_sdr(e: np.ndarray, r: np.ndarray, eps: float = 1e-8) -> float:
    e, r = e.astype(np.float64) - e.mean(), r.astype(np.float64) - r.mean()
    t = (e @ r) / (r @ r + eps) * r
    return float(10 * np.log10((t @ t) / ((e - t) @ (e - t) + eps)))


@torch.no_grad()
def wave_labels(e: np.ndarray, x: np.ndarray, y: np.ndarray, dev: str) -> dict:
    """e, x, y: float32 waveforms of equal length (output, noisy, clean)."""
    Cm = M.magnitude(torch.from_numpy(np.ascontiguousarray(y))[None].to(dev))[0]
    Yo = M.magnitude(torch.from_numpy(np.ascontiguousarray(e))[None].to(dev))[0]
    e64 = e.astype(np.float64)
    yc = y.astype(np.float64) - y.mean()
    g = float(np.dot(e64 - e64.mean(), yc) / (np.dot(yc, yc) + 1e-12))
    gu = float(np.clip(g, G_MIN, G_MAX))
    sl = slice(K0, None)
    Yl = Yo[sl] / gu
    return {"g": g, "e_clean": float((Cm[sl] ** 2).sum()),
            "e_over_lv": float(((Cm[sl] - Yl).clamp(min=0) ** 2).sum()),
            "e_under_lv": float(((Yl - Cm[sl]).clamp(min=0) ** 2).sum()),
            "sisdr_in": si_sdr(x, y), "sisdr_out": si_sdr(e, y)}


@torch.no_grad()
def enhance(model, x: np.ndarray, dev: str) -> np.ndarray:
    est, _ = model(torch.from_numpy(x)[None].to(dev))
    return est[0].float().cpu().numpy()


def meta(r, fold, split, i) -> dict:
    return {"fold": fold, "split": split, "row_idx": i, "uid": r.uid,
            "noise_type": r.noise_type, "snr": int(r.target_snr_db),
            "speaker_id": r.speaker_id, "chapter_id": r.chapter_id,
            "utterance_id": r.utterance_id, "duration_sec": r.duration_sec}


def final_path(tag, fold, split):
    return OUT / f"{tag}__{fold}__{split}.csv"


def is_done(tag, fold, split, n) -> bool:
    p = final_path(tag, fold, split)
    return p.exists() and len(pd.read_csv(p, usecols=["uid"])) == n


# ---------------------------------------------------------------- harness ---
def harness(dev: str) -> bool:
    """Gate: reproduce src.labels_level e_over_lv for b1_weather on weather val."""
    ref = C.EVAL / "labels_level" / "b1__weather__val.csv"
    old = pd.read_csv(ref)
    fr = D.build_folds()["weather"]["val"]
    assert len(old) == len(fr), f"{ref.name}: {len(old)} rows, fold has {len(fr)}"
    model = M.load_model("b1", "b1_weather", device=dev)   # same checkpoint call as src.labels_level
    new = []
    for i in range(len(fr)):
        x, y = D.read_pair(fr.iloc[i])
        new.append(wave_labels(enhance(model, x, dev), x, y, dev)["e_over_lv"])
    new = np.asarray(new)
    o = old.e_over_lv.to_numpy()
    assert (old.uid.to_numpy() == fr.uid.to_numpy()).all(), "row order differs from labels_level"
    rel = np.abs(new - o) / np.maximum(np.abs(o), 1e-12)
    rho = float(spearmanr(np.log10(new / old.e_clean + 1e-8), np.log10(o / old.e_clean + 1e-8)).statistic)
    ok = bool(np.median(rel) < 1e-4 and rho > 0.9999)
    print(f"harness: n={len(o)}  median rel diff {np.median(rel):.2e}  max {rel.max():.2e}  "
          f"spearman {rho:.6f}  ->  {'PASS' if ok else 'FAIL'}")
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"n": len(o), "median_rel": np.median(rel), "max_rel": rel.max(),
                   "spearman": rho, "pass": ok}]).to_csv(OUT / "harness.csv", index=False)
    return ok


# ------------------------------------------------------------ internal ------
def internal(tags: list[str], dev: str) -> None:
    folds = D.build_folds()
    CHUNKS.mkdir(parents=True, exist_ok=True)
    for fold in C.FAMILIES:
        for split in SPLITS:
            fr = folds[fold][split]
            n = len(fr)
            todo = [t for t in tags if not is_done(t, fold, split, n)]
            if not todo:
                print(f"{fold}/{split}: all {len(tags)} tags done")
                continue
            models = {t: M.load_model(t.split("_")[0], t, kind="best", device=dev) for t in todo}
            n_chunks = math.ceil(n / CHUNK)
            t0, done_rows = time.time(), 0
            print(f"{fold}/{split}: {n} rows x {len(models)} models ({', '.join(models)})", flush=True)
            for c in range(n_chunks):
                need = [t for t in todo if not (CHUNKS / f"{t}__{fold}__{split}__{c:03d}.csv").exists()]
                if not need:
                    continue
                rec = {t: [] for t in need}
                lo, hi = c * CHUNK, min((c + 1) * CHUNK, n)
                for i in range(lo, hi):
                    r = fr.iloc[i]
                    x, y = D.read_pair(r)
                    m = meta(r, fold, split, i)
                    for t in need:
                        rec[t].append({**m, **wave_labels(enhance(models[t], x, dev), x, y, dev)})
                for t in need:
                    pd.DataFrame(rec[t]).to_csv(CHUNKS / f"{t}__{fold}__{split}__{c:03d}.csv", index=False)
                done_rows += hi - lo
                el = (time.time() - t0) / 60
                left = el / done_rows * (n - hi)
                print(f"  {fold}/{split} {hi}/{n}  {el:.1f} min, ~{left:.0f} min left for this split", flush=True)
            for t in todo:
                parts = [pd.read_csv(CHUNKS / f"{t}__{fold}__{split}__{c:03d}.csv") for c in range(n_chunks)]
                d = pd.concat(parts, ignore_index=True)
                assert len(d) == n and (d.uid.to_numpy() == fr.uid.to_numpy()).all(), f"{t} {fold}/{split} misaligned"
                d.to_csv(final_path(t, fold, split), index=False)
                print(f"  wrote {final_path(t, fold, split).name}  median g {d.g.median():.3f}", flush=True)
            del models
            if dev == "cuda":
                torch.cuda.empty_cache()


# ------------------------------------------------------------------ DFN3 ----
def dfn_name(fold, split, i) -> str:
    return f"{fold}__{split}__{i:05d}.wav"


def write_list() -> None:
    folds = D.build_folds()
    rows = []
    for fold in C.FAMILIES:
        for split in SPLITS:
            fr = folds[fold][split]
            for i in range(len(fr)):
                rows.append({"name": dfn_name(fold, split, i), "noisy": str(C.ROOT / fr.noisy_path.iloc[i])})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "rows_dfn.csv", index=False)
    print(f"wrote {OUT / 'rows_dfn.csv'}: {len(rows)} rows")


def dfn(dfn_dir: str, dev: str) -> None:
    from pathlib import Path
    src = Path(dfn_dir)
    folds = D.build_folds()
    rows = []
    for fold in C.FAMILIES:
        for split in SPLITS:
            fr = folds[fold][split]
            n = len(fr)
            if is_done("dfn3", fold, split, n):
                print(f"dfn3 {fold}/{split}: done")
                continue
            rec, miss, t0 = [], 0, time.time()
            for i in range(n):
                f = src / dfn_name(fold, split, i)
                if not f.exists():
                    miss += 1
                    continue
                r = fr.iloc[i]
                x, y = D.read_pair(r)
                e, sr = sf.read(str(f), dtype="float32")
                assert sr == C.SR, f"{f}: {sr} Hz"
                if e.ndim > 1:
                    e = e.mean(axis=1)
                k = min(len(x), len(e))
                rec.append({**meta(r, fold, split, i), **wave_labels(e[:k], x[:k], y[:k], dev)})
                if (i + 1) % 2000 == 0:
                    print(f"  dfn3 {fold}/{split} {i + 1}/{n} {(time.time() - t0) / 60:.1f} min", flush=True)
            d = pd.DataFrame(rec)
            OUT.mkdir(parents=True, exist_ok=True)
            d.to_csv(final_path("dfn3", fold, split), index=False)
            rows.append({"fold": fold, "split": split, "n": n, "scored": len(d), "missing": miss,
                         "missing_frac": miss / n})
            print(f"dfn3 {fold}/{split}: scored {len(d)}, missing {miss} ({miss / n:.2%})", flush=True)
    if rows:
        pd.DataFrame(rows).to_csv(OUT / "dfn3_completeness.csv", index=False)


def main(argv=None):
    p = argparse.ArgumentParser(description="Claim 3 labels for active models")
    p.add_argument("cmd", choices=["harness", "list", "internal", "dfn"])
    p.add_argument("--tags", nargs="+", default=[])
    p.add_argument("--dfn-dir", default=None)
    a = p.parse_args(argv)
    dev = C.device()
    if a.cmd == "harness":
        sys.exit(0 if harness(dev) else 1)
    if a.cmd == "list":
        write_list()
    elif a.cmd == "internal":
        if not (OUT / "harness.csv").exists() or not bool(pd.read_csv(OUT / "harness.csv")["pass"].iloc[0]):
            sys.exit("harness has not passed; run `python -m src.labels_active harness` first (gate rule)")
        internal(a.tags, dev)
    elif a.cmd == "dfn":
        if not a.dfn_dir:
            sys.exit("--dfn-dir is required")
        dfn(a.dfn_dir, dev)


if __name__ == "__main__":
    main()
