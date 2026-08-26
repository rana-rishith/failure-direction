"""Downstream WER with a frozen recogniser.

The recogniser is frozen and never fine-tuned. It is a *consumer* of enhanced
audio, which is the whole point: signal metrics can improve while WER degrades,
and that gap is evidence for the asymmetry claim.
"""

from __future__ import annotations

import functools


@functools.lru_cache(maxsize=2)
def _model(size: str = "small", device: str = "cuda", compute_type: str = "int8_float16"):
    from faster_whisper import WhisperModel

    return WhisperModel(size, device=device, compute_type=compute_type)


def transcribe(path: str, size: str = "small", device: str = "cuda", language: str = "en") -> str:
    segments, _ = _model(size, device).transcribe(path, language=language, beam_size=5)
    return " ".join(s.text for s in segments).strip()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate after light normalisation. Empty reference -> NaN, not 0."""
    import jiwer

    tf = jiwer.Compose(
        [
            jiwer.ToLowerCase(),
            jiwer.RemovePunctuation(),
            jiwer.RemoveMultipleSpaces(),
            jiwer.Strip(),
            jiwer.ReduceToListOfListOfWords(),
        ]
    )
    if not reference.strip():
        return float("nan")
    return float(jiwer.wer(reference, hypothesis, truth_transform=tf, hypothesis_transform=tf))
