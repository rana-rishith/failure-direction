"""DeepFilterNet3 half-A fine-tune and window enhancement: gate U2's diverse_pretrained arm.

U2 applies U1's rule (median d falls R1 > R2 > R4) to the non-bounded architectures.
That needs an R2 rung, and R2 is "unheard segment of a heard recording", so the model
must have been trained on half A of each recording and nothing else. A zero-shot DFN3
has heard neither half, which makes R1 and R2 the same measurement and the gate
vacuous for it. Hence this fine-tune.

Run with the dfnet env (no repo imports: dfnet has no pyyaml, so src.segment cannot be
imported here). From the repo root:

    # 1. in the faildir env: the crop plan and the eval windows
    python -m src.segment --fold weather --export-plan results\\segment\\plan_weather.csv
    python -m src.segment --fold weather --export-windows D:\\u2\\weather_in

    # 2. in the dfnet env: fine-tune on half A, then enhance those windows
    python scripts\\dfn_seg.py train --plan results\\segment\\plan_weather.csv --tag dfn3_seg_weather
    python scripts\\dfn_seg.py enhance --ckpt ckpt\\dfn3_seg_weather_last.pt --in D:\\u2\\weather_in --out D:\\u2\\weather_out

    # 3. back in the faildir env: score the outputs into the CSVs U1/U2 read
    python -m src.segment --fold weather --score-windows D:\\u2\\weather_out --tag dfn3

Protocol, matching the MarVEN models: 20,000 gradient steps, batch 8, lr 2e-4, 3 s
random crops drawn inside the half-A ranges, SI-SDR loss, seed 1234. Equal steps, not
equal epochs. Checkpoints are atomic and resumable (model, optimiser, step, RNG).

Three differences from src/train.py, all reported:
  - No validation or best-checkpoint selection: the step-20,000 weights are used. The
    b*_seg models take their best-val checkpoint instead. Equal compute is equal
    gradient steps either way, but the selection rule differs and the paper must say so.
  - DFN3 runs at 48 kHz, so crops are resampled 16 -> 48 kHz and the loss is at 48 kHz.
  - The loss goes through df.loss.Istft (plain torch.istft), not df_state.synthesis(),
    which is Rust and carries no gradient. Inference still uses the real synthesis, so
    enhance mode reproduces df.enhance.enhance() exactly, delay trim included.
"""
import os
import shutil
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch
import torchaudio.functional as AF
from df.enhance import df_features, enhance, init_df
from df.loss import Istft
from df.model import ModelParams
from df.utils import as_complex
from libdf import DF

SR = 16_000
STEPS, BATCH, LR, SEED = 20_000, 8, 2e-4, 1234
CKPT_EVERY, LOG_EVERY = 500, 100


def si_sdr(est, ref, eps=1e-8):
    """Batched SI-SDR in dB, mean over the batch. Same definition as src.metrics."""
    est = est - est.mean(-1, keepdim=True)
    ref = ref - ref.mean(-1, keepdim=True)
    t = (est * ref).sum(-1, keepdim=True) / ((ref * ref).sum(-1, keepdim=True) + eps) * ref
    e = est - t
    return (10 * torch.log10((t * t).sum(-1) / ((e * e).sum(-1) + eps))).mean()


class Plan:
    """Random 3 s crops whose noise lies in half A, read straight from the MarVEN files."""

    def __init__(self, csv, split, seed=SEED):
        d = pd.read_csv(csv)
        self.rows = d[d.split == split].reset_index(drop=True)
        if self.rows.empty:
            raise SystemExit(f"{csv}: no {split} rows")
        self.win = int(self.rows.win.iloc[0])
        self.rng = np.random.default_rng(seed)

    def crop(self, r):
        ranges = [tuple(int(v) for v in part.split(":")) for part in r.ranges.split(";")]
        sizes = np.array([hi - lo + 1 for lo, hi in ranges], dtype=float)
        lo, hi = ranges[int(self.rng.choice(len(ranges), p=sizes / sizes.sum()))]
        x, sr = sf.read(r.noisy, dtype="float32")
        y, _ = sf.read(r.clean, dtype="float32")
        assert sr == SR, f"{r.noisy}: {sr} Hz"
        n = min(len(x), len(y))
        s = min(int(self.rng.integers(lo, hi + 1)), n - self.win)
        return x[s:s + self.win], y[s:s + self.win]

    def batch(self, bs=BATCH):
        idx = self.rng.integers(0, len(self.rows), bs)
        xs, ys = zip(*(self.crop(self.rows.iloc[int(i)]) for i in idx))
        return (torch.from_numpy(np.stack(xs).copy()),
                torch.from_numpy(np.stack(ys).copy()))


