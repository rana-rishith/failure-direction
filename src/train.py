"""
Stage 1 trainer — crash-resumable, equal-compute.

    python -m src.train --model b1 --fold weather --steps 20000

Re-run the exact same command after any crash: it resumes from the last atomic
checkpoint. Use --fresh to start over (which renames any existing best
checkpoint rather than destroying it).

`steps` is held constant across every baseline and both folds. That is what
makes the comparison equal-compute despite the 38.3 h / 25.3 h family imbalance.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import torch

import config as C
from src import data as D
from src import models as M
from src.metrics import si_sdr_loss


# ------------------------------------------------------------ checkpoints ----
def save_ckpt(path: Path, model, opt, scaler, step: int, best: float, epoch: int) -> None:
    """Atomic: write .tmp then os.replace. A crash mid-save cannot truncate."""
    tmp = path.with_suffix(".tmp")
    torch.save({
        "model": model.state_dict(),
        "opt": opt.state_dict(),
        "scaler": scaler.state_dict(),
        "step": step, "best": best, "epoch": epoch,
        "torch_rng": torch.get_rng_state(),
        "np_rng": np.random.get_state(),
        "config": {"n_fft": C.N_FFT, "hop": C.HOP, "sr": C.SR},
    }, tmp)
    os.replace(tmp, path)


def load_ckpt(path: Path, model, opt, scaler, device: str):
    s = M.torch_load(path, map_location=device, weights_only=False)
    model.load_state_dict(s["model"])
    opt.load_state_dict(s["opt"])
    scaler.load_state_dict(s["scaler"])
    torch.set_rng_state(s["torch_rng"].cpu() if torch.is_tensor(s["torch_rng"]) else s["torch_rng"])
    np.random.set_state(s["np_rng"])
    return s["step"], s["best"], s.get("epoch", 0)


# -------------------------------------------------------------- validation ---
@torch.no_grad()
def validate(model, frame, device: str, n_rows: int = C.VAL_ROWS) -> float:
    """
    Deterministic but speaker-skewed: it reads the first n_rows of the val split
    unshuffled, on full-length audio. Fine for early stopping. Do NOT report it
    as a metric — validation and evaluation numbers do not reconcile and should
    not be made to (evaluation uses full test frames).
    """
    was_training = model.training
    model.eval()
    losses = []
    dl = D.make_loader(frame.head(n_rows), batch_size=1, train=False, workers=0)
    for x, y, *_ in dl:
        with C.autocast():
            est, _ = model(x.to(device))
        losses.append(float(si_sdr_loss(est, y.to(device))))
    if was_training:
        model.train()
    return float(np.mean(losses)) if losses else float("nan")


# ------------------------------------------------------------------ train ----
def train(model_key: str, fold: dict, tag: str, steps: int = C.TRAIN_STEPS,
          bs: int = C.BATCH_SIZE, lr: float = C.LR, val_every: int = C.VAL_EVERY,
          ckpt_every: int = C.CKPT_EVERY, fresh: bool = False, workers: int = 0,
          seed: int = C.SEED, device: str | None = None) -> Path:
    dev = device or C.device()
    C.ensure_dirs()
    C.set_seed(seed)
    C.tune_backends()

    last_p, best_p = C.CKPT / f"{tag}_last.pt", C.CKPT / f"{tag}_best.pt"
    if fresh:
        for p in (last_p, best_p):
            if p.exists():
                p.rename(p.with_name(p.stem + "_old.pt"))
                print(f"[{tag}] --fresh: moved {p.name} -> {p.stem}_old.pt")

    model = M.MODELS[model_key]().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    scaler = torch.amp.GradScaler(dev, enabled=(dev == "cuda"))
    step, best, epoch = 0, float("inf"), 0

    if last_p.exists() and not fresh:
        step, best, epoch = load_ckpt(last_p, model, opt, scaler, dev)
        print(f"[{tag}] resumed at step {step}/{steps}, best {best:.3f}")
        if step >= steps:
            export = C.CKPT / f"{tag}.pt"
            if not export.exists() and best_p.exists():
                torch.save(M.torch_load(best_p, map_location="cpu",
                                        weights_only=False)["model"], export)
                print(f"[{tag}] wrote missing weights-only export {export.name}")
            print(f"[{tag}] already complete — nothing to do")
            return best_p if best_p.exists() else last_p

    print(f"[{tag}] {model_key} {M.n_params(model):,} params | dev={dev} | "
          f"train rows {len(fold['train'])} | steps {steps} bs {bs} lr {lr}")

    dl = D.make_loader(fold["train"], batch_size=bs, train=True, workers=workers, seed=seed)
    model.train()
    t0 = time.time()
    try:
        while step < steps:
            epoch += 1
            for x, y, *_ in dl:
                if step >= steps:
                    break
                x, y = x.to(dev), y.to(dev)
                with C.autocast():
                    est, _ = model(x)
                loss = si_sdr_loss(est, y)          # fp32, outside autocast
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                step += 1

                if step % ckpt_every == 0:
                    save_ckpt(last_p, model, opt, scaler, step, best, epoch)

                if step % val_every == 0 or step == steps:
                    v = validate(model, fold["val"], dev)
                    mins = (time.time() - t0) / 60
                    print(f"[{tag}] {step}/{steps}  val {v:.3f}  {mins:.1f}m elapsed",
                          flush=True)
                    if v < best:
                        best = v
                        save_ckpt(best_p, model, opt, scaler, step, best, epoch)
                    save_ckpt(last_p, model, opt, scaler, step, best, epoch)
    except KeyboardInterrupt:
        save_ckpt(last_p, model, opt, scaler, step, best, epoch)
        print(f"\n[{tag}] interrupted at step {step} — state saved, rerun to resume")
        return last_p

    save_ckpt(last_p, model, opt, scaler, step, best, epoch)

    # Portable export: the resumable checkpoints carry optimiser state and RNG
    # (~3x the size), so also write a bare state_dict of the BEST weights. That
    # is the artifact to ship, and it is what `<tag>.pt` means everywhere else.
    export = C.CKPT / f"{tag}.pt"
    best_sd = model.state_dict()
    if best_p.exists():
        best_sd = M.torch_load(best_p, map_location="cpu", weights_only=False)["model"]
    torch.save(best_sd, export)
    print(f"[{tag}] done at step {step}. best val {best:.3f} -> {best_p.name} "
          f"(weights-only export: {export.name})")
    return best_p


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="FailDir trainer")
    p.add_argument("--model", choices=["b1", "b3"], required=True,
                   help="b4 (Passthrough) has no weights and needs no training")
    p.add_argument("--fold", choices=list(C.FAMILIES), required=True)
    p.add_argument("--steps", type=int, default=C.TRAIN_STEPS)
    p.add_argument("--bs", type=int, default=C.BATCH_SIZE)
    p.add_argument("--lr", type=float, default=C.LR)
    p.add_argument("--val-every", type=int, default=C.VAL_EVERY)
    p.add_argument("--ckpt-every", type=int, default=C.CKPT_EVERY)
    p.add_argument("--workers", type=int, default=0,
                   help="0 is required in Jupyter on Windows; >0 is fine from a terminal")
    p.add_argument("--seed", type=int, default=C.SEED)
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--tag", default=None)
    a = p.parse_args(argv)

    folds = D.build_folds()
    print("leakage checks passed")
    train(a.model, folds[a.fold], a.tag or f"{a.model}_{a.fold}", a.steps, a.bs, a.lr,
          a.val_every, a.ckpt_every, a.fresh, a.workers, a.seed)


if __name__ == "__main__":
    main()
