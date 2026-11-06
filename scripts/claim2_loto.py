import pandas as pd, glob, os, re
parts = []
for f in glob.glob("results/confound/*__loto-*__test_*.csv"):
    m = re.match(r"(b\d)_loto_([a-z]+)__loto-[a-z]+__(test_matched|test_unseen)\.csv$", os.path.basename(f))
    if not m: continue
    d = pd.read_csv(f); d["model"], d["held"], d["split"] = m.groups()
    parts.append(d)
d = pd.concat(parts)
cands = [c for c in ["target_snr_db", "snr", "snr_db"] if c in d.columns]
if not cands:
    raise SystemExit(f"no SNR column; columns are: {list(d.columns)}")
sc = cands[0]
d = d[d[sc] <= 0].copy()
d["dc_fixed"] = d.e_over / d.e_clean
d["pre_dc"] = d.e_over_full / d.e_clean_full
g = d.groupby(["model", "held", "split", sc])[["dc_fixed", "pre_dc"]].median().unstack("split")
r = pd.DataFrame({k: g[(k, "test_unseen")] / g[(k, "test_matched")] for k in ["dc_fixed", "pre_dc"]})
print("held-out / matched r_over, mean over -15..0 dB")
print(r.groupby(["model", "held"]).mean().round(2))
print("\nper SNR")
print(r.round(2))
