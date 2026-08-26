"""Baseline 4 — no enhancement. The most important baseline in the project.

Every reported delta is against this. If enhancement does not beat passthrough
on downstream WER under shift, that *is* the finding.
"""

from __future__ import annotations

import torch.nn as nn

from failure_direction.models.registry import register


class Passthrough(nn.Module):
    def forward(self, x):
        return x


@register("passthrough")
def build(**_):
    return Passthrough()
