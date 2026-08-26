"""Stage 1.2 — run a trained model over a fold's test set and write wavs.

Enhancement and scoring are separate steps on purpose: scoring gets re-run often,
and re-running inference each time wastes GPU hours and invites silent drift.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import torch
from tqdm import tqdm

from failure_direction.models import build_model
from failure_direction.utils.audio import read, write

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="runs/<tag>")
    ap.add_argument("--manifest", default="data/manifests/inventory.csv")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    meta = json.loads((Path(a.run) / "run.json").read_text())
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(meta["model"]).to(dev).eval()
    sd = Path(a.run) / "model.pt"
    if sd.exists():
        model.load_state_dict(torch.load(sd, map_location=dev))

    ids = set(json.loads(Path(meta["fold"]).read_text())["test"])
    df = pd.read_csv(a.manifest)
    df = df[df.utt_id.isin(ids)]

    with torch.no_grad():
        for r in tqdm(df.itertuples(), total=len(df)):
            x, sr = read(r.noisy_path)
            y = model(torch.tensor(x, dtype=torch.float32, device=dev)[None])[0]
            write(Path(a.out) / f"{r.utt_id}.wav", y.cpu().numpy(), sr)
