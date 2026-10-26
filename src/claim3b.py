"""Claim 3b verdict: configs/gate_claim3b.yaml.

Same pipeline as src.claim3_active (unchanged src.claim3 arms, LightGBM settings,
seed, within-SNR / within-cell analysis, bootstrap, level target), with the 12
burst features from src.features_burst joined to the 33 features of src.features.

    python -m src.claim3b              # held-out seeds (the verdict)
    python -m src.claim3b --dev        # seeds 1-3 + DFN3, descriptive only

The held-out models (seed 4 and 5 of b1_fsd, b3_fsd, cm_fsd) did not exist when
the gate was written. The dev run reuses models whose Claim 3 result had been
seen, so it can never change the verdict.

Writes results/claim3b/<heldout|dev>/<tag>/..., verdict.csv, per_type.csv, report.md.
"""
from __future__ import annotations

import argparse

import config as C  # noqa: I001

import pandas as pd

from src import claim3 as K
from src import claim3_active as A
from src.claim3_level import verdict as rule_ab
from src.features_burst import OUT_DIR as BURST, NAMES as BURST_NAMES

OUT = C.EVAL / "claim3b"
ARCHS = ["b1_fsd", "b3_fsd", "cm_fsd"]
HELDOUT = [f"{a}_s{s}" for a in ARCHS for s in (4, 5)]
DEV = [t for a in ARCHS for t in (a, f"{a}_s2", f"{a}_s3")] + ["dfn3"]
TARGET_TYPE, TARGET_FOLD, MIN_TARGET_CELLS = "bubble_curtain", "anthro", 6
_ORIG = K.load_joined


def make_loader(tag: str):
    base = A.make_loader(tag)

    def load(fold: str, split: str, arch: str = "") -> pd.DataFrame:
        d = base(fold, split, arch)
        B = pd.read_csv(BURST / f"{fold}__{split}.csv")
        m = d.merge(B, on=["fold", "split", "row_idx"], suffixes=("", "_b"), validate="1:1")
        bad = int((m.uid != m.uid_b).sum())
        if bad or len(m) != len(d):
            raise AssertionError(f"{tag} {fold}/{split}: burst features misaligned ({bad} rows)")
        return m.drop(columns=["uid_b"])
    return load


def rule_c(cond: pd.DataFrame) -> tuple[int, int]:
    c = cond[cond.noise_type == TARGET_TYPE]
    return int((c.feats_only > c.baseline).sum()), int(len(c))


def run(tags: list[str], out) -> pd.DataFrame:
    rows, types = [], []
    for tag in tags:
        C.METRICS, C.PREDICTIONS = out / tag / "metrics", out / tag / "predictions"
        K.load_joined = make_loader(tag)
        for fold in C.FAMILIES:
            print(f"\n################ 3b model={tag}  fold={fold} ################")
            res = K.run(fold, tag)
            r = {"tag": tag, "fold": fold, **rule_ab(res)}
            if fold == TARGET_FOLD:
                won, n = rule_c(res["within_condition"])
                r.update(bubble_cells_won=won, bubble_cells=n, rule_c=won >= MIN_TARGET_CELLS)
            rows.append(r)
            types.append(A.per_type(tag, fold, res["within_condition"]))
            imp = res["importance"]
            print("burst features in full-arm top 12:",
                  [f for f in imp.head(12).index if f in BURST_NAMES] or "none")
    K.load_joined = _ORIG
    out.mkdir(parents=True, exist_ok=True)
    v = pd.DataFrame(rows)
    v.to_csv(out / "verdict.csv", index=False)
    pt = pd.concat(types, ignore_index=True) if types else pd.DataFrame()
    pt.to_csv(out / "per_type.csv", index=False)
    return v, pt


def model_pass(v: pd.DataFrame) -> dict[str, bool]:
    res = {}
    for tag, g in v.groupby("tag"):
        ab = bool(g["pass"].all()) and len(g) == len(C.FAMILIES)
        c = bool(g.loc[g.fold == TARGET_FOLD, "rule_c"].fillna(False).all())
        res[tag] = ab and c
    return res


def final(mp: dict[str, bool]) -> str:
    if not all(t in mp for t in HELDOUT):
        return "INCOMPLETE (not all held-out models have labels)"
    n = sum(mp[t] for t in HELDOUT)
    every_arch = all(any(mp[f"{a}_s{s}"] for s in (4, 5)) for a in ARCHS)
    if n >= 4 and every_arch:
        return "HOLDS"
    if n >= 2:
        return "PARTIAL"
    return "FAILS"


def main(argv=None):
    p = argparse.ArgumentParser(description="Claim 3b (gate_claim3b.yaml)")
    p.add_argument("--dev", action="store_true", help="descriptive run on seeds 1-3 + DFN3")
    a = p.parse_args(argv)
    want = DEV if a.dev else HELDOUT
    tags = [t for t in want if A.have(t)]
    skipped = [t for t in want if t not in tags]
    if skipped:
        print(f"no complete labels for: {', '.join(skipped)} (skipped)")
    out = OUT / ("dev" if a.dev else "heldout")
    v, pt = run(tags, out)
    mp = model_pass(v)
    head = ("## DEV run (descriptive; these models' Claim 3 result was seen; cannot change the verdict)"
            if a.dev else f"## Verdict: {final(mp)}")
    pd.set_option("display.width", 240)
    lines = ["# Claim 3b: burst features (configs/gate_claim3b.yaml)", "", head, "",
             *[f"- {t}: {'pass' if mp.get(t) else 'no pass'}" for t in tags], "",
             "## Per model and fold (rules a, b; rule c in the anthro fold)", "",
             v.round(3).to_string(index=False), "",
             "## Per noise type: share of SNR cells won by feats_only (descriptive)", "",
             pt.round(3).to_string(index=False) if len(pt) else "(none)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
