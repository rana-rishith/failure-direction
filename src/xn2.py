"""Gate XN2 report (configs/gate_overnight2.yaml). numpy/pandas only.

    python -m src.xn2            # writes results/xcorpus/report2/report.md + CSVs
"""
import re

import numpy as np
import pandas as pd

import config as C
from src.xcorpus import HEARD_P, OUT, PAIRED, UNSEEN_P, _derive

REP = OUT / "report2"
ARCHS = ("b1", "b3", "cm")
SFX = ("", "_s2", "_s3")
HP = ["sisdr_lc_in", "sisdr_lc_out", "sisdr_hp100_in", "sisdr_hp100_out"]


def load_eval():
    ev = pd.concat([pd.read_csv(f) for f in sorted((OUT / "eval").glob("*.csv"))], ignore_index=True)
    for c in HP:
        if c not in ev.columns:
            ev[c] = np.nan
    hd = OUT / "eval_hp"
    if hd.exists():
        h = pd.concat([pd.read_csv(f).assign(cond=f.stem) for f in sorted(hd.glob("*.csv"))], ignore_index=True)
        h = h.drop_duplicates(["tag", "cond", "uid"], keep="last").set_index(["tag", "cond", "uid"])
        key = pd.MultiIndex.from_frame(ev[["tag", "cond", "uid"]])
        for c in HP:
            fill = h[c].reindex(key).to_numpy()
            ev[c] = np.where(ev[c].isna(), fill, ev[c])
    d = _derive(ev)
    d["gain_hp100"] = d.sisdr_hp100_out - d.sisdr_hp100_in
    d["gain_lc"] = d.sisdr_lc_out - d.sisdr_lc_in
    return d


def dclass(d, nr):
    if np.isnan(d) or np.isnan(nr):
        return "no_data"
    if d > 0 and nr >= 0.5:
        return "diversity_explains"
    if d < 0 and nr < 0.3:
        return "architecture_explains"
    return "partial"


def shared(classes):
    c = pd.Series([x for x in classes if x not in ("no_data",)]).value_counts()
    return c.index[0] if len(c) and c.iloc[0] >= 2 else "mixed"


