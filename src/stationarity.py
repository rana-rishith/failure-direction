"""Pre-registered test: does noise stationarity predict transfer to unseen noise?

Origin
------
After D2 (spectral distance) failed, the B1 per-pair table suggested that the
unseen noises a model cleans fully are steady ones (hurricane, car, bus,
washing machine, office) and the ones it fails on are bursty or impulsive
(lightning, rainfall, bubble curtain). That observation is post-hoc on the B1
pairs, so the primary test here uses only (model, noise) pairs whose outcomes
nobody had seen when configs/gate_stationarity.yaml was committed.

Measure (computed from noise audio alone)
-----------------------------------------
sigma = median over 64 log-mel bands of the frame-to-frame standard deviation
of band log-energy (dB), for RMS-normalised noise, averaged over segments
(MarVEN: noisy - clean of test-split rows; DEMAND: 10 s segments of the whole
recording). Features are those of src.distance (n_fft 1024, hop 256, 60-8000 Hz,
every 2nd frame). Low sigma = steady noise, high sigma = bursty / impulsive.

Hypothesis: lower sigma -> more of the noise removed on unseen noise.

Primary set (fresh pairs only)
------------------------------
    b3_weather, b3_anthro  DEMAND environments only (their MarVEN unseen
                           results were already known from Stage 2)
    b3_demand              five MarVEN types + three held-out DEMAND environments
    cm_weather, cm_anthro  all unseen pairs (complex-mask models)
    cm_demand              five MarVEN types + three held-out environments

--set full needs all six tags; --set b3 uses the three B3 tags and is the
pre-specified fallback if the complex-mask arm is abandoned. The choice is
made once; the gate file says how.

Exploratory (already seen, reported, never pooled with primary)
---------------------------------------------------------------
    b1_weather, b1_anthro, b1_demand

Usage, from the repo root with FAILDIR_ROOT / FAILDIR_DEMAND set:
    python -m src.stationarity --sigma-only          # noise measure only, no outcomes
    python -m src.stationarity --set full            # the pre-registered test
    python -m src.stationarity --set b3              # fallback, see gate file
"""
from __future__ import annotations

import argparse

import config as C  # noqa: I001  (must precede torch)

import numpy as np
import pandas as pd
import soundfile as sf
from scipy import stats

from src import data as D
from src import distance as DS
from src import diverse as V

OUT = C.EVAL / "stationarity"
PRIMARY_FULL = {
    "b3_weather": ("demand",), "b3_anthro": ("demand",), "b3_demand": ("marine", "demand"),
    "cm_weather": ("marine", "demand"), "cm_anthro": ("marine", "demand"),
    "cm_demand": ("marine", "demand"),
}
PRIMARY_B3 = {k: v for k, v in PRIMARY_FULL.items() if k.startswith("b3_")}
EXPLORATORY = ("b1_weather", "b1_anthro", "b1_demand")
RHO_MAX = -0.4
AUC_MIN = 0.75
ACTIVE_NR = DS.ACTIVE_NR


# ------------------------------------------------------------- measure -----
def sigma_of(frames: np.ndarray) -> float:
    return float(np.median(frames.std(axis=0)))


def marven_sigma(df: pd.DataFrame, ntype: str) -> float:
    rows = df[(df.noise_type == ntype) & (df.split == "test")]
    if rows.empty:
        raise ValueError(f"no test-split rows for {ntype}")
    rows = rows.sample(min(DS.ROWS_PER_TYPE, len(rows)), random_state=DS.SEED)
    vals = []
    for r in rows.itertuples():
        x, y = D.read_pair(r)
        f = DS.logmel_frames(x - y)
        if len(f) > 1:
            vals.append(sigma_of(f))
    return float(np.mean(vals))


def demand_sigma(idx: pd.DataFrame, env: str) -> float:
    rng = np.random.default_rng([DS.SEED, sum(map(ord, env)), 7])
    sub = idx[idx.env == env]
    vals = []
    for _ in range(DS.SEGS_PER_REGION):
        r = sub.iloc[int(rng.integers(len(sub)))]
        start = int(rng.integers(0, r.n - DS.SEG_LEN + 1))
        x, _ = sf.read(r.path, start=start, frames=DS.SEG_LEN, dtype="float32")
        f = DS.logmel_frames(x if x.ndim == 1 else x.mean(1))
        if len(f) > 1:
            vals.append(sigma_of(f))
    return float(np.mean(vals))


