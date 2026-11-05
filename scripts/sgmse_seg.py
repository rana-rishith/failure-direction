r"""SGMSE+ half-A staging for gate U2's generative arm.

SGMSE+ trains through its own Lightning script in the `sgmse` env, and that script
reads audio from directories:  <base>/train/{clean,noisy}/*.wav and <base>/valid/...
So unlike the DFN3 arm, which crops inside its own training loop, SGMSE+ needs the
half-A crops rendered to disk first. This script does only that, plus a one-file
check. Training is upstream train.py and enhancement is upstream enhance_resumable.py;
neither is reimplemented here.

The crop is the same draw as scripts/dfn_seg.py:Plan.crop -- one range per row chosen
with probability proportional to its length, a uniform start inside it, clamped so a
full window fits, seed 1234. One crop per plan row is written; SGMSE+'s own dataset
then takes a random 2.04 s sub-crop inside it at every step (shuffle_spec on the train
subset), so the crop is still redrawn during training, just inside a fixed 3 s span.

Standalone on purpose: it runs in the `sgmse` env, which cannot import the repo.

From the repo root:
    conda activate sgmse
    python scripts\sgmse_seg.py stage --plan results\segment\plan_weather.csv ^
        --base ..\sgmse\u2_weather
    python scripts\sgmse_seg.py verify --base ..\sgmse\u2_weather
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

SR = 16_000
SEED = 1234                      # same as scripts/dfn_seg.py
SPLITS = {"train": "train", "val": "valid"}   # plan name -> SGMSE+ subset name


def crop(r, win: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """One 3 s (clean, noisy) pair whose noise lies in half A. Mirrors dfn_seg.Plan.crop,
    including its behaviour on a range shorter than the window: the start is clamped so a
    full window still fits, which can reach past the range. Kept identical on purpose, so
    the two U2 arms see the same crops."""
    ranges = [tuple(int(v) for v in part.split(":")) for part in r.ranges.split(";")]
    sizes = np.array([hi - lo + 1 for lo, hi in ranges], dtype=float)
    lo, hi = ranges[int(rng.choice(len(ranges), p=sizes / sizes.sum()))]
    x, sr = sf.read(r.noisy, dtype="float32")
    y, _ = sf.read(r.clean, dtype="float32")
    assert sr == SR, f"{r.noisy}: {sr} Hz"
    n = min(len(x), len(y))
    s = max(0, min(int(rng.integers(lo, hi + 1)), n - win))
    return y[s:s + win], x[s:s + win]          # (clean, noisy)


def stage(a) -> None:
    plan = pd.read_csv(a.plan)
    win = int(plan.win.iloc[0])
    rng = np.random.default_rng(SEED)
    base = Path(a.base)
    rows, wrote, skipped = [], 0, 0
    for split, subset in SPLITS.items():
        for d in ("clean", "noisy"):
            (base / subset / d).mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(plan.itertuples()):
        subset = SPLITS.get(r.split)
        if subset is None:
            continue
        name = f"s{i:06d}.wav"
        cp, npth = base / subset / "clean" / name, base / subset / "noisy" / name
        # The rng is drawn for every row whether or not the files exist, so a resumed
        # pass writes the same audio a fresh one would.
        c, nz = crop(r, win, rng)
        if cp.exists() and npth.exists():
            skipped += 1
        else:
            sf.write(str(cp), c, SR, subtype="PCM_16")
            sf.write(str(npth), nz, SR, subtype="PCM_16")
            wrote += 1
        rows.append({"name": name, "subset": subset, "uid": r.uid,
                     "noise_type": r.noise_type, "snr": int(r.snr)})
        if (i + 1) % 2000 == 0:
            print(f"  staged {i + 1}/{len(plan)}", flush=True)
    pd.DataFrame(rows).to_csv(base / "index.csv", index=False)
    n = pd.DataFrame(rows).subset.value_counts().to_dict()
    print(f"staged {len(rows)} crops {n} ({wrote} written, {skipped} already there) -> {base}")



# ----------------------------------------------------------------- train ----
# Upstream train.py cannot do this job: it passes --ckpt as Lightning's ckpt_path,
# which RESUMES the pretrained VB-DMD run (its global_step and optimizer) instead of
# fine-tuning from its weights; it exposes --max_epochs but no --max_steps, so the
# protocol's 20,000 gradient steps cannot be set; and --nolog drops every callback, so
# nothing is saved. This does the same thing with those three fixed.
STEPS, BATCH, ACCUM, LR, CKPT_EVERY = 20_000, 1, 8, 1e-4, 500


def train(a) -> None:
    import torch
    import pytorch_lightning as pl
    from pytorch_lightning.callbacks import ModelCheckpoint

    sys.path.insert(0, str(Path(a.sgmse_dir).resolve()))   # sgmse is not installed
    from sgmse.data_module import SpecsDataModule
    from sgmse.model import ScoreModel

    # Our own checkpoints carry the same pickled SpecsDataModule in their hparams, and
    # Lightning's resume path (fit(ckpt_path=...)) gives no way to pass weights_only.
    # Allowlisting that one class is enough, and these are files this script wrote.
    torch.serialization.add_safe_globals([SpecsDataModule])

    out = Path(a.ckpt_dir) / a.tag
    out.mkdir(parents=True, exist_ok=True)
    last = out / "last.ckpt"
    steps = 2 if a.smoke else a.steps

    # torch 2.6 flipped torch.load's weights_only to True, which refuses a Lightning
    # checkpoint because it pickles SpecsDataModule. Lightning forwards the flag.
    # No gpu= kwarg: ScoreModel.__init__ sets it from gpus itself (sgmse/model.py:88).
    model = ScoreModel.load_from_checkpoint(
        a.init_ckpt, weights_only=False, map_location="cpu", strict=False,
        base_dir=a.base, batch_size=a.batch, num_workers=0, num_eval_files=0,
        # SB_16k.pt carries format="ears-wham+vb-dmd", a layout this data module does
        # not implement. Our staged dirs are the plain clean/noisy layout.
        format="default")
    print(f"[{a.tag}] init weights <- {a.init_ckpt}", flush=True)

    ck = ModelCheckpoint(dirpath=str(out), filename="step{step}", save_last=True,
                         save_top_k=0, every_n_train_steps=a.ckpt_every)
    trainer = pl.Trainer(
        accelerator="gpu", devices=1, max_steps=steps,
        accumulate_grad_batches=a.accum, logger=False, callbacks=[ck],
        num_sanity_val_steps=0, limit_val_batches=0,
        log_every_n_steps=50, enable_progress_bar=False)

    # Resume only from OUR checkpoint. Passing init_ckpt here would restore the
    # pretrained run's global_step and optimizer, which is resuming, not fine-tuning.
    resume = str(last) if last.exists() and not a.fresh else None
    print(f"[{a.tag}] steps {steps} bs {a.batch} x accum {a.accum} "
          f"(effective {a.batch * a.accum}, the protocol's) "
          f"| resume: {resume or 'no, starting at step 0'}", flush=True)
    trainer.fit(model, ckpt_path=resume)
    print(f"[{a.tag}] done at step {trainer.global_step} -> {last}", flush=True)


def verify(a) -> None:
    """Cheap wiring check: counts match, pairs align, audio is finite and the right length."""
    base = Path(a.base)
    idx = pd.read_csv(base / "index.csv")
    bad = []
    for subset in sorted(idx.subset.unique()):
        cs = sorted((base / subset / "clean").glob("*.wav"))
        ns = sorted((base / subset / "noisy").glob("*.wav"))
        if len(cs) != len(ns):
            bad.append(f"{subset}: {len(cs)} clean vs {len(ns)} noisy")
        if [p.name for p in cs] != [p.name for p in ns]:
            bad.append(f"{subset}: clean and noisy file names differ")
        print(f"{subset}: {len(cs)} pairs")
    for p in list((base / "train" / "noisy").glob("*.wav"))[:20]:
        x, sr = sf.read(str(p), dtype="float32")
        c, _ = sf.read(str(base / "train" / "clean" / p.name), dtype="float32")
        if sr != SR or len(x) != len(c) or not np.isfinite(x).all() or not np.isfinite(c).all():
            bad.append(f"{p.name}: sr {sr}, len {len(x)} vs {len(c)}, finite "
                       f"{np.isfinite(x).all()}/{np.isfinite(c).all()}")
        if np.allclose(x, c):
            bad.append(f"{p.name}: noisy and clean are identical")
    if bad:
        raise SystemExit("FAILED:\n  " + "\n  ".join(bad))
    print("verify ok")


def main(argv=None) -> None:
    ap = ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage", help="render half-A crops into SGMSE+'s directory layout")
    s.add_argument("--plan", required=True, help="CSV from src.segment --export-plan")
    s.add_argument("--base", required=True, help="SGMSE+ --base_dir to create")
    s.set_defaults(fn=stage)
    tr = sub.add_parser("train", help="fine-tune SGMSE+ on a staged half-A directory")
    tr.add_argument("--base", required=True, help="staged dir from `stage`")
    tr.add_argument("--tag", required=True, help="e.g. sgmse_seg_weather")
    tr.add_argument("--init-ckpt", required=True, help="pretrained SGMSE+, e.g. ckpt/SB_16k.pt")
    tr.add_argument("--sgmse-dir", default="../sgmse", help="the SGMSE+ checkout to import from")
    tr.add_argument("--ckpt-dir", default="ckpt")
    tr.add_argument("--steps", type=int, default=STEPS)
    tr.add_argument("--batch", type=int, default=BATCH,
                    help="micro-batch; 1 peaks at 4.45 GB, 2 at 7.29 GB on an 8 GB card")
    tr.add_argument("--accum", type=int, default=ACCUM)
    tr.add_argument("--ckpt-every", type=int, default=CKPT_EVERY)
    tr.add_argument("--fresh", action="store_true", help="ignore an existing last.ckpt")
    tr.add_argument("--smoke", action="store_true", help="2 steps, wiring only")
    tr.set_defaults(fn=train)
    v = sub.add_parser("verify", help="check a staged directory")
    v.add_argument("--base", required=True)
    v.set_defaults(fn=verify)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
