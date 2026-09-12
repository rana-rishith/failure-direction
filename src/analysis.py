"""
Claims 1 and 2, plus the pre-committed gates.

    python -m src.analysis

Writes every table to results/metrics/*.csv so the paper can cite a file rather
than a scrollback buffer.

Reporting rules that came out of the Stage 2 run and are enforced here:
  * Pooling masks real effects. Every table is conditioned on split and, where
    it matters, on SNR. A single pooled number averages a 369x separation with a
    6.6x one.
  * r_under is heavy-tailed (values above 1 are arithmetic, not a bug) — report
    medians and IQRs, not means.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import yaml

import config as C
from src import metrics as MT

TRAINED = ("b1", "b3")


def _save(frame, name: str):
    C.ensure_dirs()
    path = C.METRICS / name
    frame.to_csv(path)
    print(f"  -> {path.name}")
    return frame


def prepare(res: pd.DataFrame) -> pd.DataFrame:
    """Attach r_over / r_under / dir_idx / mag using the canonical sign convention."""
    return MT.add_ratios(res)


# --------------------------------------------------------------- claim 1 -----
def claim1(res: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = res[res.tag.isin(TRAINED)]
    piv = t.pivot_table(index=["tag", "fold"], columns="split",
                        values=["si_sdr_out", "stoi_out", "pesq_out"], aggfunc="mean")
    gaps = pd.DataFrame({
        "si_sdr_gap": piv[("si_sdr_out", "test_matched")] - piv[("si_sdr_out", "test_unseen")],
        "stoi_gap": piv[("stoi_out", "test_matched")] - piv[("stoi_out", "test_unseen")],
    }).round(3)

    by_snr = t.pivot_table(index="snr", columns="split", values="si_sdr_out",
                           aggfunc="mean").round(3)
    by_snr["unseen_minus_snr"] = (by_snr["test_unseen"] - by_snr.index).round(3)

    floor = res[res.tag == "b4"].groupby("split")[["si_sdr_out", "stoi_out", "pesq_out"]]\
        .mean().round(3)

    print("\n=== Claim 1: matched - unseen, per model per fold ===")
    print(gaps.to_string())
    print("\n--- output tracks input SNR on unseen (the passthrough signature) ---")
    print(by_snr.to_string())
    print("\n--- B4 passthrough floor ---")
    print(floor.to_string())

    _save(gaps, "claim1_gaps.csv")
    _save(by_snr, "claim1_si_sdr_by_snr.csv")
    _save(floor, "claim1_b4_floor.csv")
    return {"gaps": gaps, "by_snr": by_snr, "floor": floor}


# --------------------------------------------------------------- claim 2 -----
def claim2(res: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = res[res.tag.isin(TRAINED)]

    med = t.groupby(["tag", "split"])[["r_over", "r_under"]].median().round(4)
    med["ratio"] = np.where(
        med.r_over > med.r_under,
        (med.r_over / med.r_under).round(1),
        (med.r_under / med.r_over).round(1),
    )
    med["dominant"] = np.where(med.r_over > med.r_under, "over", "under")

    per_snr = t.pivot_table(index="snr", columns="split",
                            values=["r_over", "r_under"], aggfunc="median").round(4)
    raw = t.groupby(["tag", "split"])[["e_over", "e_under", "e_clean"]].mean().round(2)
    unseen_snr = t[t.split == "test_unseen"].groupby("snr")[["e_over", "e_under"]]\
        .mean().round(1)

    # r_under is largely an SNR readout — any Claim 3 work on it must show
    # incremental value after conditioning on SNR.
    u = t[t.split == "test_unseen"]
    corr = float(np.corrcoef(np.log10(u.e_under + 1e-12), -u.snr)[0, 1])

    print("\n=== Claim 2: direction flip (medians, pooled across folds) ===")
    print(med.to_string())
    print("\n--- flip survives per-SNR conditioning ---")
    print(per_snr.to_string())
    print(f"\ncorr(log10 e_under, -snr) on unseen = {corr:.3f}  "
          "(high -> r_under is close to an SNR meter; r_over is the better target)")

    _save(med, "claim2_direction_medians.csv")
    _save(per_snr, "claim2_ratios_by_snr.csv")
    _save(raw, "claim2_raw_energy_means.csv")
    _save(unseen_snr, "claim2_unseen_energy_by_snr.csv")
    with open(C.METRICS / "claim2_snr_readout.txt", "w") as f:
        f.write(f"corr(log10 e_under, -snr) = {corr:.6f}\n")
    return {"medians": med, "by_snr": per_snr, "raw": raw, "corr_e_under_snr": corr}


# ----------------------------------------------------------------- gates -----
def load_gate_config(path=None) -> dict:
    path = path or (C.REPO / "configs" / "gate.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def gates(res: pd.DataFrame, cfg: dict | None = None) -> dict:
    cfg = cfg or load_gate_config()
    t = res[res.tag.isin(TRAINED)]
    out: dict[str, dict] = {}

    # ---- G1: direction spread across the five noise types ------------------
    thr1 = cfg["G1"]["threshold"]
    pooled = t.groupby("noise_type").dir_idx.mean().round(4)
    cond = t.pivot_table(index="noise_type", columns="split", values="dir_idx",
                         aggfunc="mean").round(3)
    within = (cond.max() - cond.min()).round(3).to_dict()
    separation = round(float(cond["test_matched"].min() - cond["test_unseen"].max()), 3)
    spread1 = round(float(pooled.max() - pooled.min()), 4)
    out["G1"] = {
        "threshold": thr1,
        "pooled_spread": spread1,
        "within_split_spread": within,
        "matched_to_unseen_separation_POSTHOC": separation,
        "verdict": "PASS" if spread1 >= thr1 else "FAIL",
        "note": "The gate points at the wrong axis: it tests whether direction "
                "varies across NOISE TYPES, while the hypothesis was that SEEN "
                "conditions fail differently from UNSEEN ones. Report it as "
                "specified, report the split-conditioned version, and flag the "
                "matched-to-unseen separation as post-hoc.",
    }
    print("\n=== G1 (spread across noise types) ===")
    print(pooled.to_string())
    print(f"pooled spread {out['G1']['pooled_spread']} vs threshold {thr1}")
    print(cond.to_string())
    print(f"within-split spreads {within} | matched-to-unseen separation "
          f"{separation} (post-hoc, flag it as such)")
    _save(cond, "gate_g1_dir_idx_by_noise_split.csv")

    # ---- G2: magnitude gap -------------------------------------------------
    thr2 = cfg["G2"]["threshold"]
    g2 = t.groupby("split").mag.agg(["mean", "median"]).round(4)
    gap_mean = round(float(g2.loc["test_unseen", "mean"] - g2.loc["test_matched", "mean"]), 3)
    gap_med = round(float(g2.loc["test_unseen", "median"] - g2.loc["test_matched", "median"]), 3)
    out["G2"] = {"threshold": thr2, "gap_mean": gap_mean, "gap_median": gap_med,
                 "verdict": "PASS" if gap_med >= thr2 else "FAIL",
                 "note": "report the median as primary; the mean is inflated by "
                         "r_under's tail at negative SNR"}
    print("\n=== G2 (magnitude gap, unseen - matched) ===")
    print(g2.to_string())
    print(f"gap mean {gap_mean} | median {gap_med} | threshold {thr2} -> {out['G2']['verdict']}")
    _save(g2, "gate_g2_magnitude.csv")

    # ---- G3: direction/condition collinearity ------------------------------
    b1 = t[t.tag == "b1"]
    lo = b1.nsmallest(200, "dir_idx")
    hi = b1.nlargest(200, "dir_idx")
    tm = b1[b1.split == "test_matched"]
    overlap = []
    for s in sorted(b1.snr.unique()):
        a = b1[(b1.split == "test_matched") & (b1.snr == s)]
        b = b1[(b1.split == "test_unseen") & (b1.snr == s)]
        overlap.append({"snr": s,
                        "matched_dir_lt0": int((a.dir_idx < 0).sum()), "n_matched": len(a),
                        "unseen_dir_gt0": int((b.dir_idx > 0).sum()), "n_unseen": len(b)})
    ov = pd.DataFrame(overlap).set_index("snr")
    collinear = 1 - (int((tm.dir_idx < 0).sum()) / max(len(tm), 1))
    out["G3"] = {
        "threshold": cfg["G3"]["threshold"],
        "under_dominant_split_mix": lo.split.value_counts().to_dict(),
        "over_dominant_split_mix": hi.split.value_counts().to_dict(),
        "matched_rows_with_negative_dir_idx": int((tm.dir_idx < 0).sum()),
        "matched_rows": int(len(tm)),
        "collinearity": round(float(collinear), 4),
        "verdict": ("UNTESTABLE" if collinear >= cfg["G3"].get("max_collinearity", 0.95)
                    else "TESTABLE"),
        "note": "A WER contrast between direction extremes measures matched "
                "against unseen and restates Claim 1 in WER units. Usable "
                "overlap exists only at the highest SNR, where the absolute "
                "failures are too small for the 0.05 threshold to be plausible. "
                "The direction extremes also saturate at +/-1, so they are "
                "degenerate rather than graded failures.",
    }
    print("\n=== G3 (WER asymmetry by direction) ===")
    print(f"under-dominant split mix: {out['G3']['under_dominant_split_mix']}")
    print(f"over-dominant split mix:  {out['G3']['over_dominant_split_mix']}")
    print(f"matched rows with dir_idx<0: {out['G3']['matched_rows_with_negative_dir_idx']}"
          f"/{len(tm)}  -> collinearity {out['G3']['collinearity']:.3f}")
    print(ov.to_string())
    _save(ov, "gate_g3_overlap_by_snr.csv")

    with open(C.METRICS / "gate_results.yaml", "w") as f:
        yaml.safe_dump(out, f, sort_keys=False)
    print(f"\n  -> gate_results.yaml")
    print("\nGate integrity note for the paper: G1's index formula and G2's "
          "definition of 'mean magnitude' were operationalised AFTER Claims 1 and 2 "
          "had been observed, because gate.yaml left them unspecified. Disclose it.")
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Claims 1-2 and gate evaluation")
    p.add_argument("--matrix", default=None, help="path to an eval matrix CSV")
    a = p.parse_args(argv)

    from src.evaluate import load_matrix
    res = pd.read_csv(a.matrix) if a.matrix else load_matrix()
    res = prepare(res)
    print(f"loaded {len(res)} evaluation rows | "
          f"NaN si_sdr_out {int(res.si_sdr_out.isna().sum())} | "
          f"NaN pesq_out {int(res.pesq_out.isna().sum())}")
    claim1(res)
    claim2(res)
    gates(res)


if __name__ == "__main__":
    main()
