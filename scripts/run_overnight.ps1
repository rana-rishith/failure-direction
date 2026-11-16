# Overnight cross-corpus run, pre-registered in configs\gate_overnight.yaml.
#
#   powershell -ExecutionPolicy Bypass -File .\run_overnight.ps1            # 12.5 h budget
#   powershell -ExecutionPolicy Bypass -File .\run_overnight.ps1 -Hours 14
#
# Plug the laptop in and close other GPU programs. Safe to rerun after any crash:
# every step resumes or skips finished work. Writes only to NEW places:
#   ckpt\*_s2*, ckpt\*_s3*, results\r3, results\r3_s2, results\r3_s3,
#   results\xcorpus, results\_xc_smoke, ..\sgmse\xc_*, FSD50K (dataset)\extracted
# Existing checkpoints and results are never overwritten.
# A failed step is logged and the queue moves on; the summary at the end lists every step.
param([double]$Hours = 12.5)

$ErrorActionPreference = "Continue"
# the script now lives in scripts/, so the repo root is two levels up
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$R  = Split-Path -Parent $repo
$DS = Join-Path $R "Failure-Direction-Datasets"
$SG = Join-Path $R "sgmse"
$ENVS = "$env:USERPROFILE\anaconda3\envs"
$basePath = $env:PATH
$env:FAILDIR_ROOT = Join-Path $DS "MarVEN"
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
Remove-Item Env:FAILDIR_EVAL -ErrorAction SilentlyContinue
$DEEPSHIP = Join-Path $DS "DeepShip-main"
$MBARI    = Join-Path $DS "MBARI"
$DEMAND   = Join-Path $DS "DEMAND (dataset)\DEMAND_16k"
$VBDMD    = Join-Path $DS "VoiceBank-DEMAND"

$start = Get-Date
$deadline = $start.AddHours($Hours)
$sgStop = $deadline.AddMinutes(-25)          # leaves time to score and report
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$log = Join-Path $repo ("logs\overnight_" + $start.ToString("yyyyMMdd_HHmm") + ".log")
$status = [ordered]@{}

function Say($t) { Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }

function UseEnv($name) {
    $E = Join-Path $ENVS $name
    $env:PATH = "$E;$E\Library\mingw-w64\bin;$E\Library\usr\bin;$E\Library\bin;$E\Scripts;$E\bin;" + $basePath
    return (Join-Path $E "python.exe")
}

