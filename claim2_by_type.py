import pandas as pd
d = pd.read_csv("results/metrics/eval_matrix.csv")
d = d[d.tag != "b4"].copy()
d["r_over"] = d.e_over / d.e_clean
m = d.groupby(["tag", "noise_type", "split"]).r_over.median().unstack("split")
m["unseen_over_matched"] = m.test_unseen / m.test_matched
print(m.round(4))
