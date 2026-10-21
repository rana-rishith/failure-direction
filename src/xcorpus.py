"""Overnight cross-corpus run (configs/gate_overnight.yaml).

Subcommands, from the repo root (faildir env; FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.xcorpus build --deepship D --mbari M --demand DM --vbdmd V [--smoke]
    python -m src.xcorpus eval [--smoke]          # every checkpoint x every condition (GPU)
    python -m src.xcorpus ext-prep --sgmse-dir S  # input folders for DFN3 / SGMSE+
    python -m src.xcorpus ext-score --sgmse-dir S # score DFN3 / SGMSE+ outputs
    python -m src.xcorpus report
build / ext-prep / ext-score / report are numpy-only; eval imports torch.
Everything is resumable and writes only under results/xcorpus (or FAILDIR_EVAL).
"""
from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import zlib
from pathlib import Path

import config as C  # noqa: I001
import numpy as np
import pandas as pd
import soundfile as sf

OUT = C.EVAL / "xcorpus"
MIX = OUT / "mix"
SR = C.SR
N_PER_SNR = 50
SHIPS = ("Cargo", "Tanker", "Passengership")
# copied from src/diverse.py (which imports torch); eval asserts they still match
HOLDOUT = ("DLIVING", "OOFFICE", "TCAR")
TRAIN_FRAC = 0.8
EXT_CONDS = ["deepship_ship", "deepship_tug", "mbari_storm", "mbari_dry", "dem_A", "dem_B", "dem_H"]
FSD_CONDS = ["fsd_eval", "fsd_weather", "fsd_boat"]       # gate XN2; built only with --fsd
PAIRED = ["dem_A", "dem_H", "marven", "deepship_ship", "mbari_storm", "mbari_dry"]   # SGMSE order per base row
HEARD_P, UNSEEN_P = ["dem_A", "dem_H"], ["marven", "deepship_ship", "mbari_storm", "mbari_dry"]


# ------------------------------------------------------------------ audio ---
def power(x):
    x = x.astype(np.float64)
    return float(np.mean((x - x.mean()) ** 2))


def mix(clean, noise, snr_db):
    """src.diverse.mix semantics: mean-removed powers, noisy = clean + g * noise."""
    g = math.sqrt(power(clean) / (max(power(noise), 1e-12) * 10 ** (snr_db / 10)))
    return (clean + g * noise).astype(np.float32), g


