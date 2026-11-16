# Claims

These tables were moved from the README. They use the gate names of the yaml
files. The README gate table gives the name that the paper uses for each gate.

## What we claim

Each line is a registered gate that passed. Thresholds live in `configs/`.

| Claim | Gate | Evidence |
|---|---|---|
| Enhancement degrades measurably on unseen noise | `G2` PASS | median direction-free magnitude gap 0.206, threshold 0.10 |
| The failure direction falls monotonically along the novelty ladder: heard samples, then unheard segment of a heard recording, then unseen type | `U1_novelty_monotone` PASS | holds for all three bounded-mask architectures |
| On an unseen noise type every architecture lands in the same failure class, **inert** | `U1_failure_class` PASS | B1, B3 and CM all inert |
| That behaviour is not an artefact of bounded masks | `U2_beyond_bounded` PASS | 3 of 3 non-bounded classes, the generative one included |
| Training-noise diversity moves the direction | `D_fsd` partial (3 of 3) | FSD50K-trained models remove 0.92 to 0.96 of the noise excess |
| A narrow, weather-only form of the pre-hoc predictor replicates on fresh seeds | `C3c` HOLDS (6 of 6), `C3_level_recheck` PASS (6 of 6) | registered after it held on 15 earlier models |
| The ladder result survives an unheard *recording* of a heard type | `r3` intermediate | 9 of 9 runs |

## What we do not claim

These gates failed, were untestable, or were never run. They are listed because
a registered ledger that only reports its successes is not a ledger.

| Not claimed | Gate | Why |
|---|---|---|
| That failure direction separates the five noise types | `G1` **FAIL** | spread 0.1608, threshold 0.30 |
| Any downstream word-error-rate asymmetry | `G3` **UNTESTABLE** | direction and condition are collinear at 0.995; only 11 of 2,280 matched rows carry a negative *d* |
| A general reference-free predictor of speech loss | `U3_within_condition` **FAIL**, `U3_transfer` **FAIL** | both post-hoc sensitivity arms fail too |
| Any mechanism behind the direction | `M0_oracle_headroom` **FAIL** | best oracle gain 0.169 dB over 4 cells; `M1` was blocked by `M0` and never run |
| That the pre-hoc predictor generalizes across noise families | `C3_active` **FAILS**, `C3b` **FAILS** | 1 of 3 FSD architectures passed both folds |
| That distance or stationarity explains the direction | `D2_distance` **FAIL**, `S_stationarity` **FAIL** | rho -0.095 and -0.083 |
| That the effect is specific to one noise family | `H_F_family_fresh` not family-specific | 0 of 9 pairs |
| That the Claim 1 weather gap is full-band | `C1_lowcut` sub-100 Hz dependent | 3 of 6 cells at or above 0.75 of the full-band gap |
| Anything about unseen noise **families** | LOTO control | "unseen" here means an unseen noise *recording*; the data cannot support the family claim |

**Withdrawn.** An earlier result claimed B3 destroys about 40% of clean speech
energy in a few concentrated bins while SI-SDR and STOI look fine. Those files
were DC-heavy and the mask was removing an offset nobody could hear. That
result, and the mechanism built on it, are withdrawn.
