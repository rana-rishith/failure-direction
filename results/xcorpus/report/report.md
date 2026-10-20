# Overnight cross-corpus report (gate_overnight.yaml)

## H_S1 seed robustness (nr_g R1 - R4 on MarVEN)

     model  contrast_s1234  contrast_s2  contrast_s3  seed_sd verdict
 b1_anthro           0.934        0.889        0.919    0.019  robust
b1_weather           0.963        0.959        0.962    0.002  robust
 b3_anthro           0.886        0.883        0.892    0.004  robust
b3_weather           0.879        0.931        0.930    0.025  robust
 cm_anthro           0.902        0.909        0.921    0.008  robust
cm_weather           0.957        0.954        0.946    0.005  robust

## H_S2 R3 across seeds: intermediate (9 runs)

  run          tag  p_noise_removed  contrast        class
   r3    b1_anthro            0.406     0.909 intermediate
   r3    b3_anthro            0.491     0.858 intermediate
   r3    cm_anthro            0.462     0.873 intermediate
r3_s2 b1_anthro_s2            0.382     0.857 intermediate
r3_s2 b3_anthro_s2            0.429     0.850 intermediate
r3_s2 cm_anthro_s2            0.435     0.886 intermediate
r3_s3 b1_anthro_s3            0.377     0.893 intermediate
r3_s3 b3_anthro_s3            0.440     0.860 intermediate
r3_s3 cm_anthro_s3            0.436     0.889 intermediate

## Pretrained ladder: dfn3

model  paired_base_rows  vbdmd_n  H_P1_delta        H_P1  H_P2_delta        H_P2                                                  note
 dfn3               400      824      -0.088 model_trait       0.005 model_trait provisional: DFN3 training noise vs DEMAND unverified

                nr_g    d_g     nr      d      g  sisdr_gain
cond                                                        
deepship_ship  0.914  0.245  0.989  0.904  0.876       5.931
deepship_tug   0.849  0.324  0.980  0.919  0.889       3.089
dem_A          0.893  0.317  0.985  0.887  0.910       8.506
dem_B          0.894  0.344  0.983  0.883  0.916       8.940
dem_H          0.920  0.378  0.986  0.877  0.943      11.279
marven         0.939  0.190  0.989  0.794  0.904       7.696
mbari_dry      0.891  0.287  0.980  0.896  0.908       4.858
mbari_storm    0.900  0.272  0.982  0.893  0.880       5.304
vbdmd_test     0.894  0.299  0.980  0.884  0.947       8.911

## Pretrained ladder: sgmse

model  paired_base_rows  vbdmd_n  H_P1_delta         H_P1  H_P2_delta         H_P2
sgmse                20       20      -0.375 underpowered      -0.054 underpowered

                nr_g    d_g     nr      d      g  sisdr_gain
cond                                                        
deepship_ship  0.857 -0.106  0.978  0.650  0.906       6.474
dem_A          0.905  0.369  0.976  0.750  0.951       8.943
dem_H          0.945  0.306  0.979  0.734  0.947      11.572
marven         0.964  0.286  0.982  0.531  0.959       7.316
mbari_dry      0.857  0.041  0.972  0.731  0.923       9.089
mbari_storm    0.876 -0.073  0.973  0.774  0.906       6.949
vbdmd_test     0.914  0.444  0.951  0.607  0.992       1.530
