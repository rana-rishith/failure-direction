# Claim 3 on active models (configs/gate_claim3_active.yaml)

## Verdict: FAILS

- FSD architectures passing (both folds): 1/3 (b1_fsd)
- DFN3: no pass; completeness ok (worst (fold, split) missing 0.00%)

## Per model and fold (level target, pre-committed rules a and b)

      tag    fold  mean_within_snr_rho_featsonly  mean_within_snr_rho_baseline  snr_strata_won  snr_strata  cells_won_frac  cells  auc_top10_featsonly_minus_baseline  rule_a  rule_b  pass
   b1_fsd weather                          0.730                         0.212               8           8           0.917     24                               0.038    True    True  True
   b1_fsd  anthro                          0.560                         0.361               8           8           0.875     16                               0.008    True    True  True
   b3_fsd weather                          0.739                         0.156               8           8           1.000     24                               0.072    True    True  True
   b3_fsd  anthro                          0.458                         0.502               5           8           0.500     16                               0.017   False   False False
   cm_fsd weather                          0.723                         0.191               8           8           1.000     24                               0.059    True    True  True
   cm_fsd  anthro                          0.492                         0.373               6           8           0.688     16                               0.004    True   False False
     dfn3 weather                          0.764                         0.289               8           8           0.708     24                               0.043    True   False False
     dfn3  anthro                          0.562                         0.448               8           8           0.688     16                               0.001    True   False False
b1_fsd_s2 weather                          0.681                         0.214               8           8           0.875     24                               0.047    True    True  True
b1_fsd_s2  anthro                          0.478                         0.359               7           8           0.688     16                               0.005    True   False False
b1_fsd_s3 weather                          0.728                         0.205               8           8           0.917     24                               0.046    True    True  True
b1_fsd_s3  anthro                          0.488                         0.364               7           8           0.750     16                               0.008    True    True  True
b3_fsd_s2 weather                          0.763                         0.173               8           8           0.958     24                               0.085    True    True  True
b3_fsd_s2  anthro                          0.463                         0.393               7           8           0.562     16                               0.026    True   False False
b3_fsd_s3 weather                          0.736                         0.176               8           8           0.958     24                               0.065    True    True  True
b3_fsd_s3  anthro                          0.326                         0.448               1           8           0.125     16                              -0.001   False   False False
cm_fsd_s2 weather                          0.729                         0.180               8           8           0.958     24                               0.062    True    True  True
cm_fsd_s2  anthro                          0.426                         0.350               6           8           0.750     16                               0.009    True    True  True
cm_fsd_s3 weather                          0.688                         0.195               8           8           0.833     24                               0.068    True    True  True
cm_fsd_s3  anthro                          0.481                         0.385               7           8           0.562     16                               0.014    True   False False

## Seeds (descriptive, cannot change the verdict)

- b1_fsd: 2/3 seeds pass
- b3_fsd: 0/3 seeds pass
- cm_fsd: 1/3 seeds pass

## Per noise type: share of SNR cells won by feats_only (descriptive)

           noise_type  cells  won  mean_d_rho  share_won       tag    fold
            hurricane      8    8       0.208      1.000    b1_fsd weather
            lightning      8    6       0.300      0.750    b1_fsd weather
             rainfall      8    8       0.423      1.000    b1_fsd weather
       bubble_curtain      8    6       0.164      0.750    b1_fsd  anthro
large_commercial_ship      8    8       0.276      1.000    b1_fsd  anthro
            hurricane      8    8       0.270      1.000    b3_fsd weather
            lightning      8    8       0.428      1.000    b3_fsd weather
             rainfall      8    8       0.453      1.000    b3_fsd weather
       bubble_curtain      8    4      -0.090      0.500    b3_fsd  anthro
large_commercial_ship      8    4       0.103      0.500    b3_fsd  anthro
            hurricane      8    8       0.241      1.000    cm_fsd weather
            lightning      8    8       0.370      1.000    cm_fsd weather
             rainfall      8    8       0.438      1.000    cm_fsd weather
       bubble_curtain      8    4      -0.011      0.500    cm_fsd  anthro
large_commercial_ship      8    7       0.154      0.875    cm_fsd  anthro
            hurricane      8    5       0.074      0.625      dfn3 weather
            lightning      8    7       0.220      0.875      dfn3 weather
             rainfall      8    5       0.230      0.625      dfn3 weather
       bubble_curtain      8    4       0.048      0.500      dfn3  anthro
large_commercial_ship      8    7       0.300      0.875      dfn3  anthro
            hurricane      8    8       0.302      1.000 b1_fsd_s2 weather
            lightning      8    6       0.222      0.750 b1_fsd_s2 weather
             rainfall      8    7       0.292      0.875 b1_fsd_s2 weather
       bubble_curtain      8    4       0.048      0.500 b1_fsd_s2  anthro