def decimate2(x):
    n = len(x) - len(x) % 2
    X = np.fft.rfft(x[:n].astype(np.float64))
    X[n // 4:] = 0
    return np.fft.irfft(X, n)[::2].astype(np.float32)


def usable(x):
    """Reject digital silence / dropouts: hydrophone archives contain gaps."""
    return power(x) > 1e-10 and np.mean(x == 0) < 0.01


class FilePool:
    """Random crops from long recordings (DeepShip 32 kHz, MBARI 16 kHz)."""

    def __init__(self, files):
        self.files = [(str(f), sf.info(str(f))) for f in sorted(files)]
        if not self.files:
            raise FileNotFoundError("empty noise pool")

    def crop(self, n, rng):
        for _ in range(50):
            f, info = self.files[int(rng.integers(len(self.files)))]
            k = info.samplerate // SR
            assert info.samplerate in (SR, 2 * SR), f"{f}: {info.samplerate} Hz"
            need = n * k
            if info.frames < need:
                continue
            start = int(rng.integers(0, info.frames - need + 1))
            x, _ = sf.read(f, start=start, frames=need, dtype="float32", always_2d=True)
            x = x[:, 0]
            if k == 2:
                x = decimate2(x)
            x = x[:n]
            if len(x) == n and usable(x):
                return x - x.mean(), f"{Path(f).parent.name}/{Path(f).name}@{start}"
        raise RuntimeError("no usable crop after 50 draws")


class DemandPool:
    """dem_A / dem_B / dem_H exactly as src.diverse.noise_pool + pick_noise."""

    def __init__(self, root, cond):
        hold = set(HOLDOUT)
        self.regions = []
        for f in sorted(Path(root).glob("*/ch*.wav")):
            env, n = f.parent.name.upper(), sf.info(str(f)).frames
            cut = int(TRAIN_FRAC * n)
            if cond == "dem_A" and env not in hold:
                self.regions.append((env, str(f), 0, cut))
            elif cond == "dem_B" and env not in hold:
                self.regions.append((env, str(f), cut, n))
            elif cond == "dem_H" and env in hold:
                self.regions.append((env, str(f), 0, n))
        if not self.regions:
            raise FileNotFoundError(f"no DEMAND regions for {cond} under {root}")
        self.envs = sorted({r[0] for r in self.regions})

    def crop(self, n, rng):
        for _ in range(50):
            env = self.envs[int(rng.integers(len(self.envs)))]
            cands = [r for r in self.regions if r[0] == env and r[3] - r[2] >= n]
            if not cands:
                continue
            _, path, lo, hi = cands[int(rng.integers(len(cands)))]
            start = int(rng.integers(lo, hi - n + 1))
            x, _ = sf.read(path, start=start, frames=n, dtype="float32")
            if x.ndim > 1:
                x = x.mean(axis=1)
            if usable(x):
                return x - x.mean(), f"{env}/{Path(path).stem}@{start}"
        raise RuntimeError(f"no usable DEMAND crop of {n} samples")


# ------------------------------------------------------------------ build ---
def base_rows(man, smoke=False):
    t = man[man.split == "test"]
    k = 2 if smoke else N_PER_SNR
    parts = []
    for snr, g in t.groupby("target_snr_db"):
        s = g.sample(min(k, len(g)), random_state=1).copy()
        s["base_rank"] = range(len(s))
        parts.append(s)
    b = pd.concat(parts).sort_values(["base_rank", "target_snr_db"]).reset_index(drop=True)
    b["uid"] = b.noisy_path.map(lambda p: Path(p).stem)
    return b


def build(a):
    root = C.ROOT
    man = pd.read_csv(root / "manifest.csv")
    base = base_rows(man, a.smoke)
    parts_dir = OUT / "manifest_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    pools = {
        "deepship_ship": lambda: FilePool([p for p in Path(a.deepship).rglob("*.wav") if p.parent.name in SHIPS]),
        "deepship_tug": lambda: FilePool([p for p in Path(a.deepship).rglob("*.wav") if p.parent.name == "Tug"]),
        "mbari_storm": lambda: FilePool(Path(a.mbari).glob("storm_*.wav")),
        "mbari_dry": lambda: FilePool(Path(a.mbari).glob("dry_*.wav")),
        "dem_A": lambda: DemandPool(a.demand, "dem_A"),
        "dem_B": lambda: DemandPool(a.demand, "dem_B"),
        "dem_H": lambda: DemandPool(a.demand, "dem_H"),
    }
    for c in FSD_CONDS:
        pools[c] = (lambda c=c: __import__("src.fsd", fromlist=["FsdPool"]).FsdPool(c))
    conds = EXT_CONDS + (FSD_CONDS if a.fsd else [])
    # MarVEN as shipped: all test rows (the base rows are a subset)
    t = man[man.split == "test"].copy()
    if a.smoke:
        t = t[t.noisy_path.isin(base.noisy_path)]
    t["uid"] = t.noisy_path.map(lambda p: Path(p).stem)
    bset = dict(zip(base.uid, base.base_rank))
    mv = pd.DataFrame(dict(cond="marven", uid=t.uid, base_uid=t.uid.where(t.uid.isin(bset.keys())),
                           base_rank=t.uid.map(bset), base_noise_type=t.noise_type,
                           snr=t.target_snr_db, noisy=[str(root / p) for p in t.noisy_path],
                           clean=[str(root / p) for p in t.clean_path], src="marven"))
    mv.to_csv(parts_dir / "marven.csv", index=False)
    print(f"marven: {len(mv)} rows ({mv.base_uid.notna().sum()} base)")
    for cond in conds:
        part = parts_dir / f"{cond}.csv"
        if part.exists() and len(pd.read_csv(part)) == len(base):
            print(f"{cond}: complete, skipped")
            continue
        pool = pools[cond]()
        d = MIX / cond
        d.mkdir(parents=True, exist_ok=True)
        rec = []
        for i, r in enumerate(base.itertuples()):
            y, sr = sf.read(root / r.clean_path, dtype="float32")
            assert sr == SR
            nz, src = pool.crop(len(y), np.random.default_rng(zlib.crc32(f"{cond}|{r.uid}".encode())))
            x, gain = mix(y, nz, float(r.target_snr_db))
            p = d / f"{r.uid}.wav"
            if not p.exists():
                sf.write(str(p), x, SR, subtype="FLOAT")
            rec.append(dict(cond=cond, uid=r.uid, base_uid=r.uid, base_rank=r.base_rank,
                            base_noise_type=r.noise_type, snr=r.target_snr_db, noisy=str(p),
                            clean=str(root / r.clean_path), src=src, mix_gain=gain))
            if i % 100 == 0:
                print(f"  {cond}: {i}/{len(base)}", flush=True)
        pd.DataFrame(rec).to_csv(part, index=False)
        print(f"{cond}: {len(rec)} mixtures")
    # VoiceBank-DEMAND test as shipped
    vb = Path(a.vbdmd) / "test"
    names = sorted(p.name for p in (vb / "noisy").glob("*.wav"))
    rng = np.random.default_rng(1)
    names = [names[i] for i in rng.permutation(len(names))]
    if a.smoke:
        names = names[:8]
    pd.DataFrame(dict(cond="vbdmd_test", uid=[Path(n).stem for n in names], base_uid=None,
                      base_rank=range(len(names)), base_noise_type="vbdmd", snr=np.nan,
                      noisy=[str(vb / "noisy" / n) for n in names], clean=[str(vb / "clean" / n) for n in names],
                      src="vbdmd")).to_csv(parts_dir / "vbdmd_test.csv", index=False)
    m = pd.concat([pd.read_csv(f) for f in sorted(parts_dir.glob("*.csv"))], ignore_index=True)
    m.to_csv(OUT / "manifest.csv", index=False)
    print(f"manifest: {len(m)} rows -> {OUT / 'manifest.csv'}")
    print(m.groupby("cond").size().to_string())


