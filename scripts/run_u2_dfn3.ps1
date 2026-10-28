# Gate U2's diverse_pretrained arm, end to end: DFN3 fine-tuned on half A of each fold,
# then enhanced over the segment-control windows, then scored into the CSVs U1/U2 read.
#
#   .\scripts\run_u2_dfn3.ps1
#   .\scripts\run_u2_dfn3.ps1 -Folds weather -Steps 2000     # one fold, short
#
# Switches env per step: faildir for the repo code, dfnet for DeepFilterNet. Every step
# is resumable, so rerunning after a crash or a GPU drop picks up where it stopped:
# the crop plan and exported windows are skipped if present, training resumes from its
# last checkpoint, enhancement skips files already written.
#
# One GPU job at a time: do not start this while a U1 or U3 run is going.
param(
    [string[]]$Folds = @("weather", "anthro"),
    [string]$Base = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\u2",
    [int]$Steps = 20000
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
    $in = Join-Path $Base "${fold}_in"
    $out = Join-Path $Base "${fold}_out"
    $tag = "dfn3_seg_$fold"
    Write-Host ""
    Write-Host "######## u2 dfn3: $fold ########"

    Use-Env faildir
    if (-not (Test-Path $plan)) {
        python -m src.segment --fold $fold --export-plan $plan
        Check "export-plan $fold"
    }
    python -m src.segment --fold $fold --export-windows $in
    Check "export-windows $fold"

    Use-Env dfnet
    # Self-check first: the differentiable synthesis must match df.enhance sample for
    # sample, or the fine-tune optimises a shifted target and still looks healthy.
    $wav = (Import-Csv $plan)[0].noisy
    python scripts\dfn_seg.py verify --wav $wav
    Check "synthesis alignment self-check"

    python scripts\dfn_seg.py train --plan $plan --tag $tag --steps $Steps --ckpt-dir "$Repo\ckpt"
    Check "train $tag"
    python scripts\dfn_seg.py enhance --ckpt "$Repo\ckpt\${tag}_last.pt" --in $in --out $out
    Check "enhance $fold"

    Use-Env faildir
    python -m src.segment --fold $fold --score-windows $out --tag dfn3
    Check "score-windows $fold"
}

Use-Env faildir
Write-Host ""
Write-Host "######## u2 verdict ########"
python scripts\run_universal.py --gate u2
# A non-zero exit here is U2 refusing a verdict because a class still has no rows,
# which is not a script failure: it is the gate declining to score an unmeasured arm.
exit 0
