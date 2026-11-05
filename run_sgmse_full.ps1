# Enhance the 1,880 frozen-split utterances SGMSE+ has not done yet, then score
# all 2,280 through probe(). Resumable: rerun after any interruption.
#
# Waits for any other GPU python job to exit first. SGMSE+ needs most of the 8 GB,
# and sharing the 4060 with the probe rescore or an sgmse_seg fine-tune drags
# enhancement from 33 s/file to 330-440 s/file, i.e. 170 h rather than 17.
# Budget ~17 h at the pilot's median of 32.7 s per file (~37 h at its mean).
param([switch]$Now)   # -Now: start even while another GPU job holds the card
$ErrorActionPreference = "Stop"
$SG   = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\sgmse"
$REPO = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\repo-failure-direction"
$SGPY = "C:\Users\ranar\anaconda3\envs\sgmse\python.exe"
$FD   = "C:\Users\ranar\anaconda3\envs\faildir"

function GpuBusy {
    # Our own enhance call is excluded by matching only the two jobs that contend
    # for the card: the probe rescore (its own --wav-maps scoring pass is CPU) and
    # an sgmse_seg fine-tune.
    $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
         Where-Object { ($_.CommandLine -like "*src.probe.rescore*" -and $_.CommandLine -notlike "*wav-maps*") `
                        -or $_.CommandLine -like "*sgmse_seg.py*" }
    return [bool]$p
}

$waited = 0
while ((GpuBusy) -and -not $Now -and $waited -lt 172800) {   # give up waiting after 48 h
    if ($waited % 600 -eq 0) { Write-Output ("waiting for the GPU to free up... " + [int]($waited/60) + " min") }
    Start-Sleep -Seconds 60; $waited += 60
}
if ((GpuBusy) -and -not $Now) { Write-Output "GPU still busy after 48 h; not starting SGMSE+"; exit 1 }
Write-Output ("GPU clear after " + [int]($waited/60) + " min; starting SGMSE+ " + (Get-Date -Format "HH:mm:ss"))

$todo = (Get-ChildItem "$SG\full_in" -Filter *.wav).Count
Write-Output "full_in holds $todo wavs to enhance"

# 1. enhancement, in the sgmse env, defaults exactly as every recorded run used
#    (sampler_type pc -> ode for SBVESDE, N 30, corrector ald, snr 0.5, t_eps 0.03)
& $SGPY -u "$SG\enhance_resumable.py" --test_dir "$SG\full_in" `
    --enhanced_dir "$SG\full_out" --ckpt "$SG\ckpt\SB_16k.pt"
Write-Output ("enhancement returned exit code " + $LASTEXITCODE)

# 2. failures: the log records every attempt; missing outputs are the real test
$made = (Get-ChildItem "$SG\full_out" -Filter *.wav -ErrorAction SilentlyContinue).Count
Write-Output "`n=== enhancement check ==="
Write-Output "wavs produced: $made of $todo"
$log = "$SG\full_out_log.csv"
if (Test-Path $log) {
    $rows = Import-Csv $log
    Write-Output ("log rows: " + $rows.Count)
    $rows | Group-Object status | ForEach-Object { Write-Output ("  status " + $_.Name + ": " + $_.Count) }
    $bad = $rows | Where-Object { $_.status -ne "ok" }
    if ($bad) { Write-Output "`nnon-ok attempts:"; $bad | Select-Object -First 15 |
                ForEach-Object { Write-Output ("  " + $_.file + "  " + $_.status) } }
}
$missing = @(Get-ChildItem "$SG\full_in" -Filter *.wav | Where-Object {
    -not (Test-Path (Join-Path "$SG\full_out" $_.Name)) })
Write-Output ("missing outputs: " + $missing.Count)
if ($missing.Count) { $missing | Select-Object -First 15 | ForEach-Object { Write-Output ("  " + $_.Name) } }

# 3. score all 2,280 as ONE population: the 400 pilot outputs plus the new ones
$env:PATH = "$FD;$FD\Library\mingw-w64\bin;$FD\Library\usr\bin;$FD\Library\bin;$FD\Scripts;$FD\bin;" + $env:PATH
$env:FAILDIR_ROOT   = "C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\Failure-Direction-Datasets\MarVEN"
$env:FAILDIR_CKPT   = "$REPO\ckpt"
$env:FAILDIR_DEVICE = "cpu"      # scoring from wavs needs no GPU
Set-Location $REPO
Copy-Item "$SG\pilot_out\*.wav" "$SG\full_out" -Force
$n = (Get-ChildItem "$SG\full_out" -Filter *.wav).Count
Write-Output "`nfull_out holds $n wavs (expect 2280); scoring"
& "$FD\python.exe" -u -m src.probe.rescore --force --wav-maps "sgmse=$SG\full_out"
