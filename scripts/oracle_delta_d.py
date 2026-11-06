"""Task C3: how far each model's direction sits from an oracle Wiener mask.

    python scripts/oracle_delta_d.py            # oracle rows, then the per-cell table
    python scripts/oracle_delta_d.py --cells    # per-cell table from saved oracle rows

delta_d = d_g(model) - d(oracle Wiener), per noise type and SNR, for the D_fsd,
DFN3 and SGMSE+ rows. Descriptive: no gate reads it.

The oracle is per utterance and independent of any model, so it is computed once
per (cond, uid) and joined to every model that scored that utterance. The noise
is recovered exactly as noisy - clean, which the xcorpus manifest supports for
all 7,104 of its rows.

CPU only. The STFT and the energy split come from src.models.magnitude and
src.metrics.energy_decomposition, the same two functions the models are scored
with, so the oracle and the model are measured on one basis. Nothing here
reimplements that algebra.

The oracle mask is bounded, so its output sits at the clean level and g ~ 1: it
has no separate level-aligned column, and delta_d_g compares the model's
level-aligned d_g against the same plain-basis oracle d. src.probe.add_delta_d
takes the same view.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402

import config as C  # noqa: E402
from src.metrics import energy_decomposition  # noqa: E402
from src.models import magnitude  # noqa: E402
from src.xcorpus import OUT, _derive  # noqa: E402

ORACLE = C.EVAL / "ci" / "oracle_wiener_rows.csv"
CELLS = C.EVAL / "ci" / "oracle_delta_d_cells.csv"
COMMITTED = C.METRICS / "review_oracle_masks_rows.csv"
CHUNK = 250


def _read(p: str) -> np.ndarray:
    x, _ = sf.read(p, dtype="float32")
    return x.mean(axis=1) if x.ndim > 1 else x


def oracle_d(noisy_path: str, clean_path: str) -> dict:
    """Wiener oracle W = |S|^2 / (|S|^2 + |N|^2) on the noisy STFT."""
    x, s = _read(noisy_path), _read(clean_path)
    n = min(len(x), len(s))
    x, s = x[:n], s[:n]
    X = magnitude(torch.from_numpy(x)[None])[0]
    S = magnitude(torch.from_numpy(s)[None])[0]
    N = magnitude(torch.from_numpy(x - s)[None])[0]
    W = S ** 2 / (S ** 2 + N ** 2 + 1e-12)
    e = energy_decomposition(W, X, S)
    ro, ru = e["e_over"] / e["e_clean"], e["e_under"] / e["e_clean"]
    return {"r_over_wiener": ro, "r_under_wiener": ru,
            "d_wiener": (ro - ru) / (ro + ru + 1e-8)}


def needed() -> pd.DataFrame:
    """The (cond, uid) pairs the three model sets actually scored."""
    mv = pd.read_csv(OUT / "eval" / "marven.csv")
    fsd = mv[mv.tag.str.contains("fsd") & (mv.snr <= 0)][["uid"]].assign(cond="marven")
    parts = [fsd]
    for m in ("dfn3", "sgmse"):
        parts.append(pd.read_csv(OUT / f"ext_{m}.csv")[["cond", "uid"]])
    want = pd.concat(parts, ignore_index=True).drop_duplicates(["cond", "uid"])

    man = pd.read_csv(OUT / "manifest.csv")[["cond", "uid", "noisy", "clean",
                                             "base_noise_type", "snr"]]
    j = want.merge(man, on=["cond", "uid"], how="left")
    miss = j[j.clean.isna()]
    if len(miss):
        # C3's instruction: never regenerate signals, record the gap and carry on.
        print(f"WARNING: {len(miss)} rows have no manifest entry and are skipped:")
        print(miss.groupby("cond").size().to_string())
        j = j[j.clean.notna()]
    return j.drop_duplicates(["cond", "uid"]).reset_index(drop=True)


def build(limit: int | None = None) -> None:
    j = needed()
    ORACLE.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if ORACLE.exists():
        prev = pd.read_csv(ORACLE)
        done = set(zip(prev.cond, prev.uid))
        print(f"resuming, already done: {len(done)}")
    todo = j[~pd.Series(list(zip(j.cond, j.uid)), index=j.index).isin(done)]
    if limit:
        todo = todo.head(limit)
    print(f"{len(todo)} of {len(j)} oracle rows to compute")

    buf = []
    for i, r in enumerate(todo.itertuples(), 1):
        buf.append({"cond": r.cond, "uid": r.uid, "noise_type": r.base_noise_type,
                    "snr": r.snr, **oracle_d(r.noisy, r.clean)})
        if len(buf) >= CHUNK or i == len(todo):
            pd.DataFrame(buf).to_csv(ORACLE, mode="a", index=False,
                                     header=not ORACLE.exists())
            buf = []
            print(f"  {i}/{len(todo)}", flush=True)


def crosscheck() -> str:
    """The committed MarVEN oracle covers 2,280 rows of the same utterances. Any
    overlap must agree, or this implementation is not the registered one."""
    if not COMMITTED.exists():
        return "committed oracle file absent, no cross-check"
    o = pd.read_csv(ORACLE)
    o = o[o.cond == "marven"]
    c = pd.read_csv(COMMITTED).drop_duplicates("noisy_path")
    # The committed file keys on a MarVEN-relative noisy_path; its stem is the uid.
    c["uid"] = c.noisy_path.str.replace("\\", "/", regex=False).str.rsplit("/", n=1).str[-1]
    c["uid"] = c.uid.str.replace(".wav", "", regex=False)
    j = o.merge(c[["uid", "r_over_wiener", "r_under_wiener"]], on="uid",
                how="inner", suffixes=("", "_c"))
    if j.empty:
        return "no overlapping rows, no cross-check"
    dro = (j.r_over_wiener - j.r_over_wiener_c).abs().max()
    dru = (j.r_under_wiener - j.r_under_wiener_c).abs().max()
    return (f"cross-check against {COMMITTED.name} on {len(j)} shared rows: "
            f"max |d r_over| {dro:.2e}, max |d r_under| {dru:.2e}")


def cells() -> pd.DataFrame:
    o = pd.read_csv(ORACLE)[["cond", "uid", "d_wiener"]]
    rows = []

    mv = _derive(pd.read_csv(OUT / "eval" / "marven.csv"))
    f = mv[mv.tag.str.contains("fsd") & (mv.snr <= 0)].assign(cond="marven")
    f["model_set"] = "D_fsd"
    rows.append(f)
    for m in ("dfn3", "sgmse"):
        e = _derive(pd.read_csv(OUT / f"ext_{m}.csv"))
        e["model_set"] = m
        rows.append(e)

    f = pd.concat(rows, ignore_index=True).merge(o, on=["cond", "uid"], how="left")
    f["delta_d"] = f.d - f.d_wiener
    f["delta_d_g"] = f.d_g - f.d_wiener

    g = (f.groupby(["model_set", "tag", "cond", "noise_type", "snr"])
         .agg(n=("d_g", "size"), n_oracle=("d_wiener", "count"),
              d_g=("d_g", "median"), d_wiener=("d_wiener", "median"),
              delta_d=("delta_d", "median"), delta_d_g=("delta_d_g", "median"))
         .reset_index())
    g["post_hoc"] = True
    return g


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cells", action="store_true", help="skip the oracle pass")
    p.add_argument("--limit", type=int, help="compute only this many oracle rows")
    a = p.parse_args(argv)

    if not a.cells:
        build(a.limit)
        print("\n" + crosscheck())

    t = cells()
    CELLS.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(CELLS, index=False)
    print(f"\n{len(t)} cells -> {CELLS}")
    miss = t[t.n_oracle < t.n]
    if len(miss):
        print(f"{len(miss)} cells are missing some oracle rows "
              f"({int((t.n - t.n_oracle).sum())} rows in all)")
    print()
    print(t.groupby(["model_set", "cond"])[["delta_d_g", "d_g", "d_wiener"]]
          .median().round(3).to_string())


if __name__ == "__main__":
    main()
