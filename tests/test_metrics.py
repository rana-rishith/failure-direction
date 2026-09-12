"""
SI-SDR, the energy decomposition, and the direction-index sign convention.

The sign test is the one to run before trusting any Claim 2 number. Construct
X_noisy = 2 * X_clean, then:

    mask 0.5 -> estimate equals clean      -> dir_idx ~  0   (degenerate: 0/eps)
    mask 0.1 -> estimate below clean       -> dir_idx ~ +1   (OVER-suppression)
    mask 1.0 -> estimate above clean       -> dir_idx ~ -1   (UNDER-suppression)

The old src/direction.py returned the opposite sign for the same inputs.
"""

import numpy as np
import pytest
import torch

from src import metrics as MT


def _spectra():
    C_mag = torch.rand(1, 257, 100) + 0.1
    X_mag = C_mag * 2
    return C_mag, X_mag


def test_si_sdr_is_high_for_identity():
    x = torch.randn(16000)
    assert MT.si_sdr(x, x) > 60


def test_si_sdr_is_scale_invariant():
    ref = torch.randn(16000)
    est = ref * 0.3 + 0.05 * torch.randn(16000)
    assert abs(MT.si_sdr(est, ref) - MT.si_sdr(est * 7.5, ref)) < 1e-3


def test_si_sdr_loss_is_negative_si_sdr():
    ref = torch.randn(2, 16000)
    est = ref + 0.1 * torch.randn(2, 16000)
    loss = float(MT.si_sdr_loss(est, ref))
    per_item = np.mean([MT.si_sdr(est[i], ref[i]) for i in range(2)])
    assert abs(loss + per_item) < 1e-2


@pytest.mark.parametrize("mask_value,expected", [(0.5, 0.0), (0.1, 1.0), (1.0, -1.0)])
def test_direction_index_sign(mask_value, expected):
    C_mag, X_mag = _spectra()
    m = torch.full_like(C_mag, mask_value)
    d, e_over, e_under = MT.direction_index(m, X_mag, C_mag)
    assert d == pytest.approx(expected, abs=1e-3)
    if expected > 0:
        assert e_over > e_under
    elif expected < 0:
        assert e_under > e_over


def test_residual_energy_exact_values():
    C_mag, X_mag = _spectra()
    for mask_value, want in ((0.5, 0.0), (0.1, 0.64), (1.0, 1.0)):
        m = torch.full_like(C_mag, mask_value)
        got = MT.residual_energy(m, X_mag, C_mag)
        assert got == pytest.approx(want, abs=1e-5)


def test_frameweighted_variant_agrees_on_sign_but_not_magnitude():
    C_mag, X_mag = _spectra()
    m = torch.full_like(C_mag, 0.1)
    d_plain, eo_plain, _ = MT.direction_index(m, X_mag, C_mag)
    d_w, eo_w, _ = MT.direction_index_frameweighted(m, X_mag, C_mag)
    assert np.sign(d_plain) == np.sign(d_w)
    assert eo_plain != pytest.approx(eo_w, rel=1e-3)   # different quantities


def test_passthrough_mask_is_pure_under_suppression():
    C_mag, X_mag = _spectra()
    d = MT.energy_decomposition(torch.ones_like(C_mag), X_mag, C_mag)
    assert d["e_under"] > d["e_over"]
    assert d["e_over"] == pytest.approx(0.0, abs=1e-6)   # no phase cancellation here


def test_add_ratios_columns_and_sign():
    import pandas as pd
    f = pd.DataFrame({"e_over": [10.0, 1.0], "e_under": [1.0, 10.0], "e_clean": [100.0, 100.0]})
    out = MT.add_ratios(f)
    assert out.r_over.tolist() == [0.1, 0.01]
    assert out.dir_idx.iloc[0] > 0 and out.dir_idx.iloc[1] < 0
    assert out.mag.iloc[0] == pytest.approx(0.11)


def test_metric_guard_counts_disabled_calls():
    MT.reset_guards(do_stoi=True, do_pesq=False)
    x = np.random.randn(16000).astype(np.float32)
    assert np.isnan(MT.safe_pesq(x, x))
    assert MT.PESQ_GUARD.disabled_skips == 1
    assert MT.PESQ_GUARD.nan_rate() == 1.0          # a silent all-NaN run is now visible
    MT.reset_guards()


def test_metric_guard_rejects_mismatched_lengths():
    MT.reset_guards()
    a = np.random.randn(16000).astype(np.float32)
    assert np.isnan(MT.safe_stoi(a, a[:8000]))
    assert MT.STOI_GUARD.guard_fail == 1
    MT.reset_guards()
