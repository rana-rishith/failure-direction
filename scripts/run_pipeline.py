"""
The whole pipeline, in order, in one command.

    python scripts/run_pipeline.py                 # full protocol (20k steps/run)
    python scripts/run_pipeline.py --smoke         # 40 steps/run, for verification
    python scripts/run_pipeline.py --from evaluate # resume at a later stage
    python scripts/run_pipeline.py --with-wer      # add the ASR stage (needs Whisper)

Stage order:
    verify_env -> verify_data -> train -> evaluate -> analysis
               -> labels -> features -> claim3 [-> wer]

Every stage is idempotent: finished checkpoints resume, finished CSVs are
skipped unless their row count disagrees with the fold they came from.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import config as C  # noqa: E402

STAGES = ("verify_env", "verify_data", "train", "evaluate", "analysis",
          "labels", "features", "claim3", "wer")


def run(cmd: list[str]) -> None:
    print(f"\n{'='*72}\n$ {' '.join(cmd)}\n{'='*72}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(f"\nSTAGE FAILED ({r.returncode}): {' '.join(cmd)}")
    print(f"[{(time.time()-t0)/60:.1f} min]")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true",
                   help="40 training steps per run — verifies wiring, not results")
    p.add_argument("--from", dest="start", default="verify_env", choices=STAGES)
    p.add_argument("--with-wer", action="store_true")
    p.add_argument("--no-pesq", action="store_true")
    p.add_argument("--workers", type=int, default=0)
    a = p.parse_args()

    py = sys.executable
    steps = 40 if a.smoke else C.TRAIN_STEPS
    val_every = 20 if a.smoke else C.VAL_EVERY
    start = STAGES.index(a.start)

    def want(stage: str) -> bool:
        return STAGES.index(stage) >= start

    if want("verify_env"):
        run([py, "scripts/00_verify_env.py"])
    if want("verify_data"):
        run([py, "scripts/01_verify_data.py"])
    if want("train"):
        for model in ("b1", "b3"):
            for fold in C.FAMILIES:
                run([py, "-m", "src.train", "--model", model, "--fold", fold,
                     "--steps", str(steps), "--val-every", str(val_every),
                     "--workers", str(a.workers)])
    if want("evaluate"):
        run([py, "-m", "src.evaluate"] + (["--no-pesq"] if a.no_pesq else []))
    if want("analysis"):
        run([py, "-m", "src.analysis"])
    if want("labels"):
        run([py, "-m", "src.labels"])
    if want("features"):
        run([py, "-m", "src.features"])
    if want("claim3"):
        run([py, "-m", "src.claim3", "--precondition"])
        for fold in C.FAMILIES:
            run([py, "-m", "src.claim3", "--fold", fold])
    if a.with_wer and want("wer"):
        run([py, "-m", "src.wer", "--snr-max", "-5"])

    print(f"\npipeline complete. tables in {C.METRICS}")


if __name__ == "__main__":
    main()
