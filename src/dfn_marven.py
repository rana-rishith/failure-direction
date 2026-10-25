"""Resumable DeepFilterNet3 enhancement of the Claim 3 MarVEN rows (gate_claim3_active.yaml).

Reads results/labels_active/rows_dfn.csv (written by `python -m src.labels_active list`)
and writes one 16 kHz output per row, named <fold>__<split>__<row>.wav. Same
processing as src/dfn_enhance.py: 16 -> 48 kHz, enhance, 48 -> 16 kHz, trimmed or
padded to the input length. 16-bit WAV, as in src/dfn_enhance.py (about 9 GB
for all 22,754 rows; put --out on a drive with room).

Run with the dfnet env (no repo imports needed):
    python src\\dfn_marven.py --rows results\\labels_active\\rows_dfn.csv --out <dir>
"""
import csv
import os
import time
from argparse import ArgumentParser

import numpy as np
import soundfile as sf
import torch
import torchaudio.functional as AF
from df.enhance import enhance, init_df


def main():
    p = ArgumentParser()
    p.add_argument("--rows", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="DeepFilterNet3")
    a = p.parse_args()

    with open(a.rows, newline="") as f:
        rows = list(csv.DictReader(f))
    os.makedirs(a.out, exist_ok=True)
    todo = [r for r in rows if not os.path.exists(os.path.join(a.out, r["name"]))]
    print(f"{len(rows)} rows, {len(rows) - len(todo)} done, {len(todo)} to go", flush=True)
    if not todo:
        return

    model, df_state, _ = init_df(a.model)
    msr = df_state.sr()
    print(f"model {a.model}, sr {msr}, cuda {torch.cuda.is_available()}", flush=True)

    log_path = a.out.rstrip("\\/") + "_log.csv"
    new = not os.path.exists(log_path)
    lf = open(log_path, "a", newline="")
    log = csv.writer(lf)
    if new:
        log.writerow(["name", "seconds", "status"])

    t_start = time.time()
    for i, r in enumerate(todo, 1):
        out = os.path.join(a.out, r["name"])
        t0 = time.time()
        try:
            x, sr = sf.read(r["noisy"], dtype="float32")
            if x.ndim > 1:
                x = x.mean(axis=1)
            n = len(x)
            xt = torch.from_numpy(x).unsqueeze(0)
            if sr != msr:
                xt = AF.resample(xt, sr, msr)
            with torch.no_grad():
                yt = enhance(model, df_state, xt)
            if sr != msr:
                yt = AF.resample(yt, msr, sr)
            y = yt.squeeze(0).cpu().numpy()[:n]
            if len(y) < n:
                y = np.pad(y, (0, n - len(y)))
            tmp = out + ".part"
            sf.write(tmp, y, sr, subtype="PCM_16", format="WAV")
            os.replace(tmp, out)          # never leave a truncated .wav behind
            status = "ok"
        except Exception as e:  # keep going; the log records the failure
            status = f"fail: {str(e).splitlines()[0][:120]}"
        log.writerow([r["name"], round(time.time() - t0, 3), status])
        lf.flush()
        if i % 200 == 0 or i == len(todo):
            el = time.time() - t_start
            print(f"{i}/{len(todo)}  {el / 60:.1f} min, ~{el / i * (len(todo) - i) / 60:.0f} min left", flush=True)
    lf.close()
    print(f"done; log at {log_path}")


if __name__ == "__main__":
    main()
