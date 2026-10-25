# Claim 3 on active models (configs\gate_claim3_active.yaml).
#
#   powershell -ExecutionPolicy Bypass -File .\run_claim3_active.ps1
#
# 0. refuses to start unless the gate is committed AND pushed (timestamp before any result)
# 1. harness: new waveform labeller must reproduce labels_level for b1_weather (gate rule)
# 2. labels for the 9 FSD checkpoints, one pass over all 22,754 rows (resumable chunks)
# 3. DFN3 on all 22,754 rows (dfnet env, resumable), then scored
# 4. src.claim3_active -> results\claim3_active\report.md, then commit (you push)
# Safe to rerun: every step resumes.
param([string]$DfnOut = "")
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
$R = Split-Path -Parent $repo
if (-not $DfnOut) { $DfnOut = Join-Path $R "dfn3_marven_out" }
$ENVS = "C:\Users\ranar\anaconda3\envs"
$basePath = $env:PATH
$env:FAILDIR_ROOT = Join-Path $R "Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
Remove-Item Env:FAILDIR_EVAL -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$start = Get-Date
$log = Join-Path $repo ("logs\claim3_active_" + $start.ToString("yyyyMMdd_HHmm") + ".log")
function Say($t) { Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }
function UseEnv($name) {
    $E = Join-Path $ENVS $name
    $env:PATH = "$E;$E\Library\mingw-w64\bin;$E\Library\usr\bin;$E\Library\bin;$E\Scripts;$E\bin;" + $basePath
    return (Join-Path $E "python.exe")
}
function Py([string]$envName, [string[]]$cmd) {
    $py = UseEnv $envName
    Say ("`n=== [$envName] " + ($cmd -join " ") + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
    & $py -u @cmd 2>&1 | ForEach-Object { Say ("$_") }
    return ($LASTEXITCODE -eq 0)
}

# 0. gate must be on GitHub before any result exists
git fetch -q 2>&1 | Out-Null
$gateCommit = git log -1 --format=%h -- configs/gate_claim3_active.yaml
if (-not $gateCommit) { Write-Host "!!! configs\gate_claim3_active.yaml is not committed. Commit and push it first."; exit 1 }
git merge-base --is-ancestor $gateCommit origin/main
if ($LASTEXITCODE -ne 0) { Write-Host "!!! gate commit $gateCommit is not pushed. Run: git push   then rerun this script."; exit 1 }
Say "start $start   gate $gateCommit (pushed)   DFN3 out: $DfnOut"
Add-Type -Namespace C3A -Name Pwr -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[C3A.Pwr]::SetThreadExecutionState([uint32]2147483649) | Out-Null   # keep the laptop awake

# 1. harness
if (-not (Py "faildir" @("-m", "src.labels_active", "harness"))) {
    Say "!!! harness FAILED: stopping (gate rule). Send me the log."; exit 1
}

# 2. FSD-trained models (primary seed first in the tag list; all 9 in one pass)
$tags = @("b1_fsd", "b3_fsd", "cm_fsd", "b1_fsd_s2", "b3_fsd_s2", "cm_fsd_s2", "b1_fsd_s3", "b3_fsd_s3", "cm_fsd_s3")
$okInt = Py "faildir" (@("-m", "src.labels_active", "internal", "--tags") + $tags)
if (-not $okInt) { Say "!!! internal labels failed: rerun to resume" }

# 3. DFN3
Py "faildir" @("-m", "src.labels_active", "list") | Out-Null
$okDfn = Py "dfnet" @((Join-Path $repo "src\dfn_marven.py"), "--rows", (Join-Path $repo "results\labels_active\rows_dfn.csv"), "--out", $DfnOut)
if (-not $okDfn) { Say "!!! DFN3 exited early: rerun to resume" }
Py "faildir" @("-m", "src.labels_active", "dfn", "--dfn-dir", $DfnOut) | Out-Null

# 4. verdict
$okV = Py "faildir" @("-m", "src.claim3_active")
if ($okV) {
    git add -- results/claim3_active/report.md results/claim3_active/verdict.csv results/claim3_active/per_type.csv `
               results/claim3_active/agreement.csv results/labels_active/harness.csv results/labels_active/dfn3_completeness.csv 2>&1 | Out-Null
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -q -m "Gate C3_active result: Claim 3 on FSD-trained models and DFN3" 2>&1 | ForEach-Object { Say ("$_") }
        Say ("committed " + (git rev-parse --short HEAD) + "  (run: git push)")
    }
}
[C3A.Pwr]::SetThreadExecutionState([uint32]2147483648) | Out-Null
Say ("`n==== done in " + [math]::Round(((Get-Date) - $start).TotalHours, 2) + " h ====")
if (Test-Path "results\claim3_active\report.md") {
    Select-String -Path "results\claim3_active\report.md" -Pattern "^## Verdict" | ForEach-Object { Say ($_.Line) }
}
