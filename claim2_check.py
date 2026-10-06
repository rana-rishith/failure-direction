import pandas as pd
d = pd.read_csv("results/metrics/eval_matrix.csv")
d = d[d.tag != "b4"].copy()
sc = "snr" if "snr" in d.columns else "target_snr_db"
d["r_over"] = d.e_over / d.e_clean
d["r_under"] = d.e_under / d.e_clean
g = d.groupby(["tag", "split"])[["r_over", "r_under"]].median()
g["over_to_under"] = g.r_over / g.r_under
print(g.round(4))
p = d.pivot_table(index=sc, columns="split", values=["r_over", "r_under"], aggfunc="median")
p["flip_holds"] = (p[("r_over","test_matched")] > p[("r_over","test_unseen")]) & (p[("r_under","test_unseen")] > p[("r_under","test_matched")])
print(p.round(4))
