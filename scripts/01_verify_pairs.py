"""Stage 0.5 — prove ``noise = noisy - clean`` is exact.

If it is not, the whole energy decomposition is unsound. Fix the data, not the
metric. Writes data/manifests/integrity.csv.
"""

from __future__ import annotations

import argparse

import pandas as pd
from tqdm import tqdm

from failure_direction.utils.audio import read, verify_mixture

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifests/inventory.csv")
    ap.add_argument("--out", default="data/manifests/integrity.csv")
    ap.add_argument("--n", type=int, default=500, help="0 = all")
    a = ap.parse_args()

    df = pd.read_csv(a.manifest)
    if a.n:
        df = df.sample(min(a.n, len(df)), random_state=1337)

    rows = []
    for r in tqdm(df.itertuples(), total=len(df)):
        clean, sr = read(r.clean_path)
        noisy, _ = read(r.noisy_path, expect_sr=sr)
        rows.append({"utt_id": r.utt_id, "labelled_snr": r.snr_db, **verify_mixture(clean, noisy)})

    out = pd.DataFrame(rows)
    out.to_csv(a.out, index=False)

    bad = (~out.exact).mean()
    print(f"\nnon-exact mixtures: {bad:.1%}")
    print("measured vs labelled SNR correlation:", out.snr_db.corr(out.labelled_snr).round(3))
    if bad > 0.01:
        print("\nSTOP. The mixture identity does not hold. Request noise stems.")
