# Audit A1: the registered basis and verdict of `D_diversity_control`

2026-11-05. No verdict file was changed. No yaml was edited.

## Question

The 5 Nov handoff carries `architecture_explains` for `D_diversity_control`. The plain
basis gives median d -0.894 and noise_removed 0.585 for `b1_demand`, which is neither
class. Which reading is the registered one.

## Answer

**The registered verdict is `partial`.** `architecture_explains` is the level-aligned
reading. It is a registered verdict, but of a different gate, `H_D2_demand_seeds`.

## What the rule says

`configs/gate_universal.yaml:99`, commit `29c1566`, 2026-10-19 11:24:59.

```
D_diversity_control:
  model: "b1_demand: SpectralMask, 20,000 steps, bs 8, lr 2e-4, 4 s crops, seed 1234, ..."
  data:  "MarVEN test split (all five types unseen), SNR <= 0 dB, output-STFT basis"
  verdict:
    diversity_explains:    "median d > 0 AND median noise_removed >= 0.5"
    architecture_explains: "median d < 0 AND median noise_removed < 0.3"
    otherwise:             "mixed; reported as partial"
```

Two things to read carefully.

1. The unit is **one model**, `b1_demand`, not an architecture family.
2. `data` names the **output-STFT** basis. That is the choice between output STFT and
   mask intent. It is not the choice between plain and level-aligned. The rule is silent
   on plain against level-aligned, and the statistic it names is `d`, not `d_g`.

## Why plain is the registered basis

Two later config files settle it, and both point the same way.

`configs/gate_amend_level.yaml`, commit `09ca3bd`, 2026-10-19 16:25:48:

```
basis_for_judgement: "U1_failure_class and U2 use the level-aligned split for all architectures"
unchanged: "... D2_distance and D_diversity_control involve bounded masks only (g ~ 1)
            and stand as run."
```

The amendment names the two gates that move to the level-aligned split, and
`D_diversity_control` is not one of them. It is named in the `unchanged` block.

`configs/gate_amend_level_correction.yaml`, commit `59fe447`, 2026-10-19 17:10:34, calls
the plain results registered in its own words: consequences are "reported as sensitivity
analyses next to the registered plain-split results".

## The numbers

Source: `results/xcorpus/report2/D_per_seed.csv`. The `cls` column in that file was
computed on the level-aligned basis for every row, demand rows included.

| tag | d_plain | nr_plain | plain class | d_g | nr_g | level-aligned class |
|---|---|---|---|---|---|---|
| b1_demand | -0.8937 | 0.5851 | **partial** | -0.9735 | 0.1542 | architecture_explains |
| b1_demand_s2 | -0.9103 | 0.6279 | **partial** | -0.9786 | 0.1044 | architecture_explains |
| b1_demand_s3 | -0.8837 | 0.6111 | **partial** | -0.9736 | 0.1862 | architecture_explains |
| b3_demand | -0.9664 | 0.2972 | architecture_explains | -0.9851 | 0.0400 | architecture_explains |
| b3_demand_s2 | -0.9728 | 0.1998 | architecture_explains | -0.9858 | 0.0515 | architecture_explains |
| b3_demand_s3 | -0.9758 | 0.1959 | architecture_explains | -0.9872 | 0.0446 | architecture_explains |
| cm_demand | -0.9990 | -2.9398 | architecture_explains | -0.9805 | 0.0608 | architecture_explains |
| cm_demand_s2 | -0.9991 | -2.7925 | architecture_explains | -0.9852 | 0.0648 | architecture_explains |
| cm_demand_s3 | -0.9989 | -2.3205 | architecture_explains | -0.9824 | 0.1629 | architecture_explains |

The registered unit is `b1_demand`, the first row: d < 0 fails
`diversity_explains`, and nr 0.5851 is not under 0.3, so `architecture_explains` fails
too. The rule falls through to `otherwise`, which is `partial`.

The `b3` and `cm` rows reach `architecture_explains` on the plain basis as well, but they
are not the registered unit, and `cm`'s plain `nr` of -2.94 is the exact pathology that
`gate_amend_level.yaml` was written to fix.

## The amendment's premise for this gate was wrong

`gate_amend_level.yaml` left `D_diversity_control` on the plain basis because the gate
"involve[s] bounded masks only (g ~ 1)". The correction file withdraws that premise:

> at SNR <= 0 dB, g is 0.78-0.98 for B1/B3, and as low as 0.57 for b1_weather on
> matched noise at -15 dB

and, for this exact model:

> for b1_demand on ship, lightning and rainfall the plain "noise removed" of 49-64%
> falls to -18..+25%, so that partial transfer was mostly the model turning the level
> down (g 0.67-0.76), not spectral suppression

So the registered `partial` rests on a noise_removed of 0.5851 that the correction shows
is mostly a level drop. The honest report is `partial` as registered, with the
level-aligned reading beside it and the correction quoted. Not a basis change.

## `architecture_explains` has its own registration

`configs/gate_overnight2.yaml`, commit `47f18bf`, 2026-10-20 04:37:31, sha256[:12]
`cc501b4c349c`:

```
metric: "src.diverse.analyse, level-aligned split (nr_g, d_g) primary for every gate below"
H_D2_demand_seeds:
  statistic: "gate-D class (rule above) of each demand seed (1234, 2, 3), per architecture"
  verdict:   "'stable' if all available seeds share the class, else 'seed_sensitive'"
```

That file registers the level-aligned basis for every gate it declares, before it ran.
Its verdict, from `results/xcorpus/report2/H_D2.csv`, is `stable` for b1, b3 and cm, with
the shared class `architecture_explains`.

So both readings are pre-registered. They belong to different gates and must be reported
under different gate ids.

## What the paper must say

- `D_diversity_control`: **partial**, plain basis, unit `b1_demand`, d -0.894,
  noise_removed 0.585.
- `H_D2_demand_seeds`: **stable**, level-aligned basis, class `architecture_explains`,
  3 of 3 seeds for each of b1, b3 and cm.
- Beside the first, the correction's finding that b1_demand's plain noise_removed is
  mostly a level drop.
- `D_fsd` is a third gate, also level-aligned by `gate_overnight2.yaml`'s `metric` line,
  and its verdict is `partial`.

Any sentence that gives `architecture_explains` as the verdict of `D_diversity_control`
is reporting the wrong gate id.

## Provenance

| item | value |
|---|---|
| `configs/gate_universal.yaml` | sha256[:12] `a13d0d71f9e6`, commit `4ba32aa` 2026-10-19 11:27:05 |
| same, at pre-commitment | sha256[:12] `96011c2ca941`, commit `29c1566` 2026-10-19 11:24:59 |
| `configs/gate_amend_level.yaml` | sha256[:12] `51d4cf35090b`, commit `09ca3bd` 2026-10-19 16:25:48 |
| `configs/gate_amend_level_correction.yaml` | sha256[:12] `e00f355806e3`, commit `59fe447` 2026-10-19 17:10:34 |
| `configs/gate_overnight2.yaml` | sha256[:12] `cc501b4c349c`, commit `47f18bf` 2026-10-20 04:37:31 |
| numbers | `results/xcorpus/report2/D_per_seed.csv`, `H_D2.csv` |

The published hash `a13d0d71f9e6` is the `4ba32aa` version, two minutes after the
pre-commitment. The only difference from `29c1566` is the two `provenance` lines being
filled in. `git diff 29c1566 HEAD -- configs/gate_universal.yaml` shows no other change,
so no threshold moved. The paper should cite `29c1566` for the pre-commitment and
`4ba32aa` for the hash, and say why they differ.
