"""
fig_direction.py  —  Claim 2 figure (double column, 7.16 x 2.8 in)

(a) median r_over / r_under vs target SNR, matched (solid) vs unseen (dashed), IQR shading
(b) dir_idx half-violins per model, matched (navy, left) vs unseen (orange, right)

Input: per-utterance eval CSVs from src.evaluate (B1/B3 rows, both folds, both splits).
Needs columns: split, e_over, e_under, e_clean, and either `model` or `tag` (b1_*/b3_*).
If target_snr_db is missing it is joined back from the manifest on (fold, split, row_idx).

Usage:  python fig_direction.py --eval-dir <dir with eval CSVs> [--out fig_direction]
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

EPS = 1e-8
SNRS = [-15, -10, -5, 0, 5, 10, 15, 20]

C_OVER, C_UNDER = "#c0392b", "#7d3c98"          # red, purple
C_MATCH, C_UNSEEN = "#1f3a68", "#e67e22"        # navy, orange


# ----------------------------------------------------------------- data
def load_eval(eval_dir: Path) -> pd.DataFrame:
    files = sorted(eval_dir.rglob("*.csv"))
    files = [f for f in files if "no_pesq" not in f.parts]       # skip the archive
    if not files:
        raise FileNotFoundError(f"no CSVs under {eval_dir}")
    # src.evaluate writes <tag>__<fold>__<split>.csv — take identity from the filename,
    # which is authoritative, and only fall back to columns for other layouts
    parts = []
    for f in files:
        d = pd.read_csv(f)
        bits = f.stem.split("__")
        if len(bits) == 3:
            d["model"], d["fold"], d["split"] = bits[0].upper(), bits[1], bits[2]
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)

    if "model" not in df.columns:
        df["model"] = df["tag"].str.split("_").str[0]
    df["model"] = df["model"].str.upper()
    df = df[df["model"].isin(["B1", "B3"])].copy()
    df = df[df["split"].isin(["test_matched", "test_unseen"])]

    if "fold" not in df.columns:
        df["fold"] = df["tag"].str.split("_").str[1]
    assert df["fold"].notna().all(), "could not resolve fold for some rows"
    n = df.groupby(["model", "split"]).size()
    print("rows per model/split:\n" + n.to_string())

    if "target_snr_db" not in df.columns:
        df = _join_snr(df)

    dup = df.duplicated(["model", "fold", "split", "row_idx"]).sum() if "row_idx" in df else 0
    assert dup == 0, f"{dup} duplicate rows — check for stale CSVs in {eval_dir}"

    df["r_over"] = df.e_over / df.e_clean
    df["r_under"] = df.e_under / df.e_clean
    df["dir_idx"] = (df.r_over - df.r_under) / (df.r_over + df.r_under + EPS)
    return df


def _join_snr(df):
    root = Path(os.environ["FAILDIR_ROOT"])
    man = pd.read_csv(root / "manifest.csv")
    weather = {"rainfall", "lightning", "hurricane"}
    man["family"] = man.noise_type.map(lambda n: "weather" if n in weather else "anthro")
    parts = []
    for fam in ["weather", "anthro"]:
        other = "anthro" if fam == "weather" else "weather"
        for split, (sp, fm) in {"test_matched": ("test", fam),
                                "test_unseen": ("test", other)}.items():
            f = man[(man.split == sp) & (man.family == fm)].reset_index(drop=True)
            parts.append(pd.DataFrame({"fold": fam, "split": split, "row_idx": f.index,
                                       "target_snr_db": f.target_snr_db.values}))
    key = pd.concat(parts)
    out = df.merge(key, on=["fold", "split", "row_idx"], how="left", validate="m:1")
    assert out.target_snr_db.notna().all(), "SNR join failed for some rows"
    return out


# ----------------------------------------------------------------- style
def set_style():
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.direction": "in", "ytick.direction": "in",
        "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 1.2, "savefig.dpi": 300,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


# ----------------------------------------------------------------- panel a
def panel_a(ax, df):
    ls = {"test_matched": "-", "test_unseen": "--"}
    for col, color in [("r_over", C_OVER), ("r_under", C_UNDER)]:
        for split in ["test_matched", "test_unseen"]:
            g = df[df.split == split].groupby("target_snr_db")[col]
            q = g.quantile([0.25, 0.5, 0.75]).unstack().reindex(SNRS)
            # light fill + outline in the line's own style, so overlapping bands stay attributable
            ax.fill_between(SNRS, q[0.25], q[0.75], color=color, alpha=0.08, lw=0)
            for edge in (q[0.25], q[0.75]):
                ax.plot(SNRS, edge, color=color, ls=ls[split], lw=0.45, alpha=0.7)
            ax.plot(SNRS, q[0.5], color=color, ls=ls[split], marker="o", ms=2.2)

    ax.axhline(1, color="0.55", ls=":", lw=0.7, zorder=0)
    ax.text(21.0, 1.12, "failure energy = clean energy", color="0.45",
            fontsize=6, style="italic", va="bottom", ha="right")

    ax.set_yscale("log")
    ax.set_ylim(1e-4, 1e2)
    ax.set_xlim(-16.5, 21.5)
    ax.set_xticks(SNRS)
    ax.set_xlabel("input SNR (dB)")
    ax.set_ylabel("failure energy / clean energy")

    h = lambda c, l: Line2D([], [], color=c, ls=l, marker="o", ms=2.2)
    # ncol=2 fills column-wise -> rows read over/matched | over/unseen, under/matched | under/unseen
    handles = [h(C_OVER, "-"), h(C_UNDER, "-"), h(C_OVER, "--"), h(C_UNDER, "--")]
    labels = ["over / matched", "under / matched", "over / unseen", "under / unseen"]
    ax.legend(handles, labels, ncol=2, loc="upper right", frameon=False,
              handlelength=2.2, columnspacing=1.0, borderaxespad=0.2)
    ax.set_title("(a)", loc="left", fontweight="bold")


# ----------------------------------------------------------------- panel b
def _half_violin(ax, data, pos, side, color, width=0.8):
    vp = ax.violinplot(data, positions=[pos], widths=width, showextrema=False,
                       bw_method=0.15, points=200)
    body = vp["bodies"][0]
    verts = body.get_paths()[0].vertices
    if side == "left":
        verts[:, 0] = np.minimum(verts[:, 0], pos)
    else:
        verts[:, 0] = np.maximum(verts[:, 0], pos)
    body.set_facecolor(color)
    body.set_edgecolor(color)
    body.set_linewidth(0.5)
    body.set_alpha(0.75)

    q1, med, q3 = np.percentile(data, [25, 50, 75])
    bw = 0.05
    x0 = pos - 0.03 - bw if side == "left" else pos + 0.03
    ax.add_patch(plt.Rectangle((x0, q1), bw, q3 - q1, facecolor="black",
                               edgecolor="black", lw=0.4, zorder=3))
    ax.plot([x0, x0 + bw], [med, med], color="white", lw=1.0, zorder=4,
            solid_capstyle="butt")


def panel_b(ax, df):
    models = ["B1", "B3"]
    for i, mdl in enumerate(models):
        d = df[df.model == mdl]
        _half_violin(ax, d[d.split == "test_matched"].dir_idx.values, i, "left", C_MATCH)
        _half_violin(ax, d[d.split == "test_unseen"].dir_idx.values, i, "right", C_UNSEEN)

    ax.axhline(0, color="0.55", ls=":", lw=0.7, zorder=0)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_xlim(-0.6, len(models) - 0.4)
    ax.set_ylim(-1.36, 1.38)
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.set_ylabel("direction index")

    ax.text(0.015, 0.985, r"over-suppression $\uparrow$", transform=ax.transAxes,
            color=C_OVER, fontsize=6.5, ha="left", va="top")
    ax.text(0.015, 0.015, r"under-suppression $\downarrow$", transform=ax.transAxes,
            color=C_UNDER, fontsize=6.5, ha="left", va="bottom")

    ax.legend([Patch(fc=C_MATCH, alpha=0.75), Patch(fc=C_UNSEEN, alpha=0.75)],
              ["matched", "unseen"], ncol=2, loc="upper right",
              frameon=False, handlelength=1.2, borderaxespad=0.2)
    ax.set_title("(b)", loc="left", fontweight="bold")


# ----------------------------------------------------------------- report
def report(df):
    m = df[df.split == "test_matched"]
    print("matched rows with dir_idx < 0")
    for mdl, g in list(m.groupby("model")) + [("pooled", m)]:
        k, n = int((g.dir_idx < 0).sum()), len(g)
        print(f"  {mdl:7s} {k:5d} / {n:5d}  ({100 * k / n:.2f}%)")


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", type=Path, required=True)
    ap.add_argument("--out", default="fig_direction")
    a = ap.parse_args()

    df = load_eval(a.eval_dir)
    report(df)

    set_style()
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.16, 2.8),
                                   gridspec_kw={"width_ratios": [1.45, 1]})
    panel_a(axa, df)
    panel_b(axb, df)
    fig.tight_layout(pad=0.3, w_pad=1.2)
    for ext in ("pdf", "png"):
        fig.savefig(f"{a.out}.{ext}", bbox_inches="tight")
    print(f"saved {a.out}.pdf / .png")


if __name__ == "__main__":
    main()
