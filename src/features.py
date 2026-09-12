"""
Reference-free input features — the pre-hoc side of Claim 3.

    python -m src.features

NOTHING in this module may touch clean_path. That constraint is what the whole
claim rests on, so it is enforced two ways: `extract()` only ever reads
`noisy_path`, and `assert_reference_free()` is called by the Claim 3 verdict on
the final feature list.

Explicitly NOT admissible (they are computed against the clean reference and are
diagnostic only, from the WER work): frac_pos, med_frame_snr, p10, iqr of frame
SNR measured against clean.

33 features:
  log_e_noisy, dur, n_frames, kurt_wave, kurt_fe, lfe_range, snr_bin_med,
  snr_bin_max, mod_4hz, 4 band ratios, plus {med,iqr,p10,p90} x
  {flatness, centroid, spread, flux, frame-SNR proxy}.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd
from scipy.signal import get_window

import config as C
from src import data as D

_WIN = get_window("hann", C.N_FFT)
BANDS = ((0, 500), (500, 2000), (2000, 4000), (4000, 8000))


def _stats(v: np.ndarray, prefix: str) -> dict[str, float]:
    return {
        f"{prefix}_med": float(np.median(v)),
        f"{prefix}_iqr": float(np.subtract(*np.percentile(v, [75, 25]))),
        f"{prefix}_p10": float(np.percentile(v, 10)),
        f"{prefix}_p90": float(np.percentile(v, 90)),
    }


def feats(x: np.ndarray, sr: int = C.SR) -> dict[str, float]:
    """
    Frame the waveform with the same window and hop as the enhancer's STFT, but
    without centre padding — these features are independent of the label-side
    STFT and only need to be internally consistent.
    """
    x = np.asarray(x, dtype=np.float64)
    if len(x) < C.N_FFT:
        x = np.pad(x, (0, C.N_FFT - len(x)))
    nf = 1 + (len(x) - C.N_FFT) // C.HOP
    idx = np.arange(C.N_FFT)[None, :] + C.HOP * np.arange(nf)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * _WIN, axis=1)) + 1e-10     # (frames, bins)
    P = S ** 2
    fe = P.sum(1)                                              # frame energy
    lfe = np.log10(fe + 1e-12)
    f = np.fft.rfftfreq(C.N_FFT, 1 / sr)

    # noise floor from a low percentile per bin over time (min-statistics proxy)
    floor = np.percentile(P, 10, axis=0)
    snr_bin = np.log10((P.mean(0) + 1e-12) / (floor + 1e-12))
    frame_snr = np.log10((fe + 1e-12) / (floor.sum() + 1e-12))

    flat = np.exp(np.log(S).mean(1)) / (S.mean(1) + 1e-12)     # spectral flatness
    cent = (S * f).sum(1) / (S.sum(1) + 1e-12)
    spread = np.sqrt((S * (f - cent[:, None]) ** 2).sum(1) / (S.sum(1) + 1e-12))
    flux = np.sqrt((np.diff(S / (S.sum(1, keepdims=True) + 1e-12), axis=0) ** 2).sum(1)) \
        if nf > 1 else np.zeros(1)

    be = [P[:, (f >= lo) & (f < hi)].sum() / (P.sum() + 1e-12) for lo, hi in BANDS]

    # 4 Hz modulation energy of the log-energy envelope (speech-rate band 2-8 Hz)
    env = lfe - lfe.mean()
    fps = sr / C.HOP
    mf = np.fft.rfftfreq(len(env), 1 / fps)
    ME = np.abs(np.fft.rfft(env)) ** 2
    mod = ME[(mf >= 2) & (mf <= 8)].sum() / (ME.sum() + 1e-12)

    d = {
        "log_e_noisy": float(np.log10(P.sum() + 1e-12)),
        "dur": len(x) / sr,
        "n_frames": float(nf),
        "kurt_wave": float(((x - x.mean()) ** 4).mean() / ((x.var() + 1e-12) ** 2)),
        "kurt_fe": float(((lfe - lfe.mean()) ** 4).mean() / ((lfe.var() + 1e-12) ** 2)),
        "lfe_range": float(np.percentile(lfe, 95) - np.percentile(lfe, 5)),
        "snr_bin_med": float(np.median(snr_bin)),
        "snr_bin_max": float(snr_bin.max()),
        "mod_4hz": float(mod),
        "band_lo": float(be[0]), "band_lomid": float(be[1]),
        "band_himid": float(be[2]), "band_hi": float(be[3]),
    }
    for v, p in ((flat, "flat"), (cent, "cent"), (spread, "spread"),
                 (flux, "flux"), (frame_snr, "fsnr")):
        d.update(_stats(np.asarray(v), p))
    return d


FORBIDDEN_SUBSTRINGS = ("clean", "ref", "oracle", "e_over", "e_under", "target_snr")


def assert_reference_free(columns) -> None:
    bad = [c for c in columns
           if any(s in c.lower() for s in FORBIDDEN_SUBSTRINGS)]
    if bad:
        raise AssertionError(f"reference leak in feature list: {bad}")


def extract(frame: pd.DataFrame, fold: str, split: str, resume: bool = True,
            log_every: int = 1000) -> pd.DataFrame:
    C.ensure_dirs()
    out = C.FEATURES / f"{fold}__{split}.csv"
    if resume and out.exists():
        prev = pd.read_csv(out)
        if len(prev) == len(frame):
            print(f"skip {out.name} (n={len(prev)})")
            return prev
        print(f"re-running {out.name}: has {len(prev)} rows, expected {len(frame)}")

    rows, t0 = [], time.time()
    for i in range(len(frame)):
        r = frame.iloc[i]
        x = D.read_mono(r.noisy_path)          # noisy only — never r.clean_path
        rows.append({"fold": fold, "split": split, "row_idx": i, "uid": r.uid, **feats(x)})
        if log_every and (i + 1) % log_every == 0:
            el = (time.time() - t0) / 60
            print(f"  {fold}/{split} {i+1}/{len(frame)} {el:.1f}m "
                  f"~{el/(i+1)*(len(frame)-i-1):.0f}m left", flush=True)

    d = pd.DataFrame(rows)
    assert_reference_free([c for c in d.columns if c not in ("fold", "split", "row_idx", "uid")])
    d.to_csv(out, index=False)
    print(f"wrote {out.name} n={len(d)} {(time.time()-t0)/60:.1f}m")
    return d


def run(folds=None, splits=("train", "val", "test_matched"), resume: bool = True):
    folds = folds or D.build_folds()
    parts = []
    for fold in C.FAMILIES:
        for split in splits:
            parts.append(extract(folds[fold][split], fold, split, resume=resume))
    return pd.concat(parts, ignore_index=True)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Reference-free feature extraction")
    p.add_argument("--no-resume", action="store_true")
    a = p.parse_args(argv)
    F = run(resume=not a.no_resume)
    print(f"\n{len(F)} rows | "
          f"{len([c for c in F.columns if c not in ('fold','split','row_idx','uid')])} features | "
          f"NaN {int(F.isna().sum().sum())}")


if __name__ == "__main__":
    main()
