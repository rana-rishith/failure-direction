"""
WER pipeline — the downstream consequence of Claim 1.

    python -m src.wer --snr-max -5            # the 818-row paper subset
    python -m src.wer --limit 20 --engine stub  # pipeline smoke test, no GPU/ASR

Four arms per row: clean, noisy (the B4 floor), b1_matched, b1_unseen.

Reported as a downstream consequence of Claim 1, NOT as gate G3: it cannot
attribute consequences to failure DIRECTION rather than to condition, because
direction and condition are collinear.

Four load-bearing decisions:
  1. Ground-truth LibriSpeech transcripts, not Whisper-on-clean pseudo-refs.
     MarVEN's clean audio is amplitude-scaled train-clean-100 (scale =
     1/mix_scale, content bit-identical), so real WER is recoverable.
  2. Re-run B1 inference and pipe straight into the ASR. Do NOT reconstruct from
     saved fp16 masks — rounding perturbs the waveform.
  3. Greedy, temperature 0.0, all fallback thresholds disabled,
     condition_on_previous_text=False. Prompt carryover on a shuffled corpus
     fabricates context, and the temperature fallback makes high-noise rows
     non-reproducible.
  4. The text normaliser is applied to BOTH sides, inside a single scoring
     function, so the two sides cannot drift apart. Scoring un-normalised
     hypotheses against a normalised reference inflated the clean arm from
     1.38% to 3.07% — a 3x error.

Peak-normalise only the waveform going INTO the ASR, never the waveform going
into B1: B1 consumes log1p(|X|), which is scale-sensitive, so renormalising its
input puts it off-distribution and you are no longer transcribing the system
evaluated in Stage 2.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import config as C
from src import data as D
from src import models as M

ARMS = ("clean", "noisy", "b1_matched", "b1_unseen")
COUNT_PREFIXES = {"S", "D", "I", "err", "nhyp", "n"}


# ------------------------------------------------------------- transcripts ---
def load_transcripts(trans_dir: Path | None = None) -> dict[str, str]:
    """`trans_dir` is the transcript DIRECTORY; the returned dict is
    `transcripts`. Keeping the two names distinct matters — the collision cost
    time once already."""
    trans_dir = trans_dir or C.TRANS_DIR
    if not trans_dir.exists():
        raise FileNotFoundError(
            f"LibriSpeech transcripts not found at FAILDIR_TRANS={trans_dir}. "
            "Download train-clean-100 (see README > Dataset)."
        )
    out: dict[str, str] = {}
    for p in trans_dir.rglob("*.trans.txt"):
        for line in p.read_text(encoding="utf-8").splitlines():
            k, _, txt = line.partition(" ")
            if k:
                out[k] = txt
    if not out:
        raise ValueError(f"no *.trans.txt files under {trans_dir}")
    return out


def check_coverage(df: pd.DataFrame, transcripts: dict[str, str],
                   split: str = "test") -> dict:
    need = set(df[df.split == split].key)
    missing = need - set(transcripts)
    return {"unique_utterances": len(need), "missing": len(missing),
            "examples": sorted(missing)[:5]}


# -------------------------------------------------------------- normaliser ---
def get_normalizer():
    try:
        from transformers.models.whisper.english_normalizer import EnglishTextNormalizer
        return EnglishTextNormalizer({})
    except Exception:  # noqa: BLE001
        try:
            from whisper.normalizers import EnglishTextNormalizer
            return EnglishTextNormalizer()
        except Exception:  # noqa: BLE001
            import re
            import unicodedata

            def basic(s: str) -> str:
                s = unicodedata.normalize("NFKC", s).lower()
                s = re.sub(r"[^a-z0-9' ]+", " ", s)
                return re.sub(r"\s+", " ", s).strip()

            print("WARNING: falling back to a basic text normaliser. Install "
                  "`transformers` or `openai-whisper` for EnglishTextNormalizer; "
                  "absolute WER will not match the paper numbers.")
            return basic


# ------------------------------------------------------------------ scoring --
def score(ref_text: str, hyp_text: str, normalizer) -> dict[str, int]:
    """
    Single place where normalisation happens. BOTH sides, always. Never score a
    raw hypothesis against a normalised reference.
    """
    import jiwer

    ref = normalizer(ref_text)
    hyp = normalizer(hyp_text)
    o = jiwer.process_words([ref], [hyp])
    return {"S": o.substitutions, "D": o.deletions, "I": o.insertions,
            "n_ref": len(ref.split()), "n_hyp": len(hyp.split())}


# ------------------------------------------------------------- ASR backends --
class WhisperBackend:
    """faster-whisper large-v3, int8_float16, deterministic decode."""

    def __init__(self, model_size: str = "large-v3", compute_type: str = "int8_float16",
                 device: str | None = None):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_size, device=device or C.device(),
                                  compute_type=compute_type)

    def __call__(self, x: np.ndarray) -> str:
        segs, _ = self.model.transcribe(
            x, language="en", beam_size=1, temperature=0.0,
            compression_ratio_threshold=None, log_prob_threshold=None,
            no_speech_threshold=None, condition_on_previous_text=False,
            vad_filter=False, without_timestamps=True)
        return " ".join(s.text for s in segs)


class StubBackend:
    """
    Deterministic fake ASR for pipeline testing without a GPU: returns the
    reference with a fraction of words dropped, scaled by how noisy the input is.
    Produces structurally valid WER rows and nothing more.
    """

    def __init__(self, reference_provider):
        self.ref_of = reference_provider

    def __call__(self, x: np.ndarray) -> str:
        words = self.ref_of().split()
        if not words:
            return ""
        rms = float(np.sqrt((x.astype(np.float64) ** 2).mean()) + 1e-9)
        drop = min(0.6, max(0.0, (rms - 0.05) * 2))
        keep = [w for i, w in enumerate(words) if (i * 7919) % 1000 >= drop * 1000]
        return " ".join(keep) or words[0]


# ------------------------------------------------------------------- input ---
def peak_normalise(x: np.ndarray, peak: float = 0.95) -> np.ndarray:
    a = float(np.abs(x).max())
    return (x * (peak / a)).astype(np.float32) if a > 0 else x.astype(np.float32)


@torch.no_grad()
def enhance(x: np.ndarray, model, device: str | None = None) -> np.ndarray:
    dev = device or C.device()
    t = torch.from_numpy(np.ascontiguousarray(x)).float().unsqueeze(0).to(dev)
    return model(t)[0].squeeze(0).cpu().numpy()


# -------------------------------------------------------------------- run ----
def run(df: pd.DataFrame | None = None, transcripts: dict | None = None,
        engine: str = "whisper", snr_max: int | None = None, limit: int | None = None,
        out_path: Path | None = None, resume: bool = True, arch: str = "b1") -> pd.DataFrame:
    C.ensure_dirs()
    df = df if df is not None else D.load_manifest()
    rows = df[df.split == "test"].reset_index(drop=True)
    if snr_max is not None:
        rows = rows[rows.target_snr_db <= snr_max].reset_index(drop=True)
    if limit:
        rows = rows.head(limit).reset_index(drop=True)

    out_path = out_path or (C.EVAL / ("wer_rows.csv" if snr_max is None
                                      else f"wer_snrmax{snr_max}.csv"))
    transcripts = transcripts if transcripts is not None else load_transcripts()
    normalizer = get_normalizer()

    models = {fam: M.load_model(arch, f"{arch}_{fam}") for fam in C.FAMILIES}

    current_ref = {"text": ""}
    asr = StubBackend(lambda: current_ref["text"]) if engine == "stub" else WhisperBackend()

    done: set[str] = set()
    if resume and out_path.exists():
        prev = pd.read_csv(out_path)
        prev = prev[prev.row_key != "row_key"]           # strip repeated append headers
        done = set(prev.row_key)
        print(f"resuming, already done: {len(done)}")

    clean_cache: dict[str, dict] = {}
    buf, t0 = [], time.time()
    print(f"rows {len(rows)} | engine {engine} | out {out_path.name}")

    for i, r in enumerate(rows.itertuples()):
        row_key = r.uid
        if row_key in done:
            continue
        ref_text = transcripts[r.key]
        current_ref["text"] = normalizer(ref_text) if callable(normalizer) else ref_text

        xn = D.read_mono(r.noisy_path)
        xc = D.read_mono(r.clean_path)
        other = "anthro" if r.family == "weather" else "weather"

        waves = {
            "clean": peak_normalise(xc),
            "noisy": peak_normalise(xn),
            f"{arch}_matched": peak_normalise(enhance(xn, models[r.family])),
            f"{arch}_unseen": peak_normalise(enhance(xn, models[other])),
        }

        rec = {"row_key": row_key, "key": r.key, "noise_type": r.noise_type,
               "family": r.family, "snr": int(r.target_snr_db)}
        for arm, w in waves.items():
            # The clean arm is cached per utterance: each utterance appears twice
            # in MarVEN. Safe because the ASR input is peak-normalised, which
            # removes the per-row mix_scale difference between the two copies.
            if arm == "clean" and r.key in clean_cache:
                s = clean_cache[r.key]
            else:
                s = score(ref_text, asr(w), normalizer)
                if arm == "clean":
                    clean_cache[r.key] = s
            rec["n_ref"] = s["n_ref"]
            rec[f"S_{arm}"], rec[f"D_{arm}"], rec[f"I_{arm}"] = s["S"], s["D"], s["I"]
            rec[f"nhyp_{arm}"] = s["n_hyp"]
            rec[f"err_{arm}"] = s["S"] + s["D"] + s["I"]
        buf.append(rec)

        if len(buf) >= 25:
            _append(buf, out_path)
            buf = []
            el = (time.time() - t0) / 60
            print(f"{i+1}/{len(rows)}  {el:.1f}m  "
                  f"~{el/(i+1)*(len(rows)-i-1):.0f}m left", flush=True)

    if buf:
        _append(buf, out_path)
    print(f"complete in {(time.time()-t0)/60:.1f} min -> {out_path}")
    return read_wer(out_path)


def _append(buf: list[dict], path: Path) -> None:
    pd.DataFrame(buf).to_csv(path, mode="a", header=not path.exists(), index=False)


def read_wer(path: Path) -> pd.DataFrame:
    h = pd.read_csv(path)
    h = h[h.row_key != "row_key"].drop_duplicates("row_key")
    for c in h.columns:
        if c.split("_")[0] in COUNT_PREFIXES or c in ("snr", "n_ref"):
            h[c] = pd.to_numeric(h[c], errors="coerce")   # never errors="ignore" (pandas 3)
    return h


# ------------------------------------------------------------- aggregation ---
def corpus_wer(g: pd.DataFrame, arms=ARMS) -> pd.Series:
    """Corpus-level WER: total edits over total reference words. Not the mean of
    per-utterance rates."""
    return pd.Series({a: 100 * g[f"err_{a}"].sum() / g.n_ref.sum()
                      for a in arms if f"err_{a}" in g.columns})


def aggregate(h: pd.DataFrame, arms=ARMS) -> dict[str, pd.DataFrame]:
    present = [a for a in arms if f"err_{a}" in h.columns]
    overall = corpus_wer(h, present).round(2).to_frame("wer_pct")

    by_type_snr = (h.groupby(["noise_type", "snr"])[[f"err_{a}" for a in present] + ["n_ref"]]
                   .sum())
    for a in present:
        by_type_snr[a] = (100 * by_type_snr[f"err_{a}"] / by_type_snr.n_ref).round(2)
    by_type_snr = by_type_snr[present]

    hallu = []
    for a in present:
        if a == "clean":
            continue
        ratio = h[f"nhyp_{a}"] / h.n_ref
        hallu.append({"arm": a, "hyp_ref_median": round(float(ratio.median()), 2),
                      "over_2x": int((ratio > 2).sum()), "n": len(h),
                      "insertion_pct": round(100 * h[f"I_{a}"].sum() / h.n_ref.sum(), 2)})

    delta = by_type_snr.copy()
    if {"noisy", "b1_matched", "b1_unseen"} <= set(present):
        delta["delta_matched"] = (delta.noisy - delta.b1_matched).round(2)
        delta["delta_unseen"] = (delta.noisy - delta.b1_unseen).round(2)

    print("\n=== corpus WER by arm ===")
    print(overall.to_string())
    print("\n=== noise_type x snr (never pool: hurricane and bubble_curtain sit at "
          "the clean floor even at -15 dB) ===")
    print(by_type_snr.round(2).to_string())
    print("\n=== hallucination / insertion rate ===")
    print(pd.DataFrame(hallu).to_string(index=False))

    C.ensure_dirs()
    overall.to_csv(C.METRICS / "wer_overall.csv")
    by_type_snr.round(2).to_csv(C.METRICS / "wer_by_type_snr.csv")
    pd.DataFrame(hallu).to_csv(C.METRICS / "wer_hallucination.csv", index=False)
    delta.round(2).to_csv(C.METRICS / "wer_delta_vs_passthrough.csv")
    return {"overall": overall, "by_type_snr": by_type_snr,
            "hallucination": pd.DataFrame(hallu), "delta": delta}


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="WER evaluation")
    p.add_argument("--snr-max", type=int, default=None,
                   help="restrict to rows at or below this target SNR (paper subset: -5)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--engine", choices=["whisper", "stub"], default="whisper")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--aggregate-only", default=None, help="path to an existing wer CSV")
    a = p.parse_args(argv)

    if a.aggregate_only:
        aggregate(read_wer(Path(a.aggregate_only)))
        return
    h = run(engine=a.engine, snr_max=a.snr_max, limit=a.limit, resume=not a.no_resume)
    aggregate(h)


if __name__ == "__main__":
    main()
