"""Claim 2 re-check: failure direction on matched vs unseen noise, with and without
level alignment.

Background (configs/gate_amend_level*.yaml): SI-SDR training leaves the output
level free. B1/B3 drop their output level at low SNR (g down to 0.57 at -15 dB on
matched noise), and part of that drop is counted as "speech destroyed" by the
plain energy split. This script recomputes the Claim 2 quantities on three bases
from the per-utterance CSVs written by `src.diverse --eval`:

    intent   mask-intent split |M| * |X|        (the basis of the Stage 2-4 numbers)
    output   |STFT(output)|                    (plain output split)
    level    |STFT(output)| / g                (level-aligned output split)

g = level of the clean component in the output; the passthrough floor (B4) is
the same on every basis.

It also checks that the intent basis reproduces the Stage 2 evaluation CSVs
(results/eval/<arch>__<fold>__<split>.csv) on the same utterances.

Usage, from the repo root:
    python -m src.claim2_level
Writes results/claim2_level/{summary.csv, by_snr.csv, reproduction.csv}.
"""
from __future__ import annotations

import config as C  # noqa: I001

import numpy as np
import pandas as pd

SRC = C.EVAL / "diverse"
OUT = C.EVAL / "claim2_level"
TAGS = ("b1_weather", "b1_anthro", "b3_weather", "b3_anthro", "cm_weather", "cm_anthro")
BASES = {"intent": ("r_over_i", "r_under_i"), "output": ("r_over", "r_under"),
         "level": ("r_over_g", "r_under_g")}
EPS = 1e-8


def load() -> pd.DataFrame:
    frames = []
    for tag in TAGS:
        p = SRC / f"{tag}.csv"
        if not p.exists():
            print(f"skip {tag}: {p} missing")
            continue
        f = pd.read_csv(p)
        f = f[f.cond.isin(["marven_m", "marven_u"])].copy()
        if "r_over_g" not in f.columns:
            raise SystemExit(f"{p} has no level-aligned columns; rerun src.diverse --eval {tag}")
        f["arch"], f["fold"] = tag.split("_")
        f["split"] = f.cond.map({"marven_m": "matched", "marven_u": "unseen"})
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def stats(f: pd.DataFrame, basis: str) -> pd.DataFrame:
    ro, ru = BASES[basis]
    d = (f[ro] - f[ru]) / (f[ro] + f[ru] + EPS)
    return pd.DataFrame({
        "r_over": f[ro], "r_under": f[ru], "d": d,
        "noise_removed": 1 - f[ru] / f.r_under_b4,
        "over_x_floor": f[ro] / f.r_over_b4,
        "magnitude": f[ro] + f[ru],
    })


def summarise(f: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for k, sub in f.groupby(keys):
        k = k if isinstance(k, tuple) else (k,)
        for basis in BASES:
            s = stats(sub, basis).median()
            rows.append({**dict(zip(keys, k)), "basis": basis, "n": len(sub),
                         "g": sub.g.median(), **s.round(4).to_dict()})
    return pd.DataFrame(rows)


def reproduction(f: pd.DataFrame) -> pd.DataFrame:
    """Intent basis here vs the Stage 2 evaluation CSVs, matched on uid."""
    rows = []
    for (arch, fold), sub in f[f.arch.isin(["b1", "b3"])].groupby(["arch", "fold"]):
        for split, cond in (("test_matched", "marven_m"), ("test_unseen", "marven_u")):
            p = C.RAW_EVAL / f"{arch}__{fold}__{split}.csv"
            if not p.exists():
                continue
            e = pd.read_csv(p)
            m = sub[sub.cond == cond].merge(e[["uid", "e_over", "e_under", "e_clean"]], on="uid")
            if m.empty:
                continue
            a = m.e_over / m.e_clean
            b = m.e_under / m.e_clean
            rows.append({"arch": arch, "fold": fold, "split": split, "n": len(m),
                         "median_rel_diff_r_over": float((np.abs(m.r_over_i - a) / (a + EPS)).median()),
                         "median_rel_diff_r_under": float((np.abs(m.r_under_i - b) / (b + EPS)).median()),
                         "stage2_r_over_median": float(a.median()),
                         "here_r_over_median": float(m.r_over_i.median())})
    return pd.DataFrame(rows)


def main():
    f = load()
    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 220)

    rep = reproduction(f)
    rep.to_csv(OUT / "reproduction.csv", index=False)
    if len(rep):
        print("Reproduction of the Stage 2 evaluation CSVs (intent basis, same utterances):")
        print(rep.round(4).to_string(index=False))

    low = f[f.snr <= 0]
    s_all = summarise(f, ["arch", "split"])
    s_low = summarise(low, ["arch", "split"])
    s_all["snr_range"], s_low["snr_range"] = "all", "<=0"
    summary = pd.concat([s_all, s_low], ignore_index=True)
    summary.to_csv(OUT / "summary.csv", index=False)

    cols = ["arch", "split", "basis", "n", "g", "r_over", "r_under", "d", "noise_removed",
            "over_x_floor", "magnitude"]
    for rng, s in (("all SNRs", s_all), ("SNR <= 0 dB", s_low)):
        print(f"\nClaim 2 medians, {rng}, pooled over folds:")
        print(s[cols].to_string(index=False))

    by = []
    for (arch, split, snr), sub in f.groupby(["arch", "split", "snr"]):
        row = {"arch": arch, "split": split, "snr": snr, "g": sub.g.median()}
        for basis in BASES:
            st = stats(sub, basis).median()
            row[f"d_{basis}"] = st.d
            row[f"over_x_floor_{basis}"] = st.over_x_floor
            row[f"noise_removed_{basis}"] = st.noise_removed
        by.append(row)
    by = pd.DataFrame(by)
    by.to_csv(OUT / "by_snr.csv", index=False)
    print("\nMedian d by SNR (intent -> level-aligned), and g:")
    piv = by.pivot_table(index=["arch", "split"], columns="snr",
                         values=["d_intent", "d_level", "g"]).round(2)
    for v in ("d_intent", "d_level", "g"):
        print(f"\n{v}:")
        print(piv[v].to_string())
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
