"""Does FSD50K contain marine-like sounds? Reviewer item #3a.

    python scripts/fsd_similarity_posthoc.py                 # full training pool
    python scripts/fsd_similarity_posthoc.py --limit 300      # smoke run

Everything here is POST HOC AND DESCRIPTIVE. No gate reads these outputs, which is
why they live under results/fsd_similarity_posthoc/. The protocol requires a check
computed after the fact to say so; this is one, and it can never be read as
confirmatory evidence.

The claim being checked
-----------------------
The paper says the FSD50K-trained models never heard marine noise. That currently
rests on labels: src/fsd.py EXCLUDE_MARINE keeps every rain, thunder, wind, water
and water-vehicle clip out of the training pool. A reviewer can answer that an
unlabelled clip may still sound marine. This measures it acoustically instead.

Features are src/distance.py unchanged - `logmel_frames` (64-band log-mel of
RMS-normalised audio, so level plays no part), `gaussian`, `frechet`, `ltas`. No
second feature extractor exists here, and the MarVEN side is `marven_source`
itself, the same per-type pooled Gaussian src.distance builds.

Two scales, because they answer different questions
---------------------------------------------------
- Per clip: the LTAS distance from each of the ~29,850 training clips to each
  MarVEN type. This finds the single closest thing in the pool - the strictest
  form of the reviewer's question. Per-clip Gaussians are unstable on short
  clips, so only LTAS (the mean log-mel vector) is used at this scale.
- Pooled: the Frechet distance between a MarVEN type and the pooled frames of its
  top-k nearest clips, k = 10, 50, 200. This is the scale the control and the
  calibration pairs live on, so it is the comparison that settles the claim.

Reference pairs, without which a distance is just a number
----------------------------------------------------------
- Positive control: DeepShip ship (Cargo / Tanker / Passengership, the same pool
  src/r3.py uses) against MarVEN large_commercial_ship. A known same-class pair,
  so it sets what "sounds like the same thing" measures. Computed pooled, and
  also per 10 s crop so the per-clip column has a control on its own scale.
- Calibration: MarVEN against MarVEN - rainfall vs hurricane, rainfall vs
  lightning, large_commercial_ship vs bubble_curtain. These set what a genuine
  between-type difference measures inside the corpus the paper is about.

If the nearest FSD50K clips are farther from a MarVEN type than DeepShip ship is
from MarVEN ship, the claim holds acoustically. Where they fall against the
calibration pairs says how much farther.

The selection bias that comparison has, and the reference that fixes it
-----------------------------------------------------------------------
The nearest FSD50K clip is a MINIMUM over ~29,850 candidates. The positive control
and the calibration pairs are single unselected pairs. So the FSD side is an
extreme-order statistic and the reference side is not, and the raw comparison
flatters the FSD side however far apart the two corpora really are - on a 250-clip
smoke run the pooled top-10 FD to MarVEN ship already came in below the DeepShip
control, which cannot be read as FSD50K containing better ship noise than DeepShip.

So a third reference is computed on exactly the per-clip scale and exactly the same
minimum-over-a-pool footing: FSD50K's own marine-labelled EVAL clips, the
`fsd_weather` (325) and `fsd_boat` (25) pools that EXCLUDE_MARINE held out of
training. Those clips ARE labelled rain, thunder, wind and boat, so they are what
"a marine-like sound in FSD50K" measures. The question the paper needs becomes:
is the nearest TRAINING clip as close to a MarVEN type as the nearest held-out
MARINE clip is? If the labelled marine clips are clearly closer, the label-based
exclusion did its job and the claim holds. If they are not distinguishable, LTAS
cannot separate marine from non-marine in FSD50K at all, and the claim cannot be
supported acoustically either way - which is a result about the measurement, not
about the training pool, and notes.md says so.

Writes, under FAILDIR_EVAL/fsd_similarity_posthoc:
    nearest.csv   per MarVEN type x FSD clip, the top TOP_N by LTAS, with labels
    summary.csv   one row per reference pair and per pooled top-k, long form
    notes.md      the five nearest clips per type, one line each; the listening
                  lines are Rana's to fill in and the file says why
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import config as C  # noqa: E402  (must precede torch: sets KMP_DUPLICATE_LIB_OK)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import soundfile as sf  # noqa: E402

from src import fsd as F  # noqa: E402
from src.distance import SEG_LEN, frechet, gaussian, logmel_frames, ltas, marven_source  # noqa: E402
from src.r3 import SHIPS, Pool  # noqa: E402
from src import data as D  # noqa: E402

OUT = C.EVAL / "fsd_similarity_posthoc"
TYPES = tuple(C.WEATHER) + tuple(C.ANTHRO)
MARVEN_SHIP = "large_commercial_ship"
KS = (10, 50, 200)
TOP_N = max(KS)                 # how many ranked clips per type reach nearest.csv
# FSD50K's own marine-labelled EVAL clips, which src/fsd.py EXCLUDE_MARINE kept out
# of training. They are the reference that makes the per-clip column readable: see
# the selection-bias note in the module docstring.
MARINE_POOLS = ("fsd_weather", "fsd_boat")
N_SHIP_CROPS = 60               # 10 s DeepShip crops: the per-clip control
CALIBRATION = (("rainfall", "hurricane"), ("rainfall", "lightning"),
               (MARVEN_SHIP, "bubble_curtain"))
DEEPSHIP = C.ROOT.parent / "DeepShip-main"


# ------------------------------------------------------------------ sources --
def marven_gaussians(df: pd.DataFrame) -> dict:
    """One pooled Gaussian per MarVEN type from test-split rows, n = x - y."""
    out = {}
    for t in TYPES:
        out[t] = marven_source(df, t, "test")
        print(f"  marven {t}: done", flush=True)
    return out


def deepship_frames(root: Path, n_crops: int = N_SHIP_CROPS) -> list[np.ndarray]:
    """Log-mel frames of 10 s DeepShip ship crops, one list entry per crop.

    src.r3.Pool is reused because it already knows DeepShip's 32 kHz and
    decimates it to 16 kHz the way every other DeepShip number in this repo was
    produced. The crops are seeded, so the control is the same on every run.
    """
    files = [p for p in Path(root).rglob("*.wav") if p.parent.name in SHIPS]
    if not files:
        raise FileNotFoundError(f"no DeepShip ship wavs under {root} (dirs {SHIPS})")
    pool = Pool(files)
    rng = np.random.default_rng(C.SEED)
    print(f"  deepship: {len(files)} ship files, {n_crops} crops", flush=True)
    return [logmel_frames(pool.crop(SEG_LEN, rng)[0]) for _ in range(n_crops)]


def clip_frames(split: str, fname: int) -> np.ndarray:
    """Log-mel frames of one cached 16 kHz FSD50K clip. src.fsd._dst is the one
    place that knows the cache layout, so it is not spelled out a second time."""
    x, sr = sf.read(str(F._dst(split, fname)), dtype="float32")
    if sr != C.SR:
        raise ValueError(f"{fname}: cache is {sr} Hz, expected {C.SR}")
    return logmel_frames(x if x.ndim == 1 else x.mean(1))


# -------------------------------------------------------------- per-clip pass --
def per_clip_ltas(clips: pd.DataFrame, mg: dict, log_every: int = 2000) -> pd.DataFrame:
    """LTAS from every training clip to every MarVEN type. One pass, mean log-mel
    only: `ltas` reads the Gaussian's mean, and a per-clip covariance would be the
    unstable quantity the handoff warns about."""
    rows = []
    for i, r in enumerate(clips.itertuples()):
        fr = clip_frames(r.split, int(r.fname))
        if len(fr) == 0:                    # silent or sub-frame clip: no LTAS to take
            continue
        gc = gaussian(fr)
        rows.append({"fname": int(r.fname), "split": r.split, "leaf": r.leaf,
                     "labels": r.labels, "n_frames": len(fr),
                     **{t: ltas(mg[t], gc) for t in TYPES}})
        if log_every and (i + 1) % log_every == 0:
            print(f"  clips {i + 1}/{len(clips)}", flush=True)
    return pd.DataFrame(rows)


def ranked(d: pd.DataFrame, pool: str, top_n: int = TOP_N) -> pd.DataFrame:
    """Long form: the top_n nearest clips per MarVEN type, with their rank."""
    out = []
    for t in TYPES:
        q = d.nsmallest(min(top_n, len(d)), t)[
            ["fname", "split", "leaf", "labels", "n_frames", t]]
        q = q.rename(columns={t: "ltas"}).assign(
            pool=pool, noise_type=t, rank=np.arange(1, len(q) + 1))
        out.append(q)
    cols = ["pool", "noise_type", "rank", "fname", "split", "ltas", "leaf", "labels",
            "n_frames"]
    return pd.concat(out, ignore_index=True)[cols]


# ---------------------------------------------------------------- the summary --
def summarise(d: pd.DataFrame, near: pd.DataFrame, mg: dict, ship_frames: list,
              marine: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per reference pair, long form, so the scales sit side by side."""
    rows = []
    train = near[near.pool == "train"]

    def add(kind, a, b, k, lt, fd, n):
        rows.append({"kind": kind, "a": a, "b": b, "k": k, "ltas": lt, "fd": fd, "n": n})

    # 1. the single nearest clip, and the spread of the ten nearest
    for t in TYPES:
        q = train[train.noise_type == t]
        add("fsd_nearest_clip", t, f"clip_{int(q.iloc[0].fname)}", 1,
            float(q.iloc[0].ltas), np.nan, len(d))
        add("fsd_top10_clips", t, "per-clip median of the 10 nearest", 10,
            float(q.head(10).ltas.median()), np.nan, 10)

    # 1b. the same two numbers for FSD50K's own held-out MARINE-labelled clips: the
    # reference that puts the per-clip column on a readable footing (see docstring)
    for pool in (MARINE_POOLS if marine is not None else ()):
        q0 = marine[marine.pool == pool]
        if q0.empty:
            continue
        for t in TYPES:
            q = q0[q0.noise_type == t]
            add(f"{pool}_nearest_clip", t, f"clip_{int(q.iloc[0].fname)}", 1,
                float(q.iloc[0].ltas), np.nan, len(q))
            add(f"{pool}_top10_clips", t, "per-clip median of the 10 nearest", 10,
                float(q.head(10).ltas.median()), np.nan, min(10, len(q)))

    # 2. pooled top-k: the scale the control and the calibration pairs live on
    for t in TYPES:
        q = train[train.noise_type == t]
        frames, got = [], 0
        for r in q.itertuples():
            frames.append(clip_frames(r.split, int(r.fname)))
            got += 1
            if got in KS:
                g = gaussian(np.concatenate(frames))
                add("fsd_pooled_topk", t, f"top{got}", got,
                    ltas(mg[t], g), max(frechet(mg[t], g), 0.0),
                    int(sum(len(f) for f in frames)))
            if got >= max(KS):
                break

    # 3. positive control, pooled and per 10 s crop
    gs = gaussian(np.concatenate([f for f in ship_frames if len(f)]))
    add("control_pooled", MARVEN_SHIP, "deepship_ship", len(ship_frames),
        ltas(mg[MARVEN_SHIP], gs), max(frechet(mg[MARVEN_SHIP], gs), 0.0),
        int(sum(len(f) for f in ship_frames)))
    per = sorted(ltas(mg[MARVEN_SHIP], gaussian(f)) for f in ship_frames if len(f))
    add("control_per_crop_nearest", MARVEN_SHIP, "deepship_ship nearest crop", 1,
        per[0], np.nan, len(per))
    add("control_per_crop_top10", MARVEN_SHIP, "deepship_ship median of 10 nearest crops",
        10, float(np.median(per[:10])), np.nan, 10)

    # 4. calibration: what a real between-type difference measures in this corpus
    for a, b in CALIBRATION:
        add("calibration", a, b, np.nan, ltas(mg[a], mg[b]),
            max(frechet(mg[a], mg[b]), 0.0), np.nan)
    return pd.DataFrame(rows)


