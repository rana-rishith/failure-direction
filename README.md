# FailDir — predicting the direction of speech-enhancement failure

Do speech enhancement models fail predictably, and can that failure be
anticipated from the noisy input alone, before enhancement runs?

The work separates two failure modes that a single quality score collapses:

| Mode | What the mask does | Consequence |
|---|---|---|
| **Over-suppression** | drives speech-band energy below the clean reference | speech destroyed, irreversible |
| **Under-suppression** | stays near 1 in noise-dominated bins | noise retained, speech survives, downstream processing still works |

The two are not interchangeable, and they have different downstream costs. A
scalar like SI-SDR or STOI cannot tell you which one happened.

## Objective

Three ordered claims:

1. **Cross-condition generalization gap.** Matched vs unseen noise-family
   performance differs.
2. **Failure-direction flip.** Over-suppression dominates under matched
   conditions; under-suppression dominates under unseen conditions.
3. **Pre-hoc prediction.** A cheap, reference-free feature set computed on the
   noisy input predicts per-utterance over-suppression magnitude, beating a
   pre-registered oracle-SNR + `log(e_noisy)` baseline within SNR strata.

Claim 3 is scoped to **within-condition magnitude prediction on `r_over`**.
Direction and condition are ~99.4% collinear in this data, so a direction
classifier would be predicting noise family from spectral shape and proving
nothing.

## Project structure

```
faildir/
├── README.md
├── requirements.txt            pip deps (PESQ is deliberately absent — see below)
├── environment.yml             conda env, Python 3.12
├── .gitignore
├── config.py                   ONE source of truth: paths, constants, device, seeds
├── configs/
│   └── gate.yaml               pre-committed gate thresholds + sign convention
├── src/
│   ├── data.py                 manifest, cross-condition folds, leakage guards, dataset
│   ├── models.py               B1/B3/B4, STFT helpers, checkpoint I/O
│   ├── metrics.py              SI-SDR, guarded STOI/PESQ, energy decomposition
│   ├── train.py                crash-resumable trainer
│   ├── evaluate.py             the 10-cell evaluation matrix
│   ├── analysis.py             Claims 1 and 2, gates G1-G3
│   ├── labels.py               Claim 3 targets (B1 energy decomposition)
│   ├── features.py             33 reference-free input features
│   ├── claim3.py               LightGBM verdict vs the registered baseline
│   └── wer.py                  ASR pipeline, four arms, aggregation
├── scripts/
│   ├── 00_verify_env.py        environment + checkpoint integrity
│   ├── 01_verify_data.py       manifest, disk, folds, leakage, distributions
│   ├── run_pipeline.py         everything, in order, one command
│   ├── make_synthetic_dataset.py   tiny MarVEN-shaped corpus for smoke tests
│   └── build_notebook.py       regenerates notebooks/main.ipynb
├── notebooks/
│   └── main.ipynb              17 stage cells, thin driver over src/
├── tests/                      36 tests: folds, leakage, sign convention, joins
├── results/                    generated (metrics/ eval/ labels/ features/)
└── ckpt/                       generated checkpoints
```

## Requirements

Python 3.12. A GPU is optional — everything runs on CPU, training is just slow.
The reference runs used an RTX 4060 Laptop (8.6 GB, Ada sm_89) and an RTX 3060
(12 GB, Ampere sm_86), CUDA 12.4.

```
numpy pandas scipy soundfile torch pystoi PyYAML
lightgbm scikit-learn          # Claim 3
jiwer faster-whisper transformers   # WER stage
pytest ipykernel
pesq                           # conda-forge ONLY
```

**PESQ is not in `requirements.txt` on purpose.** No pip wheel exists for
Windows + Python 3.12, so pip tries to compile it and fails without MSVC. Install
it from conda-forge:

```bash
conda install -c conda-forge pesq
```

Everything except the PESQ columns works without it, and the guard in
`src/metrics.py` reports loudly rather than filling the column with silent NaN.

## Installation

```bash
conda env create -f environment.yml
conda activate faildir
pip install torch --index-url https://download.pytorch.org/whl/cu124   # match your CUDA
python -m ipykernel install --user --name faildir --display-name faildir
python scripts/00_verify_env.py
```

