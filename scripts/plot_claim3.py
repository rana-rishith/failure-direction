"""Claim 3 figure: within-condition d_rho heatmap + top-decile PR curve.

Usage (from the repo root, faildir env), after `python -m src.claim3 --fold X`
has been run for both folds:

    python scripts/plot_claim3.py --arm full --out figs/claim3_drho

Reads, never recomputes, d_rho and its bootstrap CI:
    results/metrics/claim3_{fold}_drho_ci.csv      (panel a, verdict text)
    results/predictions/claim3_{fold}_preds.csv    (panel b)

Each fold's test_matched set holds only that fold's own family, so the two
files together fill the five columns: weather columns from the weather fold,
anthropogenic columns from the anthro fold.

Panel (b) definition. Positives are the top decile of log10(r_over) inside each
(fold, SNR) stratum. Scores are each model's prediction converted to a
percentile rank inside the same stratum, then pooled. Without the rank step the
pooled curve would mix the eight strata on different prediction scales; with it
every stratum contributes ~10% positives and the chance line is ~0.10.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import config as C  # noqa: E402

SNRS = list(C.SNR_LEVELS)
COLS = ["rainfall", "lightning", "hurricane", "bubble_curtain", "large_commercial_ship"]
COL_FOLD = {c: "weather" for c in C.WEATHER} | {c: "anthro" for c in C.ANTHRO}
COL_LABEL = {"rainfall": "rainfall", "lightning": "lightning", "hurricane": "hurricane",
             "bubble_curtain": "bubble\ncurtain", "large_commercial_ship": "large comm.\nship"}
GAP = 0.15
XPOS = {c: i + (GAP if i >= 3 else 0.0) for i, c in enumerate(COLS)}

ORANGE, GREEN, GREY = "#e07b00", "#1b7f3b", "#8a8a8a"
CMAP = LinearSegmentedColormap.from_list("og", [ORANGE, "#ffffff", GREEN])
HATCH_N = 30


def load(arm: str, metrics: Path, preds_dir: Path, suffix: str):
    d, p = [], []
    for fold in C.FAMILIES:
        f = metrics / f"claim3_{fold}{suffix}_drho_ci.csv"
        g = preds_dir / f"claim3_{fold}{suffix}_preds.csv"
        for path in (f, g):
            if not path.exists():
                raise SystemExit(f"missing {path}\nrun: python -m src.claim3 --fold {fold}"
                                 f"{' --damaging-only' if suffix else ''}")
        d.append(pd.read_csv(f).assign(fold=fold))
        p.append(pd.read_csv(g).assign(fold=fold))
    d, p = pd.concat(d, ignore_index=True), pd.concat(p, ignore_index=True)
    need = {f"d_rho_{arm}", f"d_rho_{arm}_lo", f"d_rho_{arm}_hi"}
    if need - set(d.columns):
        raise SystemExit(f"drho CSVs lack {sorted(need - set(d.columns))}; arm '{arm}' not run?")
    if f"pred_{arm}" not in p or "pred_baseline" not in p:
        raise SystemExit(f"preds CSVs lack pred_{arm} / pred_baseline")
    return d, p


def cells(d: pd.DataFrame, arm: str) -> pd.DataFrame:
    c = d[d.level == "cell"].copy()
    c = c[c.apply(lambda r: COL_FOLD.get(r.noise_type) == r.fold, axis=1)]
    c = c.rename(columns={f"d_rho_{arm}": "v", f"d_rho_{arm}_lo": "lo", f"d_rho_{arm}_hi": "hi"})
    c["sig"] = (c.lo > 0) | (c.hi < 0)
    dup = c.duplicated(["noise_type", "snr"]).sum()
    if dup:
        raise SystemExit(f"{dup} duplicate (noise_type, snr) cells across folds")
    return c.set_index(["noise_type", "snr"])


def fmt(v: float) -> str:
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s.replace("-", "\u2212")


def panel_a(ax, cax, c: pd.DataFrame):
    vmax = np.ceil(np.nanmax(np.abs(c.v)) * 10) / 10
    norm = Normalize(-vmax, vmax)
    for col in COLS:
        for j, snr in enumerate(SNRS):
            x, y = XPOS[col], j
            if (col, snr) not in c.index:
                ax.add_patch(Rectangle((x, y), 1, 1, fc="#eeeeee", ec="white", lw=0.8))
                ax.text(x + .5, y + .5, "–", ha="center", va="center", fontsize=6.5, color=GREY)
                continue
            r = c.loc[(col, snr)]
            fc = CMAP(norm(r.v))
            ax.add_patch(Rectangle((x, y), 1, 1, fc=fc, ec="white", lw=0.8))
            if r.n < HATCH_N:
                ax.add_patch(Rectangle((x, y), 1, 1, fc="none", ec="#555555", lw=0,
                                       hatch="////", alpha=0.6))
            dark = abs(norm(r.v) - 0.5) > 0.36
            ax.text(x + .5, y + .5, fmt(r.v), ha="center", va="center",
                    fontsize=6.3, color="white" if dark else "black",
                    fontweight="bold" if r.sig else "normal")
    ax.set_xlim(0, XPOS[COLS[-1]] + 1)
    ax.set_ylim(len(SNRS), 0)                         # -15 dB on top
    ax.set_yticks(np.arange(len(SNRS)) + .5)
    ax.set_yticklabels([(f"{s:+d}" if s else "0").replace("-", "\u2212") for s in SNRS])
    ax.set_ylabel("Input SNR (dB)", labelpad=2)
    ax.set_xticks([XPOS[c] + .5 for c in COLS])
    ax.set_xticklabels([COL_LABEL[c] for c in COLS], fontsize=6.3)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    for label, cols in (("weather", COLS[:3]), ("anthropogenic", COLS[3:])):
        x0, x1 = XPOS[cols[0]] + .08, XPOS[cols[-1]] + .92
        ax.annotate("", xy=(x0, -0.25), xytext=(x1, -0.25), annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="black"))
        ax.text((x0 + x1) / 2, -0.4, label, ha="center", va="bottom", fontsize=7)
    cb = plt.colorbar(ScalarMappable(norm, CMAP), cax=cax)
    cb.set_label("Δρ (predictor − baseline)", fontsize=7)
    cb.ax.tick_params(labelsize=6, length=2)
    cb.outline.set_linewidth(0.4)


def pr_inputs(p: pd.DataFrame, arm: str):
    g = p.groupby(["fold", "snr"])
    pos = (p.y >= g.y.transform(lambda s: s.quantile(0.90))).to_numpy()
    score = {k: g[f"pred_{k}"].rank(pct=True).to_numpy() for k in (arm, "baseline")}
    return pos, score


def panel_b(ax, pos, score, arm):
    out = {}
    for k, color, ls, name in ((arm, GREEN, "-", "predictor"), ("baseline", GREY, "--", "baseline")):
        pr, rc, _ = precision_recall_curve(pos, score[k])
        ap = average_precision_score(pos, score[k])
        out[k] = ap
        ax.plot(rc, pr, color=color, ls=ls, lw=1.2, label=f"{name} (AUPRC {ap:.2f})")
    ax.axhline(0.10, color="black", ls=":", lw=0.8, label="chance (0.10)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision", labelpad=2)
    ax.grid(True, lw=0.3, alpha=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=6.5, handlelength=2.2)
    return out


def verdict(d: pd.DataFrame, c: pd.DataFrame, arm: str) -> tuple[str, pd.DataFrame]:
    s = d[d.level == "snr"]
    w = (s.assign(wv=s[f"d_rho_{arm}"] * s.n).groupby("snr")
          .agg(wv=("wv", "sum"), n=("n", "sum"), folds=("fold", "nunique")))
    w["d_rho"] = w.wv / w.n
    k = int((w.d_rho > 0).sum())
    per = []
    for col in COLS:
        v = c.v.xs(col, level="noise_type") if col in c.index.get_level_values(0) else pd.Series()
        per.append(f"{col} {int((v > 0).sum())}/{len(v)}")
    return f"Δρ > 0 in {k}/{len(w)} SNR strata;  per noise type: " + ", ".join(per), w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="full", choices=["full", "feats_only"],
                    help="which feature arm is 'the predictor'")
    ap.add_argument("--damaging", action="store_true", help="read the --damaging-only outputs")
    ap.add_argument("--metrics", type=Path, default=C.METRICS)
    ap.add_argument("--preds", type=Path, default=C.PREDICTIONS)
    ap.add_argument("--out", type=Path, default=REPO / "figs" / "claim3_drho")
    a = ap.parse_args()

    d, p = load(a.arm, a.metrics, a.preds, "_damaging" if a.damaging else "")
    c = cells(d, a.arm)
    pos, score = pr_inputs(p, a.arm)

    plt.rcParams.update({"font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 6.5,
                         "ytick.labelsize": 6.5, "font.family": "serif", "pdf.fonttype": 42,
                         "ps.fonttype": 42, "hatch.linewidth": 0.4})
    fig = plt.figure(figsize=(7.16, 3.0))
    # panel (a) = heatmap + colourbar, panel (b) = PR; 3:2 overall, spacer between
    gs = fig.add_gridspec(1, 5, width_ratios=[2.62, 0.08, 0.08, 0.80, 1.62], wspace=0.0,
                          left=0.065, right=0.985, top=0.86, bottom=0.25)
    axa, cax = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 2])
    axb = fig.add_subplot(gs[0, 4])

    panel_a(axa, cax, c)
    aps = panel_b(axb, pos, score, a.arm)
    text, w = verdict(d, c, a.arm)
    fig.text(0.5, 0.012, text.replace("_", " ").replace(";  ", ";\n"), ha="center", va="bottom",
             fontsize=8, linespacing=1.15)
    axa.set_title("(a)", loc="left", fontsize=8, fontweight="bold", pad=14)
    axb.set_title("(b)", loc="left", fontsize=8, fontweight="bold", pad=14)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out.with_suffix(".pdf"))
    fig.savefig(a.out.with_suffix(".png"), dpi=300)
    print(f"saved {a.out.with_suffix('.pdf')} and .png  (predictor = {a.arm})\n")

    pd.set_option("display.width", 200)
    print("Panel (a) cells, as read:")
    print(c[["fold", "n", "v", "lo", "hi", "sig"]].round(3).to_string(), "\n")
    print(f"bold (CI excludes 0): {int(c.sig.sum())}/{len(c)}   hatched (n<{HATCH_N}): "
          f"{int((c.n < HATCH_N).sum())}/{len(c)}   missing cells: {len(COLS)*len(SNRS) - len(c)}")
    print("\nVerdict strata (n-weighted mean of per-fold within-SNR Δρ):")
    print(w[["n", "folds", "d_rho"]].round(3).to_string())
    print(f"\nPanel (b): positives {pos.sum()}/{len(pos)} = {pos.mean():.3f}; "
          f"AUPRC predictor {aps[a.arm]:.3f}, baseline {aps['baseline']:.3f}")
    print("\n" + text)


if __name__ == "__main__":
    main()
