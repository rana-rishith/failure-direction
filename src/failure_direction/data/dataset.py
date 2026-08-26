"""Torch dataset over the manifest. Fixed-length crops for training, full files for eval."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from failure_direction.utils.audio import read


class PairDataset:
    """Yields (noisy, clean) float32 arrays. Wrap in torch DataLoader via ``collate``."""

    def __init__(
        self,
        manifest: str | Path,
        split_json: str | Path | None = None,
        split: str = "train",
        crop_s: float | None = 4.0,
        sample_rate: int = 16000,
        seed: int = 1337,
    ):
        df = pd.read_csv(manifest)
        if split_json is not None:
            ids = set(json.loads(Path(split_json).read_text())[split])
            df = df[df.utt_id.isin(ids)].reset_index(drop=True)
        self.df = df
        self.crop = int(crop_s * sample_rate) if crop_s else None
        self.sr = sample_rate
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, i: int):
        row = self.df.iloc[i]
        noisy, _ = read(row.noisy_path, expect_sr=self.sr)
        clean, _ = read(row.clean_path, expect_sr=self.sr)
        n = min(len(noisy), len(clean))
        noisy, clean = noisy[:n], clean[:n]

        if self.crop:
            if n < self.crop:
                pad = self.crop - n
                noisy = np.pad(noisy, (0, pad))
                clean = np.pad(clean, (0, pad))
            else:
                s = int(self.rng.integers(0, n - self.crop + 1))
                noisy, clean = noisy[s : s + self.crop], clean[s : s + self.crop]

        return noisy.astype(np.float32), clean.astype(np.float32)
