# Usage

Installing, configuring and running everything in this
repository. The short overview is in the top-level
[README](../README.md).

## Requirements

Python 3.12. You don't need a GPU; everything runs on CPU, training just takes
longer. The reference runs used an RTX 4060 Laptop (8.6 GB, Ada sm_89) and an
RTX 3060 (12 GB, Ampere sm_86) on CUDA 12.4.

```
numpy pandas scipy soundfile torch pystoi PyYAML
lightgbm scikit-learn               # Claim 3
jiwer faster-whisper transformers   # WER stage
pytest ipykernel
pesq                                # conda-forge ONLY
```

`requirements.txt` leaves out PESQ on purpose. Windows + Python 3.12 has no pip
wheel for it, so pip tries to compile it and fails without MSVC. Get it from
conda-forge:

```bash
conda install -c conda-forge pesq
```

Install LightGBM from conda-forge too. Its pip wheel ships an OpenMP runtime
that clashes with the one torch and pystoi load.

Without `pesq` you lose the PESQ columns and nothing else. The guard in
`src/metrics.py` prints a warning instead of filling the column with NaN.

## Installation

The conda env and the environment variables keep the old short name, `faildir`
and `FAILDIR_*`. Only the project name changed.

```bash
conda env create -f environment.yml
conda activate faildir
pip install torch --index-url https://download.pytorch.org/whl/cu124   # match your CUDA
python -m ipykernel install --user --name faildir --display-name faildir
python scripts/00_verify_env.py
```

When something behaves oddly, check these two first:

```bash
python -c "import sys; print(sys.executable)"   # must contain envs/faildir
python -m pytest                                # bare pytest can pick up the base Python
```

## Dataset

