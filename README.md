# failure-direction

This repository holds the code, the gate files and the results of the paper
"Do No Harm, Do No Good: How Speech Enhancement Fails on Unseen Noise and How to
See It Coming" by Rana Rishith Musunuri and Kavita Jhajharia.

The paper splits the error of each enhanced utterance into speech loss and
leftover noise. It tests each claim with a registered gate. A gate has three parts:

- The **gate file** is a yaml file in `configs/`. It holds the thresholds and
  the pass rule. We committed it before the run that decided the gate.
- The **runner** is the program that scores the gate.
- The **verdict file** is the output of the runner in `results/`.

The repository does not include audio or model checkpoints. You can read every
verdict from a clone. To run a gate again, you must first train the models.

## Where is what

| Path | Contents |
|---|---|
| `configs/` | The 16 gate files and the frozen test split, `splits/marven_test_v1.json` |
| `src/` | The energy split, the models, the predictors and most runners. `src/probe/` is the probe tool |
| `scripts/` | The runner of the U gates, the pipeline, the figure scripts and the `.ps1` drivers |
| `results/` | The verdict files and the tables behind them, one folder for each gate group |
| `docs/` | [USAGE.md](docs/USAGE.md), [RESULTS.md](docs/RESULTS.md), [CLAIMS.md](docs/CLAIMS.md) and one `record_*.md` file for each analysis |
| `tests/` | The tests. Run `python -m pytest` |
| `paper/figs/` | The figures. `paper/figs_src/` and `scripts/` hold the code that draws them |
| `notebooks/` | One notebook, built by `scripts/build_notebook.py` |
| `config.py` | Paths and constants. It reads the `FAILDIR_*` environment variables |

The `.ps1` drivers are the logs of our own runs. They contain paths of our
computer, so use the commands in [docs/USAGE.md](docs/USAGE.md).

## Gates

The first column gives the gate name in the paper. The last column gives the
section of the paper. Start a `src.*` runner with `python -m` and a `scripts/`
runner with `python`. Verdict files are in `results/`.

| Gate | Gate file in `configs/` | Runner | Verdict file in `results/` | Sec. |
|---|---|---|---|---|
| G1, G2, G3 | `gate.yaml` | `src.analysis` | `metrics/gate_results.yaml` | IV-B |
| LOTO | `gate.yaml` (`confound`) | `src.confound --report` | `confound/loto_summary__b1.csv`, `loto_summary__b3.csv` | IV-C |
| Seg | `gate.yaml` (`segment`) | `src.segment --report` | `segment/segment_summary.csv` | IV-C |
| D | `gate_universal.yaml` | `src.diverse --report` | `diverse/summary_low_snr.csv` | IV-D |
| M0 | `gate_universal.yaml` | `src.method_oracle --report` | `method/m0_summary.csv` | IV-D |
| M1 | `gate_universal.yaml` | not run, because M0 failed | none | IV-D |
| D2 | `gate_distance.yaml` | `src.distance` | `distance/summary.csv` | IV-D |
| S | `gate_stationarity.yaml` | `src.stationarity --set full` | `stationarity/summary_full.csv` | IV-D |
| Level | `gate_amend_level.yaml`, `gate_amend_level_correction.yaml` | none (definition) | none | III-C |
| CM | `gate_amend_cm.yaml` | none (definition) | none | III-B |
| C3_level | `gate_claim3_level.yaml` | `src.claim3_level` | `claim3_level/verdict.csv` | IV-E |
| P-L | `gate_pilot_level.yaml` | `src.pilot_level` | `pilot_level/verdict.csv` | IV-D |
| R3 | `gate_r3.yaml` | `src.r3 --report` | `r3/verdict.csv`, `r3/report.md` | IV-C |
| H_S1, H_S2 | `gate_overnight.yaml` | `src.xcorpus report` | `xcorpus/report/H_S1_seed_contrast.csv`, `H_S2_r3_seeds.csv` | IV-C |
| D_fsd, H_FD, H_D2, H_F | `gate_overnight2.yaml` | `src.xn2` | `xcorpus/report2/D_fsd.csv`, `H_FD.csv`, `H_D2.csv`, `H_F.csv` | IV-D |
| C1_lowcut | `gate_overnight2.yaml` | `src.xn2` | `xcorpus/report2/C1_lowcut.csv` | IV-A |
| H_P DFN3 | `gate_overnight2.yaml` | `src.xn2` | `xcorpus/report2/H_P_dfn3.csv` | IV-D |
| H_P SB | `gate_xn2_sgmse_ext.yaml` | `src.xcorpus ext-score`, then `src.xn2` | `xcorpus/report2/H_P_sgmse.csv` | IV-D |
| U1 | `gate_universal.yaml` | `scripts/run_universal.py --gate u1` | `universal/u1_verdict.json` | IV-C |
| U1-class | `gate_universal.yaml` | `scripts/run_universal.py --gate u1class` | `universal/u1class_verdict.json` | IV-C |
| U2 | `gate_universal.yaml` | `scripts/run_universal.py --gate u2` | `universal/u2_verdict.json` | IV-C |
| U3 | `gate_universal.yaml` | `scripts/run_universal.py --gate u3` | `universal/u3_verdict.json` | IV-E |
| U3-transfer | `gate_universal.yaml` | `scripts/run_universal.py --gate u3_transfer` | `universal/u3_transfer_verdict.json` | IV-E |
| C3_active | `gate_claim3_active.yaml` | `src.claim3_active` | `claim3_active/verdict.csv` | IV-E |
| C3b | `gate_claim3b.yaml` | `src.claim3b` | `claim3b/heldout/verdict.csv` | IV-E |
| C3c | `gate_claim3c.yaml` | `src.claim3c` | `claim3c/heldout/verdict.csv` | IV-E |

