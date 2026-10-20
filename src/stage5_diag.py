"""Stage 5 post-overnight diagnostics (CPU only, reads results already on disk).

1. R3 per-file distribution: is anthro-on-DeepShip noise removal graded or bimodal?
   Split by DeepShip class, SNR, and source recording.
2. Family control: anthro vs weather models on the same external mixtures
   (deepship_ship, deepship_tug, mbari_dry, mbari_storm, DEMAND, VB-DMD).
3. Full xcorpus matrix, seed-averaged, with LOTO R1 split into heard-weather vs anthro.

Outputs: results/xcorpus/diag/*.csv and diag.md
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd

R = Path("results")
OUT = R / "xcorpus" / "diag"
OUT.mkdir(parents=True, exist_ok=True)
WEATHER = ("rainfall", "lightning", "hurricane")
ANTHRO = ("bubble_curtain", "large_commercial_ship")


def nr(f, b="_g"):
    return 1 - f["r_under" + b] / f.r_under_b4


def d(f, b="_g"):
    ro, ru = f["r_over" + b], f["r_under" + b]
    return (ro - ru) / (ro + ru + 1e-8)


def arch(t):
    return t.split("_")[0]


def fam(t):
    for k in ("anthro", "weather", "demand"):
        if k in t:
            return k
    m = re.search(r"loto_(\w+?)(?:_s\d+)?$", t)
    return f"loto_{m.group(1)}" if m else "other"


def seed(t):
    m = re.search(r"_s(\d)$", t)
    return int(m.group(1)) if m else 1


def bimodality(x):
    x = np.asarray(x, float); n = len(x)
    m = x.mean(); s = x.std()
    g = ((x - m) ** 3).mean() / s ** 3
    k = ((x - m) ** 4).mean() / s ** 4 - 3
    bc = (g ** 2 + 1) / (k + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
    return bc  # > 0.555 suggests bimodality (Sarle)


lines = ["# Stage 5 overnight diagnostics", ""]

# ---------- 1. R3 per-file ----------
r3 = []
for run in ("r3", "r3_s2", "r3_s3"):
    f = pd.read_csv(R / run / "R3_deepship.csv")
    f["run"] = run
    r3.append(f)
r3 = pd.concat(r3, ignore_index=True)
r3["nr_g"] = nr(r3); r3["d_g"] = d(r3)
r3["src_file"] = r3.noise_src.str.split("@").str[0]
r3["cls"] = r3.src_file.str.split("/").str[0]
r3["arch"] = r3.tag.map(arch)
r3["sisdr_gain"] = r3.sisdr_out - r3.sisdr_in

bins = [-np.inf, 0.2, 0.5, 0.8, np.inf]
lab = ["<0.2", "0.2-0.5", "0.5-0.8", ">0.8"]
r3["band"] = pd.cut(r3.nr_g, bins, labels=lab)
dist = r3.groupby("arch").band.value_counts(normalize=True).unstack()[lab].round(3)
bc = r3.groupby("arch").nr_g.apply(lambda x: bimodality(x.clip(-1, 1))).round(3)
dist["sarle_bc"] = bc
dist["median"] = r3.groupby("arch").nr_g.median().round(3)
dist.to_csv(OUT / "r3_distribution.csv")
hist = r3.groupby("arch").nr_g.apply(lambda x: np.histogram(x.clip(-0.2, 1.0), bins=np.linspace(-0.2, 1.0, 13))[0])
lines += ["## 1. R3 (anthro models on DeepShip ship), per-row nr_g, 3 seeds pooled", "",
          dist.to_string(), "", "Histogram, 12 bins from -0.2 to 1.0:", ""]
for a, h in hist.items():
    lines.append(f"  {a:3s} " + " ".join(f"{v:4d}" for v in h))
lines.append("")

bysnr = r3.groupby(["arch", "snr"]).nr_g.agg(["median", lambda x: x.quantile(.25), lambda x: x.quantile(.75)])
bysnr.columns = ["median", "q25", "q75"]
bysnr = bysnr.round(3).unstack("arch")
bysnr.to_csv(OUT / "r3_by_snr.csv")
lines += ["### by SNR (median [q25, q75])", "", bysnr.to_string(), ""]

# within-SNR distribution (does the spread vanish once SNR is fixed?)
r3["nr_resid_snr"] = r3.nr_g - r3.groupby(["arch", "run", "snr"]).nr_g.transform("median")
bycls = r3.groupby(["cls", "arch"]).agg(n=("nr_g", "size"), nr_g=("nr_g", "median"), resid=("nr_resid_snr", "median"),
                                        d_g=("d_g", "median"), gain=("sisdr_gain", "median")).round(3)
bycls.to_csv(OUT / "r3_by_class.csv")
lines += ["### by DeepShip class (resid = median nr_g minus the SNR-cell median)", "", bycls.to_string(), ""]

# source-recording effect: share of SNR-residual variance explained by source file
rows = []
for a, g in r3.groupby("arch"):
    tot = g.nr_resid_snr.var()
    between = g.groupby("src_file").nr_resid_snr.transform("mean").var()
    filemed = g.groupby("src_file").nr_resid_snr.median()
    rows.append(dict(arch=a, n_files=g.src_file.nunique(), var_resid=round(tot, 4),
                     share_between_files=round(between / tot, 3),
                     file_resid_min=round(filemed.min(), 3), file_resid_max=round(filemed.max(), 3)))
fe = pd.DataFrame(rows).set_index("arch")
fe.to_csv(OUT / "r3_file_effect.csv")
lines += ["### source-recording effect (after removing SNR-cell median)", "", fe.to_string(), ""]
fm = r3.groupby(["src_file", "arch"]).nr_resid_snr.median().unstack().round(3)
fm["cls"] = fm.index.str.split("/").str[0]
fm.sort_values("b1").to_csv(OUT / "r3_by_file.csv")
# cross-architecture agreement on which recordings are easy
c = fm[["b1", "b3", "cm"]].corr(method="spearman").round(3)
lines += ["Spearman across files of per-file residual (do architectures agree on which recordings transfer?):", "",
          c.to_string(), ""]

# ---------- 2. family control on xcorpus ----------
ev = pd.concat([pd.read_csv(f) for f in sorted((R / "xcorpus" / "eval").glob("*.csv"))], ignore_index=True)
ev["nr_g"] = nr(ev); ev["d_g"] = d(ev); ev["sisdr_gain"] = ev.sisdr_out - ev.sisdr_in
ev["arch"] = ev.tag.map(arch); ev["fam"] = ev.tag.map(fam); ev["seed"] = ev.tag.map(seed)
ev = ev[~ev.tag.str.contains("seg_")]


def cond2(row_cond, nt, family):
    if row_cond != "marven":
        return row_cond
    if nt in WEATHER:
        return "marven_weather"
    return "marven_anthro"


ev["cond2"] = [cond2(c, n, f) for c, n, f in zip(ev.cond, ev.noise_type, ev.fam)]
# per-tag medians, then mean over seeds
tm = ev.groupby(["arch", "fam", "seed", "cond2"])[["nr_g", "d_g", "sisdr_gain"]].median()
sm = tm.groupby(["arch", "fam", "cond2"]).agg(["mean", "std"])
order = ["marven_anthro", "marven_weather", "deepship_ship", "deepship_tug", "mbari_dry", "mbari_storm",
         "dem_A", "dem_B", "dem_H", "vbdmd_test"]
nrm = sm[("nr_g", "mean")].unstack("cond2")[order].round(3)
nrm.to_csv(OUT / "matrix_nr_g.csv")
dm = sm[("d_g", "mean")].unstack("cond2")[order].round(3)
dm.to_csv(OUT / "matrix_d_g.csv")
gm = sm[("sisdr_gain", "mean")].unstack("cond2")[order].round(2)
gm.to_csv(OUT / "matrix_sisdr_gain.csv")
lines += ["## 2. Full xcorpus matrix, nr_g (median per checkpoint, mean over seeds; seg models excluded)", "",
          nrm.to_string(), "", "### d_g", "", dm.to_string(), "", "### SI-SDR gain (dB)", "", gm.to_string(), ""]

# family bonus: anthro minus weather, per arch, per seed paired
fb = []
for a in ("b1", "b3", "cm"):
    for s in (1, 2, 3):
        an = tm.loc[(a, "anthro", s)].nr_g; we = tm.loc[(a, "weather", s)].nr_g
        r = (an - we).to_dict(); r.update(arch=a, seed=s); fb.append(r)
fb = pd.DataFrame(fb)
fbs = fb.groupby("arch")[order].agg(["mean", "min", "max"]).round(3)
fb_mean = fb.groupby("arch")[order].mean().round(3)
fb_rng = fb.groupby("arch")[order].agg(lambda x: f"{x.min():+.2f}..{x.max():+.2f}")
fb_mean.to_csv(OUT / "family_bonus_nr_g.csv")
lines += ["## 3. Family bonus: nr_g(anthro model) - nr_g(weather model), same mixtures, seed-paired", "",
          "mean over 3 seeds:", "", fb_mean.to_string(), "", "range over seeds:", "", fb_rng.to_string(), ""]

# family bonus by SNR for the key external conds
key = ["deepship_ship", "deepship_tug", "mbari_dry", "mbari_storm"]
ts = ev[ev.cond.isin(key) & ev.fam.isin(["anthro", "weather"])].groupby(["arch", "fam", "seed", "cond", "snr"]).nr_g.median()
ts = ts.groupby(["fam", "cond", "snr"]).mean().unstack("fam")
ts["bonus"] = ts.anthro - ts.weather
tsb = ts.round(3)
tsb.to_csv(OUT / "family_bonus_by_snr.csv")
lines += ["### family bonus by SNR (all archs and seeds averaged)", "", tsb.unstack("cond")["bonus"].round(3).to_string(), ""]

# ---------- 4. LOTO with R1 split ----------
lo = ev[ev.fam.str.startswith("loto")].copy()
lo["held"] = lo.fam.str[5:]


def loto_cond(r):
    if r.cond != "marven":
        return r.cond
    if r.noise_type == r.held:
        return "heldout_weather"
    return "heard_weather" if r.noise_type in WEATHER else "anthro_unheard"


lo["c"] = lo.apply(loto_cond, axis=1)
lt = lo.groupby(["tag", "c"]).nr_g.median().unstack()[["heard_weather", "heldout_weather", "anthro_unheard", "deepship_ship",
                                                        "deepship_tug", "mbari_dry", "mbari_storm", "dem_A", "dem_H", "vbdmd_test"]].round(3)
lt.to_csv(OUT / "loto_split.csv")
lines += ["## 4. LOTO models with MarVEN split into heard weather / held-out weather / anthro (report's R1 pooled these)", "",
          lt.to_string(), ""]
lnt = lo[lo.cond == "marven"].groupby(["tag", "noise_type"]).nr_g.median().unstack().round(3)
lines += ["per MarVEN type:", "", lnt.to_string(), ""]
lnt.to_csv(OUT / "loto_by_type.csv")

(OUT / "diag.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