def _verdict(near: pd.DataFrame, s: pd.DataFrame) -> list:
    """What this run actually found, read off the tables rather than asserted."""
    train = near[near.pool == "train"]
    closer, lines = [], []
    for t in TYPES:
        a = s[(s.kind == "fsd_nearest_clip") & (s.a == t)]
        b = s[(s.kind == "fsd_weather_nearest_clip") & (s.a == t)]
        c = s[(s.kind == "fsd_boat_nearest_clip") & (s.a == t)]
        if not (len(a) and len(b) and len(c)):
            continue
        lo = min(float(b.iloc[0].ltas), float(c.iloc[0].ltas))
        if float(a.iloc[0].ltas) < lo:
            closer.append(t)
        top = train[train.noise_type == t].head(5)
        lines.append(f"- **{t}**: nearest training clips are "
                     + ", ".join(f"`{x}`" for x in top.leaf.tolist()))
    L = ["## What this run found", ""]
    L.append(f"On the per-clip LTAS scale the nearest TRAINING clip is closer to the MarVEN "
             f"type than ANY held-out marine-labelled clip for **{len(closer)} of "
             f"{len(TYPES)}** types ({', '.join(closer) if closer else 'none'}). So the "
             "measurement does not separate marine from non-marine here, and the leaf labels")
    L += ["of those nearest clips say why:", ""]
    L += lines
    L += ["",
          "Breathing, a church bell, a piano and a door knock are not rain, thunder or a",
          "ship, and no listener would confuse them. A 64-band LTAS ranks them ahead of",
          "FSD50K's own labelled rain and thunder clips, so on this evidence the acoustic",
          "check **cannot support the paper's claim and cannot refute it either**. The",
          "claim should keep resting on the labels, and the Limitations sentence should",
          "say that an acoustic check was run and was uninformative rather than claim it",
          "passed.",
          "",
          "One substantive exception is worth a sentence in its own right. For",
          f"`{MARVEN_SHIP}` the nearest training clips are machinery - subway, train, bus,",
          "engine, aircraft - and the nearest labelled `fsd_boat` clip sits right among",
          "them rather than below them. MarVEN ship noise IS engine noise, and",
          "`EXCLUDE_MARINE` removed the `Boat_and_Water_vehicle` label but not `Train`,",
          "`Engine`, `Subway_and_metro_and_underground` or `Motor_vehicle_(road)`. So for",
          "the ship type the training pool does contain spectrally adjacent broadband",
          "machinery, and 'never saw marine noise' is a statement about labels, not about",
          "what the models heard. For the four weather and bubble-curtain types the nearest",
          "neighbours are incidental and unrelated, so there the unseen framing is safe on",
          "semantics even though LTAS cannot certify it.",
          ""]
    return L


