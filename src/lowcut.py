"""Low-cut SI-SDR (gate XN2). numpy only.

The energy split drops STFT bins below 62.5 Hz (config.DECOMP_MIN_HZ), but plain
SI-SDR counts everything. The SGMSE+ VB-DMD check (20 Oct 2026) found that 92-98%
of DEMAND / VB-DMD noise energy sits below 100 Hz, so plain SI-SDR gains can be
mostly sub-100 Hz removal. These columns remove that band from estimate and
reference alike before SI-SDR:
    sisdr_lc_*     below 62.5 Hz removed (same boundary as the energy split)
    sisdr_hp100_*  below 100 Hz removed
"""
import math

import numpy as np

import config as C

LC_HZ = math.ceil(C.DECOMP_MIN_HZ * C.N_FFT / C.SR) * C.SR / C.N_FFT   # 62.5 Hz


def si_sdr(est, ref, eps=1e-8):
    est, ref = np.asarray(est, np.float64), np.asarray(ref, np.float64)
    est, ref = est - est.mean(), ref - ref.mean()
    t = (est @ ref) / (ref @ ref + eps) * ref
    return float(10 * np.log10((t @ t) / (((est - t) @ (est - t)) + eps)))


def lowcut(x, hz):
    X = np.fft.rfft(np.asarray(x, np.float64))
    X[np.fft.rfftfreq(len(x), 1 / C.SR) < hz] = 0
    return np.fft.irfft(X, len(x))


def lowcut_sisdr(e, x, y) -> dict:
    out = {}
    for name, hz in (("lc", LC_HZ), ("hp100", 100.0)):
        yr = lowcut(y, hz)
        out[f"sisdr_{name}_in"] = si_sdr(lowcut(x, hz), yr)
        out[f"sisdr_{name}_out"] = si_sdr(lowcut(e, hz), yr)
    return out
