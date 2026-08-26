from __future__ import annotations

import json

import pandas as pd

from failure_direction.data.splits import cross_family_splits


def test_folds_are_family_and_speaker_disjoint(tmp_path):
    rows = []
    for fam, types in {"weather": ["rain", "wind"], "vessel": ["ship"]}.items():
        for nt in types:
            for spk in range(10):
                for snr in (-5, 0, 5):
                    rows.append(
                        {
                            "utt_id": f"{fam}-{nt}-{spk}-{snr}",
                            "speaker_id": f"spk{spk}",
                            "clean_path": "c.wav",
                            "noisy_path": "n.wav",
                            "noise_family": fam,
                            "noise_type": nt,
                            "snr_db": snr,
                            "duration_s": 1.0,
                            "sample_rate": 16000,
                            "transcript": "",
                        }
                    )
    m = tmp_path / "inv.csv"
    pd.DataFrame(rows).to_csv(m, index=False)

    cross_family_splits(m, tmp_path, seed=0)
    fold = json.loads((tmp_path / "fold_train-weather.json").read_text())

    assert fold["test_family"] == "vessel"
    assert not set(fold["train"]) & set(fold["val"])
    assert not set(fold["train"]) & set(fold["test"])

    df = pd.read_csv(m).set_index("utt_id")
    train_spk = set(df.loc[fold["train"]].speaker_id)
    val_spk = set(df.loc[fold["val"]].speaker_id)
    assert not train_spk & val_spk
