# Putting this repo on GitHub

Windows / PowerShell. Assumes the folder lives at `D:\Rana Rishith\failure-direction`.

Everything here is one-time setup except step 8, which you repeat forever.

---

## 1. Install the tools

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Close and reopen PowerShell so `git` and `gh` land on your PATH.

```powershell
git --version
gh --version
```

## 2. Identify yourself

The name and email are baked into every commit and are public. Use the same email
as your GitHub account, or GitHub's no-reply address if you'd rather not publish it
(Settings → Emails → *Keep my email addresses private* gives you the address).

```powershell
git config --global user.name "Rana Rishith"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.autocrlf true      # Windows line endings, LF in the repo
```

## 3. Authenticate

```powershell
gh auth login
```

Choose: **GitHub.com** → **HTTPS** → **Login with a web browser**. Paste the code it
shows you. This stores a credential so you never type a password into a git prompt.

Do not create a personal access token and paste it into a script. `gh auth login`
handles it.

## 4. Create the repository

From inside the project folder:

```powershell
cd "D:\Rana Rishith\failure-direction"

gh repo create failure-direction `
  --public `
  --source . `
  --remote origin `
  --description "Pre-hoc, reference-free prediction of speech-enhancement failure direction and magnitude under unseen noise."
```

`--source .` links the existing local repo instead of making an empty one you then
have to reconcile. If the folder is not yet a git repo:

```powershell
git init -b main
git add -A
git commit -m "Initial commit"
```

**Public or private?** Public from day one is the better call here. The repo is
evidence for the MS application, the commit history is what proves the go/no-go gate
was pre-committed rather than tuned, and none of the code is secret. Nothing in
`.gitignore` (audio, checkpoints) ever leaves your machine either way.

## 5. First push

```powershell
git push -u origin main
gh repo view --web
```

## 6. Verify nothing large or private slipped in

```powershell
git ls-files | Measure-Object          # file count — should be ~40, not thousands
git count-objects -vH                  # size-pack should be well under 10 MB
git ls-files | Select-String "\.wav$|\.pt$|\.ckpt$"   # must return nothing
```

If a large file did get committed, do not just delete it — it stays in history and
counts against the 100 MB hard limit. Remove it properly:

```powershell
pip install git-filter-repo
git filter-repo --path path/to/big.wav --invert-paths
git push --force origin main
```

Do that before anyone clones it, and only before.

## 7. Repository settings that actually matter

### Topics and description

```powershell
gh repo edit --add-topic speech-enhancement,failure-prediction,distribution-shift,marine-acoustics,pytorch
```

### Protect main

```powershell
gh api -X PUT repos/:owner/failure-direction/branches/main/protection `
  -F required_status_checks[strict]=true `
  -F "required_status_checks[contexts][]=test" `
  -F enforce_admins=true `
  -F required_pull_request_reviews=null `
  -F restrictions=null
```

Solo project, so no review requirement — but forcing CI to pass before merge means a
broken direction index can never reach `main`. That is the one thing worth protecting.

If the API call is fiddly, do it in the browser: Settings → Branches → Add rule →
`main` → *Require status checks to pass*.

### Turn off what you don't use

Settings → General → Features: uncheck Wikis and Projects. Keep **Issues** — you'll
use them in step 9.

### Placeholders

Already done — `README.md`, `pyproject.toml` and `CITATION.cff` point at
`github.com/rana-rishith/failure-direction`.

## 8. The daily loop

```powershell
git switch -c stage0-manifest       # branch per unit of work
# ... edit ...
ruff check . ; pytest               # never push red
git add -A
git commit -m "data: parse MarVEN layout into inventory.csv"
git push -u origin stage0-manifest
gh pr create --fill
gh pr merge --squash --delete-branch
```

Branch names that match the pipeline: `stage0-*`, `stage1-*`, `gate`, `stage2-*`.

Commit message prefixes, kept consistent so `git log --oneline` reads as a project
history: `data:`, `model:`, `metric:`, `exp:`, `docs:`, `fix:`, `chore:`.

**Never `git push --force` to `main`** once the gate has been evaluated. The whole
credibility of `results/gate_decision.json` rests on its timestamp being un-rewritable.

## 9. Make the repo tell the story

This is the part that separates a code dump from something a CMU faculty member can
skim in ninety seconds.

### Milestones and issues

```powershell
gh api -X POST repos/:owner/failure-direction/milestones -f title="Stage 0 — data + environment"
gh api -X POST repos/:owner/failure-direction/milestones -f title="Stage 1 — characterize + explain"
gh api -X POST repos/:owner/failure-direction/milestones -f title="Gate"
gh api -X POST repos/:owner/failure-direction/milestones -f title="Stage 2 — predictor"

gh issue create --title "Verify noise = noisy - clean holds on MarVEN" --milestone "Stage 0 — data + environment"
gh issue create --title "Rewrite parse_marven() against the real tree" --milestone "Stage 0 — data + environment"
gh issue create --title "Commit final gate thresholds before any aggregate runs" --milestone "Gate"
```

An open issue with a date on it is more convincing than a README bullet.

### Tag each stage

```powershell
git tag -a v0.1-stage0 -m "Stage 0 complete: manifest built, mixture identity verified"
git push origin v0.1-stage0
gh release create v0.1-stage0 --generate-notes
```

### CI badge

`.github/workflows/ci.yml` already runs ruff + pytest on every push. Once the first
run is green, add the badge to the README header:

```markdown
![ci](https://github.com/rana-rishith/failure-direction/actions/workflows/ci.yml/badge.svg)
```

### Archive for a DOI

When there is a paper: connect the repo at [zenodo.org/account/settings/github](https://zenodo.org/account/settings/github),
then cut a release. Zenodo mints a DOI for that exact snapshot, which is what you cite
and what a reviewer can actually run.

---

## What must never be committed

`.gitignore` already covers these. Check it survived any edits.

| | Why |
|---|---|
| `data/raw/` | 15 GB, and MarVEN has its own DOI — link, don't copy |
| `runs/`, `*.pt`, `*.ckpt` | regenerable, and they blow past GitHub's limits |
| `*.wav` | same |
| `.venv/` | machine-specific paths |

## What must always be committed

| | Why |
|---|---|
| `requirements.lock.txt` | the exact environment the numbers came from |
| every file in `configs/` | no hardcoded hyperparameters, ever |
| every CSV in `results/` | small, and they are the evidence |
| `results/gate_decision.json` | whatever it says |

That last one is the point. A gate you only commit when it passes is not a gate.
