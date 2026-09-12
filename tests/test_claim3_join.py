"""
Claim 3 join integrity.

Labels and features are joined on the POSITIONAL key (fold, split, row_idx).
If the manifest row order ever changes between the two extraction passes, that
join misaligns silently and the model trains on shuffled targets — which
produces believable but wrong results. Both sides therefore also write `uid`,
and load_joined() compares them.
"""

import pandas as pd
import pytest

import config as C
from src import claim3


def _write(tmp_path, monkeypatch, feature_uids):
    labels = tmp_path / "labels"
    feats = tmp_path / "features"
    labels.mkdir()
    feats.mkdir()
    monkeypatch.setattr(C, "LABELS", labels)
    monkeypatch.setattr(C, "FEATURES", feats)

    n = len(feature_uids)
    pd.DataFrame({
        "tag": "b1", "fold": "weather", "split": "train", "row_idx": range(n),
        "uid": [f"u{i}" for i in range(n)], "noise_type": "rainfall", "snr": 0,
        "speaker_id": range(n), "chapter_id": 1, "utterance_id": range(n),
        "duration_sec": 1.0, "e_over": 1.0, "e_under": 2.0, "e_clean": 10.0,
        "e_noisy": 20.0,
    }).to_csv(labels / "b1__weather__train.csv", index=False)

    pd.DataFrame({
        "fold": "weather", "split": "train", "row_idx": range(n),
        "uid": feature_uids, "log_e_noisy": 1.0, "flat_med": 0.5,
    }).to_csv(feats / "weather__train.csv", index=False)


def test_aligned_join_succeeds(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [f"u{i}" for i in range(4)])
    d = claim3.load_joined("weather", "train")
    assert len(d) == 4
    assert "r_over" in d and "y" in d


def test_misaligned_join_raises(tmp_path, monkeypatch):
    shuffled = ["u1", "u0", "u3", "u2"]          # same rows, different order
    _write(tmp_path, monkeypatch, shuffled)
    with pytest.raises(AssertionError, match="misaligned"):
        claim3.load_joined("weather", "train")


def test_drop_list_excludes_every_label_column(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [f"u{i}" for i in range(4)])
    d = claim3.load_joined("weather", "train")
    arms = claim3.feature_lists(d)
    for leak in ("e_over", "e_under", "e_clean", "r_over", "y", "uid"):
        assert leak not in arms["full"]
    assert "snr" in arms["full"] and "snr" not in arms["feats_only"]
    assert arms["baseline"] == ["snr", "log_e_noisy"]
