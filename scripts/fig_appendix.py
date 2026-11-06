#!/usr/bin/env python
"""
fig_appendix.py  -  appendix figures A1-A4 for the failure-direction paper.

  a1  WER downstream, one panel per noise type        needs --wer-csv
  a2  B1 vs B3 r_over rank agreement (test_unseen)    needs --eval-dir
  a3  training reproduction, RTX 3060 vs RTX 4060     needs --logs-3060 + --logs-4060, or --curves-csv
  a4  B3 +20 dB r_over ECDF, <60 Hz bins in vs out  needs --eval-dir

Examples (PowerShell, from the repo root):
  python fig_appendix.py a2 a4 --eval-dir .\\results\\eval
  python fig_appendix.py a3 --curves-csv .\\results\\metrics\\training_curves.csv
  python fig_appendix.py a1 --wer-csv .\\results\\wer_snrmax-5.csv

Each figure is written to <out-dir>/<name>.pdf (vector, fonts embedded) and a
600-dpi .png. All numbers are read from files. Each figure prints the values it
plots so they can be checked against the stage records.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from scipy.stats import spearmanr

# ---------------------------------------------------------------- style ----
NAVY, ORANGE, GREY = "#1E3A8A", "#D9661F", "#6B7280"
RED, PURPLE, GREEN, GRID = "#B83232", "#5B3A8C", "#1F7A3A", "#E5E7EB"
SNRS = [-15, -10, -5, 0, 5, 10, 15, 20]
NOISES = ["rainfall", "lightning", "hurricane", "bubble_curtain", "large_commercial_ship"]
NOISE_LABEL = {"rainfall": "rainfall", "lightning": "lightning", "hurricane": "hurricane",
               "bubble_curtain": "bubble curtain", "large_commercial_ship": "commercial ship"}
TAGS = ["b1_weather", "b1_anthro", "b3_weather", "b3_anthro"]
MK = dict(markersize=5, markeredgecolor="white", markeredgewidth=0.6)
R_OVER = r"$r_\mathrm{over}$"


def set_style():
    fonts = {f.name for f in mpl.font_manager.fontManager.ttflist}
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": (["Inter"] if "Inter" in fonts else []) + ["DejaVu Sans"],
        "font.size": 9, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "lines.linewidth": 1.8,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def panel(ax, letter, name=None):
    """Bold (a) at top-left outside the axes, optional plain identifier after it."""
    ax.annotate(f"({letter})", xy=(0, 1), xycoords="axes fraction", xytext=(-2, 5),
                textcoords="offset points", ha="right", va="bottom",
                fontsize=11, fontweight="bold", annotation_clip=False)
    if name:
        ax.annotate(name, xy=(0, 1), xycoords="axes fraction", xytext=(2, 5),
                    textcoords="offset points", ha="left", va="bottom",
                    fontsize=9, annotation_clip=False)


def save(fig, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=600)
    plt.close(fig)
    print(f"wrote {out}.pdf and {out}.png\n")


# --------------------------------------------------------------- loaders ---
def load_eval(eval_dir):
    """src.evaluate writes <tag>__<fold>__<split>.csv. Identity comes from the filename."""
    d = Path(eval_dir)
    files = [f for f in d.rglob("*.csv") if "no_pesq" not in f.parts]
    parts = []
    for f in files:
        bits = f.stem.split("__")
        if len(bits) != 3:
            continue
        x = pd.read_csv(f)
        x["model"], x["fold"], x["split"] = bits[0].upper(), bits[1], bits[2]
        parts.append(x)
    if not parts:
        sys.exit(f"no <tag>__<fold>__<split>.csv files under {d}")
    df = pd.concat(parts, ignore_index=True)
    if "target_snr_db" not in df.columns and "snr" in df.columns:
        df["target_snr_db"] = df["snr"]
    need = {"row_idx", "noise_type", "target_snr_db", "e_over", "e_clean"}
    if need - set(df.columns):
        sys.exit(f"eval CSVs missing columns {sorted(need - set(df.columns))}")
    key = ["model", "fold", "split", "row_idx"]
    assert not df.duplicated(key).any(), "duplicate rows: stale CSVs somewhere under eval dir?"
    df["target_snr_db"] = df["target_snr_db"].round().astype(int)
    df["r_over"] = df["e_over"] / df["e_clean"]
    print("eval rows per model/split:\n" + df.groupby(["model", "split"]).size().to_string() + "\n")
    return df


# ------------------------------------------------------------------ A1 -----
ARMS = ["clean", "noisy", "b1_matched", "b1_unseen"]
ARM_ALIAS = {"passthrough": "noisy", "b4": "noisy", "noisy_passthrough": "noisy",
             "matched": "b1_matched", "unseen": "b1_unseen"}


def load_wer(path):
    """
    Accepts either
      long: one row per (utterance, arm) with columns arm, noise_type, target_snr_db,
            n_ref and err (or sub/del/ins, or a per-row wer)
      wide: one row per utterance with noise_type, target_snr_db, n_ref and
            <arm>_err (or <arm>_sub/_del/_ins) for arm in clean, noisy, b1_matched, b1_unseen
    WER is corpus-level: sum(edits) / sum(reference words).
    """
    w = pd.read_csv(path)
    if "row_key" in w.columns:                       # src.wer appends repeat headers on resume
        w = w[w["row_key"] != "row_key"]
    if "target_snr_db" not in w.columns and "snr" in w.columns:
        w["target_snr_db"] = w["snr"]
    # src.wer writes err_<arm>, S_<arm>, D_<arm>, I_<arm>; normalise to <arm>_err etc.
    ren = {}
    for c in w.columns:
        m_ = re.match(r"^(err|S|D|I)_(clean|noisy|b1_matched|b1_unseen)$", c)
        if m_:
            k = {"err": "err", "S": "sub", "D": "del", "I": "ins"}[m_.group(1)]
            ren[c] = f"{m_.group(2)}_{k}"
    w = w.rename(columns=ren)
    for c in w.columns:
        if c not in ("row_key", "key", "noise_type", "family", "arm"):
            w[c] = pd.to_numeric(w[c], errors="coerce")
    cols = set(w.columns)
    base = ["noise_type", "target_snr_db", "n_ref"]
    if "arm" not in cols:
        pat = re.compile(r"^(clean|noisy|b1_matched|b1_unseen)_(err|sub|del|ins)$")
        hits = [c for c in w.columns if pat.match(c)]
        if not hits:
            sys.exit(f"WER CSV: no 'arm' column and no <arm>_err columns. Found: {sorted(cols)}")
        long = []
        for arm in ARMS:
            sub = w[base].copy()
            sub["arm"] = arm
            for k in ("err", "sub", "del", "ins"):
                if f"{arm}_{k}" in cols:
                    sub[k] = w[f"{arm}_{k}"]
            long.append(sub)
        w = pd.concat(long, ignore_index=True)
        cols = set(w.columns)
    w["arm"] = w["arm"].str.lower().replace(ARM_ALIAS)
    missing = set(base) - cols
    if missing:
        sys.exit(f"WER CSV missing {sorted(missing)}. Found: {sorted(cols)}")
    if "err" not in cols:
        if {"sub", "del", "ins"} <= cols:
            w["err"] = w["sub"] + w["del"] + w["ins"]
        elif "wer" in cols:
            w["err"] = w["wer"] * w["n_ref"]   # per-row WER weighted back to edit counts
        else:
            sys.exit("WER CSV needs err, sub/del/ins, or wer")
    w["target_snr_db"] = w["target_snr_db"].round().astype(int)
    return w


def fig_a1(wer_csv, out):
    w = load_wer(wer_csv)
    g = (w.groupby(["arm", "noise_type", "target_snr_db"])[["err", "n_ref"]].sum())
    g["wer"] = 100 * g["err"] / g["n_ref"]
    tab = g["wer"].unstack("arm").reindex(columns=[a for a in ARMS if a in g.index.get_level_values(0)])
    print("A1  corpus WER (%) by noise type x SNR")
    print(tab.round(2).to_string() + "\n")
    pooled = w.groupby("arm")[["err", "n_ref"]].sum()
    print("pooled corpus WER (%):\n" + (100 * pooled.err / pooled.n_ref).round(2).to_string() + "\n")

    spec = {
        "clean":      dict(color=GREY, ls=":", marker=None, label="clean audio (ASR floor)"),
        "noisy":      dict(color=GREY, ls="--", marker=None, label="noisy passthrough"),
        "b1_matched": dict(color=NAVY, ls="-", marker="o", label="B1 enhanced, matched"),
        "b1_unseen":  dict(color=ORANGE, ls="-", marker="o", label="B1 enhanced, unseen"),
    }
    snrs = sorted(w["target_snr_db"].unique())
    fig, axs = plt.subplots(1, 5, figsize=(7.16, 2.6), sharey=True, layout="constrained")
    for i, (ax, nt) in enumerate(zip(axs, NOISES)):
        for arm in ARMS:
            if arm not in tab.columns:
                continue
            try:
                s = tab.xs(nt, level="noise_type")[arm].dropna()
            except KeyError:
                continue
            st = spec[arm]
            kw = MK if st["marker"] else {}
            ax.plot(s.index, s.values, color=st["color"], ls=st["ls"],
                    marker=st["marker"], lw=1.8 if st["marker"] else 1.4, **kw)
        ax.set_xticks(snrs)
        ax.set_xticklabels([f"{s:+d}".replace("-", "\u2212") if s else "0" for s in snrs],
                           rotation=90 if len(snrs) > 4 else 0)
        ax.set_xlabel("SNR (dB)")
        ax.set_ylim(bottom=0)
        panel(ax, "abcde"[i], NOISE_LABEL[nt])
    axs[0].set_ylabel("WER (%)")
    handles = [Line2D([], [], color=s["color"], ls=s["ls"], marker=s["marker"],
                      lw=1.8 if s["marker"] else 1.4, **(MK if s["marker"] else {}),
                      label=s["label"]) for a, s in spec.items() if a in tab.columns]
    fig.legend(handles=handles, loc="outside lower center", ncol=len(handles), frameon=False)
    print("caption note: WER is corpus-level (total S+D+I over total reference words), scored "
          "against LibriSpeech train-clean-100 ground-truth transcripts, with Whisper's "
          "EnglishTextNormalizer applied to both hypothesis and reference. ASR: faster-whisper "
          "large-v3, int8_float16, greedy, temperature 0, condition_on_previous_text=False; all "
          "audio peak-normalised before transcription.  <- confirm this matches the run that "
          "produced the CSV.\n")
    save(fig, out)


# ------------------------------------------------------------------ A2 -----
RANGES = [("\u221215 to \u22125", [-15, -10, -5]), ("0 to +10", [0, 5, 10]), ("+15 to +20", [15, 20])]


def fig_a2(df, out):
    u = df[(df["split"] == "test_unseen") & df["model"].isin(["B1", "B3"])]
    cols = ["fold", "row_idx", "target_snr_db", "noise_type", "r_over"]
    m = u[u.model == "B1"][cols].merge(u[u.model == "B3"][cols], on=["fold", "row_idx"],
                                       suffixes=("_1", "_3"), validate="one_to_one")
    assert len(m) == (u.model == "B1").sum() == (u.model == "B3").sum(), "B1/B3 rows do not pair"
    assert (m.target_snr_db_1 == m.target_snr_db_3).all(), "SNR mismatch between paired rows"
    assert (m.noise_type_1 == m.noise_type_3).all(), "noise mismatch between paired rows"
    m["snr"] = m["target_snr_db_1"]

    # rank within SNR level, so agreement is not inflated by the SNR sweep itself
    g = m.groupby("snr")
    m["x"] = g["r_over_1"].rank(pct=True)
    m["y"] = g["r_over_3"].rank(pct=True)
    m["t1"] = m["x"] > 0.9
    m["t3"] = m["y"] > 0.9

    def stats(sub):
        rho = spearmanr(sub["x"], sub["y"]).statistic
        hit = (sub.t1 & sub.t3).sum() / max(sub.t1.sum(), 1)
        return rho, hit / sub.t3.mean()

    print(f"A2  paired test_unseen utterances: {len(m)}")
    print(f"{'SNR':>5} {'n':>5} {'rho':>6} {'top10/chance':>13}")
    for s, sub in m.groupby("snr"):
        rho, ov = stats(sub)
        print(f"{s:>+5d} {len(sub):>5d} {rho:>6.3f} {ov:>12.1f}x")
    rng = []
    for name, lv in RANGES:
        sub = m[m.snr.isin(lv)]
        if len(sub):
            rng.append((name, *stats(sub)))
    print("by range:")
    for name, rho, ov in rng:
        print(f"  {name:>12} dB  rho {rho:.3f}  top-10% overlap {ov:.1f}x chance")
    print()

    cmap = LinearSegmentedColormap.from_list("navy_seq", ["#C9D4EF", NAVY])
    bounds = np.array(SNRS + [25]) - 2.5
    norm = BoundaryNorm(bounds, cmap.N)
    fig, ax = plt.subplots(figsize=(3.5, 3.5), layout="constrained")
    p = m.sample(frac=1, random_state=0)   # shuffle draw order so no SNR overpaints another
    sc = ax.scatter(p["x"], p["y"], c=p["snr"], cmap=cmap, norm=norm,
                    s=4, alpha=0.4, linewidths=0, rasterized=True)
    ax.plot([0, 1], [0, 1], color=GREY, lw=1.0, zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_xlabel(f"B1 {R_OVER} rank (within SNR)")
    ax.set_ylabel(f"B3 {R_OVER} rank (within SNR)")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02, ticks=SNRS)
    cb.solids.set_alpha(1)
    cb.set_label("SNR (dB)")
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)

    lines = [f"{'SNR (dB)':<11}{'ρ':>5}{'top-10%':>9}"] + \
            [f"{n:<11}{r:>5.2f}{o:>8.1f}×" for n, r, o in rng]
    ax.text(0.98, 0.03, "\n".join(lines), transform=ax.transAxes, ha="right", va="bottom",
            family="DejaVu Sans Mono", fontsize=6.5, linespacing=1.3,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRID, alpha=0.92))
    save(fig, out)


# ------------------------------------------------------------------ A3 -----
LOG_LINE = re.compile(r"(\d+)\s*/\s*\d+\D*?val\w*\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.I)


def parse_logs(d):
    """Reads lines like '[b1_weather] 2000/20000 val -12.884 3.4m' from *.log / *.txt."""
    out = {}
    for f in sorted(Path(d).rglob("*")):
        if f.suffix.lower() not in {".log", ".txt"}:
            continue
        tag = next((t for t in TAGS if t in f.name.lower()), None)
        if tag is None:
            continue
        pts = {}
        for line in f.read_text(errors="ignore").splitlines():
            hit = LOG_LINE.search(line)
            if hit:
                pts[int(hit.group(1))] = float(hit.group(2))
        if pts:
            out.setdefault(tag, {}).update(pts)
    curves = {}
    for tag, pts in out.items():
        s = pd.Series(pts).sort_index()
        curves[tag] = -s if s.median() < 0 else s   # logged as SI-SDR loss -> dB
    return curves


def load_curves(a):
    if a.curves_csv:
        c = pd.read_csv(a.curves_csv)   # tag, gpu, step, val_sisdr_db
        c["gpu"] = c["gpu"].astype(str).str.extract(r"(3060|4060)")[0]
        res = {}
        for (tag, gpu), sub in c.groupby(["tag", "gpu"]):
            s = sub.set_index("step")["val_sisdr_db"].sort_index()
            res[(tag, gpu)] = -s if s.median() < 0 else s
        return res
    if not (a.logs_3060 and a.logs_4060):
        sys.exit("a3 needs --logs-3060 and --logs-4060, or --curves-csv")
    res = {}
    for gpu, d in (("3060", a.logs_3060), ("4060", a.logs_4060)):
        for tag, s in parse_logs(d).items():
            res[(tag, gpu)] = s
    return res


def fig_a3(a, out):
    cur = load_curves(a)
    fig, axs = plt.subplots(1, 4, figsize=(7.16, 2.4), sharey=True, layout="constrained")
    print("A3  validation SI-SDR (dB)")
    for i, (ax, tag) in enumerate(zip(axs, TAGS)):
        s0, s1 = cur.get((tag, "3060")), cur.get((tag, "4060"))
        for s, c, mk, lab in ((s0, GREY, "o", "RTX 3060"), (s1, NAVY, "s", "RTX 4060")):
            if s is None:
                print(f"  {tag}: no {lab} curve found")
                continue
            # a final-only 3060 value is one point; draw it on top so the 4060 square can't hide it
            ax.plot(s.index / 1000, s.values, color=c, marker=mk, label=lab,
                    zorder=4 if len(s) == 1 else 2, **MK)
        if s0 is not None and s1 is not None:
            common = sorted(set(s0.index) & set(s1.index))
            if common:
                st = common[-1]
                dlt = s1[st] - s0[st]
                ax.text(0.97, 0.05, f"Δ = {dlt:+.2f} dB".replace("-", "\u2212"), transform=ax.transAxes,
                        ha="right", va="bottom", fontsize=8)
                print(f"  {tag}: step {st}  3060 {s0[st]:.3f}  4060 {s1[st]:.3f}  Δ {dlt:+.3f}")
        ax.set_xticks([2, 5, 10, 15, 20])
        ax.set_xlim(1, 21)
        ax.set_xlabel("step (k)")
        panel(ax, "abcd"[i], tag.replace("_", " "))
    axs[0].set_ylabel("validation SI-SDR (dB)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="outside lower center", ncol=2, frameon=False)
    print()
    save(fig, out)


# ------------------------------------------------------------------ A4 -----
def _ecdf(ax, v, color, marker, ls, label):
    v = np.sort(v)
    n = len(v)
    F = np.arange(1, n + 1) / n
    idx = np.unique(np.searchsorted(v, np.geomspace(v[0], v[-1], 9)).clip(0, n - 1))
    ax.plot(v, F, drawstyle="steps-post", color=color, ls=ls, marker=marker,
            markevery=idx.tolist(), label=label, **MK)


def fig_a4(df, out, snr=20):
    """
    B3 at +20 dB on test_unseen: r_over with the bins below DECOMP_MIN_HZ = 60 Hz (DC and 31 Hz)
    excluded (e_over / e_clean, the reported metric) vs included (e_over_full /
    e_clean_full). The high-SNR tail exists only when that low band is counted.
    """
    if not {"e_over_full", "e_clean_full"} <= set(df.columns):
        sys.exit("a4 needs e_over_full and e_clean_full (DC-included) columns in the eval CSVs")
    u = df[(df["split"] == "test_unseen") & (df["target_snr_db"] == snr) & (df["model"] == "B3")]
    exc = (u["e_over"] / u["e_clean"]).to_numpy()
    inc = (u["e_over_full"] / u["e_clean_full"]).to_numpy()
    n = len(u)
    if n == 0:
        sys.exit(f"a4: no B3 test_unseen rows at {snr:+d} dB")

    print(f"A4  B3 r_over at {snr:+d} dB, test_unseen (pooled folds), n = {n}")
    print(f"{'':14}{'mean':>9}{'median':>9}{'p90':>9}{'p99':>9}{'max':>9}")
    for name, v in (("<60 Hz excl.", exc), ("<60 Hz incl.", inc)):
        print(f"{name:14}{v.mean():>9.4f}{np.median(v):>9.4f}{np.quantile(v, .9):>9.4f}"
              f"{np.quantile(v, .99):>9.4f}{v.max():>9.4f}")
    ratio = inc / exc
    top = u.assign(r_exc=exc, r_inc=inc).nlargest(5, "r_inc")
    print("largest low-band-included values (fold, row_idx, noise_type, r_inc, r_exc):")
    for r in top.itertuples():
        print(f"  {r.fold:8}{r.row_idx:>6}  {r.noise_type:22}{r.r_inc:>8.4f}{r.r_exc:>9.4f}")
    print(f"rows where including the low band raises r_over >10x: {(ratio > 10).sum()} / {n}\n")

    fig, ax = plt.subplots(figsize=(3.5, 2.6), layout="constrained")
    _ecdf(ax, inc, GREY, "s", "--", "low band included")
    _ecdf(ax, exc, RED, "s", "-", "low band excluded (<60 Hz)")
    for v, c, lab in ((exc, RED, "excl."), (inc, GREY, "incl.")):
        p99 = np.quantile(v, 0.99)
        ax.axvline(p99, color=c, ls=":", lw=1.0)
        ax.text(p99, 0.04, f" p99 {lab} = {p99:.2g}", rotation=90, ha="right", va="bottom",
                color=c, fontsize=7)
    ax.set_xscale("log")
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(f"B3 {R_OVER} at {snr:+d} dB (log)")
    ax.set_ylabel("ECDF")
    ax.text(0.03, 0.97, f"n = {n}", transform=ax.transAxes, ha="left", va="top", fontsize=7.5)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=2,
               frameon=False, fontsize=7.5)
    save(fig, out)


# ----------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("figs", nargs="*", choices=["a1", "a2", "a3", "a4"])
    ap.add_argument("--eval-dir", help="folder with <tag>__<fold>__<split>.csv (a2, a4)")
    ap.add_argument("--wer-csv", help="per-utterance WER rows (a1)")
    ap.add_argument("--logs-3060", help="folder of RTX 3060 training logs (a3)")
    ap.add_argument("--logs-4060", help="folder of RTX 4060 training logs (a3)")
    ap.add_argument("--curves-csv", help="alternative to logs: tag,gpu,step,val_sisdr_db (a3)")
    ap.add_argument("--out-dir", default="figs")
    a = ap.parse_args()
    if not a.figs:
        # Run button / no arguments: use the repo's default locations
        root = Path(__file__).resolve().parent
        a.eval_dir = a.eval_dir or str(root / "results" / "eval")
        a.curves_csv = a.curves_csv or str(root / "results" / "metrics" / "training_curves.csv")
        a.out_dir = str(root / a.out_dir)
        a.figs = ["a2", "a3", "a4"]
        # src.wer writes to FAILDIR_EVAL (default <repo>/results)
        wer = [root / "results" / sub / n for sub in ("", "eval")
               for n in ("wer_snrmax-5.csv", "wer_rows.csv")]
        wer = next((f for f in wer if f.exists()), None)
        if wer and not a.wer_csv:
            a.wer_csv = str(wer)
        if a.wer_csv:
            a.figs.insert(0, "a1")
        else:
            print("a1 skipped: no WER CSV in results yet (run python -m src.wer --snr-max -5)\n")
        print("no figures named, running defaults:", " ".join(a.figs), "\n")
    set_style()
    od = Path(a.out_dir)
    df = None
    if {"a2", "a4"} & set(a.figs):
        if not a.eval_dir:
            sys.exit("a2/a4 need --eval-dir")
        df = load_eval(a.eval_dir)
    if "a1" in a.figs:
        if not a.wer_csv:
            sys.exit("a1 needs --wer-csv")
        fig_a1(a.wer_csv, od / "figA1_wer")
    if "a2" in a.figs:
        fig_a2(df, od / "figA2_rank_agreement")
    if "a3" in a.figs:
        fig_a3(a, od / "figA3_training_repro")
    if "a4" in a.figs:
        fig_a4(df, od / "figA4_b3_dc_tail")


if __name__ == "__main__":
    main()
