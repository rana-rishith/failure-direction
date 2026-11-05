# R3: heard noise type, unheard recording

Record written 2026-11-05.

## Verdict

**U1-R3 = `intermediate`.** Unanimous: 3 of 3 anthro models, 3 of 3 seed replicates,
9 of 9 model-seed cells. No cell was `type_level`, `recording_level` or `no_contrast`.

Read plainly: when an anthro-trained model meets a *different recording of a noise type
it was trained on*, it neither behaves as it does on the heard recording nor collapses as
it does on an unseen type. It lands between the two. Failure tracks neither the noise
type alone nor the specific recording alone.

## Provenance

| item | value |
|---|---|
| config | `configs/gate_r3.yaml`, sha256[:12] `6e9767e5665c` |
| config commit | `2976373`, 2026-10-19 12:42:42 +0000 |
| runner added | `f71fba2`, 2026-10-19 12:42:44 +0000 |
| results committed | `1a9cd3d`, 2026-10-20 04:07:57 +0000 |
| thresholds now read from yaml | `4d7d0a7` |
| test pinning the parse | `99afa00` |

The config commit precedes the runner commit and precedes every R3 number by about
15.5 hours. Config and runner were committed two seconds apart, so they were written in
one sitting; the claim this supports is only the one that matters, that no R3 result
existed when the cut points were fixed.

Until `4d8c88e`..`4d7d0a7` the three cut points were literals inside `src/r3.py:report()`
rather than read from the yaml. The values always matched the config. Re-deriving all
three seed verdicts from the saved per-row CSVs with `python -m src.r3 --report` after the
change left all nine of `summary.csv`, `by_snr.csv` and `verdict.csv` byte-identical
(`git diff` empty), so no published number moved.

## Pre-registered rule

- `position`: `p = (med_R3 - med_R4) / (med_R1 - med_R4)`, pooled medians over rows.
- `validity`: a model counts only if its R1 minus R4 contrast in `noise_removed_g` is
  `>= 0.20`; else `no_contrast`.
- `criteria`: `type_level` at `p >= 0.67`, `recording_level` at `p <= 0.33`, otherwise
  `intermediate`.
- `claim_verdict`: the class shared by `>= 2` of the 3 anthro models, else `mixed`.
- Conditions: R1 = MarVEN `large_commercial_ship` test rows (441). R3 = the same clean
  file and target SNR with a DeepShip crop (Cargo, Tanker, Passengership; Tug excluded as
  not a large commercial ship), 32 kHz decimated to 16 kHz. R4 = MarVEN weather test rows
  (rainfall, lightning, hurricane), 441 drawn per-SNR-stratified, `random_state=0`.

## Per-cell table

`p_noise_removed` is the primary statistic; `p_d` is secondary. Source:
`results/r3{,_s2,_s3}/verdict.csv`.

| seed | model | nr R1 | nr R3 | nr R4 | p (nr) | p (d) | contrast | class |
|---|---|---|---|---|---|---|---|---|
| 1 | b1_anthro | 0.962 | 0.422 | 0.052 | 0.406 | 0.133 | 0.909 | intermediate |
| 1 | b3_anthro | 0.942 | 0.506 | 0.084 | 0.491 | 0.319 | 0.858 | intermediate |
| 1 | cm_anthro | 0.956 | 0.487 | 0.083 | 0.462 | 0.202 | 0.873 | intermediate |
| 2 | b1_anthro | 0.959 | 0.429 | 0.101 | 0.382 | 0.134 | 0.857 | intermediate |
| 2 | b3_anthro | 0.941 | 0.455 | 0.091 | 0.429 | 0.263 | 0.850 | intermediate |
| 2 | cm_anthro | 0.957 | 0.456 | 0.071 | 0.435 | 0.189 | 0.886 | intermediate |
| 3 | b1_anthro | 0.960 | 0.403 | 0.066 | 0.377 | 0.141 | 0.893 | intermediate |
| 3 | b3_anthro | 0.942 | 0.460 | 0.081 | 0.440 | 0.239 | 0.860 | intermediate |
| 3 | cm_anthro | 0.956 | 0.455 | 0.067 | 0.436 | 0.189 | 0.889 | intermediate |

Range of `p_noise_removed`: 0.377 to 0.491, against cut points 0.33 and 0.67. Every value
sits inside the intermediate band with margin on both sides, and the spread across three
seeds is 0.11, smaller than the distance to either cut point. Contrast 0.850 to 0.909
against a 0.20 floor, so no model was excluded for lack of contrast.

`p_d` runs lower, 0.133 to 0.319, which would read as `recording_level` if `d` were the
primary metric. The yaml names `noise_removed_g` primary and `d_g` secondary, so the
verdict stands on `p_noise_removed`. The gap between the two is reported, not resolved.

## Why R3 is not a rung in U1_novelty_monotone

`configs/gate_universal.yaml` defines R3 under `definitions.rungs` and then scopes it
conditionally in `U1_novelty_monotone.pass_unit_if`: "median d strictly decreases
R1 > R2 > R4 (**R3 added where the corpus allows**)". R3 is absent from the ordering the
gate tests. The U1 runner records `"R3": "not in this stage"`.

The corpus does not allow it, for two reasons both written down before any R3 number
existed, in `gate_r3.yaml` at `2976373`:

1. **MarVEN has one recording per type.** An R3 rung needs a second recording of a
   trained-on type, and MarVEN has none, so R3 requires an outside corpus. This is a
   property of the dataset, not of any result.
2. **The substitute corpus confounds the thing being measured.** Under
   `caveats_pre_stated`: DeepShip is the 63-file GitHub sample, 60 usable, from a
   different hydrophone and site, so "channel shift is confounded with recording
   novelty". A rung whose novelty is entangled with a channel change cannot enter a
   strict-monotonicity ordering that is supposed to isolate novelty.

So R3 is reported as a standalone gate with its own pre-registered criteria and its own
verdict, and is not inserted into the U1 ordering. The reason is a missing-data fact fixed
in advance, not a judgement made after seeing numbers.

## Also in results/r3, exploratory only

`gate_r3.yaml` declares an `exploratory` block with no verdict: weather models against
MBARI storm crops (6 days) and dry crops (4 days). Rows are in `X_*.csv` and medians in
`summary.csv`. MBARI storm mixes wind, rain and surf and is not the same type as any one
MarVEN weather recording, so the config pre-states that no R3 verdict is drawn from it.
Reported as descriptive: `b1_weather` median `noise_removed_g` 0.327 storm and 0.304 dry,
against 0.974 on heard weather and 0.008 on unseen anthro.

## Reproduce

```
python -m src.r3 --report
python -m src.r3 --report --suffix _s2
python -m src.r3 --report --suffix _s3
```

No GPU. Re-derives `summary.csv`, `by_snr.csv` and `verdict.csv` from the saved per-row
CSVs.
