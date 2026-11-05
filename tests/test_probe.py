"""probe() on three enhancers whose behaviour is known in advance.

    passthrough    e = x          nr == 0 exactly (it IS the floor), d < 0
    constant gain  e = 0.5 * x    the plain basis sees the lost level as
                                  over-suppression; the level-aligned basis
                                  divides it out and must return to the floor
    oracle Wiener  e = istft(W|X|, phase X)   d > 0, and within range of the
                                  stored mask-intent oracle (oracle_masks.py)

All three on the first 20 rows of marven_test_v1. They need the dataset, so
they skip rather than fail when FAILDIR_ROOT is not set.
"""

import numpy as np
import pytest

import config as C

pytestmark = pytest.mark.skipif(
    not (C.ROOT / "manifest.csv").exists(),
    reason="needs FAILDIR_ROOT pointing at MarVEN",
)

N = 20


@pytest.fixture(scope="module")
def passthrough():
    from src.probe import probe
    return probe(lambda x: x, limit=N, tag="b4", log_every=0)["rows"]


def test_passthrough_is_the_floor(passthrough):
    r = passthrough
    assert np.allclose(r.r_over, r.r_over_b4, atol=1e-12)
    assert np.allclose(r.r_under, r.r_under_b4, atol=1e-12)
    # nr is 1 - r_under / r_under_b4, so the floor scores exactly zero
    assert np.allclose(r.nr, 0.0, atol=1e-9)


def test_passthrough_level_aligned_floor_is_near_zero(passthrough):
    """nr_g is NOT exactly zero at the floor. g for the noisy input is only
    approximately 1 (noise correlates with speech a little, more so at low SNR),
    and the level-aligned split divides the output by g. The offset is the size
    of that correlation, not a bug."""
    assert np.abs(passthrough.nr_g).max() < 0.10


def test_passthrough_is_under_suppression(passthrough):
    # noise is retained in full and no speech is removed beyond the phase floor
    assert (passthrough.d < 0).all()
    assert (passthrough.d_g < 0).all()
    assert np.allclose(passthrough.g, 1.0, atol=0.10)
    assert np.allclose(passthrough.sisdr_gain, 0.0, atol=1e-6)


def test_constant_gain_is_rescued_by_level_alignment(passthrough):
    """A constant gain is pure level change and no suppression at all. The plain
    basis must call it over-suppression; the level-aligned basis must make it
    indistinguishable from passthrough, exactly."""
    from src.probe import probe
    r = probe(lambda x: 0.5 * x, limit=N, tag="half", log_every=0)["rows"]
    assert np.allclose(r.g, 0.5 * passthrough.g, rtol=1e-6)
    # halving the level destroys clean energy on the plain basis
    assert (r.r_over > r.r_over_b4).all()
    assert (r.d > passthrough.d).all()
    # dividing by g removes it: same numbers as passthrough's own aligned basis
    assert np.allclose(r.r_over_g, passthrough.r_over_g, rtol=1e-6)
    assert np.allclose(r.nr_g, passthrough.nr_g, rtol=1e-6, atol=1e-9)
    assert np.allclose(r.d_g, passthrough.d_g, rtol=1e-6)


def test_oracle_wiener_over_suppresses():
    import torch
    from src import data as D
    from src.probe import load_split, score

    frame = load_split().head(N)
    win = torch.hann_window(C.N_FFT)
    rows = []
    for r in frame.itertuples():
        x, y = D.read_pair(r)
        xt = torch.from_numpy(x)[None]
        Xc = torch.stft(xt, C.N_FFT, C.HOP, window=win, return_complex=True)
        S = torch.stft(torch.from_numpy(y)[None], C.N_FFT, C.HOP,
                       window=win, return_complex=True).abs()
        Nz = torch.stft(torch.from_numpy(x - y)[None], C.N_FFT, C.HOP,
                        window=win, return_complex=True).abs()
        W = S ** 2 / (S ** 2 + Nz ** 2 + 1e-12)
        e = torch.istft(Xc * W, C.N_FFT, C.HOP, window=win, length=len(x))
        rows.append(score(x, y, e[0].numpy()))
    d = np.array([q["r_over"] for q in rows])
    u = np.array([q["r_under"] for q in rows])
    di = (d - u) / (d + u + 1e-8)
    # the stored mask-intent oracle medians are 0.83 (weather) and 0.89 (anthro)
    assert np.median(di) > 0.5, f"oracle Wiener median d = {np.median(di):.3f}"
    assert (u < np.array([q["r_under_b4"] for q in rows])).all(), "oracle removed no noise"


def test_split_checksum_is_stable():
    from src.probe import load_split, split_checksum
    f = load_split()
    assert len(f) == 2280
    assert split_checksum(f.uid) == (
        "73d68b28e52518a262f603cd76a056d4979c549faa774abfa35b66074b085ac4")
