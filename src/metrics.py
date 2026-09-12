"""
Metrics: SI-SDR, STOI, PESQ, and the over/under energy decomposition.

SIGN CONVENTION (unified here, do not redefine elsewhere)
---------------------------------------------------------
    r_over  = e_over  / e_clean      speech destroyed   (irreversible)
    r_under = e_under / e_clean      noise retained     (speech survives)
    dir_idx = (r_over - r_under) / (r_over + r_under + eps)

    dir_idx > 0  -> OVER-suppression dominant
    dir_idx < 0  -> UNDER-suppression dominant

Every number in the Stage 2 record uses this convention. The old
`src/direction.py` returned (e_under - e_over)/(...), i.e. the opposite sign,
AND applied clean-energy frame weighting that the evaluation harness did not.
Two different quantities carried the same name. The evaluation-harness
definition (unweighted sums over the full STFT magnitude) is canonical because
every reported result uses it; the frame-weighted variant is kept under a
separate name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch

import config as C

EPS = 1e-8


# ----------------------------------------------------------------- SI-SDR ----
def si_sdr(est: torch.Tensor, ref: torch.Tensor, eps: float = EPS) -> float:
    """Scale-invariant SDR of a single utterance, in dB. Higher is better."""
    ref = ref - ref.mean()
    est = est - est.mean()
    a = (est * ref).sum() / (ref.pow(2).sum() + eps)
    target = a * ref
    noise = est - target
    return float(10 * torch.log10(target.pow(2).sum() / (noise.pow(2).sum() + eps)))


def si_sdr_loss(est: torch.Tensor, ref: torch.Tensor, eps: float = EPS) -> torch.Tensor:
    """Batched negative SI-SDR, used as the training loss.

    Computed in float32 even under autocast: log10 and the ratio of two sums are
    the numerically fragile part of the objective, and fp16 accumulation over
    64k samples costs precision for no speed.
    """
    est = est.float()
    ref = ref.float()
    ref = ref - ref.mean(-1, keepdim=True)
    est = est - est.mean(-1, keepdim=True)
    a = (est * ref).sum(-1, keepdim=True) / (ref.pow(2).sum(-1, keepdim=True) + eps)
    target = a * ref
    noise = est - target
    return -(10 * torch.log10(target.pow(2).sum(-1) / (noise.pow(2).sum(-1) + eps))).mean()


# ------------------------------------------------- guarded STOI / PESQ -------
@dataclass
class MetricGuard:
    """
    A safe_* wrapper that returns NaN on exception hides total failure exactly as
    quietly as it hides occasional failure. `DO_PESQ = False` silently NaN'd
    4,560 rows twice. These counters make that impossible to miss.
    """
    enabled: bool = True
    calls: int = 0
    guard_fail: int = 0
    exceptions: int = 0
    disabled_skips: int = 0
    errors: list[str] = field(default_factory=list)

    def report(self, name: str) -> str:
        return (f"{name}: enabled={self.enabled} calls={self.calls} "
                f"nan_from_guard={self.guard_fail} nan_from_exception={self.exceptions} "
                f"skipped_disabled={self.disabled_skips}"
                + (f" | first error: {self.errors[0][:90]}" if self.errors else ""))

    def nan_rate(self) -> float:
        bad = self.guard_fail + self.exceptions + self.disabled_skips
        return bad / max(self.calls, 1)


STOI_GUARD = MetricGuard(enabled=True)
PESQ_GUARD = MetricGuard(enabled=True)

_pesq_fn = None


def _valid(ref: np.ndarray, est: np.ndarray, sr: int) -> bool:
    return bool(
        len(ref) == len(est)
        and len(ref) >= sr // 2
        and np.isfinite(ref).all() and np.isfinite(est).all()
        and ref.std() > 1e-6 and est.std() > 1e-6
    )


def safe_stoi(ref: np.ndarray, est: np.ndarray, sr: int = C.SR) -> float:
    g = STOI_GUARD
    g.calls += 1
    if not g.enabled:
        g.disabled_skips += 1
        return np.nan
    if not _valid(ref, est, sr):
        g.guard_fail += 1
        return np.nan
    try:
        from pystoi import stoi as stoi_fn
        return float(stoi_fn(ref, est, sr, extended=False))
    except Exception as e:  # noqa: BLE001
        g.exceptions += 1
        g.errors.append(f"{type(e).__name__}: {e}")
        return np.nan


def safe_pesq(ref: np.ndarray, est: np.ndarray, sr: int = C.SR) -> float:
    g = PESQ_GUARD
    g.calls += 1
    if not g.enabled:
        g.disabled_skips += 1
        return np.nan
    if not _valid(ref, est, sr):
        g.guard_fail += 1
        return np.nan
    global _pesq_fn
    try:
        if _pesq_fn is None:
            from pesq import pesq as pesq_fn   # conda-forge build; no pip wheel exists
            _pesq_fn = pesq_fn
        return float(_pesq_fn(sr, ref, est, "wb"))
    except Exception as e:  # noqa: BLE001
        g.exceptions += 1
        g.errors.append(f"{type(e).__name__}: {e}")
        return np.nan


def reset_guards(do_stoi: bool = True, do_pesq: bool = True) -> None:
    global STOI_GUARD, PESQ_GUARD
    STOI_GUARD = MetricGuard(enabled=do_stoi)
    PESQ_GUARD = MetricGuard(enabled=do_pesq)


# ------------------------------------------------- energy decomposition ------
def energy_decomposition(mask: torch.Tensor, mag_noisy: torch.Tensor,
                         mag_clean: torch.Tensor) -> dict[str, float]:
    """
    Canonical decomposition, computed on the mask's PREDICTED magnitude
    Yh = M * |X| — not on the magnitude of the reconstructed waveform after
    istft. Overlap-add with a Hann window means the two differ: this measures
    mask intent, while SI-SDR and STOI measure the reconstruction. Say which one
    is reported in the methods section.

    Raw values are unnormalised and not comparable across utterances. Use the
    r_over / r_under ratios for everything.
    """
    yh = mask * mag_noisy
    return {
        "e_over": float(((mag_clean - yh).clamp(min=0) ** 2).sum()),
        "e_under": float(((yh - mag_clean).clamp(min=0) ** 2).sum()),
        "e_clean": float((mag_clean ** 2).sum()),
        "e_noisy": float((mag_noisy ** 2).sum()),
    }


def add_ratios(frame, eps: float = 1e-8):
    """Attach r_over, r_under, dir_idx, mag to an evaluation/label frame."""
    out = frame.copy()
    out["r_over"] = out.e_over / out.e_clean
    out["r_under"] = out.e_under / out.e_clean
    out["dir_idx"] = (out.r_over - out.r_under) / (out.r_over + out.r_under + eps)
    out["mag"] = out.r_over + out.r_under          # direction-agnostic total failure
    return out


def direction_index(mask: torch.Tensor, mag_noisy: torch.Tensor,
                    mag_clean: torch.Tensor, eps: float = 1e-10) -> tuple[float, float, float]:
    """(dir_idx, e_over, e_under) with the canonical sign: positive = over-suppression.

    NOTE on degeneracy: for a perfect estimate both terms are zero and the index
    returns 0/eps = 0, which is indistinguishable from "errors exactly balanced".
    Always report dir_idx alongside residual_energy.
    """
    d = energy_decomposition(mask, mag_noisy, mag_clean)
    eo, eu = d["e_over"], d["e_under"]
    return (eo - eu) / (eo + eu + eps), eo, eu


def direction_index_frameweighted(mask: torch.Tensor, mag_noisy: torch.Tensor,
                                  mag_clean: torch.Tensor, eps: float = 1e-10):
    """
    Variant weighting each frame by its share of clean energy — a continuous
    activity weighting rather than a binary gate (a threshold sweep at
    1e-2/1e-3/1e-4 moved active_frac 0.59 -> 0.753 -> 0.858 with no plateau, so
    no stable gate threshold exists).

    Kept for reference only. It is NOT the quantity behind any reported number,
    and its e_over/e_under are not comparable with energy_decomposition().
    """
    e_clean_f = (mag_clean ** 2).sum(-2)
    w = e_clean_f / (e_clean_f.sum() + eps)
    yh = mask * mag_noisy
    over = ((mag_clean - yh).clamp(min=0) ** 2).sum(-2)
    under = ((yh - mag_clean).clamp(min=0) ** 2).sum(-2)
    eo = float((over * w).sum())
    eu = float((under * w).sum())
    return (eo - eu) / (eo + eu + eps), eo, eu


def residual_energy(mask: torch.Tensor, mag_noisy: torch.Tensor,
                    mag_clean: torch.Tensor, eps: float = 1e-10) -> float:
    """Total squared magnitude error relative to clean energy, direction-agnostic."""
    yh = mask * mag_noisy
    return float(((yh - mag_clean) ** 2).sum() / ((mag_clean ** 2).sum() + eps))
