"""
Stage 0 — environment and dependency verification. Run this first.

    python scripts/00_verify_env.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402

REQUIRED = ("numpy", "pandas", "scipy", "soundfile", "torch", "pystoi", "yaml")
OPTIONAL = {
    "pesq": "PESQ (conda-forge only, no pip wheel) — evaluation reports PESQ as NaN without it",
    "lightgbm": "Claim 3 verdict",
    "sklearn": "Claim 3 verdict",
    "jiwer": "WER scoring",
    "faster_whisper": "WER transcription",
    "pytest": "test suite",
}


def main() -> int:
    print("python     ", sys.version.split()[0])
    print("executable ", sys.executable)
    if "faildir" not in sys.executable and "conda" in sys.executable:
        print("  !! not the `faildir` env — activate it before running anything else")

    missing = []
    for m in REQUIRED:
        try:
            mod = importlib.import_module(m)
            print(f"  {m:16s} {getattr(mod, '__version__', 'ok')}")
        except Exception as e:  # noqa: BLE001
            missing.append(m)
            print(f"  {m:16s} MISSING ({type(e).__name__})")

    print("\noptional:")
    for m, why in OPTIONAL.items():
        try:
            mod = importlib.import_module(m)
            print(f"  {m:16s} {getattr(mod, '__version__', 'ok')}")
        except Exception:  # noqa: BLE001
            print(f"  {m:16s} MISSING -> {why}")

    import os

    import torch
    print(f"\nKMP_DUPLICATE_LIB_OK = {os.environ.get('KMP_DUPLICATE_LIB_OK')}")
    print(f"torch.cuda.is_available() = {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        print(f"gpu: {p.name}, {p.total_memory/1e9:.3f} GB, sm_{p.major}{p.minor}")
    else:
        print("gpu: none — everything still runs on CPU, training is just slow")

    print("\n" + C.summary())

    from src import models as M
    C.ensure_dirs()
    rep = M.checkpoint_report()
    print("\ncheckpoints:")
    if not rep:
        print("  NONE — run src.train, or copy checkpoints in (see README > Files you must provide)")
    for r in rep:
        flag = "" if r["ok"] else "   <- NOT WEIGHTS (a text log named .pt?)"
        print(f"  {r['file']:24s} {r['mb']:6.2f} MB  {r['tensors']:3d} tensors  "
              f"{r['params']:>10,} params{flag}")

    if missing:
        print(f"\nFAIL: missing required packages {missing}")
        return 1
    print("\nenvironment OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
