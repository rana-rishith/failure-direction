#!/usr/bin/env python
"""Paper figures built from committed result tables (no GPU, no audio).

    python scripts/paper_figs.py                     # all four
    python scripts/paper_figs.py chain diversity     # a subset
    python scripts/paper_figs.py --out-dir paper/figs

Each figure is written as <out-dir>/<name>.svg and .pdf (the .pdf is what
LaTeX includes). Every number is read from results/, and each figure prints
the values it plots so they can be checked against the text.

  pipeline   Fig. 1. Where the clean reference is used (training only) and
             what the predictor sees at inference (noisy input only).
  chain      Claim 3 chain. Mean d_rho (feats_only minus baseline) per model
             and noise type for C3_active, C3b held-out and C3c held-out.
  diversity  nr_g and d_g on MarVEN at SNR <= 0 (level-aligned basis) by
             training noise and architecture.
  features   C3c weather-fold feature importance (full arm, share of LightGBM splits),
             burst features and the oracle SNR feature marked.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

WEATHER = ["rainfall", "lightning", "hurricane"]
ANTHRO = ["large_commercial_ship", "bubble_curtain"]
NOISE_LABEL = {"rainfall": "rainfall", "lightning": "lightning", "hurricane": "hurricane",
               "bubble_curtain": "bubble curtain", "large_commercial_ship": "commercial ship"}
ARCH_LABEL = {"b1": "B1", "b3": "B3", "cm": "CM"}
INK, MUTED, GRID = "#1F2328", "#6B7280", "#E5E7EB"


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
        "text.color": INK, "axes.labelcolor": INK,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "path",
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })


def save(fig, out_dir, name):
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("svg", "pdf"):
        fig.savefig(out_dir / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"wrote {out_dir / name}.svg and .pdf\n")


def panel_letter(ax, letter):
    ax.annotate(f"({letter})", xy=(0, 1), xycoords="axes fraction", xytext=(-4, 4),
                textcoords="offset points", ha="right", va="bottom",
                fontsize=9, fontweight="bold", annotation_clip=False)


def verdict(report_md):
    for line in Path(report_md).read_text(encoding="utf-8").splitlines():
        if line.startswith("## Verdict:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"no '## Verdict:' line in {report_md}")


def tag_order(tags):
    def key(t):
        if t == "dfn3":
            return (9, 0)
        arch, _, rest = t.partition("_fsd")
        seed = int(rest[2:]) if rest.startswith("_s") else 1
        return ("b1", "b3", "cm").index(arch), seed
    return sorted(tags, key=key)


def tag_label(t):
    if t == "dfn3":
        return "DFN3"
    arch, _, rest = t.partition("_fsd")
    seed = rest[2:] if rest.startswith("_s") else "1"
    return f"{ARCH_LABEL[arch]}·{seed}"


# ---------------------------------------------------------------- pipeline
def fig_pipeline(out_dir):
    fig, ax = plt.subplots(figsize=(7.16, 2.35))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    band = dict(boxstyle="round,pad=0,rounding_size=0.015", linewidth=0)
    ax.add_patch(FancyBboxPatch((0.185, 0.53), 0.635, 0.45, facecolor="#F3F4F6", **band))
    ax.add_patch(FancyBboxPatch((0.185, 0.02), 0.635, 0.45, facecolor="#EEF4FB", **band))
    ax.text(0.195, 0.955, "Training only: needs the clean reference $s$", ha="left", va="top",
            fontsize=7, style="italic", color=MUTED)
    ax.text(0.195, 0.445, "Inference: noisy input only, before enhancement runs",
            ha="left", va="top", fontsize=7, style="italic", color=MUTED)

    def box(xc, yc, w, h, text, fc="white", ec=INK, bold=False):
        ax.add_patch(FancyBboxPatch((xc - w / 2, yc - h / 2), w, h,
                                    boxstyle="round,pad=0,rounding_size=0.012",
                                    facecolor=fc, edgecolor=ec, linewidth=0.7))
        ax.text(xc, yc, text, ha="center", va="center", fontsize=7,
                fontweight="bold" if bold else "normal", linespacing=1.25)

    def arrow(p, q, dashed=False, rad=0.0, label=None, lpos=0.5, loff=(0, 0)):
        ax.annotate("", xy=q, xytext=p,
                    arrowprops=dict(arrowstyle="-|>", lw=0.7, color=INK, shrinkA=0, shrinkB=0,
                                    mutation_scale=7, linestyle=(0, (3, 2)) if dashed else "-",
                                    connectionstyle=f"arc3,rad={rad}"))
        if label:
            x = p[0] + lpos * (q[0] - p[0]) + loff[0]
            y = p[1] + lpos * (q[1] - p[1]) + loff[1]
            ax.text(x, y, label, fontsize=6.5, color=MUTED, ha="center", va="center",
                    style="italic")

    W, H = 0.165, 0.25
    yt, yb = 0.70, 0.20
    x1, x2, x3, xv = 0.30, 0.50, 0.70, 0.91

    box(0.085, 0.45, 0.16, 0.30, "Noisy input\n$y = s + n$\nSNR $-15$ to $20$ dB")

    box(x1, yt, W, H, "Enhancer $f$\nB1, B3, CM\n(FSD50K-trained)")
    box(x2, yt, W, H, "Energy split of $\\hat{s}$\nagainst clean $s$\n$e_\\mathrm{over},\\; e_\\mathrm{under}$")
    box(x3, yt, W, H, "Label\n$r_\\mathrm{over} = e_\\mathrm{over} / e_\\mathrm{clean}$")

    box(x1, yb, W, H, "45 reference-free\ninput features\n(33 base + 12 burst)", fc="#FFFFFF")
    box(x2, yb, W, H, "LightGBM regressor\n(feats_only arm)")
    box(x3, yb, W, H, "Predicted $r_\\mathrm{over}$\nper utterance")

    box(xv, 0.45, 0.17, 0.46,
        "Verdict\nSpearman $\\rho$ within\nSNR and type×SNR\ncells, against\noracle SNR\n+ $\\log e_\\mathrm{noisy}$",
        fc="#FFF7E6", ec="#B7791F")

    arrow((0.16, 0.52), (x1 - W / 2, yt))
    arrow((0.16, 0.38), (x1 - W / 2, yb))
    arrow((x1 + W / 2, yt), (x2 - W / 2, yt), label="$\\hat{s}$", loff=(0, 0.04))
    arrow((x2 + W / 2, yt), (x3 - W / 2, yt))
    arrow((x1 + W / 2, yb), (x2 - W / 2, yb))
    arrow((x2 + W / 2, yb), (x3 - W / 2, yb))
    arrow((x3, yt - H / 2), (x2 + 0.03, yb + H / 2), dashed=True,
          label="training target", lpos=0.42, loff=(0.06, 0.0))
    arrow((x3 + W / 2, yt), (xv - 0.085, 0.58))
    arrow((x3 + W / 2, yb), (xv - 0.085, 0.32))

    print("pipeline: schematic, no data")
    save(fig, out_dir, "fig_pipeline")


# ---------------------------------------------------------------- chain
CHAIN = [
    ("C3_active", RES / "claim3_active", "33 features; seeds 1–3, DFN3"),
    ("C3b", RES / "claim3b" / "heldout", "45 features; held-out seeds 4–5"),
    ("C3c", RES / "claim3c" / "heldout", "weather verdict; held-out seeds 6–7; hatched: descriptive"),
]


def fig_chain(out_dir):
    rows = WEATHER + ANTHRO
    blocks = []
    for name, d, desc in CHAIN:
        pt = pd.read_csv(d / "per_type.csv")
        tags = tag_order(pt.tag.unique())
        m = pt.pivot_table(index="noise_type", columns="tag", values="mean_d_rho")
        w = pt.pivot_table(index="noise_type", columns="tag", values="won")
        c = pt.pivot_table(index="noise_type", columns="tag", values="cells")
        blocks.append(dict(name=name, desc=desc, verdict=verdict(d / "report.md"),
                           tags=tags, m=m.loc[rows, tags], won=w.loc[rows, tags],
                           cells=c.loc[rows, tags]))
        print(f"{name} ({verdict(d / 'report.md')}): mean d_rho per noise type x model")
        print(m.loc[rows, tags].round(3).to_string(), "\n")

    fig = plt.figure(figsize=(7.16, 2.45))
    gs = fig.add_gridspec(1, len(blocks) + 1,
                          width_ratios=[len(b["tags"]) for b in blocks] + [0.35], wspace=0.06)
    norm = mpl.colors.TwoSlopeNorm(vmin=-0.5, vcenter=0.0, vmax=0.5)
    cmap = mpl.colormaps["RdBu"]
    for i, b in enumerate(blocks):
        ax = fig.add_subplot(gs[0, i])
        im = ax.imshow(b["m"].values, cmap=cmap, norm=norm, aspect="auto")
        for r in range(len(rows)):
            for k in range(len(b["tags"])):
                v = b["m"].values[r, k]
                won, cells = int(b["won"].values[r, k]), int(b["cells"].values[r, k])
                col = "white" if abs(v) > 0.33 else INK
                ax.text(k, r - 0.12, f"{v:+.2f}".replace("+", ""), ha="center", va="center",
                        fontsize=5.6, color=col)
                ax.text(k, r + 0.27, f"{won}/{cells}", ha="center", va="center",
                        fontsize=4.6, color=col, alpha=0.85)
        ax.axhline(len(WEATHER) - 0.5, color=INK, lw=0.8)
        ax.set_xticks(range(len(b["tags"])), [tag_label(t) for t in b["tags"]], rotation=90)
        ax.set_yticks(range(len(rows)), [NOISE_LABEL[r] for r in rows] if i == 0 else [])
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        colour = "#1F7A3A" if b["verdict"] == "HOLDS" else "#B83232"
        ax.set_title(f"{b['name']}: {b['verdict']}", fontsize=7.5, loc="left", pad=11,
                     fontweight="bold", color=colour)
        ax.text(0, 1.015, b["desc"], transform=ax.transAxes, fontsize=6, color=MUTED,
                ha="left", va="bottom")
        if b["name"] == "C3c":
            ax.add_patch(Rectangle((-0.5, len(WEATHER) - 0.5), len(b["tags"]), len(ANTHRO),
                                   fill=False, hatch="////", lw=0, edgecolor="#9CA3AF", alpha=0.6))
    cax = fig.add_subplot(gs[0, -1])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(r"mean $\Delta\rho$ (feats_only $-$ baseline)", fontsize=6.5)
    cb.ax.tick_params(labelsize=6, length=2)
    cb.outline.set_linewidth(0.4)
    fig.text(0.0, -0.06, "Weather rows above the line, anthropogenic below. "
             "Cell: mean $\\Delta\\rho$ over 8 SNR cells; small text: SNR cells won.",
             fontsize=6, color=MUTED, ha="left")
    save(fig, out_dir, "fig_claim3_chain")


# ---------------------------------------------------------------- diversity
GROUPS = [
    ("heard", "MarVEN, own family\n(heard noise)", "#C7CCD3"),
    ("family", "MarVEN, other family", "#5B3A8C"),
    ("demand", "DEMAND", "#C98A2B"),
    ("fsd", "FSD50K", "#1F7A3A"),
]


def diversity_table():
    fam = pd.read_csv(RES / "diverse" / "summary_low_snr_levelaligned.csv")
    fam = fam[fam.tag.str.contains("_weather|_anthro")].copy()
    fam["arch"] = fam.tag.str.split("_").str[0]
    fam["group"] = fam.cond.map({"marven_m": "heard", "marven_u": "family"})
    fam = fam.dropna(subset=["group"]).rename(columns={"d": "d_g", "noise_removed": "nr_g"})
    xs = pd.read_csv(RES / "xcorpus" / "report2" / "D_per_seed.csv")
    xs = xs.rename(columns={"family": "group"})
    cols = ["group", "arch", "tag", "d_g", "nr_g"]
    return pd.concat([fam[cols], xs[cols]], ignore_index=True)


def fig_diversity(out_dir):
    df = diversity_table()
    summ = df.groupby(["group", "arch"])[["nr_g", "d_g"]].agg(["median", "min", "max", "count"])
    print("MarVEN SNR <= 0, level-aligned (heard/family: seed 1234, two folds; demand/fsd: 3 seeds)")
    print(summ.round(3).to_string(), "\n")

    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.3), gridspec_kw={"wspace": 0.28})
    archs = ["b1", "b3", "cm"]
    bw = 0.19
    for ax, col, ylab, letter in [(axes[0], "nr_g", r"noise removed, $\mathrm{nr}_g$", "a"),
                                  (axes[1], "d_g", r"direction, $d_g$  (+ over, $-$ under)", "b")]:
        for gi, (g, _, colr) in enumerate(GROUPS):
            for ai, a in enumerate(archs):
                v = df[(df.group == g) & (df.arch == a)][col].values
                x = ai + (gi - 1.5) * (bw + 0.02)
                ax.bar(x, np.median(v), width=bw, color=colr, edgecolor="none",
                       alpha=0.55 if g == "heard" else 0.9)
                jit = np.linspace(-bw * 0.25, bw * 0.25, len(v)) if len(v) > 1 else [0]
                ax.scatter(x + np.asarray(jit), v, s=7, color="white", edgecolor=INK,
                           linewidth=0.5, zorder=3)
        ax.set_xticks(range(3), [ARCH_LABEL[a] for a in archs])
        ax.set_ylabel(ylab)
        ax.axhline(0, color=INK, lw=0.6)
        ax.yaxis.grid(True, color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)
        panel_letter(ax, letter)
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_ylim(-1.05, 0.65)
    handles = [Patch(facecolor=c, alpha=0.55 if g == "heard" else 0.9, label=lab)
               for g, lab, c in GROUPS]
    handles.append(Line2D([], [], marker="o", ls="", markersize=3.5, markerfacecolor="white",
                          markeredgecolor=INK, markeredgewidth=0.5, label="one model"))
    fig.legend(handles=handles, loc="upper center", ncol=5, frameon=False,
               bbox_to_anchor=(0.5, 0.0), title="Training noise, scored on MarVEN at SNR ≤ 0 dB",
               title_fontsize=6.5)
    save(fig, out_dir, "fig_diversity")


# ---------------------------------------------------------------- features
def fig_features(out_dir, top=14):
    shares = {}
    for d in sorted((RES / "claim3c" / "heldout").glob("*_fsd_s*")):
        imp = pd.read_csv(d / "metrics" / "claim3_weather_importance.csv")
        shares[d.name] = imp.set_index("feature").gain / imp.gain.sum()
    sh = pd.DataFrame(shares).fillna(0.0)
    order = sh.mean(axis=1).sort_values(ascending=False).index[:top]
    sh = sh.loc[order]
    print(f"C3c weather fold, full-arm split share (top {top}), per model")
    print((sh * 100).round(1).to_string(), "\n")

    def colour(f):
        if f == "snr":
            return "#9CA3AF"
        return "#B7791F" if f.startswith("bst_") else "#3B5B8C"

    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    y = np.arange(len(order))[::-1]
    for yi, f in zip(y, order):
        v = sh.loc[f].values * 100
        ax.barh(yi, v.mean(), height=0.65, color=colour(f),
                hatch="////" if f == "snr" else None, edgecolor="white" if f == "snr" else "none",
                linewidth=0)
        ax.scatter(v, np.full_like(v, yi) + np.linspace(-0.18, 0.18, len(v)), s=4,
                   color="white", edgecolor=INK, linewidth=0.4, zorder=3)
    ax.set_yticks(y, list(order), fontsize=6.5, family="monospace")
    ax.set_xlabel("share of tree splits (%)")
    ax.xaxis.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    handles = [Patch(facecolor="#B7791F", label="burst feature"),
               Patch(facecolor="#3B5B8C", label="base feature"),
               Patch(facecolor="#9CA3AF", hatch="////", edgecolor="white",
                     label="oracle SNR (full arm only)")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.42, -0.15), ncol=3,
              frameon=False, handlelength=1.4, columnspacing=1.0)
    ax.set_title("C3c held-out models, weather fold, full arm (6 models)", fontsize=7, loc="left",
                 color=MUTED)
    save(fig, out_dir, "fig_features")


FIGS = {"pipeline": fig_pipeline, "chain": fig_chain, "diversity": fig_diversity,
        "features": fig_features}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("figs", nargs="*", help=f"any of {', '.join(FIGS)}; default: all")
    ap.add_argument("--out-dir", type=Path, default=REPO / "paper" / "figs")
    a = ap.parse_args()
    bad = [f for f in a.figs if f not in FIGS]
    if bad:
        ap.error(f"unknown figure(s): {', '.join(bad)}")
    set_style()
    for name in a.figs or FIGS:
        FIGS[name](a.out_dir)


if __name__ == "__main__":
    main()
