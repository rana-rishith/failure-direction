"""Resumable DeepFilterNet3 zero-shot enhancement for MarVEN files.

DeepFilterNet3 runs at 48 kHz, so each 16 kHz file is resampled 16 -> 48 kHz,
enhanced, and resampled back to 16 kHz. Output length matches the input.

Run with the dfnet env active, from the sgmse folder:
    python <path>\\dfn_enhance.py --test_dir pilot_in --enhanced_dir dfn_out
"""
import csv
import glob
import os
import time
from argparse import ArgumentParser
from os.path import exists, join, relpath

import soundfile as sf
import torch
import torchaudio.functional as AF
from df.enhance import enhance, init_df


def main():
    p = ArgumentParser()
    p.add_argument("--test_dir", required=True)
    p.add_argument("--enhanced_dir", required=True)
    p.add_argument("--model", default="DeepFilterNet3")
    args = p.parse_args()

    model, df_state, _ = init_df(args.model)
    model_sr = df_state.sr()
    print(f"model {args.model}, sr {model_sr}, cuda {torch.cuda.is_available()}")

    files = sorted(glob.glob(join(args.test_dir, "**", "*.wav"), recursive=True))
    os.makedirs(args.enhanced_dir, exist_ok=True)
    log_path = args.enhanced_dir.rstrip("\\/") + "_log.csv"
    new_log = not exists(log_path)
    log_f = open(log_path, "a", newline="")
    log = csv.writer(log_f)
    if new_log:
        log.writerow(["file", "seconds", "status"])

    todo = [f for f in files if not exists(join(args.enhanced_dir, relpath(f, args.test_dir)))]
    print(f"{len(files)} files, {len(files) - len(todo)} already done, {len(todo)} to go")

    for i, f in enumerate(todo, 1):
        rel = relpath(f, args.test_dir)
        out_path = join(args.enhanced_dir, rel)
        t0 = time.time()
        try:
            x, sr = sf.read(f, dtype="float32")
            n = len(x)
            xt = torch.from_numpy(x).unsqueeze(0)
            if sr != model_sr:
                xt = AF.resample(xt, sr, model_sr)
            with torch.no_grad():
                yt = enhance(model, df_state, xt)  # pads to compensate model delay
            if sr != model_sr:
                yt = AF.resample(yt, model_sr, sr)
            y = yt.squeeze(0).cpu().numpy()[:n]
            if len(y) < n:  # guard against off-by-a-few after resampling
                y = __import__("numpy").pad(y, (0, n - len(y)))
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            sf.write(out_path, y, sr)
            status = "ok"
        except Exception as e:  # keep going; the log records the failure
            status = f"fail: {str(e).splitlines()[0][:120]}"
        log.writerow([rel, round(time.time() - t0, 2), status])
        log_f.flush()
        if i % 50 == 0 or i == len(todo):
            print(f"{i}/{len(todo)}")

    log_f.close()
    print(f"done; log at {log_path}")


if __name__ == "__main__":
    main()