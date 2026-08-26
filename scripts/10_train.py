"""Stage 1.1 — train one (model, fold, seed) combination.

    python scripts/10_train.py --model mask_stft \
        --fold data/splits/fold_train-weather.json --seed 1337

Equal compute is enforced two ways: identical max_steps, and a wall-clock ceiling.
Both are written to runs/<tag>/run.json so the paper can state the budget honestly.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader

from failure_direction.data.dataset import PairDataset
from failure_direction.models import build_model
from failure_direction.utils.seed import set_seed


def main(a):
    cfg = yaml.safe_load(Path(a.config).read_text())
    tr = cfg["train"]
    set_seed(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    ds = PairDataset(cfg.get("manifest", "data/manifests/inventory.csv"), a.fold, "train",
                     crop_s=tr["crop_s"], seed=a.seed)
    dl = DataLoader(ds, batch_size=tr["batch_size"], shuffle=True, num_workers=4, drop_last=True)

    model = build_model(a.model).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=tr["lr"])
    scaler = torch.amp.GradScaler(enabled=tr["amp"])

    tag = f"{a.model}__{Path(a.fold).stem}__s{a.seed}"
    out = Path("runs") / tag
    out.mkdir(parents=True, exist_ok=True)

    step, t0 = 0, time.time()
    while step < tr["max_steps"]:
        for noisy, clean in dl:
            noisy, clean = noisy.to(dev), clean.to(dev)
            with torch.amp.autocast(dev, enabled=tr["amp"]):
                loss = torch.nn.functional.l1_loss(model(noisy), clean)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), tr["grad_clip"])
            scaler.step(opt)
            scaler.update()

            step += 1
            if step % 500 == 0:
                print(f"{tag} step {step}/{tr['max_steps']} loss {loss.item():.4f}")
            hours = (time.time() - t0) / 3600
            if step >= tr["max_steps"] or hours > tr["wallclock_ceiling_h"]:
                break
        else:
            continue
        break

    torch.save(model.state_dict(), out / "model.pt")
    (out / "run.json").write_text(json.dumps({
        "model": a.model, "fold": a.fold, "seed": a.seed,
        "steps": step, "hours": round((time.time() - t0) / 3600, 3),
        "device": torch.cuda.get_device_name(0) if dev == "cuda" else "cpu",
    }, indent=2))
    print(f"saved {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--fold", required=True)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--config", default="configs/stage1.yaml")
    main(ap.parse_args())