Two standing diagnostics worth keeping:

```bash
python -c "import sys; print(sys.executable)"   # must contain envs/faildir
python -m pytest                                # not bare pytest; a base Python can intercept PATH
```

## Dataset

**MarVEN** — Zenodo DOI [10.5281/zenodo.20714212](https://doi.org/10.5281/zenodo.20714212).
22,754 paired clean/noisy recordings, 79.0 hours, 16 kHz, 100 LibriSpeech
`train-clean-100` speakers, 11,377 unique clean utterances. Not redistributed
here; download it yourself.

| Noise type | Family | Rows |
|---|---|---|
| rainfall | weather | 4,587 |
| lightning | weather | 4,583 |
| hurricane | weather | 4,519 |
| bubble_curtain | anthropogenic | 4,570 |
| large_commercial_ship | anthropogenic | 4,495 |

SNR levels −15 to +20 dB in 5 dB steps, roughly 2,800 rows each.
`bubble_curtain` is an offshore construction noise-mitigation device, which is
why the family split is weather vs anthropogenic and not weather vs vessel.

`ROOT` must be the folder that **contains `manifest.csv`, `noisy/` and
`clean/`** — not the repo root. This is the single most common setup mistake.

The WER stage additionally needs LibriSpeech `train-clean-100` transcripts
(`*.trans.txt`). MarVEN's clean audio is amplitude-scaled `train-clean-100`
(scale = `1/mix_scale`, content bit-identical), so true WER against ground-truth
transcripts is recoverable rather than degradation-relative-to-clean-ASR.

### No data? Build a synthetic stand-in

```bash
python scripts/make_synthetic_dataset.py --out data/MarVEN_synth
```

240 rows, 1.5 s each, MarVEN's exact structure: speaker-disjoint 80/10/10
`split` column with all five noise types in every split, every utterance in
exactly two rows, eight SNR levels, LibriSpeech-style transcripts. It produces
**no meaningful research results** — its job is to exercise the whole pipeline
on a machine that does not have the 79-hour corpus.

## Configuration

Everything is in `config.py`, and every path is overridable by environment
variable, so no path in the repo is machine-specific.

| Variable | Meaning | Default |
|---|---|---|
| `FAILDIR_ROOT` | MarVEN root (the folder with `manifest.csv`) | `<repo>/data/MarVEN` |
| `FAILDIR_CKPT` | checkpoints | `<repo>/ckpt` |
| `FAILDIR_EVAL` | results | `<repo>/results` |
| `FAILDIR_TRANS` | LibriSpeech `train-clean-100` | `<repo>/data/LibriSpeech/train-clean-100` |
| `FAILDIR_DEVICE` | force `cuda` or `cpu` | auto |

```bash
# Windows PowerShell
$env:FAILDIR_ROOT = "C:\Users\ranar\failure-direction\MarVEN"
# Windows cmd
set FAILDIR_ROOT=C:\Users\ranar\failure-direction\MarVEN
# bash
export FAILDIR_ROOT=/path/to/MarVEN
```

## How to run

```
environment  ->  data  ->  folds  ->  training  ->  evaluation  ->  claims/gates
                                                        |
                                                        +->  WER
                                                        +->  labels -> features -> Claim 3
```

One command:

```bash
python scripts/run_pipeline.py                 # full protocol
python scripts/run_pipeline.py --smoke         # 40 steps per run, verifies wiring
python scripts/run_pipeline.py --from evaluate # resume at a later stage
python scripts/run_pipeline.py --with-wer      # include the ASR stage
```

Or stage by stage:

```bash
python scripts/00_verify_env.py
python scripts/01_verify_data.py --sample 300

python -m src.train --model b1 --fold weather --steps 20000
python -m src.train --model b1 --fold anthro  --steps 20000
python -m src.train --model b3 --fold weather --steps 20000
python -m src.train --model b3 --fold anthro  --steps 20000

python -m src.evaluate                  # 10 cells, ~85 min with PESQ, ~25 without
python -m src.analysis                  # Claims 1 and 2, gates G1-G3

python -m src.wer --snr-max -5          # ~50-55 min, 818 rows
python -m src.wer --engine stub --limit 24   # pipeline smoke test, no ASR model needed

python -m src.claim3 --precondition     # B1-vs-B3 rank agreement
python -m src.labels                    # ~40 min, 22,754 rows
python -m src.features                  # ~15 min, CPU-bound
python -m src.claim3 --fold weather
python -m src.claim3 --fold weather --damaging-only
```

Every stage is idempotent. Training resumes from the last atomic checkpoint on
re-running the identical command; evaluation, label and feature CSVs are skipped
unless their row count disagrees with the fold they came from (a stale partial
CSV is re-run rather than silently trusted).

Long runs belong in a terminal, not a notebook cell: a disconnected Jupyter
kernel kills the process, a terminal script survives it.

### Notebook

`notebooks/main.ipynb`, 17 stage cells:

| Cell | Stage |
|---|---|
| 1 | imports and path bootstrap — **the only cell to re-run after a kernel restart** |
| 2 | configuration, seeds, device |
| 3 | environment / dependency verification |
| 4 | dataset setup and disk check |
| 5 | data inspection (why the shipped split cannot be used) |
| 6 | preprocessing |
| 7 | cross-condition folds and leakage assertions |
| 8 | model definitions |
| 9 | checkpoint loading / integrity |
| 10 | training configuration and loss sanity |
| 11 | training |
| 12 | validation |
| 13 | evaluation matrix |
| 14 | metrics — Claims 1, 2 and the gates |
| 15 | WER |
| 16 | Claim 3 — labels, features, verdict |
| 17 | results and final verification |

The notebook only calls into `src/`, so it cannot drift from the command line.
Regenerate it with `python scripts/build_notebook.py`. Do not re-run cells out of
order — that was a recurring failure mode in the original workflow, and Cell 1
is deliberately self-sufficient so a kernel restart costs one cell.

## Training protocol

`N_FFT=512`, `HOP=128`, `SR=16000`, 4-second random crops, batch size 8,
AdamW at 2e-4, SI-SDR loss, 20,000 gradient steps, validation every 2,000 steps
on the first 200 rows of the val split.

| ID | Model | Params |
|---|---|---|
| B1 | SpectralMask — non-causal 2-layer BLSTM, h=256 | 2,763,521 |
| B2 | SGMSE-style diffusion | deferred, needs cloud GPU |
| B3 | CausalMask — 2-layer causal GRU, h=128 | 280,833 |
| B4 | Passthrough — identity | no training |

`steps` is constant across every baseline and both folds. **Equal compute means
equal gradient steps, not equal epochs**: weather has 38.3 h of training audio
against anthropogenic's 25.3 h, so training by epoch count would silently hand
the weather fold ~50% more updates and invalidate the comparison.

## Evaluation

Ten cells — B1 and B3 across both folds and both splits, plus B4 on both splits.
B4 needs only two: Passthrough has no weights, so its numbers are identical
whichever fold label is attached. `batch_size=1`, full-length audio, no cropping.

A structural property worth knowing: weather's `test_matched` is the same rows as
anthro's `test_unseen`, and vice versa. Pooled across folds, the matched and
unseen sets are an identical 2,280 utterances differing only in whether the model
that processed them had seen that noise family. The comparison is perfectly
paired, and it confirms itself — `e_clean` is identical for both pooled splits
because it is literally the same audio.

## Expected outputs

```
ckpt/
  b1_weather.pt        weights-only export (11.1 MB, 18 tensors)
  b1_weather_best.pt   resumable: weights + optimiser + scaler + RNG (~33 MB)
  b1_weather_last.pt
  ... x4 tags
results/
  eval/        <tag>__<fold>__<split>.csv     per-utterance, 4,560 rows total
  labels/      b1__<fold>__<split>.csv        22,754 rows
  features/    <fold>__<split>.csv            22,754 rows, 33 features
  metrics/     claim1_*.csv claim2_*.csv gate_*.csv claim3_*.csv
               eval_matrix.csv fold_report.csv wer_*.csv gate_results.yaml
```

Fold sizes to check against:

| Fold | train | val | test_matched | test_unseen |
|---|---|---|---|---|
| train-on-weather | 10,973 (38.3 h) | 1,353 | 1,363 | 917 |
| train-on-anthro | 7,203 (25.3 h) | 917 | 917 | 1,363 |

## Results (from the reference runs, not regenerated by this refactor)

Final validation SI-SDR, both GPUs, all four within ±0.08 dB — a reproducibility
result in its own right:

| Tag | RTX 3060 | RTX 4060 | Δ |
|---|---|---|---|
| b1_weather | 14.71 | 14.65 | −0.06 |
| b1_anthro | 14.40 | 14.39 | −0.01 |
| b3_weather | 13.74 | 13.82 | +0.08 |
| b3_anthro | 13.17 | 13.14 | −0.03 |

**Claim 1 holds.** SI-SDR gaps of 10.8–12.4 dB, four for four, same sign. The
finding is stronger than "degraded generalization": on unseen noise, output
tracks input SNR almost exactly and PESQ sits within 0.08 of the passthrough
floor. That is total transfer failure, and the per-SNR table is what makes it
unambiguous — the small positive pooled improvement is an aggregation artifact.

**Claim 2 holds.** The direction ratio flips from ~7–8:1 over/under under matched
conditions to ~30–39:1 under/over on unseen, on medians, at every SNR level, in
both architectures. The separation collapses as SNR rises (369× at −15 dB, 6.6×
at +20 dB), so report it conditioned on SNR.

**Gates.** G1 fails as written and should be read as mis-specified — it tests
variation across noise types, while the hypothesis was seen vs unseen. G2 passes
(median gap 0.288, mean 4.46, threshold 0.10). G3 is untestable: direction and
condition are ~99.4% collinear, and the only SNR level with usable overlap is the
one where absolute failures are too small for the threshold to mean anything.

**WER** (faster-whisper large-v3, 818-row negative-SNR subset): clean 1.38%,
noisy 17.47%, b1_matched 16.23%, b1_unseen **21.93%**. Unseen enhancement is 4.5
points worse than doing nothing, while SI-SDR and STOI both report
near-passthrough. That divergence is the clearest empirical instance of the
paper's premise.

**Claim 3 precondition holds.** B1 vs B3 Spearman ρ 0.60–0.99 with top-decile
overlap 8–10× chance at every split×SNR cell: failure is input-determined, not
architecture-specific. The verdict itself (LightGBM vs the registered
two-feature baseline) is the open item.

## Reproducibility

- `config.SEED = 1234` seeds python, numpy and torch in every entry point.
- Crop offsets come from a torch `Generator`, not `np.random`. PyTorch does not
  reseed numpy in DataLoader workers, so the original code drew identical crops
  in every worker when `num_workers > 0`.
- The evaluation path is deterministic: re-running the matrix reproduced SI-SDR
  to 7.1e-15 and STOI to 1.1e-16 across separate runs and module states.
- Checkpoints store optimiser, scaler and RNG state, so a resumed run continues
  the same trajectory.
- `KMP_DUPLICATE_LIB_OK=TRUE` is set in `config.py` above every import. It is
  needed because three OpenMP DLLs from two runtimes coexist in the conda env
  (torch ships Intel's `libiomp5md.dll`; the scipy/pystoi chain pulls LLVM's
  `libomp.dll`, which calls `abort()`). Intel documents the flag as unsafe, so it
  was verified rather than trusted: STOI on 20 files computed in a torch-free and
  a torch-loaded process was bit-identical, max absolute difference 0.0. Keep
  that verification in the paper's environment section — a reviewer who sees the
  flag will ask.
- ASR decoding is pinned to greedy, `temperature=0.0`, all fallback thresholds
  disabled, `condition_on_previous_text=False`. faster-whisper's temperature
  fallback otherwise makes high-noise rows non-reproducible.

## GPU requirements

| Stage | Memory | Time |
|---|---|---|
| B1 training, 20k steps | ~4 GB | 30–34 min (4060), 60 min (3060) |
| B3 training, 20k steps | ~2 GB | 10–15 min |
| Evaluation, 10 cells | ~3 GB | ~85 min with PESQ, ~25 without |
| Labels, 22,754 rows | ~3 GB | ~40 min |
| Features, 22,754 rows | CPU only | ~15 min |
| WER, 818 rows × 4 arms | ~5 GB (int8 large-v3) | ~50–55 min |

B2 (diffusion) does not fit in 12 GB and is deferred.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no manifest.csv under FAILDIR_ROOT=...` | ROOT points at the repo, not the MarVEN folder | point it at the folder containing `manifest.csv`, `noisy/`, `clean/` |
| Kernel dies with no traceback | duplicate OpenMP runtime | already handled in `config.py`; to debug natives, `python -X faulthandler -c "..."` — Jupyter discards the stderr that names the abort |
| Every PESQ column is NaN | `pesq` not installed (no pip wheel) | `conda install -c conda-forge pesq`. The guard report at the end of the matrix tells you; so does the timing — wideband PESQ on 12-second files cannot be free |
| `load_state_dict` size mismatch | loading a B1 checkpoint into B3 or vice versa | `load_model` verifies shapes on a dummy forward pass and fails immediately |
| `*.pt` files that are ~420 bytes | log files named `.pt.txt` sitting in `ckpt/` | `scripts/00_verify_env.py` flags them; rename logs to `.log` so nothing globs them |
| Pickling error from DataLoader | `num_workers > 0` in Jupyter on Windows | keep `workers=0` in the notebook; from a terminal `--workers 4` is fine |
| Edited a module, behaviour unchanged | `importlib.reload` does not reliably rebind module-level constants | restart the kernel; verify with `inspect.getsource`, not by printing the constant |
| WER ~3x higher than expected on the clean arm | hypothesis and reference normalised asymmetrically | already structural: `src/wer.score()` normalises both sides in one place |
| Repeated header rows inside a WER CSV | appended across runs | `read_wer()` strips `row_key == "row_key"` and de-duplicates |
| `pd.to_numeric(errors="ignore")` raises | removed in pandas 3.0 | use `errors="coerce"` (done) |

## Files you must provide

| What | Where from | Where it goes |
|---|---|---|
| MarVEN (22,754 pairs, 79 h) | Zenodo 10.5281/zenodo.20714212 | `FAILDIR_ROOT` |
| LibriSpeech `train-clean-100` transcripts | openslr.org/12 | `FAILDIR_TRANS` (WER stage only) |
| Trained checkpoints | train them, or copy the four `b{1,3}_{weather,anthro}.pt` | `ckpt/` |
| faster-whisper large-v3 | downloaded automatically on first use (~1.5 GB) | HF cache |

None of these are in git. Audio, checkpoints and per-utterance CSVs are
`.gitignore`d; the small summary tables under `results/metrics/` are the ones
worth committing. Nothing in this repo needs Git LFS — if you want the four
checkpoints versioned, LFS is the right home for them (44 MB total as
weights-only exports), but a release asset or Zenodo record is better.

## What changed relative to the original code

Corrections, not methodology changes. Architectures, hyperparameters, the split
design, the metrics and the decomposition are untouched.

1. **Direction-index sign was inverted** in `src/direction.py` relative to every
   reported number, and it also applied clean-energy frame weighting that the
   evaluation harness did not — two different quantities under one name. Unified
   on the evaluation-harness definition, with the weighted version renamed and
   a parametrised sign test in `tests/test_metrics.py`.
2. **Leakage assertion on `clean_source` could never fire** (it holds a
   corpus-level string). Now asserts on the `(speaker_id, chapter_id,
   utterance_id)` tuple, and also checks train/val.
3. **Label↔feature join was positional only.** A change in manifest row order
   would have misaligned targets silently. Both sides now write a `uid` and the
   merge is validated against it.
4. **AUC column names were mislabelled**: `int((1 - 0.90) * 100)` is 9, so the
   top-decile column was named `auc_top9`. Now `round()`.
5. **The `safe_*` metric wrappers hid total failure** — `DO_PESQ=False` silently
   NaN'd 4,560 rows twice. They now count guard rejections, exceptions and
   disabled skips, and report at the end of the run.
6. **`autocast("cuda")` was hardcoded**, so nothing ran or could be tested on a
   CPU-only machine. Now device-aware.
7. **The SI-SDR loss was computed inside autocast.** Moved to fp32: `log10` of a
   ratio of two 64k-sample sums is the fragile part of the objective and fp16
   buys nothing there.
8. **Crop offsets used `np.random`**, which PyTorch does not reseed per worker.
   Now a torch `Generator`.
9. **Two `CKPT` definitions on different drives** (training wrote one, eval
   globbed the other), plus hardcoded `C:\` and `D:\` paths in three files.
   Everything now resolves through `config.py`.
10. **Two incompatible checkpoint formats** — a bare `state_dict` from the
    notebook trainer and a resumable dict from `train.py`. `load_model` accepts
    both; training also writes a portable weights-only export.
11. **`torch.load` defaults to `weights_only=True`** from torch 2.6, which
    rejects the numpy RNG state in the resumable checkpoints. Handled explicitly.
12. **Resume trusted any existing CSV.** A partial file is now detected by row
    count and re-run.
13. **Gate verdicts are computed from the data**, not written into the report
    text, and `configs/gate.yaml` records the sign convention plus the
    disclosure that G1 and G2 were operationalised after Claims 1 and 2 were
    seen.
14. **Added a third Claim 3 arm.** `full` includes `snr`, which is oracle mixing
    metadata rather than something available before enhancement, so reporting it
    alone would invite exactly one reviewer question. `feats_only` drops it and
    is the genuinely pre-hoc arm. Within an SNR stratum `snr` is constant, so the
    within-SNR margins are unaffected either way.
15. **Dropped `models/` and `splits.py`.** The package diverged on state-dict
    prefixes (an `STFTWrapper` added a `net.` prefix, `out` was a bare `Linear`
    without the sigmoid, an extra `window` buffer was registered) and would load
    wrong; `splits.py` used column names that do not exist in the manifest and
    leaked speakers and utterances.

## Limitations

- **Sampled design.** Every clean utterance appears in exactly two rows with two
  different noise types, so no utterance exists across all five conditions or all
  eight SNR levels. The direction index cannot be compared within-utterance
  across conditions and must be aggregated across the corpus. Structural;
  disclose it.
- **Recording-identity confound.** Untouched, and the sharpest open question.
  Given that Claim 1 turned out to be total transfer failure, a reviewer will ask
  whether the models learned noise-family spectral fingerprints rather than
  speech structure.
- **Direction/condition collinearity.** Blocks G3 and scopes Claim 3 to
  within-condition magnitude.
- **Pooling masks real effects.** Pooled WER and pooled Spearman both produced
  misleading readings. Every table in `results/metrics/` is conditioned on split,
  SNR, or noise type for that reason. Within a condition, `frac_pos` and `snr`
  are indistinguishable — the apparent advantage of frame-level features came
  entirely from reordering conditions.
- **Damaging regime is noise-type-determined, not SNR-determined.** Hurricane and
  bubble_curtain sit at the clean ASR floor even at −15 dB broadband SNR
  (hurricane's energy is out of band, bubble_curtain is bursty). "SNR ≤ −5" is
  the wrong cut; `--damaging-only` uses rainfall, large_commercial_ship and
  lightning instead, and the reduced training-row count is a stated limitation.
- **Pre-hoc constraint.** The predictor is reference-free *at inference*, but
  clean references are needed *during training* to construct the labels. State
  this explicitly to pre-empt a misreading.
- **B2 deferred.** Diffusion needs cloud compute.
- **Open item.** The clean-arm WER shift (3.07% → 1.38% on identical rows) is
  explained by the normalisation asymmetry, but the hypothesis-side pipeline
  change that introduced it has not been traced.

## Citation

```bibtex
@misc{faildir2026,
  title  = {Failure direction in speech enhancement: pre-hoc, reference-free
            prediction of over- and under-suppression},
  author = {Rana Rishith},
  year   = {2026},
  note   = {https://github.com/rana-rishith/failure-direction}
}
```

MarVEN:

```bibtex
@dataset{marven,
  title     = {MarVEN: Marine Vessel and Environmental Noise speech corpus},
  doi       = {10.5281/zenodo.20714212},
  publisher = {Zenodo}
}
```
