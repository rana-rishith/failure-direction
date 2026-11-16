# Second long run, pre-registered in configs\gate_overnight2.yaml (gate XN2).
#
#   powershell -ExecutionPolicy Bypass -File .\run_overnight2.ps1             # 20 h budget
#   powershell -ExecutionPolicy Bypass -File .\run_overnight2.ps1 -Hours 17
#
# Plug the laptop in, close other GPU programs. Safe to rerun after any crash: every step
# resumes or skips finished work. Writes only to NEW places:
#   ckpt\*_demand_s2/_s3*, ckpt\*_fsd*, FSD50K (dataset)\extracted + fsd16k,
#   results\xcorpus\manifest_parts\fsd_*, mix\fsd_*, eval\fsd_*, eval_hp\, report2\,
#   new rows in results\xcorpus\eval\*.csv (new checkpoints only), ..\sgmse\xc_* (resumed)
# Existing checkpoints and existing eval rows are never overwritten.
param([double]$Hours = 20)

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
$FSD      = Join-Path $DS "FSD50K (dataset)"
$env:FAILDIR_DEMAND = $DEMAND
$env:FAILDIR_FSD = $FSD

$start = Get-Date
$deadline = $start.AddHours($Hours)
$sgStop = $deadline.AddMinutes(-30)            # score + report after SGMSE
$evalReserve = 220                             # min: xcorpus eval of new tags/conds (~2.3 h) + hp pass (~50 min) + DFN3
$sgReserve = 180                               # min of SGMSE+ guaranteed (about 240 files, past the 40-row gate)
$trainMin = @{ "b1" = 50; "b3" = 30; "cm" = 50 }
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$log = Join-Path $repo ("logs\overnight2_" + $start.ToString("yyyyMMdd_HHmm") + ".log")
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

function MinutesLeft() { return ($sgStop - (Get-Date)).TotalMinutes }

function Train($tag, $k, [string[]]$cmd) {
    if (Test-Path (Join-Path $repo "ckpt\$tag.pt")) { Say "$tag already trained"; $status["train $tag"] = "done earlier"; return $true }
    $need = $trainMin[$k] + $evalReserve + $sgReserve
    if ((MinutesLeft) -lt $need) { Say "SKIP train $tag (needs $need min incl. reserves)"; $status["train $tag"] = "skipped: time"; return $false }
    return (Step "train $tag" "faildir" $cmd)
}

Add-Type -Namespace OvN2 -Name Pwr -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[OvN2.Pwr]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
if ($bat -and $bat.BatteryStatus -ne 2) { Say "WARNING: laptop does not report AC power. Plug it in." }
Say "start $start   deadline $deadline   SGMSE stops at $sgStop"
Say ("commit " + (git rev-parse --short HEAD))

if (-not (Step "GPU check" "faildir" @("-c", "import torch, sys; ok = torch.cuda.is_available(); print('cuda', ok, torch.cuda.get_device_name(0) if ok else ''); sys.exit(0 if ok else 2)"))) {
    Say "No CUDA. Stopping: everything below needs the GPU."; exit 1
}
Step "DEMAND check" "faildir" @("-m", "src.diverse", "--check") | Out-Null

