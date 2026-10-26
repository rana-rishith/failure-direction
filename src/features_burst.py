"""
Burst / impulse features for Claim 3b (configs/gate_claim3b.yaml).

    python -m src.features_burst

Why these exist: Claim 3 (gate C3_active) failed in the anthro fold, and the
failure sits on bubble_curtain, whose labels are seed-stable (label_stability.py:
median within-cell seed-to-seed rho 0.85). So the target is learnable; the 33
features in src.features miss what drives it. Bubble-curtain noise is bursty and
partly out of band, so these 12 features describe bursts, onsets, fast modulation
and the energy below and above the speech band.

The feature set was FIXED before any Claim 3b model was fitted, and it is the
same for every noise type. Like src.features, it reads noisy_path only.

12 features (prefix bst_):
  bst_crest_db      waveform peak / RMS, dB
  bst_rate5         share of frames > 5 dB above the median frame level
  bst_rate10        share of frames > 10 dB above the median frame level
  bst_onset_p90     p90 of positive frame-to-frame level jumps (dB)
  bst_onset_rate    share of frame steps with a level jump > 6 dB
  bst_lo_kurt       kurtosis over time of 0-500 Hz band energy (log)
  bst_hi_kurt       kurtosis over time of 4-8 kHz band energy (log)
  bst_sub150        share of energy below 150 Hz
  bst_hi_peak_db    p95 / median of 4-8 kHz band energy over time, dB
  bst_mod_slow      share of envelope modulation energy at 0.5-2 Hz
  bst_mod_fast      share of envelope modulation energy at 8-32 Hz
  bst_lohi_corr     correlation over time of 0-500 Hz and 4-8 kHz log energy
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd
from scipy.signal import get_window

import config as C
from src import data as D
from src.features import assert_reference_free

OUT_DIR = C.EVAL / "features_burst"
_WIN = get_window("hann", C.N_FFT)


def _kurt(v: np.ndarray) -> float:
    v = v - v.mean()
    return float((v ** 4).mean() / ((v.var() + 1e-12) ** 2))


def feats(x: np.ndarray, sr: int = C.SR) -> dict[str, float]:
    x = np.asarray(x, dtype=np.float64)
    if len(x) < C.N_FFT:
        x = np.pad(x, (0, C.N_FFT - len(x)))
    nf = 1 + (len(x) - C.N_FFT) // C.HOP
    idx = np.arange(C.N_FFT)[None, :] + C.HOP * np.arange(nf)[:, None]
    P = np.abs(np.fft.rfft(x[idx] * _WIN, axis=1)) ** 2 + 1e-20
    f = np.fft.rfftfreq(C.N_FFT, 1 / sr)

    lvl = 10 * np.log10(P.sum(1) + 1e-12)                 # frame level, dB
    rel = lvl - np.median(lvl)
    step = np.diff(lvl) if nf > 1 else np.zeros(1)
    up = step[step > 0]

    lo = np.log10(P[:, f < 500].sum(1) + 1e-12)
    hi_lin = P[:, f >= 4000].sum(1) + 1e-12
    hi = np.log10(hi_lin)
    corr = float(np.corrcoef(lo, hi)[0, 1]) if nf > 2 and lo.std() > 0 and hi.std() > 0 else 0.0

    env = lvl - lvl.mean()
    mf = np.fft.rfftfreq(len(env), C.HOP / sr)
    ME = np.abs(np.fft.rfft(env)) ** 2
    tot = ME[1:].sum() + 1e-12

    rms = np.sqrt((x ** 2).mean()) + 1e-12
    return {
        "bst_crest_db": float(20 * np.log10(np.abs(x).max() / rms + 1e-12)),
        "bst_rate5": float((rel > 5).mean()),
        "bst_rate10": float((rel > 10).mean()),
        "bst_onset_p90": float(np.percentile(up, 90)) if len(up) else 0.0,
        "bst_onset_rate": float((step > 6).mean()),
        "bst_lo_kurt": _kurt(lo),
        "bst_hi_kurt": _kurt(hi),
        "bst_sub150": float(P[:, f < 150].sum() / P.sum()),
        "bst_hi_peak_db": float(10 * np.log10(np.percentile(hi_lin, 95) / np.median(hi_lin))),
        "bst_mod_slow": float(ME[(mf >= 0.5) & (mf < 2)].sum() / tot),
        "bst_mod_fast": float(ME[(mf >= 8) & (mf <= 32)].sum() / tot),
        "bst_lohi_corr": corr,
    }


NAMES = list(feats(np.random.default_rng(0).standard_normal(C.SR)).keys())
assert_reference_free(NAMES)


def extract(frame: pd.DataFrame, fold: str, split: str, resume: bool = True,
            log_every: int = 2000) -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{fold}__{split}.csv"
    if resume and out.exists():
        prev = pd.read_csv(out)
        if len(prev) == len(frame):
            print(f"skip {out.name} (n={len(prev)})")
            return prev
    rows, t0 = [], time.time()
    for i in range(len(frame)):
        r = frame.iloc[i]
        x = D.read_mono(r.noisy_path)          # noisy only, never r.clean_path
        rows.append({"fold": fold, "split": split, "row_idx": i, "uid": r.uid, **feats(x)})
        if log_every and (i + 1) % log_every == 0:
            el = (time.time() - t0) / 60
            print(f"  {fold}/{split} {i+1}/{len(frame)} {el:.1f}m", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    print(f"wrote {out.name} n={len(d)} {(time.time()-t0)/60:.1f}m  NaN {int(d.isna().sum().sum())}")
    return d


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Burst features for Claim 3b")
    p.add_argument("--no-resume", action="store_true")
    a = p.parse_args(argv)
    folds = D.build_folds()
    for fold in C.FAMILIES:
        for split in ("train", "val", "test_matched"):
            extract(folds[fold][split], fold, split, resume=not a.no_resume)


if __name__ == "__main__":
    main()
