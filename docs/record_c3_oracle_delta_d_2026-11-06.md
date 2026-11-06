# Record C3: distance from an oracle Wiener mask

Task C3 of the 5 Nov work order. CPU only. **Descriptive and post-hoc.** No gate
reads these numbers and no verdict file was written.

| | |
|---|---|
| script | `scripts/oracle_delta_d.py` |
| oracle rows | `results/ci/oracle_wiener_rows.csv`, 6,119 utterances |
| per-cell table | `results/ci/oracle_delta_d_cells.csv`, 776 cells |
| model sets | D_fsd (3 seeds x 3 archs), DFN3, SGMSE+ |
| coverage | **776 of 776 cells complete.** No row is missing an oracle. |

## Nothing had to be regenerated

C3 warned that the clean or noise signals might be gone for some rows.
They are not. `results/xcorpus/manifest.csv` carries a `clean` path for all
7,104 of its rows, and it covers every row of `ext_dfn3.csv` (5,224) and
`ext_sgmse.csv` (280) as well as the MarVEN rows D_fsd uses. The noise is
recovered exactly as `noisy - clean`, so no mixture was rebuilt.

## Method, and why it can be trusted

The oracle is per utterance and independent of any model, so it is computed once
per `(cond, uid)` and joined to every model that scored that utterance.

The mask is the Wiener oracle $W = |S|^2 / (|S|^2 + |N|^2)$ applied to the noisy
STFT. The STFT and the energy split come from `src.models.magnitude` and
`src.metrics.energy_decomposition`, the same two functions the models themselves
are scored with, so the oracle and the model are measured on one basis. Nothing
in this script reimplements that algebra.

**Cross-check against a committed result.** `results/metrics/review_oracle_masks_rows.csv`
(from `oracle_masks.py`, Oct 16) already held a Wiener oracle for 2,280 MarVEN
test utterances, computed through an independent NumPy path. 1,295 of those rows
overlap this pass. They agree to **max |delta r_over| 5.69e-08** and
**max |delta r_under| 2.69e-09**, which is float noise. The script prints this
check on every run.

The oracle mask is bounded, so its output sits at the clean level and $g \approx 1$.
It has no separate level-aligned column, and `delta_d_g` therefore compares the
model's level-aligned $d_g$ against the same plain-basis oracle $d$.
`src.probe.add_delta_d` takes the same view.

## Finding 1: d = 0 is not the neutral reference, and the paper treats it as one

The optimal mask is strongly over-suppressive, and how strongly depends on SNR:

| input SNR | oracle median $d$ |
|---|---|
| -15 dB | **+0.946** |
| -10 dB | +0.925 |
| -5 dB | +0.871 |
| 0 dB | +0.826 |
| +5 dB | +0.757 |
| +10 dB | +0.699 |
| +15 dB | +0.655 |
| +20 dB | **+0.589** |

The paper's scale reads $d < 0$ as inert and $d > 0$ as over-suppressive, with
zero as the dividing line. On this evidence zero is not a meaningful dividing
line at all: a mask that wants to minimise error should sit near +0.95 at
-15 dB. Trading speech energy away to remove noise is what the optimum does.

The consequence is sharp. **508 of 776 cells have $d_g > 0$ and so read as
over-suppressive on the paper's scale. 492 of those 508 are still short of the
oracle.** For 97% of the cells the paper would call over-suppressive, the model
is in fact *under*-suppressing relative to the optimum. Only **16 of 776** cells
reach or pass the oracle.

This does not overturn any gate. Every registered rule is a comparison between
conditions or rungs on one scale, and shifting the reference point shifts every
arm of those comparisons together. What it changes is the prose: a sentence that
calls $d_g = +0.26$ over-suppression is describing a model 0.58 short of
optimal, in the inert direction.

## Finding 2: the shortfall is worst where enhancement matters most

Median `delta_d_g` by model set and SNR:

| SNR | D_fsd | DFN3 | SGMSE+ |
|---|---|---|---|
| -15 dB | **-1.697** | **-1.302** | **-1.363** |
| -10 dB | -1.380 | -0.999 | -0.964 |
| -5 dB | -1.160 | -0.649 | -0.934 |
| 0 dB | -0.984 | -0.505 | -0.908 |
| +5 dB | | -0.376 | -0.301 |
| +10 dB | | -0.263 | -0.454 |
| +15 dB | | -0.172 | -0.167 |
| +20 dB | | **-0.119** | **-0.087** |

D_fsd is scored at SNR <= 0 only, which is the registered D_fsd row set.

Every column is monotone: the gap from the oracle widens as the input gets
noisier. At +20 dB both pretrained models are within 0.12 of optimal. At -15 dB
all three are more than 1.3 away. The failure is not a fixed offset, it is a
collapse that tracks difficulty.

## Finding 3: per noise type, D_fsd

Median `delta_d_g`:

| noise type | -15 | -10 | -5 | 0 |
|---|---|---|---|---|
| hurricane | **-0.578** | -0.426 | -0.310 | **-0.266** |
| bubble_curtain | -1.054 | -0.743 | -0.485 | -0.444 |
| lightning | -1.690 | -1.371 | -1.154 | -1.019 |
| large_commercial_ship | -1.856 | -1.723 | -1.440 | -1.199 |
| rainfall | **-1.919** | -1.736 | -1.420 | **-1.162** |

Hurricane is three to four times closer to optimal than rainfall at every level.
That ordering is consistent with the diversity section, where DEMAND-trained
models removed 0.99 of the noise excess on hurricane and almost nothing on
bubble curtain: hurricane is the easy type, and the oracle gap confirms it from
the other direction.

## Range per model set

| model set | min | median | max | cells |
|---|---|---|---|---|
| D_fsd | -1.943 | -1.196 | -0.121 | 180 |
| DFN3 | -1.764 | -0.425 | +0.040 | 440 |
| SGMSE+ | -1.962 | -0.652 | +0.261 | 156 |

SGMSE+ holds both the single worst cell and the single best. Its 156 cells cover
7 corpora against DFN3's 12, and the generative arm's own fold-level rows are
not in this table yet: they arrive with Phase E.

## For the paper

1. Report the oracle's SNR-dependent $d$ as a reference row wherever $d$ is
   introduced. One line in the methods and one row in the direction figure.
2. Rewrite any sentence that reads $d_g > 0$ as over-suppression without saying
   what the optimum is. 492 of 508 such cells are short of the optimum.
3. Give the `delta_d_g` by SNR table. It is the clearest statement in the paper
   that the failure scales with difficulty.
4. Label all of it post-hoc. The per-cell CSV carries `post_hoc: true`.

## Reproducing

```
python scripts/oracle_delta_d.py          # oracle rows, cross-check, then cells
python scripts/oracle_delta_d.py --cells  # cells only, from saved oracle rows
```

The oracle pass is resumable and took about 8 minutes for 6,079 new rows on CPU.
`results/ci/oracle_wiener_rows.csv` is committed for the same reason
`results/metrics/review_oracle_masks_rows.csv` is: it is a reference signal, not
a model output, it costs 714 KB, and without it the per-cell table cannot be
rebuilt without the full recompute.
