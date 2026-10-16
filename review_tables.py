"""Numbers asked for by the 12 Oct deep review that need no GPU.

    python review_tables.py

Reads results/eval and results/confound, writes results/metrics/review_*.csv.
Table VII/VIII additions: B4 floor rows, floor-subtracted r_over, and speech
destroyed above the B4 floor per dB of noise removed. Table IX: LOTO held-out
r_over normalised by the SAME noise type under the full-fold model, and d per SNR.
Oracle-mask rows come from oracle_masks.py.
"""
import glob
import os
import re

import numpy as np
import pandas as pd

EV, OUT = "results/eval", "results/metrics"
EPS = 1e-12


def load(tag, fold, split):
    d = pd.read_csv(f"{EV}/{tag}__{fold}__{split}.csv")
    d["r_over"], d["r_under"] = d.e_over / d.e_clean, d.e_under / d.e_clean
    d["d"] = (d.r_over - d.r_under) / (d.r_over + d.r_under + 1e-8)
    return d


# B4 is fold-independent: its weather/matched rows are the weather test set and its
# weather/unseen rows are the anthro test set. Index both by uid.
b4 = pd.concat([load("b4", "weather", s) for s in ("test_matched", "test_unseen")]).set_index("uid")

rows, per_snr = [], []
for tag in ("b1", "b3"):
    for fold in ("weather", "anthro"):
        for split in ("test_matched", "test_unseen"):
            d = load(tag, fold, split).set_index("uid")
            f = b4.loc[d.index]
            ex_over = d.r_over - f.r_over                         # speech destroyed above the floor
            noise_db = 10 * np.log10((f.r_under + EPS) / (d.r_under + EPS))   # noise removed, dB
            per_db = ex_over / noise_db.where(noise_db > 0.1)     # undefined if mask removed <0.1 dB
            x = pd.DataFrame({"snr": d.snr, "r_over": d.r_over, "r_under": d.r_under, "d": d.d,
                              "b4_r_over": f.r_over, "b4_r_under": f.r_under,
                              "ex_over": ex_over, "noise_db": noise_db, "per_db": per_db})
            r = {"model": tag, "fold": fold, "split": split, "n": len(x),
                 "med_r_over": x.r_over.median(), "med_r_under": x.r_under.median(),
                 "ratio_over_under": x.r_over.median() / x.r_under.median(),
                 "med_d": x.d.median(),
                 "b4_med_r_over": x.b4_r_over.median(), "b4_med_r_under": x.b4_r_under.median(),
                 "r_over_x_floor": x.r_over.median() / x.b4_r_over.median(),
                 "med_ex_over": x.ex_over.median(), "med_noise_removed_db": x.noise_db.median(),
                 "med_speech_per_db": x.per_db.median(), "frac_per_db_defined": x.per_db.notna().mean()}
            rows.append(r)
            g = x.groupby("snr").median()[["r_over", "ex_over", "noise_db", "per_db", "d"]]
            g.insert(0, "split", split); g.insert(0, "fold", fold); g.insert(0, "model", tag)
            per_snr.append(g.reset_index())

b4s = b4.reset_index()
for name, sub in (("weather_test", b4s[b4s.split == "test_matched"]),
                  ("anthro_test", b4s[b4s.split == "test_unseen"])):
    rows.append({"model": "b4", "fold": name, "split": "-", "n": len(sub),
                 "med_r_over": sub.r_over.median(), "med_r_under": sub.r_under.median(),
                 "ratio_over_under": sub.r_over.median() / sub.r_under.median(),
                 "med_d": sub.d.median()})

t7 = pd.DataFrame(rows)
t7.to_csv(f"{OUT}/review_table7_floor.csv", index=False)
pd.concat(per_snr).to_csv(f"{OUT}/review_table7_floor_per_snr.csv", index=False)
print(t7.round(4).to_string(index=False))

# ---------------------------------------------------------------- Table IX
parts = []
for p in glob.glob("results/confound/*__loto-*__test_*.csv"):
    m = re.match(r"(b\d)_loto_([a-z]+)__loto-[a-z]+__(test_matched|test_unseen)\.csv$", os.path.basename(p))
    if m:
        d = pd.read_csv(p)
        d["model"], d["held"], d["split"] = m.groups()
        parts.append(d)
lo = pd.concat(parts)
sc = "snr" if "snr" in lo.columns else "target_snr_db"
lo["r_over"], lo["r_under"] = lo.e_over / lo.e_clean, lo.e_under / lo.e_clean
lo["d"] = (lo.r_over - lo.r_under) / (lo.r_over + lo.r_under + 1e-8)
held = lo[lo.split == "test_unseen"]

t9, d_snr = [], []
for (m, h), g in held.groupby(["model", "held"]):
    full = load(m, "weather", "test_matched")
    full = full[full.noise_type == h].set_index("uid")
    g = g.set_index("uid")
    common = g.index.intersection(full.index)
    gs, fs = g.loc[common], full.loc[common]
    matched_other = lo[(lo.model == m) & (lo.held == h) & (lo.split == "test_matched")]
    snrs = sorted(gs[sc].unique())
    ratio_same = np.mean([gs[gs[sc] == s].r_over.median() / fs[fs.snr == s].r_over.median()
                          for s in snrs if s <= 0])
    ratio_other = np.mean([gs[gs[sc] == s].r_over.median() /
                           matched_other[matched_other[sc] == s].r_over.median()
                           for s in snrs if s <= 0])
    t9.append({"model": m, "held_out": h, "n_paired": len(common),
               "r_over_ratio_vs_same_type_full_model": ratio_same,
               "r_over_ratio_vs_other_two_types (old Table IX)": ratio_other})
    ds = gs.groupby(sc).d.median().rename("held_out_d").to_frame()
    ds["full_model_same_rows_d"] = fs.groupby("snr").d.median()
    ds.insert(0, "held_out", h); ds.insert(0, "model", m)
    d_snr.append(ds.reset_index().rename(columns={sc: "snr"}))

t9 = pd.DataFrame(t9)
t9.to_csv(f"{OUT}/review_table9_same_type.csv", index=False)
d_snr = pd.concat(d_snr)
d_snr.to_csv(f"{OUT}/review_table9_d_per_snr.csv", index=False)
print("\nTable IX, held-out r_over / reference, mean over -15..0 dB")
print(t9.round(3).to_string(index=False))
print("\nmedian d per SNR, LOTO held-out vs full-fold model on the same rows")
print(d_snr.round(3).to_string(index=False))
