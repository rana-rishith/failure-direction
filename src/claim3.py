"""
Claim 3 — within-condition magnitude prediction on r_over.

    python -m src.claim3 --fold weather
    python -m src.claim3 --fold weather --damaging-only

Scope. Direction and condition are ~99.4% collinear, so a direction classifier
would be predicting noise family from spectral shape and proving nothing. The
claim is therefore magnitude prediction with the condition held fixed: how badly
will THIS utterance fail.

Three arms, not two:
  baseline    snr + log_e_noisy          (pre-registered: oracle SNR + loudness)
  full        baseline + all features    (the ablation contrast)
  feats_only  features, NO oracle snr    (the only arm that is genuinely
                                          pre-hoc at inference time)

The third arm exists because `target_snr_db` is mixing metadata, not something
available before enhancement on real audio. Reporting `full` alone would let a
reviewer point out that the headline model uses an oracle input. Within an SNR
stratum snr is constant, so the within-SNR margins are unaffected either way.

How to read it. Pooled numbers look strong for every arm because SNR alone
explains a lot across an eight-level sweep — that is not the result. The verdict
is the WITHIN-SNR margin and the TOP-DECILE AUC margin of the feature arms over
the baseline, on speakers the predictor never saw, with per-condition breakdowns
alongside.

Pre-committed failure condition. If the full feature set does not beat the
two-feature baseline by a few points on tail AUC — not noise — the finding is
that cheap input-side features do not predict enhancement failure, and the
ablation is the evidence. That publishes, because the baseline was registered in
advance.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import config as C
from src.features import assert_reference_free

# Columns that are labels, identifiers, or reference-derived. Never features.
DROP = {
    "tag", "fold", "split", "row_idx", "uid", "noise_type", "speaker_id",
    "chapter_id", "utterance_id", "duration_sec",
    "e_over", "e_under", "e_clean", "e_noisy", "r_over", "r_under",
    "dir_idx", "mag", "y",
}
BASELINE = ["snr", "log_e_noisy"]

# The noise types that actually damage ASR: hurricane and bubble_curtain sit at
# the clean ASR floor even at -15 dB broadband SNR (hurricane's energy is out of
# band, bubble_curtain is bursty).
DAMAGING_TYPES = ("rainfall", "large_commercial_ship", "lightning")
DAMAGING_SNR_MAX = -5


def load_joined(fold: str, split: str, arch: str = "b1") -> pd.DataFrame:
    """
    Join labels to features. Validated on `uid`, not only on the positional
    (fold, split, row_idx) key: if the manifest row order ever changes, a
    positional join misaligns silently and produces believable wrong results.
    """
    L = pd.read_csv(C.LABELS / f"{arch}__{fold}__{split}.csv")
    F = pd.read_csv(C.FEATURES / f"{fold}__{split}.csv")
    d = L.merge(F, on=["fold", "split", "row_idx"], suffixes=("", "_f"), validate="1:1")
    if "uid_f" in d.columns:
        mismatch = int((d.uid != d.uid_f).sum())
        if mismatch:
            raise AssertionError(
                f"{mismatch}/{len(d)} rows misaligned between labels and features for "
                f"{fold}/{split}. The positional row_idx join is stale — regenerate "
                "both with --no-resume."
            )
        d = d.drop(columns=["uid_f"])
    d["r_over"] = d.e_over / d.e_clean
    d["y"] = np.log10(d.r_over + 1e-8)
    return d


def feature_lists(train: pd.DataFrame) -> dict[str, list[str]]:
    full = [c for c in train.columns if c not in DROP]
    assert_reference_free([c for c in full if c != "snr"])   # snr is the declared oracle
    feats_only = [c for c in full if c != "snr"]
    return {"baseline": BASELINE, "full": full, "feats_only": feats_only}


def fit_arm(cols, name, tr, va, te, seed: int = C.SEED):
    import lightgbm as lgb

    m = lgb.LGBMRegressor(
        n_estimators=2000, learning_rate=0.03, num_leaves=31,
        min_child_samples=40, subsample=0.8, colsample_bytree=0.8,
        random_state=seed, verbose=-1,
    )
    stop = [lgb.early_stopping(100, verbose=False)]
    try:        # lightgbm >= 4.7 renamed eval_set to eval_X/eval_y
        m.fit(tr[cols], tr.y, eval_X=va[cols], eval_y=va.y, callbacks=stop)
    except TypeError:
        m.fit(tr[cols], tr.y, eval_set=[(va[cols], va.y)], callbacks=stop)
    pred = m.predict(te[cols])
    row = {
        "arm": name, "n_feat": len(cols), "best_iter": m.best_iteration_,
        "spearman_pooled": float(spearmanr(pred, te.y).statistic),
        "rmse": float(np.sqrt(((pred - te.y) ** 2).mean())),
    }
    for q in (0.90, 0.95, 0.99):
        # round(), not int(): (1 - 0.90) * 100 is 9.999999999999998, so int()
        # silently labels the top-decile column "auc_top9".
        name = f"auc_top{round((1 - q) * 100)}"
        pos = (te.y >= te.y.quantile(q)).to_numpy()
        row[name] = (float(roc_auc_score(pos, pred))
                     if 0 < pos.sum() < len(pos) else float("nan"))
    return row, m, pred


def within(te: pd.DataFrame, preds: dict[str, np.ndarray], by, min_n: int = 25):
    """Spearman inside each stratum. Pooling masks real effects — this is the
    honest view, and the per-condition version guards against the frac_pos
    artifact where an apparent advantage came entirely from reordering
    conditions rather than per-utterance prediction."""
    t = te.assign(**{f"pred_{k}": v for k, v in preds.items()})
    rows = []
    for keys, g in t.groupby(by):
        if len(g) < min_n:
            continue
        rec = dict(zip(by if isinstance(by, (list, tuple)) else [by],
                       keys if isinstance(keys, tuple) else (keys,)))
        rec["n"] = len(g)
        for k in preds:
            rec[k] = round(float(spearmanr(g[f"pred_{k}"], g.y).statistic), 3)
        rows.append(rec)
    cols = list(by) + ["n"] + list(preds)
    return pd.DataFrame(rows, columns=cols) if not rows else pd.DataFrame(rows)


def run(fold: str = "weather", arch: str = "b1", damaging_only: bool = False,
        seed: int = C.SEED) -> dict:
    tr, va, te = (load_joined(fold, s, arch) for s in ("train", "val", "test_matched"))

    if damaging_only:
        def keep(d):
            return d[d.noise_type.isin(DAMAGING_TYPES) & (d.snr <= DAMAGING_SNR_MAX)]
        tr, va, te = keep(tr), keep(va), keep(te)
        print(f"damaging regime only ({', '.join(DAMAGING_TYPES)}, snr <= "
              f"{DAMAGING_SNR_MAX}): train {len(tr)} val {len(va)} test {len(te)}")
        print("state the reduced training-row count explicitly as a limitation")

    assert not (set(tr.speaker_id) & set(te.speaker_id)), "SPEAKER LEAK train/test"
    assert not (set(tr.speaker_id) & set(va.speaker_id)), "SPEAKER LEAK train/val"

    arms = feature_lists(tr)
    print(f"fold={fold} | train {len(tr)} val {len(va)} test {len(te)} | "
          f"features: baseline {len(arms['baseline'])}, full {len(arms['full'])}, "
          f"feats_only {len(arms['feats_only'])}")

    rows, preds, importances = [], {}, None
    for name, cols in arms.items():
        row, model, pred = fit_arm(cols, name, tr, va, te, seed)
        rows.append(row)
        preds[name] = pred
        if name == "full":
            importances = pd.Series(model.feature_importances_, index=cols)\
                .sort_values(ascending=False)

    table = pd.DataFrame(rows)
    C.ensure_dirs()
    suffix = f"{fold}{'_damaging' if damaging_only else ''}"
    table.to_csv(C.METRICS / f"claim3_{suffix}_summary.csv", index=False)

    by_snr = within(te, preds, ["snr"])
    by_cond = within(te, preds, ["noise_type", "snr"])
    by_snr.to_csv(C.METRICS / f"claim3_{suffix}_within_snr.csv", index=False)
    by_cond.to_csv(C.METRICS / f"claim3_{suffix}_within_condition.csv", index=False)
    pd.DataFrame({"feature": importances.index, "gain": importances.values})\
        .to_csv(C.METRICS / f"claim3_{suffix}_importance.csv", index=False)

    print("\n=== pooled (NOT the verdict — SNR alone explains a lot) ===")
    print(table.round(4).to_string(index=False))
    print("\n=== within-SNR spearman (the honest view) ===")
    print(by_snr.to_string(index=False))
    print("\n=== within-condition x SNR (guards against the pooling artifact) ===")
    print(by_cond.to_string(index=False))
    print("\ntop 12 features (full arm):")
    print(importances.head(12).to_string())

    base = table.set_index("arm")

    def diff(frame, arm, col):
        try:
            return round(float(frame.loc[arm, col] - frame.loc["baseline", col]), 4)
        except Exception:  # noqa: BLE001
            return float("nan")

    def within_diff(arm):
        if by_snr.empty or arm not in by_snr.columns:
            return float("nan")
        return round(float((by_snr[arm] - by_snr["baseline"]).mean()), 4)

    margin = {
        "auc_top10_full_minus_baseline": diff(base, "full", "auc_top10"),
        "auc_top10_featsonly_minus_baseline": diff(base, "feats_only", "auc_top10"),
        "mean_within_snr_full_minus_baseline": within_diff("full"),
        "mean_within_snr_featsonly_minus_baseline": within_diff("feats_only"),
    }
    print("\n=== VERDICT MARGINS (the result is here, not in the pooled table) ===")
    for k, v in margin.items():
        print(f"  {k}: {v:+.4f}" if v == v else f"  {k}: n/a (too few rows per stratum)")
    print("\nPre-hoc constraint to carry into the paper: the predictor is "
          "reference-free at inference, but clean references are needed during "
          "training to build the labels.")
    return {"summary": table, "within_snr": by_snr, "within_condition": by_cond,
            "importance": importances, "margins": margin}


# --------------------------------- Claim 3 precondition ---------------------
def cross_arch_agreement(res: pd.DataFrame) -> pd.DataFrame:
    """
    Is failure input-determined or architecture-specific? If architecture-
    specific, no input-side predictor can exist. Uses the 10-cell evaluation
    matrix (B1 vs B3 on the same rows).
    """
    w = res[res.tag.isin(["b1", "b3"])].copy()
    w["r_over"] = w.e_over / w.e_clean
    p = w.pivot_table(index=["fold", "split", "row_idx", "snr"], columns="tag",
                      values=["r_over", "e_over"]).dropna()
    rows = []
    for (split, snr), g in p.groupby([p.index.get_level_values("split"),
                                      p.index.get_level_values("snr")]):
        a, b = g[("r_over", "b1")], g[("r_over", "b3")]
        k = max(1, int(0.1 * len(g)))
        ov = len(set(a.nlargest(k).index) & set(b.nlargest(k).index)) / k
        rows.append({"split": split, "snr": snr, "n": len(g),
                     "spearman": round(float(spearmanr(a, b).statistic), 3),
                     "top_decile_overlap": round(ov, 2),
                     "x_chance": round(ov / 0.1, 1)})
    out = pd.DataFrame(rows)
    raw = float(spearmanr(p[("e_over", "b1")], p[("e_over", "b3")]).statistic)
    print(out.to_string(index=False))
    print(f"\nraw e_over spearman (rules out the shared-denominator artifact): {raw:.3f}")
    C.ensure_dirs()
    out.to_csv(C.METRICS / "claim3_cross_arch_agreement.csv", index=False)
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Claim 3 verdict")
    p.add_argument("--fold", default="weather", choices=list(C.FAMILIES))
    p.add_argument("--arch", default="b1")
    p.add_argument("--damaging-only", action="store_true",
                   help=f"restrict to {DAMAGING_TYPES} at snr <= {DAMAGING_SNR_MAX}")
    p.add_argument("--precondition", action="store_true",
                   help="run the B1-vs-B3 rank agreement check instead")
    a = p.parse_args(argv)

    if a.precondition:
        from src.evaluate import load_matrix
        cross_arch_agreement(load_matrix())
        return
    run(a.fold, a.arch, a.damaging_only)


if __name__ == "__main__":
    main()
