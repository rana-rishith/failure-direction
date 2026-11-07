"""
fig_spectrograms.py -- 1 x 5 spectrogram figure (double column, 7.16 x 2.1 in).

"Matched vs unseen, same utterance"
    clean | noisy | B1 trained weather (matched) | B1 trained anthro (unseen) | both masks

Selection uses the canonical r_over (low band below DECOMP_MIN_HZ excluded,
src/metrics.py::energy_decomposition), read from results/eval.

Run from the repo root in the faildir env:
    python fig_spectrograms.py [eval_dir]
"""
import os, sys
from pathlib import Path

# Paths come from the shell (make_figs.ps1 sets both). The old hard-coded paths
# pointed at a stale clone and a MarVEN copy that no longer exists.
REPO = Path(__file__).resolve().parents[1]   # the script lives in scripts/
for _v in ("FAILDIR_ROOT", "FAILDIR_CKPT"):
    if _v not in os.environ:
        raise SystemExit(f"set {_v} first (or run make_figs.ps1)")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd
import soundfile as sf
import torch
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src.models import load_model

ROOT = Path(os.environ["FAILDIR_ROOT"])
EVAL_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "eval"
OUT_DIR = REPO / "figures"
OUT_NAME = "fig_spectrograms"

ARCH = {"b1": "b1"}               # arch name as src.models.load_model expects it
ROW1_SNR = -5
CROP = (4.0, 10.0)                # seconds shown; enhancement runs on the full utterance

SR, N_FFT, HOP = 16000, 512, 128
DB_RANGE = 80.0
DEV = "cuda" if torch.cuda.is_available() else "cpu"
WEATHER = {"rainfall", "lightning", "hurricane"}

print(sys.executable)
assert "faildir" in sys.executable, "wrong interpreter"
assert (ROOT / "manifest.csv").exists(), f"manifest not found under {ROOT}"


# ---------------------------------------------------------------- data
def make_folds():
    df = pd.read_csv(ROOT / "manifest.csv")
    df["family"] = np.where(df.noise_type.isin(WEATHER), "weather", "anthro")

    def fold(fam):
        other = "anthro" if fam == "weather" else "weather"
        f = lambda sp, fm: df[(df.split == sp) & (df.family == fm)].reset_index(drop=True)
        return {"test_matched": f("test", fam), "test_unseen": f("test", other)}

    return {fam: fold(fam) for fam in ("weather", "anthro")}


def load_eval(arch, fold, split):
    path = EVAL_DIR / f"{arch}__{fold}__{split}.csv"
    assert path.exists(), f"missing {path}"
    d = pd.read_csv(path)
    need = {"row_idx", "e_over", "e_clean", "snr"}
    assert not (need - set(d.columns)), f"{path.name} missing {need - set(d.columns)}"
    d["r_over"] = d.e_over / d.e_clean                       # canonical, low band excluded
    if {"e_over_full", "e_clean_full"} <= set(d.columns):
        d["r_over_full"] = d.e_over_full / d.e_clean_full
    return d


def load_pair(row):
    x, sr1 = sf.read(ROOT / row.noisy_path, dtype="float32")
    y, sr2 = sf.read(ROOT / row.clean_path, dtype="float32")
    assert sr1 == sr2 == SR
    n = min(len(x), len(y))
    return x[:n], y[:n]


# ---------------------------------------------------------------- signal
def stft_mag(w):
    t = torch.as_tensor(w, dtype=torch.float32)
    X = torch.stft(t, N_FFT, HOP, window=torch.hann_window(N_FFT), return_complex=True)
    return X.abs().numpy()                                   # (F, T)


@torch.no_grad()
def enhance(arch, fold, x):
    m = load_model(ARCH[arch], f"{arch}_{fold}", kind="best").to(DEV).float().eval()
    est, M = m(torch.from_numpy(x)[None].to(DEV))            # fp32, no autocast
    return est[0].float().cpu().numpy(), M[0].float().cpu().numpy()


def db(S):
    return 20 * np.log10(np.maximum(S, 1e-8))


# ---------------------------------------------------------------- selection
folds = make_folds()
wt = folds["weather"]["test_matched"]
b1m = load_eval("b1", "weather", "test_matched")
cand = b1m[b1m.snr == ROW1_SNR]
assert len(cand), f"no rows at {ROW1_SNR} dB"
med = cand.r_over.median()
sel = cand.loc[(cand.r_over - med).abs().idxmin()]
R = int(sel.row_idx)
row = wt.iloc[R]
assert int(row.target_snr_db) == ROW1_SNR, "CSV row_idx does not line up with the fold frame"
assert folds["anthro"]["test_unseen"].iloc[R].noisy_path == row.noisy_path, \
    "weather test_matched and anthro test_unseen are not row-aligned"

b1u = load_eval("b1", "anthro", "test_unseen").set_index("row_idx").loc[R]

print("\n[Selection rule] among utterances in the weather test set at "
      f"{ROW1_SNR} dB (n={len(cand)}), choose the one whose B1 (trained on weather) "
      "r_over is closest to the median.")
print(f"  median r_over = {med:.4f}; chosen row_idx {R}, r_over = {sel.r_over:.4f}, "
      f"noise = {row.noise_type}, file = {row.noisy_path}")
if "r_over_full" in b1m:
    print(f"  (r_over with the low band included, for reference: {sel.r_over_full:.4f})")
