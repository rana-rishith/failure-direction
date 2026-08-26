<div align="center">

# 🧭 Failure Direction

**Predicting *which way* speech enhancement will break, before it runs.**

`pre-hoc` · `reference-free at inference` · `tested on noise it has never heard`

![ci](https://github.com/rana-rishith/failure-direction/actions/workflows/ci.yml/badge.svg)
![status](https://img.shields.io/badge/status-active_research-1F3A5F)
![stage](https://img.shields.io/badge/stage-1_·_go%2Fno--go_gate-2E5A88)
![python](https://img.shields.io/badge/python-3.11_|_3.12-3776AB)
![license](https://img.shields.io/badge/license-MIT-555555)

</div>

---

## ❓ The question

> Can a cheap measurement on the noisy input, taken **before** any enhancement runs, tell you not just whether enhancement will fail, but **which way**?

Every line of code here exists to answer that.

## ⚖️ Why direction matters

Enhancement breaks in two opposite ways, and they cost you very differently:

| | What happens | Recoverable? |
|---|---|---|
| 🔻 **Over-suppression** | The system cuts into the speech itself | **No.** The words are gone. |
| 🔺 **Under-suppression** | The system leaves noise in, speech intact | Yes. Ugly, but the words survive. |

PESQ, STOI, any single quality score: all of them average these into one number. Watch it drop and you still can't say whether the enhancer left some hiss behind or deleted the sentence you needed. Feed it noise it was never trained on and which of the two you get stops being predictable.

This repo measures that difference, explains where it comes from, and then tries to forecast it from the input alone.

## 📐 The measurement

Read the enhancer's *effective* gain straight off its output waveform:

```
M(t,f) = |Y(t,f)| / |X(t,f)|
```

Apply that same gain to the clean and noise stems separately:

```
over  = Σ |S·(1−M)|² / Σ|S|²      speech energy destroyed
under = Σ |N·M|²     / Σ|N|²      noise energy retained
D     = (under − over) / (under + over)      ∈ [−1, +1]
```

`D = −1` is pure over-suppression. `D = +1` is pure under-suppression. Because the mask comes off the output waveform, you can run this on time-domain models, generative models and passthrough alike, with no access to model internals.

Three analytic endpoints pin the index down, and `tests/` enforces all three:

| Enhancer | Expected |
|---|---|
| `y = x` (passthrough) | `over ≈ 0`, `under ≈ 1`, `D ≈ +1` |
| `y = 0` (silence) | `over ≈ 1`, `under ≈ 0`, `D ≈ −1` |
| ideal ratio mask | strictly between. This is the **oracle floor**. |

Every reported number is a delta against that floor. Skip it and low-SNR conditions masquerade as over-suppression failures when they are simply hard.

## 🎯 Three claims, in order

| | Claim | What it establishes |
|---|---|---|
| 1️⃣ | **Characterize** | The two failure modes are real and separable by exact energy decomposition. |
| 2️⃣ | **Explain** | The two noise families leave distinct failure signatures across SNR. |
| 3️⃣ | **Predict** | A reference-free input-side measurement forecasts direction and magnitude under unseen noise. |

Claims 1 and 2 stand on their own if Claim 3 fails. Claim 3 carries the citable contribution and the most risk. [`docs/GATE.md`](docs/GATE.md) holds the pre-committed thresholds that decide whether it gets built at all.

> ⚠️ **One caveat, stated up front.** Clean references *are* used during **training**, to construct the directional labels. At **inference** the predictor sees only the noisy input. `src/failure_direction/direction/` is a labelling tool and is not reference-free. The predictor that consumes its output is. Please don't conflate them.

## 🧪 Baselines

Four enhancers, one compute budget, identical STFT framing:

| | Model | Role |
|---|---|---|
| 1 | STFT magnitude mask (BLSTM) | the mask is the object of study |
| 2 | Causal GRU mask | streaming-plausible, small budget |
| 3 | Spectral/generative (SGMSE-style) | external, see `models/diffusion.py` for why |
| 4 | Passthrough | the floor everything else is measured against |

Equal budget means **equal gradient steps**, never equal epochs. The families differ in size, so counting epochs hands one fold roughly 50% more updates and quietly voids the comparison.

## 🌊 Data

[MarVEN](https://doi.org/10.5281/zenodo.20714212): paired clean/noisy marine speech, 5 noise conditions across 2 families, 8 SNR levels from −15 to +20 dB.

| Family | Conditions |
|---|---|
| 🌧️ weather | `rainfall`, `lightning`, `hurricane` |
| 🚢 anthropogenic | `bubble_curtain`, `large_commercial_ship` |

Train on one family, test on the other. That's the shift axis.

Two structural facts shape everything downstream. The shipped `split` column separates speakers but **not** noise types, so all five conditions appear in all three splits and the folds need rebuilding. And each clean utterance appears exactly twice under two different noise types, so no utterance spans all five conditions. The direction index therefore aggregates across the corpus rather than comparing within an utterance.

## 🚀 Quickstart

```bash
git clone https://github.com/rana-rishith/failure-direction.git
cd failure-direction

py -3.11 -m venv .venv && .venv\Scripts\Activate.ps1     # Windows
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -e ".[metrics,asr,viz,dev]"
pytest                                                    # 6 tests, no GPU needed
```

Then [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) to publish it and [`docs/STAGE0.md`](docs/STAGE0.md) to run it. The environment notes assume an RTX 3060 12 GB (Ampere, sm_86) and Python 3.11 or 3.12. Avoid 3.13, where `pesq` has no usable Windows wheel.

## 🗂️ Layout

```
configs/            one YAML per experiment; nothing is hardcoded
data/manifests/     inventory.csv + integrity.csv, the single source of truth
src/failure_direction/
  direction/        the energy decomposition and the oracle floor
  models/           four baselines behind one registry
  metrics/          PESQ / STOI / SI-SDR / WER, with the traps handled
  data/             manifest building, cross-family speaker-disjoint splits
scripts/            numbered entrypoints, run in order
docs/GATE.md        the pre-committed go/no-go criteria
results/            CSVs and figures, committed
runs/               checkpoints and logs, gitignored
```

## 🛣️ Roadmap

- [x] Direction index with analytic sanity checks
- [x] Oracle floor
- [x] Cross-family, speaker-disjoint splits
- [ ] Stage 0: MarVEN downloaded, manifest built, mixture identity verified
- [ ] Stage 1: 4 models × 2 folds × 3 seeds, per-utterance scoring
- [ ] Gate evaluated once, decision committed
- [ ] Stage 2: the reference-free predictor (Claim 3)
- [ ] Second-corpus validation

## 📖 Citing

See [`CITATION.cff`](CITATION.cff).

## 📄 License

MIT.
