"""Two paper figures from committed CSVs. Run from the repo root:
    python paper/figs_src/fig_universal.py
fig_ladder: median d_g per rung (R1, R2, R4) by SNR for b1, b3, cm, dfn3, sgmse (U1 and U2 cells).
fig_u3_ceiling: U3 mean within-cell rho per arm against the label-reliability ceiling.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})
U = "results/universal/"
OUT = "paper/figs/"

cells = pd.concat([pd.read_csv(U + "u1_cells.csv"), pd.read_csv(U + "u2_cells.csv")])
cells = cells[cells.fold == "all"].drop_duplicates(["arch", "snr"])
names = {"b1": "B1", "b3": "B3", "cm": "CM", "dfn3": "DFN3 (half-A)",
         "sgmse": "SB (half-A)"}
cols = {"R1": "#1f3a6e", "R2": "#c77d14", "R4": "#7a7a7a"}
labs = {"R1": "R1 heard samples", "R2": "R2 unheard segment", "R4": "R4 unseen type"}
fig, axs = plt.subplots(1, 5, figsize=(7.16, 2.15), sharey=True)
for ax, a in zip(axs, names):
    g = cells[cells.arch == a].sort_values("snr")
    for r in ("R1", "R2", "R4"):
        ax.plot(g.snr, g[f"median_d_{r}"], marker="o", ms=3, lw=1.2, color=cols[r], label=labs[r])
    ax.axhline(0, color="0.6", lw=0.6, ls=":")
    ax.set_title(names[a], fontsize=8)
    ax.set_xticks([-15, -10, -5, 0])
    ax.set_xlabel("input SNR (dB)")
    ax.set_ylim(-1.05, 0.5)
axs[0].set_ylabel(r"median $d_g$")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, fontsize=7, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 0.0))
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.savefig(OUT + "fig_ladder.pdf"); fig.savefig(OUT + "fig_ladder.png", dpi=200)

v = pd.read_json(U + "u3_verdict.json", typ="series")
pc = v["notes"]["per_corpus"]
rel = pd.read_csv(U + "u3_label_reliability.csv").groupby(["corpus", "kind"]).mean_rho.mean()
corp = [("marven", "MarVEN"), ("demand", "DEMAND"), ("fsd50k", "FSD50K")]
arms = [("feats_only_lgbm", "feats-only", "#1f3a6e"), ("ridge_33", "ridge, 33 feat.", "#5b8fd1"),
        ("baseline_snr_logE", "SNR + log E", "#c77d14"), ("wada_snr", "WADA-SNR", "#b5b5b5")]
fig, ax = plt.subplots(figsize=(3.5, 2.5))
w = 0.18
for i, (c, cn) in enumerate(corp):
    for j, (k, an, col) in enumerate(arms):
        ax.bar(i + (j - 1.5) * w, pc[c]["mean_rho"][k], w, color=col, label=an if i == 0 else None)
    for kind, ls, ln in (("seed", "-", "reseeded replicas"), ("arch", "--", "across architectures")):
        ax.hlines(rel[(c, kind)], i - 2.2 * w, i + 2.2 * w, colors="k", linestyles=ls, lw=1,
                  label=ln if i == 0 else None)
ax.axhline(0, color="0.4", lw=0.6)
ax.set_xticks(range(3)); ax.set_xticklabels([n for _, n in corp])
ax.set_ylabel(r"mean within-cell Spearman $\rho$")
ax.set_ylim(-0.25, 1.0)
ax.legend(frameon=False, fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
fig.savefig(OUT + "fig_u3_ceiling.pdf"); fig.savefig(OUT + "fig_u3_ceiling.png", dpi=200)
print("ok")