# ------------------------------------------------------------------- eval ---
def tag_list():
    tags = []
    for p in sorted(C.CKPT.glob("*_best.pt")):
        tag = p.name[:-len("_best.pt")]
        if "smoke" in tag or tag.endswith("_old"):
            continue
        if not (C.CKPT / f"{tag}.pt").exists():      # training not finished (no weights-only export)
            print(f"  skip {tag}: no final export {tag}.pt")
            continue
        if tag.split("_")[0] in ("b1", "b3", "cm"):
            tags.append(tag)
    return tags


def evaluate(a):
    import torch
    from src import diverse as DV
    from src import models as M
    assert tuple(DV.HOLDOUT) == HOLDOUT and DV.TRAIN_FRAC == TRAIN_FRAC, "DEMAND split drifted from diverse.py"
    dev = C.device()
    man = pd.read_csv(OUT / "manifest.csv")
    ev = OUT / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    tags = a.tags or tag_list()
    print(f"{len(tags)} checkpoints: {', '.join(tags)}")
    for cond, rows in man.groupby("cond", sort=False):
        f = ev / f"{cond}.csv"
        old = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["tag"])
        have = old.groupby("tag").size().to_dict() if len(old) else {}
        todo = [t for t in tags if have.get(t, 0) != len(rows)]
        if not todo:
            print(f"{cond}: all {len(tags)} checkpoints done")
            continue
        old = old[~old.tag.isin(todo)]
        models = {}
        for t in todo:
            try:
                models[t] = M.load_model(t.split("_")[0], t, kind="best", device=dev)
            except Exception as e:  # noqa: BLE001
                print(f"  skip {t}: {e}")
        print(f"{cond}: {len(rows)} rows x {len(models)} checkpoints", flush=True)
        rec = []
        for i, r in enumerate(rows.itertuples()):
            x, _ = sf.read(r.noisy, dtype="float32")
            y, _ = sf.read(r.clean, dtype="float32")
            if x.ndim > 1:
                x = x.mean(axis=1)
            if y.ndim > 1:
                y = y.mean(axis=1)
            n = min(len(x), len(y))
            for t, m in models.items():
                rec.append(dict(tag=t, cond=cond, uid=r.uid, base_uid=r.base_uid,
                                noise_type=r.base_noise_type, snr=r.snr, **DV.analyse(m, x[:n], y[:n], dev)))
            if i % 200 == 0:
                print(f"  {cond}: {i}/{len(rows)}", flush=True)
        pd.concat([old, pd.DataFrame(rec)], ignore_index=True).to_csv(f, index=False)
        del models
        if dev == "cuda":
            torch.cuda.empty_cache()


