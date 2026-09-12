"""
FailDir — single source of truth for paths, constants and device policy.

Import this FIRST, before torch/scipy/pystoi, in every entry point. The
KMP_DUPLICATE_LIB_OK line must run before any native library is loaded
(see README "OpenMP" section).

Every path is overridable by environment variable so that nothing in the
repo is machine-specific:

    FAILDIR_ROOT   MarVEN dataset root (the folder containing manifest.csv)
    FAILDIR_CKPT   checkpoint directory        (default <repo>/ckpt)
    FAILDIR_EVAL   evaluation output directory (default <repo>/results)
    FAILDIR_TRANS  LibriSpeech train-clean-100 root (WER stage only)
    FAILDIR_DEVICE "cuda" | "cpu"  (default: cuda if available)
"""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # MUST precede torch/scipy/pystoi

import random
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------ paths ---
REPO = Path(__file__).resolve().parent

ROOT = Path(os.environ.get("FAILDIR_ROOT", REPO / "data" / "MarVEN"))
CKPT = Path(os.environ.get("FAILDIR_CKPT", REPO / "ckpt"))
EVAL = Path(os.environ.get("FAILDIR_EVAL", REPO / "results"))
TRANS_DIR = Path(os.environ.get("FAILDIR_TRANS", REPO / "data" / "LibriSpeech" / "train-clean-100"))

METRICS = EVAL / "metrics"
RAW_EVAL = EVAL / "eval"          # per-cell evaluation CSVs
LABELS = EVAL / "labels"          # Claim 3 targets
FEATURES = EVAL / "features"      # Claim 3 reference-free features
PREDICTIONS = EVAL / "predictions"
LOGS = REPO / "logs"


def ensure_dirs() -> None:
    """Create every writable output directory. Safe to call repeatedly."""
    for d in (CKPT, EVAL, METRICS, RAW_EVAL, LABELS, FEATURES, PREDICTIONS, LOGS):
        d.mkdir(parents=True, exist_ok=True)


def require_dataset() -> Path:
    """Fail fast, naming the variable, instead of an opaque FileNotFoundError later."""
    mf = ROOT / "manifest.csv"
    if not mf.exists():
        raise FileNotFoundError(
            f"no manifest.csv under FAILDIR_ROOT={ROOT}\n"
            "ROOT must be the MarVEN folder that contains manifest.csv, noisy/ and clean/ "
            "— not the repo root. See README > Dataset."
        )
    return mf


# -------------------------------------------------------------- constants ---
SR = 16_000
CROP = 4 * SR              # 4-second random crop, training only
N_FFT = 512
HOP = 128
N_BINS = N_FFT // 2 + 1

WEATHER = ("rainfall", "lightning", "hurricane")
ANTHRO = ("bubble_curtain", "large_commercial_ship")
FAMILIES = ("weather", "anthro")
SPLITS = ("train", "val", "test_matched", "test_unseen")
SNR_LEVELS = (-15, -10, -5, 0, 5, 10, 15, 20)

# Equal-compute protocol: equal GRADIENT STEPS, not equal epochs. Weather has
# 38.3 h against anthro's 25.3 h; training by epoch hands weather ~50% more updates.
TRAIN_STEPS = 20_000
BATCH_SIZE = 8
LR = 2e-4
VAL_EVERY = 2_000
CKPT_EVERY = 500
VAL_ROWS = 200             # first N rows of the val split, unshuffled (deterministic)

SEED = 1234

# --------------------------------------------------------------- device -----
def device() -> str:
    forced = os.environ.get("FAILDIR_DEVICE")
    if forced:
        return forced
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def set_seed(seed: int = SEED) -> None:
    """Seed python, numpy and torch. Called by every entry point."""
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def tune_backends() -> None:
    import torch

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True


def autocast(enabled: bool = True):
    """
    Device-aware autocast. The original code hardcoded torch.amp.autocast("cuda"),
    which raises on a CPU-only machine and made the whole pipeline untestable
    without a GPU.
    """
    import torch

    dev = device()
    return torch.amp.autocast(dev, enabled=(enabled and dev == "cuda"))


def summary() -> str:
    return (
        f"REPO      {REPO}\n"
        f"ROOT      {ROOT}   (manifest: {(ROOT / 'manifest.csv').exists()})\n"
        f"CKPT      {CKPT}\n"
        f"EVAL      {EVAL}\n"
        f"TRANS_DIR {TRANS_DIR}   (exists: {TRANS_DIR.exists()})\n"
        f"device    {device()}\n"
        f"stft      N_FFT={N_FFT} HOP={HOP} SR={SR} bins={N_BINS}\n"
        f"protocol  steps={TRAIN_STEPS} bs={BATCH_SIZE} lr={LR} seed={SEED}"
    )
