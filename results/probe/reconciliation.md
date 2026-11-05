## Reconciliation: probe vs registered gates

### U1_failure_class: probe beside the registered verdict

Registered: `results/universal/u1class_verdict.json`, gate commit `29c1566`, run 2026-10-28, verdict **PASS**.
Probe reproduces the gate's own unit (median over snr_low rows at R4, both fold
tags of an architecture pooled, level-aligned `_g` basis).

```
arch basis     n_R4    nr_R4    ox_R4    ox_R1  r_add_R4  class                 registered  
b1   full      1095  -0.0142   0.0022   0.0313    0.0032  inert                 inert       
b1   hp100     1095   0.0324   0.0014   0.0304    0.0024  inert                             
b3   full      1095   0.0190   0.0064   0.0464    0.0057  inert                 inert       
b3   hp100     1095   0.0837   0.0047   0.0440    0.0046  inert                             
cm   full      1095   0.0290   0.0034   0.0292    0.0055  inert                 inert       
cm   hp100     1095   0.0690   0.0026   0.0279    0.0048  inert                             
```

ox = r_over_x. Registered medians for comparison:
```
arch     nr_R4    ox_R4    ox_R1  r_add_R4
b1     -0.0142   0.0022   0.0313    0.0032
b3      0.0190   0.0064   0.0464    0.0057
cm      0.0290   0.0034   0.0292    0.0055
```

### D_diversity_control: probe beside the registered summary

Registered: `results/diverse/summary_low_snr_levelaligned.csv` (`_g` basis),
MarVEN test split, SNR <= 0. Verdict rule: `architecture_explains` = median d < 0
AND median noise_removed < 0.3; `diversity_explains` = d > 0 AND nr >= 0.5.

```
tag         cond      basis        n        d       nr  verdict                  reg d  reg nr
b1_demand   marven    full      1095   -0.973    0.154  architecture_explains   -0.973   0.154
b1_demand   marven    hp100     1095   -0.973    0.172  architecture_explains                 
b1_weather  marven_m  full       660    0.153    0.987  diversity_explains       0.153   0.987
b1_weather  marven_m  hp100      660    0.013    0.974  diversity_explains                    
b1_weather  marven_u  full       435   -0.995   -0.011  architecture_explains   -0.995  -0.011
b1_weather  marven_u  hp100      435   -0.994    0.009  architecture_explains                 
b1_anthro   marven_m  full       435    0.472    0.997  diversity_explains       0.472   0.997
b1_anthro   marven_m  hp100      435    0.466    0.997  diversity_explains                    
b1_anthro   marven_u  full       660   -0.994   -0.015  architecture_explains   -0.994  -0.015
b1_anthro   marven_u  hp100      660   -0.978    0.039  architecture_explains                 
```

### Gates the probe cannot reproduce

- `U1_novelty_monotone` and `U2_beyond_bounded` are R1 > R2 > R4 contrasts. R2 is
  the unheard *segment* of a heard recording, which lives in the segment-window
  eval, not in the 2,280-row frozen test split. The probe has no R2 rows, so it
  reports nothing against these two verdicts. They stand as registered.
- `M0`/`M1` (gamma/alpha control) and `U3` (input-side ranking) are not
  direction-metric gates; the probe does not touch them.

### Disagreements

- None on the registered full-band `_g` basis.
