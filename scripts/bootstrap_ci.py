"""Descriptive bootstrap CIs for the paper's headline numbers (tasks C1 and C2).

    python scripts/bootstrap_ci.py --task hp1        # C2, paired, H_P1
    python scripts/bootstrap_ci.py --task headline   # C1, four quantity families
    python scripts/bootstrap_ci.py --task all

Every CI here is DESCRIPTIVE. No gate rule reads one, and no verdict file is
touched. The registered verdicts stand on the point estimates they were
registered against; these intervals only say how firmly the data holds them.

The resampling unit is the base utterance, never the row: rows that share a base
utterance are not independent, so a row bootstrap understates the width.

src.probe.bootstrap_ci already does a cluster bootstrap of the median, but only
of one median over one value column. H_P1 is a DIFFERENCE of two medians taken
over disjoint subsets of the same resampled bases, which that signature cannot
express, so the draw loop is written out here and reused for both tasks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from src.analysis import load_gate_config  # noqa: E402
from src.xcorpus import HEARD_P, OUT, PAIRED, UNSEEN_P, _derive  # noqa: E402

N_BOOT, SEED, ALPHA = 10_000, 1234, 0.05
CI = C.EVAL / "ci"


def _pad(groups: list[np.ndarray]) -> np.ndarray:
    """Groups of unequal length as one NaN-padded array, so a draw is one index."""
    w = max(len(g) for g in groups)
    out = np.full((len(groups), w), np.nan)
    for i, g in enumerate(groups):
        out[i, :len(g)] = g
    return out


def _draws(n_groups: int, n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n_groups, size=(n, n_groups))


def _boot(parts: list[tuple[np.ndarray, object]], combine, paired: bool,
          n: int = N_BOOT, seed: int = SEED) -> tuple[float, float, float]:
    """Cluster bootstrap of any statistic built from per-part aggregates.

    parts    one (padded value matrix, aggregator) per sub-aggregate, each row a
             cluster. `paired` means ONE cluster draw indexes every part, so the
             parts must share an aligned cluster list; otherwise each part is
             drawn independently.
    combine  turns the list of per-part aggregates into the statistic. It runs
             once on scalars for the point estimate and once per chunk on arrays,
             so it must be plain arithmetic over its arguments.
    """
    point = float(combine([agg(m) for m, agg in parts]))
    out = []
    for lo in range(0, n, 500):
        k = min(500, n - lo)
        if paired:
            pick = _draws(len(parts[0][0]), k, seed + lo)
            picks = [pick] * len(parts)
        else:
            picks = [_draws(len(m), k, seed + lo + 7919 * i)
                     for i, (m, _) in enumerate(parts)]
        out.append(combine([agg(m[p].reshape(k, -1), axis=1)
                            for (m, agg), p in zip(parts, picks)]))
    lo_q, hi_q = _quantiles(np.concatenate(out))
    return (point, lo_q, hi_q)


def _parts(f: pd.DataFrame, col: str, by: str, agg=np.nanmedian,
           keys=None) -> tuple[np.ndarray, object]:
    """One (padded matrix, aggregator) part from a frame's column, clustered by
    `by`. `keys` forces a cluster order so several parts can be paired."""
    f = f[np.isfinite(f[col])]
    keys = pd.unique(f[by]) if keys is None else keys
    g = {k: v[col].to_numpy() for k, v in f.groupby(by, sort=False)}
    return (_pad([g.get(k, np.array([np.nan])) for k in keys]), agg)


def _quantiles(v: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return (np.nan, np.nan)
    return (float(np.quantile(v, alpha / 2)), float(np.quantile(v, 1 - alpha / 2)))


def median_ci(values: np.ndarray, by: np.ndarray, n: int = N_BOOT,
              seed: int = SEED) -> tuple[float, float, float, int, int]:
    """Cluster bootstrap of a median. Returns (point, lo, hi, n_rows, n_groups)."""
    ok = np.isfinite(values)
    values, by = np.asarray(values)[ok], np.asarray(by)[ok]
    if len(values) < 2:
        return (np.nan, np.nan, np.nan, len(values), 0)
    keys = pd.unique(by)
    pad = _pad([values[by == k] for k in keys])
    point = float(np.median(values))
    meds = []
    for lo in range(0, n, 500):                    # chunked: pad[pick] is the peak
        pick = _draws(len(keys), min(500, n - lo), seed + lo)
        meds.append(np.nanmedian(pad[pick].reshape(len(pick), -1), axis=1))
    lo_q, hi_q = _quantiles(np.concatenate(meds))
    return (point, lo_q, hi_q, len(values), len(keys))


def diff_of_medians_ci(a_groups: list[np.ndarray], b_groups: list[np.ndarray],
                       n: int = N_BOOT, seed: int = SEED
                       ) -> tuple[float, float, float, np.ndarray]:
    """Cluster bootstrap of median(a) - median(b), the SAME group draw applied to
    both sides. That is what makes it paired: a base utterance enters or leaves a
    resample with all of its conditions at once, so the two medians move together
    and the interval carries only the between-base variation.
    """
    A, B = _pad(a_groups), _pad(b_groups)
    point = float(np.nanmedian(A) - np.nanmedian(B))
    out = []
    for lo in range(0, n, 500):
        pick = _draws(len(a_groups), min(500, n - lo), seed + lo)
        m = len(pick)
        out.append(np.nanmedian(A[pick].reshape(m, -1), axis=1)
                   - np.nanmedian(B[pick].reshape(m, -1), axis=1))
    draws = np.concatenate(out)
    lo_q, hi_q = _quantiles(draws)
    return (point, lo_q, hi_q, draws)


# ------------------------------------------------------------------- C2: H_P1 ---
def hp1(model: str = "sgmse", n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """H_P1 = median d_g on unseen corpora minus median d_g on heard corpora,
    over the base rows that carry all PAIRED conditions. Registered cutoff 0.20
    on |delta| (src/xn2.py:161). Post-hoc: this does not re-decide the gate.
    """
    e = _derive(pd.read_csv(OUT / f"ext_{model}.csv"))
    pb = e[e.cond.isin(PAIRED)]
    full = pb.groupby("base_uid").cond.nunique()
    keep = full[full == len(PAIRED)].index
    pb = pb[pb.base_uid.isin(keep)]

    bases = list(keep)
    unseen = [pb[(pb.base_uid == b) & pb.cond.isin(UNSEEN_P)].d_g.to_numpy() for b in bases]
    heard = [pb[(pb.base_uid == b) & pb.cond.isin(HEARD_P)].d_g.to_numpy() for b in bases]
    point, lo, hi, draws = diff_of_medians_ci(unseen, heard, n=n, seed=seed)

    # Self-check: the point estimate must reproduce the committed verdict exactly,
    # or this script is not measuring the registered quantity.
    reg = pd.read_csv(OUT / "report2" / f"H_P_{model}.csv").H_P1_delta.iloc[0]
    assert abs(point - reg) < 1e-9, f"H_P1 point {point} != registered {reg}"

    # The rule is two-sided on |delta|, so "fully past" means every point of the
    # interval clears the cutoff on the same side.
    cut = 0.20
    fully = bool((lo <= -cut and hi <= -cut) or (lo >= cut and hi >= cut))
    return pd.DataFrame([{
        "quantity": f"H_P1_delta_{model}", "unit": "paired base utterance",
        "n_base": len(bases), "n_rows": len(pb),
        "point": point, "ci_lo": lo, "ci_hi": hi,
        "cutoff": cut, "ci_fully_past_cutoff": fully,
        "frac_draws_past_cutoff": float(np.mean(np.abs(draws) >= cut)),
        "frac_draws_model_trait": float(np.mean(np.abs(draws) < 0.10)),
        "n_boot": n, "seed": seed, "post_hoc": True,
    }])


# --------------------------------------------------------------- C1: headline ---
# The paper's own printed values. Each family asserts against these before it
# reports an interval, so a CI can never be published around a quantity that is
# not the one the paper states.
PUB_SISDR = {("b1", "anthro"): (15.44, 2.96), ("b1", "weather"): (15.03, 3.32),
             ("b3", "anthro"): (14.12, 2.98), ("b3", "weather"): (13.95, 3.26)}
PUB_RATIO = {("b1", "test_matched"): (0.0187, 0.0032),
             ("b3", "test_matched"): (0.0209, 0.0042),
             ("b1", "test_unseen"): (0.0059, 0.2242),
             ("b3", "test_unseen"): (0.0076, 0.2172)}


def _base(f: pd.DataFrame, col: str = "uid") -> pd.DataFrame:
    """The LibriSpeech utterance is the cluster: '19-198-0001|hurricane|-15' and
    '19-198-0001_hurricane_snr-15' both belong to base '19-198-0001'."""
    f = f.copy()
    f["base"] = f[col].str.split(r"[|_]", regex=True).str[0]
    return f


def sisdr_gap(n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Matched minus unseen mean SI-SDR output, per model and fold. The paper's
    table is a mean, not a median, so the gap is a difference of means.

    Unpaired: the two splits share 601 of their base utterances but not all, and
    pairing on the shared subset would move the point estimate off the published
    table. Ignoring that overlap widens the interval, so this errs wide.
    """
    out = []
    for (arch, fold), (pm, pu) in PUB_SISDR.items():
        parts, means = [], {}
        for split, pub in (("test_matched", pm), ("test_unseen", pu)):
            e = _base(pd.read_csv(C.EVAL / "eval" / f"{arch}__{fold}__{split}.csv"))
            means[split] = float(e.si_sdr_out.mean())
            assert round(means[split], 2) == pub, \
                f"{arch} {fold} {split}: {means[split]:.2f} != published {pub}"
            parts.append(_parts(e, "si_sdr_out", "base", np.nanmean))
        point, lo, hi = _boot(parts, lambda v: v[0] - v[1], paired=False, n=n, seed=seed)
        out.append({"family": "sisdr_gap", "quantity": f"{arch}_{fold}",
                    "detail": "mean SI-SDR out, matched minus unseen",
                    "point": point, "ci_lo": lo, "ci_hi": hi,
                    "matched": means["test_matched"], "unseen": means["test_unseen"]})
    return pd.DataFrame(out)


