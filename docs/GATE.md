# The go/no-go gate

Stage 1 exists to answer one question: **is there a phenomenon here worth building
a predictor for?** The gate is how that question gets answered honestly.

## Rules

1. Thresholds live in `configs/gate.yaml` and are committed **before** any
   aggregate is computed. The git timestamp is the proof.
2. `scripts/20_gate.py` refuses to run twice. There is no second look.
3. The decision is written to `results/gate_decision.json` and committed,
   whatever it says.

## The three conditions

| | Asks | Fails if |
|---|---|---|
| **G1** Separable | Do noise types produce measurably different failure directions? | Direction index is flat across conditions — the metric is not sensitive, or the conditions are too similar |
| **G2** Shift is real | Does cross-family testing degrade output more than matched testing? | No gap — MarVEN's two families are not far enough apart to support a shift claim |
| **G3** Consequential | Does over-suppression hurt WER more than under-suppression at equal magnitude? | No asymmetry — the direction distinction is measurable but not *useful* |

## Outcomes

- **G1 + G2 + G3 pass** → build the predictor. Claim 3 is live.
- **G1 + G2 pass, G3 fails** → proceed, but demote the asymmetry from
  "consequential" to "measurable". Claims 1 and 2 stand on their own.
- **G1 or G2 fails** → stop. Diagnose before writing any predictor code. The
  likely causes, in order: a bug in the oracle floor, a broken
  `noise = noisy − clean` identity, or genuinely homogeneous noise conditions.
  The last means MarVEN alone cannot carry a cross-condition claim, and the
  honest response is a second corpus — not a harder-working predictor.
