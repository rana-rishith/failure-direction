"""Gate R3 (configs/gate_r3.yaml): heard type, unheard recording.

PowerShell, from the repo root, faildir env:
    $env:FAILDIR_ROOT = "<...>\\Failure-Direction-Datasets\\MarVEN"
    $env:FAILDIR_CKPT = "<repo>\\ckpt"
    python -m src.r3 --deepship "<...>\\DeepShip-main" --mbari "<...>\\MBARI"
    python -m src.r3 --report          # verdict from saved CSVs
--smoke runs 16 rows per condition.
"""
from __future__ import annotations

import argparse
import zlib
from pathlib import Path

import config as C  # noqa: I001  (must precede torch)
import numpy as np
import pandas as pd
import soundfile as sf
import torch

from src import models as M
from src.diverse import analyse, derive, mix

OUT = C.EVAL / "r3"
SHIPS = ("Cargo", "Tanker", "Passengership")


def decimate2(x: np.ndarray) -> np.ndarray:
    """32 kHz -> 16 kHz: zero rfft bins above 8 kHz, keep every 2nd sample."""
    n = len(x) - len(x) % 2
    X = np.fft.rfft(x[:n].astype(np.float64))
    X[n // 4:] = 0
    return np.fft.irfft(X, n)[::2].astype(np.float32)


def rng_for(uid: str, salt: str) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(f"{salt}|{uid}".encode()))


