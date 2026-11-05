"""Rescore every existing model through probe() so one implementation produces
every number.

    python -m src.probe.rescore                  # all tags in the reference CSV
    python -m src.probe.rescore --tags b1_weather cm_anthro
    python -m src.probe.rescore --wav-dir-root out   # DFN3 / SGMSE+ wav dirs

Resumable: a tag whose rows.csv already has the full split is skipped. Enhancers
that cannot run in this process (SGMSE+ has its own conda env) are scored from a
directory of enhanced wavs instead; see src.probe.probe(wav_dir=...).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import config as C  # noqa: I001  (must precede torch)

import numpy as np
import pandas as pd
import torch

from src.probe import (SPLIT_DIR, heard_types, load_split, model_fn, probe, summarise,
                       write_report)

REF = C.EVAL / "xcorpus" / "eval" / "marven.csv"
OUT = C.EVAL / "probe"


def uid_from_name(name: str) -> str:
    """`26-495-0000_hurricane_snr5[.wav]` -> `26-495-0000|hurricane|+5`.

    Noise types contain underscores, so split on the LAST `_snr` and the FIRST
    `_` of what precedes it. The utterance key uses dashes, never underscores.
    """
    stem = Path(name).stem
    head, _, snr = stem.rpartition("_snr")
    key, _, ntype = head.partition("_")
    return f"{key}|{ntype}|{int(float(snr)):+d}"


def map_from_dir(wav_dir) -> dict:
    """uid -> path for a directory whose wavs are named after the noisy file."""
    return {uid_from_name(p.name): p for p in Path(wav_dir).glob("*.wav")}


def map_from_index(wav_dir, index_csv) -> dict:
    """uid -> path when the enhancer named its outputs positionally. `index_csv`
    is the row list that drove the enhancement: a `name` column for the output
    and a `noisy` column whose filename carries key, noise type and SNR
    (results/labels_active/rows_dfn.csv is DFN3's). Reading the identity off the
    noisy path avoids reconstructing manifest row order, which src/data.py warns
    misaligns silently."""
    wav_dir = Path(wav_dir)
    idx = pd.read_csv(index_csv)
    for c in ("name", "noisy"):
        if c not in idx.columns:
            raise ValueError(f"{index_csv} has no {c!r} column (got {list(idx.columns)})")
    m = {}
    for name, noisy in zip(idx.name, idx.noisy):
        p = wav_dir / name
        if p.exists():
            m[uid_from_name(noisy)] = p
    return m


def reference_tags() -> list[str]:
    if not REF.exists():
        raise FileNotFoundError(f"{REF} missing — cannot tell which tags to rescore")
    return sorted(pd.read_csv(REF, usecols=["tag"]).tag.unique())




def done(tag: str, n: int) -> bool:
    """Complete means the rows AND the report: a tag whose summary.md is missing
    is rescored, so a failure part-way through writing never leaves a tag that
    looks finished."""
    d = OUT / tag
    rows, md = d / "rows.csv", d / "summary.md"
    try:
        return rows.exists() and md.exists() and len(pd.read_csv(rows, usecols=["uid"])) == n
    except Exception:
        return False


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="rescore existing models through probe()")
    p.add_argument("--tags", nargs="*", default=None)
    p.add_argument("--wav-dirs", nargs="*", default=None,
                   help="tag=path pairs for enhancers scored from wavs, e.g. sgmse=out/sgmse")
    p.add_argument("--wav-maps", nargs="*", default=None,
                   help="tag=path pairs whose wavs are named after the noisy file")
    p.add_argument("--name-index", default=None,
                   help="row list mapping positional output names to noisy paths "
                        "(e.g. results/labels_active/rows_dfn.csv); applies to --wav-maps")
    p.add_argument("--split", default="marven_test_v1")
    p.add_argument("--device", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--summaries-only", action="store_true",
                   help="recompute summary.csv and summary.md from each tag's saved "
                        "rows.csv, with no model and no GPU: for a change in the "
                        "summary layer, which must not cost a full rescore")
    a = p.parse_args(argv)

    dev = a.device or C.device()
    n = len(load_split(a.split))

    if a.summaries_only:
        spec = json.loads((SPLIT_DIR / f"{a.split}.json").read_text())
        tags = sorted(d.name for d in OUT.iterdir() if (d / "rows.csv").exists())
        for i, tag in enumerate(tags):
            rows = pd.read_csv(OUT / tag / "rows.csv")
            rep = {"rows": rows, "summary": summarise(rows, heard_types(tag)),
                   "split": a.split, "sha256": spec["sha256"],
                   "n": len(rows), "n_split": n, "coverage": len(rows) / n}
            write_report(rep, OUT / tag)
            print(f"[{i+1}/{len(tags)}] {tag}: summary rebuilt from {len(rows)} saved rows",
                  flush=True)
        print(f"\n{len(tags)} summaries rebuilt -> {OUT}")
        return
    only_wavs = bool(a.wav_dirs or a.wav_maps) and a.tags is None
    jobs: list[tuple[str, str | None, dict | None]] = [
        (t, None, None) for t in ([] if only_wavs else (a.tags or reference_tags()))]
    for spec in a.wav_dirs or []:
        tag, _, path = spec.partition("=")
        jobs.append((tag, path, None))
    for spec in a.wav_maps or []:
        tag, _, path = spec.partition("=")
        wm = map_from_index(path, a.name_index) if a.name_index else map_from_dir(path)
        if not wm:
            raise ValueError(f"{tag}: no wavs mapped from {path}")
        print(f"{tag}: mapped {len(wm)} wavs from {path}", flush=True)
        jobs.append((tag, None, wm))

    print(f"{len(jobs)} jobs, {n} rows each, device={dev}, out={OUT}\n", flush=True)
    t0 = time.time()
    for i, (tag, wav_dir, wav_map) in enumerate(jobs):
        if not a.force and done(tag, n):
            print(f"[{i+1}/{len(jobs)}] {tag}: already complete, skipping", flush=True)
            continue
        ts = time.time()
        try:
            kw = dict(split=a.split, device=dev, tag=tag,
                      heard_types=heard_types(tag), out=OUT / tag, log_every=0)
            if wav_map is not None:
                cov = wav_map.keys() & set(load_split(a.split).uid)
                print(f"  {tag}: {len(cov)}/{n} of the split covered", flush=True)
                rep = probe(wav_map=wav_map, **kw)
            elif wav_dir:
                rep = probe(wav_dir=wav_dir, **kw)
            else:
                rep = probe(model_fn(tag, dev), **kw)
        except Exception as ex:
            print(f"[{i+1}/{len(jobs)}] {tag}: FAILED {type(ex).__name__}: {ex}", flush=True)
            continue
        el = (time.time() - ts) / 60
        rest = (time.time() - t0) / 60 / (i + 1) * (len(jobs) - i - 1)
        print(f"[{i+1}/{len(jobs)}] {tag}: n={rep['n']} {el:.1f}m  ~{rest:.0f}m left", flush=True)
        if dev == "cuda":
            torch.cuda.empty_cache()
    print(f"\ndone in {(time.time() - t0) / 60:.1f}m -> {OUT}")


if __name__ == "__main__":
    main()
