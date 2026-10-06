"""Stage 3: recording-identity confound, leave-one-type-out (LOTO) within weather.

Train B3 on two weather noise types, test on the third. Each noise type in MarVEN
is a single 7.6-30 s source (three are looped), so a held-out type is also a held-out recording.
Thresholds are pre-committed in configs/gate.yaml under `confound`.

Set FAILDIR_ROOT and FAILDIR_CKPT in the shell BEFORE running (config binds at import).

Usage, from the repo root:
    python -m src.confound --smoke              # 500 steps, 40 test rows, rainfall only
    python -m src.confound                      # all three held-out types, gate steps
    python -m src.confound --heldout rainfall   # one type at gate steps
    python -m src.confound --report             # verdict from saved CSVs, no training
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

import config as C
from src import data as D
from src import evaluate as E
from src.models import MODELS, load_model
from src.train import train

WEATHER = ("rainfall", "lightning", "hurricane")
GATE_PATH = Path(__file__).resolve().parents[1] / "configs" / "gate.yaml"
OUT = C.RAW_EVAL.parent / "confound"   # kept out of RAW_EVAL so load_matrix never sees it

KEY = "b3" if "b3" in MODELS else next(
    k for k, v in MODELS.items() if getattr(v, "__name__", "") == "CausalMask")


def load_gate() -> dict:
    with open(GATE_PATH) as fh:
        return yaml.safe_load(fh)["confound"]


# ---------------------------------------------------------------- folds

def make_loto_fold(df: pd.DataFrame, heldout: str) -> dict[str, pd.DataFrame]:
    """Same speaker split as the main folds; only the noise types change.

    `test_unseen` holds the held-out type so assert_no_leakage runs unchanged:
    no shared speaker, no shared noise type, no shared utterance.
    """
    if heldout not in WEATHER:
        raise ValueError(f"heldout must be one of {WEATHER}, got {heldout!r}")
    assert set(df[df.family == "weather"].noise_type) == set(WEATHER), \
        "weather family in manifest does not match WEATHER"
    seen = [t for t in WEATHER if t != heldout]

    def sel(split, types):
        return df[(df.split == split) & df.noise_type.isin(types)].reset_index(drop=True)

    fold = {
        "train":        sel("train", seen),
        "val":          sel("val", seen),
        "test_matched": sel("test", seen),       # seen recordings, unseen speakers
        "test_unseen":  sel("test", [heldout]),  # held-out recording, unseen speakers
    }
    D.assert_no_leakage(fold, tag=f"loto-{heldout}")
    return fold


# ---------------------------------------------------------------- eval

def _eval(model, frame, tag, fold_name, split, limit=None) -> pd.DataFrame:
    """Wrap src.evaluate.evaluate, redirecting its CSV into OUT.

    Passing model=None only works when the CSV already exists (report mode).
    """
    if limit:
        frame = frame.sample(n=min(limit, len(frame)), random_state=0).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    original = E.cell_path
    E.cell_path = lambda t, fo, sp: OUT / f"{t}__{fo}__{sp}.csv"
    try:
        res = E.evaluate(model, frame, tag, fold_name, split)
    finally:
        E.cell_path = original

    for col in ("si_sdr_in", "si_sdr_out"):
        assert col in res.columns, f"evaluate output missing {col}; has {list(res.columns)}"
    if "target_snr_db" not in res.columns:
        assert len(res) == len(frame), "cannot attach SNR: row count mismatch"
        res = res.assign(target_snr_db=frame.target_snr_db.values)
    return res


def score(res: pd.DataFrame) -> tuple[float, pd.Series]:
    """Median per-utterance improvement within each SNR, then mean over SNR strata.
    Pooled means gave a fake positive improvement in Stage 2; this avoids it."""
    imp = res.si_sdr_out - res.si_sdr_in
    per_snr = imp.groupby(res.target_snr_db).median()
    return float(per_snr.mean()), per_snr


def summarize(heldout, m, u):
    im, snr_m = score(m)
    iu, snr_u = score(u)
    row = {"heldout": heldout, "n_matched": len(m), "n_heldout": len(u),
           "imp_matched_db": round(im, 3), "imp_heldout_db": round(iu, 3),
           "R": round(iu / im, 3)}
    per_snr = pd.DataFrame({"matched": snr_m, "heldout": snr_u}).round(3)
    per_snr.insert(0, "heldout_type", heldout)
    return row, per_snr


def verdict(rows: list[dict], gate: dict) -> str:
    R = [r["R"] for r in rows]
    if len(R) < len(WEATHER):
        return f"INCOMPLETE: {len(R)}/{len(WEATHER)} held-out types"
    lo, hi = gate["loto"]["type_level"], gate["loto"]["family_level"]
    if all(r >= hi for r in R):
        return f"FAMILY-LEVEL: all R >= {hi}. Claim 1 stays family-level."
    if all(r <= lo for r in R):
        return f"RECORDING-LEVEL: all R <= {lo}. Reframe Claim 1 as unseen-recording failure."
    return f"PARTIAL: R not uniformly >= {hi} or <= {lo}. Report, no framing claim."


# ---------------------------------------------------------------- run

def run_one(df, heldout, steps, limit, suffix, report_only, key=KEY):
    tag = f"{key}_loto_{heldout}{suffix}"
    fold = make_loto_fold(df, heldout)
    fold_name = f"loto-{heldout}"
    print(f"\n=== {tag}: train {len(fold['train'])} rows on "
          f"{sorted(fold['train'].noise_type.unique())}, held out {heldout}")

    if report_only:
        model = None
    else:
        if (C.CKPT / f"{tag}_best.pt").exists():
            print(f"reuse {tag}_best.pt (no retrain)")
        else:
            train(key, fold, tag, steps=steps, val_every=min(C.VAL_EVERY, max(steps // 2, 1)))
        model = load_model(key, tag, kind="best")

    m = _eval(model, fold["test_matched"], tag, fold_name, "test_matched", limit)
    u = _eval(model, fold["test_unseen"], tag, fold_name, "test_unseen", limit)
    return summarize(heldout, m, u)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--heldout", nargs="+", choices=WEATHER, default=list(WEATHER))
    ap.add_argument("--model", choices=sorted(MODELS), default=KEY)
    ap.add_argument("--smoke", action="store_true", help="500 steps, 40 test rows, rainfall")
    ap.add_argument("--report", action="store_true", help="score saved CSVs only")
    a = ap.parse_args(argv)

    gate = load_gate()
    if a.smoke:
        steps, limit, suffix, heldouts = 500, 40, "_smoke", ["rainfall"]
    else:
        steps, limit, suffix, heldouts = gate["steps"], None, "", a.heldout
    print(f"model={a.model} steps={steps} heldouts={heldouts} out={OUT}")

    df = D.load_manifest()
    rows, tables = [], []
    for h in heldouts:
        r, t = run_one(df, h, steps, limit, suffix, a.report, key=a.model)
        rows.append(r)
        tables.append(t)

    summary = pd.DataFrame(rows)
    per_snr = pd.concat(tables)
    print("\n", summary.to_string(index=False))
    print("\nper-SNR median improvement (dB):\n", per_snr.to_string())

    if not a.smoke:
        summary.to_csv(OUT / f"loto_summary__{a.model}.csv", index=False)
        per_snr.to_csv(OUT / f"loto_per_snr__{a.model}.csv")
        print("\nVERDICT:", verdict(rows, gate))
    else:
        print("\nsmoke run: wiring only, no verdict")


if __name__ == "__main__":
    main()


