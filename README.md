# failure-direction

**Which way does a speech enhancement model fail on noise it never heard?**

A model can remove the speech along with the noise, or it can leave the noise
in place. The two cost completely different things downstream, and a single
quality score such as SI-SDR reports one number that cannot tell you which one
you got.

| Failure mode | What the mask does | Consequence |
|---|---|---|
| **Over-suppression** | pushes speech-band energy below the clean reference | speech is gone and no later stage recovers it |
| **Under-suppression** | stays near 1 in noise-dominated bins | noise remains, speech survives, a recognizer can still use it |

This repository splits the error of every utterance into those two energies and
measures the balance between them across noise the model heard, noise it half
heard, and noise it never heard.

Every confirmatory test was written as a gate with a numeric threshold and
committed **before** the run that decided it. Every outcome is reported here,
including the ones that failed. A paper describing this work is in preparation.

- **Set up and run it:** [docs/USAGE.md](docs/USAGE.md)
- **Every number in detail:** [docs/RESULTS.md](docs/RESULTS.md)
- **How each result was produced:** the [records](#records) below

---

## What we claim

Each line is a registered gate that passed. Thresholds live in `configs/` and
are read from the file at run time, never hard-coded.

| Claim | Gate | Evidence |
|---|---|---|
| Enhancement degrades measurably on unseen noise | `G2` PASS | median direction-free magnitude gap 0.206, threshold 0.10 |
| The failure direction falls monotonically along the novelty ladder: heard samples, then unheard segment of a heard recording, then unseen type | `U1_novelty_monotone` PASS | holds for all three bounded-mask architectures |
| On an unseen noise type every architecture lands in the same failure class, **inert** | `U1_failure_class` PASS | B1, B3 and CM all inert |
| That behaviour is not an artefact of bounded masks | `U2_beyond_bounded` PASS | 2 of 3 non-bounded classes; the generative class is pending |
| Training-noise diversity moves the direction | `D_fsd` partial (3 of 3) | FSD50K-trained models remove 0.92 to 0.96 of the noise excess |
| A narrow, weather-only form of the pre-hoc predictor replicates on fresh seeds | `C3c` HOLDS (6 of 6), `C3_level_recheck` PASS (6 of 6) | registered after it held on 15 earlier models |
| The ladder result survives an unheard *recording* of a heard type | `r3` intermediate | 9 of 9 runs |

## What we do not claim

These gates failed, were untestable, or were never run. They are listed because
a registered ledger that only reports its successes is not a ledger.

| Not claimed | Gate | Why |
|---|---|---|
| That failure direction separates the five noise types | `G1` **FAIL** | spread 0.1608, threshold 0.30 |
| Any downstream word-error-rate asymmetry | `G3` **UNTESTABLE** | direction and condition are collinear at 0.995; only 11 of 2,280 matched rows carry a negative *d* |
| A general reference-free predictor of speech loss | `U3_within_condition` **FAIL**, `U3_transfer` **FAIL** | both post-hoc sensitivity arms fail too |
| Any mechanism behind the direction | `M0_oracle_headroom` **FAIL** | best oracle gain 0.169 dB over 4 cells; `M1` was blocked by `M0` and never run |
| That the pre-hoc predictor generalizes across noise families | `C3_active` **FAILS**, `C3b` **FAILS** | 1 of 3 FSD architectures passed both folds |
| That distance or stationarity explains the direction | `D2_distance` **FAIL**, `S_stationarity` **FAIL** | rho -0.095 and -0.083 |
| That the effect is specific to one noise family | `H_F_family_fresh` not family-specific | 0 of 9 pairs |
| That the Claim 1 weather gap is full-band | `C1_lowcut` sub-100 Hz dependent | 3 of 6 cells at or above 0.75 of the full-band gap |
| Anything about unseen noise **families** | LOTO control | "unseen" here means an unseen noise *recording*; the data cannot support the family claim |

**Withdrawn.** An earlier result claimed B3 destroys about 40% of clean speech
energy in a few concentrated bins while SI-SDR and STOI look fine. Those files
were DC-heavy and the mask was removing an offset nobody could hear. That
result, and the mechanism built on it, are withdrawn.

## What we achieved

- **A pre-registered gate ledger for speech enhancement.** 31 rows: 28
  registered gates, 3 post-hoc arms kept in a separate table. 29 carry a
  machine-readable verdict, one is pending and one was never run. Every verdict
  file records the gate file's commit, its SHA-256 digest, the code commit, the
  thresholds used and every per-cell number.
- **A direction metric with an oracle floor.** The oracle Wiener mask itself
  runs at *d* = +0.95 to +0.59 across SNR, so *d* = 0 is not the neutral
  reference an intuitive reading would assume.
- **A reproducibility probe.** `src/probe/` rescores a frozen 2,280-utterance
  split and reproduces the published numbers to a worst relative difference of
  8.2e-13, and reproduces both registered verdicts it can reach with no
  disagreement.
- **Confidence intervals on every headline number**, by cluster bootstrap over
  base utterances, 10,000 resamples, reported as descriptive.

## Datasets

| Dataset | Used for | Citation |
|---|---|---|
| **MarVEN** | the corpus: speech mixed with rainfall, lightning, hurricane, bubble-curtain and ship noise | "MarVEN: Marine vessel and environmental noise speech corpus," Zenodo, doi:10.5281/zenodo.20714212 |
| **LibriSpeech** | the clean speech behind MarVEN mixtures | V. Panayotov, G. Chen, D. Povey, and S. Khudanpur, "LibriSpeech: An ASR corpus based on public domain audio books," *ICASSP*, 2015, pp. 5206-5210 |
| **DEMAND** | a contrasting noise family for the diversity control | J. Thiemann, N. Ito, and E. Vincent, "The diverse environments multi-channel acoustic noise database (DEMAND)," *Proc. Meetings Acoust.*, vol. 19, 2013, p. 035081 |
| **FSD50K** | the high-diversity training noise arm | E. Fonseca, X. Favory, J. Pons, F. Font, and X. Serra, "FSD50K: An open dataset of human-labeled sound events," *IEEE/ACM TASLP*, vol. 30, pp. 829-852, 2022 |
| **DeepShip** | unheard ship recordings for the R3 rung | M. Irfan, J. Zheng, S. Ali, M. Iqbal, Z. Masood, and U. Hamid, "DeepShip: An underwater acoustic benchmark dataset," *Expert Syst. Appl.*, vol. 183, p. 115270, 2021 |
| **VoiceBank-DEMAND** | the training set of the released pretrained enhancers | C. Valentini-Botinhao, X. Wang, S. Takaki, and J. Yamagishi, "Investigating RNN-based speech enhancement methods for noise-robust text-to-speech," *SSW*, 2016, pp. 146-152 |

## Figures

All 13 figures live in [`paper/figs/`](paper/figs) as PDF and PNG, and are
rebuilt from committed result tables by `scripts/make_figs.ps1`.

| Figure | Shows |
|---|---|
| `fig_pipeline` | data, models, measurement and prediction through to the gates |
| `fig_direction` | the over- and under-suppression split by condition |
| `fig_ladder` | median *d* per rung (R1, R2, R4) by SNR, per architecture |
| `fig_diversity` | what training-noise diversity changes |
| `fig_features` | the pre-hoc feature importances |
| `fig_claim3_chain` | the Claim 3 result chain |
| `fig_u3_ceiling` | U3 against the label-reliability ceiling |
| `fig_spectrograms` | example failures of each mode |
| `claim1_snr` | the Claim 1 gap by input SNR |
| `figA1_wer` … `figA4_b3_dc_tail` | appendix: WER, rank agreement, training reproducibility, the DC tail |

Generated LaTeX gate tables come from `scripts/make_gate_tables.py`, which
computes every verdict from the YAML rule and every provenance hash from the
file, so the table cannot drift from the ledger.

## Repository map

| Path | What is in it |
|---|---|
| `src/` | the library. Imported, never run directly: energy split, metrics, models, gates, `src/probe/` |
| `scripts/` | every runnable entry point, Python and PowerShell. `run_universal.py` scores the gates, `make_gate_tables.py` builds the ledger tables, `make_figs.ps1` rebuilds the figures, `run_*.ps1` drive the long jobs |
| `configs/` | gate files. Thresholds are read from these at run time |
| `results/` | every measured result. Index below |
| `docs/` | usage, detailed results, and one record per analysis |
| `tests/` | the test suite, `python -m pytest` |
| `paper/figs/` | the 13 figures |
| `notebooks/` | exploratory notebook |
| `config.py` | paths and constants, imported as `import config as C`. It stays at the root because every module reaches it from there |
| `conftest.py` | sets `MKL_THREADING_LAYER` before pytest imports numpy. No test code. At the root because pytest reads only the rootdir copy |

### Results index

`results/` holds 699 files and is the evidence behind every verdict in the
tables above. Nothing in it is regenerated by a normal run, so it is safe to
read as the record of what happened.

| Directory | Files | Holds |
|---|---|---|
| `claim3b/`, `claim3c/`, `claim3_active/`, `claim3_level/`, `claim3/` | 375 | the Claim 3 arms: per-seed cells, verdicts and logs |
| `probe/` | 93 | the probe rescore, one directory per model tag, plus `reconciliation.md` |
| `xcorpus/` | 70 | cross-corpus evaluation and the `report2/` summary tables |
| `metrics/` | 49 | the energy-split metric tables, oracle masks and `gate_results.yaml` |
| `universal/` | 16 | the U1, U2 and U3 cells and verdicts |
| `confound/` | 16 | the leave-one-type-out control |
| `diverse/` | 12 | the training-diversity arm |
| `r3/`, `r3_s2/`, `r3_s3/` | 23 | the R3 rung on unheard DeepShip recordings, three seeds |
| `ci/` | 4 | bootstrap confidence intervals for every headline number |
| `eval/`, `labels_*/`, `method/`, `stationarity/`, `pilot_level/`, `distance/`, `segment/`, `claim2_level/`, `label_stability/` | the rest | per-model evaluation rows and the smaller controls |

## Records

One file per analysis, in `docs/`. Each says what was measured, with which
command, what was found, and what was decided.

| Record | Subject |
|---|---|
| [gate inventory](docs/record_gate_inventory_2026-11-05.md) | every gate, its file and its verdict |
| [probe tool](docs/record_probe_tool_2026-11-05.md) | the frozen split, verification and the `unknown` class |
| [U2 arms audit](docs/record_audit_U2_arms_2026-11-05.md) | that both passing U2 arms are fine-tuned, not zero-shot |
| [U2 generative run](docs/record_u2_generative_run_2026-11-05.md) | the SGMSE+ fine-tune, including a learning-rate deviation |
| [D basis audit](docs/record_audit_D_basis_2026-11-05.md) | plain against level-aligned basis for the diversity control |
| [bootstrap CIs](docs/record_bootstrap_ci_2026-11-06.md) | the 122 headline intervals |
| [H_P1 paired CI](docs/record_c2_hp1_paired_ci_2026-11-06.md) | the SGMSE+ shift interval |
| [oracle delta d](docs/record_c3_oracle_delta_d_2026-11-06.md) | the oracle floor on the direction index |
| [WER source](docs/record_c4_wer_source_2026-11-06.md) | which run produced the reported word error rates |
| [three numbers](docs/record_c5_three_numbers_2026-11-06.md) | three paper numbers traced to their source |
| [G1 G2 G3](docs/record_g1g2g3_persisted_2026-11-06.md) | persisting the three original gates to a file |
| [repository layout](docs/record_repo_layout_2026-11-06.md) | the src/scripts split, and the stale paths it leaves in six pre-registered yamls |

## Citation

See [`CITATION.cff`](CITATION.cff). Licensed under the terms in
[`LICENSE`](LICENSE).
