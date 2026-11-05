"""Universal-claim gates (configs/gate_universal.yaml), one stage and one verdict per gate.

    python scripts/run_universal.py --gate u1class     # existing data, minutes, CPU
    python scripts/run_universal.py --gate u1          # trains the missing seg models (GPU)
    python scripts/run_universal.py --gate u3          # CPU, needs results/xcorpus
    python scripts/run_universal.py --gate u3 --sens canonical_lgbm   # post-hoc variant
    python scripts/run_universal.py --gate u2          # needs 2 of 3 non-bounded classes
    python scripts/run_universal.py --gate all         # u1 -> u1class -> u3

The gates stay separate claims; this only puts them behind one command. Each stage
writes results/universal/<gate>_verdict.json (gate id, config commit and hash, code
commit, the thresholds used, every per-cell number, PASS/FAIL) plus <gate>_cells.csv,
and skips itself when its verdict file exists. --force re-runs a stage; --no-resume
also retrains and re-extracts instead of reusing checkpoints and caches.

Every threshold comes from the yaml. Some of them live inside its prose (the class
definitions, "in >= 3 of 4 levels", "in >= 75% of cells"); _after() reads those off the
yaml text rather than typing them here, so the yaml stays the only place they exist.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import config as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

GATE_PATH = REPO / "configs" / "gate_universal.yaml"
SEG_GATE_PATH = REPO / "configs" / "gate.yaml"
OUT = C.EVAL / "universal"
XC = C.EVAL / "xcorpus"
SEG = C.EVAL / "segment"
EPS = 1e-8
Y_FLOOR = 1e-6          # r_over_x can be negative (below the passthrough floor); see u3_labels
ARCHS = ("b1", "b3", "cm")
RUNGS = ("R1", "R2", "R4")
CORPORA = {"marven": ["marven"],
           "demand": ["dem_A", "dem_B", "dem_H"],
           "fsd50k": ["fsd_eval", "fsd_weather", "fsd_boat"]}


# ------------------------------------------------------------ provenance ---
def load_gate() -> tuple[dict, str]:
    text = GATE_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text), hashlib.sha256(text.encode()).hexdigest()[:12]


def _after(s, op: str) -> float:
    """The number the yaml writes immediately after a comparison. Anchoring on the
    operator keeps a threshold apart from a digit inside a name: U2's pass_if reads
    "U1_novelty_monotone pass_arch_if holds for >= 2 of 3 ...", whose first number is
    the 1 in U1."""
    m = re.search(re.escape(op) + r"\s*(-?\d+(?:\.\d+)?)", str(s))
    if m is None:
        raise SystemExit(f"no {op!r} threshold in the yaml text: {s!r}")
    return float(m.group(1))


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()


def code_commit() -> str:
    """Dirty is recorded, not blocked: the paper's claim is that the code hash predates
    the result, and a run from an uncommitted tree must say so in its own verdict.
    Only TRACKED edits count as dirty; untracked files are listed instead, because the
    paper sources live untracked here and cannot change a result."""
    tracked = _git("status", "--porcelain", "--untracked-files=no")
    return _git("rev-parse", "HEAD") + ("+dirty" if tracked else "")


def untracked_files() -> list[str]:
    return _git("ls-files", "--others", "--exclude-standard").splitlines()


def write_verdict(gate_id: str, cfg: dict, sha: str, thresholds: dict,
                  cells: list[dict] | pd.DataFrame, passed: bool, notes: dict) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = pd.DataFrame(cells)
    cells.to_csv(OUT / f"{gate_id}_cells.csv", index=False)
    v = {"gate": gate_id,
         "config_commit": cfg["provenance"]["commit"],
         "config_committed_at": cfg["provenance"]["committed_at"],
         "config_sha256_12": sha,
         "code_commit": code_commit(),
         "untracked_files": untracked_files(),
         "run_at": dt.datetime.now().isoformat(timespec="seconds"),
         "thresholds": thresholds,
         "notes": notes,
         "cells": cells.to_dict("records"),
         "verdict": "PASS" if passed else "FAIL"}
    (OUT / f"{gate_id}_verdict.json").write_text(json.dumps(v, indent=2), encoding="utf-8")
    print("\n" + cells.to_string(index=False))
    print(f"\n{gate_id}: {v['verdict']}  ->  {OUT / (gate_id + '_verdict.json')}")
    return v


def derive(f: pd.DataFrame, b: str = "_g") -> pd.DataFrame:
    """The yaml's d, nr, r_over_x and r_add from src.diverse's ratio columns. Default
    basis is level-aligned ("_g"): CM's mask is unbounded, so the plain split counts its
    free output level as energy beyond clean. Both bases are in the source CSVs."""
    ro, ru = f["r_over" + b], f["r_under" + b]
    return f.assign(d=(ro - ru) / (ro + ru + EPS),
                    nr=1 - ru / f.r_under_b4,
                    r_over_x=ro - f.r_over_b4,
                    r_add=f["r_add" + b])


# ------------------------------------------------------------------- U1 ----
def u1_rows(archs=ARCHS, folds=C.FAMILIES) -> pd.DataFrame:
    """Per-window rows of the segment control's seg model (the one that heard half A
    only): A windows = R1 heard samples, B = R2 unheard segment of a heard recording,
    U = R4 unseen noise type."""
    rung = {"A": "R1", "B": "R2", "U": "R4"}
    parts = []
    for arch in archs:
        for fold in folds:
            for sfx in ("__windows.csv", "__unseen.csv"):
                p = SEG / f"{arch}_seg_{fold}{sfx}"
                if not p.exists():
                    raise FileNotFoundError(
                        f"{p} missing. Run: python -m src.segment --model {arch} --fold {fold}")
                d = pd.read_csv(p)
                keep = [c for c in d.columns if c.endswith("_seg")]
                d = d[keep + ["uid", "noise_type", "snr", "half"]].rename(
                    columns={c: c[: -len("_seg")] for c in keep})
                parts.append(d.assign(arch=arch, fold=fold))
    f = pd.concat(parts, ignore_index=True)
    f["rung"] = f.half.map(rung)
    return derive(f)


def u1_verdict(rows: pd.DataFrame, archs, cfg: dict) -> tuple[list[dict], dict, dict]:
    """U1's verdict, over whatever model list is handed in (U2 reuses it with the
    non-bounded architectures). `rows` needs arch, fold, rung, snr, d.

    unit  = one arch, one low-SNR level: median d strictly falls R1 > R2 > R4.
    arch  = that unit passes in at least `min_levels` of the low-SNR levels.
    Folds are pooled for the verdict; per-fold medians are reported beside it."""
    u = cfg["U1_novelty_monotone"]
    snr_low = cfg["definitions"]["snr_low"]
    min_levels = int(_after(u["pass_arch_if"], ">="))
    cells, arch_pass, levels = [], {}, {}
    for arch in archs:
        for fold in ["all", *sorted(rows.fold.unique())]:
            g = rows[rows.arch == arch]
            g = g if fold == "all" else g[g.fold == fold]
            ok = 0
            for snr in snr_low:
                h = g[g.snr == snr]
                med = {r: float(h[h.rung == r].d.median()) for r in RUNGS}
                unit = (all(np.isfinite(v) for v in med.values())
                        and med["R1"] > med["R2"] > med["R4"])
                ok += bool(unit)
                cells.append({"arch": arch, "fold": fold, "snr": snr,
                              **{f"median_d_{r}": round(med[r], 4) for r in RUNGS},
                              **{f"n_{r}": int((h.rung == r).sum()) for r in RUNGS},
                              "unit_pass": bool(unit)})
            if fold == "all":
                levels[arch], arch_pass[arch] = ok, ok >= min_levels
    thresholds = {"snr_low": snr_low, "min_levels": min_levels,
                  "pass_unit_if": u["pass_unit_if"], "pass_arch_if": u["pass_arch_if"],
                  "pass_if": u["pass_if"], "statistic": u["statistic"],
                  "basis": "output STFT, level-aligned (_g)", "levels_passed": levels}
    return cells, arch_pass, thresholds


def require_cuda(a) -> None:
    """U1 trains four models: about 40 min each on the 4060, about 6 h each on the CPU.
    The guard lives here, not in a shell pre-flight line, because PowerShell runs the
    next line of a pasted block even after the previous one failed."""
    import torch
    if torch.cuda.is_available() or a.allow_cpu:
        return
    raise SystemExit(
        "no CUDA device: torch.cuda.is_available() is False. Check that nvidia-smi sees "
        "the GPU, then rerun. Pass --allow-cpu to train on the CPU on purpose (about 25 h "
        "for the four models).")


def stage_u1(cfg: dict, sha: str, a) -> None:
    require_cuda(a)
    from src import segment as S
    steps = yaml.safe_load(SEG_GATE_PATH.read_text(encoding="utf-8"))["segment"]["steps"]
    for arch in ARCHS:
        for fold in C.FAMILIES:
            print(f"\n=== u1: {arch}/{fold} ===", flush=True)
            S.ensure_windows(arch, fold, steps, fresh=a.no_resume)
    rows = u1_rows()
    cells, arch_pass, thresholds = u1_verdict(rows, ARCHS, cfg)
    bounded = [x.lower() for x in cfg["definitions"]["architectures"]["bounded_mask"]]
    passed = all(arch_pass[k] for k in bounded)
    write_verdict("u1", cfg, sha, thresholds, cells, passed,
                  {"arch_pass": arch_pass, "required": bounded,
                   "rungs": {"R1": "A windows", "R2": "B windows",
                             "R4": "test_unseen windows"},
                   "model": "seg (half-A) model of each architecture, both folds pooled",
                   "steps": steps,
                   "R3": "not in this stage; the segment control is MarVEN only"})


# -------------------------------------------------------------- U1-class ---
def stage_u1class(cfg: dict, sha: str, a) -> None:
    u = cfg["U1_failure_class"]
    snr_low = cfg["definitions"]["snr_low"]
    nr_max = _after(u["classes"]["inert"], "<")
    add_min = _after(u["classes"]["hallucinate"], ">=")
    heard = {"weather": C.WEATHER, "anthro": C.ANTHRO}
    tags = [f"{k}_{f}" for k in ARCHS for f in C.FAMILIES]
    d = pd.read_csv(XC / "eval" / "marven.csv")
    d = d[d.tag.isin(tags) & d.snr.isin(snr_low)].reset_index(drop=True)
    missing = sorted(set(tags) - set(d.tag))
    if missing:
        raise SystemExit(f"no marven eval rows for {missing}; run src.xcorpus eval first")
    d["arch"] = d.tag.str.split("_").str[0]
    d["fold"] = d.tag.str.split("_").str[1]
    d["rung"] = np.where([nt in heard[f] for nt, f in zip(d.noise_type, d.fold)], "R1", "R4")
    d = derive(d)
    cells, classes = [], {}
    for arch in ARCHS:
        g = d[d.arch == arch]
        r4, r1 = g[g.rung == "R4"], g[g.rung == "R1"]
        nr, ox4, ox1, add = (float(r4.nr.median()), float(r4.r_over_x.median()),
                             float(r1.r_over_x.median()), float(r4.r_add.median()))
        k = ((["inert"] if (nr < nr_max and ox4 < ox1) else [])
             + (["over"] if ox4 >= ox1 else [])
             + (["hallucinate"] if add >= add_min else []))
        classes[arch] = k
        cells.append({"arch": arch, "n_R4": len(r4), "n_R1": len(r1),
                      "median_nr_R4": round(nr, 4), "median_r_over_x_R4": round(ox4, 4),
                      "median_r_over_x_R1": round(ox1, 4), "median_r_add_R4": round(add, 4),
                      "classes": "|".join(k) or "none"})
    write_verdict("u1class", cfg, sha,
                  {"classes": u["classes"], "nr_max": nr_max, "r_add_min": add_min,
                   "snr_low": snr_low, "pass_if": u["pass_if"], "rule": u["rule"]},
                  cells, all(classes[k] for k in ARCHS),
                  {"classes": classes, "tags": tags,
                   "source": "results/xcorpus/eval/marven.csv",
                   "basis": "output STFT, level-aligned (_g)",
                   "architectures_covered": "bounded_mask and complex_mask; "
                                            "diverse_pretrained and generative wait for U2"})


# ------------------------------------------------------------------- U3 ----
def u3_features(conds, fresh: bool = False) -> pd.DataFrame:
    """33 reference-free features plus WADA-SNR on each saved mixture. Reads the noisy
    file only; cached per (cond, uid), so an interrupted pass resumes."""
    import soundfile as sf

    from src import features as FT
    from wada_snr import wada
    man = pd.read_csv(XC / "manifest.csv")
    man = man[man.cond.isin(conds)].reset_index(drop=True)
    cache = OUT / "u3_features.csv"
    F = (pd.read_csv(cache) if cache.exists() and not fresh
         else pd.DataFrame(columns=["cond", "uid"]))
    have = set(zip(F.cond, F.uid))
    new = []
    for i, r in enumerate(man.itertuples()):
        if (r.cond, r.uid) in have:
            continue
        x, sr = sf.read(r.noisy, dtype="float32")
        assert sr == C.SR, f"{r.noisy}: {sr} Hz"
        if x.ndim > 1:
            x = x.mean(axis=1)
        new.append({"cond": r.cond, "uid": r.uid, "wada_snr": wada(x), **FT.feats(x)})
        if (i + 1) % 200 == 0:
            print(f"  u3 features {i + 1}/{len(man)}", flush=True)
    if new:
        F = pd.concat([F, pd.DataFrame(new)], ignore_index=True)
        OUT.mkdir(parents=True, exist_ok=True)
        F.to_csv(cache, index=False)
    FT.assert_reference_free([c for c in F.columns if c not in ("cond", "uid")])
    print(f"u3 features: {len(F)} rows ({len(new)} new)")
    return F


def u3_features_burst(conds, fresh: bool = False) -> pd.DataFrame:
    """The 12 burst features of src/features_burst.py on the same saved mixtures.

    Kept in its own cache so u3_features.csv, which backs the registered 33-feature
    verdicts, is never rewritten. Only the feats45 sensitivity reads this.
    """
    import soundfile as sf

    from src import features as FT
    from src import features_burst as FB
    man = pd.read_csv(XC / "manifest.csv")
    man = man[man.cond.isin(conds)].reset_index(drop=True)
    cache = OUT / "u3_features_burst.csv"
    F = (pd.read_csv(cache) if cache.exists() and not fresh
         else pd.DataFrame(columns=["cond", "uid"]))
    have = set(zip(F.cond, F.uid))
    new = []
    for i, r in enumerate(man.itertuples()):
        if (r.cond, r.uid) in have:
            continue
        x, sr = sf.read(r.noisy, dtype="float32")
        assert sr == C.SR, f"{r.noisy}: {sr} Hz"
        if x.ndim > 1:
            x = x.mean(axis=1)
        new.append({"cond": r.cond, "uid": r.uid, **FB.feats(x)})
        if (i + 1) % 200 == 0:
            print(f"  u3 burst features {i + 1}/{len(man)}", flush=True)
    if new:
        F = pd.concat([F, pd.DataFrame(new)], ignore_index=True)
        OUT.mkdir(parents=True, exist_ok=True)
        F.to_csv(cache, index=False)
    FT.assert_reference_free([c for c in F.columns if c not in ("cond", "uid")])
    print(f"u3 burst features: {len(F)} rows ({len(new)} new)")
    return F


def u3_labels(conds, tag: str) -> pd.DataFrame:
    """y = log10 r_over_x for one fixed enhancer. r_over_x goes negative when the model
    sits below the passthrough floor, which has no log; those rows are floored to a
    common value (Spearman handles the ties) and counted in the verdict."""
    parts = []
    for c in conds:
        p = XC / "eval" / f"{c}.csv"
        if not p.exists():
            raise SystemExit(f"{p} missing; run src.xcorpus build/eval first")
        d = pd.read_csv(p)
        d = d[d.tag == tag]
        if d.empty:
            raise SystemExit(f"{p}: no rows for tag {tag!r}")
        parts.append(d)
    d = derive(pd.concat(parts, ignore_index=True))
    d["clipped"] = d.r_over_x <= Y_FLOOR
    d["y"] = np.log10(d.r_over_x.clip(lower=Y_FLOOR))
    return d[["cond", "uid", "noise_type", "snr", "y", "clipped"]]


def _fit(kind: str, cols, tr: pd.DataFrame, te: pd.DataFrame, seed: int,
         canonical: bool = False):
    if kind == "lgbm" and canonical:
        # The canonical_lgbm sensitivity arm calls claim 3's own fitter, so "canonical"
        # means that function rather than a copy of its numbers here. It early-stops, so
        # it needs a validation split, carved off the training side by speaker.
        from sklearn.model_selection import GroupKFold

        from src.claim3 import fit_arm
        i, j = next(GroupKFold(n_splits=5).split(
            tr, groups=tr.uid.str.split("-").str[0]))
        return fit_arm(cols, "canonical_lgbm", tr.iloc[i], tr.iloc[j], te, seed)[2]
    if kind == "lgbm":
        import lightgbm as lgb
        m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=31,
                              min_child_samples=40, subsample=0.8, colsample_bytree=0.8,
                              random_state=seed, verbose=-1)
    else:
        from sklearn.linear_model import RidgeCV
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13)))
    m.fit(tr[cols], tr.y)
    return m.predict(te[cols])


def _oof(d: pd.DataFrame, cols, kind: str, seed: int = C.SEED, n_splits: int = 5,
         canonical: bool = False) -> np.ndarray:
    """Out-of-fold predictions, folds grouped by speaker: every row is a test row once,
    and no speaker is on both sides of a split."""
    from sklearn.model_selection import GroupKFold
    pred = np.full(len(d), np.nan)
    spk = d.uid.str.split("-").str[0]
    for tr, te in GroupKFold(n_splits=n_splits).split(d, groups=spk):
        pred[te] = _fit(kind, cols, d.iloc[tr], d.iloc[te], seed, canonical)
    assert np.isfinite(pred).all(), "a row got no out-of-fold prediction"
    return pred


def stage_u3(cfg: dict, sha: str, a) -> None:
    from src.claim3 import within
    sens = getattr(a, "sens", None)
    u = cfg["U3_within_condition"]
    min_frac = _after(u["pass_if"][1], ">=") / 100
    conds = [c for cs in CORPORA.values() for c in cs]
    F = u3_features(conds, a.no_resume)
    d = u3_labels(conds, a.tag).merge(F, on=["cond", "uid"], validate="1:1")
    feats = [c for c in F.columns if c not in ("cond", "uid", "wada_snr")]
    arms = {"feats_only_lgbm": ("lgbm", feats), "ridge_33": ("ridge", feats),
            "baseline_snr_logE": ("ridge", ["snr", "log_e_noisy"]),
            "wada_snr": ("ridge", ["wada_snr"])}
    assert sorted(arms) == sorted(u["arms"]), f"arms drifted from the yaml: {u['arms']}"
    rivals = [k for k in arms if k != "feats_only_lgbm"]
    cells, corpus_pass, means = [], {}, {}
    for corpus, cs in CORPORA.items():
        g = d[d.cond.isin(cs)].reset_index(drop=True)
        if g.empty:
            print(f"u3: no rows for {corpus}, skipped")
            continue
        # DEMAND / FSD cells are the condition: per-environment cells hold too few rows.
        g["cell_noise"] = np.where(g.cond == "marven", g.noise_type, g.cond)
        preds = {name: _oof(g, cols, kind, canonical=sens == "canonical_lgbm")
                 for name, (kind, cols) in arms.items()}
        w = within(g, preds, by=["cell_noise", "snr"])
        mean = {k: float(w[k].mean()) for k in arms}
        wins = {k: float((w.feats_only_lgbm > w[k]).mean()) for k in rivals}
        corpus_pass[corpus] = all(mean["feats_only_lgbm"] > mean[k] and wins[k] >= min_frac
                                  for k in rivals)
        means[corpus] = {"n_cells": len(w), "n_rows": len(g),
                         "clipped_frac": round(float(g.clipped.mean()), 4),
                         "mean_rho": {k: round(v, 4) for k, v in mean.items()},
                         "win_frac_vs": {k: round(v, 4) for k, v in wins.items()},
                         "pass": corpus_pass[corpus]}
        cells += w.assign(corpus=corpus).to_dict("records")
        print(f"u3 {corpus}: {len(w)} cells, mean rho "
              + ", ".join(f"{k}={mean[k]:.3f}" for k in arms))
    passed = bool(corpus_pass.get("marven")
                  and (corpus_pass.get("demand") or corpus_pass.get("fsd50k")))
    notes = {"per_corpus": means, "y_floor": Y_FLOOR,
             "split": "5-fold out-of-fold, grouped by speaker",
             "label": "log10(r_over_x), level-aligned (_g) output STFT",
             "corpora_required": "MarVEN and at least one of DEMAND / FSD50K"}
    if sens:
        # A post-hoc variant is not the gate. It gets its own file, says so in its own
        # notes, and never touches u3_verdict.json, which was decided before this ran.
        notes |= {"post_hoc": True, "sensitivity": sens,
                  "pre_registered_verdict": "u3_verdict.json",
                  "deviation": "the feats_only_lgbm arm is src.claim3.fit_arm "
                               "(n_estimators 2000, early stopping on a speaker-grouped "
                               "validation split) instead of this runner's fixed 600 "
                               "rounds. Thresholds and arms are the yaml's, unchanged."}
    write_verdict(f"u3_sens_{sens}" if sens else "u3", cfg, sha,
                  {"target": u["target"], "cells": u["cells"], "arms": u["arms"],
                   "pass_if": u["pass_if"], "min_cell_fraction": min_frac,
                   "min_rows_per_cell": 25, "enhancer_tag": a.tag},
                  cells, passed, notes)



# -------------------------------------------------------- U3 transfer ----
def stage_u3_transfer(cfg: dict, sha: str, a) -> None:
    """Leave-one-noise-type-out: the predictor never sees the held-out type and the
    enhancer is fixed, so no model retrains and no mixture is re-rendered.

    The yaml's design line holds out the type and nothing else. MarVEN carries 10
    speakers and every type carries all of them, so every test speaker is also a
    training speaker. That is the registered design, not an oversight here; it is
    recorded under notes.speaker_overlap so the verdict cannot be read as
    speaker-disjoint.
    """
    from src.claim3 import within
    sens = getattr(a, "sens", None)
    u = cfg["U3_transfer"]
    min_types = int(_after(u["pass_if"], ">="))
    conds = [c for cs in CORPORA.values() for c in cs]
    F = u3_features(conds, a.no_resume)
    d = u3_labels(conds, a.tag).merge(F, on=["cond", "uid"], validate="1:1")
    feats = [c for c in F.columns if c not in ("cond", "uid", "wada_snr")]
    if sens == "feats45":
        B = u3_features_burst(conds, a.no_resume)
        d = d.merge(B, on=["cond", "uid"], validate="1:1")
        feats += [c for c in B.columns if c not in ("cond", "uid")]
    ridge = f"ridge_{len(feats)}"
    arms = {"feats_only_lgbm": ("lgbm", feats), ridge: ("ridge", feats),
            "baseline_snr_logE": ("ridge", ["snr", "log_e_noisy"]),
            "wada_snr": ("ridge", ["wada_snr"])}
    # The yaml writes "> baseline rho" without naming an arm. Resolved to both of
    # U3_within_condition's baselines, the stricter of the two readings, so the
    # resolution cannot inflate a pass. wada_snr is carried descriptively.
    rivals = [ridge, "baseline_snr_logE"]

    def loto(g: pd.DataFrame, corpus: str, col: str = "noise_type") -> list[dict]:
        # noise_type names the MarVEN type on every row, DEMAND and FSD50K rows
        # included, because the xcorpus mixtures reuse it. So the held-out class for
        # those corpora is cond, which is what stage_u3 groups their cells by too.
        out = []
        for ho in sorted(g[col].unique()):
            tr = g[g[col] != ho]
            te = g[g[col] == ho].reset_index(drop=True)
            if tr.empty or len(te) < 25:
                print(f"u3_transfer {corpus}/{ho}: too few rows, skipped")
                continue
            preds = {k: _fit(kind, cols, tr, te, C.SEED)
                     for k, (kind, cols) in arms.items()}
            w = within(te, preds, by=["snr"])
            if w.empty:
                print(f"u3_transfer {corpus}/{ho}: no SNR cell reached min_n, skipped")
                continue
            mean = {k: float(w[k].mean()) for k in arms}
            row = {"corpus": corpus, "heldout_class": ho, "heldout_by": col,
                   "n_snr_cells": len(w), "n_test_rows": len(te),
                   "n_train_rows": len(tr)}
            row |= {f"mean_rho_{k}": round(mean[k], 4) for k in arms}
            row |= {f"beats_{k}": bool(mean["feats_only_lgbm"] > mean[k]) for k in rivals}
            row["type_pass"] = all(row[f"beats_{k}"] for k in rivals)
            out.append(row)
            print(f"u3_transfer {corpus}/{ho}: {len(w)} snr cells, mean rho "
                  + ", ".join(f"{k}={mean[k]:.3f}" for k in arms))
        return out

    marven = d[d.cond == "marven"].reset_index(drop=True)
    expected = sorted(C.WEATHER + C.ANTHRO)
    assert sorted(marven.noise_type.unique()) == expected,         f"MarVEN types drifted from the yaml's 5: {sorted(marven.noise_type.unique())}"
    cells = loto(marven, "marven")
    n_pass = sum(c["type_pass"] for c in cells)
    passed = n_pass >= min_types

    # The yaml's report: line asks for the same test on DEMAND / FSD50K held-out
    # classes, descriptive. These rows carry no weight in the verdict.
    for corpus, cs in CORPORA.items():
        if corpus == "marven":
            continue
        g = d[d.cond.isin(cs)].reset_index(drop=True)
        if g.empty:
            print(f"u3_transfer: no rows for {corpus}, skipped")
            continue
        cells += loto(g, corpus, "cond")

    notes = {
        "types_passed": f"{n_pass} of {len(expected)}",
        "verdict_basis": "MarVEN rows only; DEMAND / FSD50K cells are descriptive",
        "heldout_class": "MarVEN holds out noise_type (5 types). DEMAND and FSD50K hold "
                         "out cond (3 each), because noise_type carries the MarVEN type "
                         "on every row of every corpus and is not their noise class.",
        "baseline_resolved_to": rivals,
        "baseline_ambiguity": "U3_transfer pass_if says '> baseline rho' and names no "
                              "arm. Resolved to both baselines of U3_within_condition, "
                              "the stricter reading. No threshold was changed.",
        "features": f"{len(feats)} features"
                    + (" (src.features 33 plus src.features_burst 12)" if sens == "feats45"
                       else " (src.features), the set U3_within_condition registered "
                            "as ridge_33"),
        "split": "leave-one-noise-type-out; predictor refit per held-out type",
        "speaker_overlap": "the registered design holds out the noise type only. "
                           "MarVEN has 10 speakers and every type carries all of them, "
                           "so test speakers are training speakers. Not speaker-disjoint.",
        "enhancer": "fixed; no model retrained and no mixture re-rendered",
        "label": "log10(r_over_x), level-aligned (_g) output STFT",
        "cells": "within-SNR Spearman, min 25 rows per SNR cell",
    }
    if sens:
        # A post-hoc variant is not the gate. Its own file, its own notes, and it never
        # touches u3_transfer_verdict.json, which was decided before this ran.
        notes |= {"post_hoc": True, "sensitivity": sens,
                  "pre_registered_verdict": "u3_transfer_verdict.json",
                  "deviation": "the feature set is the 33 base features plus the 12 "
                               "burst features of src/features_burst.py. The yaml "
                               "registered 33 by naming its arm ridge_33. Thresholds, "
                               "arms and the leave-one-type-out design are unchanged."}
    write_verdict(f"u3_transfer_sens_{sens}" if sens else "u3_transfer", cfg, sha,
                  {"design": u["design"], "pass_if": u["pass_if"],
                   "report": u["report"], "min_types": min_types,
                   "n_marven_types": len(expected), "enhancer_tag": a.tag},
                  cells, passed, notes)

# ------------------------------------------------------------------- U2 ----
# The yaml names the non-bounded classes in prose; these are the checkpoint prefixes
# that stand for them. complex_mask -> cm is configs/gate_amend_cm.yaml, committed
# before any cm model was trained. dfn3 and sgmse are file-based: they run in the
# dfnet / sgmse envs, so their rows arrive through src.segment's --score-windows.
U2_CLASSES = {"complex_mask": ["cm"], "diverse_pretrained": ["dfn3"], "generative": ["sgmse"]}


def stage_u2(cfg: dict, sha: str, a) -> None:
    """U1's rule applied to the non-bounded architecture classes. Reuses u1_verdict with
    a different model list, which is why that function takes one.

    A class with no rows is not a failing class, it is a missing measurement, so this
    refuses to write a verdict until enough classes have data. Writing FAIL for an
    unmeasured arm would put a pre-registered verdict file on the record that says
    something the run never tested."""
    u = cfg["U2_beyond_bounded"]
    min_classes = int(_after(u["pass_if"], ">="))
    have, missing = {}, {}
    for cls, archs in U2_CLASSES.items():
        ready = [k for k in archs
                 if all((SEG / f"{k}_seg_{f}__{s}.csv").exists()
                        for f in C.FAMILIES for s in ("windows", "unseen"))]
        (have if ready else missing)[cls] = ready or archs
    if len(have) < min_classes:
        raise SystemExit(
            f"u2 needs {min_classes} of {len(U2_CLASSES)} non-bounded classes and has "
            f"{len(have)} ({', '.join(have) or 'none'}). Missing: "
            + "; ".join(f"{c} ({'/'.join(k)})" for c, k in missing.items())
            + ".\nEach missing arm needs a half-A fine-tune, then: python -m src.segment "
              "--fold <fold> --export-windows DIR, run the model over DIR, then "
              "--score-windows DIR --tag <arch>.")
    archs = [k for ks in have.values() for k in ks]
    rows = u1_rows(archs)
    cells, arch_pass, thresholds = u1_verdict(rows, archs, cfg)
    class_pass = {c: any(arch_pass[k] for k in ks) for c, ks in have.items()}
    amend = REPO / "configs" / "gate_amend_cm.yaml"
    write_verdict("u2", cfg, sha,
                  thresholds | {"pass_if": u["pass_if"], "min_classes": min_classes,
                                "on_fail": u["on_fail"]},
                  cells, sum(class_pass.values()) >= min_classes,
                  {"class_pass": class_pass, "arch_pass": arch_pass,
                   "classes_measured": have, "classes_missing": missing,
                   "complex_mask_amendment_sha256_12":
                       hashlib.sha256(amend.read_bytes()).hexdigest()[:12],
                   "rungs": {"R1": "A windows", "R2": "B windows",
                             "R4": "test_unseen windows"},
                   "requirement": "each arm must be fine-tuned on half A only, or R1 "
                                  "and R2 are the same measurement"})


STAGES = {"u1": stage_u1, "u1class": stage_u1class, "u3": stage_u3, "u2": stage_u2,
          "u3_transfer": stage_u3_transfer}
SENS_GATE = {"canonical_lgbm": "u3", "feats45": "u3_transfer"}
ORDER = ("u1", "u1class", "u3")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gate", required=True, choices=[*STAGES, "all"])
    p.add_argument("--force", action="store_true", help="re-run a stage that has a verdict")
    p.add_argument("--no-resume", action="store_true",
                   help="retrain checkpoints and re-extract caches instead of reusing them")
    p.add_argument("--tag", default="b1_weather", help="U3 enhancer whose r_over_x is the label")
    p.add_argument("--allow-cpu", action="store_true",
                   help="let U1 train on the CPU (about 25 h for the four models)")
    p.add_argument("--sens", choices=[*SENS_GATE],
                   help="post-hoc sensitivity variant, written to its own "
                        "<gate>_sens_<name>_verdict.json; the pre-registered verdict is "
                        "left alone")
    a = p.parse_args(argv)
    if a.sens and SENS_GATE[a.sens] != a.gate:
        p.error(f"--sens {a.sens} is a {SENS_GATE[a.sens]} variant; "
                f"use it with --gate {SENS_GATE[a.sens]}")
    cfg, sha = load_gate()
    for gate in (ORDER if a.gate == "all" else [a.gate]):
        gid = f"{gate}_sens_{a.sens}" if a.sens and SENS_GATE[a.sens] == gate else gate
        v = OUT / f"{gid}_verdict.json"
        if v.exists() and not a.force:
            print(f"{gid}: {json.loads(v.read_text())['verdict']} already in {v.name}, "
                  "skipped (--force to re-run)")
            continue
        print(f"\n######## {gid} ########", flush=True)
        STAGES[gate](cfg, sha, a)


if __name__ == "__main__":
    main()