class Pool:
    def __init__(self, files: list[Path]):
        self.files = [(f, sf.info(str(f))) for f in sorted(files)]

    def crop(self, n: int, rng) -> tuple[np.ndarray, str]:
        f, info = self.files[rng.integers(len(self.files))]
        sr = info.samplerate
        need = n * (sr // C.SR)
        start = int(rng.integers(0, max(1, info.frames - need)))
        x, _ = sf.read(str(f), start=start, frames=need, dtype="float32", always_2d=True)
        x = x[:, 0]
        if sr == 2 * C.SR:
            x = decimate2(x)
        assert sr in (C.SR, 2 * C.SR), f"{f}: sr {sr}"
        x = np.pad(x, (0, max(0, n - len(x))))[:n]
        return x - x.mean(), f"{f.parent.name}/{f.name}@{start}"


def rows(man: pd.DataFrame, types, n=None) -> pd.DataFrame:
    t = man[(man.split == "test") & man.noise_type.isin(types)]
    if n is not None and len(t) > n:
        k = int(np.ceil(n / len(C.SNR_LEVELS)))
        # explicit loop: groupby.apply drops the grouping column in pandas >= 2.2.
        # Same draws as the gate (per-SNR g.sample(min(k, len(g)), random_state=0)).
        t = pd.concat([g.sample(min(k, len(g)), random_state=0) for _, g in t.groupby("target_snr_db")])
        t = t.sample(min(n, len(t)), random_state=0)
    return t.reset_index(drop=True)


def run(models, cond: str, frame: pd.DataFrame, pool: Pool | None, dev, out: Path):
    done = out / f"{cond}.csv"
    if done.exists() and len(pd.read_csv(done)) == len(frame) * len(models):
        print(f"  {cond}: complete on disk, skipped")
        return pd.read_csv(done)
    rec = []
    for i, r in frame.iterrows():
        y, _ = sf.read(C.ROOT / r.clean_path, dtype="float32")
        uid = Path(r.noisy_path).name
        if pool is None:
            x, _ = sf.read(C.ROOT / r.noisy_path, dtype="float32")
            src = "marven"
        else:
            nz, src = pool.crop(len(y), rng_for(uid, cond))
            x, _ = mix(y, nz, float(r.target_snr_db))
        n = min(len(x), len(y)); x, y = x[:n], y[:n]
        for tag, m in models.items():
            a = analyse(m, x, y, dev)
            rec.append(dict(tag=tag, cond=cond, uid=uid, noise_type=r.noise_type,
                            snr=int(r.target_snr_db), noise_src=src, **a))
        if i % 50 == 0:
            print(f"  {cond}: {i}/{len(frame)}", flush=True)
    d = pd.DataFrame(rec)
    d.to_csv(out / f"{cond}.csv", index=False)
    return d


def report(gate_contrast=0.20):
    d = pd.concat([pd.read_csv(f) for f in sorted(OUT.glob("*.csv")) if f.stem not in ("summary", "verdict", "by_snr")])
    d = derive(d, "_g")  # d, noise_removed = level-aligned; plain added below
    d["d_plain"] = (d.r_over - d.r_under) / (d.r_over + d.r_under + 1e-8)
    d["nr_plain"] = 1 - d.r_under / d.r_under_b4
    cols = ["noise_removed", "d", "nr_plain", "d_plain", "g", "sisdr_gain"]
    s = d.groupby(["tag", "cond"])[cols].median()
    s.to_csv(OUT / "summary.csv")
    d.groupby(["tag", "cond", "snr"])[cols].median().to_csv(OUT / "by_snr.csv")
    v = []
    for tag in ("b1_anthro", "b3_anthro", "cm_anthro"):
        if (tag, "R3_deepship") not in s.index:
            continue
        row = dict(tag=tag)
        for met in ("noise_removed", "d"):
            r1, r3, r4 = (s.loc[(tag, c), met] for c in ("R1_ship", "R3_deepship", "R4_weather"))
            row[f"{met}_R1"], row[f"{met}_R3"], row[f"{met}_R4"] = r1, r3, r4
            row[f"p_{met}"] = (r3 - r4) / (r1 - r4) if abs(r1 - r4) > 1e-9 else np.nan
        p, con = row["p_noise_removed"], row["noise_removed_R1"] - row["noise_removed_R4"]
        row["contrast"] = con
        row["class"] = ("no_contrast" if con < gate_contrast else
                        "type_level" if p >= 0.67 else "recording_level" if p <= 0.33 else "intermediate")
        v.append(row)
    v = pd.DataFrame(v)
    cls = v["class"].value_counts()
    claim = cls.index[0] if len(cls) and cls.iloc[0] >= 2 else "mixed"
    v["U1_R3"] = claim
    v.to_csv(OUT / "verdict.csv", index=False)
    pd.set_option("display.width", 220)
    print(s.round(3).to_string()); print(); print(v.round(3).to_string(index=False))
    print(f"\nU1-R3 verdict: {claim}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deepship"); ap.add_argument("--mbari")
    ap.add_argument("--smoke", action="store_true"); ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    if a.report:
        return report()
    OUT.mkdir(parents=True, exist_ok=True)
    dev = C.device()
    man = pd.read_csv(C.ROOT / "manifest.csv")
    lim = 16 if a.smoke else None
    ship = rows(man, ["large_commercial_ship"], lim)
    weather = rows(man, list(C.WEATHER), len(ship))
    load = lambda fam: {f"{k}_{fam}": M.load_model(k, f"{k}_{fam}", kind="best", device=dev) for k in ("b1", "b3", "cm")}
    ds = Pool([p for p in Path(a.deepship).rglob("*.wav") if p.parent.name in SHIPS])
    print(f"DeepShip pool: {len(ds.files)} files; device {dev}")
    ma = load("anthro")
    run(ma, "R1_ship", ship, None, dev, OUT)
    run(ma, "R3_deepship", ship, ds, dev, OUT)
    run(ma, "R4_weather", weather, None, dev, OUT)
    del ma; torch.cuda.empty_cache()
    if a.mbari:
        mw = load("weather")
        mb = Path(a.mbari)
        wr = rows(man, list(C.WEATHER), 16 if a.smoke else 400)
        anth = rows(man, list(C.ANTHRO), len(wr))
        run(mw, "X_R1_weather", wr, None, dev, OUT)
        run(mw, "X_mbari_storm", wr, Pool(sorted(mb.glob("storm_*.wav"))), dev, OUT)
        run(mw, "X_mbari_dry", wr, Pool(sorted(mb.glob("dry_*.wav"))), dev, OUT)
        run(mw, "X_R4_anthro", anth, None, dev, OUT)
    report()


if __name__ == "__main__":
    main()
