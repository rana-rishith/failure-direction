"""Controlled check of the energy split: reviewer items A, E4, E5.

    python scripts/decomp_check.py paper/revised_2026-11-07

Everything here is POST HOC AND DESCRIPTIVE. No gate reads these outputs, which is
why every file name carries `_posthoc`. The protocol requires sensitivity checks to
say so; this is one.

Part 1 (item A, item E4) runs the split on four constructed outputs whose true
direction is known, on every row of marven_test_v1, at three low cutoffs in one pass:

    identity     e = y                 r_over = r_under = 0 exactly
    uniform      e = a*y               plain r_over = (1-a)^2, r_under = 0, d = +1.
                                       d_g = 0 by construction for a >= G_MIN: the
                                       fit returns g = a, so |STFT(e)|/g == |S|.
                                       a = 0.05 crosses the clamp, which is E5's teeth.
    leftover     e = y + b*(x - y)     true direction -1; b = 1 IS passthrough, so it
                                       must reproduce the stored floor exactly. The gap
                                       from -1 is the phase drift item A asks for.
    nonuniform   y, 30% of 128 ms      pure speech loss, true direction +1, and the one
                 blocks zeroed         arm that tests whether level alignment can still
                                       see speech loss (d_g is not 0 by construction).

Part 2 (the level-alignment bias, and E5) reads the committed results/probe/*/rows.csv
and measures the bias of the `_g` basis with the paper's own g — the estimator in
src.probe.score — rather than in a magnitude-domain simulation. It replaces
scripts/basis_bias_sim.py as the source of the four \\bs* macros the paper cites.

The split is NOT redefined here: `_ratios` is imported from src.diverse, the same
implementation behind every number in results/. The g lines mirror src.probe.score and
are asserted equal to it on the first row.

Writes, under FAILDIR_EVAL/decomp_check:
    rows_posthoc.csv      per row x arm x cutoff
    summary_posthoc.csv   median per arm x cutoff x SNR, both bases
    bias_posthoc.csv      part 2, per probe arm x SNR
and <out_dir>/newresults_basis.tex (the macros paper.tex reads).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import config as C  # noqa: E402  (must precede torch: sets KMP_DUPLICATE_LIB_OK)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from src import data as D  # noqa: E402
from src.diverse import G_MAX, G_MIN, _ratios  # noqa: E402
from src.models import magnitude  # noqa: E402
from src.probe import load_split  # noqa: E402

OUT = C.EVAL / "decomp_check"
K0S = (1, 2, 4)                                 # 31.25, 62.5, 125 Hz; 2 is the registered one
BLOCK = int(0.128 * C.SR)                       # 128 ms
MUTE = 0.30
ARMS = ([("identity", 1.0)]
        + [("uniform", a) for a in (0.9, 0.5, 0.2, 0.05)]
        + [("leftover", b) for b in (0.25, 0.5, 1.0)]
        + [("nonuniform", MUTE)])
EXTERNAL = ("dfn3", "sgmse")                    # not trained here; the only arms that clamp


def _mag(a: np.ndarray) -> torch.Tensor:
    return magnitude(torch.from_numpy(np.ascontiguousarray(a, np.float32))[None])[0]


def _dirx(ro: float, ru: float) -> float:
    """Same algebra as src.probe.derive, which needs a frame of band-suffixed columns."""
    return (ro - ru) / (ro + ru + 1e-8)


def _mute(y: np.ndarray, uid: str) -> np.ndarray:
    """y with a seeded MUTE share of 128 ms blocks zeroed. Seeded from C.SEED and the
    uid; sha256 because str hash() is salted per run."""
    nb = -(-len(y) // BLOCK)
    uh = int(hashlib.sha256(uid.encode()).hexdigest()[:16], 16)
    keep = np.ones(nb, bool)
    keep[np.random.default_rng([C.SEED, uh]).permutation(nb)[:round(MUTE * nb)]] = False
    return y * np.repeat(keep, BLOCK)[:len(y)].astype(np.float32)


def _arms(x: np.ndarray, y: np.ndarray, uid: str):
    """(arm, param, e) for every constructed output. n is built in float64 so that
    b = 1 gives back x bit-exactly and the floor assert can hold to 1e-12."""
    n = x.astype(np.float64) - y
    for arm, p in ARMS:
        if arm == "identity":
            e = y
        elif arm == "uniform":
            e = (p * y.astype(np.float64)).astype(np.float32)
        elif arm == "leftover":
            e = (y + p * n).astype(np.float32)
        else:
            e = _mute(y, uid)
        yield arm, p, e


def run(frame: pd.DataFrame, log_every: int = 200) -> pd.DataFrame:
    rows = []
    for i, r in enumerate(frame.itertuples()):
        x, y = D.read_pair(r)
        X, S = _mag(x), _mag(y)
        # the floor depends on (x, y) only, so once per utterance per cutoff, not per arm
        floor = {k: _ratios(X, S, X, (slice(k, None),))[:2] for k in K0S}
        yc = y.astype(np.float64) - y.mean()
        for arm, p, e in _arms(x, y, r.uid):
            g = float(np.dot(e.astype(np.float64) - e.mean(), yc) / (np.dot(yc, yc) + 1e-12))
            gu = float(np.clip(g, G_MIN, G_MAX))
            Y = _mag(e)
            for k in K0S:
                sl = (slice(k, None),)
                ro, ru, _ = _ratios(Y, S, X, sl)
                rog, rug, _ = _ratios(Y / gu, S, X, sl)
                rob, rub = floor[k]
                rows.append({
                    "uid": r.uid, "noise_type": r.noise_type, "snr": r.target_snr_db,
                    "arm": arm, "param": p, "k0": k, "hz": k * C.SR / C.N_FFT,
                    "r_over": ro, "r_under": ru, "d": _dirx(ro, ru),
                    "r_over_g": rog, "r_under_g": rug, "d_g": _dirx(rog, rug),
                    "g": g, "clamped": int(g != gu),
                    "r_over_b4": rob, "r_under_b4": rub,
                })
        if log_every and (i + 1) % log_every == 0:
            print(f"  {i + 1}/{len(frame)}", flush=True)
    return pd.DataFrame(rows)


def check(f: pd.DataFrame) -> None:
    """The arms have answers fixed by algebra. These must fail loudly."""
    i = f[f.arm == "identity"]
    assert i.r_over.max() < 1e-10 and i.r_under.max() < 1e-10, "identity is not exact"
    u = f[f.arm == "uniform"]
    assert np.allclose(u.r_over, (1 - u.param) ** 2, atol=1e-6), "uniform r_over != (1-a)^2"
    assert u.r_under.max() < 1e-10, "uniform added energy"
    b = f[(f.arm == "leftover") & (f.param == 1.0) & (f.k0 == 2)]
    assert np.allclose(b.r_over, b.r_over_b4, atol=1e-12), "b=1 is not the stored floor"
    assert np.allclose(b.r_under, b.r_under_b4, atol=1e-12), "b=1 is not the stored floor"


def check_vs_score(frame: pd.DataFrame) -> None:
    """Our g and our k0=2 split must be src.probe.score's, not a second estimator."""
    from src.probe import score
    r = next(frame.itertuples())
    x, y = D.read_pair(r)
    yc = y.astype(np.float64) - y.mean()
    S, X = _mag(y), _mag(x)
    for arm, _, e in _arms(x, y, r.uid):
        s = score(x, y, e)
        g = float(np.dot(e.astype(np.float64) - e.mean(), yc) / (np.dot(yc, yc) + 1e-12))
        assert g == s["g"], f"{arm}: g {g!r} != score {s['g']!r}"
        ro, ru, _ = _ratios(_mag(e), S, X, (slice(2, None),))
        assert (ro, ru) == (s["r_over"], s["r_under"]), f"{arm}: split != score"