def hp_pass(a):
    """Low-cut SI-SDR for (cond, tag) pairs whose eval rows predate the columns.
    Writes eval_hp/<cond>.csv (tag, uid, sisdr_lc_*, sisdr_hp100_*); resumable per (cond, tag)."""
    import torch
    from src import models as M
    from src.lowcut import lowcut_sisdr
    dev = C.device()
    man = pd.read_csv(OUT / "manifest.csv")
    hd = OUT / "eval_hp"
    hd.mkdir(parents=True, exist_ok=True)
    conds = a.conds or list(man.cond.unique())
    for tag in a.tags:
        model = None
        for cond in conds:
            rows = man[man.cond == cond]
            ef = OUT / "eval" / f"{cond}.csv"
            if ef.exists():
                e = pd.read_csv(ef)
                e = e[e.tag == tag]
                if "sisdr_lc_out" in e.columns and len(e) == len(rows) and e.sisdr_lc_out.notna().all():
                    continue                                  # evaluated with the columns already
            f = hd / f"{cond}.csv"
            old = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["tag", "uid"])
            if (old.tag == tag).sum() == len(rows):
                continue
            old = old[old.tag != tag]
            if model is None:
                model = M.load_model(tag.split("_")[0], tag, kind="best", device=dev)
                model.eval()
            rec = []
            with torch.no_grad():
                for r in rows.itertuples():
                    x, _ = sf.read(r.noisy, dtype="float32")
                    y, _ = sf.read(r.clean, dtype="float32")
                    x = x.mean(axis=1) if x.ndim > 1 else x
                    y = y.mean(axis=1) if y.ndim > 1 else y
                    n = min(len(x), len(y))
                    x, y = x[:n], y[:n]
                    est, _ = model(torch.from_numpy(x)[None].to(dev))
                    e_ = est[0].float().cpu().numpy()
                    rec.append(dict(tag=tag, uid=r.uid, **lowcut_sisdr(e_, x, y)))
            out = pd.concat([old, pd.DataFrame(rec)], ignore_index=True)
            tmp = f.with_suffix(".tmp")
            out.to_csv(tmp, index=False)
            os.replace(tmp, f)
            print(f"  hp {tag} {cond}: {len(rec)} rows", flush=True)
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()


