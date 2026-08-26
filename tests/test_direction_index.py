"""The direction index has three analytic endpoints. If any breaks, nothing downstream is real."""

from __future__ import annotations

import numpy as np
import pytest

from failure_direction.direction import direction_index, oracle_floor


@pytest.fixture
def stems():
    rng = np.random.default_rng(0)
    t = np.arange(16000 * 2) / 16000
    speech = np.sin(2 * np.pi * 220 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))
    noise = 0.3 * rng.standard_normal(len(t))
    return speech, noise


def test_passthrough_is_pure_under_suppression(stems):
    """y = x: no speech destroyed, all noise retained -> direction = +1."""
    clean, noise = stems
    r = direction_index(clean, noise, clean + noise)
    assert r.over < 0.01
    assert r.under == pytest.approx(1.0, abs=0.05)
    assert r.direction > 0.95


def test_silence_is_pure_over_suppression(stems):
    """y = 0: all speech destroyed, no noise retained -> direction = -1."""
    clean, noise = stems
    r = direction_index(clean, noise, np.zeros_like(clean))
    assert r.over == pytest.approx(1.0, abs=0.02)
    assert r.under < 0.01
    assert r.direction < -0.95


def test_oracle_sits_between_the_extremes(stems):
    """An ideal ratio mask trades a little speech for a lot of noise removal."""
    clean, noise = stems
    r = oracle_floor(clean, noise)
    assert -1.0 < r.direction < 1.0
    assert r.magnitude < 1.0
    assert r.over > 0.0  # even the oracle costs some speech energy


def test_direction_is_bounded(stems):
    clean, noise = stems
    rng = np.random.default_rng(1)
    for gain in [0.1, 0.5, 1.0, 1.5]:
        y = gain * (clean + noise) + 0.01 * rng.standard_normal(len(clean))
        r = direction_index(clean, noise, y)
        assert -1.0 <= r.direction <= 1.0
        assert r.over >= 0.0 and r.under >= 0.0


def test_latency_does_not_read_as_failure(stems):
    """A constant delay must not masquerade as over-suppression."""
    clean, noise = stems
    delayed = np.pad(clean + noise, (128, 0))[: len(clean)]
    r = direction_index(clean, noise, delayed)
    assert r.direction > 0.8