large_commercial_ship      8    7       0.237      0.875 b1_fsd_s2  anthro
            hurricane      8    7       0.265      0.875 b1_fsd_s3 weather
            lightning      8    8       0.387      1.000 b1_fsd_s3 weather
             rainfall      8    7       0.411      0.875 b1_fsd_s3 weather
       bubble_curtain      8    5      -0.013      0.625 b1_fsd_s3  anthro
large_commercial_ship      8    7       0.164      0.875 b1_fsd_s3  anthro
            hurricane      8    8       0.423      1.000 b3_fsd_s2 weather
            lightning      8    8       0.400      1.000 b3_fsd_s2 weather
             rainfall      8    7       0.324      0.875 b3_fsd_s2 weather
       bubble_curtain      8    3      -0.042      0.375 b3_fsd_s2  anthro
large_commercial_ship      8    6       0.220      0.750 b3_fsd_s2  anthro
            hurricane      8    7       0.264      0.875 b3_fsd_s3 weather
            lightning      8    8       0.446      1.000 b3_fsd_s3 weather
             rainfall      8    8       0.458      1.000 b3_fsd_s3 weather
       bubble_curtain      8    0      -0.182      0.000 b3_fsd_s3  anthro
large_commercial_ship      8    2      -0.040      0.250 b3_fsd_s3  anthro
            hurricane      8    8       0.276      1.000 cm_fsd_s2 weather
            lightning      8    8       0.438      1.000 cm_fsd_s2 weather
             rainfall      8    7       0.400      0.875 cm_fsd_s2 weather
       bubble_curtain      8    4      -0.074      0.500 cm_fsd_s2  anthro
large_commercial_ship      8    8       0.178      1.000 cm_fsd_s2  anthro
            hurricane      8    6       0.138      0.750 cm_fsd_s3 weather
            lightning      8    8       0.383      1.000 cm_fsd_s3 weather
             rainfall      8    6       0.420      0.750 cm_fsd_s3 weather
       bubble_curtain      8    3      -0.048      0.375 cm_fsd_s3  anthro
large_commercial_ship      8    6       0.130      0.750 cm_fsd_s3  anthro

## Cross-model agreement of the target, test_matched (descriptive)

   fold                  a         b  cells  median_cell_spearman
