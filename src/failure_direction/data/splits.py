"""Cross-family splits. Train on one noise family, test on the other.

Speaker-disjoint as well as family-disjoint: if the same speaker appears on both
sides, a shift result is partly a memorisation result and a reviewer will say so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def cross_family_splits(
    manifest: str | Path,
    out_dir: str | Path = "data/splits",
    val_frac: float = 0.1,
    seed: int = 1337,
) -> dict:
    df = pd.read_csv(manifest)
    families = sorted(df["noise_family"].unique())
    if len(families) != 2:
        raise ValueError(f"expected 2 noise families, found {families}")

    rng = pd.Series(sorted(df["speaker_id"].unique())).sample(frac=1.0, random_state=seed)
    n_val = max(1, int(len(rng) * val_frac))
    val_speakers = set(rng.iloc[:n_val])

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    folds = {}

    for train_fam in families:
        test_fam = [f for f in families if f != train_fam][0]
        tr = df[(df.noise_family == train_fam) & (~df.speaker_id.isin(val_speakers))]
        va = df[(df.noise_family == train_fam) & (df.speaker_id.isin(val_speakers))]
        te = df[df.noise_family == test_fam]

        fold = {
            "train_family": train_fam,
            "test_family": test_fam,
            "train": tr.utt_id.tolist(),
            "val": va.utt_id.tolist(),
            "test": te.utt_id.tolist(),
            "val_speakers": sorted(val_speakers),
            "seed": seed,
        }
        path = out_dir / f"fold_train-{train_fam}.json"
        path.write_text(json.dumps(fold, indent=2))
        folds[train_fam] = fold
        print(f"{path.name}: train={len(tr)} val={len(va)} test={len(te)}")

    return folds
