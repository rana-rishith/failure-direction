"""Audio I/O with the invariants this project depends on."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def read(path: str | Path, expect_sr: int | None = None) -> tuple[np.ndarray, int]:
    x, sr = sf.read(str(path), dtype="float64", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if expect_sr is not None and sr != expect_sr:
        raise ValueError(f"{path}: expected {expect_sr} Hz, got {sr} Hz")
    return x, sr


def write(path: str | Path, x: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(x, dtype=np.float32), sr)


def verify_mixture(clean: np.ndarray, noisy: np.ndarray, tol: float = 1e-4) -> dict:
    """Check that ``noise = noisy - clean`` is a real stem and not a re-encoding artefact.

    If ``residual_ratio`` is not tiny, the corpus did something to the mixture
    (resampling, normalisation, codec) and the decomposition is unsound. Stop and
    request noise stems rather than working around it.
    """
    n = min(len(clean), len(noisy))
    clean, noisy = clean[:n], noisy[:n]
    noise = noisy - clean
    recon = clean + noise
    err = float(np.mean((recon - noisy) ** 2))
    return {
        "residual_ratio": err / (float(np.mean(noisy**2)) + 1e-12),
        "exact": err < tol,
        "snr_db": 10 * np.log10((np.mean(clean**2) + 1e-12) / (np.mean(noise**2) + 1e-12)),
    }
