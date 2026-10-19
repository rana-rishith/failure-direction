"""Level-aligned Claim 3 labels (B1, train / val / test_matched, both folds).

Same rows, same model and same STFT as src.labels, plus the output level g and
the speech-loss target with level removed. See configs/gate_amend_level*.yaml for
why: B1 drops its output level at low SNR (g down to ~0.6 at -15 dB), and the
plain r_over counts that recoverable drop as destroyed speech.

Columns per row (energies are sums over bins >= DECOMP_MIN_HZ, as in src.metrics):
    g                      level of the clean component in the output
    e_clean                clean energy
    e_over_i,  e_under_i   mask intent |M||X|        (= src.labels e_over / e_under)
    e_over_lv, e_under_lv  |STFT(output)| / g        (level-aligned output; primary)
    e_over_ilv,e_under_ilv |M||X| / g                (level-aligned intent; robustness)

Usage, from the repo root (faildir env, FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.labels_level            # resumable per (fold, split)
"""
from __future__ import annotations

import argparse
import math
import time

import config as C  # noqa: I001

import numpy as np
import pandas as pd
import torch

from src import data as D
from src import models as M

OUT = C.EVAL / "labels_level"
SPLITS = ("train", "val", "test_matched")
K0 = int(math.ceil(C.DECOMP_MIN_HZ * C.N_FFT / C.SR))
G_MIN, G_MAX = 0.1, 10.0


@torch.no_grad()
def row_labels(model, x: np.ndarray, y: np.ndarray, dev: str) -> dict:
    xt = torch.from_numpy(x)[None].to(dev)
    est, Mk = model(xt)
    est = est[0].float()
    X = M.magnitude(xt)[0]
    Cm = M.magnitude(torch.from_numpy(y)[None].to(dev))[0]
    Yo = M.magnitude(est[None])[0]
    Yi = Mk[0].float() * X
    e = est.cpu().numpy().astype(np.float64)
    yc = y.astype(np.float64) - y.mean()
    g = float(np.dot(e - e.mean(), yc) / (np.dot(yc, yc) + 1e-12))
    gu = float(np.clip(g, G_MIN, G_MAX))
    sl = slice(K0, None)

    def split(Y):
        return (float(((Cm[sl] - Y[sl]).clamp(min=0) ** 2).sum()),
                float(((Y[sl] - Cm[sl]).clamp(min=0) ** 2).sum()))

    eo_i, eu_i = split(Yi)
    eo_l, eu_l = split(Yo / gu)
    eo_il, eu_il = split(Yi / gu)
    return {"g": g, "e_clean": float((Cm[sl] ** 2).sum()),
            "e_over_i": eo_i, "e_under_i": eu_i,
            "e_over_lv": eo_l, "e_under_lv": eu_l,
            "e_over_ilv": eo_il, "e_under_ilv": eu_il}


def run_split(model, frame: pd.DataFrame, arch: str, fold: str, split: str, dev: str):
    out = OUT / f"{arch}__{fold}__{split}.csv"
    if out.exists() and len(pd.read_csv(out, usecols=["uid"])) == len(frame):
        print(f"skip {out.name} (n={len(frame)})")
        return
    rows, t0 = [], time.time()
    for i in range(len(frame)):
        r = frame.iloc[i]
        x, y = D.read_pair(r)
        rows.append({"fold": fold, "split": split, "row_idx": i, "uid": r.uid,
                     "noise_type": r.noise_type, "snr": int(r.target_snr_db),
                     **row_labels(model, x, y, dev)})
        if (i + 1) % 1000 == 0:
            el = (time.time() - t0) / 60
            print(f"  {arch}/{fold}/{split} {i + 1}/{len(frame)} {el:.1f}m "
                  f"~{el / (i + 1) * (len(frame) - i - 1):.0f}m left", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {out.name} n={len(rows)} {(time.time() - t0) / 60:.1f}m", flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(description="Level-aligned Claim 3 labels")
    p.add_argument("--arch", default="b1", choices=["b1", "b3"])
    a = p.parse_args(argv)
    dev = C.device()
    folds = D.build_folds()
    for fold in C.FAMILIES:
        model = M.load_model(a.arch, f"{a.arch}_{fold}", device=dev)
        for split in SPLITS:
            run_split(model, folds[fold][split], a.arch, fold, split, dev)
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
