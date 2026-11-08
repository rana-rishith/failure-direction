"""scripts/decomp_check.py on the first 20 rows of marven_test_v1.

Its four arms have answers fixed by algebra: identity is exact zeros, a uniform
gain a gives plain r_over = (1-a)^2 with no r_under, and leftover b = 1 IS
passthrough so it must reproduce the stored floor. If a refactor ever breaks the
energy split, the controlled check is the one thing that must fail loudly.

The asserts live in the script (`check`, `check_vs_score`) and are called from
here, so the script and the test cannot drift apart — this is not a second
harness. Same skipif as tests/test_probe.py: they need the dataset.
"""

import sys
from pathlib import Path

import pytest

import config as C

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import decomp_check as dc  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (C.ROOT / "manifest.csv").exists(),
    reason="needs FAILDIR_ROOT pointing at MarVEN",
)

N = 20


@pytest.fixture(scope="module")
def frame():
    return dc.load_split().head(N)


@pytest.fixture(scope="module")
def rows(frame):
    return dc.run(frame, log_every=0)


def test_arms_hit_their_known_answers(rows):
    dc.check(rows)


def test_split_and_gain_are_src_probe_scores(frame):
    """Every arm on row 0: g and the k0=2 split must equal score() exactly, not
    approximately. A fourth copy of the energy split is what this would catch."""
    dc.check_vs_score(frame)
