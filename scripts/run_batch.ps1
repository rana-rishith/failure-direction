# Unattended queue, about 4-5 hours on the RTX 4060. From the repo root:
#     conda activate faildir
#     powershell -ExecutionPolicy Bypass -File .\run_batch.ps1
#
# Safe to rerun after any crash: finished training resumes or is skipped,
# finished evaluations are skipped, and the stationarity test never runs twice.
# Everything is logged to logs\batch_<date>_<time>.log.

$ErrorActionPreference = "Continue"     # python writes progress to stderr; do not abort on it
# the script now lives in scripts/, so the repo root is two levels up
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$env:FAILDIR_ROOT = "$env:USERPROFILE\Downloads\MAIN-failure-direction(ALL)\Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
$py = "$env:USERPROFILE\anaconda3\envs\faildir\python.exe"
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$log = Join-Path $repo ("logs\batch_" + (Get-Date -Format "yyyyMMdd_HHmm") + ".log")
powercfg /change standby-timeout-ac 0

function Say($text) { $text | Tee-Object -FilePath $log -Append }

function Step($name, [string[]]$cmd) {
    Say ("`n=== " + $name + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
    & $py -u @cmd 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) {
        Say ("!!! " + $name + " failed (exit " + $LASTEXITCODE + "). Fix, then rerun run_batch.ps1; done steps are skipped.")
        exit 1
    }
}

Step "GPU check" @("-c", "import torch, sys; ok = torch.cuda.is_available(); print('cuda', ok, torch.cuda.get_device_name(0) if ok else ''); sys.exit(0 if ok else 2)")

if (Test-Path "results\method\m0_summary.csv") { Say "M0 already done, skipping" }
else { Step "M0 oracle sweep" @("-m", "src.method_oracle") }

Step "train cm_weather" @("-m", "src.train", "--model", "cm", "--fold", "weather")
Step "train cm_anthro"  @("-m", "src.train", "--model", "cm", "--fold", "anthro")
Step "train cm_demand"  @("-m", "src.diverse", "--train", "--model", "cm")
Step "train b3_demand"  @("-m", "src.diverse", "--train", "--model", "b3")

foreach ($t in @("b3_weather", "b3_anthro", "b3_demand", "cm_weather", "cm_anthro", "cm_demand")) {
    if (Test-Path ("results\diverse\" + $t + ".csv")) { Say ($t + " already evaluated, skipping") }
    else { Step ("eval " + $t) @("-m", "src.diverse", "--eval", $t) }
}

Step "diverse report" @("-m", "src.diverse", "--report")

if (Test-Path "results\stationarity\summary_full.csv") { Say "stationarity test already run once; not rerunning (gate: run_once)" }
else { Step "stationarity test (pre-registered, run once)" @("-m", "src.stationarity", "--set", "full") }

Say ("`nALL DONE   " + (Get-Date -Format "HH:mm:ss"))
