# failure-direction: predicting which way speech enhancement fails

Do speech enhancement models fail in predictable ways? And can you see the
failure coming from the noisy input alone, before the enhancer runs?

This project splits enhancement failure into two modes that a single quality
score lumps together:

| Mode | What the mask does | Consequence |
|---|---|---|
| **Over-suppression** | pushes speech-band energy below the clean reference | speech is gone and cannot be recovered |
| **Under-suppression** | stays near 1 in noise-dominated bins | noise remains, speech survives, ASR and later stages can still use it |

The two cost different things downstream. SI-SDR and STOI report one number
and cannot tell you which mode you got.

## Claims

1. **Cross-condition generalization gap.** Models do much worse on unseen noise
   than on matched noise. In MarVEN, "unseen" means an unseen noise
   *recording*. The LOTO test below shows the data cannot support a claim about
   unseen noise *families*.
2. **Failure-direction flip.** Over-suppression dominates on matched noise.
   Under-suppression dominates on unseen noise.
3. **Pre-hoc prediction.** Cheap, reference-free features computed on the noisy
   input predict how much speech a model will destroy in each utterance. The
   predictor has to beat a pre-registered baseline (oracle SNR + `log(e_noisy)`)
   inside each SNR stratum.

Claim 3 predicts **over-suppression magnitude (`r_over`) within a condition**.
It does not predict direction. Direction and condition line up in ~99.4% of
utterances, so a direction classifier would learn to recognise the noise family
from its spectrum and tell you nothing about failure.

## Project structure

```
failure-direction/
├── README.md
├── requirements.txt            pip deps (PESQ left out on purpose, see below)
├── environment.yml             conda env, Python 3.12
├── .gitignore
├── config.py                   all paths, constants, device and seeds live here
├── env.ps1                     sets the FAILDIR_* variables for a PowerShell session
├── configs/
│   └── gate.yaml               pre-committed gate and LOTO thresholds, sign convention
├── src/
│   ├── data.py                 manifest, cross-condition folds, leakage guards, dataset
│   ├── models.py               B1/B3/B4, STFT helpers, checkpoint I/O
│   ├── metrics.py              SI-SDR, guarded STOI/PESQ, energy decomposition (no DC)
│   ├── train.py                crash-resumable trainer
│   ├── evaluate.py             the 10-cell evaluation matrix
│   ├── analysis.py             Claims 1 and 2, gates G1-G3
│   ├── confound.py             leave-one-type-out (LOTO) recording-identity test
│   ├── labels.py               Claim 3 targets (B1 energy decomposition)
│   ├── features.py             33 reference-free input features
│   ├── claim3.py               LightGBM verdict against the registered baseline
│   └── wer.py                  ASR pipeline, four arms, aggregation
├── claim2_check.py             Claim 2 direction ratios on the DC-fixed eval matrix
├── claim2_by_type.py           Claim 2 per noise type, cross-family
├── claim2_loto.py              Claim 2 per held-out recording, LOTO
├── scripts/
│   ├── 00_verify_env.py        environment and checkpoint integrity
│   ├── 01_verify_data.py       manifest, disk, folds, leakage, distributions
│   ├── run_pipeline.py         the whole pipeline in one command
│   ├── make_synthetic_dataset.py   tiny MarVEN-shaped corpus for smoke tests
│   └── build_notebook.py       regenerates notebooks/main.ipynb
├── notebooks/
│   └── main.ipynb              17 stage cells, thin driver over src/
├── tests/                      36 tests: folds, leakage, sign convention, joins
├── results/                    generated (see Expected outputs)
└── ckpt/                       generated checkpoints
```

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

## Results

The energy-based numbers (`e_over`, `e_under`, `r_over`, `r_under`, `dir_idx`)
come from the DC-fixed rerun on 7 October 2026. The fix does not touch SI-SDR,
STOI or PESQ.

### Training reproducibility

Final validation SI-SDR on two GPUs. All four tags agree within ±0.08 dB, and a
later retrain on the 4060 landed within ±0.10 dB of these.

