"""Shared STFT front/back end so every model is compared on identical framing."""

from __future__ import annotations

import torch
import torch.nn as nn


class STFTWrapper(nn.Module):
    """Wraps a magnitude-mask network: waveform in, waveform out, noisy phase reused."""

    def __init__(self, net: nn.Module, n_fft: int = 512, hop: int = 128):
        super().__init__()
        self.net = net
        self.n_fft = n_fft
        self.hop = hop
        self.register_buffer("window", torch.hann_window(n_fft))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        X = torch.stft(
            x, self.n_fft, self.hop, window=self.window, return_complex=True, center=True
        )
        mag, phase = X.abs(), torch.angle(X)
        mask = self.net(torch.log1p(mag).transpose(1, 2)).transpose(1, 2)
        Y = mask * mag * torch.exp(1j * phase)
        return torch.istft(Y, self.n_fft, self.hop, window=self.window, length=x.shape[-1])
