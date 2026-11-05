# Record: the U2 generative arm, SGMSE+ fine-tuned per fold

Started 2026-11-05 09:32:24. This file is the run's record and will carry the
verdict when scoring finishes. No gate verdict exists yet, and
`results/universal/u2_verdict.json` still records the generative class under
`classes_missing`.

## Why it is being run at all

`configs/gate_universal.yaml` registers three non-bounded architecture classes
and `U2_beyond_bounded` passes on 2 of 3. The third, `generative`, was reported
as not measured. The stated reason, in `paper.tex:1016`, was that one file took
about 95 s and that fine-tuning was not realistic on 8 GB.

The 8 GB part was wrong. At micro-batch 1 with 8x gradient accumulation the
fine-tune peaks at **4.45 GB**, measured. Micro-batch 4 thrashed and was
abandoned past 600 s. So the arm is measurable and the ledger does not have to
carry a silent third class.

## Protocol, as registered and as run

Registered: 20,000 gradient steps, batch 8, lr 2e-4, seed 1234.

| item | registered | as run | same |
|---|---|---|---|
| gradient steps | 20,000 | 20,000 (`max_steps`) | yes |
| effective batch | 8 | micro-batch 1 x accum 8 | yes |
| learning rate | 2e-4 | **1e-4** | **no** |
| weights taken | (DFN3 precedent: final step) | final step, `save_top_k=0` | by precedent |
| crop seed | 1234 | 1234 | yes |
| trainer seed | 1234 | **none set** | **no** |

### Deviation 1: learning rate 1e-4, not 2e-4

`scripts/sgmse_seg.py:93` declares `LR` in its constant tuple and never passes it
anywhere, so the optimiser took the rate in the checkpoint's own
hyperparameters. Verified by loading both checkpoints on CPU:
`ckpt/sgmse_seg_weather/last.ckpt` has `optimizer_states[0]` param-group
`lr = 0.0001` and `hyper_parameters["lr"] = 0.0001`, and `SB_16k.pt`, at its own
global_step 900,000, carries the same two values. So the fine-tune is running at
the rate the pretrained checkpoint was trained at, not at the registered double.

Reported, not corrected. The decision, taken at step 12,000 on 5 Nov: a restart
discards about 11 hours to change a fine-tune's rate from the one its pretrained
checkpoint was trained at to double that, on a diffusion model, where the
protocol's binding element is equal compute and 20,000 steps at effective batch
8 delivers it. DFN3 already carries two recorded deviations in the same section
of the paper, both of the same kind. This is the third and must be printed
beside them.

The dead `LR` constant stays until both folds finish, because the runner reads
`scripts/sgmse_seg.py` again when the anthro fold starts and the two folds must
train under identical code. Remove it afterwards.

### Deviation 2: the trainer is not seeded

`pl.Trainer` is constructed without `seed_everything`, so data order and the
diffusion noise draw are not reproducible run to run. The **staged data** is
deterministic: `crop()` uses seed 1234 and mirrors `dfn_seg.Plan.crop` exactly,
including its short-range clamping, so both arms see the same windows. Only the
training trajectory is unseeded. Not recorded anywhere before this file.

## The half-A requirement

`U2`'s rungs put R1 on half-A windows and R2 on half-B, so an arm that heard
neither half gives one measurement twice. `scripts/sgmse_seg.py stage` crops from
half A only, through the same bounds the `b*_seg` models used. The registered
fallback of a zero-shot SB cannot satisfy the gate for that reason, and
`paper.tex:1016` already declines it. See
`docs/record_audit_U2_arms_2026-11-05.md` for the equivalent check on the two
arms that already passed.

## Cost, measured

0.820 h per 1,000 steps on the 8 GB RTX 4060 Laptop, from the step count and
mtime of `ckpt/sgmse_seg_weather/last.ckpt`. 16.4 h a fold, 32.8 h for both.

Then 6,055 windows of 3.00 s to enhance across the two folds. The only measured
enhancement rate is 32.7 s per file on 13.49 s of audio, so 2.4 s of compute per
audio second gives about 7.4 s per window and 12.5 h for both folds. A 3 s file
has not been timed.

## Incident: two GPU jobs, 19:54 to 20:46

`run_sgmse_full.ps1` was started with its `-Now` override against the running
fine-tune. Both jobs then crawled:

- the full split did 17 files in 58 min, 180 s each against 32.7 s on an idle
  card, which projects to 93 h instead of 17
- the fine-tune went from a checkpoint every 25 min to none in 55 min
- GPU memory 7,849 MiB, utilisation 57%

The enhancement was stopped at 20:46, parent script first so that the copy and
`rescore --force` in its step 3 could not run: that copy would have overwritten
the committed `results/probe/sgmse` summary with 17 of 1,880 files, 0.9%
coverage. The committed results were checked afterwards and are untouched, and
the 17 enhanced wavs are kept for the resume. The card then read 90%
utilisation at 5,038 MiB, the fine-tune alone.

The trainer recovered on its own: the next checkpoint landed at 20:50:22, four
minutes after the enhancement stopped, against a 61.6 min gap from 19:48:45
while the card was shared. Slowed, never hung, so no resume was needed.

`-Now` was removed in `a35ce50`. Serial is strictly faster for both jobs, so the
override served no case.

## Remaining, in order

1. weather fine-tune to 20,000 steps; global_step 12,000 at 20:50 on 5 Nov,
   so about 6.6 h left
2. anthro fine-tune, 16.4 h
3. enhance 6,055 windows, about 12.5 h, **required for the verdict**
4. score both folds and run `--gate u2 --force`
5. `run_sgmse_full.ps1`, last: 17 h, a leaderboard row and no verdict

A note on 4: U2 already passes at 2 of 3 and the rule needs 2 of 3, so the
generative result cannot change the verdict. It closes the class, which removes
the "2 of 3" caveat from every U2 sentence.
