# Paper draft route

Written 2026-10-28. Target IEEE/ACM TASLP. Context in
`docs/handoff_paper_phase_2026-10-28.md`.

---

## The contribution, in the order it should be sold

1. **The pre-registered gate ledger.** Thresholds committed `29c1566` on 2026-10-19
   before the data existed, every gate reported including the failures, provenance hashes
   on each verdict. Rare in speech enhancement, and it is what makes the negatives
   publishable rather than embarrassing.
2. **The four-rung novelty ladder**, especially the disjoint within-recording segment
   control at R2. A protocol other people can reuse.
3. **The direction measure**, plus the finding that the ranking it produces is 0.79 to
   0.98 architecture-independent.

There is no method contribution. M0 closed it with data. Do not reopen it.

## Two principles that decide most drafting questions

**Every declared gate gets a reported outcome.** You are publishing the config file, so
the ledger must be complete. "Not run, because X" is a valid outcome; silence is not.

**Pre-registered and post-hoc never share a table.** Post-hoc variants live in their own
files with `post_hoc: true` and are labelled as such in the text, every time.

---

## Phase 0: close the ledger (runs in parallel with Phase 1)

GPU and CPU work that needs no decisions from you. Start it, then draft while it runs.

| Item | Why | Cost |
|---|---|---|
| **SGMSE+**, U2's `generative` class | Removes the "2 of 3 classes" caveat from every U2 sentence. `sgmse` env exists. Yaml allows zero-shot if the fine-tune fails its smoke test. | GPU, hours |
| **R3 rung** in U1 | The yaml defines it and the runner says "not in this stage". Takes the ladder from 3 rungs to 4, which is the actual shape of the claim. Check first whether DEMAND's held-out recordings are separable in the eval CSVs; if so it needs no training. | low if no training |
| **`U3_transfer`** | Declared, unrun, unreported. Asks a looser question than the U3 that failed (within-SNR rho on a held-out type), where the features reach 0.42 to 0.44, so it can pass. A pre-registered pass beside a pre-registered fail is a better ledger than a gap. | CPU, low |
| **Round-2 pre-registration** | Needed before the burst-feature variant below. New gate file, own commit, thresholds written *before* anything runs. | one commit |
| **Burst-feature U3 variant** | U3 used 33 features; claim 3's winners use 45 and `bst_sub150` is the top-split feature. Answers "are the features wrong or is the task impossible". Must be a round-2 gate, never the same gate id. | CPU, low |

If time runs short, the burst-feature variant is the one to keep. It closes the hole a
reviewer will point at first.

---

## Phase 1: draft, in dependency order

Write the settled parts first and the framing last. The framing changes once the
sections exist; writing the intro early guarantees rewriting it.

**Round 1, settled material, no decisions needed**

1. `04_measure.tex` — the energy split, the bases, the `_g` level alignment.
2. `03_data.tex` — MarVEN, DEMAND, FSD50K, the folds.
3. `05_models.tex` — B1, B3, cm, DFN3, SGMSE+, equal-compute protocol (20,000 steps,
   batch 8, lr 2e-4, seed 1234). Record the two DFN3 deviations here: final-step weights
   rather than best-val, and the 48 kHz loss through `df.loss.Istft` rather than the
   non-differentiable Rust synthesis, with the 73 to 74 dB self-check.
4. `06_protocol.tex` — the rung ladder, the segment control, and the pre-registration
   mechanism. **This section carries contribution 1**, so give it the space.

**Round 2, the claims**

5. `07_claim1.tex`, `08_claim2.tex` — settled.
6. `09_claim3.tex` — the three-stage chain, C3c holds, bubble curtain fails.
7. `10_diversity.tex` — `D_diversity_control`.
8. **New: the U-gate section.** U1, U1-class, U2, U3 and whatever Phase 0 adds. This
   does not exist yet and is the largest new writing job.

**Round 3, framing**

9. `11_discussion.tex` — the negatives, in full. ΔWER unsupported, routing negative
   (15.94 against 16.32 at k=5), bubble curtain unpredicted, M0 no headroom. Then the
   U3 reliability result as the thing that makes the U3 failure interpretable.
10. `12_conclusion.tex`, then `01_intro.tex`, then `02_related.tex`, then the abstract.

---

## The gate ledger table

Build `tab:gates` early, before the prose, because every claims section refers to it and
it is the artifact a reviewer will check against the config file. One row per gate:

`gate id | pre-registered criterion | verdict | where reported | config commit | yaml sha`

Generate it from the verdict JSONs rather than typing it. Include M1 with "blocked by
M0" and every Phase 0 outcome. A row with no verdict is the thing to fix before
submission.

---

## How to write U3

The temptation is to bury it. Do the opposite; it is the most defensible part of the
paper.

The sequence that works:

1. U3 as pre-registered: FAIL. MarVEN 0.105 against ridge 0.091, win fraction 0.45
   against a required 0.75.
2. The fitter is not the cause: `u3_sens_canonical_lgbm`, slightly worse at 0.091.
   Labelled post-hoc.
3. The target is not noise: within-cell agreement 0.884 across seeds and 0.791 across
   architectures. The gate was winnable and was not won.
4. If the burst-feature round-2 variant closes the gap, that is where the information
   lives. If it does not, within-condition ranking is hard even with the features that
   work across conditions.
5. The honest limit, stated plainly: the replica agreement bounds from above only.
   `r_over_x` is defined against the clean signal, so part of the reproducible component
   may rest on clean-speech properties that no reference-free feature can observe. A
   high ceiling does not say the features ought to have reached it.

That last point is what separates this from hand-waving. Keep it.

---

## Figures

- `fig_pipeline` — where the clean reference enters, already planned in `01_intro.tex`.
- The rung ladder as a schematic, with the A/B timeline split drawn. Contribution 2
  needs a picture or nobody will reuse it.
- Median `d` by rung by SNR, per architecture class. This is U1 and U2 in one panel.
- U3: measured rho against the reliability ceiling, per corpus. One panel, and it makes
  the whole U3 argument visible at a glance.

---

## Mechanics

- `paper/*.tex` stays untracked and local. Never commit or push it.
- Numbers in the text come from the committed CSVs and verdict JSONs, cited by path, as
  the existing `\src{}` plan macros already do. Do not retype a number you can cite.
- Before submission, re-read every `\plan{}` block and delete it once its prose exists.
  A stray `\plan{}` in a submitted PDF is the kind of thing that happens.
