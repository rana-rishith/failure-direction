"""
Baselines B1 / B3 / B4 and checkpoint I/O.

These class definitions are canonical. The old `models/` package in the original
repo diverged on state-dict prefixes (an STFTWrapper added a `net.` prefix, `out`
was a bare Linear instead of Sequential+Sigmoid, and an extra `window` buffer was
registered), so it either failed to load or loaded wrong. It is not carried over.

Every model returns (waveform, mask). The mask is the energy decomposition that
the direction index is built on.
"""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn

import config as C


def stft(x: torch.Tensor) -> torch.Tensor:
    return torch.stft(
        x, C.N_FFT, C.HOP,
        window=torch.hann_window(C.N_FFT, device=x.device),
        return_complex=True,
    )


def istft(X: torch.Tensor, length: int) -> torch.Tensor:
    return torch.istft(
        X, C.N_FFT, C.HOP,
        window=torch.hann_window(C.N_FFT, device=X.device),
        length=length,
    )


def magnitude(x: torch.Tensor) -> torch.Tensor:
    """|STFT| of a waveform batch -> (B, bins, frames)."""
    return stft(x).abs()


class SpectralMask(nn.Module):
    """B1: non-causal STFT magnitude mask, 2-layer BLSTM h=256 (~2.76 M params)."""

    def __init__(self, h: int = 256):
        super().__init__()
        self.rnn = nn.LSTM(C.N_BINS, h, 2, batch_first=True, bidirectional=True)
        self.out = nn.Sequential(nn.Linear(2 * h, C.N_BINS), nn.Sigmoid())

    def forward(self, x):
        X = stft(x)
        m = X.abs().permute(0, 2, 1)
        M = self.out(self.rnn(torch.log1p(m))[0]).permute(0, 2, 1)
        return istft(X * M, x.shape[-1]), M


class CausalMask(nn.Module):
    """B3: lightweight causal GRU h=128 (~280 K params, ~6x faster than B1)."""

    def __init__(self, h: int = 128):
        super().__init__()
        self.rnn = nn.GRU(C.N_BINS, h, 2, batch_first=True)
        self.out = nn.Sequential(nn.Linear(h, C.N_BINS), nn.Sigmoid())

    def forward(self, x):
        X = stft(x)
        m = X.abs().permute(0, 2, 1)
        M = self.out(self.rnn(torch.log1p(m))[0]).permute(0, 2, 1)
        return istft(X * M, x.shape[-1]), M


class Passthrough(nn.Module):
    """B4: identity. The floor every other baseline must beat."""

    def forward(self, x):
        return x, torch.ones_like(stft(x).abs())


MODELS: dict[str, type[nn.Module]] = {
    "b1": SpectralMask,
    "b3": CausalMask,
    "b4": Passthrough,
}


def n_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


# ----------------------------------------------------------- checkpoint I/O --
def _state_dict_of(obj):
    """Accept both checkpoint formats: a bare state_dict (notebook trainer) and
    a resumable dict with a "model" key (src/train.py)."""
    return obj.get("model", obj) if isinstance(obj, dict) and "model" in obj else obj


def torch_load(path, map_location="cpu", weights_only: bool | None = None):
    """
    torch >= 2.6 defaults weights_only=True, which rejects the numpy RNG state
    stored in the resumable checkpoints. Try the safe path first, fall back
    explicitly rather than crashing.
    """
    if weights_only is not None:
        return torch.load(path, map_location=map_location, weights_only=weights_only)
    try:
        return torch.load(path, map_location=map_location, weights_only=True)
    except Exception:
        return torch.load(path, map_location=map_location, weights_only=False)


def checkpoint_path(tag: str, kind: str = "auto") -> Path:
    """
    Resolve a tag ("b1_weather") to a file. The notebook trainer wrote
    `<tag>.pt`; src/train.py writes `<tag>_best.pt` and `<tag>_last.pt`.
    """
    candidates = {
        "best": [f"{tag}_best.pt", f"{tag}.pt"],
        "last": [f"{tag}_last.pt", f"{tag}.pt"],
        "auto": [f"{tag}.pt", f"{tag}_best.pt", f"{tag}_last.pt"],
    }[kind]
    for name in candidates:
        p = C.CKPT / name
        if p.exists():
            return p
    have = sorted(p.name for p in C.CKPT.glob("*.pt"))
    raise FileNotFoundError(
        f"no checkpoint for tag {tag!r} (looked for {candidates}) in {C.CKPT}. "
        f"present: {have or 'NONE'}"
    )


def load_model(arch: str | type[nn.Module], tag: str, kind: str = "auto",
               device: str | None = None, verify: bool = True) -> nn.Module:
    """Load a checkpoint and fail fast on shape mismatch."""
    dev = device or C.device()
    cls = MODELS[arch] if isinstance(arch, str) else arch
    model = cls().to(dev)
    if cls is not Passthrough:
        path = checkpoint_path(tag, kind)
        sd = _state_dict_of(torch_load(path, map_location=dev))
        model.load_state_dict(sd)
    model.eval()
    if verify:
        with torch.no_grad():
            a, M = model(torch.zeros(1, C.SR, device=dev))
        assert a.shape == (1, C.SR), f"bad audio shape {tuple(a.shape)}"
        assert M.shape[1] == C.N_BINS, f"bad mask shape {tuple(M.shape)}"
    return model


def checkpoint_report() -> list[dict]:
    """Catches the case where `*.pt` files in the checkpoint directory are
    actually ~420-byte text logs rather than weights."""
    out = []
    for p in sorted(C.CKPT.glob("*.pt")):
        try:
            sd = _state_dict_of(torch_load(p))
            out.append({
                "file": p.name,
                "mb": round(p.stat().st_size / 1e6, 2),
                "tensors": len(sd),
                "params": int(sum(v.numel() for v in sd.values())),
                "ok": True,
            })
        except Exception as e:
            out.append({"file": p.name, "mb": round(p.stat().st_size / 1e6, 3),
                        "tensors": 0, "params": 0, "ok": False, "error": str(e)[:80]})
    return out
