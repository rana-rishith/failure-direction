"""Claim 3 re-check: does input-side prediction survive a level-aligned target?

Runs the unchanged src.claim3 pipeline (same features, arms, LightGBM settings,
within-SNR and within-cell analysis, bootstrap) with the prediction target
swapped, and writes everything under results/claim3_level/<target>/ so the
original Claim 3 outputs are never overwritten.

Targets
    intent        log10 r_over from src.labels      (the original Claim 3 target;
                                                     must reproduce the original
                                                     numbers: harness check)
    level         log10 e_over_lv / e_clean        (level-aligned output split; primary)
    intent_level  log10 e_over_ilv / e_clean       (level-aligned mask intent; robustness)

Pre-committed rule (configs/gate_claim3_level.yaml), applied per fold to the
'level' target; Claim 3 survives if it holds in BOTH folds:
    (a) feats_only beats baseline in mean within-SNR Spearman, and in >= 6 of 8 SNR strata
    (b) feats_only beats baseline in >= 75% of noise_type x SNR cells (n >= 25)

Usage, after `python -m src.labels_level`:
    python -m src.claim3_level
"""
from __future__ import annotations

import argparse

import config as C  # noqa: I001

import numpy as np
import pandas as pd

from src import claim3 as K

OUT = C.EVAL / "claim3_level"
TARGETS = {"intent": None, "level": "e_over_lv", "intent_level": "e_over_ilv"}
LEVEL_DIR = C.EVAL / "labels_level"
_ORIG_LOAD = K.load_joined


def make_loader(target: str):
    col = TARGETS[target]

    def load(fold: str, split: str, arch: str = "b1") -> pd.DataFrame:
        d = _ORIG_LOAD(fold, split, arch)
        if col is None:
            return d
        L = pd.read_csv(LEVEL_DIR / f"{arch}__{fold}__{split}.csv",
                        usecols=["uid", col, "e_clean"])
        m = d.merge(L.rename(columns={col: "_e_t", "e_clean": "_e_c"}), on="uid",
                    how="left", validate="1:1")
        if m._e_t.isna().any():
            raise AssertionError(f"{int(m._e_t.isna().sum())} rows of {fold}/{split} lack "
                                 "level labels; rerun src.labels_level")
        m["r_over"] = m._e_t / m._e_c
        m["y"] = np.log10(m.r_over + 1e-8)
        return m.drop(columns=["_e_t", "_e_c"])     # never let label columns become features

    return load


def verdict(res: dict) -> dict:
    s = res["within_snr"]
    c = res["within_condition"]
    d_snr = (s.feats_only - s.baseline) if len(s) else pd.Series(dtype=float)
    d_cell = (c.feats_only - c.baseline) if len(c) else pd.Series(dtype=float)
    a = bool(len(d_snr) and d_snr.mean() > 0 and (d_snr > 0).sum() >= 6)
    b = bool(len(d_cell) and (d_cell > 0).mean() >= 0.75)
    return {"mean_within_snr_rho_featsonly": float(s.feats_only.mean()) if len(s) else np.nan,
            "mean_within_snr_rho_baseline": float(s.baseline.mean()) if len(s) else np.nan,
            "snr_strata_won": int((d_snr > 0).sum()), "snr_strata": int(len(d_snr)),
            "cells_won_frac": float((d_cell > 0).mean()) if len(d_cell) else np.nan,
            "cells": int(len(d_cell)),
            "auc_top10_featsonly_minus_baseline": res["margins"]["auc_top10_featsonly_minus_baseline"],
            "rule_a": a, "rule_b": b, "pass": a and b}


def main(argv=None):
    p = argparse.ArgumentParser(description="Claim 3 re-check with level-aligned targets")
    p.add_argument("--targets", nargs="+", default=list(TARGETS))
    p.add_argument("--arch", default="b1")
    a = p.parse_args(argv)
    rows = []
    for target in a.targets:
        base = OUT / target
        C.METRICS, C.PREDICTIONS = base / "metrics", base / "predictions"
        K.load_joined = make_loader(target)
        for fold in C.FAMILIES:
            print(f"\n################ target={target}  fold={fold} ################")
            res = K.run(fold, a.arch)
            rows.append({"target": target, "fold": fold, **verdict(res)})
    K.load_joined = _ORIG_LOAD
    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "verdict.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n================ Claim 3 under each target ================")
    print(out.round(3).to_string(index=False))
    lv = out[out.target == "level"]
    if len(lv) == len(C.FAMILIES):
        ok = bool(lv["pass"].all())
        print(f"\nPRE-COMMITTED (gate_claim3_level.yaml), level target, both folds: "
              f"{'SURVIVES' if ok else 'DOES NOT SURVIVE'}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
