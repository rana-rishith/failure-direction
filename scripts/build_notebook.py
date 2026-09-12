"""
Regenerate notebooks/main.ipynb.

    python scripts/build_notebook.py

The notebook is a thin driver over `src/` — every cell calls into the modules so
that notebook and command line cannot diverge. That is deliberate: the original
project had two definitions of the trainer, two of CKPT, and a models/ package
that disagreed with the notebook classes about state-dict prefixes.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CELLS: list[tuple[str, str]] = [
    ("md", """# FailDir — main notebook

Run the cells in order. Cell 1 is the only cell that must be re-run after a
kernel restart; nothing later depends on hidden state from an earlier session.

Set `FAILDIR_ROOT` (and `FAILDIR_TRANS` for the WER stage) in Cell 2 or as
environment variables before launching Jupyter. No path in this notebook is
machine-specific.

Stage order: environment -> config -> data -> inspection -> folds -> models ->
training -> validation -> evaluation -> claims & gates -> WER -> Claim 3 labels
-> features -> verdict -> results -> final verification."""),

    ("md", "## Cell 1 — imports and path bootstrap\n\nRe-run this, and only this, after a kernel restart."),
    ("code", """import os, sys
from pathlib import Path

REPO = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(REPO))

# Point these at your copies. Leave them unset to use <repo>/data/...
# os.environ["FAILDIR_ROOT"]  = r"C:\\Users\\ranar\\failure-direction\\MarVEN"
# os.environ["FAILDIR_TRANS"] = r"C:\\Users\\ranar\\LibriSpeech\\train-clean-100"

import config as C          # sets KMP_DUPLICATE_LIB_OK before torch is imported
from src import data as D, models as M, metrics as MT
from src import train as T, evaluate as E, analysis as A
from src import labels as L, features as FE, claim3 as C3

import numpy as np, pandas as pd, torch

print(sys.executable)       # must be the faildir env
print(C.summary())"""),

    ("md", "## Cell 2 — configuration\n\nEvery constant lives in `config.py`. Change it there, not here, so the notebook and the scripts stay in agreement."),
    ("code", """C.ensure_dirs()
C.set_seed(C.SEED)
C.tune_backends()
DEV = C.device()
print(f"device {DEV} | steps {C.TRAIN_STEPS} bs {C.BATCH_SIZE} lr {C.LR} seed {C.SEED}")
print(f"stft N_FFT={C.N_FFT} HOP={C.HOP} bins={C.N_BINS} | crop {C.CROP/C.SR:.0f}s")"""),

    ("md", "## Cell 3 — environment / dependency verification"),
    ("code", """import subprocess
print(subprocess.run([sys.executable, "scripts/00_verify_env.py"],
                     cwd=REPO, capture_output=True, text=True).stdout)"""),

    ("md", "## Cell 4 — dataset setup"),
    ("code", """C.require_dataset()
df = D.load_manifest(verbose=True)
print(D.verify_disk(df, n=300))
df.head(3)"""),

    ("md", "## Cell 5 — data inspection\n\nThe shipped `split` column is speaker-disjoint but **not** noise-disjoint: every noise type appears in every split. That is why the folds are rebuilt in Cell 7."),
    ("code", """print(df.groupby(["family", "noise_type"]).size().to_string())
print("\\nSNR levels:", sorted(df.target_snr_db.unique()))
print(df.pivot_table(index="split", columns="noise_type", values="uid",
                     aggfunc="count").fillna(0).astype(int).to_string())
print("\\nutterance appearances (MarVEN's sampled design: exactly 2):",
      df.key.value_counts().unique())
print("max |measured - target| snr:",
      float((df.measured_snr_db - df.target_snr_db).abs().max()))"""),

    ("md", "## Cell 6 — preprocessing\n\nThere is no offline preprocessing step. Mixing is already synthetic and exact, and the only transforms are the 4-second random crop (training) and the STFT inside the models. Both are deterministic given the seed."),
    ("code", """x, y = D.read_pair(df.iloc[0])