function Step($name, $envName, [string[]]$cmd, $wd = $repo) {
    if ((Get-Date) -gt $deadline) { Say "SKIP $name (past deadline)"; $status[$name] = "skipped: deadline"; return $false }
    $py = UseEnv $envName
    if (-not (Test-Path $py)) { Say "SKIP $name ($py not found)"; $status[$name] = "skipped: no env $envName"; return $false }
    Say ("`n=== " + $name + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
    $t0 = Get-Date
    Push-Location $wd
    & $py -u @cmd 2>&1 | ForEach-Object { Say ("$_") }
    $code = $LASTEXITCODE
    Pop-Location
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    if ($code -eq 0) { $status[$name] = "ok ($mins min)"; return $true }
    Say "!!! $name failed (exit $code); continuing with the next step"
    $status[$name] = "FAILED exit $code ($mins min)"
    return $false
}

# keep the PC awake while this script runs (no permanent power-setting change)
Add-Type -Namespace OvN -Name Pwr -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[OvN.Pwr]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
if ($bat -and $bat.BatteryStatus -ne 2) { Say "WARNING: laptop does not report AC power. Plug it in." }
Say "start $start   deadline $deadline   SGMSE stops at $sgStop"
Say ("commit " + (git rev-parse --short HEAD))

if (-not (Step "GPU check" "faildir" @("-c", "import torch, sys; ok = torch.cuda.is_available(); print('cuda', ok, torch.cuda.get_device_name(0) if ok else ''); sys.exit(0 if ok else 2)"))) {
    Say "No CUDA. Stopping: everything below needs the GPU."; exit 1
}

# 1. finish gate R3 (R1/R3 are on disk and skipped)
Step "R3 finish" "faildir" @("-m", "src.r3", "--deepship", $DEEPSHIP, "--mbari", $MBARI) | Out-Null

# 2. smoke test of the cross-corpus pipeline in a separate folder
$env:FAILDIR_EVAL = Join-Path $repo "results\_xc_smoke"
$xcOK = (Step "xcorpus smoke build" "faildir" @("-m", "src.xcorpus", "build", "--smoke", "--deepship", $DEEPSHIP, "--mbari", $MBARI, "--demand", $DEMAND, "--vbdmd", $VBDMD)) -and
        (Step "xcorpus smoke eval" "faildir" @("-m", "src.xcorpus", "eval", "--smoke", "--tags", "b1_anthro", "b3_anthro", "cm_anthro"))
Remove-Item Env:FAILDIR_EVAL -ErrorAction SilentlyContinue
if (-not $xcOK) { Say "xcorpus smoke failed: cross-corpus steps will be skipped" }

# 3. build the real mixtures (CPU, ~15 min)
if ($xcOK) { $xcOK = Step "xcorpus build" "faildir" @("-m", "src.xcorpus", "build", "--deepship", $DEEPSHIP, "--mbari", $MBARI, "--demand", $DEMAND, "--vbdmd", $VBDMD) }

# 4. seed replicates: all of seed 2, then all of seed 3 (~2 h per seed)
foreach ($s in 2, 3) {
    foreach ($k in "b1", "b3", "cm") {
        foreach ($fam in "anthro", "weather") {
            $tag = "${k}_${fam}_s$s"
            if (Test-Path (Join-Path $repo "ckpt\$tag.pt")) { Say "$tag already trained"; $status["train $tag"] = "done earlier"; continue }
            if (($sgStop - (Get-Date)).TotalMinutes -lt 240) { Say "SKIP train $tag (less than 4 h left: evaluation comes first)"; $status["train $tag"] = "skipped: time"; continue }
            Step "train $tag" "faildir" @("-m", "src.train", "--model", $k, "--fold", $fam, "--seed", "$s", "--tag", $tag) | Out-Null
        }
    }
    if ((Test-Path "ckpt\b1_anthro_s$s.pt") -and (Test-Path "ckpt\b3_anthro_s$s.pt") -and (Test-Path "ckpt\cm_anthro_s$s.pt")) {
        Step "R3 seed $s" "faildir" @("-m", "src.r3", "--suffix", "_s$s", "--deepship", $DEEPSHIP) | Out-Null
    }
}

# 5. every checkpoint x every condition (~2-3 h)
if ($xcOK) { Step "xcorpus eval" "faildir" @("-m", "src.xcorpus", "eval") | Out-Null }

# 6. pretrained models
$extOK = $false
if ($xcOK) { $extOK = Step "ext prep" "faildir" @("-m", "src.xcorpus", "ext-prep", "--sgmse-dir", $SG) }
if ($extOK) {
    Step "DFN3 all mixtures" "dfnet" @((Join-Path $repo "src\dfn_enhance.py"), "--test_dir", (Join-Path $SG "xc_dfn_in"), "--enhanced_dir", (Join-Path $SG "xc_dfn_out")) | Out-Null
}

# 7. FSD50K extraction in the background, low priority (prep only, not analysed tonight)
$z = @("C:\Program Files\7-Zip\7z.exe", "C:\Program Files (x86)\7-Zip\7z.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
$fsd = Join-Path $DS "FSD50K (dataset)"
$fsdOut = Join-Path $fsd "extracted"
$fsdJob = $null
if (Test-Path (Join-Path $fsdOut "_done.txt")) { $status["FSD50K extract"] = "done earlier" }
elseif ($z) {
    Say "FSD50K: extracting in the background with $z"
    $fsdJob = Start-Job -ArgumentList $z, $fsd, $fsdOut -ScriptBlock {
        param($z, $fsd, $out)
        New-Item -ItemType Directory -Force $out | Out-Null
        foreach ($a in "FSD50K.ground_truth.zip", "FSD50K.doc.zip", "FSD50K.metadata.zip", "FSD50K.eval_audio.zip", "FSD50K.dev_audio.zip") {
            $p = Join-Path $fsd $a
            if (-not (Test-Path $p)) { "missing $a"; continue }
            $proc = Start-Process -FilePath $z -ArgumentList "x `"$p`" -o`"$out`" -aos -y" -PassThru -WindowStyle Hidden
            try { $proc.PriorityClass = "BelowNormal" } catch {}
            $proc.WaitForExit()
            "$a exit $($proc.ExitCode)"
        }
        Set-Content (Join-Path $out "_done.txt") "ok"
    }
} else { Say "FSD50K: 7-Zip not found, extraction skipped"; $status["FSD50K extract"] = "skipped: no 7-Zip" }

# 8. SGMSE+ on the interleaved paired set until the deadline (~33 s per file)
if ($extOK -and (Get-Date) -lt $sgStop) {
    $py = UseEnv "sgmse"
    if (Test-Path $py) {
        Say ("`n=== SGMSE+ until " + $sgStop.ToString("HH:mm") + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
        $o = Join-Path $repo "logs\overnight_sgmse_out.log"; $e = Join-Path $repo "logs\overnight_sgmse_err.log"
        $p = Start-Process -FilePath $py -WorkingDirectory $SG -PassThru -NoNewWindow -RedirectStandardOutput $o -RedirectStandardError $e `
             -ArgumentList @("-u", "enhance_resumable.py", "--test_dir", "xc_sg_in", "--enhanced_dir", "xc_sg_out", "--ckpt", "ckpt\SB_16k.pt")
        while (-not $p.HasExited -and (Get-Date) -lt $sgStop) { Start-Sleep -Seconds 30 }
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Say "SGMSE+ stopped at the deadline (resumable: rerun continues)" }
        $n = (Get-ChildItem (Join-Path $SG "xc_sg_out") -Filter *.wav -ErrorAction SilentlyContinue).Count
        $status["SGMSE+"] = "$n files enhanced"
        Say "SGMSE+: $n files"
    } else { $status["SGMSE+"] = "skipped: no sgmse env" }
}

if ($fsdJob) {
    Say "waiting for FSD50K extraction"
    Wait-Job $fsdJob -Timeout 3600 | Out-Null
    Receive-Job $fsdJob | ForEach-Object { Say "FSD50K: $_" }
    $status["FSD50K extract"] = $fsdJob.State
}

# 9. score and report
if ($extOK) { Step "ext score" "faildir" @("-m", "src.xcorpus", "ext-score", "--sgmse-dir", $SG) | Out-Null }
Step "report" "faildir" @("-m", "src.xcorpus", "report") | Out-Null

[OvN.Pwr]::SetThreadExecutionState([uint32]2147483648) | Out-Null
Say ("`n==== SUMMARY  (" + [math]::Round(((Get-Date) - $start).TotalHours, 2) + " h) ====")
foreach ($k in $status.Keys) { Say ("{0,-28} {1}" -f $k, $status[$k]) }
Say "report: results\xcorpus\report\report.md"
