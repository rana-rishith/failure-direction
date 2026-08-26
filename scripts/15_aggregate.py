"""Stage 1.4 — the four analyses. Reads per-utterance CSV, writes tables and figures.

Aggregation is the ONLY place means are taken. If a mean appears earlier in the
pipeline, that is a bug.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/stage1_per_utterance.csv")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    df = pd.read_csv(a.results)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"rows: {len(df)}   NaN counts:\n{df.isna().sum()[lambda s: s > 0]}\n")

    # A1 — does direction separate by noise type?
    a1 = df.groupby(["model", "noise_type"])[["direction", "magnitude"]].agg(["mean", "std"])
    a1.to_csv(out / "a1_direction_by_noise_type.csv")

    # A2 — matched vs shifted, per model
    a2 = df.groupby(["model", "fold", "noise_family"])[["direction", "magnitude"]].mean()
    a2.to_csv(out / "a2_matched_vs_shifted.csv")

    # A3 — SNR sweep against the oracle floor
    cols = [c for c in ["direction", "magnitude", "direction_delta", "magnitude_delta"] if c in df]
    a3 = df.groupby(["model", "snr_db"])[cols].mean()
    a3.to_csv(out / "a3_snr_sweep.csv")

    # A4 — does direction predict downstream cost? (the asymmetry check)
    if "wer" in df:
        df["dir_bucket"] = pd.cut(df.direction, [-1.01, -0.2, 0.2, 1.01],
                                  labels=["over", "balanced", "under"])
        a4 = df.groupby(["model", "dir_bucket"])[["wer", "pesq", "stoi", "si_sdr"]].mean()
        a4.to_csv(out / "a4_wer_by_direction.csv")
        print(a4)
    else:
        print("no WER column — G3 is unevaluable, record that decision explicitly")

    print(f"\nwrote 3-4 tables to {out}")