def sigma_table(holdout=V.HOLDOUT) -> pd.DataFrame:
    """sigma for every MarVEN type and every DEMAND environment (noise audio only)."""
    df = D.load_manifest()
    idx = V.demand_index()
    rows = [{"source": t, "group": "marine", "sigma": marven_sigma(df, t)}
            for t in C.WEATHER + C.ANTHRO]
    rows += [{"source": e, "group": "demand", "sigma": demand_sigma(idx, e)}
             for e in sorted(set(idx.env))]
    return pd.DataFrame(rows)


# ------------------------------------------------------------- analysis ----
def pairs(tags_groups: dict, sig: pd.DataFrame, holdout) -> pd.DataFrame:
    s = dict(zip(sig.source, sig.sigma))
    out = []
    for tag, groups in tags_groups.items():
        t = DS.unit_table(tag, holdout)
        t = t[(~t.seen) & (t.group.isin(groups))].copy()
        t["sigma"] = [s[u.split(":")[0]] for u in t.unit]
        out.append(t.drop(columns="feat"))
    return pd.concat(out, ignore_index=True)


def test(p: pd.DataFrame, label: str) -> dict:
    rho = stats.spearmanr(p.sigma, p.noise_removed).statistic
    lo, hi = DS.cluster_boot_rho(p, "sigma", "noise_removed")
    active = (p.noise_removed >= ACTIVE_NR).values
    auc = DS.auc_lower_is_active(p.sigma.values, active)
    rho_g = stats.spearmanr(p.sigma, p.gain).statistic
    passed = bool((rho <= RHO_MAX) and (hi < 0))
    print(f"\n{label} (n={len(p)} pairs, {p.unit.str.split(':').str[0].nunique()} noise sources): "
          f"Spearman rho(sigma, noise_removed) = {rho:+.3f}, cluster-bootstrap 95% CI "
          f"[{lo:+.3f}, {hi:+.3f}]")
    print(f"  rho(sigma, gain) = {rho_g:+.3f} | AUC steady->active = {auc:.3f} "
          f"({int(active.sum())} active of {len(p)})")
    for tag, s in p.groupby("tag"):
        if len(s) > 2:
            print(f"  {tag}: n={len(s)} rho = {stats.spearmanr(s.sigma, s.noise_removed).statistic:+.3f}")
    return {"set": label, "n": len(p), "rho": rho, "ci_lo": lo, "ci_hi": hi, "rho_gain": rho_g,
            "auc": auc, "n_active": int(active.sum()), "pass": passed}


def run(which: str, holdout=V.HOLDOUT, primary=None):
    primary = primary or (PRIMARY_FULL if which == "full" else PRIMARY_B3)
    missing = [t for t in primary if not (V.OUT / f"{t}.csv").exists()]
    if missing:
        raise SystemExit(f"--set {which} needs results/diverse/<tag>.csv for: {missing}. "
                         "Run src.diverse --eval for them first; do not run a partial primary set.")
    OUT.mkdir(parents=True, exist_ok=True)
    sig = sigma_table(holdout)
    sig.to_csv(OUT / "sigma.csv", index=False)
    p = pairs(primary, sig, holdout)
    p.to_csv(OUT / f"pairs_primary_{which}.csv", index=False)
    res = test(p, f"PRIMARY ({which})")
    rule = f"rho <= {RHO_MAX} AND CI upper < 0"
    print(f"  pre-committed rule: {rule}  ->  {'PASS' if res['pass'] else 'FAIL'}")
    print(f"  secondary (not a gate): AUC >= {AUC_MIN}: {'yes' if res['auc'] >= AUC_MIN else 'no'}")
    rows = [res]
    ex = [t for t in EXPLORATORY if (V.OUT / f"{t}.csv").exists()]
    if ex:
        pe = pairs({t: ("marine", "demand") for t in ex}, sig, holdout)
        pe.to_csv(OUT / "pairs_exploratory_b1.csv", index=False)
        rows.append(test(pe, "EXPLORATORY (B1, already seen; not part of the test)"))
    pd.DataFrame(rows).to_csv(OUT / f"summary_{which}.csv", index=False)
    print("\nsigma per source:")
    print(sig.sort_values("sigma").round(2).to_string(index=False))
    print(f"\nsaved to {OUT}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Pre-registered stationarity test")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--set", choices=["full", "b3"])
    g.add_argument("--sigma-only", action="store_true")
    p.add_argument("--holdout", default=",".join(V.HOLDOUT))
    a = p.parse_args(argv)
    holdout = tuple(h.strip().upper() for h in a.holdout.split(",") if h.strip())
    if a.sigma_only:
        sig = sigma_table(holdout)
        OUT.mkdir(parents=True, exist_ok=True)
        sig.to_csv(OUT / "sigma.csv", index=False)
        print(sig.sort_values("sigma").round(2).to_string(index=False))
    else:
        run(a.set, holdout)


if __name__ == "__main__":
    main()
