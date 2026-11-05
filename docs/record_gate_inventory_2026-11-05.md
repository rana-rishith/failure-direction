# Audit A4: every declared gate and where its verdict lives

2026-11-05. Nothing was recomputed. No yaml was edited and no verdict changed.

## The headline

**26 declared gates across 16 yaml files. 7 have a machine-readable verdict.**

The rest have their verdict in a markdown report or a CSV column. Three have it
nowhere on disk. That decides how the ledger table can be built:
`scripts/make_gate_tables.py` cannot read every verdict from a verdict file,
because for most gates there is no such file.

## The gate files

| yaml | commit | committed | sha256[:12] |
|---|---|---|---|
| `configs/gate.yaml` | `0084394` | 2026-10-16 20:28 | `3fb113d537ee` |
| `configs/gate_universal.yaml` | `4ba32aa` | 2026-10-19 11:27 | `a13d0d71f9e6` |
| `configs/gate_pilot_level.yaml` | `d063a17` | 2026-10-19 12:35 | `02d8f4872320` |
| `configs/gate_r3.yaml` | `2976373` | 2026-10-19 12:42 | `6e9767e5665c` |
| `configs/gate_overnight.yaml` | `3acde60` | 2026-10-19 13:02 | `cf5a9b141818` |
| `configs/gate_distance.yaml` | `d15040a` | 2026-10-19 13:07 | `f9a259ff9d58` |
| `configs/gate_stationarity.yaml` | `d1668b2` | 2026-10-19 13:15 | `089facd7c373` |
| `configs/gate_amend_cm.yaml` | `9dccace` | 2026-10-19 13:24 | `85f3ef3e8df0` |
| `configs/gate_amend_level.yaml` | `09ca3bd` | 2026-10-19 16:25 | `51d4cf35090b` |
| `configs/gate_amend_level_correction.yaml` | `59fe447` | 2026-10-19 17:10 | `e00f355806e3` |
| `configs/gate_claim3_level.yaml` | `e9f6b92` | 2026-10-19 17:19 | `48ae481d7785` |
| `configs/gate_overnight2.yaml` | `47f18bf` | 2026-10-20 04:37 | `cc501b4c349c` |
| `configs/gate_xn2_sgmse_ext.yaml` | `ab5cd02` | 2026-10-21 23:08 | `f993f26e88a5` |
| `configs/gate_claim3_active.yaml` | `5923dda` | 2026-10-26 02:24 | `ee8d58e978d1` |
| `configs/gate_claim3b.yaml` | `3708f98` | 2026-10-26 12:07 | `0206bccecf4b` |
| `configs/gate_claim3c.yaml` | `fe42ce7` | 2026-10-26 17:24 | `8ea11be67ff5` |

Four of these declare no gate. `gate_amend_cm`, `gate_amend_level`,
`gate_amend_level_correction` are amendments to how an existing gate is measured,
and `gate_overnight` is a run order for gate XN. They belong in the ledger as
provenance, not as rows.

## The inventory

`reg` = registered before it ran. `post` = post-hoc, labelled as such in its own
verdict file. Verdict hashes are sha256[:12] of the file named.

