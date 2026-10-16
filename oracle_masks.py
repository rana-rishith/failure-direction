"""Oracle-mask reference rows for Tables VII/VIII (deep review, concern 2).

    python oracle_masks.py [MarVEN root]

For every test utterance (both families, 2,280 rows), the noise is recovered
exactly as noisy - clean, and three oracle magnitude masks are applied to the
noisy STFT. The energy decomposition matches src/metrics.energy_decomposition:
predicted magnitude M*|X|, bins below 60 Hz excluded, and the STFT matches
torch.stft defaults (n_fft 512, hop 128, periodic Hann, centre, reflect pad).

    wiener  |S|^2 / (|S|^2 + |N|^2)
    irm     sqrt(wiener)
    iam1    min(|S| / |X|, 1)     best possible bounded mask; its r_over equals
                                  B4's by construction (the phase floor)

Needs numpy, pandas and the stdlib only.
"""
import math
import os
import sys
import wave

import numpy as np
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FAILDIR_ROOT", "data/MarVEN")
N_FFT, HOP, SR = 512, 128, 16000
K0 = int(math.ceil(60.0 * N_FFT / SR))
WIN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)


def read(p):
    w = wave.open(os.path.join(ROOT, p))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x


def stft_mag(x):
    x = np.pad(x, N_FFT // 2, mode="reflect")
    n = 1 + (len(x) - N_FFT) // HOP
    fr = np.lib.stride_tricks.as_strided(x, (n, N_FFT), (x.strides[0] * HOP, x.strides[0]))
    return np.abs(np.fft.rfft(fr * WIN, axis=1)).T


def decomp(M, X, S):
    yh = M * X
    over = (np.clip(S - yh, 0, None) ** 2)[K0:].sum()
    under = (np.clip(yh - S, 0, None) ** 2)[K0:].sum()
    return over, under, (S ** 2)[K0:].sum()


df = pd.read_csv(os.path.join(ROOT, "manifest.csv"))
df = df[df.split == "test"].reset_index(drop=True)
df["family"] = np.where(df.noise_type.isin(["rainfall", "lightning", "hurricane"]), "weather", "anthro")
out = "results/metrics/review_oracle_masks_rows.csv"
done = set(pd.read_csv(out).noisy_path) if os.path.exists(out) else set()
rows = []
for i, r in enumerate(df.itertuples()):
    if r.noisy_path in done:
        continue
    x, s = read(r.noisy_path), read(r.clean_path)
    n = min(len(x), len(s)); x, s = x[:n], s[:n]
    X, S, N = stft_mag(x), stft_mag(s), stft_mag(x - s)
    w = S ** 2 / (S ** 2 + N ** 2 + 1e-12)
    rec = {"noisy_path": r.noisy_path, "noise_type": r.noise_type, "family": r.family,
           "snr": int(r.target_snr_db)}
    for name, M in (("wiener", w), ("irm", np.sqrt(w)), ("iam1", np.minimum(S / (X + 1e-12), 1.0))):
        o, u, c = decomp(M, X, S)
        rec[f"r_over_{name}"], rec[f"r_under_{name}"] = o / c, u / c
    rows.append(rec)
    if len(rows) % 200 == 0:
        pd.DataFrame(rows).to_csv(out, mode="a", header=not os.path.exists(out), index=False)
        rows = []
        print(f"{i + 1}/{len(df)}", flush=True)
if rows:
    pd.DataFrame(rows).to_csv(out, mode="a", header=not os.path.exists(out), index=False)

d = pd.read_csv(out)
summ = []
for (fam, name) in [(f, m) for f in ("weather", "anthro") for m in ("wiener", "irm", "iam1")]:
    g = d[d.family == fam]
    ro, ru = g[f"r_over_{name}"], g[f"r_under_{name}"]
    dd = (ro - ru) / (ro + ru + 1e-8)
    summ.append({"family": fam, "mask": name, "n": len(g), "med_r_over": ro.median(),
                 "med_r_under": ru.median(), "ratio_over_under": ro.median() / max(ru.median(), 1e-12),
                 "med_d": dd.median()})
s = pd.DataFrame(summ)
s.to_csv("results/metrics/review_oracle_masks.csv", index=False)
print(s.round(4).to_string(index=False))