print("pair", x.shape, y.shape, "aligned:", x.shape == y.shape)
ds = D.MarVEN(df.head(4), train=True)
xc, yc, snr, ntype, uid = ds[0]
print("cropped", tuple(xc.shape), tuple(yc.shape), snr, ntype, uid)"""),

    ("md", """## Cell 7 — cross-condition folds

Filter by family **inside** the shipped speaker split. Filtering by family alone
is not sufficient: each utterance has two rows that may straddle families, so
the same speaker and the same clean waveform can land on both sides.

The three leakage assertions run on every fold build. Do not comment them out —
a single leaked file makes Claim 1 collapse silently while still looking
plausible."""),
    ("code", """folds = D.build_folds(df)
print(D.fold_report(folds).to_string(index=False))
print("\\nweather/test_matched == anthro/test_unseen:",
      set(folds["weather"]["test_matched"].uid) == set(folds["anthro"]["test_unseen"].uid))"""),

    ("md", "## Cell 8 — model definitions\n\nB1 SpectralMask (BLSTM), B3 CausalMask (GRU), B4 Passthrough. B2 (diffusion) is deferred; it does not fit in 8–12 GB and is a substantially larger build."),
    ("code", """for k in ("b1", "b3", "b4"):
    m = M.MODELS[k]()
    with torch.no_grad():
        a, mask = m(torch.zeros(1, C.SR))
    print(f"{k}: {M.n_params(m):>10,} params | out {tuple(a.shape)} | mask {tuple(mask.shape)}")"""),

    ("md", "## Cell 9 — model initialisation / checkpoint loading\n\nSkip if you are about to train. `load_model` accepts both checkpoint formats and fails fast on a shape mismatch."),
    ("code", """print(pd.DataFrame(M.checkpoint_report()).to_string(index=False)
      if M.checkpoint_report() else "no checkpoints yet")"""),

    ("md", """## Cell 10 — training configuration

SI-SDR loss, AdamW, 20,000 gradient steps per run. `steps` is held constant
across every baseline and both folds: that is what makes the comparison
equal-compute despite the 38.3 h / 25.3 h family imbalance. Training by epoch
count would silently hand the weather fold ~50% more updates."""),
    ("code", """est = torch.randn(2, C.SR); ref = est + 0.1 * torch.randn(2, C.SR)
print("si_sdr_loss sanity (should be negative, ~-20):", float(MT.si_sdr_loss(est, ref)))
print("si_sdr identity (should be > 60 dB):", MT.si_sdr(ref[0], ref[0]))"""),

    ("md", """## Cell 11 — training

Long runs belong in a terminal, not a notebook cell: a disconnected kernel kills
the process, while `python -m src.train ...` survives. The trainer is
crash-resumable — re-run the identical command and it picks up from the last
atomic checkpoint.

    python -m src.train --model b1 --fold weather --steps 20000

The cell below is the in-notebook equivalent. Use a small `steps` to smoke-test
first; validation SI-SDR should move in the right direction within 2,000 steps.
If it is flat, something upstream is wrong and it is far cheaper to find now."""),
    ("code", """SMOKE = True    # set False for the full 20,000-step protocol
steps = 200 if SMOKE else C.TRAIN_STEPS

