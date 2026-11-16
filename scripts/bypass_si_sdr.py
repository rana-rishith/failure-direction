"""Bypass simulation for the Claim 3 predictor, in SI-SDR terms (CPU only, no audio).

    python scripts/bypass_si_sdr.py [repo root]

Policy. Within each SNR level, rank the rows of the weather fold by the predicted
speech loss (pred_feats_only, the log10 r_over,g prediction of gate C3c) and send
the top share q of them through unprocessed. The outcome is the mean per-row SI-SDR
after the choice. Three references share the same rows:

    enhance   every row enhanced (q = 0)
    random    expected value of bypassing a random share q inside each SNR level
    oracle    bypass exactly the rows where the input beat the output (best choice per row)

The second output is the within-SNR Spearman correlation between the prediction and
the per-row SI-SDR improvement (sisdr_out - sisdr_in). A positive value means that
the rows predicted to lose the most speech are also the rows that enhancement helps
most, which is the reason a bypass on predicted speech loss cannot help.

Inputs, all committed result files:
    results/claim3c/heldout/<tag>/predictions/claim3_weather_preds.csv
    results/labels_active/<tag>__weather__test_matched.csv

Writes results/bypass/bypass_si_sdr.csv, bypass_si_sdr_summary.csv and the LaTeX macro
file paper/newresults_bypass.tex that paper.tex reads.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
TAGS = [f"{a}_fsd_s{s}" for a in ("b1", "b3", "cm") for s in (6, 7)]
SHARES = (0.05, 0.10, 0.20)


def load(tag: str) -> pd.DataFrame:
    p = pd.read_csv(os.path.join(ROOT, "results/claim3c/heldout", tag, "predictions",
                                 "claim3_weather_preds.csv"))
    q = pd.read_csv(os.path.join(ROOT, "results/labels_active",
                                 f"{tag}__weather__test_matched.csv"),
                    usecols=["uid", "sisdr_in", "sisdr_out"])
    d = p.merge(q, on="uid", validate="1:1")
    if len(d) != len(p):
        raise SystemExit(f"{tag}: merge lost rows")
    d["gain"] = d.sisdr_out - d.sisdr_in
    return d


def policy(d: pd.DataFrame, share: float) -> dict:
    out_pred, out_rand, out_orc = [], [], []
    for _, g in d.groupby("snr"):
        n = len(g)
        k = int(math.ceil(share * n))
        order = g.pred_feats_only.to_numpy().argsort()[::-1]
        bypass = np.zeros(n, bool)
        bypass[order[:k]] = True
        res = np.where(bypass, g.sisdr_in, g.sisdr_out)
        out_pred.append(res)
        out_rand.append(g.sisdr_out.to_numpy() + share * (g.sisdr_in.to_numpy() - g.sisdr_out.to_numpy()))
        out_orc.append(np.maximum(g.sisdr_in.to_numpy(), g.sisdr_out.to_numpy()))
    cat = np.concatenate
    return {"predicted": cat(out_pred).mean(), "random": cat(out_rand).mean(),
            "oracle": cat(out_orc).mean()}


def main() -> None:
    rows, corr = [], []
    for tag in TAGS:
        d0 = load(tag)
        for scope, d in (("all", d0), ("snr_le_-5", d0[d0.snr <= -5])):
            base = d.sisdr_out.mean()
            r = [stats.spearmanr(g.pred_feats_only, g.gain)[0] for _, g in d.groupby("snr")
                 if len(g) >= 25]
            corr.append({"tag": tag, "scope": scope, "rho_pred_gain": float(np.nanmean(r)),
                         "n": len(d)})
            for q in SHARES:
                p = policy(d, q)
                rows.append({"tag": tag, "scope": scope, "share": q, "enhance": base, **p,
                             "pred_minus_random": p["predicted"] - p["random"]})
    res = pd.DataFrame(rows)
    cor = pd.DataFrame(corr)
    os.makedirs(os.path.join(ROOT, "results/bypass"), exist_ok=True)
    res.to_csv(os.path.join(ROOT, "results/bypass/bypass_si_sdr.csv"), index=False)
    cor.to_csv(os.path.join(ROOT, "results/bypass/bypass_si_sdr_corr.csv"), index=False)
    summ = res.groupby(["scope", "share"])[["enhance", "predicted", "random", "oracle",
                                            "pred_minus_random"]].agg(["min", "max"])
    summ.to_csv(os.path.join(ROOT, "results/bypass/bypass_si_sdr_summary.csv"))
    pd.set_option("display.width", 200)
    print(res.groupby(["scope", "share"])[["enhance", "predicted", "random", "oracle",
                                           "pred_minus_random"]].mean().round(3))
    print(cor.groupby("scope").rho_pred_gain.agg(["min", "max"]).round(3))
    # LaTeX macros
    mac = []
    for scope, tagname in (("all", "All"), ("snr_le_-5", "Low")):
        c = cor[cor.scope == scope].rho_pred_gain
        mac.append(f"\\newcommand{{\\bypRho{tagname}Min}}{{{c.min():.2f}}}")
        mac.append(f"\\newcommand{{\\bypRho{tagname}Max}}{{{c.max():.2f}}}")
        for q in SHARES:
            s = res[(res.scope == scope) & (res.share == q)]
            qq = int(round(q * 100))
            mac.append(f"\\newcommand{{\\bypPredMinusRand{tagname}{ {5:"Five",10:"Ten",20:"Twenty"}[qq]}Min}}{{{s.pred_minus_random.min():.2f}}}")
            mac.append(f"\\newcommand{{\\bypPredMinusRand{tagname}{ {5:"Five",10:"Ten",20:"Twenty"}[qq]}Max}}{{{s.pred_minus_random.max():.2f}}}")
        s = res[(res.scope == scope) & (res.share == SHARES[0])]
        orc = s.oracle - s.enhance
        mac.append(f"\\newcommand{{\\bypOracleMinusEnh{tagname}Min}}{{{orc.min():.2f}}}")
        mac.append(f"\\newcommand{{\\bypOracleMinusEnh{tagname}Max}}{{{orc.max():.2f}}}")
        for q in SHARES:
            t = res[(res.scope == scope) & (res.share == q)]
            pe = t.predicted - t.enhance
            qq = int(round(q * 100))
            mac.append(f"\\newcommand{{\\bypPredMinusEnh{tagname}{ {5:"Five",10:"Ten",20:"Twenty"}[qq]}Min}}{{{pe.min():.2f}}}")
            mac.append(f"\\newcommand{{\\bypPredMinusEnh{tagname}{ {5:"Five",10:"Ten",20:"Twenty"}[qq]}Max}}{{{pe.max():.2f}}}")
    with open(os.path.join(ROOT, "paper/newresults_bypass.tex"), "w") as f:
        f.write("% written by scripts/bypass_si_sdr.py\n" + "\n".join(mac) + "\n")


if __name__ == "__main__":
    main()
