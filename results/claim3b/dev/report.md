# Claim 3b: burst features (configs/gate_claim3b.yaml)

## DEV run (descriptive; these models' Claim 3 result was seen; cannot change the verdict)

- b1_fsd: pass
- b1_fsd_s2: pass
- b1_fsd_s3: pass
- b3_fsd: no pass
- b3_fsd_s2: no pass
- b3_fsd_s3: no pass
- cm_fsd: no pass
- cm_fsd_s2: pass
- cm_fsd_s3: no pass
- dfn3: no pass

## Per model and fold (rules a, b; rule c in the anthro fold)

      tag    fold  mean_within_snr_rho_featsonly  mean_within_snr_rho_baseline  snr_strata_won  snr_strata  cells_won_frac  cells  auc_top10_featsonly_minus_baseline  rule_a  rule_b  pass  bubble_cells_won  bubble_cells rule_c
   b1_fsd weather                          0.745                         0.212               8           8           0.875     24                               0.038    True    True  True               NaN           NaN    NaN
   b1_fsd  anthro                          0.546                         0.361               8           8           0.875     16                               0.007    True    True  True               6.0           8.0   True
b1_fsd_s2 weather                          0.700                         0.214               8           8           0.792     24                               0.046    True    True  True               NaN           NaN    NaN
b1_fsd_s2  anthro                          0.490                         0.359               8           8           0.875     16                               0.007    True    True  True               6.0           8.0   True
b1_fsd_s3 weather                          0.749                         0.205               8           8           0.958     24                               0.045    True    True  True               NaN           NaN    NaN
b1_fsd_s3  anthro                          0.488                         0.364               7           8           0.812     16                               0.006    True    True  True               6.0           8.0   True
   b3_fsd weather                          0.750                         0.156               8           8           1.000     24                               0.072    True    True  True               NaN           NaN    NaN
   b3_fsd  anthro                          0.472                         0.502               5           8           0.562     16                               0.019   False   False False               3.0           8.0  False
b3_fsd_s2 weather                          0.766                         0.173               8           8           0.917     24                               0.084    True    True  True               NaN           NaN    NaN
b3_fsd_s2  anthro                          0.465                         0.393               7           8           0.688     16                               0.026    True   False False               4.0           8.0  False
b3_fsd_s3 weather                          0.744                         0.176               8           8           1.000     24                               0.062    True    True  True               NaN           NaN    NaN
b3_fsd_s3  anthro                          0.393                         0.448               2           8           0.312     16                               0.003   False   False False               1.0           8.0  False
   cm_fsd weather                          0.733                         0.191               8           8           0.958     24                               0.057    True    True  True               NaN           NaN    NaN
   cm_fsd  anthro                          0.480                         0.373               6           8           0.625     16                               0.004    True   False False               2.0           8.0  False
cm_fsd_s2 weather                          0.749                         0.180               8           8           0.958     24                               0.060    True    True  True               NaN           NaN    NaN
cm_fsd_s2  anthro                          0.426                         0.350               7           8           0.812     16                               0.008    True    True  True               6.0           8.0   True
cm_fsd_s3 weather                          0.715                         0.195               8           8           0.917     24                               0.069    True    True  True               NaN           NaN    NaN
cm_fsd_s3  anthro                          0.488                         0.385               7           8           0.625     16                               0.014    True   False False               4.0           8.0  False
     dfn3 weather                          0.775                         0.289               8           8           0.708     24                               0.043    True   False False               NaN           NaN    NaN
     dfn3  anthro                          0.563                         0.448               7           8           0.688     16                               0.001    True   False False               5.0           8.0  False

## Per noise type: share of SNR cells won by feats_only (descriptive)

           noise_type  cells  won  mean_d_rho  share_won       tag    fold
            hurricane      8    7       0.268      0.875    b1_fsd weather
            lightning      8    7       0.350      0.875    b1_fsd weather
             rainfall      8    7       0.402      0.875    b1_fsd weather
       bubble_curtain      8    6       0.160      0.750    b1_fsd  anthro
large_commercial_ship      8    8       0.276      1.000    b1_fsd  anthro
            hurricane      8    8       0.361      1.000 b1_fsd_s2 weather
            lightning      8    6       0.260      0.750 b1_fsd_s2 weather
             rainfall      8    5       0.256      0.625 b1_fsd_s2 weather
       bubble_curtain      8    6       0.106      0.750 b1_fsd_s2  anthro
large_commercial_ship      8    8       0.257      1.000 b1_fsd_s2  anthro
            hurricane      8    8       0.337      1.000 b1_fsd_s3 weather
            lightning      8    8       0.448      1.000 b1_fsd_s3 weather
             rainfall      8    7       0.381      0.875 b1_fsd_s3 weather
       bubble_curtain      8    6       0.018      0.750 b1_fsd_s3  anthro
large_commercial_ship      8    7       0.147      0.875 b1_fsd_s3  anthro
            hurricane      8    8       0.362      1.000    b3_fsd weather
            lightning      8    8       0.459      1.000    b3_fsd weather
             rainfall      8    8       0.436      1.000    b3_fsd weather
       bubble_curtain      8    3      -0.102      0.375    b3_fsd  anthro
large_commercial_ship      8    6       0.137      0.750    b3_fsd  anthro
            hurricane      8    8       0.446      1.000 b3_fsd_s2 weather
            lightning      8    7       0.389      0.875 b3_fsd_s2 weather
             rainfall      8    7       0.344      0.875 b3_fsd_s2 weather
       bubble_curtain      8    4      -0.022      0.500 b3_fsd_s2  anthro
large_commercial_ship      8    7       0.227      0.875 b3_fsd_s2  anthro
            hurricane      8    8       0.317      1.000 b3_fsd_s3 weather
            lightning      8    8       0.482      1.000 b3_fsd_s3 weather
             rainfall      8    8       0.454      1.000 b3_fsd_s3 weather
       bubble_curtain      8    1      -0.107      0.125 b3_fsd_s3  anthro
large_commercial_ship      8    4       0.039      0.500 b3_fsd_s3  anthro
            hurricane      8    8       0.305      1.000    cm_fsd weather
            lightning      8    8       0.395      1.000    cm_fsd weather
             rainfall      8    7       0.376      0.875    cm_fsd weather
       bubble_curtain      8    2      -0.012      0.250    cm_fsd  anthro
large_commercial_ship      8    8       0.139      1.000    cm_fsd  anthro
            hurricane      8    8       0.326      1.000 cm_fsd_s2 weather
            lightning      8    8       0.476      1.000 cm_fsd_s2 weather
             rainfall      8    7       0.389      0.875 cm_fsd_s2 weather
       bubble_curtain      8    6       0.001      0.750 cm_fsd_s2  anthro
large_commercial_ship      8    7       0.146      0.875 cm_fsd_s2  anthro
            hurricane      8    7       0.202      0.875 cm_fsd_s3 weather
            lightning      8    8       0.451      1.000 cm_fsd_s3 weather
             rainfall      8    7       0.400      0.875 cm_fsd_s3 weather
       bubble_curtain      8    4       0.008      0.500 cm_fsd_s3  anthro
large_commercial_ship      8    6       0.120      0.750 cm_fsd_s3  anthro
            hurricane      8    5       0.111      0.625      dfn3 weather
            lightning      8    7       0.222      0.875      dfn3 weather
             rainfall      8    5       0.256      0.625      dfn3 weather
       bubble_curtain      8    5       0.067      0.625      dfn3  anthro
large_commercial_ship      8    6       0.316      0.750      dfn3  anthro
