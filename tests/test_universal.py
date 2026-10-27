"""Universal-gate verdict logic and the thresholds parsed out of gate_universal.yaml.

The thresholds are pre-registered inside the yaml's prose, so the parse is the part
that can silently drift. These expected values are the yaml's own, read off
configs/gate_universal.yaml at commit 29c1566.
"""

import numpy as np
import pandas as pd
import pytest

from scripts import run_universal as U


@pytest.fixture(scope="module")
def cfg():
    return U.load_gate()[0]


def test_thresholds_parsed_from_yaml(cfg):
    assert U._nums(cfg["U1_novelty_monotone"]["pass_arch_if"])[0] == 3          # >= 3 of 4 levels
    assert U._nums(cfg["U1_failure_class"]["classes"]["inert"])[0] == 0.30      # nr < 0.30
    assert U._nums(cfg["U1_failure_class"]["classes"]["hallucinate"])[0] == 0.05
    assert U._nums(cfg["U3_within_condition"]["pass_if"][1])[0] / 100 == 0.75
    assert cfg["definitions"]["snr_low"] == [-15, -10, -5, 0]
    assert cfg["provenance"]["commit"] == "29c1566"


def _rows(d_by_level):
    """One row per (level, rung); d_by_level maps snr -> (d_R1, d_R2, d_R4)."""
    rec = [{"arch": "b1", "fold": "weather", "snr": snr, "rung": r, "d": v}
           for snr, ds in d_by_level.items() for r, v in zip(U.RUNGS, ds)]
    return pd.DataFrame(rec)


def test_u1_needs_three_monotone_levels(cfg):
    fall, flat = (0.3, -0.2, -0.99), (0.3, 0.3, -0.99)
    snrs = cfg["definitions"]["snr_low"]
    three = _rows({s: (fall if i < 3 else flat) for i, s in enumerate(snrs)})
    cells, arch_pass, thr = U.u1_verdict(three, ["b1"], cfg)
    assert arch_pass["b1"] and thr["levels_passed"]["b1"] == 3
    assert sum(c["unit_pass"] for c in cells if c["fold"] == "all") == 3

    two = _rows({s: (fall if i < 2 else flat) for i, s in enumerate(snrs)})
    assert not U.u1_verdict(two, ["b1"], cfg)[1]["b1"]


def test_u1_missing_rung_is_not_a_pass(cfg):
    rows = _rows({s: (0.3, -0.2, -0.99) for s in cfg["definitions"]["snr_low"]})
    rows = rows[rows.rung != "R4"]                 # R4 never evaluated -> median is NaN
    assert not U.u1_verdict(rows, ["b1"], cfg)[1]["b1"]


def test_derive_matches_the_yaml_definitions():
    f = pd.DataFrame({"r_over_g": [0.4], "r_under_g": [0.1], "r_add_g": [0.02],
                      "r_over_b4": [0.3], "r_under_b4": [0.5]})
    d = U.derive(f).iloc[0]
    assert d.d == pytest.approx((0.4 - 0.1) / (0.4 + 0.1 + U.EPS))
    assert d.nr == pytest.approx(1 - 0.1 / 0.5)
    assert d.r_over_x == pytest.approx(0.4 - 0.3)
    assert d.r_add == pytest.approx(0.02)


def test_ext_metrics_passthrough_is_the_b4_floor():
    """A file-based enhancer that returns its input must land exactly on the passthrough
    floor, and one that returns the clean signal must sit at gain 1 with no excess."""
    from src import segment as S
    rng = np.random.default_rng(0)
    y = rng.standard_normal(S.C.SR).astype("float32")
    x = (y + 0.5 * rng.standard_normal(S.C.SR)).astype("float32")

    thru = S.ext_metrics(x, y, x)
    assert thru["r_over"] == pytest.approx(thru["r_over_b4"])
    assert thru["r_under"] == pytest.approx(thru["r_under_b4"])
    assert thru["r_add"] == pytest.approx(0.0)
    assert thru["g"] == pytest.approx(1.0, abs=0.05)

    ideal = S.ext_metrics(x, y, y)
    assert ideal["g"] == pytest.approx(1.0, abs=1e-6)
    assert ideal["r_over"] == pytest.approx(0.0) and ideal["r_under"] == pytest.approx(0.0)

    short = S.ext_metrics(x, y, x[:-200])        # a trimmed output is padded, not rejected
    assert np.isfinite(list(short.values())).all()


def test_unseen_window_covers_the_whole_utterance():
    from src import segment as S
    f = S.attach_full_window(pd.DataFrame({"duration_sec": [10.0, 0.5]}))
    assert f.seg_U.iloc[0] == [(0, 10 * S.C.SR - S.WIN)]
    assert f.seg_U.iloc[1] == []                   # shorter than the 3 s window
    assert S.centre_start(f.seg_U.iloc[0], 10 * S.C.SR) == (10 * S.C.SR - S.WIN) // 2
