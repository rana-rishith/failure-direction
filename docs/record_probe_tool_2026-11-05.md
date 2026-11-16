# Record: the probe tool, and what it reproduces

2026-11-05. Covers the build of `src/probe/` and the verification run. No gate
verdict is changed by anything here.

## What was built

- `src/probe/__init__.py` — `probe()`, the energy split for one utterance, the
  bootstrap summary and the gate classes.
- `src/probe/__main__.py` — CLI.
- `src/probe/rescore.py` — loops every tag in the reference CSV, resumable.
- `configs/splits/marven_test_v1.json` — the frozen split.
- `tests/test_probe.py` — 6 tests.
- README gained a "The probe tool" section.

The metric is **not** redefined. `_ratios`, the level-aligned gain clamp `G_MIN`
/ `G_MAX` and the bin floor `K0` are imported from `src/diverse.py`, which
produced the numbers in `results/`. There is one energy split in this repo.

## Phase A decisions

The handoff asked for a new inert threshold, a new `r_add` and hp100 as the
primary column. All three are already fixed by `configs/gate_universal.yaml`
(`29c1566`, committed 2026-10-19), whose `U1_failure_class` has been scored and
reads PASS (all inert) in the paper. Changing them now would make every U-gate
post-hoc by the gate file's own rule.

So:

- **Inert threshold**: unchanged, `nr < 0.30` with `r_over_x` below its R1
  reference. The handoff's `nr_g < 0.3 and |d_g| < 0.2` was not adopted.
- **`r_add`**: unchanged, `sum(clamp(|Yhat| - |X|, 0)^2) / e_clean`, flagged at
  `>= 0.05`. The handoff's `||residual||^2 / ||error||^2` at `> 0.2` is a
  different quantity and was not adopted.
- **hp100**: computed for every ratio as a `_hp100` column and reported
  **alongside** the registered 62.5 Hz columns, not instead of them. `class` and
  `class_hp100` sit side by side so any disagreement is visible rather than
  resolved silently.
- **Oracle reference**: `delta_d` joins the existing oracle Wiener rows from
  `oracle_masks.py` (`results/metrics/review_oracle_masks_rows.csv`, all 2,280
  rows, computed 2026-10-16). Nothing was recomputed.

`active_balanced` is the one label with no gate behind it: it marks a cell that
matches none of the three gate classes. It is the tool's own and is named as
such in the README.

## The frozen split

`marven_test_v1` = the 2,280 manifest rows with `split == "test"`.

```
n       2280
sha256  73d68b28e52518a262f603cd76a056d4979c549faa774abfa35b66074b085ac4
```

The handoff specified "a fixed list of utterance IDs plus the mixing parameters
(noise offset, SNR, gain)". There are none to record: MarVEN ships pre-mixed and
the manifest carries `noisy_path` and `clean_path`, so the uid list *is* the
split. `load_split()` recomputes the checksum on every call and refuses to run
if the manifest moved.

## Verification

Reference: `results/xcorpus/eval/marven.csv`, 100,320 rows = 44 tags x 2,280.

| check | result |
| --- | --- |
| `probe()` vs reference, b1_weather, 100 rows, 11 metric columns | worst relative difference 9.9e-13 |
| all 44 tags, 5 utterances each | 44 match, 0 differ, worst 8.2e-13 |
| `tests/test_probe.py` | 6 passed |
| full suite `python -m pytest` | 65 passed |

8e-13 is float64 round-off. The tool reproduces the paper's numbers exactly.

Two reference files exist and agree with each other on shared uids:
`results/xcorpus/eval/marven.csv` (44 tags) and `results/diverse/*.csv` (9 tags).
`xcorpus` is the one the rescore targets, being the complete set.

## Tests

- **passthrough** `e = x`: `r_over == r_over_b4` and `r_under == r_under_b4` to
  1e-12, `nr == 0` exactly, `d < 0` on every row, `sisdr_gain == 0`.