# 1. FSD50K extraction + 16 kHz cache in the background (CPU, below-normal priority)
$fsdJob = $null
if (Test-Path (Join-Path $FSD "fsd16k\_prep_done.txt")) { $status["FSD50K prep"] = "done earlier" }
else {
    $z = @("C:\Program Files\7-Zip\7z.exe", "C:\Program Files (x86)\7-Zip\7z.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    $out = Join-Path $FSD "extracted"
    if (-not (Test-Path (Join-Path $out "_done.txt")) -and -not $z) {
        Say "FSD50K: not extracted and 7-Zip not found: every FSD50K step will be skipped"
        $status["FSD50K prep"] = "skipped: no 7-Zip"
    } else {
        $py = UseEnv "faildir"
        Say "FSD50K: extraction (if needed) + 16 kHz cache in the background"
        $fsdJob = Start-Job -ArgumentList $z, $FSD, $out, $py, $repo, $env:PATH, $env:FAILDIR_ROOT, $env:FAILDIR_FSD -ScriptBlock {
            param($z, $fsd, $out, $py, $repo, $path, $root, $fsdenv)
            $env:PATH = $path; $env:FAILDIR_ROOT = $root; $env:FAILDIR_FSD = $fsdenv
            if (-not (Test-Path (Join-Path $out "_done.txt"))) {
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
            Set-Location $repo
            $proc = Start-Process -FilePath $py -ArgumentList "-u -m src.fsd prep --workers 6" -PassThru -NoNewWindow `
                    -RedirectStandardOutput (Join-Path $repo "logs\overnight2_fsdprep_out.log") -RedirectStandardError (Join-Path $repo "logs\overnight2_fsdprep_err.log")
            try { $proc.PriorityClass = "BelowNormal" } catch {}
            $proc.WaitForExit()
            "prep exit $($proc.ExitCode)"
        }
    }
}

# 2. demand seed 2 (no FSD dependency)
foreach ($k in "b1", "b3", "cm") {
    Train "${k}_demand_s2" $k @("-m", "src.diverse", "--train", "--model", $k, "--seed", "2", "--suffix", "_s2") | Out-Null
}

# 3. FSD50K ready? then check, build the FSD50K mixtures, smoke-train
if ($fsdJob) {
    Say "waiting for FSD50K prep"
    Wait-Job $fsdJob -Timeout 10800 | Out-Null
    Receive-Job $fsdJob | ForEach-Object { Say "FSD50K: $_" }
    $status["FSD50K prep"] = $fsdJob.State
}
$fsdOK = (Test-Path (Join-Path $FSD "fsd16k\_prep_done.txt")) -and (Step "FSD50K check" "faildir" @("-m", "src.fsd", "check"))
if ($fsdOK) {
    $fsdOK = Step "xcorpus build (+FSD50K)" "faildir" @("-m", "src.xcorpus", "build", "--fsd", "--deepship", $DEEPSHIP, "--mbari", $MBARI, "--demand", $DEMAND, "--vbdmd", $VBDMD)
}
$fsdTrainOK = $fsdOK -and (Step "FSD50K smoke train" "faildir" @("-m", "src.fsd", "train", "--model", "b1", "--smoke"))
if ($fsdOK -and -not $fsdTrainOK) { Say "FSD50K smoke training failed: FSD50K models skipped (FSD50K mixtures are still evaluated)" }

# 4. trainings in priority order
if ($fsdTrainOK) {
    foreach ($k in "b1", "b3", "cm") { Train "${k}_fsd" $k @("-m", "src.fsd", "train", "--model", $k) | Out-Null }
    foreach ($k in "b1", "b3", "cm") { Train "${k}_fsd_s2" $k @("-m", "src.fsd", "train", "--model", $k, "--seed", "2", "--suffix", "_s2") | Out-Null }
}
foreach ($k in "b1", "b3", "cm") {
    Train "${k}_demand_s3" $k @("-m", "src.diverse", "--train", "--model", $k, "--seed", "3", "--suffix", "_s3") | Out-Null
}
if ($fsdTrainOK) {
    foreach ($k in "b1", "b3", "cm") { Train "${k}_fsd_s3" $k @("-m", "src.fsd", "train", "--model", $k, "--seed", "3", "--suffix", "_s3") | Out-Null }
}

# 5. evaluation: every new checkpoint x every condition, every checkpoint x the FSD50K conditions
Step "xcorpus eval" "faildir" @("-m", "src.xcorpus", "eval") | Out-Null

# 6. low-cut SI-SDR for the old rows of the seed-1234 main checkpoints
$hpTags = @("b1_anthro", "b1_weather", "b1_demand", "b3_anthro", "b3_weather", "b3_demand", "cm_anthro", "cm_weather", "cm_demand")
Step "low-cut SI-SDR pass" "faildir" (@("-m", "src.xcorpus", "hp", "--tags") + $hpTags) | Out-Null

# 7. DFN3 on the new FSD50K mixtures (resumes; old outputs kept)
$extOK = Step "ext prep" "faildir" @("-m", "src.xcorpus", "ext-prep", "--sgmse-dir", $SG)
if ($extOK) {
    Step "DFN3 new mixtures" "dfnet" @((Join-Path $repo "src\dfn_enhance.py"), "--test_dir", (Join-Path $SG "xc_dfn_in"), "--enhanced_dir", (Join-Path $SG "xc_dfn_out")) | Out-Null
}

# 8. SGMSE+ resumes the interleaved paired list until 30 min before the deadline
if ((Get-Date) -lt $sgStop) {
    $py = UseEnv "sgmse"
    if (Test-Path $py) {
        $n0 = (Get-ChildItem (Join-Path $SG "xc_sg_out") -Filter *.wav -ErrorAction SilentlyContinue).Count
        Say ("`n=== SGMSE+ until " + $sgStop.ToString("HH:mm") + "   " + (Get-Date -Format "HH:mm:ss") + "   ($n0 files on disk) ===")
        $o = Join-Path $repo "logs\overnight2_sgmse_out.log"; $e = Join-Path $repo "logs\overnight2_sgmse_err.log"
        $p = Start-Process -FilePath $py -WorkingDirectory $SG -PassThru -NoNewWindow -RedirectStandardOutput $o -RedirectStandardError $e `
             -ArgumentList @("-u", "enhance_resumable.py", "--test_dir", "xc_sg_in", "--enhanced_dir", "xc_sg_out", "--ckpt", "ckpt\SB_16k.pt")
        while (-not $p.HasExited -and (Get-Date) -lt $sgStop) { Start-Sleep -Seconds 30 }
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Say "SGMSE+ stopped at the deadline (resumable)" }
        $n = (Get-ChildItem (Join-Path $SG "xc_sg_out") -Filter *.wav -ErrorAction SilentlyContinue).Count
        $status["SGMSE+"] = "$n files on disk (+$($n - $n0))"
        Say "SGMSE+: $n files"
    } else { $status["SGMSE+"] = "skipped: no sgmse env" }
}

# 9. score and report
Step "ext score" "faildir" @("-m", "src.xcorpus", "ext-score", "--sgmse-dir", $SG) | Out-Null
Step "XN2 report" "faildir" @("-m", "src.xn2") | Out-Null

[OvN2.Pwr]::SetThreadExecutionState([uint32]2147483648) | Out-Null
Say ("`n==== SUMMARY  (" + [math]::Round(((Get-Date) - $start).TotalHours, 2) + " h) ====")
foreach ($k in $status.Keys) { Say ("{0,-30} {1}" -f $k, $status[$k]) }
Say "report: results\xcorpus\report2\report.md"
