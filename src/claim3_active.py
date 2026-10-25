"""Claim 3 on ACTIVE models: verdict for configs/gate_claim3_active.yaml.

Runs the unchanged src.claim3 pipeline (features, arms, LightGBM settings, seed,
within-SNR / within-cell analysis, bootstrap) with the target taken from
results/labels_active/<tag>__<fold>__<split>.csv: y = log10(e_over_lv / e_clean).

    python -m src.claim3_active                    # all models with labels on disk
    python -m src.claim3_active --tags b1_fsd dfn3

Writes results/claim3_active/<tag>/{metrics,predictions}/, verdict.csv,
per_type.csv, agreement.csv and report.md. The verdict lines in report.md apply
the pre-committed rule; everything else is descriptive.
"""
from __future__ import annotations

import argparse

import config as C  # noqa: I001

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src import claim3 as K
from src.claim3_level import verdict as rule_verdict
from src.labels_active import OUT as LAB, SPLITS

OUT = C.EVAL / "claim3_active"
PRIMARY_FSD = ["b1_fsd", "b3_fsd", "cm_fsd"]
PRIMARY = PRIMARY_FSD + ["dfn3"]
SEEDS = {a: [a, f"{a}_s2", f"{a}_s3"] for a in PRIMARY_FSD}
ROBUST = [t for a in PRIMARY_FSD for t in SEEDS[a][1:]]
LABEL_COLS = ["g", "e_over_lv", "e_under_lv", "sisdr_in", "sisdr_out"]   # never features
MAX_MISSING = 0.01
_ORIG = K.load_joined


def make_loader(tag: str):
    def load(fold: str, split: str, arch: str = "") -> pd.DataFrame:
        L = pd.read_csv(LAB / f"{tag}__{fold}__{split}.csv")
        F = pd.read_csv(C.FEATURES / f"{fold}__{split}.csv")
        d = L.merge(F, on=["fold", "split", "row_idx"], suffixes=("", "_f"), validate="1:1")
        bad = int((d.uid != d.uid_f).sum())
        if bad:
            raise AssertionError(f"{tag} {fold}/{split}: {bad} rows misaligned between labels and features")
        d = d.drop(columns=["uid_f"])
        d["r_over"] = d.e_over_lv / d.e_clean
        d["y"] = np.log10(d.r_over + 1e-8)
        return d.drop(columns=LABEL_COLS)
    return load


def have(tag: str) -> bool:
    return all((LAB / f"{tag}__{f}__{s}.csv").exists() for f in C.FAMILIES for s in SPLITS)


def dfn3_complete() -> tuple[bool, str]:
    p = LAB / "dfn3_completeness.csv"
    if not p.exists():
        return have("dfn3"), "no completeness file"
    c = pd.read_csv(p)
    worst = float(c.missing_frac.max())
    return worst <= MAX_MISSING, f"worst (fold, split) missing {worst:.2%}"


def per_type(tag: str, fold: str, cond: pd.DataFrame) -> pd.DataFrame:
    if cond.empty:
        return pd.DataFrame()
    c = cond.assign(d_rho=cond.feats_only - cond.baseline)
    c["win"] = c.d_rho > 0
    g = c.groupby("noise_type").agg(cells=("win", "size"), won=("win", "sum"),
                                    mean_d_rho=("d_rho", "mean"))
    g["share_won"] = g.won / g.cells
    return g.reset_index().assign(tag=tag, fold=fold)


def agreement(tags: list[str]) -> pd.DataFrame:
    """Descriptive: within noise_type x SNR cells on test_matched, Spearman of the
    level target between models. MarVEN-trained b1 (labels_level) is the reference."""
    rows = []
    for fold in C.FAMILIES:
        cols, meta = {}, None
        ref = C.EVAL / "labels_level" / f"b1__{fold}__test_matched.csv"
        if ref.exists():
            r = pd.read_csv(ref)
            cols[f"b1_{fold}(marven)"] = r.set_index("uid").eval("log10(e_over_lv / e_clean + 1e-8)")
            meta = r.set_index("uid")[["noise_type", "snr"]]
        for t in tags:
            p = LAB / f"{t}__{fold}__test_matched.csv"
            if p.exists():
                d = pd.read_csv(p).set_index("uid")
                cols[t] = np.log10(d.e_over_lv / d.e_clean + 1e-8)
                meta = d[["noise_type", "snr"]]
        if meta is None or len(cols) < 2:
            continue
        W = pd.DataFrame(cols).join(meta, how="inner")
        names = list(cols)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                rho = [spearmanr(g[a], g[b]).statistic for _, g in W.groupby(["noise_type", "snr"])
                       if g[[a, b]].dropna().shape[0] >= 25]
                rows.append({"fold": fold, "a": a, "b": b, "cells": len(rho),
                             "median_cell_spearman": float(np.nanmedian(rho)) if rho else np.nan})
    return pd.DataFrame(rows)


