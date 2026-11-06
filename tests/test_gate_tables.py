"""B1's guard rails. The table generator reads 31 heterogeneous sources, so the
cheap mistakes are structural: a post-hoc arm drifting into the registered table,
a verdict silently becoming blank when a schema changes, or a provenance hash
going stale because someone pasted it.
"""
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

pytest.importorskip("yaml")
make_gate_tables = pytest.importorskip("make_gate_tables")

POST_HOC_IDS = {"u3_sens_canonical_lgbm", "u3_transfer_sens_feats45",
                "D_diversity_control (level-aligned)"}


@pytest.fixture(scope="module")
def rows():
    return make_gate_tables.rows()


def test_no_post_hoc_arm_reaches_the_registered_table(rows):
    """The work order's hard rule: registered gates and post-hoc arms never share
    a table. Checked both ways, by the flag and by the known arm names."""
    reg = [r for r in rows if not r["post_hoc"]]
    post = [r for r in rows if r["post_hoc"]]
    assert reg and post, "both tables must have rows"

    bare = lambda r: r["gate"].replace("\\_", "_")          # noqa: E731
    leaked = [bare(r) for r in reg if bare(r) in POST_HOC_IDS]
    assert not leaked, f"post-hoc arms in the registered table: {leaked}"

    missing = POST_HOC_IDS - {bare(r) for r in post}
    assert not missing, f"post-hoc arms that vanished from the post-hoc table: {missing}"

    rendered = make_gate_tables.render(reg, "c", "gates")
    for gid in POST_HOC_IDS:
        assert gid.replace("_", "\\_") not in rendered, f"{gid} rendered into tab:gates"


def test_every_verdict_came_from_somewhere(rows):
    """A blank or nan verdict means a source moved and the reader failed quietly."""
    bad = [r["gate"] for r in rows
           if not r["raw_verdict"].strip() or r["raw_verdict"].strip().lower() == "nan"]
    assert not bad, f"empty verdicts: {bad}"


def test_u2_generative_class_is_still_pending(rows):
    """Until the SGMSE+ fine-tune lands, U2's third class must read as pending and
    must not be quietly filled or dropped."""
    u2 = [r for r in rows if r["gate"] == "U2\\_beyond\\_bounded"]
    assert len(u2) == 1
    assert "pending" in u2[0]["numbers"], u2[0]["numbers"]


def test_provenance_hashes_are_computed_not_pasted(rows):
    """Each row's hash must be sha256 of the config as it stands now. If a hash
    were hard-coded, editing a yaml would leave the table claiming old
    provenance."""
    import hashlib
    for r in rows:
        want = hashlib.sha256((REPO / "configs" / r["yaml"]).read_bytes()).hexdigest()[:12]
        assert r["hash"] == want, f"{r['gate']}: stale hash for {r['yaml']}"


def test_no_threshold_is_hard_coded_in_the_criteria(rows):
    """Criteria are read from the yaml, so each one must appear in its own
    config file. Catches a criterion typed into the script."""
    for r in rows:
        nums = re.findall(r"\d+\.\d+", r["criterion"])
        if not nums:
            continue
        text = (REPO / "configs" / r["yaml"]).read_text(encoding="utf-8")
        for n in nums:
            assert n in text, f"{r['gate']}: {n} in the criterion is not in {r['yaml']}"


def test_controls_are_not_rows(rows):
    """confound and segment give a protocol, not a threshold, and write no
    summary verdict. They belong in the caption."""
    bare = {r["gate"].replace("\\_", "_") for r in rows}
    assert "confound" not in bare
    assert "segment" not in bare


def test_both_tables_render_balanced_latex(rows):
    for sub, label in (([r for r in rows if not r["post_hoc"]], "gates"),
                       ([r for r in rows if r["post_hoc"]], "gates_posthoc")):
        tex = make_gate_tables.render(sub, "caption", label)
        assert tex.count("\\begin{tabular}") == tex.count("\\end{tabular}") == 1
        assert tex.count("\\begin{table*}") == tex.count("\\end{table*}") == 1
        assert f"\\label{{tab:{label}}}" in tex
        # one row per gate, each with four ampersands
        body = tex.split("\\midrule")[1].split("\\bottomrule")[0]
        lines = [ln for ln in body.strip().splitlines() if ln.strip()]
        assert len(lines) == len(sub), f"{label}: {len(lines)} lines for {len(sub)} rows"
        for ln in lines:
            assert ln.count("&") == 4, ln
