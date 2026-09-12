"""
Manifest loading, cross-condition fold construction, dataset and loaders.

Fold construction is the load-bearing piece of the whole project. The shipped
`split` column is speaker-disjoint (80/10/10) but all five noise types appear in
all three splits, so training on it as shipped means every "unseen" noise type
has in fact been seen. Folds are rebuilt by filtering on family INSIDE the
shipped speaker split, which gives family-disjoint and speaker-disjoint at once.

Filtering by family alone is not sufficient: each clean utterance appears
exactly twice with two different noise types, so the same speaker and the same
clean waveform can straddle the two families.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from torch.utils.data import DataLoader, Dataset

import config as C

MANIFEST_COLUMNS = (
    "noisy_path", "clean_path", "speaker_id", "chapter_id", "utterance_id",
    "noise_type", "target_snr_db", "duration_sec", "split",
)


# ----------------------------------------------------------------- manifest --
def librispeech_key(speaker_id, chapter_id, utterance_id) -> str:
    """LibriSpeech utterance IDs are four-digit zero-padded: 19-198-0000."""
    return f"{int(speaker_id)}-{int(chapter_id)}-{int(utterance_id):04d}"


def row_uid(row) -> str:
    """
    Stable per-row identity: utterance + noise condition + SNR.

    Labels and features are joined on (fold, split, row_idx), which is
    POSITIONAL. If the manifest row order ever changes, that join misaligns
    silently and produces believable but wrong results. Every stage therefore
    also writes `uid`, and merges are validated against it.
    """
    k = librispeech_key(row.speaker_id, row.chapter_id, row.utterance_id)
    return f"{k}|{row.noise_type}|{int(row.target_snr_db):+d}"


def load_manifest(root=None, verbose: bool = False) -> pd.DataFrame:
    root = C.ROOT if root is None else root
    mf = root / "manifest.csv"
    if not mf.exists():
        C.require_dataset()
    df = pd.read_csv(mf)

    missing = [c for c in MANIFEST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"manifest.csv is missing required columns: {missing}")

    df["family"] = np.where(df.noise_type.isin(C.WEATHER), "weather", "anthro")
    df["key"] = [librispeech_key(r.speaker_id, r.chapter_id, r.utterance_id)
                 for r in df.itertuples()]
    df["uid"] = [row_uid(r) for r in df.itertuples()]

    unknown = sorted(set(df.noise_type) - set(C.WEATHER) - set(C.ANTHRO))
    if unknown:
        raise ValueError(
            f"noise types not assigned to a family: {unknown}. "
            "Add them to config.WEATHER or config.ANTHRO — family assignment "
            "must never be inferred from filenames."
        )
    if df.uid.duplicated().any():
        n = int(df.uid.duplicated().sum())
        raise ValueError(f"{n} duplicate (utterance, noise_type, snr) rows in manifest")

    if verbose:
        print(f"manifest: {len(df)} rows | {df.duration_sec.sum()/3600:.1f} h | "
              f"{df.speaker_id.nunique()} speakers | {df.key.nunique()} unique utterances")
    return df


# -------------------------------------------------------------------- folds --
def utterance_keys(frame: pd.DataFrame) -> set:
    """(speaker, chapter, utterance) tuples. NEVER assert on `clean_source`:
    it holds a corpus-level string, so the assertion can never fire."""
    return set(zip(frame.speaker_id, frame.chapter_id, frame.utterance_id))


def make_fold(df: pd.DataFrame, train_family: str) -> dict[str, pd.DataFrame]:
    if train_family not in C.FAMILIES:
        raise ValueError(f"train_family must be one of {C.FAMILIES}, got {train_family!r}")
    other = "anthro" if train_family == "weather" else "weather"

    def sel(split_name, family):
        return df[(df.split == split_name) & (df.family == family)].reset_index(drop=True)

    fold = {
        "train":        sel("train", train_family),
        "val":          sel("val", train_family),     # in-domain, early stopping only
        "test_matched": sel("test", train_family),    # seen family, unseen speakers
        "test_unseen":  sel("test", other),           # THE cross-condition evaluation
    }
    assert_no_leakage(fold, tag=f"train-on-{train_family}")
    return fold


def assert_no_leakage(fold: dict[str, pd.DataFrame], tag: str = "") -> None:
    """Three cheap assertions. Keep them in the code; do not comment them out.
    A single leaked file makes Claim 1 collapse silently while still looking plausible."""
    tr, te = fold["train"], fold["test_unseen"]
    assert not (set(tr.speaker_id) & set(te.speaker_id)), f"SPEAKER LEAK {tag}"
    assert not (set(tr.noise_type) & set(te.noise_type)), f"NOISE LEAK {tag}"
    assert not (utterance_keys(tr) & utterance_keys(te)), f"UTTERANCE LEAK {tag}"
    # val is used for early stopping, so it must not touch the training utterances either
    assert not (utterance_keys(tr) & utterance_keys(fold["val"])), f"VAL UTTERANCE LEAK {tag}"


def build_folds(df: pd.DataFrame | None = None) -> dict[str, dict[str, pd.DataFrame]]:
    """Lazy by design: importing this module must not require the dataset on disk."""
    if df is None:
        df = load_manifest()
    return {fam: make_fold(df, fam) for fam in C.FAMILIES}


def fold_report(folds: dict) -> pd.DataFrame:
    rows = []
    for fam, d in folds.items():
        for split, frame in d.items():
            rows.append({
                "fold": fam, "split": split, "rows": len(frame),
                "hours": round(frame.duration_sec.sum() / 3600, 2),
                "speakers": frame.speaker_id.nunique(),
                "noise_types": ",".join(sorted(frame.noise_type.unique())),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- audio ---
def read_mono(path, root=None) -> np.ndarray:
    root = C.ROOT if root is None else root
    x, sr = sf.read(root / path, dtype="float32")
    if x.ndim > 1:                      # the WER path handled this, the dataset did not
        x = x.mean(axis=1)
    if sr != C.SR:
        raise ValueError(f"{path}: expected {C.SR} Hz, got {sr}")
    return np.ascontiguousarray(x)


def read_pair(row, root=None) -> tuple[np.ndarray, np.ndarray]:
    """Noisy/clean pair, truncated to the common length."""
    x = read_mono(row.noisy_path, root)
    y = read_mono(row.clean_path, root)
    n = min(len(x), len(y))
    return x[:n], y[:n]


class MarVEN(Dataset):
    """
    train=True  -> 4-second random crop (or zero-pad if shorter)
    train=False -> full-length audio, no cropping (evaluation)

    Crop offsets come from a torch Generator, not np.random. PyTorch does not
    reseed numpy in DataLoader workers, so with num_workers>0 every worker
    would draw the identical crop sequence.
    """

    def __init__(self, frame: pd.DataFrame, root=None, train: bool = True, seed: int = C.SEED):
        self.f = frame.reset_index(drop=True)
        self.root = C.ROOT if root is None else root
        self.train = train
        self.seed = seed

    def __len__(self) -> int:
        return len(self.f)

    def __getitem__(self, i: int):
        r = self.f.iloc[i]
        x, y = read_pair(r, self.root)
        n = len(x)
        if self.train:
            if n < C.CROP:
                pad = C.CROP - n
                x, y = np.pad(x, (0, pad)), np.pad(y, (0, pad))
            else:
                g = torch.Generator().manual_seed(
                    self.seed + i + torch.initial_seed() % (2**31)
                )
                s = int(torch.randint(0, n - C.CROP + 1, (1,), generator=g).item())
                x, y = x[s:s + C.CROP], y[s:s + C.CROP]
        return (
            torch.from_numpy(np.ascontiguousarray(x)),
            torch.from_numpy(np.ascontiguousarray(y)),
            int(r.target_snr_db),
            str(r.noise_type),
            str(r.uid),
        )


def make_loader(frame, root=None, batch_size: int = C.BATCH_SIZE, train: bool = True,
                workers: int = 0, seed: int = C.SEED) -> DataLoader:
    """
    num_workers=0 is required inside Jupyter on Windows: spawned workers cannot
    pickle classes defined in notebook cells. From a terminal script (where
    MarVEN is imported from this module) workers>0 is safe.
    """
    return DataLoader(
        MarVEN(frame, root, train, seed),
        batch_size=batch_size if train else 1,
        shuffle=train,
        num_workers=workers,
        drop_last=train,
        pin_memory=(C.device() == "cuda"),
        generator=torch.Generator().manual_seed(seed) if train else None,
    )


# ------------------------------------------------------------ verification ---
def verify_disk(df: pd.DataFrame, n: int = 300, root=None, seed: int = 0) -> dict:
    """A file-not-found on the first training batch looks like a code bug and is not one."""
    root = C.ROOT if root is None else root
    sample = df.sample(min(n, len(df)), random_state=seed)
    miss_noisy = [p for p in sample.noisy_path if not (root / p).exists()]
    miss_clean = [p for p in sample.clean_path if not (root / p).exists()]
    r = df.iloc[0]
    x, y = read_pair(r, root)
    return {
        "sampled": len(sample),
        "missing_noisy": len(miss_noisy),
        "missing_clean": len(miss_clean),
        "examples": (miss_noisy + miss_clean)[:5],
        "first_pair_aligned": len(x) == len(y),
        "first_pair_len": len(x),
    }