def main(argv=None):
    p = argparse.ArgumentParser(description="Claim 3 on active models (gate_claim3_active.yaml)")
    p.add_argument("--tags", nargs="+", default=None)
    a = p.parse_args(argv)
    tags = [t for t in (a.tags or PRIMARY + ROBUST) if have(t)]
    missing = [t for t in (a.tags or PRIMARY + ROBUST) if t not in tags]
    if missing:
        print(f"no complete labels for: {', '.join(missing)} (skipped)")

    rows, types = [], []
    for tag in tags:
        base = OUT / tag
        C.METRICS, C.PREDICTIONS = base / "metrics", base / "predictions"
        K.load_joined = make_loader(tag)
        for fold in C.FAMILIES:
            print(f"\n################ model={tag}  fold={fold} ################")
            res = K.run(fold, tag)
            rows.append({"tag": tag, "fold": fold, **rule_verdict(res)})
            types.append(per_type(tag, fold, res["within_condition"]))
    K.load_joined = _ORIG

    OUT.mkdir(parents=True, exist_ok=True)
    v = pd.DataFrame(rows)
    v.to_csv(OUT / "verdict.csv", index=False)
    pt = pd.concat(types, ignore_index=True) if types else pd.DataFrame()
    pt.to_csv(OUT / "per_type.csv", index=False)
    ag = agreement(tags)
    ag.to_csv(OUT / "agreement.csv", index=False)

    model_pass = v.groupby("tag")["pass"].agg(lambda s: bool(s.all()) and len(s) == len(C.FAMILIES)).to_dict()
    dfn_ok, dfn_note = dfn3_complete()
    dfn_pass = bool(model_pass.get("dfn3", False)) and dfn_ok
    fsd_n = sum(bool(model_pass.get(t, False)) for t in PRIMARY_FSD)
    fsd_pass = fsd_n >= 2
    primary_ready = all(t in model_pass for t in PRIMARY)
    if not primary_ready:
        final = "INCOMPLETE (not all primary models have labels)"
    elif dfn_pass and fsd_pass:
        final = "HOLDS_ACTIVE"
    elif dfn_pass or fsd_pass:
        final = "PARTIAL (" + ("DFN3 passes, FSD models do not" if dfn_pass else "FSD models pass, DFN3 does not") + ")"
    else:
        final = "FAILS"

    seed_lines = []
    for arch, ts in SEEDS.items():
        got = {t: model_pass[t] for t in ts if t in model_pass}
        if len(got) == 3:
            maj = sum(got.values()) >= 2
            flag = "" if got[arch] == maj else "  <- seed_sensitive"
            seed_lines.append(f"- {arch}: {sum(got.values())}/3 seeds pass{flag}")
        elif got:
            seed_lines.append(f"- {arch}: {sum(got.values())}/{len(got)} seeds with labels pass (incomplete)")

    pd.set_option("display.width", 220)
    lines = ["# Claim 3 on active models (configs/gate_claim3_active.yaml)", "",
             f"## Verdict: {final}", "",
             f"- FSD architectures passing (both folds): {fsd_n}/3 "
             f"({', '.join(t for t in PRIMARY_FSD if model_pass.get(t))})",
             f"- DFN3: {'pass' if model_pass.get('dfn3') else 'no pass'}; completeness {'ok' if dfn_ok else 'NOT ok'} ({dfn_note})",
             "", "## Per model and fold (level target, pre-committed rules a and b)", "",
             v.round(3).to_string(index=False), "",
             "## Seeds (descriptive, cannot change the verdict)", "", *(seed_lines or ["- none run"]), "",
             "## Per noise type: share of SNR cells won by feats_only (descriptive)", "",
             pt.round(3).to_string(index=False) if len(pt) else "(none)", "",
             "## Cross-model agreement of the target, test_matched (descriptive)", "",
             ag.round(3).to_string(index=False) if len(ag) else "(none)", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