def summarise(f: pd.DataFrame) -> pd.DataFrame:
    g = f.groupby(["arm", "param", "k0", "hz", "snr"])
    s = g[["d", "d_g", "r_over", "r_under", "r_over_g", "r_under_g",
           "r_over_b4", "r_under_b4", "g"]].median()
    s["n"] = g.size()
    s["clamped_pct"] = 100.0 * g.clamped.mean()
    return s.reset_index()


def bias(probe_dir: Path) -> pd.DataFrame:
    """Part 2: the `_g` bias on real enhancers, per probe arm and SNR, 62.5 Hz band.
    E5 comes from the same files: `g` is stored unclamped."""
    rows = []
    for p in sorted(probe_dir.glob("*/rows.csv")):
        f = pd.read_csv(p, usecols=["snr", "g", "d", "d_g"])
        for snr, q in f.groupby("snr"):
            rows.append({
                "tag": p.parent.name, "snr": snr, "n": len(q),
                "bias": float((q.d_g - q.d).mean()),
                "flip_pct": 100.0 * float((np.sign(q.d_g) != np.sign(q.d)).mean()),
                "rho": float(spearmanr(q.d, q.d_g)[0]),
                "clamped": int(((q.g < G_MIN) | (q.g > G_MAX)).sum()),
                "g_min": float(q.g.min()), "g_max": float(q.g.max()),
            })
    if not rows:
        raise FileNotFoundError(f"no rows.csv under {probe_dir}")
    return pd.DataFrame(rows)


