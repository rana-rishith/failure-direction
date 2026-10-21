"""Gate XN2 follow-ups (descriptive, no verdicts). numpy/pandas only.

    python -m src.xn2_extra      # writes results/xcorpus/report2/extra.md + CSVs

1. per-SNR level-aligned split (d_g, nr_g, g) for the fsd / demand models on MarVEN
2. C1 reconciliation: the C1_lowcut statistic (median gain gap) next to the Table III
   statistic (mean output SI-SDR, heard minus unseen rows) on the same checkpoints
"""
import numpy as np
import pandas as pd

import config as C
from src.xcorpus import OUT, _derive
from src.xn2 import REP, load_eval

MET = ["d_g", "nr_g", "g", "sisdr_gain"]


def per_snr(d, lines):
    mv = d[(d.cond == "marven") & d.tag.str.contains("_fsd|_demand")].copy()
    mv["group"] = mv.tag.str.replace(r"_s\d$", "", regex=True)
    t = mv.groupby(["group", "tag", "snr"])[MET].median().groupby(["group", "snr"]).mean()
    t.round(4).to_csv(REP / "extra_marven_per_snr.csv")
    for m in ("d_g", "nr_g", "g"):
        lines += [f"## MarVEN per SNR, seed mean of per-tag medians: {m}", "", t[m].unstack("snr").round(3).to_string(), ""]
    # seed spread for d_g at each SNR
    s = mv.groupby(["group", "tag", "snr"]).d_g.median().groupby(["group", "snr"]).agg(["min", "max"])
    s.round(4).to_csv(REP / "extra_marven_per_snr_dg_seed_range.csv")
    lines += ["## d_g per SNR, seed range (min / max)", "",
              (s["min"].round(3).astype(str) + " / " + s["max"].round(3).astype(str)).unstack("snr").to_string(), ""]
    # pretrained models on the same MarVEN rows
    ext = []
    for model in ("dfn3", "sgmse"):
        p = OUT / f"ext_{model}.csv"
        if p.exists():
            e = _derive(pd.read_csv(p))
            ext.append(e[e.cond == "marven"].assign(group=model))
    if ext:
        e = pd.concat(ext)
        te = e.groupby(["group", "snr"])[MET].median()
        te["n"] = e.groupby(["group", "snr"]).size()
        te.round(4).to_csv(REP / "extra_marven_per_snr_pretrained.csv")
        lines += ["## Pretrained models on MarVEN, per SNR (medians; SGMSE+ n is small)", "", te.round(3).to_string(), ""]
    # per type x SNR <= 0 for fsd models (where does d_g go negative?)
    low = mv[mv.snr <= 0]
    pt = low[low.group.str.contains("_fsd")].groupby(["group", "tag", "noise_type"]).d_g.median().groupby(["group", "noise_type"]).mean()
    pt = pt.unstack("noise_type").round(3)
    pt.to_csv(REP / "extra_fsd_dg_by_type_lowsnr.csv")
    lines += ["## fsd models, d_g by MarVEN type, SNR <= 0 (seed mean)", "", pt.to_string(), ""]


def c1_reconcile(d, lines):
    mv = d[d.cond == "marven"]
    rows = []
    for a in ("b1", "b3", "cm"):
        for fam, heard in (("anthro", C.ANTHRO), ("weather", C.WEATHER)):
            x = mv[mv.tag == f"{a}_{fam}"]
            if x.empty:
                continue
            h, u = x[x.noise_type.isin(heard)], x[~x.noise_type.isin(heard)]
            r = dict(tag=f"{a}_{fam}", n_heard=len(h), n_unseen=len(u),
                     in_mean_h=h.sisdr_in.mean(), in_mean_u=u.sisdr_in.mean(),
                     out_mean_gap=h.sisdr_out.mean() - u.sisdr_out.mean(),
                     gain_mean_gap=h.sisdr_gain.mean() - u.sisdr_gain.mean(),
                     gain_median_gap=h.sisdr_gain.median() - u.sisdr_gain.median())
            hh, uu = h.sisdr_hp100_out - h.sisdr_hp100_in, u.sisdr_hp100_out - u.sisdr_hp100_in
            r["hp100_out_mean_gap"] = h.sisdr_hp100_out.mean() - u.sisdr_hp100_out.mean()
            r["hp100_gain_mean_gap"] = hh.mean() - uu.mean()
            r["hp100_gain_median_gap"] = hh.median() - uu.median()
            r["ratio_median_gain"] = r["hp100_gain_median_gap"] / r["gain_median_gap"]   # = C1_lowcut ratio
            r["ratio_mean_out"] = r["hp100_out_mean_gap"] / r["out_mean_gap"]
            r["ratio_mean_gain"] = r["hp100_gain_mean_gap"] / r["gain_mean_gap"]
            rows.append(r)
    t = pd.DataFrame(rows)
    em = C.METRICS / "eval_matrix.csv"
    if em.exists():
        m = pd.read_csv(em)
        g = m[m.tag.isin(["b1", "b3", "cm"])].groupby(["tag", "fold", "split"]).si_sdr_out.mean().unstack("split")
        g["table3_gap"] = g.test_matched - g.test_unseen
        t["table3_gap"] = [g.table3_gap.get(tuple(s.split("_")), np.nan) for s in t.tag]
    t.to_csv(REP / "extra_c1_reconcile.csv", index=False)
    lines += ["## C1 reconciliation (MarVEN test rows, seed-1234 checkpoints)", "",
              t.round(3).to_string(index=False), ""]


def main():
    d = load_eval()
    lines = ["# Gate XN2 follow-ups (descriptive)", ""]
    per_snr(d, lines)
    c1_reconcile(d, lines)
    (REP / "extra.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