| gate | yaml | verdict | verdict file | hash | kind |
|---|---|---|---|---|---|
| `G1` direction spread | gate | **not on disk** | `src.analysis.gates()` prints it | — | reg |
| `G2` magnitude gap | gate | **not on disk** | `src.analysis.gates()` prints it | — | reg |
| `G3` WER asymmetry | gate | **not on disk** | `src.analysis.gates()` prints it | — | reg |
| `confound` | gate | per-cell only | `results/confound/*.csv` | — | reg |
| `segment` | gate | per-cell only | `results/segment/*__windows.csv` | — | reg |
| `M0_oracle_headroom` | universal | FAIL, 4 of 4 cells | `results/method/m0_summary.csv` | `777aa874a3de` | reg |
| `M1_predicted_gamma` | universal | not run, blocked by M0 | none | — | reg |
| `U1_novelty_monotone` | universal | PASS | `results/universal/u1_verdict.json` | `1d8aad957c32` | reg |
| `U1_failure_class` | universal | PASS, all inert | `results/universal/u1class_verdict.json` | `5baa64756779` | reg |
| `U2_beyond_bounded` | universal | PASS, 2 of 3; generative pending | `results/universal/u2_verdict.json` | `8c190a0d475c` | reg |
| `U3_within_condition` | universal | FAIL | `results/universal/u3_verdict.json` | `fc238bf90ad8` | reg |
| `U3_transfer` | universal | FAIL, 2 of 5 | `results/universal/u3_transfer_verdict.json` | `249292ba907f` | reg |
| `D_diversity_control` | universal | **partial** (plain basis, b1_demand) | `results/xcorpus/report2/D_per_seed.csv` | `e34b958d8be3` | reg |
| `pilot_level` | pilot_level | dfn3 `survives`, sgmse `partly_level` | `results/pilot_level/verdict.csv` | `526f729e555f` | reg |
| `r3` | r3 | `intermediate`, 9 of 9 | `results/r3/report.md` | `60780ff2c735` | reg |
| `D2_distance` | distance | FAIL, rho -0.095 | `results/distance/summary.csv` | `a52feb7fc8c6` | reg |
| `S_stationarity` | stationarity | FAIL, rho -0.083 | `results/stationarity/summary_full.csv` | `aab63eefa397` | reg |
| `C3_level_recheck` | claim3_level | PASS, all 3 targets, both folds | `results/claim3_level/verdict.csv` | `dadcf943fec1` | reg |
| `D_fsd` | overnight2 | partial | `results/xcorpus/report2/report.md:25` | `577b95645bbd` | reg |
| `H_FD_widening` | overnight2 | widens | same report `:41` | `577b95645bbd` | reg |
| `H_D2_demand_seeds` | overnight2 | stable (`architecture_explains`) | `results/xcorpus/report2/H_D2.csv` | `0800ee50a38d` | reg |
| `H_F_family_fresh` | overnight2 | not_family_specific, E >= 0.10 in 0 of 9 | same report `:48` | `577b95645bbd` | reg |
| `C1_lowcut` | overnight2 | sub100_dependent | same report `:61` | `577b95645bbd` | reg |
| `H_P_final` dfn3 | overnight2 | H_P1 model_trait (-0.088), H_P2 model_trait | same report `:71` | `577b95645bbd` | reg |
| `H_P_final` sgmse | overnight2 | H_P1 shifts_with_novelty (-0.233), H_P2 model_trait | same report `:91` | `577b95645bbd` | reg |
| `sgmse_extension` | xn2_sgmse_ext | the 40 paired base rows behind H_P_final sgmse | same report `:91` | `577b95645bbd` | reg |
| `C3_active` | claim3_active | FAILS | `results/claim3_active/report.md` | `5378a4d52fa3` | reg |
| `C3b` | claim3b | FAILS | `results/claim3b/heldout/report.md` | `78ea95c3ee3e` | reg |
| `C3c` | claim3c | HOLDS | `results/claim3c/heldout/report.md` | `13d927443116` | reg |
| `H_S1` seed robustness | overnight | 6 of 6, same sign | `results/xcorpus/report/report.md:3` | `61798fa069e4` | reg |
| `H_S2` R3 across seeds | overnight | intermediate, 9 runs | same report `:13` | `61798fa069e4` | reg |
| `u3_sens_canonical_lgbm` | universal | FAIL | `results/universal/u3_sens_canonical_lgbm_verdict.json` | `9a759386782d` | **post** |
| `u3_transfer_sens_feats45` | universal | FAIL, 2 of 5 | `results/universal/u3_transfer_sens_feats45_verdict.json` | `ca2c6d297e06` | **post** |

## Gates with no verdict, and why

**`G1`, `G2`, `G3`.** `src/analysis.py:125-181` computes all three from
`results/metrics/*.csv` and prints them. Nothing is persisted, and
`results/metrics/` holds no gate file. So the verdicts exist in a scrollback
buffer and in whatever the paper says. This is the one real hole in the ledger:
the three earliest gates cannot be cited to a file. Fixing it is cheap, since
`gates()` already returns a dict. It needs a run and a written output, not new
logic.

**`confound` and `segment`.** Both are controls with per-cell CSVs and no
summary verdict. The gate text gives a protocol rather than a threshold, so
"verdict" may be the wrong frame for them. Decide whether they are ledger rows
at all.

**`C3_level_recheck` is not silent and deserves more prominence than it has.**
`results/claim3_level/verdict.csv` carries all six rows, `pass=True` on every
one. Its PRIMARY target is the level-aligned one, and it holds: feats_only
reaches mean within-SNR rho 0.719 on weather against a baseline of 0.152, and
0.725 on anthro against 0.388, winning 8 of 8 SNR strata and 92% / 94% of cells
in both folds. So the registered `on_fail`, which would have made the paper say
Claim 3 predicts the recoverable level drop rather than irreversible speech
loss, does not fire. Given that `gate_amend_level_correction.yaml` shows how much
of the plain-split effect is level, this gate is the direct answer to the
obvious reviewer objection against Claim 3, and it is worth a named paragraph.

**`M1_predicted_gamma`.** Correctly not run: M0 failed 4 of 4 and M1 depends on
it. The ledger row is "not run, blocked by M0" and that is a complete outcome.

**`U2`'s generative class.** Pending the SGMSE+ fine-tune. The U2 verdict file
already records it under `classes_missing`, so the gate is reported; only the
third class is open.

## What this means for the table generator

`docs/paper_draft_route.md` says to generate `tab:gates` from the verdict JSONs
rather than typing it. That works for 7 rows out of 33. For the rest the
generator has to read a markdown heading or a CSV column, which is parsing prose
again, the same fragility `_after` already has.

The cheaper and more honest option: keep this file as the single typed source,
with the hashes above pinning every cited file, and have the generator emit the
7 JSON rows automatically and read the rest from a small table in this
repository rather than from 12 different report formats. The alternative, giving
every gate a verdict JSON retrospectively, means re-running gates whose code has
moved since, which risks changing a published number to tidy a table.

Recommended before the generator is written:

1. Persist `G1`, `G2`, `G3` by writing what `src.analysis.gates()` already
   returns. One run, no new logic.
2. Decide whether `confound` and `segment` are gates or controls.