for model_key in ("b1", "b3"):
    for fam in C.FAMILIES:
        T.train(model_key, folds[fam], f"{model_key}_{fam}",
                steps=steps, val_every=max(20, steps // 4))"""),

    ("md", "## Cell 12 — validation\n\nValidation is deterministic but speaker-skewed: it reads the first 200 val rows unshuffled. Fine for early stopping. Do **not** report it as a metric — validation and evaluation numbers do not reconcile and should not be made to."),
    ("code", """m = M.load_model("b1", "b1_weather")
print("val SI-SDR loss (b1_weather):", T.validate(m, folds["weather"]["val"], C.device()))
del m"""),

    ("md", """## Cell 13 — evaluation matrix

Ten cells: B1 and B3 across both folds and both splits, plus B4 on both splits.
B4 needs only two — Passthrough has no weights, so its numbers are identical
whichever fold label is attached. `batch_size=1`, full-length audio, no cropping.

With PESQ this takes ~85 minutes on the full corpus; without it, ~25. Watch the
guard report at the end: if `nan_from_exception` equals the call count, PESQ is
not actually installed and every PESQ column is NaN."""),
    ("code", """res = E.run_matrix(folds, do_pesq=True)
print(res.groupby(["tag", "fold", "split"])[["si_sdr_out", "stoi_out", "pesq_out"]]
        .mean().round(3).to_string())
print("\\nB4 floor:", E.b4_floor_check(res))"""),

    ("md", """## Cell 14 — metrics: Claims 1 and 2, and the gates

Claim 1 is the matched-minus-unseen gap. Read the absolute unseen numbers too:
the finding is total transfer failure, not partial degradation.

Claim 2 is the direction flip — over-suppression dominant under matched
conditions, under-suppression dominant under unseen ones. Report medians and
IQRs: `r_under` above 1 at low SNR is arithmetic, not a bug, and it is
heavy-tailed."""),
    ("code", """res = A.prepare(res)
_ = A.claim1(res)
_ = A.claim2(res)
gate = A.gates(res)"""),

    ("md", """## Cell 15 — WER (downstream consequence of Claim 1)

Needs `faster-whisper`, `jiwer` and the LibriSpeech `train-clean-100`
transcripts. Reported as a downstream consequence of Claim 1, **not** as gate
G3: it cannot attribute consequences to failure direction rather than to
condition, because the two are collinear.

Never pool across noise types. Hurricane and bubble_curtain sit at the clean ASR
floor even at −15 dB broadband SNR; the whole effect lives in rainfall,
large_commercial_ship and lightning."""),
    ("code", """from src import wer as W
RUN_WER = False          # ~50-55 min for the 818-row negative-SNR subset
if RUN_WER:
    h = W.run(df, snr_max=-5)
    tables = W.aggregate(h)
else:
    print("skipped — set RUN_WER=True, or use: python -m src.wer --snr-max -5")
    print("smoke test without an ASR model: python -m src.wer --engine stub --limit 24")"""),

    ("md", """## Cell 16 — Claim 3: labels, features, verdict

Scoped to within-condition magnitude prediction on `r_over`. Direction and
condition are ~99.4% collinear, so a direction classifier would be predicting
noise family from spectral shape and proving nothing.

Labels come from B1 only — Claim 3 predicts the failure of one specific
enhancer, and the cross-architecture rank agreement is the justification for
that, not a reason to fit both. The feature side never touches `clean_path`."""),
    ("code", """_ = C3.cross_arch_agreement(res)      # precondition: is failure input-determined?

lab = L.run(folds)
L.sanity(lab)
feat = FE.run(folds)
print(f"features: {len(feat)} rows")

for fam in C.FAMILIES:
    print(f"\\n########## fold {fam} ##########")
    C3.run(fam)"""),

    ("md", "## Cell 17 — results and final verification\n\nEvery table is on disk under `results/metrics/`. This cell re-checks the invariants that matter and lists what was written."),
    ("code", """import subprocess
print(subprocess.run([sys.executable, "-m", "pytest", "-q"],
                     cwd=REPO, capture_output=True, text=True).stdout[-1500:])

full = E.load_matrix()
print("eval rows:", len(full), "| NaN si_sdr_out:", int(full.si_sdr_out.isna().sum()))
print("B4 invariants:", E.b4_floor_check(full))
D.assert_no_leakage(folds["weather"], "weather")
D.assert_no_leakage(folds["anthro"], "anthro")
print("leakage: clean")

for p in sorted(C.METRICS.glob("*")):
    print(f"  {p.name:46s} {p.stat().st_size/1024:8.1f} KB")"""),
]


def build() -> Path:
    cells = []
    for kind, src in CELLS:
        lines = src.splitlines(keepends=True)
        if kind == "md":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
        else:
            cells.append({"cell_type": "code", "execution_count": None,
                          "metadata": {}, "outputs": [], "source": lines})
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "faildir", "language": "python",
                           "name": "faildir"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }
    out = REPO / "notebooks" / "main.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(cells)} cells)")
    return out


if __name__ == "__main__":
    build()