| Tag | RTX 3060 | RTX 4060 | Δ |
|---|---|---|---|
| b1_weather | 14.71 | 14.65 | −0.06 |
| b1_anthro | 14.40 | 14.39 | −0.01 |
| b3_weather | 13.74 | 13.82 | +0.08 |
| b3_anthro | 13.17 | 13.14 | −0.03 |

### Evaluation matrix

| Model | Fold | Split | SI-SDR out | STOI out | PESQ out |
|---|---|---|---|---|---|
| B1 | anthro | test_matched | 15.435 | 0.899 | 2.696 |
| B1 | anthro | test_unseen | 2.962 | 0.813 | 1.819 |
| B1 | weather | test_matched | 15.031 | 0.877 | 2.610 |
| B1 | weather | test_unseen | 3.321 | 0.809 | 1.763 |
| B3 | anthro | test_matched | 14.115 | 0.876 | 2.486 |
| B3 | anthro | test_unseen | 2.983 | 0.813 | 1.832 |
| B3 | weather | test_matched | 13.945 | 0.855 | 2.461 |
| B3 | weather | test_unseen | 3.255 | 0.808 | 1.747 |
| B4 | weather | test_matched | 2.697 | 0.807 | 1.757 |
| B4 | weather | test_unseen | 2.815 | 0.802 | 1.725 |

No NaN in any PESQ or STOI column. Even passthrough shows nonzero `e_over`
(1,411.7 matched, 1,285.2 unseen), because noise cancels speech in some bins
through phase. Read each trained model's `e_over` against that floor.

### Claim 1 holds, at the recording level

The SI-SDR gap between matched and unseen runs from 10.7 to 12.5 dB, with the
same sign in all four model/fold pairs. On unseen noise, output SI-SDR follows
input SNR closely and PESQ lands within 0.1 of passthrough. The models do
nothing useful. The small positive improvement in the pooled mean comes from
averaging across SNR levels and vanishes once you split by SNR.

**LOTO confound test.** Each run trains on two weather types and tests on the
third. R is held-out SI-SDR improvement divided by matched improvement (median
within each SNR stratum, then averaged). `configs/gate.yaml` fixed the
thresholds before any run: R ≥ 0.5 means family-level generalization, R ≤ 0.2
means recording-level failure.

| Held out | B3 R | B1 R |
|---|---|---|
| rainfall | 0.059 | 0.089 |
| lightning | −0.016 | −0.002 |
| hurricane | −0.006 | −0.003 |

A model trained on two weather recordings learns close to nothing that helps on
a third. On held-out rainfall at −15 dB, both models score below passthrough:
−4.16 dB for B3 and −1.36 dB for B1. So Claim 1 reads "models fail on an unseen
noise recording". This dataset can't support the family-level version.

### Claim 2 holds

Median direction ratios, pooled across folds:

| | Matched | Unseen |
|---|---|---|
| B1 | over-dominant, 5.9:1 | under-dominant, 38:1 |
| B3 | over-dominant, 5.0:1 | under-dominant, 28:1 |

The flip shows up at all eight SNR levels on both architectures. At −15 dB the
matched and unseen splits sit 794× apart on `r_under` and 6.2× on `r_over`; at
+20 dB the gaps shrink to 5.7× and 1.27×. Report it per SNR level, since a
pooled number averages those very different gaps.

Across held-out recordings within weather, the amount of speech the mask
destroys varies by recording. Held-out ÷ matched `r_over`, averaged over −15 to
0 dB:

| Held out | B1 | B3 | Mask |
|---|---|---|---|
| hurricane | 0.01 | 0.01 | inert |
| lightning | 0.97 | 0.86 | active, near matched level |
| rainfall | 2.28 | 5.24 | over-active |

Both architectures order them the same way: hurricane, then lightning, then
rainfall.

### Claim 3 passes on all four runs

The rule, fixed in advance: `full` beats the oracle baseline (SNR +
`log e_noisy`) only if its within-SNR Spearman is higher in a clear majority of
the 8 SNR strata **and** inside each noise type on its own.

