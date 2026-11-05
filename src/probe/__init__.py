"""faildir probe — the failure-direction metric as one function.

    from src.probe import probe
    rep = probe(enhance_fn, split="marven_test_v1")      # callable: noisy -> enhanced
    rep = probe(wav_dir="out/sgmse")                      # or pre-enhanced wavs by uid

The metric is NOT redefined here. `_ratios`, the level-aligned gain clamp and the
bin floor are imported from src.diverse, which produced every number in
results/diverse/. A second copy of the energy split is exactly the mistake
src/metrics.py documents in its header, so this module has none.

Two bands are reported for every ratio:
    ""        bins from config.DECOMP_MIN_HZ (62.5 Hz) up — the REGISTERED basis
              behind configs/gate_universal.yaml and every gate verdict
    "_hp100"  bins from 100 Hz up — reported alongside, never instead of

Classes come from configs/gate_universal.yaml (commit 29c1566) unchanged:
    inert        nr < 0.30 and r_over_x(cell) < r_over_x(R1 reference)
    over         r_over_x(cell) >= r_over_x(R1 reference)
    hallucinate  median r_add >= 0.05
A cell matching none of the three is labelled `active_balanced`, which is a
tool-only label with no gate behind it. A cell can carry several classes; the
gate says so and says no class is a failure.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import config as C  # noqa: I001  (must precede torch: sets KMP_DUPLICATE_LIB_OK)

import numpy as np
import pandas as pd
import soundfile as sf
import torch

from src import data as D
from src.analysis import load_gate_config
from src.diverse import G_MAX, G_MIN, K0, _ratios
from src.lowcut import lowcut_sisdr
from src.models import magnitude
from src.r3 import _after      # the only _after in src/, rather than a third copy

SPLIT_DIR = Path(C.REPO) / "configs" / "splits"
K100 = int(np.ceil(100.0 * C.N_FFT / C.SR))      # first bin of the 100 Hz band
BANDS = (("", K0), ("_hp100", K100))

# Gate thresholds, read out of configs/gate_universal.yaml U1_failure_class at import
# so this file cannot hold a second copy of a registered number. scripts/run_universal.py
# parses the same two lines the same way.
_U1 = load_gate_config(Path(C.REPO) / "configs" / "gate_universal.yaml")["U1_failure_class"]
NR_INERT = _after(_U1["classes"]["inert"], "<")
RADD_HALLUCINATE = _after(_U1["classes"]["hallucinate"], ">=")

HEARD = {"weather": C.WEATHER, "anthro": C.ANTHRO}


def heard_types(tag: str):
    """MarVEN types this tag was trained on, which fixes its R1 reference. One
    implementation for every caller: a tag classed from the CLI and the same tag
    classed by the rescore must not get different rungs."""
    for fam, types in HEARD.items():
        if f"_{fam}" in tag:
            return types
    if "_loto_" in tag:                      # leave-one-type-out: heard the rest of weather
        held = tag.split("_loto_")[1].split("_s")[0]
        return tuple(t for t in C.WEATHER if t != held)
    return ()                                # demand / fsd / dns: no MarVEN type heard


def model_fn(tag: str, dev: str):
    from src import models as M
    model = M.load_model(tag.split("_")[0], tag, kind="best", device=dev)
    model.eval()

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        xt = torch.from_numpy(np.ascontiguousarray(x, np.float32))[None].to(dev)
        return model(xt)[0][0].float().cpu().numpy()
    return fn

ORACLE_ROWS = C.METRICS / "review_oracle_masks_rows.csv"


# ------------------------------------------------------------------ split ---
def split_checksum(uids) -> str:
    """SHA256 over the sorted uid list. MarVEN ships pre-mixed, so the uid list
    IS the split: there are no mixing parameters to pin down."""
    return hashlib.sha256("\n".join(sorted(uids)).encode()).hexdigest()


def freeze_split(name: str = "marven_test_v1", overwrite: bool = False) -> Path:
    df = D.load_manifest()
    te = df[df.split == "test"]
    if te.uid.duplicated().any():
        raise ValueError("duplicate uids in the test split")
    p = SPLIT_DIR / f"{name}.json"
    if p.exists() and not overwrite:
        return p
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "name": name,
        "sr": C.SR,
        "n": len(te),
        "selector": 'manifest split == "test"',
        "note": "MarVEN is pre-mixed on disk; noisy_path/clean_path come from the "
                "manifest, so no noise offset, SNR or gain needs recording here.",
        "sha256": split_checksum(te.uid),
        "uids": sorted(te.uid),
    }, indent=1))
    return p


def load_split(name: str = "marven_test_v1") -> pd.DataFrame:
    p = SPLIT_DIR / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing — run `python -m src.probe --freeze-split`")
    spec = json.loads(p.read_text())
    df = D.load_manifest()
    rows = df[df.uid.isin(set(spec["uids"]))].reset_index(drop=True)
    if len(rows) != spec["n"]:
        raise ValueError(f"{name}: manifest gives {len(rows)} of {spec['n']} uids")
    got = split_checksum(rows.uid)
    if got != spec["sha256"]:
        raise ValueError(f"{name} checksum mismatch\n  frozen {spec['sha256']}\n  now    {got}")
    return rows


# ----------------------------------------------------------------- scoring ---
def _si_sdr(est: np.ndarray, ref: np.ndarray, eps: float = 1e-8) -> float:
    est, ref = est.astype(np.float64), ref.astype(np.float64)
    est, ref = est - est.mean(), ref - ref.mean()
    t = (est @ ref) / (ref @ ref + eps) * ref
    return float(10 * np.log10((t @ t) / (((est - t) @ (est - t)) + eps)))


@torch.no_grad()
def score(x: np.ndarray, y: np.ndarray, e: np.ndarray, dev: str = "cpu") -> dict:
    """Energy split of one utterance on the OUTPUT STFT basis.

    x noisy, y clean, e enhanced, all float32 (T,) at config.SR and equal length.
    Mask-free by design: the gate uses the output STFT for every model, so the
    mask-intent columns (`_i` in src/diverse.py) are not reproduced here.
    """
    if not (len(x) == len(y) == len(e)):
        raise ValueError(f"length mismatch noisy={len(x)} clean={len(y)} enhanced={len(e)}")
    t = [torch.from_numpy(np.ascontiguousarray(a, np.float32))[None].to(dev) for a in (x, y, e)]
    X, S, Y = (magnitude(a)[0] for a in t)

    yc = y.astype(np.float64) - y.mean()
    g = float(np.dot(e.astype(np.float64) - e.mean(), yc) / (np.dot(yc, yc) + 1e-12))
    gu = float(np.clip(g, G_MIN, G_MAX))

    out = {"g": g, "sisdr_in": _si_sdr(x, y), "sisdr_out": _si_sdr(e, y)}
    for band, k in BANDS:
        sl = (slice(k, None),)
        ro, ru, ra = _ratios(Y, S, X, sl)
        rog, rug, rag = _ratios(Y / gu, S, X, sl)
        rob, rub, _ = _ratios(X, S, X, sl)          # passthrough floor, same utterance
        out.update({
            f"r_over{band}": ro, f"r_under{band}": ru, f"r_add{band}": ra,
            f"r_over_g{band}": rog, f"r_under_g{band}": rug, f"r_add_g{band}": rag,
            f"r_over_b4{band}": rob, f"r_under_b4{band}": rub,
        })
    out.update(lowcut_sisdr(e, x, y))
    return out


def derive(f: pd.DataFrame) -> pd.DataFrame:
    """d, nr and r_over_x for both bases and both bands. Same algebra as
    src.xcorpus._derive, extended over the band suffix."""
    f = f.copy()
    for band, _ in BANDS:
        for b in ("", "_g"):
            ro, ru = f[f"r_over{b}{band}"], f[f"r_under{b}{band}"]
            f[f"d{b}{band}"] = (ro - ru) / (ro + ru + 1e-8)
            f[f"nr{b}{band}"] = 1 - ru / f[f"r_under_b4{band}"]
            f[f"r_over_x{b}{band}"] = ro - f[f"r_over_b4{band}"]
    f["sisdr_gain"] = f.sisdr_out - f.sisdr_in
    f["sisdr_gain_hp100"] = f.sisdr_hp100_out - f.sisdr_hp100_in
    return f


def add_delta_d(f: pd.DataFrame) -> pd.DataFrame:
    """delta_d = d(model) - d(oracle Wiener), joined per utterance from
    results/metrics/review_oracle_masks_rows.csv (oracle_masks.py, 2,280 rows).

    The oracle masks are bounded, so their output level is the clean level and
    g ~ 1: the oracle has no separate level-aligned column, and delta_d_g
    therefore uses d_g(model) against the same plain-basis oracle d.
    """
    f = f.copy()
    if not ORACLE_ROWS.exists():
        f["d_wiener"] = np.nan
        f["delta_d"] = np.nan
        f["delta_d_g"] = np.nan
        return f
    o = pd.read_csv(ORACLE_ROWS).drop_duplicates("noisy_path")
    ro, ru = o.r_over_wiener, o.r_under_wiener
    o["d_wiener"] = (ro - ru) / (ro + ru + 1e-8)
    man = D.load_manifest()[["uid", "noisy_path"]]
    o = o.merge(man, on="noisy_path", how="inner")[["uid", "d_wiener"]]
    f = f.merge(o, on="uid", how="left")
    f["delta_d"] = f.d - f.d_wiener
    f["delta_d_g"] = f.d_g - f.d_wiener
    return f


# ------------------------------------------------------------------- probe ---
def _read_enhanced(p: Path, x) -> np.ndarray:
    e, sr = sf.read(p, dtype="float32")
    if e.ndim > 1:
        e = e.mean(axis=1)
    if sr != C.SR:
        raise ValueError(f"{p}: expected {C.SR} Hz, got {sr}")
    return np.ascontiguousarray(e[:min(len(e), len(x))])


def _from_map(wav_map: dict):
    """uid -> path. Use it when the enhancer named its outputs positionally:
    build the map from the row list that drove the enhancement (DFN3 has one in
    results/labels_active/rows_dfn.csv) rather than reconstructing row order."""
    def fn(x, uid):
        p = wav_map.get(uid)
        if p is None:
            raise KeyError(f"{uid} is not in wav_map ({len(wav_map)} entries)")
        return _read_enhanced(Path(p), x)
    return fn


def _from_dir(wav_dir: Path):
    wav_dir = Path(wav_dir)

    def fn(x, uid):
        p = wav_dir / f"{uid}.wav"
        if not p.exists():                       # uid carries | and +, illegal on NTFS
            p = wav_dir / (uid.replace("|", "__").replace("+", "p") + ".wav")
        if not p.exists():
            raise FileNotFoundError(f"no enhanced wav for {uid} in {wav_dir}")
        return _read_enhanced(p, x)
    return fn


def probe(enhance_fn=None, *, wav_dir=None, wav_map=None, split: str = "marven_test_v1",
          sr: int = C.SR, device: str | None = None, heard_types=None,
          limit: int | None = None, out=None, tag: str = "model",
          log_every: int = 200) -> dict:
    """Score one enhancer on a frozen split.

    enhance_fn  np.ndarray (T,) float32 noisy -> np.ndarray (T,) enhanced
    wav_dir     alternative to enhance_fn: a directory of enhanced wavs named by
                uid. Use it for enhancers that cannot be called in this process
                (SGMSE+ runs in its own conda env).
    wav_map     alternative to both: a dict uid -> path, for enhancers whose
                outputs are named positionally.
    heard_types noise types this enhancer was trained on. Required for the gate
                classes, which are defined as R4-versus-R1 contrasts; without it
                the class columns are "unknown".
    returns     {"rows": DataFrame, "summary": DataFrame, "split": str,
                 "sha256": str, "n": int}
    """
    if sr != C.SR:
        raise ValueError(f"the frozen split is {C.SR} Hz audio; sr={sr} is not supported")
    given = [k for k, v in (("enhance_fn", enhance_fn), ("wav_dir", wav_dir),
                            ("wav_map", wav_map)) if v is not None]
    if len(given) != 1:
        raise ValueError(f"pass exactly one of enhance_fn, wav_dir, wav_map (got {given})")
    dev = device or C.device()
    frame = load_split(split)
    spec = json.loads((SPLIT_DIR / f"{split}.json").read_text())
    n_split = len(frame)
    if wav_map is not None:
        # partial coverage is legitimate: SGMSE+ has 400 of the 2,280 enhanced.
        # Score what exists and let the report say how much that was.
        frame = frame[frame.uid.isin(wav_map)].reset_index(drop=True)
        if frame.empty:
            raise ValueError("wav_map covers none of the split's uids")
    if limit:
        frame = frame.head(limit)

    takes_uid = enhance_fn is None
    fn = enhance_fn if enhance_fn is not None else (
        _from_dir(wav_dir) if wav_dir is not None else _from_map(wav_map))

    rows = []
    for i, r in enumerate(frame.itertuples()):
        x, y = D.read_pair(r)
        e = fn(x, r.uid) if takes_uid else fn(x)
        e = np.ascontiguousarray(np.asarray(e, np.float32).squeeze())
        n = min(len(e), len(x))
        if len(e) != len(x):
            if abs(len(e) - len(x)) > C.HOP:
                raise ValueError(
                    f"{r.uid}: enhancer returned {len(e)} samples for {len(x)} in — "
                    "probe() needs the same length back")
            x, y, e = x[:n], y[:n], e[:n]
        rows.append({"tag": tag, "uid": r.uid, "noise_type": r.noise_type,
                     "snr": int(r.target_snr_db), "family": r.family,
                     **score(x, y, e, dev)})
        if log_every and (i + 1) % log_every == 0:
            print(f"  {tag} {i + 1}/{len(frame)}", flush=True)

    d = add_delta_d(derive(pd.DataFrame(rows)))
    s = summarise(d, heard_types=heard_types)
    rep = {"rows": d, "summary": s, "split": split, "sha256": spec["sha256"],
           "n": len(d), "n_split": n_split, "coverage": len(d) / n_split}
    if out:
        write_report(rep, out)
    return rep


# ----------------------------------------------------------------- summary ---
SNR_BANDS = (("low", -15, 0), ("high", 5, 20))
SUMMARY_COLS = ("d", "d_g", "nr", "nr_g", "r_over_x", "r_add", "delta_d", "sisdr_gain")


def snr_band(snr: int) -> str:
    for name, lo, hi in SNR_BANDS:
        if lo <= snr <= hi:
            return name
    return "other"


def bootstrap_ci(v, by=None, n: int = 2000, alpha: float = 0.05, seed: int = C.SEED):
    """Percentile CI of the median, resampling the clusters named in `by` (base
    utterances) and not rows: the same clean utterance appears under several noise
    types and SNRs, so resampling rows treats one utterance as several independent
    draws and shrinks the interval. by=None is one row per cluster, i.e. the plain
    row bootstrap, and is only right when the rows really are independent."""
    v = np.asarray(v, dtype=np.float64)
    by = np.arange(len(v)) if by is None else np.asarray(by)
    ok = np.isfinite(v)
    v, by = v[ok], by[ok]
    if len(v) < 2:
        return (np.nan, np.nan)
    order = np.argsort(by, kind="stable")
    sizes = np.unique(by, return_counts=True)[1]        # same order as `order` groups them
    pad = np.full((len(sizes), int(sizes.max())), np.nan)
    for j, (s, k) in enumerate(zip(np.r_[0, np.cumsum(sizes)[:-1]], sizes)):
        pad[j, :k] = v[order[s:s + k]]
    rng = np.random.default_rng(seed)
    meds = []
    for lo in range(0, n, 250):                         # chunked: pad[pick] is the memory peak
        m = min(250, n - lo)
        pick = rng.integers(0, len(sizes), size=(m, len(sizes)))
        meds.append(np.nanmedian(pad[pick].reshape(m, -1), axis=1))
    meds = np.concatenate(meds)
    return (float(np.quantile(meds, alpha / 2)), float(np.quantile(meds, 1 - alpha / 2)))


def _classify(nr: float, r_over_x: float, r_add: float, r_over_x_r1: float) -> str:
    """configs/gate_universal.yaml U1_failure_class, verbatim thresholds."""
    if not np.isfinite(r_over_x_r1):
        return "unknown"
    cls = []
    if np.isfinite(r_add) and r_add >= RADD_HALLUCINATE:
        cls.append("hallucinate")
    if np.isfinite(r_over_x) and r_over_x >= r_over_x_r1:
        cls.append("over")
    elif np.isfinite(nr) and nr < NR_INERT:
        cls.append("inert")
    return "+".join(cls) if cls else "active_balanced"


def summarise(rows: pd.DataFrame, heard_types=None, n_boot: int = 2000) -> pd.DataFrame:
    """Medians with 95% bootstrap CIs per noise type x SNR band, plus the gate
    class for both bands. Pooled rows are appended last and are secondary."""
    d = rows.copy()
    d["snr_band"] = [snr_band(s) for s in d.snr]
    heard = set(heard_types or ())
    d["rung"] = np.where(d.noise_type.isin(heard), "R1", "R4") if heard else "unknown"
    # base utterance = the LibriSpeech key, so the CI resamples utterances
    d["base"] = [u.split("|")[0] for u in d.uid]

    def r1_ref(band, snr_b):
        if not heard:
            return np.nan
        g = d[(d.rung == "R1") & (d.snr_band == snr_b)]
        return g[f"r_over_x{band}"].median() if len(g) else np.nan

    out = []
    groups = [((t, b), g) for (t, b), g in d.groupby(["noise_type", "snr_band"])]
    groups += [(("POOLED", b), g) for b, g in d.groupby("snr_band")]
    for (ntype, band_name), g in groups:
        rec = {"noise_type": ntype, "snr_band": band_name, "n": len(g),
               "n_base": g.base.nunique(),
               "rung": "/".join(sorted(g.rung.unique()))}
        for band, _ in BANDS:
            for c in SUMMARY_COLS:
                col = f"{c}{band}"       # no fallback to the full band: a column with no
                if col not in g:         # _hp100 twin must not be reported under that name
                    continue
                v = g[col]
                lo, hi = bootstrap_ci(v.values, g.base.values, n=n_boot)
                rec[f"{c}{band}"] = float(v.median())
                rec[f"{c}{band}_lo"] = lo
                rec[f"{c}{band}_hi"] = hi
            rec[f"class{band}"] = _classify(
                g[f"nr{band}"].median(), g[f"r_over_x{band}"].median(),
                g[f"r_add{band}"].median(), r1_ref(band, band_name))
        out.append(rec)
    s = pd.DataFrame(out)
    return s.sort_values(["noise_type", "snr_band"]).reset_index(drop=True)


def write_report(rep: dict, out) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rep["rows"].to_csv(out / "rows.csv", index=False)
    rep["summary"].to_csv(out / "summary.csv", index=False)
    s = rep["summary"]
    keep = ["noise_type", "snr_band", "n", "n_base", "rung",
            "d_g", "d_g_lo", "d_g_hi", "nr_g", "nr_g_lo", "nr_g_hi",
            "r_add", "delta_d", "class", "d_g_hp100", "nr_g_hp100", "class_hp100"]
    keep = [c for c in keep if c in s]
    cover = ""
    if rep.get("coverage", 1.0) < 1.0:
        cover = (f" - **partial coverage: {rep['n']} of {rep['n_split']} "
                 f"({rep['coverage']:.1%})**, medians cover only those rows")
    md = [f"# probe report: {rep['rows'].tag.iloc[0]}", "",
          f"- split `{rep['split']}` n={rep['n']} sha256 `{rep['sha256'][:16]}...`{cover}",
          "- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);",
          "  `class_hp100` is the 100 Hz band reported alongside it.",
          "- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.",
          "",
          "```",
          s[keep].round(4).to_string(index=False),
          "```"]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    return out
