"""Gate M0: oracle headroom of the aggressiveness-control method.

Method idea: before enhancing, choose per utterance how hard the enhancer
pushes, either by a mask exponent (Yhat = M**gamma * X) or by mixing the output
with the input (yhat = alpha * enhanced + (1 - alpha) * noisy). M1 would later
predict that choice from the 33 input features. M0 asks whether there is
anything to predict: does the per-utterance BEST gamma beat the single best
fixed gamma by enough to matter?

Pre-committed in configs/gate_universal.yaml (M0_oracle_headroom):
    data      test_matched, B1 and B3, both folds (4 cells)
    grid      gamma [0.3, 0.5, 0.7, 1.0, 1.5, 2.0], alpha [0.5, 0.7, 0.9, 1.0]
    compare   per-utterance oracle gamma vs single best global gamma, same cell
    pass_if   mean SI-SDR gain >= 0.5 dB in >= 3 of 4 cells
    on_fail   drop the method; the paper stays measurement-only

The oracle is an upper bound: picking the best of six values per utterance
always beats a fixed value somewhat, partly by selection noise. M1 tests how
much of it a predictor recovers. The secondary WER check named in the gate
needs the Whisper stage and is not run here.

Also reported (not part of the gate): the best gamma per SNR level, i.e. what
a predictor that only knew the SNR could reach, and the same comparison for alpha.

Usage, from the repo root (faildir env, FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.method_oracle                 # grid for the 4 cells, then the verdict
    python -m src.method_oracle --report        # verdict from saved grids only
"""
from __future__ import annotations

import argparse
import time

import config as C  # noqa: I001  (must precede torch)

import numpy as np
import pandas as pd
import torch

from src import data as D
from src import models as M

OUT = C.EVAL / "method"
CELLS = ("b1_weather", "b1_anthro", "b3_weather", "b3_anthro")
GAMMAS = (0.3, 0.5, 0.7, 1.0, 1.5, 2.0)
ALPHAS = (0.5, 0.7, 0.9, 1.0)
PASS_DB, PASS_CELLS = 0.5, 3


def si_sdr(est: torch.Tensor, ref: torch.Tensor, eps: float = 1e-8) -> float:
    est = est.double() - est.double().mean()
    ref = ref.double() - ref.double().mean()
    t = (est @ ref) / (ref @ ref + eps) * ref
    return float(10 * torch.log10((t @ t) / ((est - t) @ (est - t) + eps)))


@torch.no_grad()
def grid_row(model, x: np.ndarray, y: np.ndarray, dev: str) -> dict:
    xt = torch.from_numpy(x).to(dev)
    yt = torch.from_numpy(y).to(dev)
    X = M.stft(xt[None])
    _, Mk = model(xt[None])
    Mk = Mk.float().clamp(min=1e-6)
    n = xt.shape[-1]
    row = {"sisdr_in": si_sdr(xt, yt)}
    base = None
    for g in GAMMAS:
        est = M.istft(X * Mk ** g, n)[0]
        row[f"g{g}"] = si_sdr(est, yt)
        if g == 1.0:
            base = est
    for a in ALPHAS:
        row[f"a{a}"] = si_sdr(a * base + (1 - a) * xt, yt)
    return row


def run_cell(tag: str) -> pd.DataFrame:
    dev = C.device()
    arch, fam = tag.split("_")
    model = M.load_model(arch, tag, kind="best", device=dev)
    df = D.load_manifest()
    rows = df[(df.split == "test") & (df.family == fam)].reset_index(drop=True)
    out = []
    t0 = time.time()
    for k, r in enumerate(rows.itertuples()):
        x, y = D.read_pair(r)
        out.append({"uid": r.uid, "noise": r.noise_type, "snr": int(r.target_snr_db),
                    **grid_row(model, x, y, dev)})
        if (k + 1) % 250 == 0:
            print(f"  [{tag}] {k + 1}/{len(rows)}  {(time.time() - t0) / 60:.1f}m", flush=True)
    f = pd.DataFrame(out)
    OUT.mkdir(parents=True, exist_ok=True)
    f.to_csv(OUT / f"{tag}_grid.csv", index=False)
    print(f"[{tag}] {len(f)} rows -> {OUT / f'{tag}_grid.csv'}")
    return f


