# Working in this repo

Solo project, but the rules exist so results stay defensible.

- **Commit**: configs, `requirements.lock.txt`, every results CSV, every gate decision.
- **Never commit**: audio, checkpoints, anything in `runs/` or `data/raw/`.
- **Means are taken in one place** — `scripts/15_aggregate.py`. Nowhere else.
- **`configs/gate.yaml` is frozen** once Stage 1 starts. Changing it after seeing
  results means the gate proved nothing; the git history will show it.
- **New metric or model** → add a test that pins its behaviour on a synthetic
  signal with a known answer, the way `tests/test_direction_index.py` does.
- Run `ruff check . && pytest` before pushing.
