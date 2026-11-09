"""BSS Eval-style decomposition of one enhanced utterance — post hoc, descriptive.

No gate reads this module. It exists so reviewer item #4 can ask whether the
direction index `d` says anything the standard decompositions do not, and the
answer needs the standard terms computed the standard way.

SI-SDR terms (Le Roux et al., "SDR - half-baked or well done?", ICASSP 2019)
---------------------------------------------------------------------------
With the clean `s`, the true noise `n` and the output `e`, all mean-removed:

    e_target = <e, s> / <s, s> * s                 projection onto s
    e_interf = P_{span{s,n}} e - e_target          what leaked in from the noise
    e_artif  = e - P_{span{s,n}} e                 what is in neither source

    SI-SIR = 10 log10(|e_target|^2 / |e_interf|^2)
    SI-SAR = 10 log10(|e_target|^2 / |e_artif|^2)

Both are scale-invariant: `e` and `a*e` give the same pair, because every term
scales with `a`. The eps in the denominators is relative to the target energy
for the same reason - an absolute eps would make the ceiling depend on level.
A perfect term therefore reads 120 dB, not infinity.

MarVEN mixing is additive and exact, so `n = x - y` is the true noise (review
handoff S2.3) and span{s, n} really is the span of the two sources.

Loizou-Kim regions
------------------
`regions` counts STFT bins by what the enhancer did to the clean magnitude:
attenuated, amplified, and amplified by more than 6.02 dB (a doubling, the
threshold Loizou and Kim use for audible amplification damage). It uses
src.models.magnitude - the same STFT as every other number in this repo - and
starts at the registered bin floor, which the caller passes in; src.probe
holds that floor (K0 = 2, 62.5 Hz) and this module does not re-register it.
"""
from __future__ import annotations

import numpy as np
import torch

from src.models import magnitude

EPS = 1e-12          # relative to the target energy: a perfect term reads 120 dB
DB6 = 2.0            # 6.02 dB in magnitude = a doubling


def _c(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64).squeeze()
    return a - a.mean()


def si_terms(e: np.ndarray, s: np.ndarray, n: np.ndarray) -> dict:
    """SI-SDR / SI-SIR / SI-SAR of one utterance. e enhanced, s clean, n noise."""
    e, s, n = _c(e), _c(s), _c(n)
    if not (len(e) == len(s) == len(n)):
        raise ValueError(f"length mismatch enhanced={len(e)} clean={len(s)} noise={len(n)}")
    tgt = (e @ s) / (s @ s + 1e-20) * s
    # least squares onto span{s, n}: the projection, not a per-source fit
    A = np.stack([s, n], axis=1)
    proj = A @ np.linalg.lstsq(A, e, rcond=None)[0]
    interf = proj - tgt
    artif = e - proj
    p_t = float(tgt @ tgt)

    def db(num: float, den: float) -> float:
        return float(10 * np.log10(num / (den + EPS * num + 1e-300)))

    return {"si_sdr": db(p_t, float((e - tgt) @ (e - tgt))),
            "si_sir": db(p_t, float(interf @ interf)),
            "si_sar": db(p_t, float(artif @ artif))}


@torch.no_grad()
def regions(e: np.ndarray, s: np.ndarray, k0: int, dev: str = "cpu") -> dict:
    """Share of STFT bins from `k0` up where the output attenuates or amplifies
    the clean magnitude. `r_amp6` is the subset amplified by over 6.02 dB."""
    E, S = (magnitude(torch.from_numpy(np.ascontiguousarray(a, np.float32))[None].to(dev))[0]
            for a in (e, s))
    E, S = E[k0:], S[k0:]
    return {"r_atten": float((E < S).double().mean()),
            "r_amp": float((E > S).double().mean()),
            "r_amp6": float((E > DB6 * S).double().mean())}
