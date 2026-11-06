# Results in detail

Every measured result, the limitations, and what
changed relative to the original code. The headline claims are in the
top-level [README](../README.md).

## Results

The energy-based numbers (`e_over`, `e_under`, `r_over`, `r_under`, `dir_idx`)
come from the DC-fixed rerun on 7 October 2026. The fix does not touch SI-SDR,
STOI or PESQ.

### Training reproducibility

Final validation SI-SDR on two GPUs. All four tags agree within ±0.08 dB, and a
later retrain on the 4060 landed within ±0.10 dB of these.

| Tag | RTX 3060 | RTX 4060 | Δ |
|---|---|---|---|
| b1_weather | 14.71 | 14.65 | −0.06 |
| b1_anthro | 14.40 | 14.39 | −0.01 |
| b3_weather | 13.74 | 13.82 | +0.08 |
| b3_anthro | 13.17 | 13.14 | −0.03 |

### Evaluation matrix

| Model | Fold | Split | SI-SDR out | STOI out | PESQ out |
|---|---|---|---|---|---|
| B1 | anthro | test_matched | 15.435 | 0.899 | 2.696 |
| B1 | anthro | test_unseen | 2.962 | 0.813 | 1.819 |
| B1 | weather | test_matched | 15.031 | 0.877 | 2.610 |
| B1 | weather | test_unseen | 3.321 | 0.809 | 1.763 |
| B3 | anthro | test_matched | 14.115 | 0.876 | 2.486 |
| B3 | anthro | test_unseen | 2.983 | 0.813 | 1.832 |
| B3 | weather | test_matched | 13.945 | 0.855 | 2.461 |
| B3 | weather | test_unseen | 3.255 | 0.808 | 1.747 |
| B4 | weather | test_matched | 2.697 | 0.807 | 1.757 |
| B4 | weather | test_unseen | 2.815 | 0.802 | 1.725 |

No NaN in any PESQ or STOI column. Even passthrough shows nonzero `e_over`
(1,411.7 matched, 1,285.2 unseen), because noise cancels speech in some bins
through phase. Read each trained model's `e_over` against that floor.

### Claim 1 holds, at the recording level

The SI-SDR gap between matched and unseen runs from 10.7 to 12.5 dB, with the
same sign in all four model/fold pairs. On unseen noise, output SI-SDR follows
input SNR closely and PESQ lands within 0.1 of passthrough. The models do
nothing useful. The small positive improvement in the pooled mean comes from
averaging across SNR levels and vanishes once you split by SNR.

**LOTO confound test.** Each run trains on two weather types and tests on the
third. R is held-out SI-SDR improvement divided by matched improvement (median
within each SNR stratum, then averaged). `configs/gate.yaml` fixed the
thresholds before any run: R ≥ 0.5 means family-level generalization, R ≤ 0.2
means recording-level failure.

| Held out | B3 R | B1 R |
|---|---|---|
| rainfall | 0.059 | 0.089 |
| lightning | −0.016 | −0.002 |
| hurricane | −0.006 | −0.003 |

A model trained on two weather recordings learns close to nothing that helps on
a third. On held-out rainfall at −15 dB, both models score below passthrough:
−4.16 dB for B3 and −1.36 dB for B1. So Claim 1 reads "models fail on an unseen
noise recording". This dataset can't support the family-level version.

### Claim 2 holds

Median direction ratios, pooled across folds:

| | Matched | Unseen |
|---|---|---|
| B1 | over-dominant, 5.9:1 | under-dominant, 38:1 |
| B3 | over-dominant, 5.0:1 | under-dominant, 28:1 |

The flip shows up at all eight SNR levels on both architectures. At −15 dB the
matched and unseen splits sit 794× apart on `r_under` and 6.2× on `r_over`; at
+20 dB the gaps shrink to 5.7× and 1.27×. Report it per SNR level, since a
pooled number averages those very different gaps.

Across held-out recordings within weather, the amount of speech the mask
destroys varies by recording. Held-out ÷ matched `r_over`, averaged over −15 to
0 dB:

| Held out | B1 | B3 | Mask |
|---|---|---|---|
| hurricane | 0.01 | 0.01 | inert |
| lightning | 0.97 | 0.86 | active, near matched level |
| rainfall | 2.28 | 5.24 | over-active |

Both architectures order them the same way: hurricane, then lightning, then
rainfall.

### Claim 3 passes on all four runs

The rule, fixed in advance: `full` beats the oracle baseline (SNR +
`log e_noisy`) only if its within-SNR Spearman is higher in a clear majority of
the 8 SNR strata **and** inside each noise type on its own.

