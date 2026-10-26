# Claim 3b: burst features (configs/gate_claim3b.yaml)

## Verdict: FAILS

- b1_fsd_s4: pass
- b1_fsd_s5: no pass
- b3_fsd_s4: no pass
- b3_fsd_s5: no pass
- cm_fsd_s4: no pass
- cm_fsd_s5: no pass

## Per model and fold (rules a, b; rule c in the anthro fold)

      tag    fold  mean_within_snr_rho_featsonly  mean_within_snr_rho_baseline  snr_strata_won  snr_strata  cells_won_frac  cells  auc_top10_featsonly_minus_baseline  rule_a  rule_b  pass  bubble_cells_won  bubble_cells rule_c
b1_fsd_s4 weather                          0.724                         0.177               8           8           0.875     24                               0.052    True    True  True               NaN           NaN    NaN
b1_fsd_s4  anthro                          0.563                         0.359               7           8           0.938     16                               0.005    True    True  True               7.0           8.0   True
b1_fsd_s5 weather                          0.733                         0.177               8           8           0.958     24                               0.047    True    True  True               NaN           NaN    NaN
b1_fsd_s5  anthro                          0.539                         0.362               7           8           0.688     16                               0.006    True   False False               6.0           8.0   True
b3_fsd_s4 weather                          0.759                         0.137               8           8           1.000     24                               0.078    True    True  True               NaN           NaN    NaN
b3_fsd_s4  anthro                          0.476                         0.448               6           8           0.688     16                               0.020    True   False False               3.0           8.0  False
b3_fsd_s5 weather                          0.734                         0.181               8           8           0.917     24                               0.069    True    True  True               NaN           NaN    NaN
b3_fsd_s5  anthro                          0.470                         0.436               4           8           0.500     16                               0.009   False   False False               1.0           8.0  False
cm_fsd_s4 weather                          0.745                         0.158               8           8           1.000     24                               0.062    True    True  True               NaN           NaN    NaN
cm_fsd_s4  anthro                          0.369                         0.333               6           8           0.688     16                               0.008    True   False False               5.0           8.0  False
cm_fsd_s5 weather                          0.735                         0.165               8           8           1.000     24                               0.054    True    True  True               NaN           NaN    NaN
cm_fsd_s5  anthro                          0.400                         0.352               5           8           0.500     16                               0.004   False   False False               4.0           8.0  False

## Per noise type: share of SNR cells won by feats_only (descriptive)

           noise_type  cells  won  mean_d_rho  share_won       tag    fold
            hurricane      8    8       0.312      1.000 b1_fsd_s4 weather
            lightning      8    8       0.384      1.000 b1_fsd_s4 weather
             rainfall      8    5       0.411      0.625 b1_fsd_s4 weather
       bubble_curtain      8    7       0.070      0.875 b1_fsd_s4  anthro
large_commercial_ship      8    8       0.258      1.000 b1_fsd_s4  anthro
            hurricane      8    8       0.332      1.000 b1_fsd_s5 weather
            lightning      8    8       0.447      1.000 b1_fsd_s5 weather
             rainfall      8    7       0.423      0.875 b1_fsd_s5 weather
       bubble_curtain      8    6       0.095      0.750 b1_fsd_s5  anthro
large_commercial_ship      8    5       0.266      0.625 b1_fsd_s5  anthro
            hurricane      8    8       0.458      1.000 b3_fsd_s4 weather
            lightning      8    8       0.438      1.000 b3_fsd_s4 weather
             rainfall      8    8       0.504      1.000 b3_fsd_s4 weather
       bubble_curtain      8    3      -0.007      0.375 b3_fsd_s4  anthro
large_commercial_ship      8    8       0.250      1.000 b3_fsd_s4  anthro
            hurricane      8    8       0.372      1.000 b3_fsd_s5 weather
            lightning      8    8       0.398      1.000 b3_fsd_s5 weather
             rainfall      8    6       0.373      0.750 b3_fsd_s5 weather
       bubble_curtain      8    1      -0.094      0.125 b3_fsd_s5  anthro
large_commercial_ship      8    7       0.115      0.875 b3_fsd_s5  anthro
            hurricane      8    8       0.250      1.000 cm_fsd_s4 weather
            lightning      8    8       0.422      1.000 cm_fsd_s4 weather
             rainfall      8    8       0.504      1.000 cm_fsd_s4 weather
       bubble_curtain      8    5       0.032      0.625 cm_fsd_s4  anthro
large_commercial_ship      8    6       0.145      0.750 cm_fsd_s4  anthro
            hurricane      8    8       0.219      1.000 cm_fsd_s5 weather
            lightning      8    8       0.466      1.000 cm_fsd_s5 weather
             rainfall      8    8       0.436      1.000 cm_fsd_s5 weather
       bubble_curtain      8    4       0.038      0.500 cm_fsd_s5  anthro
large_commercial_ship      8    4       0.130      0.500 cm_fsd_s5  anthro
