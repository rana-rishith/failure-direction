"""probe CLI.

    python -m src.probe --freeze-split
    python -m src.probe --model b1_weather --out results/probe/b1_weather/
    python -m src.probe --wav-dir out/sgmse --tag sgmse --out results/probe/sgmse/

--model loads a repo checkpoint with src.models.load_model(arch, tag, kind="best"),
where arch is the tag's first underscore field. Heard noise types are taken from
the tag's family field, so the gate classes get their R1 reference.
"""

from __future__ import annotations

import argparse

import config as C  # noqa: I001  (must precede torch)

import numpy as np
import torch

from src.probe import SPLIT_DIR, freeze_split, heard_types, model_fn, probe


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="failure-direction probe")
    p.add_argument("--model", help="repo checkpoint tag, e.g. b1_weather")
    p.add_argument("--wav-dir", help="directory of enhanced wavs named by uid")
    p.add_argument("--tag", default=None, help="label for the output rows")
    p.add_argument("--split", default="marven_test_v1")
    p.add_argument("--out", default=None)
    p.add_argument("--limit", type=int, default=None, help="first N rows (smoke runs)")
    p.add_argument("--device", default=None)
    p.add_argument("--freeze-split", action="store_true",
                   help="write configs/splits/<split>.json and exit")
    p.add_argument("--overwrite-split", action="store_true")
    a = p.parse_args(argv)

    if a.freeze_split:
        path = freeze_split(a.split, overwrite=a.overwrite_split)
        import json
        spec = json.loads(path.read_text())
        print(f"{path}  n={spec['n']}  sha256={spec['sha256']}")
        return

    if (a.model is None) == (a.wav_dir is None):
        p.error("pass exactly one of --model or --wav-dir")

    dev = a.device or C.device()
    tag = a.tag or a.model or "wavdir"
    out = a.out or (C.EVAL / "probe" / tag)

    if a.model:
        rep = probe(model_fn(a.model, dev), split=a.split, device=dev, tag=tag,
                    heard_types=heard_types(a.model), limit=a.limit, out=out)
    else:
        rep = probe(wav_dir=a.wav_dir, split=a.split, device=dev, tag=tag,
                    heard_types=heard_types(tag), limit=a.limit, out=out)

    print(f"\n{tag}: n={rep['n']} split={rep['split']} sha256={rep['sha256'][:16]}...")
    s = rep["summary"]
    cols = [c for c in ("noise_type", "snr_band", "n", "rung", "d_g", "nr_g",
                        "r_add", "delta_d", "class", "class_hp100") if c in s]
    print(s[cols].round(3).to_string(index=False))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
