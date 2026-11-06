"""Descriptive bootstrap CIs for the paper's headline numbers (tasks C1 and C2).

    python scripts/bootstrap_ci.py --task hp1        # C2, paired, H_P1
    python scripts/bootstrap_ci.py --task headline   # C1, four quantity families
    python scripts/bootstrap_ci.py --task all

Every CI here is DESCRIPTIVE. No gate rule reads one, and no verdict file is
touched. The registered verdicts stand on the point estimates they were
registered against; these intervals only say how firmly the data holds them.

The resampling unit is the base utterance, never the row: rows that share a base
utterance are not independent, so a row bootstrap understates the width.

src.probe.bootstrap_ci already does a cluster bootstrap of the median, but only
of one median over one value column. H_P1 is a DIFFERENCE of two medians taken
over disjoint subsets of the same resampled bases, which that signature cannot
express, so the draw loop is written out here and reused for both tasks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from src.xcorpus import HEARD_P, OUT, PAIRED, UNSEEN_P, _derive  # noqa: E402

N_BOOT, SEED, ALPHA = 10_000, 1234, 0.05
CI = C.EVAL / "ci"


def _pad(groups: list[np.ndarray]) -> np.ndarray:
    """Groups of unequal length as one NaN-padded array, so a draw is one index."""
    w = max(len(g) for g in groups)
    out = np.full((len(groups), w), np.nan)
    for i, g in enumerate(groups):
        out[i, :len(g)] = g
    return out


def _draws(n_groups: int, n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n_groups, size=(n, n_groups))


def _quantiles(v: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return (np.nan, np.nan)
    return (float(np.quantile(v, alpha / 2)), float(np.quantile(v, 1 - alpha / 2)))


def median_ci(values: np.ndarray, by: np.ndarray, n: int = N_BOOT,
              seed: int = SEED) -> tuple[float, float, float, int, int]:
    """Cluster bootstrap of a median. Returns (point, lo, hi, n_rows, n_groups)."""
    ok = np.isfinite(values)
    values, by = np.asarray(values)[ok], np.asarray(by)[ok]
    if len(values) < 2:
        return (np.nan, np.nan, np.nan, len(values), 0)
    keys = pd.unique(by)
    pad = _pad([values[by == k] for k in keys])
    point = float(np.median(values))
    meds = []
    for lo in range(0, n, 500):                    # chunked: pad[pick] is the peak
        pick = _draws(len(keys), min(500, n - lo), seed + lo)
        meds.append(np.nanmedian(pad[pick].reshape(len(pick), -1), axis=1))
    lo_q, hi_q = _quantiles(np.concatenate(meds))
    return (point, lo_q, hi_q, len(values), len(keys))


def diff_of_medians_ci(a_groups: list[np.ndarray], b_groups: list[np.ndarray],
                       n: int = N_BOOT, seed: int = SEED
                       ) -> tuple[float, float, float, np.ndarray]:
    """Cluster bootstrap of median(a) - median(b), the SAME group draw applied to
    both sides. That is what makes it paired: a base utterance enters or leaves a
    resample with all of its conditions at once, so the two medians move together
    and the interval carries only the between-base variation.
    """
    A, B = _pad(a_groups), _pad(b_groups)
    point = float(np.nanmedian(A) - np.nanmedian(B))
    out = []
    for lo in range(0, n, 500):
        pick = _draws(len(a_groups), min(500, n - lo), seed + lo)
        m = len(pick)
        out.append(np.nanmedian(A[pick].reshape(m, -1), axis=1)
                   - np.nanmedian(B[pick].reshape(m, -1), axis=1))
    draws = np.concatenate(out)
    lo_q, hi_q = _quantiles(draws)
    return (point, lo_q, hi_q, draws)


# ------------------------------------------------------------------- C2: H_P1 ---
def hp1(model: str = "sgmse", n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """H_P1 = median d_g on unseen corpora minus median d_g on heard corpora,
    over the base rows that carry all PAIRED conditions. Registered cutoff 0.20
    on |delta| (src/xn2.py:161). Post-hoc: this does not re-decide the gate.
    """
    e = _derive(pd.read_csv(OUT / f"ext_{model}.csv"))
    pb = e[e.cond.isin(PAIRED)]
    full = pb.groupby("base_uid").cond.nunique()
    keep = full[full == len(PAIRED)].index
    pb = pb[pb.base_uid.isin(keep)]

    bases = list(keep)
    unseen = [pb[(pb.base_uid == b) & pb.cond.isin(UNSEEN_P)].d_g.to_numpy() for b in bases]
    heard = [pb[(pb.base_uid == b) & pb.cond.isin(HEARD_P)].d_g.to_numpy() for b in bases]
    point, lo, hi, draws = diff_of_medians_ci(unseen, heard, n=n, seed=seed)

    # Self-check: the point estimate must reproduce the committed verdict exactly,
    # or this script is not measuring the registered quantity.
    reg = pd.read_csv(OUT / "report2" / f"H_P_{model}.csv").H_P1_delta.iloc[0]
    assert abs(point - reg) < 1e-9, f"H_P1 point {point} != registered {reg}"

    # The rule is two-sided on |delta|, so "fully past" means every point of the
    # interval clears the cutoff on the same side.
    cut = 0.20
    fully = bool((lo <= -cut and hi <= -cut) or (lo >= cut and hi >= cut))
    return pd.DataFrame([{
        "quantity": f"H_P1_delta_{model}", "unit": "paired base utterance",
        "n_base": len(bases), "n_rows": len(pb),
        "point": point, "ci_lo": lo, "ci_hi": hi,
        "cutoff": cut, "ci_fully_past_cutoff": fully,
        "frac_draws_past_cutoff": float(np.mean(np.abs(draws) >= cut)),
        "frac_draws_model_trait": float(np.mean(np.abs(draws) < 0.10)),
        "n_boot": n, "seed": seed, "post_hoc": True,
    }])


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=("hp1", "headline", "all"), default="all")
    p.add_argument("--n-boot", type=int, default=N_BOOT)
    a = p.parse_args(argv)
    CI.mkdir(parents=True, exist_ok=True)

    if a.task in ("hp1", "all"):
        t = hp1(n=a.n_boot)
        out = CI / "hp1_paired_ci.csv"
        t.to_csv(out, index=False)
        print(t.to_string(index=False))
        print(f"\n-> {out}")

    if a.task in ("headline", "all"):
        print("\nheadline (C1): not implemented yet")


if __name__ == "__main__":
    main()
