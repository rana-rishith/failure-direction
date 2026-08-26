"""Model registry. Four baselines, equal compute budget, one interface."""

from __future__ import annotations

from collections.abc import Callable

MODELS: dict[str, Callable] = {}


def register(name: str):
    def deco(fn):
        MODELS[name] = fn
        return fn

    return deco


def build_model(name: str, **kwargs):
    if name not in MODELS:
        raise KeyError(f"unknown model '{name}'. registered: {sorted(MODELS)}")
    return MODELS[name](**kwargs)


# Import for side effects — each module registers itself.
from failure_direction.models import causal, mask_stft, passthrough  # noqa: E402,F401