def setup(model_name="DeepFilterNet3", dev=None):
    dev = dev or ("cuda" if torch.cuda.is_available() else "cpu")
    model, df_state, _ = init_df(model_name)
    p = ModelParams()
    istft = Istft(p.fft_size, p.hop_size,
                  torch.as_tensor(df_state.fft_window().copy())).to(dev)
    model = model.to(dev)
    return model, df_state, istft, p, dev


def forward_48k(model, df_state, istft, p, x48, dev):
    """df.enhance.enhance()'s path with a differentiable synthesis: pad by one frame,
    features from the Rust state, model, then torch.istft, then the same delay trim.

    x48 stays on the CPU: df_features() calls audio.numpy() on it and only moves the
    features to the device, exactly as df.enhance.enhance() does."""
    assert x48.device.type == "cpu", "df_features needs CPU audio (it calls .numpy())"
    n = x48.shape[-1]
    pad = torch.nn.functional.pad(x48, (0, p.fft_size))
    nb_df = getattr(model, "nb_df", getattr(model, "df_bins", p.nb_df))
    if hasattr(model, "reset_h0"):
        model.reset_h0(batch_size=x48.shape[0], device=dev)
    spec, erb_feat, spec_feat = df_features(pad, df_state, nb_df, device=dev)
    enh = model(spec.clone(), erb_feat, spec_feat)[0]
    wav = istft(as_complex(enh.squeeze(1)))
    # No delay trim here. enhance() drops fft_size - hop_size because the Rust synthesis
    # is a streaming implementation; df.loss.Istft already compensates by padding one
    # frame, so trimming again put this path 480 samples (one hop) ahead of enhance()'s
    # output and would have trained against a shifted target. Verified: correlation
    # 1.0000 against enhance() at lag 0 with this slice.
    return wav[..., :n]


def resample(x, sr_in=SR, sr_out=None):
    return AF.resample(x, sr_in, sr_out)


def save(path, model, opt, step):
    tmp = Path(str(path) + ".tmp")
    torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": step,
                "torch_rng": torch.get_rng_state(), "np_rng": np.random.get_state()}, tmp)
    os.replace(tmp, path)


def train(a):
    model, df_state, istft, p, dev = setup(a.model)
    plan = Plan(a.plan, "train")
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    steps = 2 if a.smoke else a.steps
    last = Path(a.ckpt_dir) / f"{a.tag}_last.pt"
    last.parent.mkdir(parents=True, exist_ok=True)
    step = 0
    if last.exists() and not a.fresh:
        s = torch.load(last, map_location=dev, weights_only=False)
        model.load_state_dict(s["model"])
        opt.load_state_dict(s["opt"])
        torch.set_rng_state(s["torch_rng"].cpu())
        np.random.set_state(s["np_rng"])
        step = s["step"]
        print(f"[{a.tag}] resumed at step {step}/{steps}", flush=True)
        if step >= steps:
            print(f"[{a.tag}] already complete")
            return
    torch.manual_seed(SEED + step)
    print(f"[{a.tag}] dev={dev} sr={p.sr} fft={p.fft_size} hop={p.hop_size} "
          f"| {len(plan.rows)} half-A train rows | steps {steps} bs {BATCH} lr {LR}", flush=True)

    model.train()
    t0 = time.time()
    while step < steps:
        x, y = plan.batch()
        x48, y48 = resample(x, SR, p.sr), resample(y, SR, p.sr).to(dev)
        est = forward_48k(model, df_state, istft, p, x48, dev)
        n = min(est.shape[-1], y48.shape[-1])
        loss = -si_sdr(est[..., :n], y48[..., :n])
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        if step % LOG_EVERY == 0 or a.smoke:
            print(f"[{a.tag}] {step}/{steps}  si-sdr {-loss.item():.3f}  "
                  f"{(time.time() - t0) / 60:.1f}m elapsed", flush=True)
        if step % CKPT_EVERY == 0 or step == steps:
            save(last, model, opt, step)
    save(last, model, opt, step)
    print(f"[{a.tag}] done at step {step} -> {last}")


