"""Claim 3c verdict: configs/gate_claim3c.yaml.

Reuses src.claim3b unchanged (45 reference-free features, level target, arms,
LightGBM settings, within-SNR / within-cell analysis). Only the models and the
verdict rule differ:

  models   b1_fsd, b3_fsd, cm_fsd at seeds 6 and 7 (trained after the gate commit)
  verdict  weather fold only: rule a, rule b (thresholds as C3b) and rule t
           (mean d_rho > 0 within each of rainfall, lightning, hurricane)

The anthro fold is run and reported, descriptive only.

    python -m src.claim3c

Writes results/claim3c/heldout/<tag>/..., verdict.csv, per_type.csv, report.md.
"""
from __future__ import annotations

import argparse

import config as C  # noqa: I001

import pandas as pd

from src import claim3_active as A
from src import claim3b as B

OUT = C.EVAL / "claim3c"
ARCHS = B.ARCHS
SEEDS = (6, 7)
HELDOUT = [f"{a}_s{s}" for a in ARCHS for s in SEEDS]
VERDICT_FOLD = "weather"
WEATHER = ("rainfall", "lightning", "hurricane")


def rule_t(pt: pd.DataFrame, tag: str) -> bool:
    g = pt[(pt.tag == tag) & (pt.fold == VERDICT_FOLD)]
    if set(g.noise_type) != set(WEATHER):
        return False
    return bool((g.mean_d_rho > 0).all())


def model_pass(v: pd.DataFrame, pt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tag in v.tag.unique():
        w = v[(v.tag == tag) & (v.fold == VERDICT_FOLD)]
        a = bool(len(w) == 1 and w.rule_a.iloc[0])
        b = bool(len(w) == 1 and w.rule_b.iloc[0])
        t = rule_t(pt, tag)
        rows.append({"tag": tag, "rule_a": a, "rule_b": b, "rule_t": t, "pass": a and b and t})
    return pd.DataFrame(rows)


def final(mp: pd.DataFrame) -> str:
    got = dict(zip(mp.tag, mp["pass"])) if len(mp) else {}
    if not all(t in got for t in HELDOUT):
        return "INCOMPLETE (not all held-out models have labels)"
    n = sum(bool(got[t]) for t in HELDOUT)
    every_arch = all(any(got[f"{a}_s{s}"] for s in SEEDS) for a in ARCHS)
    if n >= 4 and every_arch:
        return "HOLDS"
    if n >= 2:
        return "PARTIAL"
    return "FAILS"


def main(argv=None):
    argparse.ArgumentParser(description="Claim 3c (gate_claim3c.yaml)").parse_args(argv)
    tags = [t for t in HELDOUT if A.have(t)]
    skipped = [t for t in HELDOUT if t not in tags]
    if skipped:
        print(f"no complete labels for: {', '.join(skipped)} (skipped)")
    out = OUT / "heldout"
    v, pt = B.run(tags, out)
    mp = model_pass(v, pt)
    mp.to_csv(out / "model_pass.csv", index=False)
    pd.set_option("display.width", 240)
    w, an = v[v.fold == VERDICT_FOLD], v[v.fold != VERDICT_FOLD]
    lines = ["# Claim 3c: weather noise, held-out seeds 6 and 7 (configs/gate_claim3c.yaml)", "",
             f"## Verdict: {final(mp)}", "",
             *[f"- {r.tag}: {'pass' if r['pass'] else 'no pass'}" for _, r in mp.iterrows()], "",
             "## Verdict rules per model (weather fold: rules a, b, t)", "",
             mp.to_string(index=False) if len(mp) else "(none)", "",
             "## Weather fold (verdict)", "",
             w.round(3).to_string(index=False) if len(w) else "(none)", "",
             "## Anthro fold (descriptive only; rules a, b, c as C3b)", "",
             an.round(3).to_string(index=False) if len(an) else "(none)", "",
             "## Per noise type: share of SNR cells won by feats_only (weather = verdict, anthro = descriptive)", "",
             pt.round(3).to_string(index=False) if len(pt) else "(none)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
