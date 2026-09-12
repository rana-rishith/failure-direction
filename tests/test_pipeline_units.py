"""Models, checkpoint I/O, feature admissibility and WER scoring symmetry."""

import numpy as np
import pytest
import torch

import config as C
from src import features as F
from src import models as M
from src import wer as W


# ------------------------------------------------------------------ models ---
@pytest.mark.parametrize("key,expect_params", [("b1", 2_763_521), ("b3", 280_833)])
def test_shapes_and_param_counts(key, expect_params):
    m = M.MODELS[key]()
    assert M.n_params(m) == expect_params
    x = torch.randn(2, C.SR)
    with torch.no_grad():
        y, mask = m(x)
    assert y.shape == x.shape
    assert mask.shape[0] == 2 and mask.shape[1] == C.N_BINS
    assert float(mask.min()) >= 0.0 and float(mask.max()) <= 1.0


def test_passthrough_is_an_identity_with_an_all_ones_mask():
    x = torch.randn(1, C.SR)
    y, mask = M.Passthrough()(x)
    assert torch.equal(x, y)
    assert torch.all(mask == 1)


def test_istft_roundtrip_length_is_preserved():
    x = torch.randn(1, 12345)
    assert M.istft(M.stft(x), x.shape[-1]).shape[-1] == 12345


def test_checkpoint_loads_from_both_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CKPT", tmp_path)
    m = M.CausalMask()
    torch.save(m.state_dict(), tmp_path / "bare_tag.pt")             # notebook trainer
    torch.save({"model": m.state_dict(), "step": 10, "best": -1.0,
                "np_rng": np.random.get_state()},
               tmp_path / "resumable_tag_best.pt")                    # src/train.py
    for tag in ("bare_tag", "resumable_tag"):
        loaded = M.load_model("b3", tag, device="cpu")
        for k, v in m.state_dict().items():
            assert torch.equal(v, loaded.state_dict()[k])


def test_missing_checkpoint_names_the_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CKPT", tmp_path)
    with pytest.raises(FileNotFoundError, match="no checkpoint for tag"):
        M.load_model("b1", "does_not_exist", device="cpu")


# ---------------------------------------------------------------- features ---
def test_feature_count_and_finiteness():
    rng = np.random.default_rng(0)
    d = F.feats(rng.standard_normal(int(1.5 * C.SR)).astype(np.float32) * 0.1)
    assert len(d) == 33, sorted(d)
    assert all(np.isfinite(v) for v in d.values())


def test_features_handle_audio_shorter_than_one_frame():
    d = F.feats(np.zeros(100, dtype=np.float32))
    assert np.isfinite(d["log_e_noisy"])


def test_reference_free_assertion_catches_leaks():
    F.assert_reference_free(["log_e_noisy", "flat_med"])
    for bad in ("e_clean", "clean_energy", "oracle_snr", "e_over", "target_snr_db"):
        with pytest.raises(AssertionError, match="reference leak"):
            F.assert_reference_free(["log_e_noisy", bad])


# --------------------------------------------------------------------- WER ---
def _norm():
    return W.get_normalizer()


def test_scoring_normalises_both_sides():
    """The bug that inflated the clean arm from 1.38% to 3.07%: an un-normalised
    hypothesis scored against a normalised reference."""
    n = _norm()
    s = W.score("THE QUICK BROWN FOX", "the quick brown fox.", n)
    assert s["S"] + s["D"] + s["I"] == 0
    assert s["n_ref"] == 4


def test_scoring_counts_edits():
    s = W.score("THE QUICK BROWN FOX", "the quick fox", _norm())
    assert s["D"] == 1 and s["S"] == 0 and s["I"] == 0


def test_peak_normalise_targets_095_and_survives_silence():
    x = np.array([0.1, -0.2, 0.05], dtype=np.float32)
    assert np.isclose(np.abs(W.peak_normalise(x)).max(), 0.95)
    z = np.zeros(10, dtype=np.float32)
    assert np.array_equal(W.peak_normalise(z), z)


def test_corpus_wer_is_edits_over_reference_words_not_a_mean_of_rates():
    import pandas as pd
    g = pd.DataFrame({"err_noisy": [1, 9], "n_ref": [1, 99]})
    got = float(W.corpus_wer(g, arms=("noisy",)).iloc[0])
    assert got == pytest.approx(100 * 10 / 100)
    assert got != pytest.approx(np.mean([100.0, 9 / 99 * 100]))
