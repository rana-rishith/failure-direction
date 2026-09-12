"""
Build a tiny synthetic dataset with MarVEN's exact structure.

    python scripts/make_synthetic_dataset.py --out data/MarVEN_synth --speakers 20

This is NOT research data and produces no meaningful results. Its only job is to
let the full pipeline be executed end to end — folds, leakage assertions,
training, evaluation, labels, features, Claim 3, WER — in a couple of minutes on
CPU, on a machine that does not have the 79-hour corpus. Use it to verify a
fresh install and to run the tests.

It reproduces the structural properties the code depends on:
  * speaker-disjoint 80/10/10 `split` column, with all five noise types present
    in every split (which is exactly why the folds have to be rebuilt)
  * each clean utterance appears exactly twice, once per family
  * eight SNR levels, synthetic and exact (measured == target)
  * LibriSpeech-style four-digit zero-padded utterance IDs and .trans.txt files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402

WEATHER = list(C.WEATHER)
ANTHRO = list(C.ANTHRO)
WORDS = ("THE QUICK BROWN FOX JUMPS OVER A LAZY DOG WHILE MORNING LIGHT FALLS "
         "ACROSS THE HARBOUR AND THE SHIPS BEGIN TO MOVE").split()


def synth_speech(n: int, rng: np.random.Generator, sr: int = C.SR) -> np.ndarray:
    """Harmonic stack with a syllabic amplitude envelope — speech-like enough to
    exercise the pipeline and the feature extractor."""
    t = np.arange(n) / sr
    f0 = rng.uniform(90, 200)
    x = sum((1.0 / k) * np.sin(2 * np.pi * f0 * k * t + rng.uniform(0, 6.28))
            for k in range(1, 12))
    env = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(2.5, 4.5) * t)
    gate = (rng.random(max(1, n // 2000)) > 0.2).astype(float)
    gate = np.repeat(gate, 2000)[:n]
    x = x * env * np.where(gate > 0, 1.0, 0.05)
    return (x / (np.abs(x).max() + 1e-9) * 0.3).astype(np.float32)


def synth_noise(kind: str, n: int, rng: np.random.Generator, sr: int = C.SR) -> np.ndarray:
    w = rng.standard_normal(n)
    if kind == "rainfall":                      # broadband, slightly high-passed
        x = np.diff(np.concatenate([[0.0], w]))
    elif kind == "hurricane":                   # low-frequency, out of the speech band
        k = 200
        x = np.convolve(w, np.ones(k) / k, mode="same")
    elif kind == "lightning":                   # impulsive
        x = np.zeros(n)
        for _ in range(max(1, n // 8000)):
            i = rng.integers(0, n)
            L = min(600, n - i)
            x[i:i + L] += rng.standard_normal(L) * np.exp(-np.arange(L) / 120)
    elif kind == "bubble_curtain":              # bursty
        x = w * (np.repeat((rng.random(max(1, n // 1600)) > 0.55).astype(float), 1600)[:n])
    elif kind == "large_commercial_ship":       # low tonal plus hum
        t = np.arange(n) / sr
        x = np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 110 * t) + 0.2 * w
    else:
        raise ValueError(kind)
    return (x / (np.std(x) + 1e-9)).astype(np.float32)


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float):
    pc = float((clean ** 2).sum())
    pn = float((noise ** 2).sum()) + 1e-12
    scale = np.sqrt(pc / (pn * 10 ** (snr_db / 10)))
    noisy = clean + scale * noise
    peak = float(np.abs(noisy).max())
    if peak > 0.99:                              # avoid clipping; record the gain
        g = 0.99 / peak
        return (noisy * g).astype(np.float32), (clean * g).astype(np.float32), float(g), float(scale)
    return noisy.astype(np.float32), clean.astype(np.float32), 1.0, float(scale)


def build(out: Path, n_speakers: int = 20, utts_per_speaker: int = 6,
          dur: float = 1.5, seed: int = 0) -> Path:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    n = int(dur * C.SR)

    speakers = [100 + i for i in range(n_speakers)]
    n_tr = max(1, int(0.8 * n_speakers))
    n_va = max(1, int(0.1 * n_speakers))
    split_of = {}
    for i, s in enumerate(speakers):
        split_of[s] = "train" if i < n_tr else ("val" if i < n_tr + n_va else "test")

    rows, trans = [], {}
    for spk in speakers:
        chap = 1000 + (spk % 7)
        for u in range(utts_per_speaker):
            key = f"{spk}-{chap}-{u:04d}"
            clean = synth_speech(n, rng)
            text = " ".join(rng.choice(WORDS, size=int(rng.integers(6, 14))))
            trans.setdefault((spk, chap), []).append((key, text))

            # one weather + one anthropogenic condition per utterance:
            # every utterance appears exactly twice, as in MarVEN
            picks = [(str(rng.choice(WEATHER)), int(rng.choice(C.SNR_LEVELS))),
                     (str(rng.choice(ANTHRO)), int(rng.choice(C.SNR_LEVELS)))]
            for ntype, snr in picks:
                noise = synth_noise(ntype, n, rng)
                noisy, clean_scaled, gain, scale = mix_at_snr(clean, noise, snr)

                cpath = Path("clean") / str(spk) / str(chap) / f"{key}.wav"
                npath = Path("noisy") / str(spk) / str(chap) / f"{key}_{ntype}_snr{snr}.wav"
                for p, wav in ((cpath, clean_scaled), (npath, noisy)):
                    (out / p).parent.mkdir(parents=True, exist_ok=True)
                    sf.write(out / p, wav, C.SR, subtype="PCM_16")

                rows.append({
                    "noisy_path": npath.as_posix(), "clean_path": cpath.as_posix(),
                    "clean_source": "librispeech_train_clean_100_synth",
                    "speaker_id": spk, "chapter_id": chap, "utterance_id": u,
                    "noise_type": ntype, "target_snr_db": snr, "measured_snr_db": snr,
                    "noise_offset_sec": 0.0, "mix_scale": round(1.0 / max(gain, 1e-6), 6),
                    "sample_rate": C.SR, "duration_sec": round(len(noisy) / C.SR, 3),
                    "split": split_of[spk],
                })

    df = pd.DataFrame(rows)
    df.to_csv(out / "manifest.csv", index=False)

    troot = out.parent / "LibriSpeech" / "train-clean-100"
    for (spk, chap), items in trans.items():
        d = troot / str(spk) / str(chap)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{spk}-{chap}.trans.txt").write_text(
            "\n".join(f"{k} {t}" for k, t in items) + "\n", encoding="utf-8")

    print(f"wrote {len(df)} rows -> {out/'manifest.csv'}")
    print(df.groupby(["split", "noise_type"]).size().unstack(fill_value=0).to_string())
    print(f"transcripts -> {troot}")
    print("\nexport these before running the pipeline:")
    print(f'  FAILDIR_ROOT="{out.resolve()}"')
    print(f'  FAILDIR_TRANS="{troot.resolve()}"')
    return out / "manifest.csv"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/MarVEN_synth")
    p.add_argument("--speakers", type=int, default=20)
    p.add_argument("--utts", type=int, default=6)
    p.add_argument("--dur", type=float, default=1.5)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    build(Path(a.out), a.speakers, a.utts, a.dur, a.seed)