def macros(s: pd.DataFrame, b: pd.DataFrame, out_dir: Path) -> Path:
    """The four \\bs* macros the paper already cites, now measured on real audio with
    the paper's own g, plus the phase drift, the clamp share and max g."""
    t = b[~b.tag.isin(EXTERNAL)]                             # trained B1/B3/CM arms
    pt = s[(s.arm == "leftover") & (s.param == 1.0) & (s.k0 == 2)].set_index("snr")
    drift = pt.d + 1.0                                       # distance of median d from -1
    m = {
        "BiasMin": f"{t.bias.min():+.3f}", "BiasMax": f"{t.bias.max():+.3f}",
        "RhoMin": f"{t.rho.min():.3f}", "FlipMax": f"{t.flip_pct.max():.1f}\\,\\%",
        "DriftMin": f"{drift.min():.3f}", "DriftMax": f"{drift.max():.3f}",
        "DriftP20": f"{drift.loc[20]:.3f}",
        "ClampRows": f"{int(b.clamped.sum()):,}".replace(",", "{,}"),
        "ClampTotal": f"{int(b.n.sum()):,}".replace(",", "{,}"),
        "ClampPct": f"{100.0 * b.clamped.sum() / b.n.sum():.4f}\\,\\%",
        "GMax": f"{b.g_max.max():.3f}",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "newresults_basis.tex"
    p.write_text("% written by scripts/decomp_check.py - post hoc, no gate reads this\n"
                 + "".join(f"\\newcommand{{\\bs{k}}}{{{v}}}\n" for k, v in m.items()))
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out_dir", help="where newresults_basis.tex goes, e.g. paper/revised_2026-11-07")
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (smoke run, no .tex)")
    a = ap.parse_args()

    frame = load_split()
    if a.limit:
        frame = frame.head(a.limit)
    check_vs_score(frame)
    print(f"part 1: {len(frame)} rows x {len(ARMS)} arms x {len(K0S)} cutoffs", flush=True)
    f = run(frame)
    check(f)
    s = summarise(f)
    b = bias(C.EVAL / "probe")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, frm in (("rows_posthoc", f), ("summary_posthoc", s), ("bias_posthoc", b)):
        frm.to_csv(OUT / f"{name}.csv", index=False)
        print(f"wrote {(OUT / name).resolve()}.csv  ({len(frm)} rows)")
    if a.limit:
        print("--limit set: macros not written")
        return
    print(f"wrote {macros(s, b, Path(a.out_dir)).resolve()}")


if __name__ == "__main__":
    main()
