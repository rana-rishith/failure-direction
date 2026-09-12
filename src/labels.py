"""
Claim 3 label generation — the prediction target.

    python -m src.labels

B1 only, on train / val / test_matched of both folds (22,754 rows total).

Four design points:
  * B1 only. Claim 3 predicts the failure of one specific enhancer. The
    cross-architecture rank agreement (rho 0.60-0.99) is the JUSTIFICATION for
    treating one enhancer's labels as meaningful; it is not a reason to fit both.
  * No test_unseen. Claim 3 is within-condition magnitude prediction;
    test_matched is the held-out set. Unseen is Claims 1 and 2's territory.
  * e_noisy is included. It is the loudness feature the rho(r_over, e_clean)
    = +0.56 result made necessary, and it is admissible (computed from noisy
    audio only).
  * uid is written alongside row_idx so the join to the features can be
    validated rather than trusted.

The labels require the clean reference. That is expected and must be stated
plainly in the paper: the predictor is reference-free AT INFERENCE, but clean
references are needed DURING TRAINING to construct the targets.
"""

from __future__ import annotations

import argparse
import time

import pandas as pd
import torch

import config as C
from src import data as D
from src import metrics as MT
from src import models as M

LABEL_SPLITS = ("train", "val", "test_matched")


@torch.no_grad()
def decompose(model, frame: pd.DataFrame, tag: str, fold: str, split: str,
              resume: bool = True, log_every: int = 500,
              device: str | None = None) -> pd.DataFrame:
    dev = device or C.device()
    C.ensure_dirs()
    out = C.LABELS / f"{tag}__{fold}__{split}.csv"
    if resume and out.exists():
        prev = pd.read_csv(out)
        if len(prev) == len(frame):
            print(f"skip {out.name} (n={len(prev)})")
            return prev
        print(f"re-running {out.name}: has {len(prev)} rows, expected {len(frame)}")

    model.eval().to(dev)
    win = torch.hann_window(C.N_FFT, device=dev)
    rows, t0 = [], time.time()

    for i in range(len(frame)):
        r = frame.iloc[i]
        x, c = D.read_pair(r)
        xt = torch.from_numpy(x).unsqueeze(0).to(dev)
        ct = torch.from_numpy(c).unsqueeze(0).to(dev)
        _, mask = model(xt)
        mag_noisy = torch.stft(xt, C.N_FFT, C.HOP, window=win, return_complex=True).abs()
        mag_clean = torch.stft(ct, C.N_FFT, C.HOP, window=win, return_complex=True).abs()

        rec = {
            "tag": tag, "fold": fold, "split": split, "row_idx": i, "uid": r.uid,
            "noise_type": r.noise_type, "snr": int(r.target_snr_db),
            "speaker_id": int(r.speaker_id), "chapter_id": int(r.chapter_id),
            "utterance_id": int(r.utterance_id), "duration_sec": float(r.duration_sec),
        }
        rec.update(MT.energy_decomposition(mask.float(), mag_noisy, mag_clean))
        rows.append(rec)

        if log_every and (i + 1) % log_every == 0:
            el = (time.time() - t0) / 60
            print(f"  {tag}/{fold}/{split} {i+1}/{len(frame)} {el:.1f}m "
                  f"~{el/(i+1)*(len(frame)-i-1):.0f}m left", flush=True)

    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    print(f"wrote {out.name}  n={len(d)}  {(time.time()-t0)/60:.1f}m")
    return d


def run(folds=None, arch: str = "b1", resume: bool = True) -> pd.DataFrame:
    folds = folds or D.build_folds()
    parts = []
    for fold in C.FAMILIES:
        model = M.load_model(arch, f"{arch}_{fold}")
        for split in LABEL_SPLITS:
            parts.append(decompose(model, folds[fold][split], arch, fold, split,
                                   resume=resume))
        del model
        if C.device() == "cuda":
            torch.cuda.empty_cache()
    return pd.concat(parts, ignore_index=True)


def load_labels(arch: str = "b1") -> pd.DataFrame:
    files = sorted(C.LABELS.glob(f"{arch}__*.csv"))
    if not files:
        raise FileNotFoundError(f"no label CSVs in {C.LABELS} — run src.labels first")
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True)


def sanity(L: pd.DataFrame) -> dict:
    L = MT.add_ratios(L)
    checks = {
        "rows": len(L),
        "nan": int(L[["e_over", "e_under", "e_clean", "e_noisy"]].isna().sum().sum()),
        "degenerate_e_clean": int((L.e_clean <= 0).sum()),
        "duplicate_uid": int(L.duplicated(["fold", "split", "uid"]).sum()),
        "train_val_speaker_overlap": len(
            set(L[L.split == "train"].speaker_id) & set(L[L.split == "val"].speaker_id)),
        "train_test_speaker_overlap": len(
            set(L[L.split == "train"].speaker_id) & set(L[L.split == "test_matched"].speaker_id)),
        "top1pct_share_of_e_over": round(
            float(L.nlargest(max(1, int(0.01 * len(L))), "e_over").e_over.sum()
                  / max(L.e_over.sum(), 1e-12)), 3),
    }
    print("label sanity:", checks)
    print("\nr_over median by split x snr:")
    print(L.pivot_table(index="snr", columns="split", values="r_over",
                        aggfunc="median").round(4).to_string())
    for k in ("nan", "degenerate_e_clean", "duplicate_uid",
              "train_val_speaker_overlap", "train_test_speaker_overlap"):
        assert checks[k] == 0, f"label sanity failed on {k}: {checks[k]}"
    return checks


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Claim 3 label generation")
    p.add_argument("--arch", default="b1", choices=["b1", "b3"])
    p.add_argument("--no-resume", action="store_true")
    a = p.parse_args(argv)
    L = run(arch=a.arch, resume=not a.no_resume)
    sanity(L)


if __name__ == "__main__":
    main()
