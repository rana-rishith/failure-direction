# U3_transfer: predicting speech loss on a noise type the predictor never saw

Record written 2026-11-05.

## Verdict

**FAIL. 2 of 5 MarVEN types, where the pre-registration requires 3.**

`bubble_curtain` and `rainfall` pass. `hurricane`, `large_commercial_ship` and
`lightning` fail.

This gate was declared in `configs/gate_universal.yaml` on 2026-10-19 and had never been
run or reported. It is now run and reported, and it fails.

## Provenance

| item | value |
|---|---|
| config | `configs/gate_universal.yaml`, sha256[:12] `a13d0d71f9e6` |
| config commit | `29c1566`, 2026-10-19 |
| code commit | `dc5453d`, clean tree |
| run at | 2026-11-05T08:49 |
| verdict | `results/universal/u3_transfer_verdict.json` |
| per-cell table | `results/universal/u3_transfer_cells.csv` |
| enhancer tag | `b1_weather` (fixed; nothing retrained) |

No threshold in `gate_universal.yaml` was edited. `min_types` is parsed out of the yaml
prose at run time by `_after`, like every other universal threshold.

## Pre-registered rule, as written

- `design`: "predictor trained without the held-out type; enhancer fixed"
- `pass_if`: "mean within-SNR rho > baseline rho for >= 3 of 5 MarVEN types"
- `report`: "same test on DEMAND / FSD50K held-out classes, descriptive"

## Two ambiguities, and how they were resolved

The yaml does not fully specify this gate. Neither resolution changes a threshold, and
both are recorded in the verdict's `notes`.

1. **`pass_if` says "> baseline rho" and names no arm.** `U3_within_condition` names four
   arms; `U3_transfer` inherits none explicitly. Resolved to **both** of that gate's
   baselines, `ridge_33` and `baseline_snr_logE`, so `feats_only_lgbm` has to clear both.
   This is the stricter of the two readings, so the resolution cannot inflate a pass.
   `wada_snr` is computed and reported but carries no verdict weight.
2. **The feature set is unspecified.** Run on the **33** base features from
   `src/features.py`, the set `U3_within_condition` registered by naming its arm
   `ridge_33`. The 12 burst features in `src/features_burst.py` are **not** included; see
   "Not done" below.

## A limitation of the registered design

The design line holds out the noise type and nothing else. MarVEN has **10 speakers and
every type carries all ten**, so in every fold the test speakers are also training
speakers. `stage_u3` groups its own folds by speaker precisely to avoid this;
`U3_transfer` as registered does not.

This is the registered design, not an implementation slip, and it is recorded under
`notes.speaker_overlap` so the verdict cannot be read as speaker-disjoint. A
speaker-disjoint variant is not a drop-in: holding out a type already removes all ten
speakers' rows for that type, so a joint holdout would have to split the 10 speakers and
shrink both sides. It was not run.

## MarVEN, the verdict rows

Mean within-SNR Spearman rho, 8 SNR cells per type, minimum 25 rows per cell.

| held-out type | test rows | train rows | feats_only | ridge_33 | snr+logE | wada | beats ridge | beats snr+logE | pass |
|---|---|---|---|---|---|---|---|---|---|
| bubble_curtain | 476 | 1,804 | **0.258** | 0.112 | 0.252 | -0.053 | yes | yes | **yes** |
| rainfall | 458 | 1,822 | **0.111** | 0.042 | 0.040 | -0.165 | yes | yes | **yes** |
| large_commercial_ship | 441 | 1,839 | 0.074 | -0.012 | 0.090 | -0.059 | yes | no | no |
| lightning | 459 | 1,821 | -0.036 | 0.240 | 0.259 | -0.018 | no | no | no |
| hurricane | 446 | 1,834 | -0.105 | -0.048 | -0.401 | 0.088 | no | yes | no |

Read plainly: on a MarVEN type the predictor has never seen, it ranks utterances by
expected speech loss barely better than chance at best (0.258) and worse than chance on
two of five types. On `lightning` the SNR-plus-energy baseline beats it outright, 0.259
against -0.036. On `hurricane` every arm but WADA is negative.

## DEMAND and FSD50K, descriptive only

The yaml's `report:` line asks for the same test on these corpora, descriptive. They carry
no verdict weight. `noise_type` carries the MarVEN type on every row of every corpus, so
the held-out class here is `cond`, which is how `stage_u3` groups these corpora's cells
too.

| corpus | held-out class | feats_only | ridge_33 | snr+logE | wada | beats both |
|---|---|---|---|---|---|---|
| demand | dem_A | 0.708 | 0.492 | 0.272 | 0.059 | yes |
| demand | dem_B | 0.733 | 0.514 | 0.178 | -0.025 | yes |
| demand | dem_H | 0.552 | 0.168 | 0.426 | 0.083 | yes |
| fsd50k | fsd_boat | 0.536 | 0.389 | -0.002 | 0.089 | yes |
| fsd50k | fsd_eval | 0.521 | 0.333 | 0.040 | 0.319 | yes |
| fsd50k | fsd_weather | 0.518 | 0.418 | -0.023 | 0.282 | yes |

All six cross-corpus classes clear both baselines, by margins of 0.13 to 0.38.

## The asymmetry is the result

`feats_only_lgbm` scores 0.518 to 0.733 on every held-out DEMAND and FSD50K class, and
-0.105 to 0.258 on MarVEN types. Same features, same fitter, same label definition, same
fixed enhancer. The difference is which noise the held-out rows carry.

That matches `U3_within_condition`'s own failure (MarVEN mean cell rho 0.105) and
`u3_label_reliability.csv`, which put MarVEN within-cell rank agreement at 0.884 between
reseeded replicas. The label is reproducible; it is simply not predictable from the noisy
input *within* MarVEN. On the cross-corpus conditions it is.

So U3's failure is not a feature problem or a fitter problem, and now not a
train/test-split problem either. Three gates have looked at it from three angles and
landed in the same place.

## Not done

- **The 45-feature sensitivity.** Approved, not run. `results/universal/u3_features.csv`
  holds the 33 base features plus WADA-SNR and nothing else, so the 12 burst features
  from `src/features_burst.py` need a fresh extraction pass over all 4,680 saved mixtures
  before a `--sens` arm can use them. `bst_sub150` has the largest split share in all six
  C3c models, so this is worth doing; it is a feature-extraction job, not a threshold
  question, and it cannot change the verdict above, which is registered at 33.
- **A speaker-disjoint variant**, for the reason given above.

## Reproduce

```
python scripts/run_universal.py --gate u3_transfer
```

No GPU. Reuses the cached feature table; refits four arms per held-out class.
