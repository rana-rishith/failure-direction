"""Determinism helpers. Every run in the paper records its seed."""

from __future__ import annotations

import os
import random

import numpy as np


def set_seed(seed: int = 1337, deterministic: bool = False) -> int:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.use_deterministic_algorithms(True, warn_only=True)
            torch.backends.cudnn.benchmark = False
        else:
            # Ampere (sm_86): TF32 + autotuner are the right default for throughput.
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
    except ImportError:
        pass
    return seed
