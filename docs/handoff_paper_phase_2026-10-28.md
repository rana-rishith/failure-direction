# Handoff: failure-direction, paper phase

Written 2026-10-28. For a fresh Claude chat with no history of this project.

Read this, then `docs/paper_draft_route.md` for the drafting plan.

---

## What this project is

An enhancement model trained on one noise distribution and deployed on another fails in
a *direction*: it either removes speech (over-suppression) or leaves noise
(under-suppression). The repo measures that direction, tests whether it follows noise
novelty, and tests whether it can be predicted from the noisy input before enhancement
runs.

Setting is marine and underwater listening (MarVEN), with DEMAND and FSD50K as
cross-corpus checks.

## Repo

`C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\repo-failure-direction`,
GitHub `rana-rishith/failure-direction`, branch `main`. Head at writing: `b5ac579`.

## The pre-registration, which is the paper's spine

`configs/gate_universal.yaml`, committed `29c1566` on 2026-10-19, before any
universal-claim data existed. Every gate's pass criteria were fixed in advance.
`configs/gate_amend_cm.yaml` was committed before any `cm` model was trained and is what
makes `cm` count as the complex-mask class.

`scripts/run_universal.py` reads every threshold out of the yaml prose at run time via
`_after()`. **No threshold is typed into the code.** Each gate writes
`results/universal/<gate>_verdict.json` carrying the config commit, the yaml sha256, the
code commit, a dirty flag, the thresholds used and every per-cell number.

The paper will state that the U gates ran after other results were seen with thresholds
unchanged. Nothing in the code may weaken that statement.

## Gate status

| Gate | Verdict | Where |
|---|---|---|
| `U1_novelty_monotone` | **PASS** | `results/universal/u1_verdict.json` |
| `U1_failure_class` | **PASS** (all three architectures inert) | `u1class_verdict.json` |
| `U2_beyond_bounded` | **PASS**, 2 of 3 classes | `u2_verdict.json` |
| `U3_within_condition` | **FAIL** | `u3_verdict.json` |
| `M0_oracle_headroom` | **FAIL**, all 4 cells | `results/method/m0_summary.csv` |
| `M1_predicted_gamma` | blocked by M0's `requires`, never run | nowhere |
| `U3_transfer` | **declared, never run, never reported** | nowhere |
| `D_diversity_control` | run | `results/diverse/` |
| `C3_active` / `C3b` / `C3c` | FAIL / FAIL / HOLDS | `results/claim3*/` |

Earlier claims 1 and 2 are settled and written up in the section plans.

### Numbers worth knowing

- **U1**: median `d` decreases R1 > R2 > R4 in 4 of 4 low-SNR levels for both bounded
  masks. R3 is defined in the yaml and was **not** evaluated; the runner records
  `"R3": "not in this stage"`.
- **U2**: `cm` and `dfn3` each clear 4 of 4 levels, both folds. `dfn3` pooled medians at
  −15 dB are R1 −0.106, R2 −0.976, R4 −0.998. SGMSE+ (the `generative` class) is
  unmeasured and recorded under `classes_missing`.
- **U3**: MarVEN mean within-cell rho, `feats_only_lgbm` 0.105 against `ridge_33` 0.091,
  `baseline_snr_logE` −0.072, `wada_snr` −0.068. Win fraction against ridge 0.45 where
  0.75 was required. DEMAND 0.455, FSD50K 0.463.
- **U3 post-hoc sensitivity** (`u3_sens_canonical_lgbm_verdict.json`, `post_hoc: true`):
  refitting the lgbm arm with `src.claim3.fit_arm` gives 0.091 / 0.436 / 0.417, slightly
  *worse*. The fitter is not what fails U3.
- **U3 label reliability** (`results/universal/u3_label_reliability.csv`): within-cell
  rank agreement on MarVEN is 0.884 between reseeded replicas and 0.791 across
  architectures. The label is reproducible, so U3 failed on a real target, not on noise.
  DEMAND 0.847 / 0.773, FSD50K 0.855 / 0.761.
