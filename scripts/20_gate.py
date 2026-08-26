"""Stage 1 exit — evaluate the pre-committed go/no-go gate. Run ONCE.

Thresholds live in configs/gate.yaml and must be committed to git BEFORE this
script is first run. The script records the decision with a timestamp so that
the commit history proves the thresholds were not tuned after seeing results.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd
import yaml

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/stage1_per_utterance.csv")
    ap.add_argument("--gate", default="configs/gate.yaml")
    ap.add_argument("--out", default="results/gate_decision.json")
    a = ap.parse_args()

    if Path(a.out).exists():
        raise SystemExit(f"{a.out} already exists. The gate is evaluated once. Do not re-run.")

    cfg = yaml.safe_load(Path(a.gate).read_text())
    df = pd.read_csv(a.results)

    spread = df.groupby("noise_type").direction.mean()
    g1 = bool((spread.max() - spread.min()) >= cfg["g1_direction_spread"])

    shift = df[df.fold.str.contains("cross", na=False)]
    g2 = bool(
        (shift.magnitude.mean() - df[~df.index.isin(shift.index)].magnitude.mean())
        >= cfg["g2_shift_gap"]
    )

    over = df[df.direction < 0]
    under = df[df.direction > 0]
    g3 = None
    if "wer" in df:
        g3 = bool((over.wer.mean() - under.wer.mean()) >= cfg["g3_wer_asymmetry"])

    decision = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "thresholds": cfg,
        "G1_direction_separable": g1,
        "G2_shift_visible": g2,
        "G3_asymmetry_consequential": g3,
        "verdict": (
            "proceed to Claim 3"
            if g1 and g2 and g3
            else "proceed, demote asymmetry to 'measurable'"
            if g1 and g2
            else "STOP — diagnose before building the predictor"
        ),
    }
    Path(a.out).write_text(json.dumps(decision, indent=2))
    print(json.dumps(decision, indent=2))
