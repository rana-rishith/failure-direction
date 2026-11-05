# Gate U2's generative arm, end to end: SGMSE+ fine-tuned on half A of each fold,
# then enhanced over the segment-control windows, then scored into the CSVs U1/U2 read.
#
#   .\scripts\run_u2_sgmse.ps1
#   .\scripts\run_u2_sgmse.ps1 -Folds weather -Steps 2000     # one fold, short
#   .\scripts\run_u2_sgmse.ps1 -SkipGate                      # leave the verdict alone
#
# Switches env per step: faildir for the repo code, sgmse for SGMSE+. Every step is
# resumable, so rerunning after a crash or a GPU drop picks up where it stopped:
# staging skips crops already written, training resumes from its last.ckpt (every 500
# steps), enhancement skips files already enhanced, scoring and the gate are rerun.
#
# The windows are the SAME directories the DFN3 arm enhanced ($Base\<fold>_in), so both
# U2 arms see byte-identical input. They are produced by --export-windows, which is
# skipped when index.csv is already there.
#
# One GPU job at a time: do not start this while a U1, U3 or DFN3 run is going.
#
# Cost measured on an 8 GB RTX 4060 Laptop: training 0.85 h per 1,000 steps, so 17 h a
# fold. Enhancement is 6,055 windows of 3 s across both folds.
param(
    [string[]]$Folds = @("weather", "anthro"),
    [string]$Base = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\u2",
    [string]$Sgmse = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\sgmse",
    [int]$Steps = 20000,
    [switch]$SkipGate
)

$Repo = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\repo-failure-direction"
$Orig = $env:PATH
$env:FAILDIR_ROOT = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT = "$Repo\ckpt"
Set-Location $Repo

function Use-Env($name) {
    $e = "C:\Users\ranar\anaconda3\envs\$name"
    $env:PATH = "$e;$e\Library\mingw-w64\bin;$e\Library\usr\bin;$e\Library\bin;$e\Scripts;$e\bin;" + $Orig
}

function Check($what) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "FAILED: $what (exit $LASTEXITCODE). Nothing after this ran." -ForegroundColor Red
        exit 1
    }
}

foreach ($fold in $Folds) {
    $plan = "results\segment\plan_$fold.csv"
    $in   = Join-Path $Base "${fold}_in"
    $out  = Join-Path $Base "${fold}_out_sgmse"
    $data = Join-Path $Sgmse "u2_$fold"
    $tag  = "sgmse_seg_$fold"
    Write-Host ""
    Write-Host "######## u2 sgmse: $fold ########"
    Write-Host "started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

    Use-Env faildir
    if (-not (Test-Path $plan)) {
        python -m src.segment --fold $fold --export-plan $plan
        Check "export-plan $fold"
    }
    if (-not (Test-Path (Join-Path $in "index.csv"))) {
        python -m src.segment --fold $fold --export-windows $in
        Check "export-windows $fold"
    }

    Use-Env sgmse
    # SGMSE+ reads training audio off disk, so the half-A crops are rendered first.
    python scripts\sgmse_seg.py stage --plan $plan --base $data
    Check "stage $fold"
    python scripts\sgmse_seg.py verify --base $data
    Check "verify staged $fold"

    python scripts\sgmse_seg.py train --base $data --tag $tag `
        --init-ckpt (Join-Path $Sgmse "ckpt\SB_16k.pt") `
        --ckpt-dir "$Repo\ckpt" --steps $Steps
    Check "train $tag"

    # enhance_resumable.py imports sgmse from the current directory, so it runs there.
    Push-Location $Sgmse
    python enhance_resumable.py --test_dir $in --enhanced_dir $out `
        --ckpt (Join-Path $Repo "ckpt\$tag\last.ckpt")
    $rc = $LASTEXITCODE
    Pop-Location
    $global:LASTEXITCODE = $rc
    Check "enhance $fold"

    Use-Env faildir
    python -m src.segment --fold $fold --score-windows $out --tag sgmse
    Check "score-windows $fold"
    Write-Host "finished ${fold}: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

if (-not $SkipGate) {
    Write-Host ""
    Write-Host "######## u2 verdict ########"
    Use-Env faildir
    python scripts\run_universal.py --gate u2 --force
    Check "u2 verdict"
}
$env:PATH = $Orig
