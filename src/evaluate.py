"""
Evaluation harness — the 10-cell matrix.

    python -m src.evaluate                 # all ten cells
    python -m src.evaluate --no-pesq       # ~3x faster, PESQ columns all NaN
    python -m src.evaluate --cells b1:weather:test_matched

Ten cells, not twelve: B1 and B3 across both folds and both splits, plus B4 on
both splits. B4 has no weights, so its numbers are identical regardless of which
fold label is attached.

batch_size=1, full-length audio, no cropping — metrics are computed on complete
utterances.
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

CELLS = (
    [("b1", f, s) for f in C.FAMILIES for s in ("test_matched", "test_unseen")]
    + [("b3", f, s) for f in C.FAMILIES for s in ("test_matched", "test_unseen")]
    + [("b4", "weather", "test_matched"), ("b4", "weather", "test_unseen")]
)


def cell_path(tag: str, fold: str, split: str):
    return C.RAW_EVAL / f"{tag}__{fold}__{split}.csv"


@torch.no_grad()
def evaluate(model, frame: pd.DataFrame, tag: str, fold: str, split: str,
             resume: bool = True, log_every: int = 200,
             device: str | None = None) -> pd.DataFrame:
    dev = device or C.device()
    out = cell_path(tag, fold, split)
    if resume and out.exists():
        prev = pd.read_csv(out)
        if len(prev) == len(frame):
            print(f"skip {out.name} (n={len(prev)})")
            return prev
        print(f"re-running {out.name}: has {len(prev)} rows, expected {len(frame)}")

    model.eval().to(dev)
    win = torch.hann_window(C.N_FFT, device=dev)
    rows, t0 = [], time.time()

    for i, (x, y, snr, ntype, uid) in enumerate(
            D.make_loader(frame, batch_size=1, train=False, workers=0)):
        x, y = x.to(dev), y.to(dev)
        with C.autocast():
            est, mask = model(x)
        est, mask = est.float(), mask.float()
        mag_noisy = torch.stft(x, C.N_FFT, C.HOP, window=win, return_complex=True).abs()
        mag_clean = torch.stft(y, C.N_FFT, C.HOP, window=win, return_complex=True).abs()

        xn, yn, en = x[0].cpu().numpy(), y[0].cpu().numpy(), est[0].cpu().numpy()
        rec = {
            "tag": tag, "fold": fold, "split": split, "row_idx": i, "uid": uid[0],
            "noise_type": ntype[0], "snr": int(snr[0]),
            "si_sdr_in": MT.si_sdr(x[0], y[0]), "si_sdr_out": MT.si_sdr(est[0], y[0]),
            "stoi_in": MT.safe_stoi(yn, xn), "stoi_out": MT.safe_stoi(yn, en),
            "pesq_in": MT.safe_pesq(yn, xn), "pesq_out": MT.safe_pesq(yn, en),
        }
        rec.update(MT.energy_decomposition(mask, mag_noisy, mag_clean))
        rows.append(rec)

        if log_every and (i + 1) % log_every == 0:
            el = (time.time() - t0) / 60
            print(f"  {tag}/{fold}/{split} {i+1}/{len(frame)} {el:.1f}m "
                  f"~{el/(i+1)*(len(frame)-i-1):.0f}m left", flush=True)

    d = pd.DataFrame(rows)
    C.ensure_dirs()
    d.to_csv(out, index=False)
    print(f"wrote {out.name}  n={len(d)}  {(time.time()-t0)/60:.1f}m")
    return d


def run_matrix(folds=None, cells=CELLS, do_pesq: bool = True, do_stoi: bool = True,
               resume: bool = True, log_every: int = 200) -> pd.DataFrame:
    folds = folds or D.build_folds()
    MT.reset_guards(do_stoi=do_stoi, do_pesq=do_pesq)
    C.ensure_dirs()

    parts = []
    for tag in ("b1", "b3", "b4"):
        todo = [c for c in cells if c[0] == tag]
        if not todo:
            continue
        loaded: dict[str, torch.nn.Module] = {}
        for _, fold, split in todo:
            key = f"{tag}_{fold}"
            if key not in loaded:
                loaded = {}                       # keep one model resident at a time
                if C.device() == "cuda":
                    torch.cuda.empty_cache()
                loaded[key] = M.load_model(tag, key)
            parts.append(evaluate(loaded[key], folds[fold][split], tag, fold, split,
                                  resume=resume, log_every=log_every))
        loaded.clear()
        if C.device() == "cuda":
            torch.cuda.empty_cache()

    res = pd.concat(parts, ignore_index=True)
    print("\n" + MT.STOI_GUARD.report("stoi"))
    print(MT.PESQ_GUARD.report("pesq"))
    if do_pesq and MT.PESQ_GUARD.nan_rate() > 0.5:
        print("!! PESQ produced NaN for most rows — check the conda-forge `pesq` install. "
              "Timing is the tell: wideband PESQ on 12-second files cannot be free.")
    out = C.METRICS / "eval_matrix.csv"
    res.to_csv(out, index=False)
    print(f"\nwrote {out} n={len(res)}")
    return res


def load_matrix() -> pd.DataFrame:
    """Reassemble the matrix from per-cell CSVs (or the combined file)."""
    combined = C.METRICS / "eval_matrix.csv"
    files = sorted(C.RAW_EVAL.glob("*__*__*.csv"))
    if files:
        return pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    if combined.exists():
        return pd.read_csv(combined)
    raise FileNotFoundError(f"no evaluation CSVs in {C.RAW_EVAL} — run src.evaluate first")


def b4_floor_check(res: pd.DataFrame) -> dict:
    """
    Passthrough invariants. e_over is NOT zero for an all-ones mask (~1,840 on
    matched, ~1,404 on unseen): that is phase cancellation, bins where noise sums
    destructively and noisy magnitude falls below clean. Read every trained
    model's e_over against that floor, not against zero.
    """
    b4 = res[res.tag == "b4"]
    if b4.empty:
        return {"error": "no b4 rows"}
    import numpy as np
    return {
        "si_sdr_identity": bool(np.allclose(b4.si_sdr_in, b4.si_sdr_out, atol=1e-6)),
        "under_gt_over_frac": float((b4.e_under > b4.e_over).mean()),
        "e_over_floor": b4.groupby("split").e_over.mean().round(1).to_dict(),
    }


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="FailDir evaluation matrix")
    p.add_argument("--no-pesq", action="store_true", help="skip PESQ (~3x faster)")
    p.add_argument("--no-stoi", action="store_true")
    p.add_argument("--no-resume", action="store_true", help="recompute existing cells")
    p.add_argument("--cells", nargs="*", default=None,
                   help="tag:fold:split triples, e.g. b1:weather:test_unseen")
    a = p.parse_args(argv)

    cells = CELLS
    if a.cells:
        cells = [tuple(c.split(":")) for c in a.cells]
    res = run_matrix(cells=cells, do_pesq=not a.no_pesq, do_stoi=not a.no_stoi,
                     resume=not a.no_resume)
    print("\nmeans by cell:")
    print(res.groupby(["tag", "fold", "split"])[["si_sdr_out", "stoi_out", "pesq_out"]]
            .mean().round(3).to_string())
    print("\nB4 floor:", b4_floor_check(res))


if __name__ == "__main__":
    main()
