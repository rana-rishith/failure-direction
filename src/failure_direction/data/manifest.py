"""Build one inventory CSV that every later stage reads. Nothing else walks the tree.

Do not hardcode a directory layout you have not looked at. ``discover()`` prints
what is actually there; you then write the parser for *that*.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

MANIFEST_COLUMNS = [
    "utt_id",
    "speaker_id",
    "clean_path",
    "noisy_path",
    "noise_family",  # 2 levels: weather | vessel
    "noise_type",  # 5 levels
    "snr_db",  # 8 levels
    "duration_s",
    "sample_rate",
    "transcript",
]


def discover(root: str | Path, limit: int = 40) -> None:
    """Print the real tree. Run this before writing a single parser rule."""
    root = Path(root)
    dirs = sorted({p.parent for p in root.rglob("*.wav")})
    print(f"{len(dirs)} directories containing wav files")
    for d in dirs[:limit]:
        print("  ", d.relative_to(root))
    wavs = list(root.rglob("*.wav"))
    print(f"\n{len(wavs)} wav files. Sample names:")
    for w in wavs[:limit]:
        print("  ", w.relative_to(root))


def build_manifest(
    root: str | Path,
    parse: Callable[[Path], dict],
    out_csv: str | Path = "data/manifests/inventory.csv",
) -> pd.DataFrame:
    """Walk noisy files, apply ``parse`` to each, attach header info, write CSV.

    ``parse`` receives a noisy-file path and returns the metadata fields it can
    infer from the path: utt_id, speaker_id, clean_path, noise_family,
    noise_type, snr_db, transcript.
    """
    import soundfile as sf

    root = Path(root)
    rows = []
    for wav in sorted(root.rglob("*.wav")):
        meta = parse(wav)
        if meta is None:
            continue
        info = sf.info(str(wav))
        meta.setdefault("noisy_path", str(wav))
        meta["duration_s"] = round(info.frames / info.samplerate, 4)
        meta["sample_rate"] = info.samplerate
        meta.setdefault("transcript", "")
        rows.append(meta)

    df = pd.DataFrame(rows)
    missing = [c for c in MANIFEST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"parse() did not supply: {missing}")
    df = df[MANIFEST_COLUMNS]

    if df["utt_id"].duplicated().any():
        raise ValueError("utt_id is not unique — splits will leak")

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"{len(df)} rows -> {out_csv}")
    print(df.groupby(["noise_family", "noise_type"]).size())
    return df
