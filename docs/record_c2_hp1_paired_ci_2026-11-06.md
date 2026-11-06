# Record C2: paired bootstrap CI for SGMSE+ H_P1

Task C2 of the 5 Nov work order. CPU only. **Post-hoc and descriptive.** The
registered verdict in `results/xcorpus/report2/H_P_sgmse.csv` is unchanged and
must stay unchanged.

## Result

| | |
|---|---|
| quantity | H_P1 = median $d_g$ on unseen corpora minus median $d_g$ on heard corpora |
| registered point estimate | **-0.2326** |
| 95% CI, paired cluster bootstrap | **[-0.3617, -0.0689]** |
| registered cutoff | $\lvert\Delta\rvert \ge 0.20$ |
| is the CI fully past the cutoff? | **no** |
| draws clearing the cutoff | **56.9%** |
| draws under 0.10, the `model_trait` band | 6.8% |
| draws in the inconclusive band | 36.3% |
| unit | 40 paired base utterances, 240 rows |
| resamples / seed | 10,000 / 1234 |

Output: `results/ci/hp1_paired_ci.csv`. Script: `scripts/bootstrap_ci.py --task hp1`.

## What this says, and what it does not

The registered classification is `shifts_with_novelty`, because
$\lvert-0.2326\rvert \ge 0.20$. The point estimate clears the cutoff by 0.033.

The interval does not. Resampling the 40 base utterances puts 56.9% of draws
past the cutoff, 36.3% in the inconclusive band between 0.10 and 0.20, and 6.8%
in the `model_trait` band. So the data supports the registered class but holds it
loosely: a little over half of the resamples would reproduce it.

**This does not reopen the gate.** The rule was registered against a point
estimate and the point estimate is what it gets. The CI is reported because a
reader is entitled to know that the margin is 0.033 on 40 base rows, and because
stating it is cheaper than being asked.

## Method

The unit is the base utterance, not the row. Each of the 40 base rows carries all
six `PAIRED` conditions: two heard (`dem_A`, `dem_H`) and four unseen
(`marven`, `deepship_ship`, `mbari_storm`, `mbari_dry`).

The bootstrap is paired in the strict sense: **one draw of base utterances is
applied to both sides.** A base enters or leaves a resample with all six of its
conditions at once, so the two medians move together and the interval carries
only between-base variation. Resampling the two sides independently would
inflate the width by treating the heard and unseen measurements of one utterance
as unrelated.

`src.probe.bootstrap_ci` was not reused: it takes a cluster bootstrap of one
median over one value column, and H_P1 is a difference of two medians over
disjoint subsets of the same resampled bases, which that signature cannot
express. The draw loop in `scripts/bootstrap_ci.py` is shared with C1 instead.

## Self-check

The script asserts that its own point estimate reproduces
`results/xcorpus/report2/H_P_sgmse.csv` to within 1e-9 before it reports an
interval. It does: -0.23264907954609557 both ways. If the filter, the condition
lists or the `_derive` algebra ever drift, the script fails rather than
publishing an interval around a different quantity. Two consecutive runs gave
identical output, so the seeding is deterministic.

## For the paper

One sentence, in the H_P section, labelled post-hoc:

> A paired bootstrap over the 40 base utterances (10,000 resamples, descriptive,
> not part of the registered rule) puts the 95% interval for H\_P1 at
> $[-0.36, -0.07]$. The registered point estimate of $-0.233$ clears the 0.20
> cutoff by 0.033, and 57% of resamples clear it, so the `shifts_with_novelty`
> class is supported but not firmly separated from the inconclusive band.

Do not place this in the registered gate table. It belongs in the post-hoc table
with `post_hoc: true`, which the CSV already records.
