"""Fold construction, family assignment and the leakage guards."""

import numpy as np
import pandas as pd
import pytest

import config as C
from src import data as D


def toy_manifest():
    rows = []
    for i, spk in enumerate(range(100, 120)):
        split = "train" if i < 16 else ("val" if i < 18 else "test")
        for u in range(2):
            for ntype in ("rainfall", "bubble_curtain"):
                rows.append({
                    "noisy_path": f"noisy/{spk}/1/{spk}-1-{u:04d}_{ntype}_snr0.wav",
                    "clean_path": f"clean/{spk}/1/{spk}-1-{u:04d}.wav",
                    "speaker_id": spk, "chapter_id": 1, "utterance_id": u,
                    "noise_type": ntype, "target_snr_db": 0,
                    "duration_sec": 1.0, "split": split,
                })
    df = pd.DataFrame(rows)
    df["family"] = np.where(df.noise_type.isin(C.WEATHER), "weather", "anthro")
    df["key"] = [D.librispeech_key(r.speaker_id, r.chapter_id, r.utterance_id)
                 for r in df.itertuples()]
    df["uid"] = [D.row_uid(r) for r in df.itertuples()]
    return df


def test_librispeech_key_is_zero_padded():
    assert D.librispeech_key(19, 198, 0) == "19-198-0000"
    assert D.librispeech_key("19", "198", "7") == "19-198-0007"


def test_uid_is_unique_per_row():
    df = toy_manifest()
    assert df.uid.is_unique


def test_folds_are_family_and_speaker_disjoint():
    folds = D.build_folds(toy_manifest())
    for fam, d in folds.items():
        assert set(d["train"].family) == {fam}
        assert set(d["test_unseen"].family) != {fam}
        assert not set(d["train"].speaker_id) & set(d["test_unseen"].speaker_id)
        assert not set(d["train"].noise_type) & set(d["test_unseen"].noise_type)


def test_matched_and_unseen_are_the_same_utterances_across_folds():
    """Weather's test_matched is anthro's test_unseen. That makes the
    matched/unseen comparison perfectly paired, and it is why e_clean comes out
    identical for both pooled splits."""
    folds = D.build_folds(toy_manifest())
    a = set(folds["weather"]["test_matched"].uid)
    b = set(folds["anthro"]["test_unseen"].uid)
    assert a == b and len(a) > 0


def test_speaker_leak_is_detected():
    df = toy_manifest()
    leak = df.copy()
    leak.loc[(leak.split == "test") & (leak.family == "anthro"), "split"] = "test"
    # move one *training* speaker's anthro row into the test split
    victim = leak[(leak.split == "train") & (leak.family == "anthro")].index[0]
    leak.loc[victim, "split"] = "test"
    with pytest.raises(AssertionError, match="SPEAKER LEAK"):
        D.make_fold(leak, "weather")


def test_noise_leak_is_detected():
    df = toy_manifest()
    leak = df.copy()
    # a training row keeps its anthro family label but is mixed with a weather
    # noise type: the "unseen" weather family has now been seen during training
    victim = leak[(leak.split == "train") & (leak.family == "anthro")].index[0]
    leak.loc[victim, "noise_type"] = "rainfall"
    with pytest.raises(AssertionError, match="NOISE LEAK"):
        D.make_fold(leak, "anthro")


def test_unknown_noise_type_is_rejected(tmp_path):
    df = toy_manifest()
    df.loc[0, "noise_type"] = "krakens"
    df.to_csv(tmp_path / "manifest.csv", index=False)
    with pytest.raises(ValueError, match="not assigned to a family"):
        D.load_manifest(tmp_path)


def test_clean_source_must_not_be_used_for_leakage():
    """`clean_source` holds a corpus-level string, so an assertion on it can
    never fire. utterance_keys must use the (speaker, chapter, utterance) tuple."""
    df = toy_manifest()
    df["clean_source"] = "librispeech_train_clean_100"
    assert df.clean_source.nunique() == 1
    keys = D.utterance_keys(df)
    assert len(keys) == df[["speaker_id", "chapter_id", "utterance_id"]].drop_duplicates().shape[0]