# ---------------------------------------------------------- DFN3 / SGMSE ----
def _link(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def ext_prep(a):
    man = pd.read_csv(OUT / "manifest.csv")
    sg = Path(a.sgmse_dir)
    dfn_in, sg_in = sg / "xc_dfn_in", sg / "xc_sg_in"
    dfn_in.mkdir(exist_ok=True)
    sg_in.mkdir(exist_ok=True)
    base = man[man.base_uid.notna()]
    for r in base.itertuples():          # DFN3: every paired mixture (all conditions)
        _link(r.noisy, dfn_in / f"{r.cond}__{r.uid}.wav")
    vb = man[man.cond == "vbdmd_test"].sort_values("base_rank")
    for r in vb.itertuples():
        _link(r.noisy, dfn_in / f"vbdmd_test__{r.uid}.wav")
    # SGMSE: base row by base row, PAIRED conditions + one VB-DMD file, so any prefix is paired
    ranks = base[["base_uid", "base_rank", "snr"]].drop_duplicates("base_uid").sort_values(["base_rank", "snr"])
    vbl = list(vb.itertuples())
    n = 0
    for j, b in enumerate(ranks.itertuples()):
        rows = base[base.base_uid == b.base_uid].set_index("cond")
        for k, cond in enumerate(PAIRED):
            if cond in rows.index:
                _link(rows.loc[cond, "noisy"], sg_in / f"{j:04d}_{k}__{cond}__{b.base_uid}.wav")
                n += 1
        if j < len(vbl):
            _link(vbl[j].noisy, sg_in / f"{j:04d}_9__vbdmd_test__{vbl[j].uid}.wav")
            n += 1
    print(f"DFN3 inputs: {len(list(dfn_in.glob('*.wav')))}   SGMSE inputs (ordered): {n}")


def _parse(name):
    m = re.match(r"(?:\d{4}_\d__)?([A-Za-z_]+?)__(.+)\.wav$", name)
    return (m.group(1), m.group(2)) if m else (None, None)


def ext_score(a):
    from src.lowcut import lowcut_sisdr
    from src.pilot_level import G_MAX, G_MIN, mag, ratios, si_sdr
    man = pd.read_csv(OUT / "manifest.csv").set_index(["cond", "uid"])
    sg = Path(a.sgmse_dir)
    for model, d in (("dfn3", "xc_dfn_out"), ("sgmse", "xc_sg_out")):
        if a.models and model not in a.models:
            continue
        files = sorted((sg / d).glob("*.wav"))
        if not files:
            print(f"{model}: no outputs")
            continue
        rec = []
        for f in files:
            cond, uid = _parse(f.name)
            if (cond, uid) not in man.index:
                print(f"  {model}: unmatched {f.name}")
                continue
            r = man.loc[(cond, uid)]
            x, _ = sf.read(r.noisy, dtype="float32")
            y, _ = sf.read(r.clean, dtype="float32")
            e, sr = sf.read(str(f), dtype="float32")
            assert sr == SR, f"{f}: {sr}"
            n = min(len(x), len(y), len(e))
            x, y, e = x[:n], y[:n], e[:n]
            X, Cm, Y = mag(x), mag(y), mag(e)
            yc = y.astype(np.float64) - y.mean()
            g = float((e.astype(np.float64) - e.mean()) @ yc / (yc @ yc + 1e-12))
            ro, ru, ra = ratios(Y, Cm, X)
            rog, rug, rag = ratios(Y / np.clip(g, G_MIN, G_MAX), Cm, X)
            rob, rub, _ = ratios(X, Cm, X)
            rec.append(dict(tag=model, cond=cond, uid=uid, base_uid=r.base_uid, noise_type=r.base_noise_type,
                            snr=r.snr, sisdr_in=si_sdr(x, y), sisdr_out=si_sdr(e, y), g=g,
                            r_over=ro, r_under=ru, r_add=ra, r_over_g=rog, r_under_g=rug, r_add_g=rag,
                            r_over_b4=rob, r_under_b4=rub, **lowcut_sisdr(e, x, y)))
        pd.DataFrame(rec).to_csv(OUT / f"ext_{model}.csv", index=False)
        print(f"{model}: scored {len(rec)} outputs")


# ----------------------------------------------------------------- report ---
def _derive(f):
    f = f.copy()
    for b in ("", "_g"):
        ro, ru = f["r_over" + b], f["r_under" + b]
        f["d" + b] = (ro - ru) / (ro + ru + 1e-8)
        f["nr" + b] = 1 - ru / f.r_under_b4
    f["sisdr_gain"] = f.sisdr_out - f.sisdr_in
    return f


def _family(tag):
    for fam in ("anthro", "weather", "demand"):
        if fam in tag:
            return fam
    m = re.search(r"loto_(\w+?)(?:_s\d+)?$", tag)
    return f"loto:{m.group(1)}" if m else "other"


def _rung(tag, cond, nt):
    fam = _family(tag)
    heard = {"anthro": C.ANTHRO, "weather": C.WEATHER}.get(fam)
    if cond == "marven":
        if heard is not None:
            return "R1" if nt in heard else "R4"
        if fam.startswith("loto:"):
            if nt == fam[5:]:
                return "R4_heldout"
            return "R1" if nt in C.WEATHER else "R4_anthro"   # anthro types were never heard by loto models
        return "R4_marine"
    if fam == "anthro" and cond == "deepship_ship":
        return "R3"
    if fam == "demand" and cond in ("dem_A", "dem_B", "dem_H"):
        return {"dem_A": "R1", "dem_B": "R2", "dem_H": "R4"}[cond]
    return "X_" + cond


def report(a):
    rep = OUT / "report"
    rep.mkdir(exist_ok=True)
    cols = ["nr_g", "d_g", "nr", "d", "g", "sisdr_gain"]
    lines = ["# Overnight cross-corpus report (gate_overnight.yaml)", ""]
    ev = sorted((OUT / "eval").glob("*.csv"))
    if ev:
        d = _derive(pd.concat([pd.read_csv(f) for f in ev], ignore_index=True))
        d["family"] = d.tag.map(_family)
        d["rung"] = [_rung(t, c, n) for t, c, n in zip(d.tag, d.cond, d.noise_type)]
        s = d.groupby(["tag", "rung"])[cols].median().round(4)
        s.to_csv(rep / "trained_by_rung.csv")
        d.groupby(["tag", "cond", "snr"])[cols].median().round(4).to_csv(rep / "trained_by_cond_snr.csv")
        # H_S1: seed robustness of the R1 - R4 contrast on MarVEN
        h = []
        for k in ("b1", "b3", "cm"):
            for fam in ("anthro", "weather"):
                cs = {}
                for sfx in ("", "_s2", "_s3"):
                    t = f"{k}_{fam}{sfx}"
                    if (t, "R1") in s.index and (t, "R4") in s.index:
                        cs[sfx or "_s1234"] = s.loc[(t, "R1"), "nr_g"] - s.loc[(t, "R4"), "nr_g"]
                sg = {np.sign(v) for v in cs.values()}
                h.append(dict(model=f"{k}_{fam}", **{f"contrast{key}": v for key, v in cs.items()},
                              seed_sd=np.std(list(cs.values())) if cs else np.nan,
                              verdict="incomplete" if len(cs) < 3 else ("robust" if len(sg) == 1 else "seed_sensitive")))
        h = pd.DataFrame(h)
        h.to_csv(rep / "H_S1_seed_contrast.csv", index=False)
        lines += ["## H_S1 seed robustness (nr_g R1 - R4 on MarVEN)", "", h.round(3).to_string(index=False), ""]
    # H_S2 from results/r3*/verdict.csv
    v = []
    for p in sorted(C.EVAL.glob("r3*/verdict.csv")):
        x = pd.read_csv(p)
        x["run"] = p.parent.name
        v.append(x)
    if v:
        v = pd.concat(v, ignore_index=True)
        cls = v["class"].value_counts()
        n_ok = len(v)
        claim = cls.index[0] if len(cls) and cls.iloc[0] >= 6 else ("mixed" if n_ok >= 9 else "incomplete")
        v.to_csv(rep / "H_S2_r3_seeds.csv", index=False)
        lines += [f"## H_S2 R3 across seeds: {claim} ({n_ok} runs)", "",
                  v[["run", "tag", "p_noise_removed", "contrast", "class"]].round(3).to_string(index=False), ""]
    # H_P1 / H_P2: pretrained ladder
    for model in ("dfn3", "sgmse"):
        p = OUT / f"ext_{model}.csv"
        if not p.exists():
            continue
        e = _derive(pd.read_csv(p))
        e.groupby(["cond"])[cols].median().round(4).to_csv(rep / f"{model}_by_cond.csv")
        e.groupby(["cond", "snr"])[cols].median().round(4).to_csv(rep / f"{model}_by_cond_snr.csv")
        pb = e[e.cond.isin(PAIRED)]
        full = pb.groupby("base_uid").cond.nunique()
        keep = full[full == len(PAIRED)].index
        pb = pb[pb.base_uid.isin(keep)]
        row = dict(model=model, paired_base_rows=len(keep), vbdmd_n=int((e.cond == "vbdmd_test").sum()))
        for met, key in (("d_g", "H_P1"), ("nr_g", "H_P2")):
            delta = pb[pb.cond.isin(UNSEEN_P)][met].median() - pb[pb.cond.isin(HEARD_P)][met].median()
            row[f"{key}_delta"] = delta
            if model == "sgmse" and len(keep) < 40:
                row[key] = "underpowered"
            elif np.isnan(delta):
                row[key] = "no_data"
            else:
                row[key] = ("shifts_with_novelty" if abs(delta) >= 0.20 else
                            "model_trait" if abs(delta) < 0.10 else "inconclusive")
        if model == "dfn3":
            row["note"] = "provisional: DFN3 training noise vs DEMAND unverified"
        pd.DataFrame([row]).to_csv(rep / f"H_P_{model}.csv", index=False)
        lines += [f"## Pretrained ladder: {model}", "", pd.DataFrame([row]).round(3).to_string(index=False), "",
                  e.groupby("cond")[cols].median().round(3).to_string(), ""]
    (rep / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "eval", "hp", "ext-prep", "ext-score", "report"])
    ap.add_argument("--deepship"); ap.add_argument("--mbari"); ap.add_argument("--demand"); ap.add_argument("--vbdmd")
    ap.add_argument("--sgmse-dir"); ap.add_argument("--tags", nargs="*"); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--fsd", action="store_true", help="also build the FSD50K conditions (gate XN2)")
    ap.add_argument("--conds", nargs="*")
    ap.add_argument("--models", nargs="*", help="ext-score: only these (dfn3, sgmse); others keep their CSV")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    {"build": build, "eval": evaluate, "hp": hp_pass, "ext-prep": ext_prep, "ext-score": ext_score,
     "report": report}[a.cmd](a)


if __name__ == "__main__":
    main()
