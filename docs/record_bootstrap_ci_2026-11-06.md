# Record C1: bootstrap CIs for the headline numbers

Task C1 of the 5 Nov work order. CPU only.

**Every interval in this record is descriptive and is not part of a gate rule.**
No verdict file was read for a decision, none was written, and no registered
class changes. The intervals say how firmly the data holds the numbers the paper
prints, nothing more.

| | |
|---|---|
| script | `scripts/bootstrap_ci.py --task headline` |
| output | `results/ci/headline_ci.csv`, 122 intervals |
| resamples / seed | 10,000 / 1234 |
| resampling unit | the base LibriSpeech utterance, never the row |
| runtime | 27 s for all 122 |

## Method, and the one thing that makes it trustworthy

Rows that share a base utterance are not independent, so the unit is the base
utterance and every row of a drawn base enters the resample together. A row
bootstrap would report intervals that are too narrow.

**Each family asserts its own point estimate against the number the paper
prints, before it reports an interval.** If the row filter, the column choice or
the aggregation ever drifts, the script fails instead of publishing a confident
interval around the wrong quantity. All 122 passed. The checks are:

| family | checked against | tolerance |
|---|---|---|
| SI-SDR gap | the paper's own table, `paper.tex:826-829` | 2 dp |
| over:under ratio | the medians at `paper.tex:896-899` | 4 dp |
| U1 median d | `results/universal/u1_cells.csv`, all 108 | 4 dp |
| D_fsd | `results/xcorpus/report2/D_fsd.csv` | 1e-9 |

Identifying the right aggregation was not obvious and is worth recording: the
SI-SDR table is a **mean**, not a median, and the over:under figures use
`e_over/e_clean` on the mask-intent basis, not the `_full` columns. Both were
settled by reproducing the printed values, not by assumption.

## 1. SI-SDR gap, each model and fold

Matched minus unseen mean SI-SDR output.

| model, fold | matched | unseen | gap | 95% CI |
|---|---|---|---|---|
| B1 anthro | 15.435 | 2.962 | **12.47** | [11.71, 13.24] |
| B1 weather | 15.031 | 3.321 | **11.71** | [10.86, 12.56] |
| B3 anthro | 14.115 | 2.983 | **11.13** | [10.37, 11.90] |
| B3 weather | 13.945 | 3.255 | **10.69** | [9.83, 11.55] |

The abstract's "10.7 to 12.5 dB" is the spread of these four point estimates and
is correct. But each single cell carries about +/-0.8 dB, so **the four cells are
not resolved from one another**: B1 anthro at 12.47 and B3 weather at 10.69 have
intervals that nearly touch, and the two middle cells overlap both. The
honest reading is one gap of about 11.5 dB with fold-level differences the data
cannot separate, not a trend across folds. The CI union is 9.83 to 13.24 dB.

The bootstrap is unpaired here. The two splits share 601 base utterances but not
all of them (982 matched, 759 unseen), and pairing on the shared subset would
move the point estimate off the published table. Ignoring the shared bases
widens the interval, so these four err wide rather than narrow.

## 2. Over:under median ratio, matched and unseen

Ratio of the two median ratios, mask-intent basis, pooled over both folds and
all SNRs.

| arch, split | orientation | point | 95% CI | paper prints |
|---|---|---|---|---|
| B1 matched | over : under | **5.93** | [5.62, 6.26] | 5.8 |
| B3 matched | over : under | **4.95** | [4.66, 5.34] | 5.0 |
| B1 unseen | under : over | **37.72** | [34.34, 42.54] | 38 |
| B3 unseen | under : over | **28.44** | [26.28, 31.65] | 29 |

B1 and B3 do not overlap in either split, so the architecture difference is
resolved in both directions: B1 over-suppresses more on matched noise and goes
further inert on unseen noise.

### Two printed ratios are off, from dividing rounded medians

The paper computes each ratio from the medians it has already rounded to 4 dp:

| | rounded division | printed | true ratio | should print |
|---|---|---|---|---|
| B1 matched | 0.0187/0.0032 = 5.84 | 5.8 | 5.931 | **5.9** |
| B3 matched | 0.0209/0.0042 = 4.98 | 5.0 | 4.951 | 5.0, no change |
| B1 unseen | 0.2242/0.0059 = 38.00 | 38 | 37.719 | 38, no change |
| B3 unseen | 0.2172/0.0076 = 28.58 | **29** | 28.444 | **28** |

Two consequences, both for D8:

- `paper.tex:898` should read 5.9 rather than 5.8
- `paper.tex:60` and the abstract's "29 to 38 times" should read **28 to 38**

Neither is large and neither touches a gate. Both are wrong as printed, and the
B3 one changes a number in the abstract.

## 3. U1 median d, each rung and each low-SNR level

108 intervals: 3 architectures x {all, anthro, weather} x 4 low-SNR levels x
{R1, R2, R4}. Widths run from 0.00042 (`cm_all_snr-15_R4`, where d is pinned at
-0.998) to 0.5595 (`b1_anthro_snr-15_R1`, where R1 sits near zero and the sign
is genuinely uncertain).

**The registered ordering survives the intervals completely.**

| | |
|---|---|
| cells where median d falls R1 > R2 > R4 | **36 of 36** |
| cells where the 95% CIs separate R1 from R2 **and** R2 from R4, with no overlap | **36 of 36** |
| narrowest separating margin | 0.0199, `b3/anthro/snr-15`, between R2 and R4 |

This is strictly stronger than U1 asks for. The gate needs the ordering to hold
on point estimates in at least `min_levels` of the low-SNR levels; it holds in
every cell, and the intervals do not touch in any of them. The ladder is the
firmest result in the paper and the text should say so in these terms.

## 4. D_fsd nr_g and d_g, each architecture

The registered statistic is the median over the three fsd seeds of the per-seed
median, on MarVEN test rows at SNR <= 0. The bootstrap resamples base utterances
and recomputes that whole statistic, so the point estimate is the gate's own
number and not a pooled approximation of it. 3,285 rows and 864 base utterances
per architecture.

| arch | d_g | 95% CI | nr_g | 95% CI | registered class |
|---|---|---|---|---|---|
| B1 | -0.141 | [-0.210, -0.075] | 0.961 | [0.955, 0.969] | partial |
| B3 | -0.481 | [-0.512, -0.450] | 0.920 | [0.904, 0.931] | partial |
| CM | -0.214 | [-0.263, -0.173] | 0.951 | [0.944, 0.960] | partial |

Every d_g interval is strictly negative and every nr_g interval is far above
0.5, so `partial` is robust for all three: `diversity_explains` needs d_g > 0,
which no interval reaches, and `architecture_explains` needs nr_g < 0.3, which
no interval approaches. The headline "pooled d_g -0.14 to -0.48" is the range of
the three point estimates; the CI union is -0.075 to -0.512.

B1's interval is the widest of the three and comes closest to zero at -0.075.
That is the cell to quote if a reviewer asks how close the FSD50K models get to
balanced, and it is still clearly negative.

## For the paper, D8

1. Apply the four SI-SDR gap CIs, and say the four cells are not resolved from
   one another.
2. Correct 5.8 to 5.9 and 29 to 28, in the body and in the abstract.
3. State the U1 result as 36 of 36 cells with non-overlapping intervals. This is
   the strongest sentence available and it is currently not made.
4. Apply the six D_fsd CIs beside the per-architecture classes.
5. Label every one of them descriptive, in the text and in the post-hoc table.