| Run | SNR strata won | Per noise type | Mean margin, full / feats_only | AUC top-10% margin |
|---|---|---|---|---|
| B1 weather | 8/8 | hurricane 8/8, lightning 8/8, rainfall 8/8 | +0.647 / +0.605 | +0.040 |
| B1 anthro | 8/8 | bubble_curtain 8/8, ship 8/8 | +0.445 / +0.414 | +0.007 |
| B3 weather | 8/8 | hurricane 7/8, lightning 8/8, rainfall 8/8 | +0.648 / +0.619 | +0.045 |
| B3 anthro | 8/8 | bubble_curtain 7/8, ship 8/8 | +0.452 / +0.402 | +0.011 |

The predictor lost two strata: hurricane at +20 dB (B3 weather) and
bubble_curtain at −15 dB (B3 anthro). `feats_only` drops oracle SNR, which makes
it the strictly pre-hoc arm, and it wins on its own.

A win over the baseline doesn't make the predictor useful in every stratum. For
hurricane at +15 and +20 dB both arms score near zero, and B3 weather rainfall
is weak at −15, −10 and +10 dB. Those strata pass because the baseline does even
worse there.

**Precondition.** B1 and B3 agree on which utterances fail worst (Spearman
0.60–0.99 in every split × SNR cell, top-decile overlap well above chance). A
2.8M-parameter BLSTM and a 280K-parameter GRU flag the same files, so the input
drives the failure. A segment-position check (η² 0.06–0.11 against ~0.07 by
chance) shows the predictor isn't just recognising which stretch of the looped
noise recording it hears.

### WER

faster-whisper large-v3 on the 818 negative-SNR rows: clean 1.38%, noisy
17.45%, b1_matched 15.94%, b1_unseen **20.68%**. On unseen noise, enhancement
makes ASR 3.2 points worse than leaving the audio alone, while SI-SDR and STOI
call the output roughly as good as passthrough. WER never reads the energy
decomposition, so the DC fix leaves these numbers as they were.

These replace an earlier set (noisy 17.47, b1_matched 16.23, b1_unseen 21.93,
a 4.5 point gap) that was measured with the B1 checkpoints preceding the 13 Sep
2026 retrain. The two arms that never run B1, clean and noisy, moved by 1 and 5
words of 29,643 between the two runs, which is what rules the text normaliser
out as the cause. See `docs/record_c4_wer_source_2026-11-06.md`.

### Gates

Recomputed on the corrected energies and persisted to
`results/metrics/gate_results.yaml` on 6 Nov 2026. No verdict changed.

G1 fails as written (pooled spread 0.161, threshold 0.30). It asks whether
direction varies across the five noise types, but the hypothesis was about seen
vs unseen, so the gate tests the wrong axis. Split-conditioned, matched runs
0.618 to 0.737 and unseen -0.925 to -0.666, a separation of 1.284, which is
post-hoc and must be flagged as such. G2 passes (median gap 0.206, threshold
0.10); the pre-fix energies gave 0.288, so the paper's printed 0.0347 / 0.3223 /
0.288 are superseded by 0.0240 / 0.2304 / 0.206. G3 can't be tested: direction
and condition overlap in 99.5% of utterances (11 of 2,280 matched rows have a
negative direction index), and the one SNR level with enough overlap (+20 dB)
has failures too small for the threshold to mean anything.

See `docs/record_g1g2g3_persisted_2026-11-06.md`.

### Withdrawn

An earlier result claimed B3 destroys ~40% of clean speech energy in a few
concentrated bins while SI-SDR and STOI look fine. Those files turned out to be
DC-heavy, and the mask was removing an offset nobody could hear. That result
and the mechanism built on it are withdrawn.

## Limitations

- **One recording per noise type.** Each noise type is a single short recording,
  and three of them loop. Noise type and recording identity can't be pulled
  apart, so Claim 1 holds at the recording level only. A family-level claim
  would need several recordings per type.
- **Sampled design.** Each clean utterance appears in two rows, with two
  different noise types. No utterance spans all five noise types or all eight
  SNR levels, so the direction index has to be aggregated over the corpus
  instead of compared within an utterance.
- **Direction/condition collinearity.** This blocks G3 and limits Claim 3 to
  magnitude within a condition.
- **Pooling hides real effects.** Pooled WER and pooled Spearman both gave
  misleading answers, so every table in `results/metrics/` is split by
  condition, SNR or noise type. Within one condition, `frac_pos` and `snr` carry
  the same information; the frame-level features only looked better because
  they reordered conditions.
