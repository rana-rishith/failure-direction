# Rerun commands for the new analyses. Run from the repo root with FAILDIR_ROOT set.
# 1. No audio needed (about 1 minute each)
python scripts/bypass_si_sdr.py
# 2. Needs the FSD50K cache (python -m src.fsd prep) and MarVEN
python scripts/decomp_check.py paper/revised_2026-11-07   # items A/E4/E5, post hoc, ~6 min
python scripts/fd_fsd.py
# 3. Needs enhanced test wavs per model, and: pip install speechmos
python scripts/dnsmos_arm.py --models b1 b3 cm_fsd_s6
# 4. Needs results/xcorpus (CPU)
python scripts/u3_swap.py --tag b1
# Then rebuild the paper (the paper uses the new numbers once paper/newresults_*.tex exist)
cd paper; latexmk -pdf paper.tex
