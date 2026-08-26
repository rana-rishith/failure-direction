"""Mask-based energy decomposition of speech-enhancement failure.

The idea in one paragraph
------------------------
An enhancer takes noisy ``x = s + n`` and returns ``y``. Whatever it did
internally, its *effective* action in the STFT domain can be recovered as a
real, non-negative gain per time-frequency bin::

    M(t,f) = |Y(t,f)| / |X(t,f)|

Because we hold ``s`` and ``n`` separately during training and evaluation, we
can apply that same recovered gain to each component and ask two independent
questions:

* how much **speech energy did it destroy**?  -> over-suppression  (irreversible)
* how much **noise energy did it leave in**?  -> under-suppression (recoverable)

This works for time-domain models, generative models and passthrough alike,
because the mask is read off the *output waveform*, never off the model's
internals.

Reference use
-------------
This module needs clean and noise stems. It is a **labelling / evaluation**
tool. The downstream predictor that consumes these labels is reference-free at
inference time — it sees only the noisy input. Do not conflate the two.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

EPS = 1e-10


@dataclass(frozen=True)
class DirectionResult:
    """Outcome of one (clean, noise, output) triple."""

    over: float
    """Fraction of clean speech energy destroyed, in [0, 1]. Higher is worse."""

    under: float
    """Fraction of noise energy retained, in [0, mask_ceiling**2]. Higher is noisier."""

    direction: float
    """(under - over) / (under + over). -1 = pure over-suppression, +1 = pure under."""

    magnitude: float
    """over + under. Total normalised damage, direction-agnostic."""

    mask_mean: float
    mask_p05: float
    mask_p95: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def stft(x: np.ndarray, n_fft: int = 512, hop: int = 128, win: str = "hann") -> np.ndarray:
    """Minimal STFT with a Hann window. Returns complex array of shape (freq, frames)."""
    import scipy.signal as ss

    _, _, Z = ss.stft(
        x,
        nperseg=n_fft,
        noverlap=n_fft - hop,
        window=win,
        boundary="zeros",
        padded=True,
        return_onesided=True,
    )
    return Z


def effective_mask(
    noisy: np.ndarray,
    output: np.ndarray,
    n_fft: int = 512,
    hop: int = 128,
    ceiling: float = 2.0,
) -> np.ndarray:
    """Recover the enhancer's effective magnitude gain from waveforms.

    ``ceiling`` bounds amplification so a single unstable bin cannot dominate.
    """
    noisy, output = _align(noisy, output)
    X = np.abs(stft(noisy, n_fft, hop))
    Y = np.abs(stft(output, n_fft, hop))
    M = Y / (X + EPS)
    return np.clip(M, 0.0, ceiling)


def direction_index(
    clean: np.ndarray,
    noise: np.ndarray,
    output: np.ndarray,
    n_fft: int = 512,
    hop: int = 128,
    ceiling: float = 2.0,
) -> DirectionResult:
    """Decompose one enhancement into over- and under-suppression.

    Parameters
    ----------
    clean, noise
        The two stems. ``noisy`` is reconstructed as ``clean + noise``; if your
        corpus stores a pre-mixed noisy file, verify ``noisy - clean == noise``
        to float tolerance before trusting any of this.
    output
        The enhancer's waveform. Latency-aligned to ``clean`` inside.

    Notes
    -----
    Over-suppression counts only *attenuation* of speech (``M < 1``); gain above
    unity is not a loss of speech and is excluded from the numerator.
    """
    clean = np.asarray(clean, dtype=np.float64)
    noise = np.asarray(noise, dtype=np.float64)
    output = np.asarray(output, dtype=np.float64)

    n = min(len(clean), len(noise))
    clean, noise = clean[:n], noise[:n]
    noisy = clean + noise

    M = effective_mask(noisy, output, n_fft, hop, ceiling)

    S = np.abs(stft(clean, n_fft, hop))
    N = np.abs(stft(noise, n_fft, hop))
    T = min(M.shape[1], S.shape[1], N.shape[1])
    M, S, N = M[:, :T], S[:, :T], N[:, :T]

    attenuation = np.clip(1.0 - M, 0.0, 1.0)  # only attenuation destroys speech
    speech_lost = float(np.sum((S * attenuation) ** 2))
    speech_total = float(np.sum(S**2)) + EPS

    noise_kept = float(np.sum((N * M) ** 2))
    noise_total = float(np.sum(N**2)) + EPS

    over = speech_lost / speech_total
    under = noise_kept / noise_total
    direction = (under - over) / (under + over + EPS)

    return DirectionResult(
        over=over,
        under=under,
        direction=direction,
        magnitude=over + under,
        mask_mean=float(M.mean()),
        mask_p05=float(np.percentile(M, 5)),
        mask_p95=float(np.percentile(M, 95)),
    )


def _align(reference: np.ndarray, other: np.ndarray, max_shift: int = 512) -> tuple:
    """Compensate constant enhancer latency by cross-correlation, then trim to equal length.

    Causal models and diffusion samplers routinely introduce a fixed delay. Left
    uncorrected it reads as catastrophic over-suppression, which is a lie.
    """
    reference = np.asarray(reference, dtype=np.float64)
    other = np.asarray(other, dtype=np.float64)
    n = min(len(reference), len(other))
    if n == 0:
        return reference, other

    a = reference[: min(n, 16000)]
    b = other[: min(n, 16000)]
    if np.allclose(a, 0) or np.allclose(b, 0):
        return reference[:n], other[:n]

    corr = np.correlate(b - b.mean(), a - a.mean(), mode="full")
    lag = int(np.argmax(np.abs(corr)) - (len(a) - 1))
    if abs(lag) > max_shift:
        lag = 0

    if lag > 0:
        other = other[lag:]
    elif lag < 0:
        other = np.pad(other, (-lag, 0))

    n = min(len(reference), len(other))
    return reference[:n], other[:n]