- **constant gain** `e = 0.5x`: the plain basis charges it for over-suppression
  (`r_over > r_over_b4` on every row, `d` above passthrough's); the level-aligned
  basis makes it *identical* to passthrough to 1e-6 in `r_over_g`, `nr_g` and
  `d_g`. This is the test that the level alignment does what it claims.
- **oracle Wiener**, reconstructed through istft: median `d` > 0.5, and noise
  below the passthrough floor on every row. The stored mask-intent medians are
  0.83 (weather) and 0.89 (anthro); the output-STFT basis is not expected to
  match them exactly.

`nr_g` is **not** exactly zero at the passthrough floor. `g` for the noisy input
is only approximately 1 — noise correlates with speech a little, more so at low
SNR — and the level-aligned split divides by it. Measured offset over the first
20 rows is under 0.10. This is a property of the basis, not an error.

## Gotcha that cost real time

`FAILDIR_CKPT` was set in the inherited shell environment to
`%USERPROFILE%\failure-direction\ckpt`, which holds 12 checkpoints. The repo's
own `ckpt/` holds 199. Setting only `FAILDIR_ROOT` silently scored the wrong
weights, and the first verification run reported every tag as DIFFERING with
`g = 0.615` against a stored `g = 0.998`. Set both variables, every time; a
missing `FAILDIR_CKPT` fails by giving plausible wrong numbers, not by erroring.

## Two findings from the first scored model

SGMSE+ scored on its 400 available rows (see "Still open") turned up two things
that affect how the hp100 columns can be used in the paper.

1. **`nr_hp100` is degenerate for sub-100 Hz noise.** hurricane at SNR > 0 has
   `r_under_b4` = 1.7e-3 full-band and 1.4e-5 in the 100 Hz band, so the `nr`
   denominator collapses and single-utterance `nr_g_hp100` reaches -295. The
   cell median came out -2.42 against 0.89-0.99 everywhere else. `d_hp100` is
   fine, being a normalised difference. This is a direct argument against the
   handoff's "hp100 primary": it would have put a degenerate column in the
   headline for the weather types the paper is about.
2. **The gate classes cannot be computed for a zero-shot model.** `inert` and
   `over` are R4-versus-R1 contrasts within one model. SGMSE+, DFN3 and any
   sweep candidate have no R1 rows on MarVEN, so `probe()` returns
   `class = unknown`. The absolute `hallucinate` rule still applies. Classing
   zero-shot models needs a registered decision about the R1 substitute; the
   tool does not invent one.

## Audit of the first 16 rescored tags

All 16 complete: n = 2,280 each (sgmse 400, its coverage), a report written for
every one, 0.00% NaN across `d`/`d_g`/`nr`/`nr_g`/`r_add`/`delta_d`/`g`/
`sisdr_gain`, and zero rows hitting the `G_MIN`/`G_MAX` gain clamp. No flags.

Two things the audit makes precise.

**The hp100 denominator collapse is systematic, not an outlier.** Rows with
`nr_g_hp100 < -1` per tag: 6 to 134, worst on dfn3 (134) and b1_fsd (115-121).
Full-band `nr_g < -1` is far rarer, 0 to 41. So the degeneracy is a property of
the 100 Hz band across every model, not a quirk of one noise type. It is another
reason hp100 cannot be the primary column.

**`class = unknown` reaches models already in the paper, not just future
zero-shot ones.** `b1_demand`, `b1_fsd` and their seeds report `unknown` in all
12 cells, because a model trained on DEMAND or FSD noise heard no MarVEN type
and so has no R1 rows on this split to compare `r_over_x` against. That is the
whole diversity-control arm. It does **not** affect the paper: the registered
`D_diversity_control` verdict uses median `d` and `noise_removed`, not the U1
class rule. But it means the probe's `class` column is silent for that arm, and
the leaderboard cannot carry a class for any model that never saw MarVEN.

**Per-cell class is not the gate's class.** `U1_failure_class` is one label per
architecture, over `snr_low` rows at R4. The probe reports a label per noise type
x SNR band across the whole split, R1 and high-SNR cells included, so a single
model shows a mix: b1_weather comes out `active_balanced:5, over:5, inert:2`
while the registered verdict for the architecture is `inert`. These are different
aggregations of the same rows and neither overrides the other. The reconciliation
table must put the gate's architecture-level aggregate beside the registered
verdict, and keep the per-cell labels as the finer view underneath.

## Still open

- The 44-tag rescore through `probe()` is running. It is needed only for the new
  `_hp100` energy-split columns and `delta_d`; every other column is already
  proven bit-identical to `results/xcorpus/eval/marven.csv`.
- DFN3 and SGMSE+ are not among the 44 checkpoint tags. DFN3's 22,754 outputs in
  `dfn3_marven_out/` are named positionally, but `results/labels_active/rows_dfn.csv`
  maps each name to its noisy path and the path carries utterance key, noise type
  and SNR, so the uid is derivable without reconstructing row order. `probe()`
  takes a `wav_map` for this. Neither has been scored yet.
- Reconciling tool numbers against the registered verdicts waits on the rescore.

## Rescore complete: all 44 tags

- `python -m src.probe.rescore` finished exit 0 in 537.6 min, 44 tags, every one
  n=2280. Plus `dfn3` (2280) and `sgmse` (400, partial coverage) scored earlier:
  46 tag outputs under `results/probe/`.
- Audit over all 46: 0.00% NaN across d/d_g/nr/nr_g/r_add/delta_d/g/sisdr_gain,
  zero rows hitting the gain clamp [0.1, 10.0], every tag has summary.md. No flags.
  **Correction, 2026-11-16:** the clamp count was wrong. The stored `g` is below
  0.1 on 18 of the 103,000 rows (9 `dfn3`, 9 `sgmse`), and the largest `g` is
  2.614. The same correction applies to the 16-tag audit above.
- Per-tag cost: b3 ~6 min, b1/cm ~15-17 min.

## Reconciliation against the registered gates

Full table: `results/probe/reconciliation.md`. The probe reproduces each gate's
own aggregation from its own rows (same tags, same snr_low filter, same rung
labelling, same algebra), then adds the hp100 counterpart beside it. No verdict
was recomputed or changed.

- **U1_failure_class.** Probe matches the registered medians for b1, b3 and cm to
  all four printed digits (nr_R4, r_over_x_R4, r_over_x_R1, r_add_R4), n_R4=1095
  per architecture as registered. Class `inert` for all three, as registered.
- **hp100 changes no class.** On the 100 Hz band nr_R4 rises (b1 -0.0142 ->
  0.0324, b3 0.0190 -> 0.0837, cm 0.0290 -> 0.0690) and r_over_x_R4 falls, but
  every architecture stays `inert`: nr is still far under 0.30 and r_add_R4 still
  far under 0.05. So the handoff's "hp100 primary" proposal would not have moved
  the registered verdict even if it had been adopted.
- **D_diversity_control.** b1_demand on MarVEN at SNR <= 0 reproduces exactly
  (d_g -0.973, noise_removed 0.154 -> `architecture_explains`), and so do the
  b1_weather / b1_anthro comparison rows on both their heard and unseen halves.
  hp100 shifts noise_removed by at most 0.05 and changes no verdict.
- **Disagreements: none.** Nothing to explain away; the tool and the registered
  gates agree on the registered basis, and the two candidate sources of
  disagreement (hp100, r_add) both leave every verdict standing.

### Gates the probe does not speak to

- `U1_novelty_monotone` and `U2_beyond_bounded` are R1 > R2 > R4 contrasts. R2 is
  the unheard segment of a heard recording, which lives in the segment-window
  eval, not in the 2,280-row frozen split. The probe has no R2 rows and reports
  nothing against those two verdicts.
- `M0`/`M1` and `U3` are not direction-metric gates.
