"""Disjoint-segment control: window starts must keep noise strictly inside one half."""

import numpy as np
import pytest

from src import segment as S


@pytest.mark.parametrize("p0,n", [(0, 3000), (450, 3000), (999, 250), (10, 90), (700, 5000)])
@pytest.mark.parametrize("half", ["A", "B"])
def test_valid_starts_exact(p0, n, half):
    L, W = 1000, 100
    a, b = S.half_bounds(L, half)

    def inside(t):
        pos = (p0 + t + np.arange(W)) % L
        return bool(((pos >= a) & (pos < b)).all())

    want = [t for t in range(0, n - W + 1) if inside(t)]
    got = [t for lo, hi in S.valid_starts(p0, n, L, half, W) for t in range(lo, hi + 1)]
    assert sorted(got) == want


def test_halves_disjoint_with_guard():
    for L in S.LOOP_SAMPLES.values():
        a0, b0 = S.half_bounds(L, "A")
        a1, b1 = S.half_bounds(L, "B")
        assert b0 + 2 * S.GUARD <= a1 + 1 and b0 - a0 >= S.WIN and b1 - a1 >= S.WIN


def test_centre_start_is_valid():
    ranges = [(0, 10), (500, 900)]
    s = S.centre_start(ranges, 2000, w=100)
    assert any(lo <= s <= hi for lo, hi in ranges)
