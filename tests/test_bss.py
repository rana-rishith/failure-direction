"""src.bss on outputs whose SI-SIR and SI-SAR are fixed by algebra.

Post hoc, descriptive: src/bss.py serves reviewer item #4 and no gate reads it,
but its four terms still have answers that cannot be argued with, so they are
asserted here rather than eyeballed in the output table.

    e = s           nothing leaked and nothing invented -> both terms at the ceiling
    e = s + 0.1 n   leaked noise lies in span{s, n}     -> finite SI-SIR, SI-SAR ceiling
    e = 0.5 s       pure level change                   -> both at the ceiling
    e = s + w       w independent of s and n            -> finite SI-SAR, high SI-SIR

The ceiling is 10 log10(1/EPS) = 120 dB, so "no such error term" reads as
above 100 dB. Scale invariance is what makes the third case a test and not a
restatement of the first.
"""

import numpy as np
import pytest

from src.bss import si_terms

CEIL = 100.0          # dB; the true ceiling is 10 log10(1/EPS) = 120


@pytest.fixture(scope="module")
def sn():
    """A speech-like s and an independent noise n, neither white nor collinear."""
    rng = np.random.default_rng(1234)
    t = np.arange(16000) / 16000.0
    s = (np.sin(2 * np.pi * 220 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))).astype(np.float32)
    n = rng.standard_normal(16000).astype(np.float32)
    n = np.convolve(n, np.ones(32) / 32, mode="same").astype(np.float32)   # coloured, not white
    return s, n


def test_identity_has_no_error_terms(sn):
    s, n = sn
    q = si_terms(s, s, n)
    assert q["si_sir"] > CEIL, q
    assert q["si_sar"] > CEIL, q


def test_leftover_noise_is_interference_not_artifact(sn):
    s, n = sn
    q = si_terms(s + 0.1 * n, s, n)
    assert 0.0 < q["si_sir"] < 60.0, q          # finite: 0.1 n is a real leak
    assert q["si_sar"] > CEIL, q                # s + 0.1 n lies wholly in span{s, n}


def test_scale_invariance(sn):
    s, n = sn
    q = si_terms(0.5 * s, s, n)
    assert q["si_sir"] > CEIL, q
    assert q["si_sar"] > CEIL, q
    # and the finite terms do not move with the output level at all. An output
    # with both a leak and an artifact, so neither term sits at the eps ceiling,
    # where the residual is float noise and not proportional to the level.
    w = np.random.default_rng(7).standard_normal(len(s)).astype(np.float32) * 0.1
    a = si_terms(s + 0.1 * n + w, s, n)
    b = si_terms(7.0 * (s + 0.1 * n + w), s, n)
    assert a["si_sir"] == pytest.approx(b["si_sir"], abs=1e-6)
    assert a["si_sar"] == pytest.approx(b["si_sar"], abs=1e-6)


def test_independent_white_noise_is_artifact(sn):
    s, n = sn
    w = np.random.default_rng(7).standard_normal(len(s)).astype(np.float32) * 0.1
    q = si_terms(s + w, s, n)
    assert 0.0 < q["si_sar"] < 60.0, q          # w is in neither source
    assert q["si_sir"] > q["si_sar"] + 10.0, q  # only its span{s,n} shadow counts as leak


def test_regions_see_attenuation_and_amplification(sn):
    """regions() on a half-gain and a double-gain output, at the registered floor."""
    from src.bss import regions
    from src.probe import K0

    s, _ = sn
    half = regions(0.5 * s, s, K0)
    assert half["r_atten"] > 0.99 and half["r_amp6"] == 0.0, half
    loud = regions(2.0 * s, s, K0)
    assert loud["r_amp"] > 0.99 and loud["r_amp6"] == 0.0, loud   # exactly 6.02 dB, not over
    louder = regions(4.0 * s, s, K0)
    assert louder["r_amp6"] > 0.99, louder