The code and the result files use the tag `sgmse` for the model that the paper
calls SB. The two `*_sens_*_verdict.json` files in `results/universal/` are post
hoc checks and change no verdict.

## Check a verdict without training

1. Open a verdict file from the table. The five U verdicts are JSON files. Each
   one records the gate file commit, the gate file hash, the code commit, the
   thresholds and the verdict.
2. Run `sha256sum configs/gate_universal.yaml`. Compare the first 12 characters
   with `config_sha256_12` in the JSON file.
3. Run `git log -- configs/gate_universal.yaml`. Compare the commit date with
   `run_at` in the JSON file. The commit must be the earlier one.
4. The other verdict files are CSV, yaml or markdown files and record no commit.
   For these files, compare the dates of `git log` on the gate file and on the
   verdict file.

`results/probe/reconciliation.md` compares the probe tool with the registered
verdicts. `results/ci/` holds the bootstrap intervals.

## Reproduce

```
conda env create -f environment.yml
conda activate faildir
pip install torch --index-url https://download.pytorch.org/whl/cu124
python scripts/00_verify_env.py
python -m pytest
```

| Data | Where to get it | How the code finds it |
|---|---|---|
| MarVEN | Zenodo, doi:10.5281/zenodo.20714212 | Set `FAILDIR_ROOT` to the folder that holds `manifest.csv` |
| LibriSpeech transcripts | openslr.org/12 | Set `FAILDIR_TRANS`. Only the WER stage reads it |
| DEMAND, FSD50K, DeepShip, MBARI, VoiceBank-DEMAND | From their publishers | `python -m src.xcorpus build` and `python -m src.fsd prep` |

MarVEN citation: R. Bhagawati and K. Jhajharia, "MarVEN: A controlled benchmark
of clean speech in marine weather and vessel noise," [Dataset], Zenodo, ver. 1.0,
Jun. 2026, doi:10.5281/zenodo.20714212.

- To check the data, run `python scripts/01_verify_data.py --sample 300`.
- To work without MarVEN, run `python scripts/make_synthetic_dataset.py --out data/MarVEN_synth`.
- To train one model, run `python -m src.train --model b1 --fold weather --steps 20000`.
- To test the pipeline with short runs, run `python scripts/run_pipeline.py --smoke`.
- To run the full pipeline, run `python scripts/run_pipeline.py`.

[docs/USAGE.md](docs/USAGE.md) gives each command with its options.

## Licence and citation

The code has the MIT licence ([LICENSE](LICENSE)). To cite it, use
[CITATION.cff](CITATION.cff). For questions, open an issue on GitHub.
