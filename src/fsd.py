"""FSD50K as a broad-diversity training and test noise (gate XN2, configs/gate_overnight2.yaml).

Same B1/B3/cm architectures, protocol and MarVEN speech as src.train / src.diverse;
only the training noise changes (DEMAND -> FSD50K, 200-class vocabulary).

Clip selection (fixed before any FSD50K run)
-------------------------------------------
- EXCLUDE_VOICE: clips with any speech / singing / vocal-crowd label are never used
  (the targets are speech, so speech-like noise would make the task ill-posed).
- EXCLUDE_MARINE: clips with any rain, thunder, wind, water or water-vehicle label
  are kept out of the TRAINING pool so that all five MarVEN types stay unseen.
  The same labels define two fresh test conditions from the FSD50K eval split:
      fsd_weather   Rain / Raindrop / Thunder / Thunderstorm / Wind (no Boat label)
      fsd_boat      Boat_and_Water_vehicle
- fsd_eval: eligible eval-split clips (heard classes, unheard recordings).
- Training pool: dev split 'train'; validation noise: dev split 'val'.
- Sampling: leaf class (first label) uniform, then clip uniform within class.
  fsd_weather groups are thunder / rain / wind (uniform); fsd_boat is one group.
  Clips are mean-removed, set to unit RMS, given 10 ms fades and concatenated
  until the crop is filled; the crop starts at a random offset in the first clip.

Audio: FSD50K is 44.1 kHz. `prep` resamples the needed clips once to 16 kHz with
an FFT (band-limited) resampler and caches them as float32 WAV under
<FSD>/fsd16k/{dev,eval}/<fname>.wav plus <FSD>/fsd16k/index.csv.

Usage (repo root, FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.fsd prep  [--workers 8]          # CPU, resumable
    python -m src.fsd check
    python -m src.fsd train --model b1 --smoke     # 500 steps, tag b1_fsd_smoke
    python -m src.fsd train --model b1 [--seed 1234 --suffix ""]
"""
from __future__ import annotations

import argparse
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import config as C  # noqa: I001

import numpy as np
import pandas as pd
import soundfile as sf

FSD = Path(os.environ.get("FAILDIR_FSD", C.ROOT.parent / "FSD50K (dataset)"))
EXTRACTED = FSD / "extracted"
CACHE = FSD / "fsd16k"
SR_IN = 44_100
FADE = int(0.010 * C.SR)
MIN_RMS = 1e-4

EXCLUDE_VOICE = {
    "Human_voice", "Speech", "Male_speech_and_man_speaking", "Female_speech_and_woman_speaking",
    "Child_speech_and_kid_speaking", "Conversation", "Speech_synthesizer", "Whispering",
    "Singing", "Male_singing", "Female_singing", "Chatter", "Crowd", "Shout", "Yell",
    "Screaming", "Laughter", "Giggle", "Chuckle_and_chortle", "Crying_and_sobbing", "Cheering",
}
WEATHER_LAB = {"Rain", "Raindrop", "Thunder", "Thunderstorm", "Wind"}
BOAT_LAB = {"Boat_and_Water_vehicle"}
EXCLUDE_MARINE = WEATHER_LAB | BOAT_LAB | {
    "Ocean", "Waves_and_surf", "Water", "Stream", "Splash_and_splatter", "Gurgling", "Boiling",
    "Drip", "Trickle_and_dribble", "Liquid", "Pour", "Fill_(with_liquid)",
    "Bathtub_(filling_or_washing)", "Sink_(filling_or_washing)", "Water_tap_and_faucet", "Toilet_flush",
}
POOLS = ("train", "val", "fsd_eval", "fsd_weather", "fsd_boat")


# ------------------------------------------------------------ selection ----
def _gt(name):
    for p in (EXTRACTED / "FSD50K.ground_truth" / f"{name}.csv", FSD / "FSD50K.ground_truth" / f"{name}.csv"):
        if p.exists():
            return pd.read_csv(p)
    raise FileNotFoundError(f"FSD50K ground truth {name}.csv not found under {EXTRACTED}")


