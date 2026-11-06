"""Set MKL's threading layer before any test module imports numpy or torch.

config.py sets the same variable, but under pytest a test module can reach
numpy first, and MKL reads the variable when its DLL loads. pytest imports the
rootdir conftest before collection, so this is the only place that is always
early enough. See docs/USAGE.md > If the test suite dies with a Windows fatal
exception.
"""
import os

os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")
