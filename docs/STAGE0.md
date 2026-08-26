# Stage 0 — environment and data

## 0.1 Environment (Windows, RTX 3060 12 GB / Ampere sm_86)

```powershell
py -3.11 -m venv "D:\Rana Rishith\failure-direction\.venv"
& "D:\Rana Rishith\failure-direction\.venv\Scripts\Activate.ps1"
$env:PYTHONNOUSERSITE = "1"      # keep user site-packages out of the venv

pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "import torch; a=torch.randn(4000,4000,device='cuda'); print((a@a).sum().item())"

pip install -e ".[metrics,asr,viz,dev]"
pip freeze > requirements.lock.txt   # commit this
```

Python 3.11 or 3.12 — **not 3.13**. `pesq` has thin wheel coverage on 3.13/Windows
and will try to build from source, which needs MSVC Build Tools.

If the matmul raises `no kernel image is available`, the wheel does not match
sm_86. Fix it now; it will otherwise resurface three weeks in.

## 0.2 Data

Download MarVEN (Zenodo 10.5281/zenodo.20714212, ~15 GB) into `data/raw/marven/`,
or point `--root` at wherever it already lives.

```powershell
python scripts\00_build_manifest.py --root "D:\Rana Rishith\MarVEN" --discover
```

Read that output. Then rewrite `parse_marven()` in the same file to match the
**actual** layout, and run without `--discover`.

## 0.3 The check that gates everything else

```powershell
python scripts\01_verify_pairs.py --n 500
```

The energy decomposition assumes `noise = noisy − clean` holds exactly. If more
than ~1% of pairs fail, the corpus re-encoded or renormalised its mixtures, and
every direction number downstream would be fiction. Request noise stems instead
of working around it.

## 0.4 Splits

```powershell
python scripts\02_make_splits.py
```

Cross-family **and** speaker-disjoint. A reviewer will check the second one.

## Exit checklist

- [ ] `torch.cuda.is_available()` is True inside the venv
- [ ] `requirements.lock.txt` committed
- [ ] `inventory.csv` built, row counts per (family, type, SNR) sane
- [ ] `integrity.csv` shows <1% non-exact mixtures
- [ ] Transcripts present, or WER explicitly deferred to Stage 2 in writing
- [ ] Two fold JSONs written, no speaker overlap
- [ ] `pytest` green