def select() -> pd.DataFrame:
    """One row per (clip, pool). A clip can sit in fsd_eval only if eligible for training classes."""
    rows = []
    for split, df in (("dev", _gt("dev")), ("eval", _gt("eval"))):
        for r in df.itertuples():
            labs = set(r.labels.split(","))
            leaf = r.labels.split(",")[0]
            if labs & EXCLUDE_VOICE:
                continue
            marine = bool(labs & EXCLUDE_MARINE)
            if split == "dev":
                if not marine:
                    rows.append((int(r.fname), "dev", r.split, leaf, r.labels))
            else:
                if not marine:
                    rows.append((int(r.fname), "eval", "fsd_eval", leaf, r.labels))
                if labs & WEATHER_LAB and not labs & BOAT_LAB:
                    # sampling group = weather kind, not the clip's leaf (secondary labels are common)
                    grp = ("thunder" if labs & {"Thunder", "Thunderstorm"} else
                           "rain" if labs & {"Rain", "Raindrop"} else "wind")
                    rows.append((int(r.fname), "eval", "fsd_weather", grp, r.labels))
                if labs & BOAT_LAB:
                    rows.append((int(r.fname), "eval", "fsd_boat", "boat", r.labels))
    return pd.DataFrame(rows, columns=["fname", "split", "pool", "leaf", "labels"])


# ------------------------------------------------------------ resample -----
def resample(x: np.ndarray, sr_in: int, sr_out: int = C.SR) -> np.ndarray:
    """FFT (band-limited) resampling, as scipy.signal.resample: brick-wall at the new Nyquist."""
    x = x.astype(np.float64)
    n = len(x)
    m = int(round(n * sr_out / sr_in))
    X = np.fft.rfft(x)
    Y = np.zeros(m // 2 + 1, dtype=complex)
    k = min(len(X), len(Y))
    Y[:k] = X[:k]
    if m % 2 == 0:
        Y[-1] = Y[-1].real
    return (np.fft.irfft(Y, m) * (m / n)).astype(np.float32)


def _src(split, fname):
    return EXTRACTED / f"FSD50K.{split}_audio" / f"{fname}.wav"


def _dst(split, fname):
    return CACHE / split / f"{fname}.wav"


def _convert(job):
    split, fname = job
    dst = _dst(split, fname)
    try:
        if dst.exists():
            y, sr = sf.read(str(dst), dtype="float32")
        else:
            x, sr = sf.read(str(_src(split, fname)), dtype="float32", always_2d=True)
            x = x.mean(axis=1)
            y = resample(x, sr) if sr != C.SR else x
            tmp = dst.with_suffix(".tmp.wav")
            sf.write(str(tmp), y, C.SR, subtype="FLOAT")
            os.replace(tmp, dst)
        yc = y.astype(np.float64) - y.mean()
        rms = float(np.sqrt(np.mean(yc ** 2))) if len(y) else 0.0
        zeros = float(np.mean(y == 0)) if len(y) else 1.0
        return fname, split, len(y), rms, zeros, "ok"
    except Exception as e:  # noqa: BLE001
        return fname, split, 0, 0.0, 1.0, f"error: {e}"


def prep(workers: int = 8) -> pd.DataFrame:
    sel = select()
    for s in ("dev", "eval"):
        (CACHE / s).mkdir(parents=True, exist_ok=True)
    jobs = sorted({(r.split, r.fname) for r in sel.itertuples()})
    missing = [j for j in jobs if not _src(*j).exists() and not _dst(*j).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} FSD50K source clips missing, e.g. {_src(*missing[0])}")
    print(f"{len(sel)} (clip, pool) rows, {len(jobs)} unique clips to cache under {CACHE}", flush=True)
    t0, out = time.time(), []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(_convert, jobs, chunksize=64)):
            out.append(r)
            if (i + 1) % 2000 == 0:
                print(f"  {i + 1}/{len(jobs)}  {(time.time() - t0) / 60:.1f} min", flush=True)
    info = pd.DataFrame(out, columns=["fname", "split", "n", "rms", "zeros", "status"])
    bad = info[info.status != "ok"]
    if len(bad):
        print(f"{len(bad)} clips failed, e.g. {bad.iloc[0].to_dict()}")
    idx = sel.merge(info, on=["fname", "split"], how="left")
    idx["usable"] = (idx.status == "ok") & (idx.rms > MIN_RMS) & (idx.n >= C.SR // 10)
    idx.to_csv(CACHE / "index.csv", index=False)
    s = idx.groupby("pool").agg(clips=("fname", "size"), usable=("usable", "sum"), classes=("leaf", "nunique"),
                                hours=("n", lambda v: v.sum() / C.SR / 3600))
    print(s.round(2).to_string())
    (CACHE / "_prep_done.txt").write_text(s.round(3).to_csv(), encoding="utf-8")
    return idx


def load_index() -> pd.DataFrame:
    p = CACHE / "index.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run `python -m src.fsd prep` first")
    return pd.read_csv(p)


