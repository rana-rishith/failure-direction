"""Is U3's label rankable inside a cell at all?

    python scripts/u3_label_reliability.py

U3 asks a predictor to rank log r_over_x within a (noise type x SNR) cell and fails on
MarVEN at rho 0.091. That number only means something if the ranking it is chasing is
real. If two models built by the same recipe with different seeds disagree inside a
cell, the within-cell variation is training noise, no input-only predictor could track
it, and the gate was unwinnable rather than informative.

So this measures agreement between enhancers on U3's own label, cells and floor:

  seed   same architecture and fold, different seed. Bounds the share of within-cell
         variation that survives retraining, so it bounds any input-only predictor.
  arch   different model family on the same mixtures. How much of the ranking is a
         property of the input rather than of the model.

A bound from above only. The reproducible component may still rest on clean-signal
properties that a reference-free feature set cannot observe by construction, so a high
ceiling does not say the features ought to have reached it. It does rule out the
reading that U3 asked for something nobody could have predicted.

Diagnostic, not a gate: no yaml threshold, no verdict, nothing here can change U3.
"""
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.run_universal import CORPORA, OUT, u3_labels  # noqa: E402

# Replica pairs that exist in results/xcorpus/eval. b*_weather_s2 / _s3 are the same
# recipe reseeded; the gate's own label is b1_weather, which anchors both groups.
PAIRS = {"seed": [("b1_weather", "b1_weather_s2"), ("b1_weather", "b1_weather_s3"),
                  ("b1_weather_s2", "b1_weather_s3"),
                  ("b3_weather", "b3_weather_s2"), ("cm_weather", "cm_weather_s2")],
         "arch": [("b1_weather", "b3_weather"), ("b1_weather", "cm_weather"),
                  ("b3_weather", "cm_weather")]}
MIN_N = 25          # U3's own minimum rows per cell (src.claim3.within)


def main() -> None:
    conds = [c for cs in CORPORA.values() for c in cs]
    tags = sorted({t for ps in PAIRS.values() for p in ps for t in p})
    lab = {t: u3_labels(conds, t).set_index(["cond", "uid"]) for t in tags}

    rows = []
    for kind, pairs in PAIRS.items():
        for a, b in pairs:
            j = lab[a][["noise_type", "snr", "y"]].join(
                lab[b][["y"]], rsuffix="_b", how="inner").reset_index()
            # Same cells as the gate: MarVEN splits by noise type, the others by cond.
            j["cell_noise"] = j.noise_type.where(j.cond == "marven", j.cond)
            for corpus, cs in CORPORA.items():
                g = j[j.cond.isin(cs)]
                rho = pd.Series([spearmanr(c.y, c.y_b).statistic
                                 for _, c in g.groupby(["cell_noise", "snr"])
                                 if len(c) >= MIN_N])
                if rho.empty:
                    continue
                rows.append({"kind": kind, "pair": f"{a} / {b}", "corpus": corpus,
                             "n_cells": len(rho), "mean_rho": round(rho.mean(), 3),
                             "median_rho": round(rho.median(), 3),
                             "min_rho": round(rho.min(), 3),
                             "max_rho": round(rho.max(), 3)})

    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "u3_label_reliability.csv", index=False)
    print(out.to_string(index=False))
    print("\nmean rho over cells:")
    print(out.pivot_table(index="kind", columns="corpus",
                          values="mean_rho").round(3).to_string())
    print(f"\n-> {OUT / 'u3_label_reliability.csv'}")


if __name__ == "__main__":
    main()
