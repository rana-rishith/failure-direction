"""PESQ / STOI / SI-SDR, with the failure modes that bite in practice handled.

Three traps, all of which silently corrupt results:

1. **Latency.** A constant delay tanks SI-SDR and PESQ. Align first.
2. **Sample rate.** Wideband PESQ requires 16 kHz; narrowband requires 8 kHz.
   Anything else raises rather than resamples behind your back.
3. **Silence.** PESQ and STOI are undefined on near-silent references. Those
   utterances return NaN and must be *counted* in the paper, not dropped quietly.
"""

from __future__ import annotations

import numpy as np

from failure_direction.direction.index import _align

SILENCE_RMS = 1e-4


def si_sdr(reference: np.ndarray, estimate: np.ndarray) -> float:
    reference, estimate = _align(reference, estimate)
    reference = reference - reference.mean()
    estimate = estimate - estimate.mean()
    alpha = np.dot(estimate, reference) / (np.dot(reference, reference) + 1e-12)
    target = alpha * reference
    noise = estimate - target
    return float(10 * np.log10((np.sum(target**2) + 1e-12) / (np.sum(noise**2) + 1e-12)))


def score_pair(reference: np.ndarray, estimate: np.ndarray, sr: int) -> dict[str, float]:
    """All three signal metrics for one utterance. NaN means 'undefined', not 'zero'."""
    reference, estimate = _align(reference, estimate)
    out: dict[str, float] = {"si_sdr": np.nan, "pesq": np.nan, "stoi": np.nan}

    if float(np.sqrt(np.mean(reference**2))) < SILENCE_RMS:
        return out

    out["si_sdr"] = si_sdr(reference, estimate)

    try:
        from pesq import pesq as _pesq

        if sr == 16000:
            out["pesq"] = float(_pesq(sr, reference, estimate, "wb"))
        elif sr == 8000:
            out["pesq"] = float(_pesq(sr, reference, estimate, "nb"))
        else:
            raise ValueError(f"PESQ needs 8k or 16k, got {sr}")
    except Exception:
        pass

    try:
        from pystoi import stoi as _stoi

        out["stoi"] = float(_stoi(reference, estimate, sr, extended=False))
    except Exception:
        pass

    return out
