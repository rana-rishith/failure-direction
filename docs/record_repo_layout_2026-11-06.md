# Record: repository layout, and the stale paths it leaves behind

2026-11-06. No gate verdict is changed by anything here. This records one
deliberate cost of the layout change so a future reader does not treat it as a
mistake.

## The layout

Every runnable entry point now lives in `scripts/`. Every importable module
lives in `src/`. The repository root holds only project metadata and
`config.py`.

| Path | Rule |
| --- | --- |
| `src/` | imported, never run directly |
| `scripts/` | run directly, never imported |
| `configs/` | pre-registered gate files, read at run time |
| `results/` | evidence, written by runs, read by figures and tables |
| `docs/` | usage, detailed results, and one record per analysis |
| `tests/` | `python -m pytest` |
| `paper/figs/` | the 13 figures |
| root | `README.md`, `LICENSE`, `CITATION.cff`, `environment.yml`, `requirements.txt`, `config.py`, `conftest.py` |

`config.py` and `conftest.py` are the two exceptions to the rule. `conftest.py`
was added later the same day: pytest only reads the rootdir copy, and it must set
`MKL_THREADING_LAYER` before any test module imports numpy. It holds no test code.

`config.py` is the other exception. Roughly forty modules reach it as
`import config as C`, which resolves against the repository root. Moving it
would mean editing every one of those imports for no gain, so it stays.

## What moved

Into `scripts/`: `make_figs.ps1`, `label_stability.py`, and the seven
`run_*.ps1` job drivers. Earlier the same day, nine helper scripts
(`claim2_by_type`, `claim2_check`, `claim2_loto`, `fig_appendix`,
`fig_direction`, `fig_spectrograms`, `oracle_masks`, `review_h3`,
`review_tables`) moved there too, and a byte-identical duplicate
`plot_claim1_snr.py` was deleted from the root.

Into `src/`: `wada_snr.py`, which is a feature extractor, not a script.

## Two things the move broke, and the fixes

**The PowerShell scripts derived the repository root from their own location.**
Each held

```powershell
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
```

which inside `scripts/` points at `scripts/`, one level too deep. `$R`, the
parent of the repository where the datasets sit, was wrong by the same amount.
Eight scripts now take the parent twice. Verified by computing the expression
for all eleven `.ps1` in `scripts/`: eleven correct, zero wrong, and `$R`
resolving to `MAIN-failure-direction(ALL)`.

`run_sgmse_full.ps1` needed no fix, because it hard-codes an absolute path.

**`scripts/run_universal.py` imported `wada_snr` from the repository root**,
which it puts on `sys.path`. It now reads `from src.wada_snr import wada`.
Verified directly, because this is the script that scores the pending U2
verdict.

## The cost: six pre-registered yaml files now name a stale path

Six gate files record the producing code in a comment, naming the scripts
where they used to live:

| Gate file | The line |
| --- | --- |
| `gate_claim3_active.yaml:2` | `# Code: ..., run_claim3_active.ps1.` |
| `gate_claim3b.yaml:2` | `# Code: ..., run_claim3b.ps1.` |
| `gate_claim3b.yaml:9` | `... and label_stability.py ...` |
| `gate_claim3c.yaml:2` | `# Code: ..., run_claim3c.ps1 ...` |
| `gate_overnight.yaml:2` | `... of run_overnight.ps1 runs ...` |
| `gate_overnight2.yaml:1` | `# Gate XN2: second long run (run_overnight2.ps1).` |
| `gate_xn2_sgmse_ext.yaml:17` | `code: "..., run_finish.ps1"` |

**These files were not edited and must not be.** Each carries a SHA-256 digest
recorded inside every verdict JSON it produced, and the hash is recomputed from
the file at table-build time. Editing one to follow a moved script would break
the match between a verdict and the configuration that decided it, which is the
one guarantee the ledger offers.

So the comments stay as written. The file names in them are unchanged and still
unique in the repository, so the code they name is one search away. Only the
implied directory is stale. Nothing executable reads these strings: they are
provenance prose, not paths the runner resolves.

`gate_universal.yaml` also contains `wada_snr`, at line 83. That one is **not**
stale. It is an arm name in the registered `arms:` list, not a file path, and
the arm is still called `wada_snr`.

## Verification

- `python -m pytest`: 78 passed.
- `from src.wada_snr import wada`: resolves.
- Repository-root derivation: correct for all 11 scripts in `scripts/`.
- Every script path `scripts/make_figs.ps1` invokes: all 7 exist.
