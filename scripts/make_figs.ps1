# Rebuild every paper figure into paper\figs as .svg (+ .pdf for LaTeX).
#
#   powershell -ExecutionPolicy Bypass -File .\make_figs.ps1
#
# New figures (pipeline, Claim 3 chain, diversity, features) read committed
# result tables only. Existing figures are re-rendered from results\eval;
# fig_spectrograms needs the GPU, the b1 checkpoints and MarVEN audio.
# The retired figs\claim3_drho is not rebuilt.
$ErrorActionPreference = "Continue"
# the script now lives in scripts/, so the repo root is two levels up
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo
$R = Split-Path -Parent $repo
$E = "$env:USERPROFILE\anaconda3\envs\faildir"
$env:PATH = "$E;$E\Library\mingw-w64\bin;$E\Library\usr\bin;$E\Library\bin;$E\Scripts;$E\bin;" + $env:PATH
$py = Join-Path $E "python.exe"
$env:FAILDIR_ROOT = Join-Path $R "Failure-Direction-Datasets\MarVEN"
# The figure scripts import pandas directly and never import config.py, so the
# pin there does not reach them and MKL kills them with 0xc06d007f.
if (-not $env:MKL_THREADING_LAYER) { $env:MKL_THREADING_LAYER = "SEQUENTIAL" }
$env:FAILDIR_CKPT = Join-Path $repo "ckpt"
$man = Join-Path $env:FAILDIR_ROOT "manifest.csv"
$out = "paper\figs"
New-Item -ItemType Directory -Force $out | Out-Null
$sv = "scripts\svg_runner.py"
$failed = @()

function Run($name, [string[]]$cmd) {
    Write-Host "`n=== $name ==="
    & $py -u @cmd
    if ($LASTEXITCODE -ne 0) { $script:failed += $name }
}

Run "new figures" @("scripts\paper_figs.py", "--out-dir", $out)
Run "claim1_snr" @($sv, "scripts\plot_claim1_snr.py", "--eval-dir", "results\eval", "--manifest", $man, "--out", "$out\claim1_snr")
Run "fig_direction" @($sv, "scripts\fig_direction.py", "--eval-dir", "results\eval", "--out", "$out\fig_direction")
Run "appendix a1-a4" @($sv, "scripts\fig_appendix.py", "a1", "a2", "a3", "a4",
    "--eval-dir", "results\eval", "--wer-csv", "results\wer_snrmax-5.csv",
    "--curves-csv", "results\metrics\training_curves.csv", "--out-dir", $out)
# Not through $sv: this one writes its own .pdf and .png and no .svg, so it will not
# appear in the listing below. It reads u1_cells.csv and u2_cells.csv, which the U2
# gate rewrites, so fig_ladder is the figure that goes stale after a U2 rerun.
Run "fig_ladder + fig_u3_ceiling" @("paper\figs_src\fig_universal.py")
Run "fig_spectrograms (GPU)" @($sv, "scripts\fig_spectrograms.py")
if (Test-Path "figures\fig_spectrograms.svg") { Copy-Item "figures\fig_spectrograms.*" $out -Force }

Write-Host "`n=== done ==="
Get-ChildItem $out -Filter *.svg | ForEach-Object { Write-Host ("  " + $_.Name) }
if ($failed.Count) { Write-Host ("`n!!! failed: " + ($failed -join ", ")) } else { Write-Host "`nall figures built" }
