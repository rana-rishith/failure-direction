# Record: G1, G2 and G3 persisted, and the G2 numbers the paper prints are pre-DC

Follows recommendation 1 of `docs/record_gate_inventory_2026-11-05.md`, which
found these three gates to be the one real hole in the ledger: computed, cited
in the paper, and not on disk anywhere.

Resolved by running `python -m src.analysis`. No new logic was written. The run
is pure pandas over `results/eval/*.csv`, takes seconds, needs no GPU, and
overwrote nothing: all ten of its output paths were absent and untracked.

## Now on disk

| file | holds |
|---|---|
| `results/metrics/gate_results.yaml` | all three verdicts, thresholds, numbers and notes |
| `results/metrics/gate_g1_dir_idx_by_noise_split.csv` | G1 per noise type and split |
| `results/metrics/gate_g2_magnitude.csv` | G2 mean and median per split |
| `results/metrics/gate_g3_overlap_by_snr.csv` | G3 overlap counts per SNR |

B1's table generator can now read all three instead of skipping them, which was
the reason this was blocking.

## The verdicts

| gate | threshold | statistic | verdict |
|---|---|---|---|
| G1 direction spread | 0.30 | pooled spread **0.1608** | **FAIL** |
| G2 magnitude gap | 0.10 | median gap **0.206** | **PASS** |
| G3 WER asymmetry | 0.05 | collinearity **0.9952** | **UNTESTABLE** |

No verdict changed from what the paper claims. G1 still fails, G2 still passes,
G3 still cannot be tested.

## But three G2 numbers did change

`src.metrics.add_ratios` builds `r_over` and `r_under` from `e_over / e_clean`,
the DC-excluded canonical columns. The `_full` columns hold the old pre-fix
definition. So this run is post-DC, and the paper's G2 figures are not. The
README said as much at line 614, "Gates (pre-DC, not yet recomputed)", and the
recomputation had never happened.

| quantity | paper prints | post-DC | source |
|---|---|---|---|
| matched median magnitude | 0.0347 | **0.0240** | `paper.tex:930` |
| unseen median magnitude | 0.3223 | **0.2304** | `paper.tex:930` |
| G2 median gap | 0.288 | **0.206** | `paper.tex:613` and `:930` |

The verdict is unaffected: 0.206 still clears the 0.10 threshold by a wide
margin. Only the printed values move, and they move down.

Do **not** touch `paper.tex:1265`. Its 0.288 is a Spearman rho in the U3
predictor section and has nothing to do with G2.

## G1 and G3, for the text

G1 fails at 0.1608 against 0.30, and the gate's own note records why that is the
wrong question: it tests whether direction varies across **noise types**, while
the hypothesis was that **seen** conditions fail differently from **unseen**
ones. Split-conditioned, the separation is stark:

| noise type | matched | unseen |
|---|---|---|
| bubble_curtain | 0.675 | -0.925 |
| hurricane | 0.618 | -0.801 |
| large_commercial_ship | 0.737 | -0.666 |
| lightning | 0.709 | -0.686 |
| rainfall | 0.644 | -0.743 |

Within-split spread is 0.119 matched and 0.259 unseen, both under the 0.30 bar,
while the matched-to-unseen separation is **1.284**. That separation is
**post-hoc** and the gate's note says to flag it as such every time. Report the
failure as specified first.

G3's collinearity is 0.9952: only 11 of 2,280 matched rows have a negative
direction index. Usable overlap exists only at +15 and +20 dB, where the
absolute failures are too small for a 0.05 WER threshold to mean anything.

That 11 of 2,280 is the same count C5 confirmed independently for B1 matched
rows with d < 0, from a different code path. The two agree.

## Still open

Recommendation 2 of the inventory is untouched: whether `confound` and `segment`
are ledger rows at all. Both are controls with per-cell CSVs and no summary
verdict, and their gate text gives a protocol rather than a threshold. B1 needs
an answer only to decide whether they get rows.

## Disclosure that must survive into the paper

`src/analysis.py` prints this on every run and `configs/gate.yaml:3-7` records
it:

> G1's index formula and G2's definition of "mean magnitude" were operationalised
> AFTER Claims 1 and 2 had been observed, because `gate.yaml` left them
> unspecified.

The thresholds were fixed beforehand; the operationalisations were not. This
belongs in D4 beside the pre-registration wording, not buried in a config
comment.
