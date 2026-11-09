"""Does d tell you anything BSS Eval does not? Reviewer item #4.

    python scripts/bss_posthoc.py                    # all arms, full split
    python scripts/bss_posthoc.py --limit 8          # smoke run
    python scripts/bss_posthoc.py --tags b1_weather dfn3

Everything here is POST HOC AND DESCRIPTIVE. No gate reads these outputs, which is
why they live under results/bss_posthoc/. The protocol requires a check computed
after the fact to say so; this is one, and it can never be read as confirmatory.

The question is whether the direction index d adds anything to the standard
decomposition, given that level alignment moves d by -0.992 to +1.150 and changed
sign on up to 69.2 % of draws (\bsBiasMin, \bsBiasMax, \bsFlipMax in the paper).
Per utterance of marven_test_v1, on the enhanced output regenerated in memory:

    SI-SIR, SI-SAR      src.bss.si_terms, the Le Roux et al. (2019) split, with
                        n = x - y as the true noise (MarVEN mixing is additive)
    region shares       src.bss.regions at the registered floor src.probe.K0
    d, d_g, g, r_over,  src.probe.score and src.probe.derive, unchanged. The
    r_under             energy split is NOT reimplemented here - a second copy is
                        the mistake src/metrics.py documents in its header.

The BSS analogue of d is (SI-SAR - SI-SIR): speech loss leaves the output outside
span{s, n} and costs SI-SAR, leftover noise lies inside it and costs SI-SIR. So d
and (SI-SAR - SI-SIR) should run opposite ways, and the disagreement table is the
answer to "what does d add": rows where d > 0 (speech loss dominates) while
SI-SAR >= SI-SIR (the artifact term is the healthier one), and the reverse.

Arms: B1/B3/CM on both MarVEN folds (matched and unseen rows of the same split),
the three FSD50K-trained models at seed 1234, and zero-shot DFN3 read from the
wavs src/dfn_marven.py already wrote - DFN3 needs the dfnet env, so it cannot be
regenerated in this process.

Writes, under FAILDIR_EVAL/bss_posthoc:
    rows.csv          per row x arm
    summary.csv       median per arm x condition x SNR, plus the within-SNR
                      Spearman of d and d_g against (SI-SAR - SI-SIR)
    disagreement.csv  the d-versus-BSS disagreement counts, with median
                      r_over, r_under and g, per arm x condition x SNR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import config as C  # noqa: E402  (must precede torch: sets KMP_DUPLICATE_LIB_OK)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from src import data as D  # noqa: E402
from src.bss import regions, si_terms  # noqa: E402
from src.probe import K0, derive, heard_types, load_split, model_fn, score  # noqa: E402
from src.probe import _from_map  # noqa: E402  (the uid->wav reader probe() itself uses)
from src.probe.rescore import map_from_index  # noqa: E402

OUT = C.EVAL / "bss_posthoc"
DFN_INDEX = C.EVAL / "labels_active" / "rows_dfn.csv"
DFN_WAVS = C.ROOT.parent.parent / "dfn3_marven_out"
# B1/B3/CM on both MarVEN folds, the FSD50K models at seed 1234 (no suffix), DFN3
TAGS = ("b1_weather", "b1_anthro", "b3_weather", "b3_anthro", "cm_weather", "cm_anthro",
        "b1_fsd", "b3_fsd", "cm_fsd", "dfn3")
MEDIAN_COLS = ("si_sir", "si_sar", "si_sdr", "r_atten", "r_amp", "r_amp6",
               "d", "d_g", "g", "r_over", "r_under")


def arm_fn(tag: str, dev: str):
    """(callable(x, uid) -> enhanced, how it was obtained)."""
    if tag == "dfn3":
        m = map_from_index(DFN_WAVS, DFN_INDEX)
        if not m:
            raise FileNotFoundError(f"no DFN3 wavs matched {DFN_WAVS} via {DFN_INDEX}")
        return _from_map(m), f"wavs {DFN_WAVS.name}"
    fn = model_fn(tag, dev)
    return (lambda x, uid: fn(x)), "in memory"


def rows_for(tag: str, frame: pd.DataFrame, dev: str, log_every: int = 200) -> pd.DataFrame:
    fn, how = arm_fn(tag, dev)
    heard = set(heard_types(tag))
    print(f"[{tag}] {len(frame)} rows, {how}, heard {sorted(heard) or 'nothing marine'}",
          flush=True)
    out = []
    for i, r in enumerate(frame.itertuples()):
        x, y = D.read_pair(r)
        e = np.ascontiguousarray(np.asarray(fn(x, r.uid), np.float32).squeeze())
        n = min(len(e), len(x))
        if len(e) != len(x):
            if abs(len(e) - len(x)) > C.HOP:
                raise ValueError(f"{r.uid}: {len(e)} samples back for {len(x)} in")
            x, y, e = x[:n], y[:n], e[:n]
        out.append({"tag": tag, "uid": r.uid, "noise_type": r.noise_type,
                    "snr": int(r.target_snr_db), "family": r.family,
                    "cond": "matched" if r.noise_type in heard else "unseen",
                    **score(x, y, e, dev),
                    **si_terms(e, y, x.astype(np.float64) - y),
                    **regions(e, y, K0, dev)})
        if log_every and (i + 1) % log_every == 0:
            print(f"  {tag} {i + 1}/{len(frame)}", flush=True)
    return derive(pd.DataFrame(out))


def check_vs_committed(f: pd.DataFrame, atol: float = 1e-6) -> None:
    """Our d and g must be the committed probe rows', per arm.

    This is a checkpoint guard, not a maths guard. FAILDIR_CKPT is set in the user
    environment to a superseded directory whose files load without error and give a
    different model: on b1_weather the stale checkpoint turns g ~ 0.99, d ~ -0.79
    into g ~ 0.62, d ~ +0.98, a sign flip on the construct with nothing raised. The
    committed rows come from src.diverse and src.probe independently and agree, so
    they are the reference. An arm with no committed rows is skipped, not invented.

    atol is 1e-6, not 0: the in-process arms reproduce the committed rows to 1e-16,
    but a wav-read arm like dfn3 lands at ~5e-8 because its committed run took the
    float32 STFT on a different device. A wrong checkpoint shows up at 1e-1, five
    orders of magnitude above the tolerance, so nothing is lost by allowing that.
    """
    for tag, q in f.groupby("tag"):
        p = C.EVAL / "probe" / tag / "rows.csv"
        if not p.exists():
            print(f"  {tag}: no committed rows to check against", flush=True)
            continue
        j = q.merge(pd.read_csv(p, usecols=["uid", "d", "g"]), on="uid",
                    suffixes=("_new", "_ref"))
        if j.empty:
            continue
        for col in ("d", "g"):
            worst = float((j[f"{col}_new"] - j[f"{col}_ref"]).abs().max())
            if not worst < atol:
                raise AssertionError(
                    f"{tag}: {col} differs from {p} by {worst:.3e} on {len(j)} rows. "
                    f"FAILDIR_CKPT is {C.CKPT} — point it at <repo>/ckpt (199 files), "
                    "not the stale 12-file directory the user environment sets.")
        print(f"  {tag}: d and g match the committed rows on {len(j)} uids", flush=True)


def _rho(q: pd.DataFrame, basis: str) -> float:
    """Spearman of the basis against the BSS analogue (SI-SAR - SI-SIR)."""
    if q[basis].nunique() < 2 or len(q) < 3:
        return float("nan")
    return float(spearmanr(q[basis], q.si_sar - q.si_sir).statistic)


def summarise(f: pd.DataFrame) -> pd.DataFrame:
    """Medians per arm x condition x SNR. Pooled rows are appended last and are
    secondary: an arm's matched and unseen rows sit at different SNRs in different
    numbers, so a pooled median mixes them."""
    out = []
    groups = [((t, c, str(s)), q) for (t, c, s), q in f.groupby(["tag", "cond", "snr"])]
    groups += [((t, c, "pooled"), q) for (t, c), q in f.groupby(["tag", "cond"])]
    for (tag, cond, snr), q in groups:
        rec = {"tag": tag, "cond": cond, "snr": snr, "n": len(q),
               "rho_d_sar_minus_sir": _rho(q, "d"), "rho_dg_sar_minus_sir": _rho(q, "d_g")}
        rec.update({c: float(q[c].median()) for c in MEDIAN_COLS})
        out.append(rec)
    return pd.DataFrame(out).sort_values(["tag", "cond", "snr"]).reset_index(drop=True)


def disagreement(f: pd.DataFrame) -> pd.DataFrame:
    """Where the direction index and the BSS terms point opposite ways.

    `d_says_loss_bss_says_noise`   d > 0 but SI-SAR >= SI-SIR
    `d_says_noise_bss_says_loss`   d < 0 but SI-SAR <  SI-SIR
    and the two agreeing cells, so the counts can be read as shares.
    """
    bss_loss = f.si_sar < f.si_sir                      # artifact is the worse term
    out = []
    for basis in ("d", "d_g"):
        pos = f[basis] > 0                              # the index says speech loss
        case = np.where(pos & ~bss_loss, "d_says_loss_bss_says_noise",
                np.where(~pos & bss_loss, "d_says_noise_bss_says_loss",
                np.where(pos, "agree_loss", "agree_noise")))
        g = f.assign(basis=basis, case=case)
        tot = g.groupby(["tag", "cond", "snr"]).size().rename("n_cell")
        for keys, q in g.groupby(["tag", "cond", "snr", "case"]):
            tag, cond, snr, c = keys
            out.append({"basis": basis, "tag": tag, "cond": cond, "snr": str(snr),
                        "case": c, "n": len(q), "n_cell": int(tot.loc[(tag, cond, snr)]),
                        "share": len(q) / int(tot.loc[(tag, cond, snr)]),
                        "r_over": float(q.r_over.median()),
                        "r_under": float(q.r_under.median()), "g": float(q.g.median()),
                        f"{basis}_med": float(q[basis].median()),
                        "si_sir": float(q.si_sir.median()),
                        "si_sar": float(q.si_sar.median())})
        for keys, q in g.groupby(["tag", "cond", "case"]):
            tag, cond, c = keys
            cell = int((g.tag == tag).mul(g.cond == cond).sum())
            out.append({"basis": basis, "tag": tag, "cond": cond, "snr": "pooled",
                        "case": c, "n": len(q), "n_cell": cell, "share": len(q) / cell,
                        "r_over": float(q.r_over.median()),
                        "r_under": float(q.r_under.median()), "g": float(q.g.median()),
                        f"{basis}_med": float(q[basis].median()),
                        "si_sir": float(q.si_sir.median()),
                        "si_sar": float(q.si_sar.median())})
    return pd.DataFrame(out).sort_values(["basis", "tag", "cond", "snr", "case"]) \
                            .reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tags", nargs="+", default=list(TAGS))
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (smoke run)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    frame = load_split()
    if a.limit:
        frame = frame.head(a.limit)
    dev = C.device()
    f = pd.concat([rows_for(t, frame, dev) for t in a.tags], ignore_index=True)
    print("checkpoint guard:", flush=True)
    check_vs_committed(f)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, frm in (("rows", f), ("summary", summarise(f)),
                      ("disagreement", disagreement(f))):
        frm.to_csv(out / f"{name}.csv", index=False)
        print(f"wrote {(out / name).resolve()}.csv  ({len(frm)} rows)")


if __name__ == "__main__":
    main()
