"""Baseline 2 — lightweight causal GRU mask. Streaming-plausible, small budget."""

from __future__ import annotations

import torch
import torch.nn as nn

from failure_direction.models.base import STFTWrapper
from failure_direction.models.registry import register


class CausalGRUMask(nn.Module):
    def __init__(self, n_freq: int = 257, hidden: int = 128, layers: int = 2):
        super().__init__()
        self.rnn = nn.GRU(n_freq, hidden, layers, batch_first=True, bidirectional=False)
        self.out = nn.Linear(hidden, n_freq)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h, _ = self.rnn(x)
        return torch.sigmoid(self.out(h))


@register("causal_gru")
def build(n_fft: int = 512, hop: int = 128, hidden: int = 128, layers: int = 2):
    return STFTWrapper(CausalGRUMask(n_fft // 2 + 1, hidden, layers), n_fft, hop)
