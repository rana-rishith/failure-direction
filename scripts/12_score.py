"""Stage 1.3 — per-utterance scoring: signal metrics + direction decomposition + oracle floor.

Writes results/stage1_per_utterance.csv. One row per (model, fold, utterance).
Aggregation happens in 15_aggregate.py, never here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from failure_direction.direction import direction_index, oracle_floor
from failure_direction.metrics.signal import score_pair
from failure_direction.utils.audio import read

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifests/inventory.csv")
    ap.add_argument("--enhanced-dir", required=True, help="dir of enhanced wavs named <utt_id>.wav")
    ap.add_argument("--model", required=True)
    ap.add_argument("--fold", required=True)
    ap.add_argument("--out", default="results/stage1_per_utterance.csv")
    ap.add_argument("--oracle", action="store_true", help="also compute the oracle floor (slow)")
    a = ap.parse_args()

    df = pd.read_csv(a.manifest)
    enh_dir = Path(a.enhanced_dir)
    rows = []

    for r in tqdm(df.itertuples(), total=len(df)):
        wav = enh_dir / f"{r.utt_id}.wav"
        if not wav.exists():
            continue
        clean, sr = read(r.clean_path)
        noisy, _ = read(r.noisy_path, expect_sr=sr)
        out, _ = read(wav, expect_sr=sr)
        noise = noisy[: min(len(noisy), len(clean))] - clean[: min(len(noisy), len(clean))]

        d = direction_index(clean, noise, out)
        row = {
            "model": a.model,
            "fold": a.fold,
            "utt_id": r.utt_id,
            "noise_family": r.noise_family,
            "noise_type": r.noise_type,
            "snr_db": r.snr_db,
            **score_pair(clean, out, sr),
            **d.as_dict(),
        }
        if a.oracle:
            o = oracle_floor(clean, noise)
            row.update({f"oracle_{k}": v for k, v in o.as_dict().items()})
            row["direction_delta"] = d.direction - o.direction
            row["magnitude_delta"] = d.magnitude - o.magnitude
        rows.append(row)

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if out_path.exists():
        new = pd.concat([pd.read_csv(out_path), new], ignore_index=True)
    new.to_csv(out_path, index=False)
    print(f"{len(rows)} rows appended -> {out_path}")
