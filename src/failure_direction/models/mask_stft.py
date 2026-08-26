"""Baseline 1 — STFT magnitude-mask estimator (non-causal BLSTM).

Chosen over a time-domain separator because the mask is the object of study: it
is directly comparable to the effective mask recovered in
``direction/index.py``, and the failure decomposition is exact rather than
inferred.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from failure_direction.models.base import STFTWrapper
from failure_direction.models.registry import register


class BLSTMMask(nn.Module):
    def __init__(self, n_freq: int = 257, hidden: int = 256, layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.rnn = nn.LSTM(
            n_freq,
            hidden,
            layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.out = nn.Linear(2 * hidden, n_freq)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # (B, T, F) -> (B, T, F)
        h, _ = self.rnn(x)
        return torch.sigmoid(self.out(h))


@register("mask_stft")
def build(n_fft: int = 512, hop: int = 128, hidden: int = 256, layers: int = 2):
    return STFTWrapper(BLSTMMask(n_fft // 2 + 1, hidden, layers), n_fft, hop)
