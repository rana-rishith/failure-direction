# Record C5: the three numbers from the 27 Oct handoff

Task C5 of the 5 Nov work order. The source line is
`handoff/claude_code_handoff_U_gates.md:68`. CPU only, committed files only.

## Verdict

All three are **correct**. No line in `paper/paper.tex` needs to change for any
of them. One adjacent claim on the same paper line could not be confirmed and is
listed at the end.

| # | claim | verdict | source of record |
|---|---|---|---|
| 1 | level-aligned `nr_g` for single-family transfer is -1% to 4% | **confirmed**, -0.015 to +0.043 | `results/diverse/summary_low_snr_levelaligned.csv` |
| 2 | matched rows with `d < 0` are 49 of 4,560 (B1 11, B3 38) | **confirmed exactly** | `results/eval/b[13]__*__test_matched.csv` |
| 3 | the LightGBM "gain" column is split counts | **confirmed**, three ways | `src/claim3.py:224` and the four committed CSVs |

## 1. Single-family transfer, -1% to 4%

The claim lands at `paper.tex:1066`: "Models trained on one MarVEN family removed
$-0.01$ to 0.04 of the noise excess on the other family."

Registered source: `results/diverse/summary_low_snr_levelaligned.csv`, rows with
`cond == marven_u`, which is the MarVEN unseen family. MarVEN test split,
SNR <= 0, level-aligned basis.

| tag | d | nr_g | g |
|---|---|---|---|
| b1_anthro | -0.994 | **-0.015** | 0.960 |
| b1_weather | -0.995 | -0.011 | 0.947 |
| b3_anthro | -0.992 | 0.008 | 0.956 |
| b3_weather | -0.995 | **0.043** | 0.929 |
| cm_anthro | -0.993 | 0.042 | 1.417 |
| cm_weather | -0.995 | 0.003 | 1.740 |

Range -0.015 to +0.043, which is -0.01 to 0.04 at the precision the paper
prints. Confirmed.

### A trap worth recording

The probe tool gives a different answer for what reads like the same quantity.
Pooling `results/probe/<tag>/rows.csv` over the other family's noise types, one
median per run, gives **+0.011 to +0.094** across the 18 single-family runs, and
never a negative value. The difference is the unit, not the data:

- the registered figure takes **SNR <= 0 only**; the probe pooling above took
  every SNR level, and the high-SNR rows remove far more noise
- the registered figure groups by the `cond` column; a per-tag pooling mixes
  cells the gate keeps apart

So `paper.tex:1066` must keep citing the diverse summary. Anyone who recomputes
it from the probe rows will get a number that is both larger and single-signed,
and will think the paper is wrong. `results/probe/reconciliation.md` records
this kind of unit mismatch for U1; this line is not covered there and should be.

## 2. Matched rows with d < 0, 49 of 4,560

$d = (r_{over} - r_{under}) / (r_{over} + r_{under})$, so $d < 0$ is a row where
under-suppression dominates: the model left more noise than it took speech, on
the noise family it was trained on. Computed from the committed per-row eval
files, with the shared `e_clean` denominator cancelling.

| file | rows | d < 0 |
|---|---|---|
| b1__anthro__test_matched.csv | 917 | 1 |
| b1__weather__test_matched.csv | 1,363 | 10 |
| b3__anthro__test_matched.csv | 917 | 8 |
| b3__weather__test_matched.csv | 1,363 | 30 |
| **total** | **4,560** | **49** |

By architecture: B1 11 of 2,280, B3 38 of 2,280. Exactly the claimed figures,
including the split. Confirmed.

The asymmetry is worth a clause in the text: B3 is the 280K-parameter GRU and
produces 38 of the 49, so inertness on matched noise is more than three times as
common in the small model.

## 3. The LightGBM "gain" column holds split counts

`src/claim3.py:222` fits `lgb.LGBMRegressor` and reads
`model.feature_importances_`. `src/claim3.py:236` writes that vector to a column
named `gain`. Three independent confirmations:

1. the regressor is constructed at `src/claim3.py:97` with no `importance_type`
2. lightgbm 4.7.0 is installed, and its `LGBMRegressor.importance_type` default
   is `split`
3. every value in all four committed importance CSVs is an integer, which gain
   never is:

| file | all integer | sum | max |
|---|---|---|---|
| claim3_weather_importance.csv | yes | 20,460 | 1,316 |
| claim3_anthro_importance.csv | yes | 7,140 | 492 |
| claim3_weather_damaging_importance.csv | yes | 3,870 | 361 |
| claim3_anthro_damaging_importance.csv | yes | 1,729 | 305 |

The figure caption is already correct: `scripts/paper_figs.py:18` says "share of
LightGBM splits". The column name inside the CSV is the only thing that
misleads, and renaming it would invalidate the committed files, so leave it and
say what it is wherever it is read.

## Open item, not one of the three

`paper.tex:1067` continues: "DEMAND-trained models removed 0.04 to 0.19 and
FSD50K-trained models 0.91 to 0.96 (per seed)."

The seed-1 DEMAND values are 0.154 (B1), 0.040 (B3) and 0.061 (CM), so 0.040 to
0.154. The claimed upper bound of 0.19 must come from seed 2 or seed 3, and
`results/diverse/` holds no per-seed files: the FSD50K row set is not in that
summary at all. **Neither the 0.19 nor the 0.91 to 0.96 range can be confirmed
from the committed diverse summary.** The per-seed source has to be located
before D8 copies those two ranges forward. This is outside C5's three numbers
and is not a finding against the paper, only an unverified claim.

### Resolved 2026-11-06: the paper is correct

The per-seed source is `results/xcorpus/report2/D_per_seed.csv`, not
`results/diverse/`. It carries one row per tag with `family` (demand or fsd),
`arch`, `nr_g` and `nr_plain`, 18 rows, 9 seeds for each family.

Level-aligned `nr_g` by family, over the 9 seeds:

| family | min | max | paper |
|---|---|---|---|
| demand | 0.040 | 0.186 | 0.04 to 0.19 |
| fsd | 0.912 | 0.962 | 0.91 to 0.96 |

Both ranges reproduce. The 0.19 upper bound is 0.186 rounded, and it does come
from a seed other than seed 1, which is why the seed-1 figures alone stopped at
0.154.

The trap worth recording: `nr_plain` over the same rows gives -2.940 to 0.628
for demand and 0.450 to 0.996 for fsd. Reading the plain column instead of the
level-aligned one would make the paper's claim look wrong by a wide margin in
both directions. The quantity in the paper is the level-aligned `nr_g`.
