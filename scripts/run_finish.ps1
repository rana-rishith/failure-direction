# Finish gate XN2: SGMSE+ to exactly 40 paired base rows (configs\gate_xn2_sgmse_ext.yaml), then score and report.
#
#   powershell -ExecutionPolicy Bypass -File .\run_finish.ps1
#
# 1. commits the XN2 results, then the gate amendment (before any new SGMSE+ file)
# 2. SGMSE+ resumes the ordered list and is stopped once 280 files exist (about 2.7 h at ~95 s/file)
# 3. scores SGMSE+ only, regenerates report2 (src.xn2 + src.xn2_extra), commits, pushes
# Safe to rerun: commits are skipped when nothing changed, SGMSE+ resumes.
$ErrorActionPreference = "Continue"
# the script now lives in scripts/, so the repo root is two levels up
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$R  = Split-Path -Parent $repo
$SG = Join-Path $R "sgmse"
$ENVS = "C:\Users\ranar\anaconda3\envs"
$basePath = $env:PATH
$env:FAILDIR_ROOT = Join-Path $R "Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
Remove-Item Env:FAILDIR_EVAL -ErrorAction SilentlyContinue
$TARGET = 280
New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$start = Get-Date
$log = Join-Path $repo ("logs\finish_" + $start.ToString("yyyyMMdd_HHmm") + ".log")
function Say($t) { Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }
function UseEnv($name) {
    $E = Join-Path $ENVS $name
    $env:PATH = "$E;$E\Library\mingw-w64\bin;$E\Library\usr\bin;$E\Library\bin;$E\Scripts;$E\bin;" + $basePath
    return (Join-Path $E "python.exe")
}
function Py([string[]]$cmd) {
    $py = UseEnv "faildir"
    Say ("`n=== " + ($cmd -join " ") + "   " + (Get-Date -Format "HH:mm:ss") + " ===")
    & $py -u @cmd 2>&1 | ForEach-Object { Say ("$_") }
    return ($LASTEXITCODE -eq 0)
}
function Commit([string[]]$paths, [string[]]$msg) {
    git add -- @paths 2>&1 | Out-Null
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Say "commit skipped (nothing new): $($msg[0])"; return }
    $m = @(); foreach ($x in $msg) { $m += "-m"; $m += $x }
    git commit -q @m 2>&1 | ForEach-Object { Say ("$_") }
    Say ("committed " + (git rev-parse --short HEAD) + ": " + $msg[0])
}
function Count() { return (Get-ChildItem (Join-Path $SG "xc_sg_out") -Filter *.wav -ErrorAction SilentlyContinue).Count }

Add-Type -Namespace Fin -Name Pwr -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Fin.Pwr]::SetThreadExecutionState([uint32]2147483649) | Out-Null
Say "start $start"
git reset -q   # unstage anything staged by hand

# 1. results of the XN2 run, then the amendment
Commit @("results/xcorpus/report2", "results/xcorpus/manifest.csv", "results/xcorpus/manifest_parts",
         "results/xcorpus/ext_dfn3.csv", "results/xcorpus/ext_sgmse.csv", "src/xn2_extra.py") `
       @("Gate XN2 results: FSD50K diversity, demand seeds, low-cut SI-SDR, DFN3 final",
         "D_fsd partial (nr_g 0.92-0.96, d_g < 0), H_D2 stable, H_FD widens, H_F not_family_specific (0/9),",
         "C1_lowcut sub100_dependent (weather 0.68-0.72), DFN3 H_P model_trait, SGMSE+ underpowered (25 rows).",
         "src/xn2_extra.py: per-SNR split for fsd/demand models, C1 vs Table III reconciliation (descriptive).")
Commit @("configs/gate_xn2_sgmse_ext.yaml", "src/xcorpus.py", "run_finish.ps1") `
       @("Pre-commit XN2 amendment: SGMSE+ H_P_final at exactly 40 paired base rows",
         "Fixed stop at the first 280 ordered files (base ranks 0-4 x 8 SNRs). ext-score --models.")

# 2. SGMSE+ to 280 files
$n0 = Count
if ($n0 -lt $TARGET) {
    $py = UseEnv "sgmse"
    Say ("`n=== SGMSE+ to $TARGET files   " + (Get-Date -Format "HH:mm:ss") + "   ($n0 on disk) ===")
    $o = Join-Path $repo "logs\finish_sgmse_out.log"; $e = Join-Path $repo "logs\finish_sgmse_err.log"
    $p = Start-Process -FilePath $py -WorkingDirectory $SG -PassThru -NoNewWindow -RedirectStandardOutput $o -RedirectStandardError $e `
         -ArgumentList @("-u", "enhance_resumable.py", "--test_dir", "xc_sg_in", "--enhanced_dir", "xc_sg_out", "--ckpt", "ckpt\SB_16k.pt")
    $last = $n0
    while (-not $p.HasExited) {
        Start-Sleep -Seconds 15
        $n = Count
        if ($n -ge $TARGET) { Start-Sleep -Seconds 2; Stop-Process -Id $p.Id -Force; break }
        if ($n -ge $last + 10) { Say ("  " + (Get-Date -Format "HH:mm") + "  $n / $TARGET"); $last = $n }
    }
}
$n = Count
Say "SGMSE+: $n files on disk"
if ($n -lt $TARGET) { Say "!!! fewer than $TARGET files: SGMSE+ exited early, see logs\finish_sgmse_err.log. Rerun this script to resume." }

# 3. score, report, commit
Py @("-m", "src.xcorpus", "ext-score", "--sgmse-dir", $SG, "--models", "sgmse") | Out-Null
Py @("-m", "src.xn2") | Out-Null
Py @("-m", "src.xn2_extra") | Out-Null
if ($n -ge $TARGET) {
    Commit @("results/xcorpus/report2", "results/xcorpus/ext_sgmse.csv") `
           @("Gate XN2 amendment result: SGMSE+ H_P_final on 40 paired base rows")
    git push -q 2>&1 | ForEach-Object { Say ("$_") }
    Say ("pushed: " + (git log -1 --format="%h %s"))
}
[Fin.Pwr]::SetThreadExecutionState([uint32]2147483648) | Out-Null
Say ("`n==== done in " + [math]::Round(((Get-Date) - $start).TotalHours, 2) + " h ====")
Select-String -Path (Join-Path $repo "results\xcorpus\report2\report.md") -Pattern "^## H_P_final: sgmse" -Context 0,4 | ForEach-Object { Say ($_.ToString()) }