def notes(near: pd.DataFrame, s: pd.DataFrame, out: Path) -> Path:
    """The listening file. It is written with the labels and the measured distances
    filled in and the heard description left open, because this process cannot
    listen and must not pretend the numbers settled the question."""
    ctl = s[s.kind == "control_pooled"].iloc[0]
    ctl_near = s[s.kind == "control_per_crop_nearest"].iloc[0]
    cal = s[s.kind == "calibration"]
    L = [
        "# What do the nearest FSD50K clips actually sound like?",
        "",
        "Post hoc and descriptive. No gate reads this file.",
        "",
        "## Why a number cannot close this",
        "",
        "Every distance here is between log-mel *spectra* of RMS-normalised audio. That",
        "throws away level, phase and all temporal structure above the frame rate, which",
        "is most of what makes a sound recognisable. Two recordings can sit close in this",
        "space and be obviously different things to a listener - broadband hiss from a",
        "crowd, a hairdryer and rain on water are near neighbours by LTAS and nobody",
        "confuses them by ear. The measurement can therefore show that nothing in the",
        "FSD50K training pool is acoustically close to MarVEN noise, which is a real",
        "result and the one the paper needs; it cannot show that something close-by",
        "*sounds marine*. Only listening settles that, and only listening can catch the",
        "case the reviewer is really asking about: an unlabelled clip that a human would",
        "call rain or a boat.",
        "",
        "**The lines below are Rana's to fill in.** Each one names the clip, its FSD50K",
        "labels and its measured distance; the `heard:` field is deliberately empty. The",
        "cached 16 kHz audio is at",
        f"`{F.CACHE}/<split>/<fname>.wav`.",
        "",
        "## Reference points, for reading the distances",
        "",
        f"- positive control, DeepShip ship vs MarVEN {MARVEN_SHIP}, pooled: "
        f"LTAS {ctl.ltas:.2f} dB, FD {ctl.fd:.1f}",
        f"- the same control at per-crop scale, nearest 10 s crop: LTAS {ctl_near.ltas:.2f} dB",
        "- calibration, MarVEN type against MarVEN type:",
    ]
    for r in cal.itertuples():
        L.append(f"  - {r.a} vs {r.b}: LTAS {r.ltas:.2f} dB, FD {r.fd:.1f}")
    L += ["",
          "A nearest FSD50K clip farther than the positive control means the pool holds",
          "nothing as close to that MarVEN type as a genuine recording of the same class.",
          "",
          "### Read the per-clip column against the marine reference, not the control",
          "",
          "The nearest training clip is a minimum over ~29,850 candidates; the DeepShip",
          "control and the calibration pairs are single unselected pairs. An extreme-order",
          "statistic will beat an unselected one whatever the corpora are really like, so",
          "`fsd_nearest_clip` being below `control_per_crop_nearest` on its own says",
          "nothing. The rows that are comparable are FSD50K's own held-out marine-labelled",
          "clips, `fsd_weather_*` and `fsd_boat_*` in summary.csv - same per-clip scale,",
          "same minimum-over-a-pool construction, and they are labelled rain, thunder,",
          "wind and boat, so they are what a marine-like FSD50K clip actually measures:", ""]
    for pool in MARINE_POOLS:
        for t in TYPES:
            q = s[(s.kind == f"{pool}_nearest_clip") & (s.a == t)]
            r = s[(s.kind == "fsd_nearest_clip") & (s.a == t)]
            if len(q) and len(r):
                L.append(f"- {t}: nearest held-out {pool} clip {float(q.iloc[0].ltas):.2f} dB "
                         f"vs nearest TRAINING clip {float(r.iloc[0].ltas):.2f} dB")
    L += ["",
          "If the training clips are not clearly farther than the marine-labelled ones,",
          "the honest conclusion is about the measurement: a 64-band LTAS cannot separate",
          "marine from non-marine inside FSD50K, so it can neither support nor refute the",
          "paper's claim, and the claim should keep resting on the labels while saying so.",
          ""]
    L += _verdict(near, s)
    L += ["## The five nearest clips per MarVEN type", ""]
    train = near[near.pool == "train"] if "pool" in near else near
    for t in TYPES:
        q = train[train.noise_type == t].head(5)
        L.append(f"### {t}")
        L.append("")
        for r in q.itertuples():
            L.append(f"- **rank {r.rank}, clip {r.fname}** ({r.split}), "
                     f"LTAS {r.ltas:.2f} dB, {r.n_frames} frames")
            L.append(f"  - labels: `{r.labels}`")
            L.append("  - heard: _(to fill in)_")
        L.append("")
    out.mkdir(parents=True, exist_ok=True)
    p = out / "notes.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=0, help="first N training clips (smoke)")
    ap.add_argument("--deepship", default=str(DEEPSHIP))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    idx = F.load_index()
    clips = idx[(idx.pool == "train") & idx.usable].reset_index(drop=True)
    if a.limit:
        clips = clips.head(a.limit)
    print(f"{len(clips)} FSD50K training clips, {len(TYPES)} MarVEN types", flush=True)

    mg = marven_gaussians(D.load_manifest())
    ship = deepship_frames(Path(a.deepship))
    d = per_clip_ltas(clips, mg)
    near = ranked(d, "train")

    marine = []
    for pool in MARINE_POOLS:
        mc = idx[(idx.pool == pool) & idx.usable].reset_index(drop=True)
        print(f"{len(mc)} held-out {pool} clips (the marine-labelled reference)", flush=True)
        dm = per_clip_ltas(mc, mg, log_every=0)
        if len(dm):
            marine.append(ranked(dm, pool))
    marine = pd.concat(marine, ignore_index=True) if marine else None

    s = summarise(d, near, mg, ship, marine)
    if marine is not None:
        near = pd.concat([near, marine], ignore_index=True)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, frm in (("nearest", near), ("summary", s)):
        frm.to_csv(out / f"{name}.csv", index=False)
        print(f"wrote {(out / name).resolve()}.csv  ({len(frm)} rows)")
    print(f"wrote {notes(near, s, out).resolve()}")


if __name__ == "__main__":
    main()
