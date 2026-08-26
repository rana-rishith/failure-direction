<div align="center">

# Failure Direction

**Predicting *which way* speech enhancement will break — before it runs.**

pre-hoc · reference-free at inference · tested on noise it has never heard

![status](https://img.shields.io/badge/status-active_research-1F3A5F)
![stage](https://img.shields.io/badge/stage-1_·_go%2Fno--go_gate-2E5A88)
![python](https://img.shields.io/badge/python-3.11_|_3.12-3776AB)
![license](https://img.shields.io/badge/license-MIT-555555)

</div>

---

## The question

> Can a cheap measurement on the noisy input — taken **before** any enhancement runs — tell you not just whether enhancement will fail, but **which way**?

Everything in this repo exists to answer that.

## Why direction matters

Speech enhancement fails in two opposite ways, and they are not equally bad:

| | What happens | Recoverable? |
|---|---|---|
| **Over-suppression** | The system cuts into the speech itself | **No.** The words are gone. |
| **Under-suppression** | The system leaves noise in, speech intact | Yes. Ugly, but the words survive. |

PESQ, STOI, a single quality score — all of them collapse these into one number. The
number drops and you cannot tell whether the system politely left some hiss in or
quietly deleted the sentence you needed. Under noise the model was never trained on,
which of the two you get becomes unpredictable.

This repo measures the difference, explains it, and then tries to predict it from the
input alone.

## The measurement

Recover the enhancer's *effective* gain from its output waveform:

```
M(t,f) = |Y(t,f)| / |X(t,f)|
```

Apply that same gain to the clean and noise stems separately:

```
over  = Σ |S·(1−M)|² / Σ|S|²      speech energy destroyed
under = Σ |N·M|²     / Σ|N|²      noise energy retained
D     = (under − over) / (under + over)      ∈ [−1, +1]
```

`D = −1` is pure over-suppression, `D = +1` is pure under-suppression. Because the mask
is read off the output waveform, this works for time-domain models, generative models
and passthrough alike — no access to model internals required.

Three analytic endpoints pin it down, and they are enforced in `tests/`:

| Enhancer | Expected |
|---|---|
| `y = x` (passthrough) | `over ≈ 0`, `under ≈ 1`, `D ≈ +1` |
| `y = 0` (silence) | `over ≈ 1`, `under ≈ 0`, `D ≈ −1` |
| ideal ratio mask | strictly between — this is the **oracle floor** |

Every reported number is a delta against that oracle floor. Without it, low-SNR
conditions look like over-suppression failures when they are simply hard.

## Three claims, in order

1. **Characterize** — the two failure modes are real and separable via exact energy decomposition.
2. **Explain** — the two noise families leave distinct failure signatures across SNR.
3. **Predict** — a reference-free input-side measurement forecasts direction and magnitude under unseen noise.

Claims 1 and 2 stand on their own if Claim 3 fails. Claim 3 is the citable contribution
and the riskiest; see [`docs/GATE.md`](docs/GATE.md) for the pre-committed thresholds
that decide whether it gets built at all.

> **One caveat, stated up front:** clean references *are* used during **training**, to
> construct the directional labels. At **inference** the predictor sees only the noisy
> input. `src/failure_direction/direction/` is a labelling tool and is not reference-free;
> the predictor that consumes its output is. Do not conflate them.

## Baselines

Four enhancers, equal compute budget, identical STFT framing:

| | Model | Role |
|---|---|---|
| 1 | STFT magnitude mask (BLSTM) | the mask is the object of study |
| 2 | Causal GRU mask | streaming-plausible, small budget |
| 3 | Spectral/generative (SGMSE-style) | external — see `models/diffusion.py` for why |
| 4 | Passthrough | the baseline everything is measured against |

## Data

[MarVEN](https://doi.org/10.5281/zenodo.20714212) — paired clean/noisy marine speech,
5 noise conditions in 2 families (weather vs. vessel), 8 SNR levels from −15 to +20 dB.
Training on one family and testing on the other is the shift axis.

## Quickstart

```bash
git clone https://github.com/OWNER/failure-direction.git
cd failure-direction

py -3.11 -m venv .venv && .venv\Scripts\Activate.ps1     # Windows
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -e ".[metrics,asr,viz,dev]"
pytest                                                    # 6 tests, no GPU needed
```

Then follow [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) to publish it, and [`docs/STAGE0.md`](docs/STAGE0.md) to run it. The environment notes assume an
RTX 3060 12 GB (Ampere, sm_86) and Python 3.11 or 3.12 — **not 3.13**, where `pesq`
has no usable Windows wheel.

## Layout

```
configs/            one YAML per experiment; nothing is hardcoded
data/manifests/     inventory.csv + integrity.csv — the single source of truth
src/failure_direction/
  direction/        the energy decomposition and the oracle floor
  models/           four baselines behind one registry
  metrics/          PESQ / STOI / SI-SDR / WER, with the traps handled
  data/             manifest building, cross-family speaker-disjoint splits
scripts/            numbered entrypoints, run in order
docs/GATE.md        the pre-committed go/no-go criteria
results/            CSVs and figures — committed
runs/               checkpoints and logs — gitignored
```

## Roadmap

- [x] Direction index with analytic sanity checks
- [x] Oracle floor
- [x] Cross-family, speaker-disjoint splits
- [ ] Stage 0 — MarVEN downloaded, manifest built, mixture identity verified
- [ ] Stage 1 — 4 models × 2 folds × 3 seeds, per-utterance scoring
- [ ] Gate evaluated once, decision committed
- [ ] Stage 2 — the reference-free predictor (Claim 3)
- [ ] Second-corpus validation

## Citing

See [`CITATION.cff`](CITATION.cff).

## License

MIT.
