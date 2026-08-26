"""Thin console entrypoints. The numbered scripts remain the primary interface."""

from __future__ import annotations

import argparse

from failure_direction.data.manifest import discover


def manifest_main() -> None:
    ap = argparse.ArgumentParser(prog="fd-manifest", description="Inspect a corpus tree.")
    ap.add_argument("root")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    discover(a.root, a.limit)