def enhance_dir(a):
    """Inference uses the real Rust synthesis, so outputs match df.enhance exactly.
    File names are passed through untouched and index.csv is copied along: that file is
    how src.segment --score-windows maps a window back to (half, start, uid)."""
    model, df_state, _, p, dev = setup(a.model)
    if a.ckpt:
        s = torch.load(a.ckpt, map_location=dev, weights_only=False)
        model.load_state_dict(s["model"])
        print(f"loaded {a.ckpt} (step {s.get('step')})")
    else:
        print("NO --ckpt: zero-shot DFN3, which cannot answer U2 (R1 == R2 by construction)")
    model.eval()
    src, out = Path(a.in_dir), Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("*.wav"))
    todo = [f for f in files if not (out / f.name).exists()]
    print(f"{len(files)} windows, {len(files) - len(todo)} done, {len(todo)} to go", flush=True)
    t0 = time.time()
    for i, f in enumerate(todo, 1):
        x, sr = sf.read(str(f), dtype="float32")
        assert sr == SR, f"{f}: {sr} Hz"
        if x.ndim > 1:
            x = x.mean(axis=1)
        n = len(x)
        xt = torch.from_numpy(x)[None]
        e = enhance(model, df_state, AF.resample(xt, SR, p.sr))
        e = AF.resample(e, p.sr, SR)[0, :n].numpy()
        sf.write(str(out / f.name), np.pad(e, (0, max(0, n - len(e)))), SR, subtype="FLOAT")
        if i % 200 == 0:
            print(f"  {i}/{len(todo)} {(time.time() - t0) / 60:.1f}m", flush=True)
    if (src / "index.csv").exists():
        shutil.copyfile(src / "index.csv", out / "index.csv")
    print(f"wrote {len(todo)} files -> {out}")


def verify(a):
    """The self-check this module needs and pytest cannot run: `df` lives only in the
    dfnet env. forward_48k's torch synthesis must match df.enhance.enhance()'s Rust one
    sample for sample, or the fine-tune optimises against a shifted target and still
    looks healthy. The first version of this file was one hop (480 samples) out."""
    model, df_state, istft, p, dev = setup(a.model)
    model.eval()
    x, sr = sf.read(a.wav, dtype="float32")
    assert sr == SR, f"{a.wav}: {sr} Hz"
    x48 = AF.resample(torch.from_numpy(x[:3 * SR].copy())[None], SR, p.sr)
    with torch.no_grad():
        mine = forward_48k(model, df_state, istft, p, x48, dev).cpu()
        theirs = enhance(model, df_state, x48).cpu()
    n = min(mine.shape[-1], theirs.shape[-1])
    agree = si_sdr(mine[:, :n], theirs[:, :n]).item()
    print(f"forward_48k vs df.enhance: {agree:.2f} dB at lag 0")
    assert agree > 40, f"synthesis paths disagree ({agree:.2f} dB): check the delay trim"
    print("ok")


def main():
    ap = ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="fine-tune on half A only")
    t.add_argument("--plan", required=True, help="CSV from src.segment --export-plan")
    t.add_argument("--tag", required=True, help="e.g. dfn3_seg_weather")
    t.add_argument("--steps", type=int, default=STEPS)
    t.add_argument("--ckpt-dir", default="ckpt")
    t.add_argument("--model", default="DeepFilterNet3")
    t.add_argument("--fresh", action="store_true")
    t.add_argument("--smoke", action="store_true", help="2 steps, wiring only")
    t.set_defaults(fn=train)

    e = sub.add_parser("enhance", help="run a fine-tuned model over exported windows")
    e.add_argument("--in", dest="in_dir", required=True)
    e.add_argument("--out", dest="out_dir", required=True)
    e.add_argument("--ckpt", default=None)
    e.add_argument("--model", default="DeepFilterNet3")
    e.set_defaults(fn=enhance_dir)

    v = sub.add_parser("verify", help="self-check: the torch synthesis matches df.enhance")
    v.add_argument("--wav", required=True, help="any 16 kHz MarVEN noisy file")
    v.add_argument("--model", default="DeepFilterNet3")
    v.set_defaults(fn=verify)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
