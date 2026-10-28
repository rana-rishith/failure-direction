"""Universal-gate verdict logic and the thresholds parsed out of gate_universal.yaml.

The thresholds are pre-registered inside the yaml's prose, so the parse is the part
that can silently drift. These expected values are the yaml's own, read off
configs/gate_universal.yaml at commit 29c1566.
"""

import argparse
import json

import numpy as np
import pandas as pd
import pytest

from scripts import run_universal as U


@pytest.fixture(scope="module")
def cfg():
    return U.load_gate()[0]


def test_thresholds_parsed_from_yaml(cfg):
    assert U._after(cfg["U1_novelty_monotone"]["pass_arch_if"], ">=") == 3      # >= 3 of 4 levels
    assert U._after(cfg["U1_failure_class"]["classes"]["inert"], "<") == 0.30   # nr < 0.30
    assert U._after(cfg["U1_failure_class"]["classes"]["hallucinate"], ">=") == 0.05
    assert U._after(cfg["U3_within_condition"]["pass_if"][1], ">=") / 100 == 0.75
    # the 1 in "U1_novelty_monotone" must not be read as the threshold
    assert U._after(cfg["U2_beyond_bounded"]["pass_if"], ">=") == 2
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


def _seg_csvs(root, arch, d_by_rung):
    """Minimal segment CSVs for one arch: the columns u1_rows keeps, both folds."""
    import config as C
    ratios = {"A": d_by_rung["R1"], "B": d_by_rung["R2"], "U": d_by_rung["R4"]}
    for fold in C.FAMILIES:
        for name, halves in (("windows", ("A", "B")), ("unseen", ("U",))):
            rec = []
            for snr in (-15, -10, -5, 0):
                for h in halves:
                    ro, ru = ratios[h]
                    rec.append({"uid": f"1-1-0001_{h}{snr}", "noise_type": "rainfall",
                                "snr": snr, "half": h, "r_over_g_seg": ro,
                                "r_under_g_seg": ru, "r_add_g_seg": 0.01,
                                "r_over_b4_seg": 0.3, "r_under_b4_seg": 0.5})
            pd.DataFrame(rec).to_csv(root / f"{arch}_seg_{fold}__{name}.csv", index=False)


def test_u2_refuses_a_verdict_while_arms_are_missing(cfg, tmp_path, monkeypatch):
    """A class with no rows is an unmeasured arm, not a failing one, so no verdict file
    may be written while fewer than two classes have data."""
    monkeypatch.setattr(U, "SEG", tmp_path)
    monkeypatch.setattr(U, "OUT", tmp_path / "out")
    args = argparse.Namespace(allow_cpu=False, force=True, no_resume=False, tag="b1_weather")

    with pytest.raises(SystemExit) as none_ready:
        U.stage_u2(cfg, "sha", args)
    assert "needs 2 of 3" in str(none_ready.value)

    _seg_csvs(tmp_path, "cm", {"R1": (0.4, 0.1), "R2": (0.2, 0.2), "R4": (0.1, 0.4)})
    with pytest.raises(SystemExit) as one_ready:
        U.stage_u2(cfg, "sha", args)
    assert "has 1" in str(one_ready.value) and "dfn3" in str(one_ready.value)
    assert not (tmp_path / "out" / "u2_verdict.json").exists()


def test_u2_scores_the_classes_it_has(cfg, tmp_path, monkeypatch):
    monkeypatch.setattr(U, "SEG", tmp_path)
    monkeypatch.setattr(U, "OUT", tmp_path / "out")
    args = argparse.Namespace(allow_cpu=False, force=True, no_resume=False, tag="b1_weather")
    _seg_csvs(tmp_path, "cm", {"R1": (0.4, 0.1), "R2": (0.2, 0.2), "R4": (0.1, 0.4)})
    _seg_csvs(tmp_path, "dfn3", {"R1": (0.2, 0.2), "R2": (0.2, 0.2), "R4": (0.2, 0.2)})

    U.stage_u2(cfg, "sha", args)
    v = json.loads((tmp_path / "out" / "u2_verdict.json").read_text())
    assert v["notes"]["class_pass"] == {"complex_mask": True, "diverse_pretrained": False}
    assert v["thresholds"]["min_classes"] == 2
    assert v["verdict"] == "FAIL"          # one passing class is not two


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


def test_canonical_lgbm_arm_predicts_every_row():
    """The post-hoc variant routes the lgbm arm through src.claim3.fit_arm, which early
    stops and so needs a validation split carved off the training side. Every row must
    still come back with exactly one out-of-fold prediction."""
    rng = np.random.default_rng(0)
    n = 300
    d = pd.DataFrame({"uid": [f"{i % 20}-1-{i:04d}" for i in range(n)],
                      "f1": rng.standard_normal(n), "f2": rng.standard_normal(n)})
    d["y"] = 2 * d.f1 + 0.1 * rng.standard_normal(n)
    pred = U._oof(d, ["f1", "f2"], "lgbm", canonical=True)
    assert np.isfinite(pred).all()
    assert np.corrcoef(pred, d.y)[0, 1] > 0.5


def test_sens_is_refused_outside_u3():
    """--sens writes u3_sens_<name>_verdict.json, so it means nothing on another gate
    and must not be silently ignored there."""
    with pytest.raises(SystemExit):
        U.main(["--gate", "u1class", "--sens", "canonical_lgbm"])
