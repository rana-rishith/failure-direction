# Record C4: which WER numbers are correct, and why two sets exist

Task C4 of the 5 Nov work order. CPU only, no rerun of the ASR.

## Verdict

**20.68% is correct.** The cause is the 13 Sep B1 retrain, not the text
normaliser. The work order gave this as a hypothesis; it is now confirmed twice
over, by the commit dates and by which arms moved.

`paper/paper.tex` already carries the correct set. `README.md` carries the
superseded set and needs the erratum.

## The two sets

| arm | Stage 2 record | `results/wer_snrmax-5.csv` | delta | in words of 29,643 | runs B1 |
|---|---|---|---|---|---|
| clean | 1.38 | 1.38 | 0.00 | 1.1 | no |
| noisy | 17.47 | 17.45 | -0.02 | 4.6 | no |
| b1_matched | 16.23 | 15.94 | -0.29 | 86.1 | yes |
| b1_unseen | 21.93 | 20.68 | -1.25 | 369.7 | yes |

Recomputed from the committed file with the repo's own `corpus_wer`, which is
total edits over total reference words and not a mean of per-utterance rates:
818 rows, no duplicate `row_key`, no appended header rows, so the file is one
clean run and not two runs merged by `--resume`. Edit counts 408, 5,174, 4,725
and 6,131 over 29,643 reference words, which are the same counts
`paper.tex:1447` prints.

## Why the retrain, and not the normaliser

Two arguments, either sufficient.

**1. The arms that do not touch B1 did not move.** `clean` and `noisy` go
straight to the ASR. They moved by 1.1 and 4.6 words out of 29,643. The two
arms that run B1 inference moved by 86 and 370. A normaliser acts on every arm
at once, so it cannot move two arms and leave the other two still.

**2. The normaliser signature is absent.** `src/wer.py:107` puts normalisation
in one function applied to both sides. Its docstring records what the
asymmetric version did: it inflated the clean arm from 1.38% to 3.07%. Both
records read clean 1.38, so both runs were already symmetric. If Stage 2 had
scored a raw hypothesis against a normalised reference, its clean arm would read
about 3.07.

The residual 4.6 words on the `noisy` arm is 0.02 points. faster-whisper
`large-v3` at `int8_float16` is not bit-reproducible across runs, so a handful
of words is the floor, not a finding.

## Provenance

| | |
|---|---|
| producing script | `python -m src.wer --snr-max -5`, `src/wer.py` |
| output | `C.EVAL / wer_snrmax-5.csv`, 818 rows, written 11 Oct 21:45 |
| B1 weights it used | `ckpt/b1_weather.pt` and `ckpt/b1_anthro.pt`, both **13 Sep 2026** |
| 21.93 first committed | `3dc8ac1`, `README.md`, **12 Sep 2026** |

The 21.93 value was committed one day before the checkpoints that stand in
`ckpt/` today. It was therefore produced by the pre-retrain B1 weights, which
are no longer on disk. That is why it cannot be reproduced, and why it must not
be quoted.

The per-utterance file is gitignored by `.gitignore:23` (`results/*.csv`), which
is correct: it is a per-utterance dump. The aggregates are committed and carry
the correct values, so the numbers in the paper are reproducible from the repo:

```
results/metrics/wer_overall.csv        clean 1.38  noisy 17.45  b1_matched 15.94  b1_unseen 20.68
results/metrics/wer_by_type_snr.csv
results/metrics/wer_delta_vs_passthrough.csv
results/metrics/wer_hallucination.csv
```

## Erratum for the Stage 2 record

> The Stage 2 WER figures (clean 1.38%, noisy 17.47%, b1_matched 16.23%,
> b1_unseen 21.93%) were measured with the B1 checkpoints that preceded the
> 13 Sep 2026 retrain. The retrained checkpoints give clean 1.38%, noisy
> 17.45%, b1_matched 15.94%, b1_unseen 20.68%, and those are the values the
> paper reports. The normaliser was symmetric in both runs. The gap between
> enhancement on unseen noise and no enhancement narrows from 4.5 to 3.2
> points; the direction of the finding does not change.

## Lines that must change

| file | line | present | action |
|---|---|---|---|
| `README.md` | 603 | noisy 17.47%, b1_matched 16.23%, b1_unseen **21.93%**, "4.5 points worse" | replace with the retrained set and 3.2 points |
| `paper/paper.tex` | 843, 1447 | already 1.38 / 17.45 / 15.94 / 20.68 | none |
| `paper/_old/_plans_backup/A_appendix.tex` | 7 | a `\todo` asking for exactly this check | resolved by this record, file is in `_old/` and not committed |

No change is needed in `paper.tex`. Its `\todo` at the appendix is answered:
the run settings behind `results/wer_snrmax-5.csv` are the 13 Sep checkpoints
with symmetric normalisation, and 20.68% is the value to keep.
