# Claim 3c: weather noise, held-out seeds 6 and 7 (configs/gate_claim3c.yaml)

## Verdict: HOLDS

- b1_fsd_s6: pass
- b1_fsd_s7: pass
- b3_fsd_s6: pass
- b3_fsd_s7: pass
- cm_fsd_s6: pass
- cm_fsd_s7: pass

## Verdict rules per model (weather fold: rules a, b, t)

      tag  rule_a  rule_b  rule_t  pass
b1_fsd_s6    True    True    True  True
b1_fsd_s7    True    True    True  True
b3_fsd_s6    True    True    True  True
b3_fsd_s7    True    True    True  True
cm_fsd_s6    True    True    True  True
cm_fsd_s7    True    True    True  True

## Weather fold (verdict)

      tag    fold  mean_within_snr_rho_featsonly  mean_within_snr_rho_baseline  snr_strata_won  snr_strata  cells_won_frac  cells  auc_top10_featsonly_minus_baseline  rule_a  rule_b  pass  bubble_cells_won  bubble_cells rule_c
b1_fsd_s6 weather                          0.770                         0.202               8           8           0.958     24                               0.060    True    True  True               NaN           NaN    NaN
b1_fsd_s7 weather                          0.723                         0.179               8           8           0.958     24                               0.046    True    True  True               NaN           NaN    NaN
b3_fsd_s6 weather                          0.745                         0.186               8           8           0.875     24                               0.068    True    True  True               NaN           NaN    NaN
b3_fsd_s7 weather                          0.751                         0.163               8           8           0.917     24                               0.078    True    True  True               NaN           NaN    NaN
cm_fsd_s6 weather                          0.728                         0.161               8           8           0.958     24                               0.048    True    True  True               NaN           NaN    NaN
cm_fsd_s7 weather                          0.736                         0.160               8           8           1.000     24                               0.065    True    True  True               NaN           NaN    NaN

## Anthro fold (descriptive only; rules a, b, c as C3b)

      tag   fold  mean_within_snr_rho_featsonly  mean_within_snr_rho_baseline  snr_strata_won  snr_strata  cells_won_frac  cells  auc_top10_featsonly_minus_baseline  rule_a  rule_b  pass  bubble_cells_won  bubble_cells rule_c
b1_fsd_s6 anthro                          0.597                         0.391               8           8           0.750     16                               0.007    True    True  True               5.0           8.0  False
b1_fsd_s7 anthro                          0.539                         0.367               7           8           0.688     16                               0.003    True   False False               3.0           8.0  False
b3_fsd_s6 anthro                          0.352                         0.245               6           8           0.688     16                               0.023    True   False False               3.0           8.0  False
b3_fsd_s7 anthro                          0.492                         0.456               6           8           0.625     16                               0.006    True   False False               2.0           8.0  False
cm_fsd_s6 anthro                          0.445                         0.337               8           8           0.812     16                               0.012    True    True  True               6.0           8.0   True
cm_fsd_s7 anthro                          0.468                         0.333               8           8           0.625     16                               0.005    True   False False               3.0           8.0  False

## Per noise type: share of SNR cells won by feats_only (weather = verdict, anthro = descriptive)

           noise_type  cells  won  mean_d_rho  share_won       tag    fold
            hurricane      8    8       0.389      1.000 b1_fsd_s6 weather
            lightning      8    8       0.387      1.000 b1_fsd_s6 weather
             rainfall      8    7       0.369      0.875 b1_fsd_s6 weather
       bubble_curtain      8    5       0.076      0.625 b1_fsd_s6  anthro
large_commercial_ship      8    7       0.327      0.875 b1_fsd_s6  anthro
            hurricane      8    8       0.318      1.000 b1_fsd_s7 weather
            lightning      8    7       0.305      0.875 b1_fsd_s7 weather
             rainfall      8    8       0.453      1.000 b1_fsd_s7 weather
       bubble_curtain      8    3       0.001      0.375 b1_fsd_s7  anthro
large_commercial_ship      8    8       0.284      1.000 b1_fsd_s7  anthro
            hurricane      8    8       0.421      1.000 b3_fsd_s6 weather
            lightning      8    6       0.311      0.750 b3_fsd_s6 weather
             rainfall      8    7       0.471      0.875 b3_fsd_s6 weather
       bubble_curtain      8    3      -0.090      0.375 b3_fsd_s6  anthro
large_commercial_ship      8    8       0.330      1.000 b3_fsd_s6  anthro
            hurricane      8    7       0.309      0.875 b3_fsd_s7 weather
            lightning      8    8       0.347      1.000 b3_fsd_s7 weather
             rainfall      8    7       0.433      0.875 b3_fsd_s7 weather
       bubble_curtain      8    2      -0.101      0.250 b3_fsd_s7  anthro
large_commercial_ship      8    8       0.211      1.000 b3_fsd_s7  anthro
            hurricane      8    8       0.328      1.000 cm_fsd_s6 weather
            lightning      8    8       0.368      1.000 cm_fsd_s6 weather
             rainfall      8    7       0.418      0.875 cm_fsd_s6 weather
       bubble_curtain      8    6       0.052      0.750 cm_fsd_s6  anthro
large_commercial_ship      8    7       0.193      0.875 cm_fsd_s6  anthro
            hurricane      8    8       0.348      1.000 cm_fsd_s7 weather
            lightning      8    8       0.303      1.000 cm_fsd_s7 weather
             rainfall      8    8       0.459      1.000 cm_fsd_s7 weather
       bubble_curtain      8    3      -0.006      0.375 cm_fsd_s7  anthro
large_commercial_ship      8    7       0.296      0.875 cm_fsd_s7  anthro
