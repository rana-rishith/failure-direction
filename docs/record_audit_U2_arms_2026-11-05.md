# Audit A2 and A3: the U2 arms, and when the inert rule was fixed

2026-11-05. No verdict file was changed. No yaml was edited.

---

## A2. Are both passing U2 arms fine-tuned on half A

**Yes. Neither is zero-shot. `U2_beyond_bounded` stands as PASS, 2 of 3 classes.**

The registered on_fail, which would narrow the headline to "bounded mask estimators",
does not fire.

### Why the question matters

R1 is the half-A windows and R2 is the half-B windows of the same recording. A model that
heard neither half, or both, gives the same measurement at R1 and R2, so it cannot
produce the strict ordering the gate asks for. `results/universal/u2_verdict.json`
already carries this as a note:

```
"requirement": "each arm must be fine-tuned on half A only, or R1 and R2 are the same measurement"
```

### The two passing classes

From `results/universal/u2_verdict.json` (verdict PASS, config `29c1566`, sha256[:12]
`a13d0d71f9e6`, code `cc8aab9`, run 2026-10-28T12:04:49):

```
"classes_measured": {"complex_mask": ["cm"], "diverse_pretrained": ["dfn3"]}
"classes_missing":  {"generative": ["sgmse"]}
"levels_passed":    {"cm": 4, "dfn3": 4}
```

### Checkpoints, per fold

| class | tag | checkpoint | bytes | written |
|---|---|---|---|---|
| complex_mask | cm_seg_weather | `ckpt/cm_seg_weather_last.pt` | 47,405,008 | 2026-10-28 01:29 |
| complex_mask | cm_seg_anthro | `ckpt/cm_seg_anthro_last.pt` | 47,404,946 | 2026-10-28 02:00 |
| diverse_pretrained | dfn3_seg_weather | `ckpt/dfn3_seg_weather_last.pt` | 25,877,288 | 2026-10-28 10:36 |
| diverse_pretrained | dfn3_seg_anthro | `ckpt/dfn3_seg_anthro_last.pt` | 25,876,923 | 2026-10-28 11:48 |

`cm_seg_*` also has `_best.pt`. `dfn3_seg_*` has `_last` only, which matches the
registered DFN3 deviation: the weights at step 20,000 rather than the best validation
checkpoint.

Scored windows exist for all four: `results/segment/{cm,dfn3}_seg_{weather,anthro}__windows.csv`
and `__unseen.csv`.

### Proof that half B was excluded from training

Not an inspection of the data, but of the code path that built it. Both arms draw crops
from half A by construction, and the halves cannot touch.

`src/segment.py:83`

```python
def half_bounds(L: int, half: str) -> tuple[int, int]:
    mid = L // 2
    return (GUARD, mid - GUARD) if half == "A" else (mid + GUARD, L - GUARD)
```

A ends at `mid - GUARD` and B starts at `mid + GUARD`, so the two are disjoint with a
guard band of `2 * GUARD` between them, and neither reaches the first or last `GUARD`
samples of the recording.

`src/segment.py:88` `valid_starts()` admits a window start only if every recording
position it covers, wrapped modulo the recording length, lies inside the requested half.
So a crop cannot straddle the midpoint even when the noise loops.

`src/segment.py:164`, the training loader, passes the half as a literal:

```python
def _seg_loader(frame, root=None, ...):
    """Drop-in for data.make_loader while training the seg model: half A only."""
    return DataLoader(SegWindows(frame, "A", train, seed, root), ...)
```

There is no parameter to change it, so a `cm_seg` model cannot have been trained on
anything but half A.

For the DFN3 arm, `scripts/dfn_seg.py:68` states the same for its own `Plan`: "Random 3 s
crops whose noise lies in half A, read straight from the MarVEN files", and the module
docstring at line 5 names the failure it exists to avoid.

The split is of the **noise recording**, not of the speech. That is the intended design:
the novelty being controlled is novelty of the noise recording, and the speech comes from
the MarVEN train split in both halves.

### One check this audit did not do

`src/segment.py:350` documents a stronger guarantee than the code enforces:

> R1 (half A) against R2 (half B) only carries meaning if this enhancer was fine-tuned on
> half A alone, the way the b*_seg models were. A model that saw both halves, or neither,
> has R1 == R2 by construction and its U1 unit is empty, not passing.

`score_windows()` does not verify the claim for the tag it is given. It is a comment, not
an assertion. For `cm` and `dfn3` the claim is true, established above from the training
code. For any future arm it has to be checked by hand again.

---

## A3. When was the numeric inert rule fixed

**Pre-committed, by 8 days 21 hours 53 minutes.**

### The rule

`configs/gate_universal.yaml:63`

```
classes:
  inert:        "nr < 0.30 and r_over_x(R4) < r_over_x(R1)"
  over:         "r_over_x(R4) >= r_over_x(R1)"
  hallucinate:  "median r_add >= 0.05"
```

### The two times

| event | when | source |
|---|---|---|
| rule committed | 2026-10-19 11:24:59 | commit `29c1566` |
| provenance block filled | 2026-10-19 11:27:05 | commit `4ba32aa`, no threshold changed |
| first `U1_failure_class` score | 2026-10-28 09:17:48 | `run_at` in `results/universal/u1class_verdict.json` |

`configs/gate_universal.yaml` has exactly two commits in its whole history, both on
19 Oct, two minutes apart. `git diff 29c1566 HEAD -- configs/gate_universal.yaml`
contains nothing but the two `provenance` lines. The numeric cut points have never moved.

### The caveat that belongs in the text

No `U1_failure_class` score existed when `nr < 0.30` was written, and that is what
"pre-committed" means here. It does not mean the cut point was chosen blind.

- The gate file's own header says the pre-commitment is relative to a narrower event:
  "gates and src/diverse.py, before any diversity-control run".
- `r_over`, `r_under` and `r_under_B4`, from which `nr` is derived, were already being
  computed and reported by the gate-XN runs before 19 Oct.
  `configs/gate_overnight2.yaml`'s header lists what had been seen by 20 Oct, including
  "every gate-XN result (seeds, R3, xcorpus matrix of 29 checkpoints, DFN3, 20 SGMSE+
  base rows)".
- The word "inert" appears in earlier gate files as a concept with no number attached:
  `configs/gate.yaml:12`, `configs/gate_claim3_active.yaml:16`. The only earlier numeric
  cut is `configs/gate_pilot_level.yaml:22`, which uses "median d < -0.3" for a different
  label, `reversed`.
- `configs/gate_overnight2.yaml:40` reuses the same 0.3 cut for `D_fsd`'s
  `architecture_explains` branch, registered the next day.

So the defensible claim is the narrow one: the class rule was fixed before any
classification was computed, and has not changed since. The paper should not claim the
thresholds were chosen without any knowledge of the metric's scale, because the metric
had been reported for 29 checkpoints by then. This is the same disclosure the draft
already plans for the U gates as a whole: thresholds committed 19 Oct, after the Claim 1
and 2 results and some Claim 3 results had been seen.
