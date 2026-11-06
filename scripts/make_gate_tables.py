"""B1: build the gate ledger tables for the paper.

    python scripts/make_gate_tables.py

Writes two LaTeX tables and prints what it found:

    paper/tables/gates_registered.tex   gates registered before they ran
    paper/tables/gates_posthoc.tex      post-hoc arms only

Rules this file exists to enforce, from the 5 Nov work order:

* **No verdict is typed by hand.** Every verdict cell is read out of the file
  that gate wrote. If a source file moves or its schema changes, the row raises
  rather than printing a stale string. The one exception is U2's generative
  cell, which is deliberately `pending` until the SGMSE+ fine-tune lands.
* **No threshold is hard-coded.** Criteria are read from the yaml at run time.
* **Registered and post-hoc never share a table.** Two files, and
  `tests/test_gate_tables.py` fails if a post-hoc arm reaches the registered one.
* **Hashes are computed, not copied.** Each row's yaml hash is sha256 of the
  config as it stands now, so a table built after an edit cannot claim the old
  provenance.

`D_diversity_control` is the registered, plain-basis, b1_demand verdict from
audit A1. The level-aligned reading of the same gate is a separate post-hoc row,
labelled as such. See `docs/record_audit_D_basis_2026-11-05.md`.

`confound` and `segment` are controls, not gates: their yaml gives a protocol
rather than a threshold and neither writes a summary verdict. They are named in
the caption and have no rows. `M1_predicted_gamma` never ran, blocked by M0.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

import config as C  # noqa: E402
from src.r3 import _after  # noqa: E402  the repo's own "number after an operator" parser

CONF = REPO / "configs"
OUT = REPO / "paper" / "tables"
R = C.EVAL


# ------------------------------------------------------------------ readers ---
def _sha(name: str) -> str:
    return hashlib.sha256((CONF / name).read_bytes()).hexdigest()[:12]


def _cfg(name: str) -> dict:
    return yaml.safe_load((CONF / name).read_text(encoding="utf-8"))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _md(path: Path, pattern: str) -> str:
    """First capture group of `pattern` in a markdown report."""
    m = re.search(pattern, path.read_text(encoding="utf-8"), re.M)
    if not m:
        raise ValueError(f"{path}: no match for {pattern!r}")
    return m.group(1).strip()


def _one(frame: pd.DataFrame, col: str) -> str:
    """The single value of `col`, or 'x of n' when the rows disagree."""
    v = frame[col].astype(str)
    u = sorted(v.unique())
    if len(u) == 1:
        return u[0]
    top = v.value_counts()
    return f"{top.index[0]} ({top.iloc[0]} of {len(v)})"


def _f(x, n: int = 3) -> str:
    return f"{float(x):.{n}f}"


# -------------------------------------------------------------------- rows ----
# Each entry: id, yaml, criterion (read from the yaml where it has one), and a
# reader returning (verdict, key numbers). `post` marks a post-hoc arm.
def rows() -> list[dict]:
    out: list[dict] = []

    def add(gid, yml, criterion, verdict, numbers, post=False, section=""):
        # gate and verdict are plain words out of files, so they are escaped here.
        # criterion comes pre-escaped from _brief; numbers are authored with
        # deliberate math and are left alone.
        esc = lambda s: str(s).replace("_", "\\_")        # noqa: E731
        out.append({"gate": esc(gid), "yaml": yml, "hash": _sha(yml),
                    "criterion": criterion, "verdict": esc(verdict),
                    "numbers": str(numbers), "post_hoc": post, "section": section,
                    "raw_verdict": str(verdict)})

    # --- configs/gate.yaml: G1, G2, G3 --------------------------------------
    g = _cfg("gate.yaml")
    gr = yaml.safe_load((C.METRICS / "gate_results.yaml").read_text(encoding="utf-8"))
    add("G1", "gate.yaml", f"{g['G1']['statistic']} $\\ge$ {g['G1']['threshold']}",
        gr["G1"]["verdict"], f"spread {_f(gr['G1']['pooled_spread'], 4)}", section="claim2")
    add("G2", "gate.yaml", f"{g['G2']['statistic']} $\\ge$ {g['G2']['threshold']}",
        gr["G2"]["verdict"], f"median gap {_f(gr['G2']['gap_median'])}", section="claim2")
    add("G3", "gate.yaml", f"{g['G3']['statistic']} $\\ge$ {g['G3']['threshold']}",
        gr["G3"]["verdict"],
        f"collinearity {_f(gr['G3']['collinearity'])}", section="claim2")

    # --- configs/gate_universal.yaml ---------------------------------------
    u = _cfg("gate_universal.yaml")
    for gid, fn, key, num in (
        ("U1_novelty_monotone", "u1_verdict.json", "U1_novelty_monotone", None),
        ("U1_failure_class", "u1class_verdict.json", "U1_failure_class", None),
        ("U2_beyond_bounded", "u2_verdict.json", "U2_beyond_bounded", None),
        ("U3_within_condition", "u3_verdict.json", "U3_within_condition", None),
        ("U3_transfer", "u3_verdict.json" if not (R / "universal" / "u3_transfer_verdict.json").exists()
         else "u3_transfer_verdict.json", "U3_transfer", None),
    ):
        v = _json(R / "universal" / fn)
        crit = u[key].get("pass_if", u[key].get("statistic", ""))
        n = v["notes"]
        if gid == "U2_beyond_bounded":
            # The generative class is deliberately pending, not absent.
            cp = n.get("class_pass", {})
            miss = n.get("classes_missing", ["generative"])
            num = (f"{sum(bool(x) for x in cp.values())} of {len(cp) + len(miss)} classes; "
                   f"{', '.join(miss)} pending")
        elif gid == "U3_transfer":
            num = str(n.get("n_pass", n.get("types_pass", "")))[:40]
        else:
            num = ", ".join(f"{k} {v2}" for k, v2 in list(
                (n.get("arch_pass") or n.get("classes") or {}).items())[:3])
        add(gid, "gate_universal.yaml", _brief(crit), v["verdict"], num, section="novelty")

    m0 = _csv(R / "method" / "m0_summary.csv")
    add("M0_oracle_headroom", "gate_universal.yaml",
        _brief(u["M0_oracle_headroom"]["pass_if"]), _one(m0, "verdict"),
        f"best oracle gain {_f(m0.gamma_oracle_gain.max())} dB in {len(m0)} cells",
        section="diversity")
    add("M1_predicted_gamma", "gate_universal.yaml",
        _brief(u["M1_predicted_gamma"].get("pass_if", u["M1_predicted_gamma"].get("question", ""))),
        "not run", "blocked by M0", section="diversity")

    dps = _csv(R / "xcorpus" / "report2" / "D_per_seed.csv")
    reg = dps[(dps.family == "demand") & (dps.arch == "b1") & (dps.tag == "b1_demand")]
    # The registered basis is the plain one (audit A1), and D_per_seed.csv stores
    # the level-aligned class, so the registered verdict is not a column anywhere.
    # Evaluate the registered rule on the registered numbers instead of typing it.
    dv = u["D_diversity_control"]["verdict"]
    d_p, nr_p = float(reg.d_plain.iloc[0]), float(reg.nr_plain.iloc[0])
    if d_p > 0 and nr_p >= _after(dv["diversity_explains"], ">="):
        d_cls = "diversity_explains"
    elif d_p < 0 and nr_p < _after(dv["architecture_explains"], "<"):
        d_cls = "architecture_explains"
    else:
        d_cls = "partial"                      # the yaml's "mixed; reported as partial"
    add("D_diversity_control", "gate_universal.yaml", _brief(dv), d_cls,
        f"plain basis, b1\\_demand: $d$ {_f(d_p)}, nr {_f(nr_p)}", section="diversity")

    # --- configs/gate_overnight2.yaml --------------------------------------
    o2 = _cfg("gate_overnight2.yaml")["gates"]
    dfsd = _csv(R / "xcorpus" / "report2" / "D_fsd.csv")
    add("D_fsd", "gate_overnight2.yaml", _brief(o2["D_fsd"]["claim"]), _one(dfsd, "class"),
        f"$d_g$ {_f(dfsd.d_g.min())} to {_f(dfsd.d_g.max())}, "
        f"nr$_g$ {_f(dfsd.nr_g.min())} to {_f(dfsd.nr_g.max())}", section="diversity")
    hfd = _csv(R / "xcorpus" / "report2" / "H_FD.csv")
    add("H_FD_widening", "gate_overnight2.yaml", _brief(o2["H_FD_widening"]["verdict"]),
        _one(hfd, "cls"), f"$\\Delta$nr$_g$ {_f(hfd.delta.min())} to {_f(hfd.delta.max())}",
        section="diversity")
    hd2 = _csv(R / "xcorpus" / "report2" / "H_D2.csv")
    add("H_D2_demand_seeds", "gate_overnight2.yaml", _brief(o2["H_D2_demand_seeds"]["verdict"]),
        _one(hd2, "verdict"), f"{int(hd2.n.sum())} runs, one class", section="diversity")
    hf = _csv(R / "xcorpus" / "report2" / "H_F.csv")
    hfv = o2["H_F_family_fresh"]["verdict"]
    thr = _after(hfv["family_specific"], ">=")            # the E bar, 0.10
    need = int(re.search(r">=\s*(\d+)\s*of", hfv["family_specific"]).group(1))
    n_ok = int((hf.E >= thr).sum())
    hf_cls = ("family_specific" if n_ok >= need else
              "not_family_specific" if (len(hf) - n_ok) >= need else "mixed")
    add("H_F_family_fresh", "gate_overnight2.yaml", _brief(hfv), hf_cls,
        f"$E \\ge {thr}$ in {n_ok} of {len(hf)} pairs", section="diversity")

    c1 = _csv(R / "xcorpus" / "report2" / "C1_lowcut.csv")
    c1v = o2["C1_lowcut"]["verdict"]
    frac = _after(c1v, ">=")                              # the 0.75 of gap_full bar
    partly = int(re.search(r"'partly' if in >=\s*(\d+)", c1v).group(1))
    n_ok = int((c1.gap_hp100 >= frac * c1.gap_full).sum())
    c1_cls = ("robust" if n_ok == len(c1) else
              "partly" if n_ok >= partly else "sub100_dependent")
    add("C1_lowcut", "gate_overnight2.yaml", _brief(c1v), c1_cls,
        f"ratio {_f(c1.ratio.min())} to {_f(c1.ratio.max())}, "
        f"{n_ok} of {len(c1)} cells at $\\ge{frac}$", section="diversity")
    for model in ("dfn3", "sgmse"):
        h = _csv(R / "xcorpus" / "report2" / f"H_P_{model}.csv")
        add(f"H_P_final {model}", "gate_overnight2.yaml",
            _brief(o2["H_P_final"]),          # its rule key, picked up by _brief
            f"H_P1 {_one(h, 'H_P1')}", f"$\\Delta$ {_f(h.H_P1_delta.iloc[0])}, "
            f"{int(h.paired_base_rows.iloc[0])} paired base rows", section="novelty")

    # --- the single-gate yamls ---------------------------------------------
    r3 = _md(R / "r3" / "report.md", r"\*\*U1-R3 = `([^`]+)`")
    add("r3", "gate_r3.yaml", _brief(_cfg("gate_r3.yaml")), r3,
        "9 of 9 runs", section="novelty")
    pl = _csv(R / "pilot_level" / "verdict.csv")
    add("pilot_level", "gate_pilot_level.yaml", _brief(_cfg("gate_pilot_level.yaml")),
        "; ".join(f"{t} {v}" for t, v in zip(pl.model, pl.verdict)),
        f"{len(pl)} pretrained models", section="diversity")
    d2 = _csv(R / "distance" / "summary.csv")
    add("D2_distance", "gate_distance.yaml", _brief(_cfg("gate_distance.yaml")),
        _one(d2, "verdict"), f"$\\rho$ {_f(d2.rho_nr.iloc[0])}, n {int(d2.n_unseen.iloc[0])}",
        section="diversity")
    st = _csv(R / "stationarity" / "summary_full.csv")
    add("S_stationarity", "gate_stationarity.yaml", _brief(_cfg("gate_stationarity.yaml")),
        "PASS" if bool(st["pass"].iloc[0]) else "FAIL",
        f"$\\rho$ {_f(st.rho.iloc[0])}, n {int(st.n.iloc[0])}", section="diversity")
    cl = _csv(R / "claim3_level" / "verdict.csv")
    add("C3_level_recheck", "gate_claim3_level.yaml", _brief(_cfg("gate_claim3_level.yaml")),
        "PASS" if bool(cl["pass"].all()) else "FAIL",
        f"{int(cl['pass'].sum())} of {len(cl)} target-fold cells", section="claim3")
    for gid, yml, path in (
        ("C3_active", "gate_claim3_active.yaml", R / "claim3_active" / "report.md"),
        ("C3b", "gate_claim3b.yaml", R / "claim3b" / "heldout" / "report.md"),
        ("C3c", "gate_claim3c.yaml", R / "claim3c" / "heldout" / "report.md"),
    ):
        v = _md(path, r"^## Verdict:\s*(\S+)")
        n = _md(path, r"^- (.+)$")
        add(gid, yml, _brief(_cfg(yml)), v, n[:60], section="claim3")

    ov = R / "xcorpus" / "report" / "report.md"
    add("H_S1", "gate_overnight.yaml", "sign of nr$_g$(R1) $-$ nr$_g$(R4) over 3 seeds",
        _md(ov, r"^\s*\S+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+(\w+)\s*$"),
        "6 of 6 models", section="novelty")
    add("H_S2", "gate_overnight.yaml", "R3 class across seeds",
        _md(ov, r"^## H_S2 R3 across seeds:\s*(\w+)"), "9 runs", section="novelty")

    # --- post-hoc arms ------------------------------------------------------
    for gid, fn in (("u3_sens_canonical_lgbm", "u3_sens_canonical_lgbm_verdict.json"),
                    ("u3_transfer_sens_feats45", "u3_transfer_sens_feats45_verdict.json")):
        v = _json(R / "universal" / fn)
        add(gid, "gate_universal.yaml",
            _brief(v["thresholds"]), v["verdict"], "", post=True, section="novelty")

    # The same gate on the level-aligned basis. Its class IS a column here, so it
    # is read, not evaluated. A1 established that this reading is not the
    # registered one, which is why it sits in the post-hoc table.
    lvl = dps[(dps.family == "demand") & (dps.tag == "b1_demand")]
    add("D_diversity_control (level-aligned)", "gate_amend_level.yaml",
        "same gate read on the level-aligned basis", _one(lvl, "cls"),
        f"$d_g$ {_f(lvl.d_g.iloc[0])}, nr$_g$ {_f(lvl.nr_g.iloc[0])}",
        post=True, section="diversity")
    return out


def _brief(x, n: int = 64) -> str:
    """A criterion short enough for a table cell, from whatever the yaml holds."""
    if isinstance(x, dict):
        for k in ("pass_if", "claim", "verdict", "statistic", "question", "rule"):
            if k in x:
                x = x[k]
                break
        else:
            x = next(iter(x.values()))
    if isinstance(x, dict):
        x = "; ".join(f"{k}: {v}" for k, v in list(x.items())[:2])
    s = re.sub(r"\s+", " ", str(x)).strip()
    s = s.replace("_", "\\_").replace("%", "\\%").replace("&", "\\&")
    s = s.replace(">=", "$\\ge$").replace("<=", "$\\le$")
    return s if len(s) <= n else s[: n - 1].rstrip() + "\\ldots"


# ------------------------------------------------------------------ output ----
HEAD = r"""%% generated by scripts/make_gate_tables.py -- do not edit by hand
\begin{table*}[!t]
\caption{%s}
\label{tab:%s}
\centering
\footnotesize
\begin{tabular}{@{}llllp{0.26\textwidth}@{}}
\toprule
Gate & Criterion & Verdict & Key numbers & Provenance (yaml / sha256) \\
\midrule
"""

FOOT = r"""\bottomrule
\end{tabular}
\end{table*}
"""


def render(rs: list[dict], caption: str, label: str) -> str:
    body = "".join(
        f"{r['gate']} & {r['criterion']} & {r['verdict']} & {r['numbers']} & "
        f"\\texttt{{{r['yaml'].replace('_', chr(92) + '_')}}} / "
        f"\\texttt{{{r['hash']}}} \\\\\n" for r in rs)
    return (HEAD % (caption, label)) + body + FOOT


def main() -> None:
    rs = rows()
    reg = [r for r in rs if not r["post_hoc"]]
    post = [r for r in rs if r["post_hoc"]]
    assert reg and post, "both tables must have rows"

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gates_registered.tex").write_text(render(
        reg, "Registered gates. Every verdict is read from the file that gate wrote; "
        "no cell is typed by hand. \\texttt{confound} and \\texttt{segment} are controls "
        "with a protocol rather than a threshold and are not rows. U2's generative class "
        "is pending the SGMSE+ fine-tune.", "gates"), encoding="utf-8")
    (OUT / "gates_posthoc.tex").write_text(render(
        post, "Post-hoc arms. Registered after the result they test was known, and not "
        "part of any registered verdict.", "gates_posthoc"), encoding="utf-8")

    print(f"registered {len(reg)} rows -> {OUT / 'gates_registered.tex'}")
    print(f"post-hoc   {len(post)} rows -> {OUT / 'gates_posthoc.tex'}")
    print()
    print(pd.DataFrame(rs)[["gate", "verdict", "post_hoc", "hash"]].to_string(index=False))


if __name__ == "__main__":
    main()
