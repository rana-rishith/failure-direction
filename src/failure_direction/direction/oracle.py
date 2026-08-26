"""Oracle floor — the damage that is unavoidable at a given SNR.

Without this, low-SNR conditions look like over-suppression failures when they
are simply hard. Every direction/magnitude number in the paper is reported as a
delta against this floor.
"""

from __future__ import annotations

import numpy as np

from failure_direction.direction.index import EPS, DirectionResult, direction_index, stft


def wiener_mask(clean: np.ndarray, noise: np.ndarray, n_fft: int = 512, hop: int = 128):
    """Ideal ratio (Wiener) mask computed from the true stems."""
    S = np.abs(stft(clean, n_fft, hop)) ** 2
    N = np.abs(stft(noise, n_fft, hop)) ** 2
    T = min(S.shape[1], N.shape[1])
    return S[:, :T] / (S[:, :T] + N[:, :T] + EPS)


def oracle_output(clean: np.ndarray, noise: np.ndarray, n_fft: int = 512, hop: int = 128):
    """Waveform an ideal-ratio-mask enhancer would produce, with noisy phase."""
    import scipy.signal as ss

    n = min(len(clean), len(noise))
    clean, noise = clean[:n], noise[:n]
    X = stft(clean + noise, n_fft, hop)
    M = wiener_mask(clean, noise, n_fft, hop)
    T = min(X.shape[1], M.shape[1])
    _, y = ss.istft(
        X[:, :T] * M[:, :T],
        nperseg=n_fft,
        noverlap=n_fft - hop,
        window="hann",
        input_onesided=True,
        boundary=True,
    )
    return np.asarray(y, dtype=np.float64)


def oracle_floor(
    clean: np.ndarray, noise: np.ndarray, n_fft: int = 512, hop: int = 128
) -> DirectionResult:
    """Direction/magnitude of the ideal-ratio-mask enhancer. Report deltas against this."""
    return direction_index(clean, noise, oracle_output(clean, noise, n_fft, hop), n_fft, hop)
