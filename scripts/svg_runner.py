#!/usr/bin/env python
"""Run an existing figure script unchanged and also write an .svg next to
every .pdf it saves.

    python scripts/svg_runner.py fig_direction.py --eval-dir results/eval --out paper/figs/fig_direction

Everything after the script name is passed to it as its own arguments.
"""
import runpy
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

_orig_savefig = Figure.savefig


def _savefig(self, fname, *args, **kwargs):
    _orig_savefig(self, fname, *args, **kwargs)
    p = Path(str(fname))
    if p.suffix.lower() == ".pdf":
        kw = {k: v for k, v in kwargs.items() if k not in ("format", "dpi")}
        _orig_savefig(self, p.with_suffix(".svg"), *args, **kw)
        print(f"  + {p.with_suffix('.svg')}")


Figure.savefig = _savefig

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
script = Path(sys.argv[1]).resolve()
sys.argv = [str(script)] + sys.argv[2:]
sys.path.insert(0, str(script.parent))
# and the repo root, for `from src... import`: before the scripts/ move the line
# above already put the root on the path, and fig_spectrograms.py relies on it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
runpy.run_path(str(script), run_name="__main__")