# ------------------------------------------------------------- pool --------
class FsdPool:
    """Class-balanced crops built from concatenated unit-RMS clips."""

    def __init__(self, pool: str, idx: pd.DataFrame | None = None):
        idx = load_index() if idx is None else idx
        f = idx[(idx.pool == pool) & idx.usable]
        if f.empty:
            raise ValueError(f"FSD pool {pool} is empty")
        self.pool = pool
        self.by_leaf = {k: [(s, int(n)) for s, n in zip(g.split, g.fname)] for k, g in f.groupby("leaf")}
        self.leaves = sorted(self.by_leaf)
        self.n_clips = len(f)

    def _clip(self, rng):
        leaf = self.leaves[int(rng.integers(len(self.leaves)))]
        cands = self.by_leaf[leaf]
        split, fname = cands[int(rng.integers(len(cands)))]
        y, _ = sf.read(str(_dst(split, fname)), dtype="float32")
        y = y.astype(np.float64)
        y -= y.mean()
        y /= max(np.sqrt(np.mean(y ** 2)), 1e-8)
        if len(y) > 2 * FADE:
            w = 0.5 - 0.5 * np.cos(np.pi * np.arange(FADE) / FADE)
            y[:FADE] *= w
            y[-FADE:] *= w[::-1]
        return y, f"{leaf}:{fname}"

    def crop(self, n: int, rng: np.random.Generator):
        for _ in range(50):
            first, name = self._clip(rng)
            off = int(rng.integers(0, len(first)))
            parts, names, have = [first[off:]], [f"{name}@{off}"], len(first) - off
            while have < n:
                y, nm = self._clip(rng)
                parts.append(y)
                names.append(nm)
                have += len(y)
            x = np.concatenate(parts)[:n].astype(np.float32)
            xc = x - x.mean()
            if float(np.mean(xc.astype(np.float64) ** 2)) > 1e-10 and np.mean(x == 0) < 0.01:
                return xc, "+".join(names)
        raise RuntimeError(f"no usable {self.pool} crop of {n} samples")


