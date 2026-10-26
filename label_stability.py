"""Claim 3 follow-up: label-stability check (decision rule fixed BEFORE running).

Question
--------
Is r_over a stable per-utterance property under each noise type, or does it
change with the enhancer's training seed? If seeds of the same architecture
disagree on which clips fail, no reference-free predictor can rank them, and
the bubble_curtain failure is a target problem rather than a feature problem.

Pre-committed rule
------------------
stat = median Spearman between seed pairs of the same architecture, computed
       within each (noise_type, SNR) cell on test_matched, pooled over cells
       and pairs for that noise type.
  STABLE    : stat >= 0.50
  UNSTABLE  : stat <  0.30
  AMBIGUOUS : otherwise

Consequence for Claim 3b scope
  STABLE    -> noise type stays in 3b.
  UNSTABLE  -> excluded from 3b, reported as "failure direction not defined
               under this noise" (a finding, stated in the paper).
  AMBIGUOUS -> stays in 3b; no exclusion without evidence.

Commit this file BEFORE running it so the rule is timestamped.

Usage (repo root, faildir env):
  python label_stability.py
  python label_stability.py --root results --pattern "labels_active/**/*test_matched*.csv"
  (r_over is derived as e_over / e_clean when no r_over column exists)
"""
import argparse
import itertools
import re
import sys
from pathlib import Path

import pandas as pd

STABLE, UNSTABLE = 0.50, 0.30
MIN_CELL_N = 20
FULL = False  # set by --full: use e_over_full / e_clean_full

ID_COLS = ["uid", "utt_id", "utt", "id", "clip_id", "file", "path", "noisy_path"]
NT_COLS = ["noise_type", "noise", "condition"]
SNR_COLS = ["snr", "snr_db"]
TAG_RE = re.compile(r"(b1_fsd|b3_fsd|cm_fsd|dfn3|b1|b3)(_s\d+)?", re.I)


def pick(df, cands):
    for c in cands:
        if c in df.columns:
            return c
    return None


def read(p):
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)


def tag_of(path, root):
    matches = list(TAG_RE.finditer(str(path.relative_to(root)).replace("\\", "/")))
    if not matches:
        return None
    m = matches[-1]
    arch = m.group(1).lower()
    seed = int(m.group(2)[2:]) if m.group(2) else 1
    return arch, seed


def load_tables(root, pattern, target, split):
    tables = {}
    rows = []
    shown_cols = False
    for p in sorted(root.glob(pattern)):
        if p.suffix not in {".csv", ".parquet"}:
            continue
        key = tag_of(p, root)
        df = read(p)
        # r_over = over-suppression energy / clean energy. Spearman is rank-based,
        # so this agrees with any monotone transform (log, dB) of the same ratio.
        if target not in df.columns and {"e_over_lv", "e_clean"} <= set(df.columns):
            df[target] = df["e_over_lv"] / df["e_clean"]          # active labels (level target)
        elif target not in df.columns and {"e_over", "e_clean"} <= set(df.columns):
            sfx = "_full" if FULL else ""
            df[target] = df[f"e_over{sfx}"] / df[f"e_clean{sfx}"]  # MarVEN labels
        idc, ntc, snrc = pick(df, ID_COLS), pick(df, NT_COLS), pick(df, SNR_COLS)
        missing = [n for n, v in [("tag", key), (target, target in df.columns),
                                  ("id", idc), ("noise_type", ntc), ("snr", snrc)] if not v]
        ok = not missing
        rows.append((str(p.relative_to(root)), key, len(df),
                     "used" if ok else "skipped: no " + ",".join(missing)))
        if not ok:
            if not shown_cols:
                print(f"\n[first skipped file] {p.name} columns: {list(df.columns)}")
                shown_cols = True
            continue
        if split and "split" in df.columns:
            df = df[df["split"].astype(str) == split]
        t = pd.DataFrame({
            "id": df[idc].astype(str),
            "noise_type": df[ntc].astype(str),
            "snr": pd.to_numeric(df[snrc]).round().astype(int),
            "y": pd.to_numeric(df[target]),
        })
        tables.setdefault(key, []).append(t)
    print("\n=== discovered files ===")
    print(pd.DataFrame(rows, columns=["file", "arch_seed", "rows", "status"]).to_string(index=False))
    return {k: pd.concat(v).drop_duplicates("id") for k, v in tables.items()}


def pair_cells(a, b):
    m = a.merge(b[["id", "y"]], on="id", suffixes=("_a", "_b"))
    out = []
    for (nt, snr), g in m.groupby(["noise_type", "snr"]):
        if len(g) >= MIN_CELL_N:
            out.append((nt, snr, len(g), g["y_a"].corr(g["y_b"], method="spearman")))
    return out


def verdict(x):
    return "STABLE" if x >= STABLE else ("UNSTABLE" if x < UNSTABLE else "AMBIGUOUS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results")
    ap.add_argument("--pattern", default="**/*label*")
    ap.add_argument("--target", default="r_over")
    ap.add_argument("--split", default="test_matched")
    ap.add_argument("--out", default="results/label_stability")
    ap.add_argument("--full", action="store_true", help="derive r_over from the *_full energies")
    a = ap.parse_args()
    global FULL
    FULL = a.full

    root = Path(a.root)
    tables = load_tables(root, a.pattern, a.target, a.split)

    by_arch = {}
    for (arch, seed), t in tables.items():
        by_arch.setdefault(arch, {})[seed] = t

    rows = []
    for arch, seeds in by_arch.items():
        for s1, s2 in itertools.combinations(sorted(seeds), 2):
            for nt, snr, n, rho in pair_cells(seeds[s1], seeds[s2]):
                rows.append((arch, f"s{s1}-s{s2}", nt, snr, n, rho))

    if not rows:
        sys.exit("\nNo seed pairs found. Check --root/--pattern/--target against the file list above.")

    cells = pd.DataFrame(rows, columns=["arch", "pair", "noise_type", "snr", "n", "rho"])

    per_arch = (cells.groupby(["noise_type", "arch"])["rho"]
                .agg(median="median", frac_pos=lambda r: (r > 0).mean(), cells="size")
                .reset_index())
    summary = (cells.groupby("noise_type")["rho"]
               .agg(median="median", frac_pos=lambda r: (r > 0).mean(), cells="size")
               .reset_index())
    summary["verdict"] = summary["median"].map(verdict)

    pd.set_option("display.width", 200)
    print("\n=== seed-to-seed label agreement, per noise type x arch (descriptive) ===")
    print(per_arch.round(3).to_string(index=False))
    print(f"\n=== VERDICT per noise type (STABLE >= {STABLE}, UNSTABLE < {UNSTABLE}) ===")
    print(summary.round(3).to_string(index=False))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cells.to_csv(out / "cells.csv", index=False)
    per_arch.to_csv(out / "per_arch.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    print(f"\nsaved {out.resolve()}")


if __name__ == "__main__":
    main()