def headroom(f: pd.DataFrame, cols: list[str]) -> dict:
    means = f[cols].mean()
    best = means.idxmax()
    oracle = f[cols].max(axis=1).mean()
    snr_best = f.groupby("snr")[cols].mean().max(axis=1)          # best fixed value per SNR
    snr_level = (f.groupby("snr").size() * snr_best).sum() / len(f)
    return {"best_fixed": best, "best_fixed_db": float(means[best]),
            "per_snr_db": float(snr_level), "oracle_db": float(oracle),
            "oracle_gain": float(oracle - means[best]),
            "per_snr_gain": float(snr_level - means[best]),
            "oracle_picks": f[cols].idxmax(axis=1).value_counts().to_dict()}


def report(cells=CELLS) -> pd.DataFrame:
    rows = []
    for tag in cells:
        p = OUT / f"{tag}_grid.csv"
        if not p.exists():
            raise SystemExit(f"missing {p}; run without --report first")
        f = pd.read_csv(p)
        g = headroom(f, [f"g{x}" for x in GAMMAS])
        a = headroom(f, [f"a{x}" for x in ALPHAS])
        rows.append({"cell": tag, "n": len(f),
                     "sisdr_in": f.sisdr_in.mean(), "gamma1_db": f["g1.0"].mean(),
                     "gamma_best_fixed": g["best_fixed"], "gamma_best_fixed_db": g["best_fixed_db"],
                     "gamma_per_snr_gain": g["per_snr_gain"], "gamma_oracle_gain": g["oracle_gain"],
                     "alpha_best_fixed": a["best_fixed"], "alpha_oracle_gain": a["oracle_gain"],
                     "gamma_oracle_picks": g["oracle_picks"]})
        by_snr = f.groupby("snr")[[f"g{x}" for x in GAMMAS]].mean().round(2)
        print(f"\n[{tag}] mean SI-SDR (dB) by SNR and gamma:")
        print(by_snr.to_string())
    s = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("\nM0 summary (dB; gains are over the single best fixed value in the same cell):")
    cols = ["cell", "n", "sisdr_in", "gamma1_db", "gamma_best_fixed", "gamma_best_fixed_db",
            "gamma_per_snr_gain", "gamma_oracle_gain", "alpha_best_fixed", "alpha_oracle_gain"]
    print(s[cols].round(3).to_string(index=False))
    for r in s.itertuples():
        print(f"  {r.cell}: oracle gamma picks {r.gamma_oracle_picks}")
    n_pass = int((s.gamma_oracle_gain >= PASS_DB).sum())
    verdict = "PASS" if n_pass >= PASS_CELLS else "FAIL"
    print(f"\nPRE-COMMITTED M0: oracle-vs-best-fixed gamma gain >= {PASS_DB} dB in "
          f"{n_pass} of {len(s)} cells (need >= {PASS_CELLS})  ->  {verdict}")
    s.assign(verdict=verdict).to_csv(OUT / "m0_summary.csv", index=False)
    print(f"saved {OUT / 'm0_summary.csv'}")
    return s


def main(argv=None):
    p = argparse.ArgumentParser(description="Gate M0: oracle headroom of gamma / alpha control")
    p.add_argument("--report", action="store_true", help="verdict from saved grids only")
    p.add_argument("--cells", nargs="+", default=list(CELLS))
    a = p.parse_args(argv)
    if not a.report:
        for tag in a.cells:
            run_cell(tag)
    report(a.cells)


if __name__ == "__main__":
    main()
