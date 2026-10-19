"""Sanity check for zero-shot enhancer outputs on MarVEN.

Usage (from the sgmse folder, sgmse env active, $env:MARVEN set):
    python smoke_check.py smoke_out

For each enhanced wav, finds its noisy and clean pair in manifest.csv and prints
SI-SDR in/out and the energy split on the OUTPUT STFT (DC bins 0-1 excluded):
    r_over  = e_over  / e_clean   speech energy missing from the output
    r_under = e_under / e_clean   energy the output has beyond clean
    r_add   = energy the output adds beyond the noisy input (0 for bounded masks)
The _B4 columns are the same split for the noisy input (passthrough floor).
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch

N_FFT, HOP = 512, 128
WIN = torch.hann_window(N_FFT)


def mag(x):
    X = torch.stft(torch.from_numpy(x).float(), N_FFT, HOP, window=WIN, return_complex=True)
    return X.abs()[2:]  # drop DC bins 0-1


def si_sdr(est, ref, eps=1e-8):
    est = est - est.mean()
    ref = ref - ref.mean()
    a = (est * ref).sum() / ((ref ** 2).sum() + eps)
    t = a * ref
    return 10 * np.log10((t ** 2).sum() / (((est - t) ** 2).sum() + eps))


def split(Y, C, X):
    e_clean = (C ** 2).sum()
    e_over = ((C - Y).clamp(min=0) ** 2).sum() / e_clean
    e_under = ((Y - C).clamp(min=0) ** 2).sum() / e_clean
    e_add = ((Y - X).clamp(min=0) ** 2).sum() / e_clean
    return e_over.item(), e_under.item(), e_add.item()


def main(out_dir):
    root = Path(os.environ["MARVEN"])
    man = pd.read_csv(root / "manifest.csv")
    man["base"] = man.noisy_path.map(lambda p: Path(p).name)
    rows = []
    for f in sorted(Path(out_dir).glob("*.wav")):
        r = man[man.base == f.name]
        if r.empty:
            print(f"skip {f.name}: not in manifest")
            continue
        r = r.iloc[0]
        x, sr_x = sf.read(root / r.noisy_path, dtype="float32")
        y, sr_y = sf.read(root / r.clean_path, dtype="float32")
        e, sr_e = sf.read(f, dtype="float32")
        assert sr_x == sr_y == sr_e == 16000, f"sample rate mismatch in {f.name}"
        n = min(len(x), len(y), len(e))
        x, y, e = x[:n], y[:n], e[:n]
        X, C, Y = mag(x), mag(y), mag(e)
        ro, ru, ra = split(Y, C, X)
        bo, bu, _ = split(X, C, X)
        rows.append(dict(
            noise=r.noise_type, snr=int(r.target_snr_db),
            sisdr_in=si_sdr(x, y), sisdr_out=si_sdr(e, y),
            r_over=ro, r_over_B4=bo, r_under=ru, r_under_B4=bu, r_add=ra,
            len_ok=(len(e) >= len(x) - 1),
        ))
    df = pd.DataFrame(rows).sort_values(["noise", "snr"])
    pd.set_option("display.width", 200)

    csv_path = str(out_dir).rstrip("\\/") + "_metrics.csv"
    df.to_csv(csv_path, index=False)

    df["sisdr_gain"] = df.sisdr_out - df.sisdr_in
    df["over_x_floor"] = df.r_over / df.r_over_B4          # speech loss relative to passthrough
    df["noise_removed"] = 1 - df.r_under / df.r_under_B4   # fraction of noise excess removed
    df["d"] = (df.r_over - df.r_under) / (df.r_over + df.r_under + 1e-8)
    cols = ["sisdr_gain", "over_x_floor", "noise_removed", "d", "r_add"]

    if len(df) <= 10:
        print(df.round(4).to_string(index=False))
    print(f"\n{len(df)} files; all rows saved to {csv_path}")
    print(f"len_ok false: {(~df.len_ok).sum()}   r_add >= 0.05: {(df.r_add >= 0.05).sum()}")
    print("\nMedians by SNR:")
    print(df.groupby("snr")[cols].median().round(3).to_string())
    print("\nMedians by noise type:")
    print(df.groupby("noise")[cols].median().round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "smoke_out")