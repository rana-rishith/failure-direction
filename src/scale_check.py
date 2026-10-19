"""Diagnostic: how loud is each model's output relative to the clean speech?

SI-SDR is scale-invariant, so training never fixes the output level. Bounded
masks (B1, B3) cannot exceed the input; the unbounded complex mask (cm) can.
If cm settles at a large gain, the energy split on the output STFT counts the
extra level as "energy beyond clean" (r_under), which is a level artefact,
not a failure. This prints, per model, on 30 matched and 30 unseen MarVEN rows:

    g    = <est, clean> / <clean, clean>   level of the clean component in the output (1 = right level)
    out_in = rms(est) / rms(noisy)

Usage, from the repo root (faildir env, FAILDIR_ROOT / FAILDIR_CKPT set):
    python -m src.scale_check
"""
import config as C  # noqa: I001

import numpy as np
import torch

from src import data as D
from src import models as M

TAGS = ("b1_weather", "b3_weather", "cm_weather", "cm_anthro", "cm_demand")
N = 30


@torch.no_grad()
def main():
    dev = C.device()
    df = D.load_manifest()
    test = df[df.split == "test"]
    print(f"{'model':<12}{'rows':<10}{'median g':>10}{'p10 g':>9}{'p90 g':>9}{'median out/in':>15}")
    for tag in TAGS:
        arch, fam = tag.split("_")
        model = M.load_model(arch, tag, kind="best", device=dev)
        groups = {"all": test} if fam == "demand" else {
            "matched": test[test.family == fam], "unseen": test[test.family != fam]}
        for name, rows in groups.items():
            g, r = [], []
            for row in rows.sample(N, random_state=C.SEED).itertuples():
                x, y = D.read_pair(row)
                est = model(torch.from_numpy(x)[None].to(dev))[0][0].float().cpu().numpy()
                yc = y - y.mean()
                g.append(float(np.dot(est - est.mean(), yc) / np.dot(yc, yc)))
                r.append(float(np.sqrt(np.mean(est ** 2)) / np.sqrt(np.mean(x ** 2))))
            print(f"{tag:<12}{name:<10}{np.median(g):>10.2f}{np.percentile(g, 10):>9.2f}"
                  f"{np.percentile(g, 90):>9.2f}{np.median(r):>15.2f}")


if __name__ == "__main__":
    main()