print(f"  same utterance under B1 trained anthro: r_over = {b1u.r_over:.4f}")
print(f"  manifest: duration {row.duration_sec:.2f} s, noise_offset_sec {row.noise_offset_sec:.3f}, "
      f"mix_scale {row.mix_scale:.4f}")


# ---------------------------------------------------------------- compute
x, y = load_pair(row)
o_m, M_m = enhance("b1", "weather", x)
o_u, M_u = enhance("b1", "anthro", x)
specs = [db(stft_mag(y)), db(stft_mag(x)), db(stft_mag(o_m)), db(stft_mag(o_u))]

# Crop to the display window (frame t covers t*HOP/SR seconds).
T = specs[0].shape[1]
f0 = int(round(CROP[0] * SR / HOP))
f1 = min(T, int(round(CROP[1] * SR / HOP)))
assert f1 > f0, f"CROP {CROP} is outside the utterance ({T * HOP / SR:.2f} s)"
specs = [s[:, f0:f1] for s in specs]
M_m, M_u = M_m[:, f0:f1], M_u[:, f0:f1]
T0 = f0 * HOP / SR
print(f"  showing {T0:.2f}-{f1 * HOP / SR:.2f} s of {T * HOP / SR:.2f} s")

# Locate one-frame broadband discontinuities in the noise (splice / loop seam).
n_only = stft_mag(x - y)
jump = np.abs(np.diff(db(n_only).mean(axis=0)))
jump[:3] = jump[-3:] = 0                       # STFT edge frames, not real seams
for t in np.argsort(jump)[-3:][::-1]:
    print(f"  noise discontinuity candidate at {(t + 1) * HOP / SR:.2f} s "
          f"(broadband jump {jump[t]:.1f} dB)")
vmax = max(s.max() for s in specs)                          # shared colour scale
specs = [s - vmax for s in specs]


# ---------------------------------------------------------------- plot
mpl.rcParams.update({
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
    "xtick.labelsize": 6, "ytick.labelsize": 6,
    "font.family": "serif", "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2, "ytick.major.size": 2,
})
NAVY = LinearSegmentedColormap.from_list("white_navy", ["#ffffff", "#0b1f4d"])
SPEC = dict(cmap="magma", vmin=-DB_RANGE, vmax=0)

fig = plt.figure(figsize=(7.16, 2.1))
# cols: 4 spectrograms | dB bar | spacer for its labels | masks | mask bar
gs = fig.add_gridspec(1, 8, width_ratios=[1, 1, 1, 1, 0.05, 0.34, 1, 0.05],
                      left=0.095, right=0.905, bottom=0.20, top=0.80, wspace=0.08)


# Interior integer ticks only, so adjacent panels' end labels never collide.
XT = [t for t in range(int(np.ceil(CROP[0])) + 1, int(np.floor(CROP[1])))
      if (t - int(np.ceil(CROP[0]))) % 2 == 1]


def show(ax, S, **kw):
    ext = [T0, T0 + S.shape[1] * HOP / SR, 0, SR / 2000]
    im_ = ax.imshow(S, origin="lower", aspect="auto", extent=ext,
                    interpolation="nearest", rasterized=True, **kw)
    ax.set_xticks(XT)
    return im_


titles = ["Clean", "Noisy", "B1, trained weather\n(matched)",
          "B1, trained anthro\n(unseen)", "B1 masks"]
axes = []
for c, S in enumerate(specs):
    ax = fig.add_subplot(gs[0, c])
    im = show(ax, S, **SPEC)
    ax.set_yticks([0, 2, 4, 6, 8])
    if c == 0:
        ax.set_ylabel("Frequency (kHz)")
    else:
        ax.tick_params(labelleft=False)
    ax.set_title(titles[c], pad=3)
    axes.append(ax)

sub = gs[0, 6].subgridspec(2, 1, hspace=0.06)
for k, (M, lab) in enumerate([(M_m, "matched"), (M_u, "unseen")]):
    ax = fig.add_subplot(sub[k])
    imM = show(ax, M, cmap=NAVY, vmin=0, vmax=1)
    ax.set_yticks([0, 4, 8])
    ax.tick_params(labelleft=False, labelbottom=(k == 1))
    ax.text(0.03, 0.92, lab, transform=ax.transAxes, ha="left", va="top", fontsize=5.5,
            color="black", bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.7, lw=0))
    if k == 0:
        ax.set_title(titles[4], pad=3)
pm = ax.get_position()
fig.colorbar(im, cax=fig.add_subplot(gs[0, 4]), label="dB")
cbM = fig.colorbar(imM, cax=fig.add_subplot(gs[0, 7]), ticks=[0, 1])
cbM.ax.set_yticklabels(["0\nsuppress", "1\npass"], fontsize=5.5)
cbM.set_label("mask", labelpad=-2)

p0 = axes[0].get_position()
fig.text((p0.x0 + pm.x1) / 2, 0.02, "Time (s)", ha="center", va="bottom")
fig.text(0.018, (p0.y0 + p0.y1) / 2, "Matched vs unseen,\nsame utterance", rotation=90,
         ha="center", va="center", fontsize=7, fontweight="bold")

OUT_DIR.mkdir(parents=True, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(OUT_DIR / f"{OUT_NAME}.{ext}", dpi=300)
print(f"\nsaved {OUT_DIR / OUT_NAME}.pdf / .png")