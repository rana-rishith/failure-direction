"""Claim 1 figure: output SI-SDR and PESQ vs input SNR, matched vs unseen.

Usage (from the repo root, faildir env):
    python plot_claim1_snr.py --eval-dir results/eval --out figs/claim1_snr

Reads every per-row eval CSV in --eval-dir (non-recursive, so eval/no_pesq/ is skipped).
Expected columns: tag, fold, split, row_idx, si_sdr_out, pesq_out.
If target_snr_db is not in the eval CSVs it is joined from the manifest by
rebuilding the folds exactly as in the Stage 2 record.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

SNRS = [-15, -10, -5, 0, 5, 10, 15, 20]
WEATHER = {"rainfall", "lightning", "hurricane"}
NAVY, ORANGE, GREY = "#1f3b73", "#e07b00", "#8a8a8a"
SPLIT_COLOR = {"test_matched": NAVY, "test_unseen": ORANGE}
ARCH_STYLE = {"b1": dict(marker="o", dx=-0.4), "b3": dict(marker="s", dx=+0.4)}


def load_eval(eval_dir: Path) -> pd.DataFrame:
    files = sorted(eval_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"no CSVs in {eval_dir}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    need = {"tag", "fold", "split", "row_idx", "si_sdr_out", "pesq_out"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"eval CSVs missing columns: {sorted(missing)}; have {list(df.columns)}")
    df["arch"] = df["tag"].str.extract(r"^(b\d)", expand=False).str.lower()
    dupes = df.duplicated(["tag", "fold", "split", "row_idx"]).sum()
    if dupes:
        raise SystemExit(f"{dupes} duplicate (tag, fold, split, row_idx) rows; check for stale CSVs in {eval_dir}")
    return df


def attach_snr(df: pd.DataFrame, manifest: Path | None) -> pd.DataFrame:
    if "target_snr_db" not in df.columns and "snr" in df.columns:
        df = df.rename(columns={"snr": "target_snr_db"})
    if "target_snr_db" in df.columns:
        return df
    if manifest is None:
        raise SystemExit("eval CSVs have no target_snr_db; pass --manifest")
    m = pd.read_csv(manifest)
    m["family"] = np.where(m.noise_type.isin(WEATHER), "weather", "anthro")
    parts = []
    for fam in ["weather", "anthro"]:
        other = "anthro" if fam == "weather" else "weather"
        for split, sp, fm in [("test_matched", "test", fam), ("test_unseen", "test", other)]:
            f = m[(m.split == sp) & (m.family == fm)].reset_index(drop=True)
            parts.append(pd.DataFrame({"fold": fam, "split": split, "row_idx": f.index,
                                       "target_snr_db": f.target_snr_db.values}))
    key = pd.concat(parts, ignore_index=True)
    out = df.merge(key, on=["fold", "split", "row_idx"], how="left", validate="many_to_one")
    if out.target_snr_db.isna().any():
        raise SystemExit("SNR join left unmatched rows; fold labels or row_idx do not match the manifest rebuild")
    return out


def stats(df, arch, split, col):
    d = df[(df.arch == arch) & (df.split == split)]
    g = d.groupby("target_snr_db")[col]
    s = pd.DataFrame({"med": g.median(), "q1": g.quantile(0.25), "q3": g.quantile(0.75), "n": g.size()})
    return s.reindex(SNRS)


def b4_floor(df, col):
    # Passthrough is fold-independent; one fold label avoids double-counting
    # whatever fold labels were written for B4.
    d = df[df.arch == "b4"]
    if d.empty:
        return None
    d = d[d.fold == d.fold.iloc[0]]
    return d.groupby("target_snr_db")[col].median().reindex(SNRS)


def panel(ax, df, col, ylabel, ref, ref_label, gap_ann):
    table = {}
    for arch, st in ARCH_STYLE.items():
        for split, c in SPLIT_COLOR.items():
            s = stats(df, arch, split, col)
            table[(arch, split)] = s
            x = np.array(SNRS) + st["dx"]
            ax.fill_between(x, s.q1, s.q3, color=c, alpha=0.12, lw=0)
            ax.plot(x, s.med, color=c, lw=1.1, marker=st["marker"], ms=3.2,
                    mfc=c, mew=0.9)
    if ref is not None:
        rx, ry = ref
        ax.plot(rx, ry, ls="--", color=GREY, lw=0.9, zorder=0)
        ax.annotate(ref_label, xy=(rx[-1], ry[-1]), xytext=(10, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=6.5, color=GREY)
    if gap_ann:
        x0 = -5 + ARCH_STYLE["b1"]["dx"] - 0.9
        hi = table[("b1", "test_matched")].med.loc[-5]
        lo = table[("b1", "test_unseen")].med.loc[-5]
        ax.annotate("", xy=(x0, hi), xytext=(x0, lo),
                    arrowprops=dict(arrowstyle="<->", lw=0.6, color="black", shrinkA=0, shrinkB=0))
        ax.text(x0 - 0.9, (hi + lo) / 2, "Claim 1 gap", rotation=90, ha="right", va="center", fontsize=6.5)
    ax.set_xticks(SNRS)
    ax.set_xlim(-18, 28)
    ax.set_xlabel("Input SNR (dB)")
    ax.set_ylabel(ylabel)
    ax.grid(True, lw=0.3, alpha=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return table


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eval-dir", type=Path, default=Path("results/eval"))
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--out", type=Path, default=Path("figs/claim1_snr"))
    a = p.parse_args()

    df = attach_snr(load_eval(a.eval_dir), a.manifest)
    df["target_snr_db"] = df.target_snr_db.astype(int)

    plt.rcParams.update({"font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 6.5,
                         "ytick.labelsize": 6.5, "font.family": "serif", "pdf.fonttype": 42,
                         "ps.fonttype": 42})
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.16, 2.8))

    ta = panel(axa, df, "si_sdr_out", "Output SI-SDR (dB)",
               ([-15, 20], [-15, 20]), "no enhancement", gap_ann=True)
    b4 = b4_floor(df, "pesq_out")
    if b4 is None:
        print("WARNING: no B4 rows found; panel (b) has no passthrough line")
    tb = panel(axb, df, "pesq_out", "Output PESQ (WB)",
               (SNRS, b4.values) if b4 is not None else None, "passthrough (B4)", gap_ann=False)
    axa.set_title("(a)", loc="left", fontsize=8, fontweight="bold")
    axb.set_title("(b)", loc="left", fontsize=8, fontweight="bold")

    handles = [
        Line2D([], [], color=NAVY, lw=1.1, label="matched"),
        Line2D([], [], color=ORANGE, lw=1.1, label="unseen"),
        Line2D([], [], color="black", lw=0, marker="o", ms=3.5, label="B1"),
        Line2D([], [], color="black", lw=0, marker="s", ms=3.5, label="B3"),
        Line2D([], [], color=GREY, lw=0.9, ls="--", label="no enhancement"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=7,
               bbox_to_anchor=(0.5, 0.0), handlelength=1.8, columnspacing=1.4)
    fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=1.5)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out.with_suffix(".pdf"))
    fig.savefig(a.out.with_suffix(".png"), dpi=300)
    print(f"saved {a.out.with_suffix('.pdf')} and .png\n")

    # ---- table of plotted medians ----
    pd.set_option("display.width", 200)
    for name, t, col in [("SI-SDR out (dB)", ta, "si_sdr_out"), ("PESQ out", tb, "pesq_out")]:
        cols = {f"{arch.upper()} {split.split('_')[1]}": s.med for (arch, split), s in t.items()}
        if col == "pesq_out" and b4 is not None:
            cols["B4"] = b4
        tab = pd.DataFrame(cols)
        tab.index.name = "SNR"
        n = {f"{arch.upper()} {split.split('_')[1]}": s.n for (arch, split), s in t.items()}
        print(f"Medians plotted, {name}:")
        print(tab.round(3).to_string())
        print("n per cell:", {k: sorted(set(v.dropna().astype(int))) for k, v in n.items()}, "\n")

    # Stage 2 record section 7 reports MEANS pooled over B1+B3 and both folds.
    # Reproduce that exactly so the numbers can be checked line by line.
    t = (df[df.arch.isin(["b1", "b3"])]
         .groupby(["target_snr_db", "split"]).si_sdr_out.mean().unstack())
    t["unseen - SNR"] = t["test_unseen"] - t.index
    print("Check vs Stage 2 record sec. 7 (MEAN si_sdr_out, B1+B3 pooled, both folds):")
    print(t.round(3).to_string())


if __name__ == "__main__":
    main()
