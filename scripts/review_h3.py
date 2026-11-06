"""Claim 3 additions asked for by the 12 Oct deep review (concerns 1 and 6).

    python review_h3.py baselines   # feats-only as headline, ridge / best-single / WADA baselines
    python review_h3.py transfer    # predictor trained on some noise types, tested on a held-out one
    python review_h3.py routing     # bypass-the-enhancer simulation on the B1 matched WER set

Everything is scored INSIDE strata (SNR, and noise type x SNR), where the oracle
SNR column is constant, so no arm gets credit for recovering the SNR sweep.
AUPRC / ROC use positives = top decile of y within the stratum (chance AUPRC 0.10).
Needs pandas, numpy, scipy, scikit-learn, lightgbm. Reads results/{labels,features,
predictions}; writes results/metrics/review_h3_*.csv.
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

R, M = "results", "results/metrics"
SEED = 1234
NOT_FEAT = {"fold", "split", "row_idx", "uid", "y", "snr", "noise_type", "speaker_id"}


def joined(fold, split, arch="b1"):
    L = pd.read_csv(f"{R}/labels/{arch}__{fold}__{split}.csv")
    F = pd.read_csv(f"{R}/features/{fold}__{split}.csv")
    d = L.merge(F, on=["fold", "split", "row_idx"], suffixes=("", "_f"), validate="1:1")
    assert (d.uid == d.uid_f).all(), "label/feature misalignment"
    d["y"] = np.log10(d.e_over / d.e_clean + 1e-8)
    return d


def feat_cols(d):
    lab = {"tag", "chapter_id", "utterance_id", "duration_sec", "uid_f"}
    return [c for c in d.columns if c not in NOT_FEAT | lab
            and not c.startswith(("e_", "r_")) and c != "y"]


def strat_scores(t, arms, by):
    rows = []
    for k, g in t.groupby(by):
        if len(g) < 25:
            continue
        pos = (g.y >= g.y.quantile(0.9)).to_numpy()
        rec = dict(zip(by, k if isinstance(k, tuple) else (k,)), n=len(g))
        for a in arms:
            p = g[a].to_numpy()
            rec[f"rho_{a}"] = spearmanr(p, g.y).statistic
            rec[f"auprc_{a}"] = average_precision_score(pos, p) if 0 < pos.sum() < len(pos) else np.nan
            rec[f"roc_{a}"] = roc_auc_score(pos, p) if 0 < pos.sum() < len(pos) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def lgbm(tr, va, cols):
    import lightgbm as lgb
    m = lgb.LGBMRegressor(n_estimators=2000, learning_rate=0.03, num_leaves=31,
                          min_child_samples=40, subsample=0.8, colsample_bytree=0.8,
                          random_state=SEED, verbose=-1)
    try:
        m.fit(tr[cols], tr.y, eval_X=va[cols], eval_y=va.y,
              callbacks=[lgb.early_stopping(100, verbose=False)])
    except TypeError:
        m.fit(tr[cols], tr.y, eval_set=[(va[cols], va.y)],
              callbacks=[lgb.early_stopping(100, verbose=False)])
    return m


def best_single(tr, cols):
    """Feature with the highest mean |within-SNR Spearman| on TRAIN; sign from train."""
    best = None
    for c in cols:
        r = [spearmanr(g[c], g.y).statistic for _, g in tr.groupby("snr") if g[c].nunique() > 1]
        s = np.nanmean(r)
        if best is None or abs(s) > abs(best[1]):
            best = (c, s)
    return best


def baselines():
    wada = pd.read_csv(f"{R}/features/wada_snr.csv")[["uid", "wada_snr"]]
    summary, cells_all = [], []
    for fold in ("weather", "anthro"):
        tr, va = joined(fold, "train"), joined(fold, "val")
        te = joined(fold, "test_matched")
        P = pd.read_csv(f"{R}/predictions/claim3_{fold}_preds.csv")
        assert (P.uid.values == te.uid.values).all()
        cols = feat_cols(tr)
        assert len(cols) == 33, cols
        t = te[["uid", "noise_type", "snr", "y", "log_e_noisy"]].copy()
        for a in ("baseline", "full", "feats_only"):
            t[a] = P[f"pred_{a}"].values
        rid = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13)))
        rid.fit(pd.concat([tr, va])[cols], pd.concat([tr, va]).y)
        t["ridge33"] = rid.predict(te[cols])
        c, s = best_single(tr, cols)
        t["best_single"] = np.sign(s) * te[c].values
        vw = va.merge(wada, on="uid")
        sgn = np.sign(np.nanmean([spearmanr(g.wada_snr, g.y).statistic for _, g in vw.groupby("snr")]))
        t = t.merge(wada, on="uid", how="left")
        t["wada"] = sgn * t.wada_snr
        t["log_e_only"] = t.log_e_noisy
        arms = ["baseline", "log_e_only", "wada", "best_single", "ridge33", "feats_only", "full"]
        for by, lvl in ((["snr"], "snr"), (["noise_type", "snr"], "cell")):
            s_ = strat_scores(t, arms, by)
            s_.insert(0, "level", lvl); s_.insert(0, "fold", fold)
            cells_all.append(s_)
            row = {"fold": fold, "level": lvl, "n_strata": len(s_), "best_single_feature": c}
            for a in arms:
                row[f"rho_{a}"] = s_[f"rho_{a}"].mean()
                row[f"auprc_{a}"] = s_[f"auprc_{a}"].mean()
                row[f"roc_{a}"] = s_[f"roc_{a}"].mean()
            row["feats_only_beats_baseline"] = int((s_.rho_feats_only > s_.rho_baseline).sum())
            row["feats_only_beats_ridge33"] = int((s_.rho_feats_only > s_.rho_ridge33).sum())
            row["feats_only_beats_wada"] = int((s_.rho_feats_only > s_.rho_wada).sum())
            row["min_abs_rho_feats_only"] = s_.rho_feats_only.min()
            row["max_abs_rho_feats_only"] = s_.rho_feats_only.max()
            summary.append(row)
    S = pd.DataFrame(summary)
    S.to_csv(f"{M}/review_h3_baselines_summary.csv", index=False)
    pd.concat(cells_all).to_csv(f"{M}/review_h3_baselines_strata.csv", index=False)
    pd.set_option("display.width", 250)
    for lvl in ("snr", "cell"):
        X = S[S.level == lvl].set_index("fold")
        print(f"\n== mean over {lvl} strata ==")
        for k in ("rho", "auprc", "roc"):
            print(X[[c for c in X.columns if c.startswith(k + "_")]].round(3).to_string())
        print(X[["n_strata", "best_single_feature", "feats_only_beats_baseline",
                 "feats_only_beats_ridge33", "feats_only_beats_wada",
                 "min_abs_rho_feats_only", "max_abs_rho_feats_only"]].round(3).to_string())


def transfer():
    """Enhancer = the full-fold B1 (heard every type). The PREDICTOR never sees the
    held-out type: trained on train/val rows of the other types, tested on the
    held-out type's test rows. Tests whether input-side damage prediction carries
    to a noise recording the predictor has not seen."""
    out = []
    for fold, types in (("weather", ("rainfall", "lightning", "hurricane")),
                        ("anthro", ("bubble_curtain", "large_commercial_ship"))):
        tr, va, te = (joined(fold, s) for s in ("train", "val", "test_matched"))
        cols = feat_cols(tr)
        for h in types:
            a, b, c = (d[d.noise_type != h] for d in (tr, va)), None, te[te.noise_type == h]
            tra, vaa = a
            t = c[["uid", "noise_type", "snr", "y"]].copy()
            t["feats_only"] = lgbm(tra, vaa, cols).predict(c[cols])
            t["baseline"] = lgbm(tra, vaa, ["snr", "log_e_noisy"]).predict(c[["snr", "log_e_noisy"]])
            # in-type reference: same predictor family trained WITH the held-out type
            t["feats_only_in_type"] = lgbm(tr, va, cols).predict(c[cols])
            s_ = strat_scores(t, ["baseline", "feats_only", "feats_only_in_type"], ["snr"])
            s_.insert(0, "held_out", h); s_.insert(0, "fold", fold)
            out.append(s_)
            print(f"{fold}/{h}: mean within-SNR rho  baseline {s_.rho_baseline.mean():.3f}  "
                  f"feats_only(held-out) {s_.rho_feats_only.mean():.3f}  "
                  f"feats_only(in-type) {s_.rho_feats_only_in_type.mean():.3f}  "
                  f"| feats>baseline in {(s_.rho_feats_only > s_.rho_baseline).sum()}/{len(s_)} SNRs "
                  f"| AUPRC {s_.auprc_feats_only.mean():.3f} vs base {s_.auprc_baseline.mean():.3f}",
                  flush=True)
    pd.concat(out).to_csv(f"{M}/review_h3_transfer.csv", index=False)


def routing():
    """B1, matched noise, SNR <= -5 (the only rows with WER). Per utterance choose the
    enhanced or the noisy input; corpus WER = sum(errors) / sum(reference words)."""
    w = pd.read_csv(f"{R}/wer_snrmax-5.csv")
    P = pd.concat([pd.read_csv(f"{R}/predictions/claim3_{f}_preds.csv") for f in ("weather", "anthro")])
    d = w.merge(P[["uid", "pred_feats_only", "pred_baseline", "y"]], left_on="row_key", right_on="uid")
    print(f"WER rows {len(w)}, with predictions {len(d)}")
    n = d.n_ref.sum()

    def wer(use_noisy):
        return 100 * np.where(use_noisy, d.err_noisy, d.err_b1_matched).sum() / n

    rows = [{"policy": "always enhance", "k": 0, "wer": wer(np.zeros(len(d), bool))},
            {"policy": "never enhance", "k": 100, "wer": wer(np.ones(len(d), bool))},
            {"policy": "oracle per utterance", "k": np.nan,
             "wer": wer((d.err_noisy < d.err_b1_matched).to_numpy())}]
    for score in ("pred_feats_only", "pred_baseline", "y"):
        for k in (5, 10, 20, 30, 50):
            # bypass the top-k% predicted r_over within each SNR level (no SNR leakage)
            thr = d.groupby("snr")[score].transform(lambda s: s.quantile(1 - k / 100))
            rows.append({"policy": f"bypass top-k by {score}", "k": k, "wer": wer((d[score] >= thr).to_numpy())})
    r = pd.DataFrame(rows)
    r.to_csv(f"{M}/review_h3_routing.csv", index=False)
    print(r.round(2).to_string(index=False))
    gain = (d.err_noisy - d.err_b1_matched)
    print("\nrows where enhancement hurts:", int((gain < 0).sum()), "helps:", int((gain > 0).sum()),
          "ties:", int((gain == 0).sum()))
    print("spearman(pred_feats_only, enhanced - noisy errors) within SNR:",
          [round(spearmanr(g.pred_feats_only, g.err_b1_matched - g.err_noisy).statistic, 3)
           for _, g in d.groupby("snr")])


if __name__ == "__main__":
    {"baselines": baselines, "transfer": transfer, "routing": routing}[sys.argv[1]]()
