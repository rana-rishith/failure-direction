"""The probe's summary layer: the bootstrap and the band columns.

These guard the two defects that put wrong numbers in every published
summary.csv, so they must run without the dataset. tests/test_probe.py covers
the per-utterance split and skips when FAILDIR_ROOT is unset; nothing here
touches audio.
"""

import numpy as np
import pandas as pd

from src.probe import NR_INERT, RADD_HALLUCINATE, SUMMARY_COLS, bootstrap_ci, summarise


def test_gate_thresholds_come_from_the_yaml():
    """configs/gate_universal.yaml U1_failure_class, not a literal in the module."""
    assert NR_INERT == 0.30
    assert RADD_HALLUCINATE == 0.05


def test_cluster_bootstrap_is_wider_than_the_row_bootstrap():
    """Each base utterance contributes 4 identical rows, so the rows carry no more
    information than 25 independent draws. Resampling rows pretends there are 100
    and shrinks the interval, which is the bug this replaces."""
    rng = np.random.default_rng(0)
    per_base = rng.normal(size=25)
    v = np.repeat(per_base, 4)
    base = np.repeat([f"u{i}" for i in range(25)], 4)

    c_lo, c_hi = bootstrap_ci(v, base, n=2000)
    r_lo, r_hi = bootstrap_ci(v, None, n=2000)
    assert (c_hi - c_lo) > 1.5 * (r_hi - r_lo), (
        f"cluster width {c_hi - c_lo:.4f} vs row width {r_hi - r_lo:.4f}")


def test_bootstrap_is_deterministic_and_brackets_the_median():
    v = np.arange(40.0)
    base = np.repeat([f"u{i}" for i in range(20)], 2)
    a = bootstrap_ci(v, base, n=500)
    assert a == bootstrap_ci(v, base, n=500)
    assert a[0] <= np.median(v) <= a[1]


def test_nan_rows_are_dropped_not_propagated():
    v = np.array([1.0, 2.0, np.nan, 3.0, 4.0])
    base = np.array(["a", "a", "b", "b", "c"])
    lo, hi = bootstrap_ci(v, base, n=200)
    assert np.isfinite(lo) and np.isfinite(hi)


def _rows(n=240):
    """A frame with the columns summarise reads: two noise types, four SNRs, and
    two rows per base utterance so the clusters are real."""
    rng = np.random.default_rng(1)
    base = [f"{i}-0-0" for i in range(n // 2) for _ in (0, 1)]
    d = pd.DataFrame({
        "uid": [f"{b}|t{i % 2}|{[-15, -10, -5, 0][i % 4]:+d}" for i, b in enumerate(base)],
        "noise_type": [f"t{i % 2}" for i in range(n)],
        "snr": [[-15, -10, -5, 0][i % 4] for i in range(n)],
        "tag": "synthetic",
    })
    for c in SUMMARY_COLS:
        d[c] = rng.normal(size=n)
        if c != "delta_d":                      # delta_d has no hp100 counterpart
            d[f"{c}_hp100"] = rng.normal(size=n)
    return d


def test_no_hp100_column_is_a_copy_of_its_full_band_twin():
    """delta_d has no hp100 oracle, so delta_d_hp100 must be absent rather than
    carry the 62.5 Hz value under the 100 Hz name."""
    s = summarise(_rows(), heard_types=("t0",), n_boot=200)
    assert "delta_d" in s.columns
    assert "delta_d_hp100" not in s.columns
    for c in SUMMARY_COLS:
        if f"{c}_hp100" in s.columns:
            assert not s[f"{c}_hp100"].equals(s[c]), f"{c}_hp100 duplicates {c}"


def test_summary_reports_both_row_and_cluster_counts():
    s = summarise(_rows(), heard_types=("t0",), n_boot=200)
    assert (s.n_base <= s.n).all()
    assert (s.n_base < s.n).any(), "the fixture must have clustered rows"