**MarVEN**, Zenodo DOI [10.5281/zenodo.20714212](https://doi.org/10.5281/zenodo.20714212).
22,754 paired clean/noisy recordings, 79.0 hours at 16 kHz, built from 11,377
LibriSpeech `train-clean-100` utterances by 100 speakers. This repo does not
include it; download it from Zenodo.

| Noise type | Family | Rows | Source recording |
|---|---|---|---|
| rainfall | weather | 4,587 | 11.05 s |
| lightning | weather | 4,583 | 7.57 s |
| hurricane | weather | 4,519 | ~29–30 s |
| bubble_curtain | anthropogenic | 4,570 | ~29–30 s |
| large_commercial_ship | anthropogenic | 4,495 | 10.01 s |

Eight SNR levels from −15 to +20 dB in 5 dB steps, about 2,800 rows each. A
bubble curtain is a noise-mitigation device used in offshore construction, so
it goes with the ship under "anthropogenic". The split is weather vs
anthropogenic, and only one of the two anthropogenic types is a vessel.

Two properties of the data matter for every result below.

**Each noise type comes from one short recording.** Autocorrelation shows that
three of the five loop. You cannot separate noise type from recording identity
in this dataset, which limits what Claim 1 can say.

**About 6% of the clean files carry a large DC offset**, up to 97% of their
signal power. You can't hear it, but it inflates any energy measure that counts
the 0 Hz bin. The energy decomposition drops everything below 60 Hz for this
reason (item 16 under What changed).

Point `ROOT` at the folder that holds `manifest.csv`, `noisy/` and `clean/`.
Pointing it at the repo root is the most common setup mistake.

The WER stage also needs the LibriSpeech `train-clean-100` transcripts
(`*.trans.txt`). MarVEN's clean audio is `train-clean-100` scaled by
`1/mix_scale` with the content bit-identical, so the pipeline scores true WER
against the original transcripts.

### No data? Build a synthetic stand-in

```bash
python scripts/make_synthetic_dataset.py --out data/MarVEN_synth
```

This writes 240 rows of 1.5 s each with MarVEN's structure: a speaker-disjoint
80/10/10 `split` column, all five noise types in every split, each utterance in
two rows, eight SNR levels and LibriSpeech-style transcripts. The numbers it
produces mean nothing. Use it to check that the pipeline runs end to end on a
machine without the 79-hour corpus.

## Configuration

`config.py` holds every setting, and environment variables override every path,
so the repo contains no machine-specific paths.

| Variable | Meaning | Default |
|---|---|---|
| `FAILDIR_ROOT` | MarVEN root (the folder with `manifest.csv`) | `<repo>/data/MarVEN` |
| `FAILDIR_CKPT` | checkpoints | `<repo>/ckpt` |
| `FAILDIR_EVAL` | results | `<repo>/results` |
| `FAILDIR_TRANS` | LibriSpeech `train-clean-100` | `<repo>/data/LibriSpeech/train-clean-100` |
| `FAILDIR_DEVICE` | force `cuda` or `cpu` | auto |

`config.DECOMP_MIN_HZ = 60.0` sets the lowest frequency the energy
decomposition counts.

```bash
# Windows PowerShell
$env:FAILDIR_ROOT = "D:\data\MarVEN"
# Windows cmd
set FAILDIR_ROOT=D:\data\MarVEN
# bash
export FAILDIR_ROOT=/path/to/MarVEN
```

`config.py` reads these once, at import. Set them before the first import. In a
notebook, restart the kernel after changing one. If an old `FAILDIR_ROOT` sits
in your Windows system variables, it beats the default; override it per session
with `$env:` or `os.environ[...] = ...`. `setdefault` won't work, because the
variable already exists.

### If the test suite dies with a Windows fatal exception

On some Windows conda installs MKL's threaded layer cannot delay-load its
OpenMP DLL, and the process dies with `Windows fatal exception: code
0xc06d007f` on the first BLAS call. It looks like a crash in whatever code
happens to reach `numpy.dot` first, so it reads as a bug in this repo and is
not one: a bare `python -c "import numpy as np; a=np.random.rand(10); a@a"`
dies the same way. Force the sequential layer:

```bash
# Windows PowerShell
$env:MKL_THREADING_LAYER="SEQUENTIAL"
# bash
export MKL_THREADING_LAYER=SEQUENTIAL
```

`config.py` already sets `KMP_DUPLICATE_LIB_OK` for the related duplicate-OpenMP
problem, but this one is deliberately left to the environment: the threading
layer changes the order BLAS accumulates in, and pinning it repo-wide would
alter numbers in a way that belongs to a decision, not a default.

## How to run

```
environment  ->  data  ->  folds  ->  training  ->  evaluation  ->  claims/gates
                                                        |
                                                        +->  WER
                                                        +->  LOTO confound
                                                        +->  labels -> features -> Claim 3
```

One command:

```bash
python scripts/run_pipeline.py                 # full protocol
python scripts/run_pipeline.py --smoke         # 40 steps per run, checks the wiring
python scripts/run_pipeline.py --from evaluate # resume at a later stage
python scripts/run_pipeline.py --with-wer      # include the ASR stage
```

Or one stage at a time:

```bash
python scripts/00_verify_env.py
python scripts/01_verify_data.py --sample 300

python -m src.train --model b1 --fold weather --steps 20000
python -m src.train --model b1 --fold anthro  --steps 20000
python -m src.train --model b3 --fold weather --steps 20000
python -m src.train --model b3 --fold anthro  --steps 20000

python -m src.evaluate                  # 10 cells, ~85 min with PESQ, ~25 without
python -m src.analysis                  # Claims 1 and 2, gates G1-G3

python -m src.confound --model b3       # LOTO over 3 held-out weather types; trains if no checkpoint
python -m src.confound --model b1
python -m src.confound --model b3 --report   # score saved CSVs only
python -m src.confound --smoke          # 500 steps, 40 test rows, rainfall

python -m src.wer --snr-max -5          # ~50-55 min, 818 rows
python -m src.wer --engine stub --limit 24   # pipeline smoke test, no ASR model needed

python -m src.claim3 --precondition     # B1-vs-B3 rank agreement
python -m src.labels                    # ~40 min, 22,754 rows
python -m src.features                  # ~15 min, CPU-bound
python -m src.claim3 --fold weather
python -m src.claim3 --fold weather --damaging-only

python claim2_check.py                  # Claim 2 tables on the corrected energies
python claim2_by_type.py
python claim2_loto.py
```

You can re-run any stage safely. Training picks up from the last atomic
checkpoint when you repeat the same command. `src.confound` finds an existing
LOTO checkpoint and re-evaluates without retraining. The evaluation, label and
feature stages skip a CSV whose row count matches its fold and re-run one that
falls short, so a half-written file gets redone.

The row-count check won't catch a complete file with outdated values, such as
energies from before the DC fix. Move those files aside yourself before
re-running.

Run long jobs from a terminal. If a Jupyter kernel disconnects, the job dies
with it; a terminal process keeps going.

### Notebook

`notebooks/main.ipynb` has 17 stage cells:

| Cell | Stage |
|---|---|
| 1 | imports and path bootstrap (**the only cell to re-run after a kernel restart**) |
| 2 | configuration, seeds, device |
| 3 | environment and dependency checks |
| 4 | dataset setup and disk check |
| 5 | data inspection (why the shipped split cannot be used) |
| 6 | preprocessing |
| 7 | cross-condition folds and leakage assertions |
| 8 | model definitions |
| 9 | checkpoint loading and integrity |
| 10 | training configuration and loss sanity |
| 11 | training |
| 12 | validation |
| 13 | evaluation matrix |
| 14 | metrics: Claims 1, 2 and the gates |
| 15 | WER |
| 16 | Claim 3: labels, features, verdict |
| 17 | results and final verification |

The notebook calls into `src/` and nothing else, so it stays in sync with the
command line. `python scripts/build_notebook.py` regenerates it. Run the cells
in order; running them out of order caused most of the early bugs. Cell 1
stands on its own, so after a kernel restart you re-run one cell.

## Training protocol

`N_FFT=512`, `HOP=128`, `SR=16000`, 4-second random crops, batch size 8,
AdamW at 2e-4, SI-SDR loss, 20,000 gradient steps. Validation runs every 2,000
steps on the first 200 rows of the val split.

| ID | Model | Params |
|---|---|---|
| B1 | SpectralMask, non-causal 2-layer BLSTM, h=256 | 2,763,521 |
| B2 | SGMSE-style diffusion | deferred, needs a cloud GPU |
| B3 | CausalMask, 2-layer causal GRU, h=128 | 280,833 |
| B4 | Passthrough, identity | no training |

Every baseline, both folds and all six LOTO runs get the same number of steps.
Equal compute here means equal gradient steps. Weather has 38.3 h of training
audio and anthropogenic has 25.3 h, so counting epochs would give the weather
fold about 50% more updates and break the comparison.

## Evaluation

Ten cells: B1 and B3 on both folds and both splits, plus two for B4. Passthrough
has no weights, so its numbers come out the same under either fold label.
`batch_size=1`, full-length audio, no cropping.

Weather's `test_matched` holds the same rows as anthro's `test_unseen`, and the
other way round. Pool both folds and the matched and unseen sets contain the
same 2,280 utterances. The only difference is whether the model had trained on
that noise family. That makes every matched-vs-unseen comparison paired, and
you can check it: `e_clean` comes out identical for the two pooled splits.

The energy decomposition compares the clean magnitude with `Yh = M * X`, the
magnitude the mask predicts. It does not use the STFT of the reconstructed
waveform. So the decomposition measures what the mask tried to do, while SI-SDR
and STOI measure what came out. It skips bins below 60 Hz (bins 0 and 1 at
`N_FFT=512`). The older all-bin values sit in `e_over_full`, `e_under_full`,
`e_clean_full` and `e_noisy_full`.

## The probe tool

`src/probe/` packages the failure-direction metric as one function so that an
enhancer trained anywhere can be scored on the same frozen split. It is a
wrapper, not a reimplementation: `_ratios`, the level-aligned gain clamp and the
bin floor are imported from `src/diverse.py`, which produced the numbers in
`results/`. There is one definition of the energy split in this repo.

Nothing extra to install. It needs the same `faildir` environment as the rest
of the repo, and `FAILDIR_ROOT` and `FAILDIR_CKPT` must both be set before the
first import. Leaving `FAILDIR_CKPT` unset silently picks up whatever is already
in the environment, which is the easiest way to score the wrong weights.

```python
from src.probe import probe

# enhance_fn: np.ndarray (T,) float32 noisy -> np.ndarray (T,) enhanced
rep = probe(enhance_fn, split="marven_test_v1", heard_types=("rainfall", "lightning", "hurricane"))
rep["rows"]      # per-utterance DataFrame
rep["summary"]   # medians with 95% bootstrap CIs per noise type x SNR band
```

For an enhancer that cannot run in this process (SGMSE+ has its own conda env),
score a directory of enhanced wavs named by `uid` instead:

```python
rep = probe(wav_dir="out/sgmse", tag="sgmse")
```

From the command line:

```
python -m src.probe --freeze-split
python -m src.probe --model b1_weather --out results/probe/b1_weather/
python -m src.probe --wav-dir out/sgmse --tag sgmse --out results/probe/sgmse/
python -m src.probe.rescore                    # every tag in the reference CSV
```

### The frozen split

`marven_test_v1` is the 2,280 manifest rows with `split == "test"`, pinned in
`configs/splits/marven_test_v1.json` with a SHA256 over the sorted uid list.
MarVEN ships pre-mixed, so there are no noise offsets, SNRs or gains to record:
the uid list *is* the split, and `load_split()` recomputes the checksum on every
call and refuses to run if the manifest has moved underneath it.

Every tag in `results/xcorpus/eval/marven.csv` reproduces through `probe()` to a
worst relative difference of 8.2e-13, which is float64 round-off.

### Output columns

Ratios are energy relative to the clean utterance, on the output-STFT basis (the
gate uses the output STFT for every model, so mask-intent columns are not
reproduced here).

| column | meaning |
| --- | --- |
| `r_over` | clean energy destroyed |
| `r_under` | noise energy retained |
| `r_add` | energy added beyond the noisy input; 0 by construction for a bounded mask |
| `r_over_b4`, `r_under_b4` | the same two for passthrough on that utterance (the floor) |
| `r_over_x` | `r_over` minus the passthrough floor: speech destroyed in excess of phase cancellation |
| `d` | `(r_over - r_under) / (r_over + r_under)`; positive is over-suppression |
| `nr` | `1 - r_under / r_under_b4`: the fraction of the noise excess removed |
| `g` | level of the clean component in the output |
| `delta_d` | `d` minus `d` of the oracle Wiener mask on the same utterance |
| `sisdr_in`, `sisdr_out`, `sisdr_gain` | SI-SDR, and `sisdr_lc_*` / `sisdr_hp100_*` with the sub-62.5 Hz and sub-100 Hz bands removed |

Each `_g` suffix is the level-aligned basis: the output divided by `g` before the
split, so a model that merely changed level is not charged for over-suppression.
Each `_hp100` suffix is the same quantity computed from 100 Hz up instead of
62.5 Hz. The unsuffixed 62.5 Hz columns are the registered basis behind
`configs/gate_universal.yaml`; `_hp100` is reported **alongside** them and never
replaces them.

`class` and `class_hp100` apply the `U1_failure_class` thresholds from
`configs/gate_universal.yaml` (commit `29c1566`) unchanged: `inert` at
`nr < 0.30` with `r_over_x` below its R1 reference, `over` at `r_over_x` at or
above it, `hallucinate` at `r_add >= 0.05`. A cell can carry more than one, and
no class is a failure. `active_balanced` marks a cell matching none of the three;
that label is the tool's own and has no gate behind it. The classes are
R4-versus-R1 contrasts, so they need `heard_types`; without it the class columns
read `unknown`.

Confidence intervals are 95% percentile bootstrap of the median, 2,000
resamples, resampling **base utterances** rather than rows: a clean utterance can
appear under more than one noise type, so resampling rows would treat one
utterance as several independent draws and report intervals that are too narrow.

Measured, the clustering is weak: 1.03 rows per base utterance in a
`noise_type` x `snr_band` cell and 1.29 in the pooled rows, so on this split the
two bootstraps agree to within about 5%, scattered both ways. The clustered one
is used because it is the correct one, not because it changes a reading.

### Two limits of the reported columns

**`nr_hp100` has a degenerate denominator.** `nr` is `1 - r_under / r_under_b4`,
and for a noise type whose energy is almost entirely below 100 Hz there is
nearly no noise left above 100 Hz to remove. Measured on SGMSE+, hurricane at
SNR > 0: `r_under_b4` is 1.7e-3 full-band but 1.4e-5 in the 100 Hz band, and
single-utterance `nr_g_hp100` reaches -295. Read `nr_hp100` only together with
`r_under_b4_hp100`, which is in the per-utterance CSV for exactly this reason.
`d_hp100` is unaffected: it is a normalised difference and stays in [-1, 1].
This is the concrete reason the 62.5 Hz columns remain primary and hp100 is
reported beside them.

**The gate classes are undefined for a zero-shot model.** `inert` and `over`
compare `r_over_x` at R4 against its R1 reference, so they need rows from the
same model on noise it was trained on. A model that never saw MarVEN -- SGMSE+,
DFN3, and every candidate in a zero-shot sweep -- has no R1 rows on this split,
and `probe()` reports `class = unknown` rather than guessing a substitute
reference. Classing such a model needs a registered decision about what plays
the part of R1; `hallucinate`, which is an absolute `r_add` threshold, still
applies.

Each MarVEN noise type is a single looped recording. Results on this split
describe those five recordings, not the noise types in general.

## Expected outputs

```
ckpt/
  b1_weather.pt        weights-only export (11.1 MB, 18 tensors)
  b1_weather_best.pt   resumable: weights + optimiser + scaler + RNG (~33 MB)
  b1_weather_last.pt
  ... x4 tags, plus b{1,3}_loto_{rainfall,lightning,hurricane}
results/
  eval/        <tag>__<fold>__<split>.csv     per-utterance, 4,560 rows total
  labels/      b1__<fold>__<split>.csv        22,754 rows
  features/    <fold>__<split>.csv            22,754 rows, 33 features
  confound/    <model>_loto_<type>__loto-<type>__<split>.csv
               loto_summary__<model>.csv  loto_per_snr__<model>.csv
  claim3/      <fold>.txt  <fold>_damaging.txt     verdict printouts
  claim3_logs/ <model>_<fold>.txt  precondition.txt
  metrics/     claim1_*.csv claim2_*.csv gate_*.csv claim3_*.csv
               eval_matrix.csv fold_report.csv wer_*.csv gate_results.yaml
  claim2_*_dc_fixed.txt  confound_<model>_dc_fixed.txt
```

Fold sizes to check against:

| Fold | train | val | test_matched | test_unseen |
|---|---|---|---|---|
| train-on-weather | 10,973 (38.3 h) | 1,353 | 1,363 | 917 |
| train-on-anthro | 7,203 (25.3 h) | 917 | 917 | 1,363 |

## Reproducibility

- `config.SEED = 1234` seeds python, numpy and torch in every entry point.
- Crop offsets come from a torch `Generator`. The original code used
  `np.random`, which PyTorch doesn't reseed in DataLoader workers, so every
  worker drew the same crops when `num_workers > 0`.
- Evaluation is deterministic. Re-running the matrix reproduced SI-SDR to
  7.1e-15 and STOI to 1.1e-16. The LOTO re-evaluation after the DC fix gave the
  same R values to the last digit.
- Checkpoints store optimiser, scaler and RNG state, so a resumed run follows
  the same trajectory as an uninterrupted one.
- `config.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` above every import. The conda env
  holds three OpenMP DLLs from two runtimes: torch ships Intel's
  `libiomp5md.dll`, and the scipy/pystoi chain pulls LLVM's `libomp.dll`, which
  calls `abort()` when it finds the other one. Intel calls this flag unsafe, so
  we tested it: STOI on 20 files came out bit-identical in a torch-free process
  and a torch-loaded one (max absolute difference 0.0).
- ASR decoding uses greedy search, `temperature=0.0`, every fallback threshold
  off and `condition_on_previous_text=False`. With faster-whisper's temperature
  fallback on, high-noise rows change from run to run.

## GPU requirements

| Stage | Memory | Time |
|---|---|---|
| B1 training, 20k steps | ~4 GB | 30–34 min (4060), 60 min (3060) |
| B3 training, 20k steps | ~2 GB | 10–15 min |
| Evaluation, 10 cells | ~3 GB | ~85 min with PESQ, ~25 without |
| LOTO, 3 held-out types per model | as training | ~2.5 h for all six from scratch |
| Labels, 22,754 rows | ~3 GB | ~40 min |
| Features, 22,754 rows | CPU only | ~15 min |
| WER, 818 rows × 4 arms | ~5 GB (int8 large-v3) | ~50–55 min |

B2 (diffusion) needs more than 12 GB, so it waits for cloud compute.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no manifest.csv under FAILDIR_ROOT=...` | ROOT points at the repo, or an old system-level variable wins | point it at the folder with `manifest.csv`, `noisy/`, `clean/`; set it with `$env:` or `os.environ[...]`, then restart the kernel |
| Kernel dies with no traceback | two OpenMP runtimes loaded | `config.py` handles this; to see the native error, run `python -X faulthandler -c "..."` from a terminal, because Jupyter swallows the message |
| Every PESQ column is NaN | `pesq` missing (no pip wheel) | `conda install -c conda-forge pesq`. The guard report at the end of the matrix says so, and the run finishes suspiciously fast: wideband PESQ on 12-second files takes real time |
| `r_over` far above the tables here | CSVs from before the DC fix | look for `e_over_full` columns; if they're missing, move the CSVs aside and re-run |
| `load_state_dict` size mismatch | B1 checkpoint loaded into B3, or the reverse | `load_model` checks shapes on a dummy forward pass and stops right away |
| `*.pt` files of ~420 bytes | log files named `.pt.txt` in `ckpt/` | `scripts/00_verify_env.py` flags them; rename logs to `.log` so no glob picks them up |
| Pickling error from DataLoader | `num_workers > 0` in Jupyter on Windows | keep `workers=0` in the notebook; `--workers 4` works from a terminal |
| Edited a module, nothing changed | `importlib.reload` doesn't reliably rebind module-level constants | restart the kernel; check with `inspect.getsource`, not by printing the constant |
| Clean-arm WER ~3x too high | hypothesis and reference normalised differently | `src/wer.score()` now normalises both sides in one place |
| Repeated header rows inside a WER CSV | appends across runs | `read_wer()` strips `row_key == "row_key"` rows and de-duplicates |
| `pd.to_numeric(errors="ignore")` raises | pandas 3.0 removed it | use `errors="coerce"` (done) |

## Files you must provide

| What | Where from | Where it goes |
|---|---|---|
| MarVEN (22,754 pairs, 79 h) | Zenodo 10.5281/zenodo.20714212 | `FAILDIR_ROOT` |
| LibriSpeech `train-clean-100` transcripts | openslr.org/12 | `FAILDIR_TRANS` (WER stage only) |
| Trained checkpoints | train them, or copy the four `b{1,3}_{weather,anthro}.pt` | `ckpt/` |
| faster-whisper large-v3 | downloads on first use (~1.5 GB) | HF cache |

Git holds none of these. `.gitignore` excludes audio, checkpoints and the large
per-utterance CSVs in `eval/`, `labels/` and `features/`. The repo does track
the summary tables in `results/metrics/`, the Claim 3 verdicts and logs, the
LOTO outputs in `results/confound/` and the `*_dc_fixed.txt` reports. You don't
need Git LFS. LFS could hold the four checkpoints (44 MB as weights-only
exports), though a GitHub release or a Zenodo record suits them better.
