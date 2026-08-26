"""Stage 0.4 — inventory the corpus.

    python scripts/00_build_manifest.py --root "D:/Rana Rishith/MarVEN" --discover
    python scripts/00_build_manifest.py --root "D:/Rana Rishith/MarVEN"

Edit ``parse_marven`` to match what --discover actually printed. Do not trust
the placeholder rules below.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from failure_direction.data.manifest import build_manifest, discover

WEATHER = {"rainfall", "lightning", "hurricane"}
VESSEL = {"ship", "commercial_ship", "bubble_curtain"}


def parse_marven(wav: Path) -> dict | None:
    """PLACEHOLDER. Rewrite against the real layout before running."""
    parts = [p.lower() for p in wav.parts]
    noise_type = next((p for p in parts if p in WEATHER | VESSEL), None)
    if noise_type is None:
        return None  # skip clean-only files

    m = re.search(r"(-?\d+)\s*db", wav.stem, re.IGNORECASE)
    snr = int(m.group(1)) if m else None

    speaker = wav.stem.split("-")[0]
    clean = wav.parent.parent / "clean" / f"{wav.stem.split('_')[0]}.wav"

    return {
        "utt_id": wav.stem,
        "speaker_id": speaker,
        "clean_path": str(clean),
        "noisy_path": str(wav),
        "noise_family": "weather" if noise_type in WEATHER else "vessel",
        "noise_type": noise_type,
        "snr_db": snr,
        "transcript": "",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="data/manifests/inventory.csv")
    ap.add_argument("--discover", action="store_true")
    a = ap.parse_args()

    if a.discover:
        discover(a.root)
    else:
        build_manifest(a.root, parse_marven, a.out)