- **Cross-architecture label agreement**, pooled within SNR
  (`results/metrics/claim3_cross_arch_agreement.csv`): 0.98 matched, 0.96 unseen.
- **C3c HOLDS**: `feats_only` mean within-SNR rho 0.72 to 0.77 against baseline 0.16 to
  0.20, 6 of 6 held-out models.
- **M0**: per-utterance oracle gamma buys 0.029 to 0.169 dB against a 0.5 dB threshold,
  and the oracle picks `g1.0` for 833 of 1363 utterances. The method has no headroom.
- **Routing is negative**: 15.94 corpus WER always-enhance against 16.32 at k=5.

### The feature-count gap

U3 ran on the **33** base features (`src/features.py`). Claim 3's winning models use
**45**: the 33 plus the 12 burst features in `src/features_burst.py`.
`scripts/run_universal.py:262` imports only `src.features`. `bst_sub150` has the largest
split share in all six C3c models, so the most important feature in the configuration
that works was absent from the gate that failed.

The yaml pre-registered the 33 set and names the arm `ridge_33`, so **the U3 verdict is
correct as it stands and must not be re-run with 45 features under the same gate id.**

## Venue and goal

Target is **IEEE/ACM TASLP**. Journal, no deadline, expects completeness. A preprint on
arXiv plus "submitted to TASLP" is also the deliverable for a CMU AI MS application in
December 2026; see `docs/PRIVATE_ms_application_plan.md`, which must not be committed.

Two consequences for how the work is finished:

1. **Every gate declared in the published yaml needs a reported outcome**, including
   "not run, and why". `U3_transfer` and the R3 rung are currently silent, and a
   reviewer who opens the config file will count. A pre-registration with a silent gate
   is selective reporting.
2. SGMSE+ and R3 are table stakes at this venue, not optional polish. Better run now
   than in a revision on a reviewer's clock.

## Paper state

`paper/` holds `main.tex` (102 lines) and 13 section files, 464 lines total. Almost
every section is a `\plan{}` skeleton naming its outline and source files, with no prose.
Drafting is the bottleneck, not the experiments.

**Never commit or push `paper/*.tex`.** They stay untracked and local.

## Hard rules, carried from the previous handoff

- Read every threshold from `configs/gate_universal.yaml`. Hard-code none.
- Do not edit `gate_universal.yaml`. If a threshold looks wrong or ambiguous, stop and
  ask Rana.
- Commit one file at a time.
- No `Co-Authored-By`, `Claude-Session` or any other attribution trailer. Only Rana
  appears as author. This holds for every commit and for file contents.
- Commit a result only after exit code 0 and a non-empty output file. A crash once
  committed a 0-byte PDF.
- Per-utterance dumps stay gitignored. Commit verdict JSON and per-cell CSVs.
- Run anything that imports torch from inside `conda activate faildir`. Calling
  faildir's `python.exe` by full path from `(base)` loads base's MKL and numpy dies with
  `0xc06d007f`. Check `sys.executable` contains `envs\faildir\`. Use `python -m pytest`,
  never bare `pytest`.
- One GPU job at a time. Never run U1 training and U3 feature extraction together.
- There is no D: drive.

Conda envs: `faildir` (repo code), `dfnet` (DeepFilterNet3), `sgmse` (SGMSE+).

## Run commands

```bash
python scripts/run_universal.py --gate all          # u1 -> u1class -> u3
python scripts/run_universal.py --gate u2
python scripts/run_universal.py --gate u3 --sens canonical_lgbm
python scripts/u3_label_reliability.py
python -m pytest -q                                 # 58 tests
```

The DFN3 arm, end to end, switching envs per step and resumable at every step:

```bash
.\scripts\run_u2_dfn3.ps1
```

## Rana's preferences

Terse answers, one concept at a time, no em dashes. State failures plainly with the
numbers. Do not pad with options that will not be pursued.
