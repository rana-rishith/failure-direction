"""SGMSE+ VB-DMD diagnostic: 2x2 swap of speech source (VCTK vs LibriSpeech) and
noise source (VB-DMD noise vs DEMAND dem_A noise), each at the VB file's own SNR.

  build: writes <sgmse>/diag_in/*.wav and <sgmse>/diag_ref/*.wav (+ diag_manifest.csv)
  score: SI-SDR in/out per file from <sgmse>/diag_out
numpy + soundfile only.
"""
import sys, zlib
from pathlib import Path
import numpy as np, pandas as pd, soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
SG = ROOT / "sgmse"
XC = ROOT / "repo-failure-direction" / "results" / "xcorpus"


def win(p):
    s = str(p)
    i = s.find("MAIN-failure-direction(ALL)")
    return ROOT / s[i + len("MAIN-failure-direction(ALL)") + 1:].replace("\\", "/") if i >= 0 else Path(s)


def pw(x):
    x = x - x.mean(); return float(np.mean(x ** 2))


def fit(n, L, seed):
    if len(n) < L:
        n = np.tile(n, int(np.ceil(L / len(n))))
    o = np.random.default_rng(seed).integers(0, len(n) - L + 1)
    return n[o:o + L]


def sisdr(e, r):
    e = e - e.mean(); r = r - r.mean(); a = np.dot(e, r) / np.dot(r, r); t = a * r
    return 10 * np.log10(np.sum(t ** 2) / np.sum((e - t) ** 2))


def build(n=10):
    vb = pd.read_csv(XC / "manifest_parts" / "vbdmd_test.csv").head(n)
    da = pd.read_csv(XC / "manifest_parts" / "dem_A.csv")
    da = da[da.snr >= 5].reset_index(drop=True)          # cleaner noise estimate not needed: noise = noisy - clean exactly
    (SG / "diag_in").mkdir(exist_ok=True); (SG / "diag_ref").mkdir(exist_ok=True)
    rows = []
    for i, r in vb.iterrows():
        vn, sr = sf.read(win(r.noisy)); vc, _ = sf.read(win(r.clean))
        vnoise = vn - vc
        snr = 10 * np.log10(pw(vc) / pw(vnoise))
        d = da.iloc[i]
        dn, _ = sf.read(win(d.noisy), dtype="float32"); dc, _ = sf.read(win(d.clean), dtype="float32")
        dnoise = (dn - dc).astype(np.float64); dc = dc.astype(np.float64)
        L = len(vc)
        lib = fit(dc, L, zlib.crc32(f"lib{i}".encode()))
        dno = fit(dnoise, L, zlib.crc32(f"dem{i}".encode()))

        def mk(c, nz):
            g = np.sqrt(pw(c) / (pw(nz) * 10 ** (snr / 10))); return c + g * nz

        variants = {
            "vb_pcm": (vn, vc, "PCM_16"),
            "vb_float": (vn, vc, "FLOAT"),
            "vctk_demA": (mk(vc, dno), vc, "FLOAT"),
            "libri_vbnoise": (mk(lib, vnoise), lib, "FLOAT"),
            "libri_demA": (mk(lib, dno), lib, "FLOAT"),
        }
        for k, (x, c, st) in variants.items():
            name = f"{i:02d}__{k}.wav"
            sf.write(SG / "diag_in" / name, x.astype(np.float32), sr, subtype=st)
            sf.write(SG / "diag_ref" / name, c.astype(np.float32), sr, subtype="FLOAT")
            rows.append(dict(file=name, idx=i, variant=k, vb_uid=r.uid, snr=round(snr, 2)))
    pd.DataFrame(rows).to_csv(SG / "diag_manifest.csv", index=False)
    print(f"{len(rows)} files -> {SG / 'diag_in'}")


def score():
    m = pd.read_csv(SG / "diag_manifest.csv")
    out = []
    for _, r in m.iterrows():
        p = SG / "diag_out" / r.file
        if not p.exists():
            continue
        x, _ = sf.read(SG / "diag_in" / r.file); c, _ = sf.read(SG / "diag_ref" / r.file); o, _ = sf.read(p)
        L = min(len(x), len(c), len(o))
        out.append(dict(r, sisdr_in=sisdr(x[:L], c[:L]), sisdr_out=sisdr(o[:L], c[:L]), out_vs_noisy=sisdr(o[:L], x[:L])))
    f = pd.DataFrame(out); f["gain"] = f.sisdr_out - f.sisdr_in
    f.to_csv(SG / "diag_scores.csv", index=False)
    print(f.groupby("variant")[["sisdr_in", "sisdr_out", "gain", "out_vs_noisy"]].median().round(2).to_string())
    print(f.pivot(index="idx", columns="variant", values="gain").round(1).to_string())


if __name__ == "__main__":
    {"build": build, "score": score}[sys.argv[1]]()
