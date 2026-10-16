"""WADA-SNR (Kim & Stern, Interspeech 2008) on the noisy input: a reference-free
SNR estimate, used as an extra Claim 3 baseline (deep review, concern 6).

    python wada_snr.py [MarVEN root]      -> results/features/wada_snr.csv (val + test rows)

The G(SNR) lookup is built by Monte Carlo from the paper's model: speech
amplitude Gamma-distributed with shape 0.4, additive Gaussian noise.
"""
import os
import sys
import wave

import numpy as np
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.environ.get("FAILDIR_ROOT", "data/MarVEN")
OUT = "results/features/wada_snr.csv"


def table(alpha=0.4, n=400_000, seed=0):
    rng = np.random.default_rng(seed)
    s = rng.gamma(alpha, 1.0, n) * rng.choice([-1, 1], n)
    s /= s.std()
    g = rng.standard_normal(n)
    db = np.arange(-20, 100.1, 0.1)
    G = []
    for d in db:
        z = np.abs(s + g * 10 ** (-d / 20)) + 1e-20
        G.append(np.log(z.mean()) - np.log(z).mean())
    return db, np.array(G)


DB, G = table()
G = np.maximum.accumulate(G)              # Monte Carlo jitter at the flat ends


def wada(x):
    x = x.astype(np.float64)
    v = np.abs(x - x.mean()) + 1e-20          # some clean files carry DC; remove it
    g = np.log(v.mean()) - np.log(v).mean()
    # G rises with SNR (Gaussian noise -> ~0.41, Gamma(0.4) speech -> larger)
    return float(np.interp(g, G, DB))


df = pd.read_csv(os.path.join(ROOT, "manifest.csv"))
df = df[df.split.isin(["val", "test"])].reset_index(drop=True)
if "--fresh" in sys.argv and os.path.exists(OUT):
    open(OUT, "w").close()
done = set(pd.read_csv(OUT).noisy_path) if os.path.exists(OUT) and os.path.getsize(OUT) else set()
rows = []
for i, r in enumerate(df.itertuples()):
    if r.noisy_path in done:
        continue
    w = wave.open(os.path.join(ROOT, r.noisy_path))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) / 32768.0
    uid = f"{r.speaker_id}-{r.chapter_id}-{int(r.utterance_id):04d}|{r.noise_type}|{int(r.target_snr_db):+d}"
    rows.append({"noisy_path": r.noisy_path, "uid": uid, "wada_snr": wada(x)})
    if len(rows) == 500:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not (os.path.exists(OUT) and os.path.getsize(OUT)), index=False)
        rows = []
        print(i + 1, flush=True)
if rows:
    pd.DataFrame(rows).to_csv(OUT, mode="a", header=not (os.path.exists(OUT) and os.path.getsize(OUT)), index=False)
d = pd.read_csv(OUT)
print(len(d), "rows; WADA vs nominal SNR correlation:",
      round(float(np.corrcoef(d.wada_snr, d.uid.str.split("|").str[2].astype(int))[0, 1]), 3))
