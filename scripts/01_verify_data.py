"""
Stage 1 — dataset verification. Run before any training.

    python scripts/01_verify_data.py --sample 300

A file-not-found on the first training batch looks like a code bug and is not
one, so the disk check comes first. The fold report is the second half: it is
what proves the cross-condition splits are family- AND speaker-disjoint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402
from src import data as D  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=300, help="files to stat-check")
    a = p.parse_args()

    C.ensure_dirs()
    C.require_dataset()
    df = D.load_manifest(verbose=True)

    print("\nnoise types:")
    print(df.groupby(["family", "noise_type"]).size().to_string())
    print("\nSNR levels:", sorted(df.target_snr_db.unique()))
    print("rows per SNR:", df.groupby("target_snr_db").size().to_dict())
    print("\nshipped split (speaker-disjoint, but every noise type is in every split "
          "— which is exactly why the folds are rebuilt):")
    print(df.pivot_table(index="split", columns="noise_type", values="uid",
                         aggfunc="count").fillna(0).astype(int).to_string())

    if "measured_snr_db" in df.columns:
        dev = float((df.measured_snr_db - df.target_snr_db).abs().max())
        print(f"\nmax |measured - target| SNR: {dev:.4f} "
              "(0 means mixing is synthetic and exact; ignore the measured column)")

    appearances = df.key.value_counts()
    print(f"\nutterance appearances: min {appearances.min()} max {appearances.max()} "
          f"(MarVEN's sampled design puts every utterance in exactly 2 rows — "
          "so the direction index cannot be compared within-utterance across conditions)")

    print("\ndisk check:")
    v = D.verify_disk(df, n=a.sample)
    print(" ", v)
    if v["missing_noisy"] or v["missing_clean"]:
        print("FAIL: files referenced by the manifest are missing — the download is "
              "incomplete. Resolve this before anything else.")
        return 1
    if not v["first_pair_aligned"]:
        print("FAIL: first noisy/clean pair has mismatched lengths")
        return 1

    print("\nfolds:")
    folds = D.build_folds(df)
    print(D.fold_report(folds).to_string(index=False))
    print("\nall leakage assertions passed (speaker, noise type, utterance tuple, val)")

    a_keys = set(folds["weather"]["test_matched"].uid)
    b_keys = set(folds["anthro"]["test_unseen"].uid)
    print(f"paired-comparison check: weather/test_matched == anthro/test_unseen -> "
          f"{a_keys == b_keys} ({len(a_keys)} rows)")

    rep = D.fold_report(folds)
    rep.to_csv(C.METRICS / "fold_report.csv", index=False)
    print(f"\nwrote {C.METRICS / 'fold_report.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