weather b1_weather(marven)    b1_fsd     24                 0.565
weather b1_weather(marven)    b3_fsd     24                 0.336
weather b1_weather(marven)    cm_fsd     24                 0.466
weather b1_weather(marven)      dfn3     24                 0.436
weather b1_weather(marven) b1_fsd_s2     24                 0.587
weather b1_weather(marven) b1_fsd_s3     24                 0.496
weather b1_weather(marven) b3_fsd_s2     24                 0.384
weather b1_weather(marven) b3_fsd_s3     24                 0.339
weather b1_weather(marven) cm_fsd_s2     24                 0.433
weather b1_weather(marven) cm_fsd_s3     24                 0.410
weather             b1_fsd    b3_fsd     24                 0.649
weather             b1_fsd    cm_fsd     24                 0.870
weather             b1_fsd      dfn3     24                 0.623
weather             b1_fsd b1_fsd_s2     24                 0.842
weather             b1_fsd b1_fsd_s3     24                 0.794
weather             b1_fsd b3_fsd_s2     24                 0.737
weather             b1_fsd b3_fsd_s3     24                 0.590
weather             b1_fsd cm_fsd_s2     24                 0.818
weather             b1_fsd cm_fsd_s3     24                 0.795
weather             b3_fsd    cm_fsd     24                 0.684
weather             b3_fsd      dfn3     24                 0.485
weather             b3_fsd b1_fsd_s2     24                 0.630
weather             b3_fsd b1_fsd_s3     24                 0.732
weather             b3_fsd b3_fsd_s2     24                 0.770
weather             b3_fsd b3_fsd_s3     24                 0.855
weather             b3_fsd cm_fsd_s2     24                 0.722
weather             b3_fsd cm_fsd_s3     24                 0.722
weather             cm_fsd      dfn3     24                 0.574
weather             cm_fsd b1_fsd_s2     24                 0.800
weather             cm_fsd b1_fsd_s3     24                 0.807
weather             cm_fsd b3_fsd_s2     24                 0.765
weather             cm_fsd b3_fsd_s3     24                 0.648
weather             cm_fsd cm_fsd_s2     24                 0.858
weather             cm_fsd cm_fsd_s3     24                 0.826
weather               dfn3 b1_fsd_s2     24                 0.529
weather               dfn3 b1_fsd_s3     24                 0.563
weather               dfn3 b3_fsd_s2     24                 0.513
weather               dfn3 b3_fsd_s3     24                 0.413
weather               dfn3 cm_fsd_s2     24                 0.552
weather               dfn3 cm_fsd_s3     24                 0.573
weather          b1_fsd_s2 b1_fsd_s3     24                 0.782
weather          b1_fsd_s2 b3_fsd_s2     24                 0.764
weather          b1_fsd_s2 b3_fsd_s3     24                 0.555
weather          b1_fsd_s2 cm_fsd_s2     24                 0.806
weather          b1_fsd_s2 cm_fsd_s3     24                 0.814
weather          b1_fsd_s3 b3_fsd_s2     24                 0.722
weather          b1_fsd_s3 b3_fsd_s3     24                 0.710
weather          b1_fsd_s3 cm_fsd_s2     24                 0.855
weather          b1_fsd_s3 cm_fsd_s3     24                 0.840
weather          b3_fsd_s2 b3_fsd_s3     24                 0.731
weather          b3_fsd_s2 cm_fsd_s2     24                 0.763
weather          b3_fsd_s2 cm_fsd_s3     24                 0.769
weather          b3_fsd_s3 cm_fsd_s2     24                 0.707
weather          b3_fsd_s3 cm_fsd_s3     24                 0.736
weather          cm_fsd_s2 cm_fsd_s3     24                 0.857
 anthro  b1_anthro(marven)    b1_fsd     16                 0.564
 anthro  b1_anthro(marven)    b3_fsd     16                 0.232
 anthro  b1_anthro(marven)    cm_fsd     16                 0.381
 anthro  b1_anthro(marven)      dfn3     16                 0.404
 anthro  b1_anthro(marven) b1_fsd_s2     16                 0.423
 anthro  b1_anthro(marven) b1_fsd_s3     16                 0.350
 anthro  b1_anthro(marven) b3_fsd_s2     16                 0.349
 anthro  b1_anthro(marven) b3_fsd_s3     16                 0.198
 anthro  b1_anthro(marven) cm_fsd_s2     16                 0.385
 anthro  b1_anthro(marven) cm_fsd_s3     16                 0.325
 anthro             b1_fsd    b3_fsd     16                 0.506
 anthro             b1_fsd    cm_fsd     16                 0.833
 anthro             b1_fsd      dfn3     16                 0.556
 anthro             b1_fsd b1_fsd_s2     16                 0.834
 anthro             b1_fsd b1_fsd_s3     16                 0.796
 anthro             b1_fsd b3_fsd_s2     16                 0.663
 anthro             b1_fsd b3_fsd_s3     16                 0.527
 anthro             b1_fsd cm_fsd_s2     16                 0.808
 anthro             b1_fsd cm_fsd_s3     16                 0.758
 anthro             b3_fsd    cm_fsd     16                 0.629
 anthro             b3_fsd      dfn3     16                 0.303
 anthro             b3_fsd b1_fsd_s2     16                 0.579
 anthro             b3_fsd b1_fsd_s3     16                 0.623
 anthro             b3_fsd b3_fsd_s2     16                 0.793
 anthro             b3_fsd b3_fsd_s3     16                 0.845
 anthro             b3_fsd cm_fsd_s2     16                 0.675
 anthro             b3_fsd cm_fsd_s3     16                 0.658
 anthro             cm_fsd      dfn3     16                 0.526
 anthro             cm_fsd b1_fsd_s2     16                 0.821
 anthro             cm_fsd b1_fsd_s3     16                 0.786
 anthro             cm_fsd b3_fsd_s2     16                 0.679
 anthro             cm_fsd b3_fsd_s3     16                 0.592
 anthro             cm_fsd cm_fsd_s2     16                 0.825
 anthro             cm_fsd cm_fsd_s3     16                 0.823
 anthro               dfn3 b1_fsd_s2     16                 0.548
 anthro               dfn3 b1_fsd_s3     16                 0.504
 anthro               dfn3 b3_fsd_s2     16                 0.471
 anthro               dfn3 b3_fsd_s3     16                 0.275
 anthro               dfn3 cm_fsd_s2     16                 0.556
 anthro               dfn3 cm_fsd_s3     16                 0.526
 anthro          b1_fsd_s2 b1_fsd_s3     16                 0.798
 anthro          b1_fsd_s2 b3_fsd_s2     16                 0.685
 anthro          b1_fsd_s2 b3_fsd_s3     16                 0.522
 anthro          b1_fsd_s2 cm_fsd_s2     16                 0.785
 anthro          b1_fsd_s2 cm_fsd_s3     16                 0.769
 anthro          b1_fsd_s3 b3_fsd_s2     16                 0.633
 anthro          b1_fsd_s3 b3_fsd_s3     16                 0.624
 anthro          b1_fsd_s3 cm_fsd_s2     16                 0.804
 anthro          b1_fsd_s3 cm_fsd_s3     16                 0.843
 anthro          b3_fsd_s2 b3_fsd_s3     16                 0.762
 anthro          b3_fsd_s2 cm_fsd_s2     16                 0.693
 anthro          b3_fsd_s2 cm_fsd_s3     16                 0.666
 anthro          b3_fsd_s3 cm_fsd_s2     16                 0.715
 anthro          b3_fsd_s3 cm_fsd_s3     16                 0.679
 anthro          cm_fsd_s2 cm_fsd_s3     16                 0.832
