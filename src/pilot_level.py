"""Level-aligned re-score of the zero-shot pilot outputs (gate_pilot_level.yaml).

Usage: python -m src.pilot_level <sgmse_dir> <marven_dir>
Writes results/pilot_level/{per_row,by_snr,by_type,verdict}.csv
Numpy-only so it runs without torch; STFT matches torch.stft(center=True,
reflect pad, periodic Hann).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf

N_FFT, HOP, K0 = 512, 128, 2
G_MIN, G_MAX = 0.1, 10.0
WIN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)


def mag(x):
    x = np.pad(x.astype(np.float64), N_FFT // 2, mode="reflect")
    n = 1 + (len(x) - N_FFT) // HOP
    fr = np.lib.stride_tricks.as_strided(x, (n, N_FFT), (x.strides[0] * HOP, x.strides[0]))
    return np.abs(np.fft.rfft(fr * WIN, axis=1)).T[K0:]


def ratios(Y, C, X):
    ec = (C ** 2).sum()
    return (np.clip(C - Y, 0, None) ** 2).sum() / ec, (np.clip(Y - C, 0, None) ** 2).sum() / ec, \
        (np.clip(Y - X, 0, None) ** 2).sum() / ec


def si_sdr(e, r, eps=1e-8):
    e, r = e.astype(np.float64) - e.mean(), r.astype(np.float64) - r.mean()
    t = (e @ r) / (r @ r + eps) * r
    return 10 * np.log10((t @ t) / ((e - t) @ (e - t) + eps))


def score(out_dir, root, man):
    rows = []
    for f in sorted(out_dir.glob("*.wav")):
        r = man.loc[f.name]
        x, _ = sf.read(root / r.noisy_path, dtype="float32")
        y, _ = sf.read(root / r.clean_path, dtype="float32")
        e, _ = sf.read(f, dtype="float32")
        n = min(len(x), len(y), len(e)); x, y, e = x[:n], y[:n], e[:n]
        X, C, Y = mag(x), mag(y), mag(e)
        yc = y.astype(np.float64) - y.mean()
        g = float((e.astype(np.float64) - e.mean()) @ yc / (yc @ yc + 1e-12))
        ro, ru, ra = ratios(Y, C, X)
        rog, rug, rag = ratios(Y / np.clip(g, G_MIN, G_MAX), C, X)
        rob, rub, _ = ratios(X, C, X)
        rows.append(dict(file=f.name, noise=r.noise_type, snr=int(r.target_snr_db),
                         sisdr_gain=si_sdr(e, y) - si_sdr(x, y), g=g,
                         r_over=ro, r_under=ru, r_add=ra, r_over_g=rog, r_under_g=rug, r_add_g=rag,
                         r_over_b4=rob, r_under_b4=rub))
    return pd.DataFrame(rows)


def derive(f, b):
    ro, ru = f["r_over" + b], f["r_under" + b]
    f["d" + b] = (ro - ru) / (ro + ru + 1e-8)
    f["noise_removed" + b] = 1 - ru / f.r_under_b4
    f["over_x_floor" + b] = ro / f.r_over_b4


def main(sg, root):
    sg, root = Path(sg), Path(root)
    man = pd.read_csv(root / "manifest.csv")
    man.index = man.noisy_path.map(lambda p: Path(p).name)
    out = Path("results/pilot_level"); out.mkdir(parents=True, exist_ok=True)
    allf, verdict = [], []
    for model, d in [("sgmse", "pilot_out"), ("dfn3", "dfn_out")]:
        f = score(sg / d, root, man); f.insert(0, "model", model)
        for b in ("", "_g"):
            derive(f, b)
        old = pd.read_csv(sg / f"{d}_metrics.csv")
        rep = max(abs(f.r_over.median() / old.r_over.median() - 1), abs(f.r_under.median() / old.r_under.median() - 1))
        bys = f.groupby("snr")["d_g"].median()
        dpos, nr = int((bys > 0).sum()), f.noise_removed_g.median()
        if f.d_g.median() < -0.3: v = "reversed"
        elif dpos >= 6 and nr >= 0.80: v = "survives"
        elif (bys <= 0).sum() >= 3 or nr < 0.80: v = "partly_level"
        else: v = "unclassified"
        verdict.append(dict(model=model, repro_rel_err=rep, repro_ok=rep < 1e-3, snrs_d_pos=dpos,
                            noise_removed_g=nr, d_g_pooled=f.d_g.median(), d_plain_pooled=f.d.median(),
                            g_median=f.g.median(), verdict=v))
        allf.append(f)
    f = pd.concat(allf)
    cols = ["g", "d", "d_g", "noise_removed", "noise_removed_g", "over_x_floor_g", "r_add_g", "sisdr_gain"]
    f.to_csv(out / "per_row.csv", index=False)
    s = f.groupby(["model", "snr"])[cols].median(); s.to_csv(out / "by_snr.csv")
    t = f.groupby(["model", "noise"])[cols].median(); t.to_csv(out / "by_type.csv")
    v = pd.DataFrame(verdict); v.to_csv(out / "verdict.csv", index=False)
    pd.set_option("display.width", 220)
    print(s.round(3).to_string()); print(); print(t.round(3).to_string()); print(); print(v.round(4).to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:3])