| Run | SNR strata won | Per noise type | Mean margin, full / feats_only | AUC top-10% margin |
|---|---|---|---|---|
| B1 weather | 8/8 | hurricane 8/8, lightning 8/8, rainfall 8/8 | +0.647 / +0.605 | +0.040 |
| B1 anthro | 8/8 | bubble_curtain 8/8, ship 8/8 | +0.445 / +0.414 | +0.007 |
| B3 weather | 8/8 | hurricane 7/8, lightning 8/8, rainfall 8/8 | +0.648 / +0.619 | +0.045 |
| B3 anthro | 8/8 | bubble_curtain 7/8, ship 8/8 | +0.452 / +0.402 | +0.011 |

The predictor lost two strata: hurricane at +20 dB (B3 weather) and
bubble_curtain at −15 dB (B3 anthro). `feats_only` drops oracle SNR, which makes
it the strictly pre-hoc arm, and it wins on its own.

A win over the baseline doesn't make the predictor useful in every stratum. For
hurricane at +15 and +20 dB both arms score near zero, and B3 weather rainfall
is weak at −15, −10 and +10 dB. Those strata pass because the baseline does even
worse there.

**Precondition.** B1 and B3 agree on which utterances fail worst (Spearman
0.60–0.99 in every split × SNR cell, top-decile overlap well above chance). A
2.8M-parameter BLSTM and a 280K-parameter GRU flag the same files, so the input
drives the failure. A segment-position check (η² 0.06–0.11 against ~0.07 by
chance) shows the predictor isn't just recognising which stretch of the looped
noise recording it hears.

### WER

faster-whisper large-v3 on the 818 negative-SNR rows: clean 1.38%, noisy
17.47%, b1_matched 16.23%, b1_unseen **21.93%**. On unseen noise, enhancement
makes ASR 4.5 points worse than leaving the audio alone, while SI-SDR and STOI
call the output roughly as good as passthrough. WER never reads the energy
decomposition, so the DC fix leaves these numbers as they were.

### Gates (pre-DC, not yet recomputed)

G1 fails as written. It asks whether direction varies across the five noise
types, but the hypothesis was about seen vs unseen, so the gate tests the wrong
axis. G2 passed on the pre-fix energies (median gap 0.288, threshold 0.10). G3
can't be tested: direction and condition overlap in ~99.4% of utterances, and
the one SNR level with enough overlap (+20 dB) has failures too small for the
threshold to mean anything. G1 and G2 both read the energy decomposition, so
both need a rerun on the corrected energies.

### Withdrawn

An earlier result claimed B3 destroys ~40% of clean speech energy in a few
concentrated bins while SI-SDR and STOI look fine. Those files turned out to be
DC-heavy, and the mask was removing an offset nobody could hear. That result
and the mechanism built on it are withdrawn.

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

## What changed relative to the original code

These are bug fixes. The architectures, hyperparameters, split design and
metrics stay as they were.

1. **The direction-index sign was flipped** in `src/direction.py` relative to
   every reported number. That file also weighted frames by clean energy, which
   the evaluation harness did not, so one name covered two quantities. The code
   now uses the harness definition, the weighted version has its own name, and
   `tests/test_metrics.py` checks the sign.
2. **The leakage assertion on `clean_source` could never fire**, because that
   column holds one corpus-level string. It now checks the `(speaker_id,
   chapter_id, utterance_id)` tuple and covers train/val as well.
3. **Labels and features were joined by position.** Reordering the manifest
   would have misaligned targets without any error. Both sides now write a
   `uid`, and the merge checks it.
4. **AUC columns had the wrong names.** `int((1 - 0.90) * 100)` gives 9, so the
   top-decile column came out as `auc_top9`. The code now uses `round()`.
5. **The `safe_*` metric wrappers hid total failure.** With `DO_PESQ=False` they
   returned NaN for all 4,560 rows, twice, with no warning. They now count
   guard rejections, exceptions and skips, and print the counts at the end.
6. **`autocast("cuda")` was hardcoded**, so nothing ran on a CPU-only machine.
   It now follows the device.
7. **The SI-SDR loss ran inside autocast.** It now runs in fp32. Taking `log10`
   of a ratio of two 64k-sample sums is the fragile step, and fp16 gains nothing
   there.