# ------------------------------------------------------------ training -----
def train(model_key: str, tag: str, steps: int = C.TRAIN_STEPS, seed: int = C.SEED, val_every: int = C.VAL_EVERY,
          workers: int = 0, fresh: bool = False):
    """src.diverse.train with the FSD50K pool; validation set fixed at C.SEED for every seed."""
    import torch
    from torch.utils.data import DataLoader, Dataset

    from src import data as D
    from src import diverse as DV
    from src import models as M
    from src.metrics import si_sdr_loss
    from src.train import load_ckpt, save_ckpt

    class FsdMix(Dataset):
        def __init__(self, cleans, pool, seed):
            self.cleans, self.pool, self.seed, self.crop, self.epoch = list(cleans), pool, seed, C.CROP, 0

        def __len__(self):
            return len(self.cleans)

        def __getitem__(self, i):
            rng = np.random.default_rng([self.seed, self.epoch, i])
            y = D.read_mono(self.cleans[i])
            ps_ref = DV.power(y)
            n = len(y)
            if n < self.crop:
                y = np.pad(y, (0, self.crop - n))
            else:
                s = int(rng.integers(0, n - self.crop + 1))
                y = y[s:s + self.crop]
            noise, _ = self.pool.crop(self.crop, rng)
            snr = float(C.SNR_LEVELS[int(rng.integers(len(C.SNR_LEVELS)))])
            x, _ = DV.mix(y, noise, snr, ps_ref)
            return torch.from_numpy(x), torch.from_numpy(np.ascontiguousarray(y))

    def build_val(df, pool):
        rng = np.random.default_rng([C.SEED, 99])
        out = []
        for k, p in enumerate(DV.clean_paths(df, "val")[:DV.N_VAL]):
            y = D.read_mono(p)
            if len(y) > DV.VAL_LEN:
                s = (len(y) - DV.VAL_LEN) // 2
                y = y[s:s + DV.VAL_LEN]
            noise, _ = pool.crop(len(y), rng)
            x, _ = DV.mix(y, noise, float(C.SNR_LEVELS[k % len(C.SNR_LEVELS)]))
            out.append((torch.from_numpy(x)[None], torch.from_numpy(np.ascontiguousarray(y))[None]))
        return out

    dev = C.device()
    C.ensure_dirs()
    C.set_seed(seed)
    C.tune_backends()
    df = D.load_manifest()
    idx = load_index()
    ds = FsdMix(DV.clean_paths(df, "train"), FsdPool("train", idx), seed)
    val = build_val(df, FsdPool("val", idx))

    last_p, best_p = C.CKPT / f"{tag}_last.pt", C.CKPT / f"{tag}_best.pt"
    model = M.MODELS[model_key]().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=C.LR)
    scaler = torch.amp.GradScaler(dev, enabled=(dev == "cuda"))
    step, best, epoch = 0, float("inf"), 0
    if last_p.exists() and not fresh:
        step, best, epoch = load_ckpt(last_p, model, opt, scaler, dev)
        print(f"[{tag}] resumed at step {step}/{steps}, best {best:.3f}")
        if step >= steps:
            print(f"[{tag}] already complete")
            return best_p
    print(f"[{tag}] {model_key} {M.n_params(model):,} params | dev={dev} | {len(ds)} train utterances | "
          f"FSD50K train pool {ds.pool.n_clips} clips / {len(ds.pool.leaves)} classes | seed {seed} | "
          f"steps {steps} bs {C.BATCH_SIZE} lr {C.LR}", flush=True)
    model.train()
    t0 = time.time()
    while step < steps:
        ds.epoch = epoch
        dl = DataLoader(ds, batch_size=C.BATCH_SIZE, shuffle=True, num_workers=workers, drop_last=True,
                        pin_memory=(dev == "cuda"), persistent_workers=False,
                        generator=torch.Generator().manual_seed(seed + epoch))
        epoch += 1
        for x, y in dl:
            if step >= steps:
                break
            x, y = x.to(dev), y.to(dev)
            with C.autocast():
                est, _ = model(x)
            loss = si_sdr_loss(est, y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            step += 1
            if step % C.CKPT_EVERY == 0:
                save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
            if step % val_every == 0 or step == steps:
                v = DV.validate(model, val, dev)
                print(f"[{tag}] {step}/{steps}  val {v:.3f}  {(time.time() - t0) / 60:.1f}m", flush=True)
                if v < best:
                    best = v
                    save_ckpt(best_p, model, opt, scaler, step, best, epoch - 1)
                save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
    save_ckpt(last_p, model, opt, scaler, step, best, epoch - 1)
    sd = M.torch_load(best_p, map_location="cpu", weights_only=False)["model"] if best_p.exists() else model.state_dict()
    torch.save(sd, C.CKPT / f"{tag}.pt")
    print(f"[{tag}] done. best val {best:.3f}; weights-only export {tag}.pt")
    return best_p


# --------------------------------------------------------------- check -----
def check():
    idx = load_index()
    print(idx.groupby("pool").agg(rows=("fname", "size"), usable=("usable", "sum"), classes=("leaf", "nunique")).to_string())
    tr = set(idx[idx.pool == "train"].fname)
    assert not tr & set(idx[idx.pool == "val"].fname), "train/val clip overlap"
    assert set(idx[idx.pool == "train"].split) == {"dev"} and set(idx[idx.pool == "fsd_eval"].split) == {"eval"}
    for p in POOLS:
        labs = idx[idx.pool == p].labels.str.split(",")
        assert not labs.map(lambda l: bool(set(l) & EXCLUDE_VOICE)).any(), f"voice label in {p}"
        if p in ("train", "val", "fsd_eval"):
            assert not labs.map(lambda l: bool(set(l) & EXCLUDE_MARINE)).any(), f"marine label in {p}"
    pool = FsdPool("train", idx)
    rng = np.random.default_rng(0)
    t0 = time.time()
    for _ in range(20):
        x, src = pool.crop(C.CROP, rng)
        assert len(x) == C.CROP and np.isfinite(x).all()
    print(f"20 training crops in {time.time() - t0:.2f}s; example source {src[:120]}")
    print("check ok")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["prep", "check", "train"])
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--model", choices=["b1", "b3", "cm"], default="b1")
    p.add_argument("--seed", type=int, default=C.SEED)
    p.add_argument("--suffix", default="")
    p.add_argument("--smoke", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "prep":
        prep(a.workers)
    elif a.cmd == "check":
        check()
    else:
        tag = f"{a.model}_fsd{a.suffix}" + ("_smoke" if a.smoke else "")
        train(a.model, tag, steps=500 if a.smoke else C.TRAIN_STEPS, seed=a.seed,
              val_every=250 if a.smoke else C.VAL_EVERY)


if __name__ == "__main__":
    main()