def main():
    REP.mkdir(parents=True, exist_ok=True)
    d = load_eval()
    lines = ["# Gate XN2 report", ""]
    low = d[(d.cond == "marven") & (d.snr <= 0)]
    med = low.groupby("tag")[["d_g", "nr_g", "d", "nr", "sisdr_gain", "gain_hp100"]].median()

    # D_fsd and H_D2
    rows = []
    for fam in ("fsd", "demand"):
        for a in ARCHS:
            for s in SFX:
                t = f"{a}_{fam}{s}"
                if t in med.index:
                    rows.append(dict(family=fam, arch=a, tag=t, d_g=med.loc[t, "d_g"], nr_g=med.loc[t, "nr_g"],
                                     d_plain=med.loc[t, "d"], nr_plain=med.loc[t, "nr"],
                                     cls=dclass(med.loc[t, "d_g"], med.loc[t, "nr_g"])))
    per = pd.DataFrame(rows)
    per.to_csv(REP / "D_per_seed.csv", index=False)
    if len(per):
        lines += ["## Per-seed gate-D statistics (MarVEN, SNR <= 0, level-aligned)", "", per.round(3).to_string(index=False), ""]
    fs = per[per.family == "fsd"] if len(per) else per
    if len(fs):
        agg = fs.groupby("arch")[["d_g", "nr_g"]].median()
        agg["n_seeds"] = fs.groupby("arch").size()
        agg["class"] = [dclass(r.d_g, r.nr_g) for r in agg.itertuples()]
        agg.to_csv(REP / "D_fsd.csv")
        lines += [f"## D_fsd: {shared(agg['class'])}", "", agg.round(3).to_string(), ""]
    dm = per[per.family == "demand"] if len(per) else per
    if len(dm):
        h = dm.groupby("arch").agg(classes=("cls", lambda c: ",".join(c)), n=("cls", "size"))
        h["verdict"] = [("stable" if len(set(c.split(","))) == 1 else "seed_sensitive") if n > 1 else "one_seed"
                        for c, n in zip(h.classes, h.n)]
        h.to_csv(REP / "H_D2.csv")
        lines += ["## H_D2 demand seeds", "", h.to_string(), ""]
    if len(fs) and len(dm):
        w = []
        for a in ARCHS:
            f_, m_ = fs[fs.arch == a].nr_g.mean(), dm[dm.arch == a].nr_g.mean()
            delta = f_ - m_
            w.append(dict(arch=a, nr_g_fsd=f_, nr_g_demand=m_, delta=delta,
                          cls="no_data" if np.isnan(delta) else "widens" if delta >= 0.10 else
                          "narrows" if delta <= -0.10 else "no_change"))
        w = pd.DataFrame(w)
        w.to_csv(REP / "H_FD.csv", index=False)
        lines += [f"## H_FD_widening: {shared(w.cls)}", "", w.round(3).to_string(index=False), ""]

    # H_F family on fresh FSD50K weather
    cm_ = d.groupby(["tag", "cond"]).nr_g.median()
    hf = []
    for a in ARCHS:
        for s in SFX:
            we, an = f"{a}_weather{s}", f"{a}_anthro{s}"
            try:
                b_w = cm_[(we, "fsd_weather")] - cm_[(an, "fsd_weather")]
                b_e = cm_[(we, "fsd_eval")] - cm_[(an, "fsd_eval")]
            except KeyError:
                continue
            boat = (cm_.get((an, "fsd_boat"), np.nan) - cm_.get((we, "fsd_boat"), np.nan)) - (-b_e)
            hf.append(dict(arch=a, seed=s or "_s1234", bonus_weather=b_w, bonus_eval=b_e, E=b_w - b_e, E_boat=boat))
    if hf:
        hf = pd.DataFrame(hf)
        n = len(hf)
        k = int((hf.E >= 0.10).sum())
        v = ("family_specific" if k >= 7 else "not_family_specific" if n - k >= 7 else "mixed") if n == 9 else f"incomplete ({n} pairs)"
        hf.to_csv(REP / "H_F.csv", index=False)
        lines += [f"## H_F_family_fresh: {v} (E >= 0.10 in {k} of {n})", "", hf.round(3).to_string(index=False), ""]

    # C1_lowcut
    mv = d[d.cond == "marven"]
    c1 = []
    for a in ARCHS:
        for fam, heard in (("anthro", C.ANTHRO), ("weather", C.WEATHER)):
            t = f"{a}_{fam}"
            x = mv[mv.tag == t]
            if x.empty or x.gain_hp100.isna().all():
                continue
            h, u = x[x.noise_type.isin(heard)], x[~x.noise_type.isin(heard)]
            gf = h.sisdr_gain.median() - u.sisdr_gain.median()
            gh = h.gain_hp100.median() - u.gain_hp100.median()
            gl = h.gain_lc.median() - u.gain_lc.median()
            c1.append(dict(tag=t, gap_full=gf, gap_lc=gl, gap_hp100=gh, ratio=gh / gf, ok=gh >= 0.75 * gf))
    if c1:
        c1 = pd.DataFrame(c1)
        k = int(c1.ok.sum())
        v = ("robust" if k == 6 else "partly" if k >= 4 else "sub100_dependent") if len(c1) == 6 else f"incomplete ({len(c1)} cells)"
        c1.to_csv(REP / "C1_lowcut.csv", index=False)
        lines += [f"## C1_lowcut: {v}", "", c1.round(3).to_string(index=False), ""]

    # H_P final (pretrained ladder)
    for model in ("dfn3", "sgmse"):
        p = OUT / f"ext_{model}.csv"
        if not p.exists():
            continue
        e = _derive(pd.read_csv(p))
        if "sisdr_hp100_out" in e.columns:
            e["gain_hp100"] = e.sisdr_hp100_out - e.sisdr_hp100_in
        pb = e[e.cond.isin(PAIRED)]
        full = pb.groupby("base_uid").cond.nunique()
        keep = full[full == len(PAIRED)].index
        pb = pb[pb.base_uid.isin(keep)]
        row = dict(model=model, paired_base_rows=len(keep))
        for met, key in (("d_g", "H_P1"), ("nr_g", "H_P2"), ("gain_hp100", "hp100_gain_desc"), ("sisdr_gain", "gain_desc")):
            if met not in pb.columns:
                continue
            delta = pb[pb.cond.isin(UNSEEN_P)][met].median() - pb[pb.cond.isin(HEARD_P)][met].median()
            row[f"{key}_delta"] = delta
            if key.startswith("H_P"):
                row[key] = ("underpowered" if model == "sgmse" and len(keep) < 40 else
                            "shifts_with_novelty" if abs(delta) >= 0.20 else
                            "model_trait" if abs(delta) < 0.10 else "inconclusive")
        cols = [c for c in ["nr_g", "d_g", "g", "sisdr_gain", "gain_hp100"] if c in e.columns]
        e.groupby("cond")[cols].median().round(4).to_csv(REP / f"{model}_by_cond.csv")
        pd.DataFrame([row]).to_csv(REP / f"H_P_{model}.csv", index=False)
        lines += [f"## H_P_final: {model}", "", pd.DataFrame([row]).round(3).to_string(index=False), "",
                  e.groupby("cond")[cols].median().round(3).to_string(), ""]

    # descriptive matrix (seed-mean of per-tag medians)
    d["group"] = d.tag.str.replace(r"_s\d$", "", regex=True)
    fam = d.group.str.extract(r"_(anthro|weather)$")[0]
    heard = np.where(fam == "anthro", d.noise_type.isin(C.ANTHRO), d.noise_type.isin(C.WEATHER))
    d["cond"] = np.where((d.cond == "marven") & fam.notna(), np.where(heard, "marven_heard", "marven_unseen"), d.cond)
    tm = d.groupby(["group", "tag", "cond"])[["nr_g", "d_g", "sisdr_gain", "gain_hp100"]].median()
    gm = tm.groupby(["group", "cond"]).mean()
    for met in ("nr_g", "d_g", "sisdr_gain", "gain_hp100"):
        t = gm[met].unstack("cond").round(3)
        t.to_csv(REP / f"matrix_{met}.csv")
        lines += [f"## Matrix (seed mean): {met}", "", t.to_string(), ""]
    pt = d[(d.cond == "marven") & d.group.str.contains("demand|fsd")].groupby(["tag", "noise_type"]).nr_g.median().unstack().round(3)
    if len(pt):
        pt.to_csv(REP / "marven_by_type_demand_fsd.csv")
        lines += ["## MarVEN per type, nr_g (demand and fsd models)", "", pt.to_string(), ""]
    (REP / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