8. **Crop offsets used `np.random`**, which PyTorch doesn't reseed per worker.
   They now come from a torch `Generator`.
9. **`CKPT` was defined twice, on different drives.** Training wrote to one and
   evaluation read from the other. Three files also hardcoded `C:\` and `D:\`
   paths. Every path now comes from `config.py`.
10. **Checkpoints came in two formats**: a bare `state_dict` from the notebook
    trainer and a resumable dict from `train.py`. `load_model` reads both, and
    training also writes a portable weights-only export.
11. **torch 2.6 made `weights_only=True` the default for `torch.load`**, which
    rejects the numpy RNG state stored in resumable checkpoints. The loader sets
    the flag explicitly.
12. **Resume trusted any existing CSV.** A partial file now fails the row-count
    check and gets re-run.
13. **Gate verdicts come from the data** instead of the report text.
    `configs/gate.yaml` records the sign convention and states that G1 and G2
    were operationalised after Claims 1 and 2 were seen.
14. **Claim 3 gained a third arm.** `full` includes `snr`, which is mixing
    metadata you wouldn't have before enhancement. `feats_only` drops it. Within
    a single SNR stratum `snr` is constant, so the within-SNR margins come out
    the same either way.
15. **`models/` and `splits.py` are gone.** The old package disagreed on
    state-dict prefixes (an `STFTWrapper` added `net.`, `out` was a bare
    `Linear` with no sigmoid, an extra `window` buffer appeared) and loaded
    weights wrong. `splits.py` used column names the manifest doesn't have and
    leaked speakers and utterances.
16. **The energy decomposition counted the DC bin.** In the ~6% of clean files
    with a large offset, a mask that removed the inaudible offset got charged
    with destroying speech. `energy_decomposition` now skips bins below
    `config.DECOMP_MIN_HZ = 60.0` and keeps the old values in `*_full` columns.
    Voiced speech starts around 80 Hz, so the cut removes nothing you can hear.
    Every energy-based number changed, and one finding was withdrawn.
17. **`src/confound.py` is new**, with a `--model` flag so the LOTO test runs on
    both B1 and B3.

## Limitations

- **One recording per noise type.** Each noise type is a single short recording,
  and three of them loop. Noise type and recording identity can't be pulled
  apart, so Claim 1 holds at the recording level only. A family-level claim
  would need several recordings per type.
- **Sampled design.** Each clean utterance appears in two rows, with two
  different noise types. No utterance spans all five noise types or all eight
  SNR levels, so the direction index has to be aggregated over the corpus
  instead of compared within an utterance.
- **Direction/condition collinearity.** This blocks G3 and limits Claim 3 to
  magnitude within a condition.
- **Pooling hides real effects.** Pooled WER and pooled Spearman both gave
  misleading answers, so every table in `results/metrics/` is split by
  condition, SNR or noise type. Within one condition, `frac_pos` and `snr` carry
  the same information; the frame-level features only looked better because
  they reordered conditions.
- **Noise type, not SNR, decides which rows hurt ASR.** Hurricane and
  bubble_curtain stay at the clean-ASR floor even at −15 dB broadband SNR:
  hurricane's energy falls outside the speech band and bubble_curtain comes in
  bursts. A cut at SNR ≤ −5 picks the wrong rows. `--damaging-only` uses
  rainfall, large_commercial_ship and lightning instead, at the cost of fewer
  training rows.
- **Pre-hoc only at inference.** The predictor needs no clean reference when it
  runs, but building its training labels does.
- **Gates not recomputed** on the DC-fixed energies, and the over-dominant
  fraction on the LOTO held-out rows hasn't been rerun either.
- **B2 deferred.** Diffusion needs cloud compute.
- **Open item.** The clean-arm WER dropped from 3.07% to 1.38% on the same rows.
  The normalisation mismatch explains the size of the drop, but the change on
  the hypothesis side that caused it hasn't been tracked down.

## Citation

```bibtex
@misc{failuredirection2026,
  title  = {Failure direction in speech enhancement: pre-hoc, reference-free
            prediction of over- and under-suppression},
  author = {Musunuri, Rana Rishith},
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