- **Noise type, not SNR, decides which rows hurt ASR.** Hurricane and
  bubble_curtain stay at the clean-ASR floor even at −15 dB broadband SNR:
  hurricane's energy falls outside the speech band and bubble_curtain comes in
  bursts. A cut at SNR ≤ −5 picks the wrong rows. `--damaging-only` uses
  rainfall, large_commercial_ship and lightning instead, at the cost of fewer
  training rows.
- **Pre-hoc only at inference.** The predictor needs no clean reference when it
  runs, but building its training labels does.
- **Gates not recomputed** on the DC-fixed energies, and the over-dominant
  fraction on the LOTO held-out rows hasn't been rerun either.
- **B2 deferred.** Diffusion needs cloud compute.
- **Open item.** The clean-arm WER dropped from 3.07% to 1.38% on the same rows.
  The normalisation mismatch explains the size of the drop, but the change on
  the hypothesis side that caused it hasn't been tracked down.

## What changed relative to the original code

These are bug fixes. The architectures, hyperparameters, split design and
metrics stay as they were.

1. **The direction-index sign was flipped** in `src/direction.py` relative to
   every reported number. That file also weighted frames by clean energy, which
   the evaluation harness did not, so one name covered two quantities. The code
   now uses the harness definition, the weighted version has its own name, and
   `tests/test_metrics.py` checks the sign.
2. **The leakage assertion on `clean_source` could never fire**, because that
   column holds one corpus-level string. It now checks the `(speaker_id,
   chapter_id, utterance_id)` tuple and covers train/val as well.
3. **Labels and features were joined by position.** Reordering the manifest
   would have misaligned targets without any error. Both sides now write a
   `uid`, and the merge checks it.
4. **AUC columns had the wrong names.** `int((1 - 0.90) * 100)` gives 9, so the
   top-decile column came out as `auc_top9`. The code now uses `round()`.
5. **The `safe_*` metric wrappers hid total failure.** With `DO_PESQ=False` they
   returned NaN for all 4,560 rows, twice, with no warning. They now count
   guard rejections, exceptions and skips, and print the counts at the end.
6. **`autocast("cuda")` was hardcoded**, so nothing ran on a CPU-only machine.
   It now follows the device.
7. **The SI-SDR loss ran inside autocast.** It now runs in fp32. Taking `log10`
   of a ratio of two 64k-sample sums is the fragile step, and fp16 gains nothing
   there.
8. **Crop offsets used `np.random`**, which PyTorch doesn't reseed per worker.
   They now come from a torch `Generator`.
9. **`CKPT` was defined twice, on different drives.** Training wrote to one and
   evaluation read from the other. Three files also hardcoded `C:\` and `D:\`
   paths. Every path now comes from `config.py`.
10. **Checkpoints came in two formats**: a bare `state_dict` from the notebook
    trainer and a resumable dict from `train.py`. `load_model` reads both, and
    training also writes a portable weights-only export.
11. **torch 2.6 made `weights_only=True` the default for `torch.load`**, which
    rejects the numpy RNG state stored in resumable checkpoints. The loader sets
    the flag explicitly.
12. **Resume trusted any existing CSV.** A partial file now fails the row-count
    check and gets re-run.
13. **Gate verdicts come from the data** instead of the report text.
    `configs/gate.yaml` records the sign convention and states that G1 and G2
    were operationalised after Claims 1 and 2 were seen.
14. **Claim 3 gained a third arm.** `full` includes `snr`, which is mixing
    metadata you wouldn't have before enhancement. `feats_only` drops it. Within
    a single SNR stratum `snr` is constant, so the within-SNR margins come out
    the same either way.
15. **`models/` and `splits.py` are gone.** The old package disagreed on
    state-dict prefixes (an `STFTWrapper` added `net.`, `out` was a bare
    `Linear` with no sigmoid, an extra `window` buffer appeared) and loaded
    weights wrong. `splits.py` used column names the manifest doesn't have and
    leaked speakers and utterances.
16. **The energy decomposition counted the DC bin.** In the ~6% of clean files
    with a large offset, a mask that removed the inaudible offset got charged
    with destroying speech. `energy_decomposition` now skips bins below
    `config.DECOMP_MIN_HZ = 60.0` and keeps the old values in `*_full` columns.
    Voiced speech starts around 80 Hz, so the cut removes nothing you can hear.
    Every energy-based number changed, and one finding was withdrawn.
17. **`src/confound.py` is new**, with a `--model` flag so the LOTO test runs on
    both B1 and B3.