def over_under_ratio(n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Ratio of the two median ratios on the mask-intent basis, pooled over both
    folds and all SNRs. A ratio OF medians, which is what the paper prints, not a
    median of per-row ratios. Paired: both numbers come from the same rows.
    """
    out = []
    for (arch, split), (pro, pru) in PUB_RATIO.items():
        e = pd.concat([pd.read_csv(p) for p in
                       sorted((C.EVAL / "eval").glob(f"{arch}__*__{split}.csv"))],
                      ignore_index=True)
        e = _base(e)
        e["ro"], e["ru"] = e.e_over / e.e_clean, e.e_under / e.e_clean
        assert round(e.ro.median(), 4) == pro and round(e.ru.median(), 4) == pru, \
            f"{arch} {split}: {e.ro.median():.4f}/{e.ru.median():.4f} != {pro}/{pru}"
        keys = pd.unique(e.base)
        parts = [_parts(e, "ro", "base", np.nanmedian, keys),
                 _parts(e, "ru", "base", np.nanmedian, keys)]
        # Matched is over-suppressive, so the paper quotes over:under; unseen is
        # under-suppressive and quoted the other way up. Keep its orientation.
        if split == "test_matched":
            point, lo, hi = _boot(parts, lambda v: v[0] / v[1], True, n, seed)
            detail = "median r_over / median r_under"
        else:
            point, lo, hi = _boot(parts, lambda v: v[1] / v[0], True, n, seed)
            detail = "median r_under / median r_over"
        out.append({"family": "over_under_ratio", "quantity": f"{arch}_{split}",
                    "detail": detail, "point": point, "ci_lo": lo, "ci_hi": hi,
                    "matched": np.nan, "unseen": np.nan})
    return pd.DataFrame(out)


def u1_median_d(n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """U1's own unit: median d per architecture, fold, low-SNR level and rung.
    The rows come from run_universal.u1_rows, so this is the registered row set
    and the registered algebra, not a re-derivation.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import run_universal as RU

    rows = _base(RU.u1_rows())
    cells = pd.read_csv(C.EVAL / "universal" / "u1_cells.csv")
    snr_low = load_gate_config(REPO / "configs" / "gate_universal.yaml"
                               )["definitions"]["snr_low"]
    out = []
    for arch in RU.ARCHS:
        for fold in ["all", *sorted(rows.fold.unique())]:
            g = rows[rows.arch == arch]
            g = g if fold == "all" else g[g.fold == fold]
            for snr in snr_low:
                h = g[g.snr == snr]
                pub = cells[(cells.arch == arch) & (cells.fold == fold)
                            & (cells.snr == snr)]
                for rung in RU.RUNGS:
                    v = h[h.rung == rung]
                    point, lo, hi, n_rows, n_base = median_ci(
                        v.d.to_numpy(), v.base.to_numpy(), n=n, seed=seed)
                    if not pub.empty and np.isfinite(point):
                        want = float(pub[f"median_d_{rung}"].iloc[0])
                        assert round(point, 4) == want, \
                            f"U1 {arch}/{fold}/{snr}/{rung}: {point:.4f} != {want}"
                    out.append({"family": "u1_median_d",
                                "quantity": f"{arch}_{fold}_snr{int(snr)}_{rung}",
                                "detail": "median d, registered rung rows",
                                "point": point, "ci_lo": lo, "ci_hi": hi,
                                "n_rows": n_rows, "n_base": n_base})
    return pd.DataFrame(out)


def d_fsd(n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """D_fsd's registered statistic: per architecture, the median over its three
    fsd seeds of the per-seed median. The bootstrap resamples base utterances and
    recomputes that whole statistic, so the point estimate is the gate's own.
    """
    m = _base(_derive(pd.read_csv(OUT / "eval" / "marven.csv")))
    low = m[m.snr <= 0]
    pub = pd.read_csv(OUT / "report2" / "D_fsd.csv").set_index("arch")
    out = []
    for arch in ("b1", "b3", "cm"):
        tags = [f"{arch}_fsd", f"{arch}_fsd_s2", f"{arch}_fsd_s3"]
        sub = low[low.tag.isin(tags)]
        keys = pd.unique(sub.base)
        for met in ("d_g", "nr_g"):
            parts = [_parts(sub[sub.tag == t], met, "base", np.nanmedian, keys)
                     for t in tags]
            point, lo, hi = _boot(parts, lambda v: np.median(np.stack(v), axis=0),
                                  paired=True, n=n, seed=seed)
            want = float(pub.loc[arch, met])
            assert abs(point - want) < 1e-9, f"D_fsd {arch} {met}: {point} != {want}"
            out.append({"family": "d_fsd", "quantity": f"{arch}_{met}",
                        "detail": "median over 3 fsd seeds of the per-seed median, SNR <= 0",
                        "point": point, "ci_lo": lo, "ci_hi": hi,
                        "n_rows": len(sub), "n_base": len(keys)})
    return pd.DataFrame(out)


def headline(n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    t = pd.concat([sisdr_gap(n, seed), over_under_ratio(n, seed),
                   u1_median_d(n, seed), d_fsd(n, seed)], ignore_index=True)
    t["n_boot"], t["seed"] = n, seed
    t["note"] = "descriptive, not part of a gate rule"
    return t


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=("hp1", "headline", "all"), default="all")
    p.add_argument("--n-boot", type=int, default=N_BOOT)
    a = p.parse_args(argv)
    CI.mkdir(parents=True, exist_ok=True)

    if a.task in ("hp1", "all"):
        t = hp1(n=a.n_boot)
        out = CI / "hp1_paired_ci.csv"
        t.to_csv(out, index=False)
        print(t.to_string(index=False))
        print(f"\n-> {out}")

    if a.task in ("headline", "all"):
        t = headline(n=a.n_boot)
        out = CI / "headline_ci.csv"
        t.to_csv(out, index=False)
        for fam, g in t.groupby("family", sort=False):
            print(f"\n== {fam} ==")
            show = g[["quantity", "point", "ci_lo", "ci_hi"]].round(4)
            print(show.to_string(index=False) if len(g) <= 12 else
                  show.head(6).to_string(index=False) + f"\n   ... {len(g)} rows")
        print(f"\n{len(t)} intervals -> {out}")


if __name__ == "__main__":
    main()
