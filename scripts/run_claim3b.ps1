# Claim 3b (configs\gate_claim3b.yaml).
#
#   powershell -ExecutionPolicy Bypass -File .\run_claim3b.ps1
#
# 0. refuses to start unless the gate is committed AND pushed
# 1. burst features for all 22,754 rows (reference-free, resumable)
# 2. train the 6 held-out enhancers (seed 4, 5 x b1/b3/cm); skips any that already exist
# 3. labels for the 6 held-out models (resumable chunks)
# 4. src.claim3b -> verdict, then the descriptive dev run, then commit (you push)
# Safe to rerun: every step resumes.
$ErrorActionPreference = "Continue"
# the script now lives in scripts/, so the repo root is two levels up
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$R = Split-Path -Parent $repo
$E = "C:\Users\ranar\anaconda3\envs\faildir"
$env:PATH = "$E;$E\Library\mingw-w64\bin;$E\Library\usr\bin;$E\Library\bin;$E\Scripts;$E\bin;" + $env:PATH
$py = Join-Path $E "python.exe"
$env:FAILDIR_ROOT = Join-Path $R "Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
Remove-Item Env:FAILDIR_EVAL -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$start = Get-Date
$log = Join-Path $repo ("logs\claim3b_" + $start.ToString("yyyyMMdd_HHmm") + ".log")
function Say($t) { Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }
function Py([string[]]$cmd) {
    Say ("`n=== " + ($cmd -join " ") + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
    & $py -u @cmd 2>&1 | ForEach-Object { Say ("$_") }
    return ($LASTEXITCODE -eq 0)
}

# 0. gate must be on GitHub before any result exists
git fetch -q 2>&1 | Out-Null
$gate = git log -1 --format=%h -- configs/gate_claim3b.yaml
if (-not $gate) { Write-Host "!!! configs\gate_claim3b.yaml is not committed. Commit and push it first."; exit 1 }
git merge-base --is-ancestor $gate origin/main
if ($LASTEXITCODE -ne 0) { Write-Host "!!! gate commit $gate is not pushed. Run: git push   then rerun."; exit 1 }
Say "start $start   gate $gate (pushed)"
Add-Type -Namespace C3B -Name Pwr -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[C3B.Pwr]::SetThreadExecutionState([uint32]2147483649) | Out-Null

# 1. burst features
if (-not (Py @("-m", "src.features_burst"))) { Say "!!! burst features failed: rerun to resume"; exit 1 }

# 2. held-out enhancers
$tags = @()
foreach ($s in 4, 5) {
    foreach ($k in "b1", "b3", "cm") {
        $t = "${k}_fsd_s$s"; $tags += $t
        if (Test-Path (Join-Path $repo "ckpt\${t}_best.pt")) { Say "skip training $t (checkpoint exists)"; continue }
        if (-not (Py @("-m", "src.fsd", "train", "--model", $k, "--seed", "$s", "--suffix", "_s$s"))) {
            Say "!!! training $t failed: rerun to resume"; exit 1
        }
    }
}

# 3. labels
if (-not (Py (@("-m", "src.labels_active", "internal", "--tags") + $tags))) { Say "!!! labels failed: rerun to resume"; exit 1 }

# 4. verdict, then dev (descriptive)
$okV = Py @("-m", "src.claim3b")
Py @("-m", "src.claim3b", "--dev") | Out-Null
if ($okV) {
    git add -- results/claim3b/heldout/report.md results/claim3b/heldout/verdict.csv results/claim3b/heldout/per_type.csv `
               results/claim3b/dev/report.md results/claim3b/dev/verdict.csv results/claim3b/dev/per_type.csv 2>&1 | Out-Null
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -q -m "Gate C3b result: Claim 3b burst features on held-out seeds" 2>&1 | ForEach-Object { Say ("$_") }
        Say ("committed " + (git rev-parse --short HEAD) + "  (run: git push)")
    }
}
[C3B.Pwr]::SetThreadExecutionState([uint32]2147483648) | Out-Null
Say ("`n==== done in " + [math]::Round(((Get-Date) - $start).TotalHours, 2) + " h ====")
if (Test-Path "results\claim3b\heldout\report.md") {
    Select-String -Path "results\claim3b\heldout\report.md" -Pattern "^## Verdict" | ForEach-Object { Say ($_.Line) }
}
