"""Stage 0.6 — cross-family, speaker-disjoint folds."""

from __future__ import annotations

import argparse

from failure_direction.data.splits import cross_family_splits

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifests/inventory.csv")
    ap.add_argument("--out", default="data/splits")
    ap.add_argument("--seed", type=int, default=1337)
    a = ap.parse_args()
    cross_family_splits(a.manifest, a.out, seed=a.seed)
