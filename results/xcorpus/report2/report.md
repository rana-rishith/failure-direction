# Gate XN2 report

## Per-seed gate-D statistics (MarVEN, SNR <= 0, level-aligned)

family arch          tag    d_g  nr_g  d_plain  nr_plain                   cls
   fsd   b1       b1_fsd -0.109 0.962    0.708     0.996               partial
   fsd   b1    b1_fsd_s2 -0.141 0.961    0.718     0.996               partial
   fsd   b1    b1_fsd_s3 -0.180 0.957    0.668     0.996               partial
   fsd   b3       b3_fsd -0.481 0.921    0.507     0.988               partial
   fsd   b3    b3_fsd_s2 -0.510 0.912    0.405     0.985               partial
   fsd   b3    b3_fsd_s3 -0.435 0.920    0.583     0.992               partial
   fsd   cm       cm_fsd -0.210 0.955   -0.970     0.469               partial
   fsd   cm    cm_fsd_s2 -0.214 0.951   -0.954     0.650               partial
   fsd   cm    cm_fsd_s3 -0.274 0.951   -0.971     0.450               partial
demand   b1    b1_demand -0.973 0.154   -0.894     0.585 architecture_explains
demand   b1 b1_demand_s2 -0.979 0.104   -0.910     0.628 architecture_explains
demand   b1 b1_demand_s3 -0.974 0.186   -0.884     0.611 architecture_explains
demand   b3    b3_demand -0.985 0.040   -0.966     0.297 architecture_explains
demand   b3 b3_demand_s2 -0.986 0.052   -0.973     0.200 architecture_explains
demand   b3 b3_demand_s3 -0.987 0.045   -0.976     0.196 architecture_explains
demand   cm    cm_demand -0.980 0.061   -0.999    -2.940 architecture_explains
demand   cm cm_demand_s2 -0.985 0.065   -0.999    -2.793 architecture_explains
demand   cm cm_demand_s3 -0.982 0.163   -0.999    -2.320 architecture_explains

## D_fsd: partial

        d_g   nr_g  n_seeds    class
arch                                
b1   -0.141  0.961        3  partial
b3   -0.481  0.920        3  partial
cm   -0.214  0.951        3  partial

## H_D2 demand seeds

                                                                classes  n verdict
arch                                                                              
b1    architecture_explains,architecture_explains,architecture_explains  3  stable
b3    architecture_explains,architecture_explains,architecture_explains  3  stable
cm    architecture_explains,architecture_explains,architecture_explains  3  stable

## H_FD_widening: widens

arch  nr_g_fsd  nr_g_demand  delta    cls
  b1     0.960        0.148  0.812 widens
  b3     0.918        0.045  0.872 widens
  cm     0.952        0.096  0.856 widens

## H_F_family_fresh: not_family_specific (E >= 0.10 in 0 of 9)

arch   seed  bonus_weather  bonus_eval      E  E_boat
  b1 _s1234          0.039       0.015  0.025   0.034
  b1    _s2          0.015       0.008  0.007   0.016
  b1    _s3          0.025       0.009  0.015   0.014
  b3 _s1234         -0.018       0.029 -0.048   0.161
  b3    _s2          0.019       0.004  0.015   0.043
  b3    _s3          0.025       0.008  0.017   0.047
  cm _s1234         -0.017       0.006 -0.023   0.084
  cm    _s2         -0.005       0.001 -0.007   0.072
  cm    _s3          0.021       0.020  0.001   0.078

## C1_lowcut: sub100_dependent

       tag  gap_full  gap_lc  gap_hp100  ratio    ok
 b1_anthro    11.064  11.243     10.572  0.956  True
b1_weather    10.338   9.200      7.446  0.720 False
 b3_anthro     9.645   9.718      9.020  0.935  True
b3_weather     8.976   7.817      6.085  0.678 False
 cm_anthro    10.845  10.919     10.177  0.938  True
cm_weather    10.490   9.228      7.480  0.713 False

## H_P_final: dfn3

model  paired_base_rows  H_P1_delta        H_P1  H_P2_delta        H_P2  hp100_gain_desc_delta  gain_desc_delta
 dfn3               400      -0.088 model_trait       0.005 model_trait                  2.374           -4.301

                nr_g    d_g      g  sisdr_gain  gain_hp100
cond                                                      
deepship_ship  0.914  0.245  0.876       5.931       5.066
deepship_tug   0.849  0.324  0.889       3.089       4.030
dem_A          0.893  0.317  0.910       8.506       3.170
dem_B          0.894  0.344  0.916       8.940       3.105
dem_H          0.920  0.378  0.943      11.279       2.373
fsd_boat       0.937  0.249  0.881       7.607       6.620
fsd_eval       0.954  0.259  0.891       8.434       8.677
fsd_weather    0.940  0.245  0.884       8.135       7.546
marven         0.939  0.190  0.904       7.696       6.521
mbari_dry      0.891  0.287  0.908       4.858       4.167
mbari_storm    0.900  0.272  0.880       5.304       5.138
vbdmd_test     0.894  0.299  0.947       8.911       2.085

## H_P_final: sgmse

model  paired_base_rows  H_P1_delta                H_P1  H_P2_delta        H_P2  hp100_gain_desc_delta  gain_desc_delta
sgmse                40      -0.233 shifts_with_novelty      -0.032 model_trait                  1.067           -1.794

                nr_g    d_g      g  sisdr_gain  gain_hp100
cond                                                      
deepship_ship  0.867 -0.052  0.926       4.981       3.544
dem_A          0.915  0.341  0.957       8.235       3.542
dem_H          0.910  0.298  0.951       9.878       2.443
marven         0.928  0.168  0.954       6.792       5.427
mbari_dry      0.843  0.182  0.936       8.348       3.272
mbari_storm    0.876  0.096  0.929       6.949       4.689
vbdmd_test     0.914  0.478  0.989       1.380       3.542

## Matrix (seed mean): nr_g

cond               deepship_ship  deepship_tug  dem_A  dem_B  dem_H  fsd_boat  fsd_eval  fsd_weather  marven  marven_heard  marven_unseen  mbari_dry  mbari_storm  vbdmd_test
group                                                                                                                                                                        
b1_anthro                  0.412         0.170  0.144  0.136  0.055     0.175     0.028        0.149     NaN         0.983          0.069      0.255        0.149       0.129
b1_demand                  0.869         0.814  0.912  0.901  0.908     0.707     0.377        0.659   0.400           NaN            NaN      0.880        0.850       0.888
b1_fsd                     0.850         0.770  0.862  0.849  0.882     0.886     0.918        0.896   0.884           NaN            NaN      0.836        0.840       0.870
b1_loto_hurricane          0.200         0.473  0.049  0.043  0.012     0.088     0.021        0.117   0.312           NaN            NaN      0.258        0.325       0.064
b1_loto_lightning          0.153         0.428  0.292  0.342  0.810     0.095     0.026        0.076   0.053           NaN            NaN      0.330        0.333       0.611
b1_loto_rainfall           0.216         0.427  0.317  0.357  0.779     0.162     0.023        0.133   0.435           NaN            NaN      0.328        0.294       0.519
b1_weather                 0.230         0.502  0.312  0.330  0.807     0.164     0.038        0.175     NaN         0.974          0.013      0.316        0.343       0.568
b3_anthro                  0.498         0.166  0.214  0.204  0.136     0.229     0.042        0.155     NaN         0.970          0.083      0.295        0.165       0.219
b3_demand                  0.804         0.739  0.865  0.861  0.878     0.470     0.246        0.436   0.143           NaN            NaN      0.825        0.788       0.854
b3_fsd                     0.707         0.626  0.735  0.742  0.748     0.748     0.826        0.797   0.750           NaN            NaN      0.727        0.719       0.741
b3_loto_hurricane          0.245         0.513  0.060  0.056  0.026     0.107     0.051        0.133   0.273           NaN            NaN      0.300        0.337       0.084
b3_loto_lightning          0.159         0.377  0.259  0.293  0.841     0.087     0.022        0.070   0.037           NaN            NaN      0.327        0.310       0.646
b3_loto_rainfall           0.246         0.464  0.309  0.306  0.763     0.155     0.042        0.145   0.466           NaN            NaN      0.313        0.283       0.534
b3_seg_anthro              0.481         0.192  0.206  0.202  0.111     0.239     0.040        0.154     NaN         0.922          0.074      0.269        0.155       0.202
b3_seg_weather             0.265         0.472  0.310  0.327  0.806     0.147     0.033        0.137     NaN         0.924          0.012      0.344        0.317       0.598
b3_weather                 0.234         0.492  0.302  0.303  0.754     0.158     0.055        0.163     NaN         0.955          0.042      0.318        0.319       0.585
cm_anthro                  0.490         0.201  0.154  0.151  0.048     0.242     0.037        0.182     NaN         0.977          0.066      0.281        0.174       0.147
cm_demand                  0.837         0.784  0.893  0.883  0.882     0.627     0.310        0.588   0.329           NaN            NaN      0.856        0.810       0.876
cm_fsd                     0.818         0.739  0.826  0.828  0.837     0.861     0.905        0.872   0.863           NaN            NaN      0.813        0.818       0.850
cm_weather                 0.216         0.478  0.275  0.254  0.644     0.173     0.046        0.181     NaN         0.971          0.019      0.285        0.320       0.482

## Matrix (seed mean): d_g

cond               deepship_ship  deepship_tug  dem_A  dem_B  dem_H  fsd_boat  fsd_eval  fsd_weather  marven  marven_heard  marven_unseen  mbari_dry  mbari_storm  vbdmd_test
group                                                                                                                                                                        
b1_anthro                 -0.822        -0.791 -0.916 -0.926 -0.915    -0.935    -0.975       -0.950     NaN         0.428         -0.964     -0.825       -0.898      -0.849
b1_demand                 -0.018         0.085  0.079  0.072  0.198    -0.511    -0.884       -0.648  -0.785           NaN            NaN      0.163        0.040       0.110
b1_fsd                    -0.080        -0.034  0.002  0.006  0.254    -0.065    -0.062       -0.092  -0.016           NaN            NaN      0.019       -0.076       0.086
b1_loto_hurricane         -0.872        -0.617 -0.922 -0.932 -0.929    -0.937    -0.977       -0.948  -0.832           NaN            NaN     -0.792       -0.831      -0.874
b1_loto_lightning         -0.893        -0.638 -0.841 -0.846 -0.578    -0.941    -0.979       -0.965  -0.814           NaN            NaN     -0.775       -0.825      -0.675
b1_loto_rainfall          -0.880        -0.634 -0.883 -0.865 -0.673    -0.930    -0.978       -0.951  -0.711           NaN            NaN     -0.814       -0.865      -0.713
b1_weather                -0.860        -0.568 -0.848 -0.834 -0.569    -0.921    -0.974       -0.941     NaN         0.259         -0.954     -0.775       -0.819      -0.669
b3_anthro                 -0.699        -0.729 -0.874 -0.880 -0.873    -0.906    -0.964       -0.933     NaN         0.323         -0.955     -0.730       -0.825      -0.786
b3_demand                 -0.165        -0.015 -0.072 -0.050  0.085    -0.763    -0.925       -0.832  -0.887           NaN            NaN      0.084       -0.106      -0.022
b3_fsd                    -0.271        -0.119 -0.147 -0.146  0.133    -0.332    -0.312       -0.304  -0.312           NaN            NaN     -0.113       -0.230      -0.197
b3_loto_hurricane         -0.841        -0.506 -0.898 -0.905 -0.916    -0.929    -0.970       -0.944  -0.813           NaN            NaN     -0.743       -0.792      -0.860
b3_loto_lightning         -0.888        -0.674 -0.842 -0.840 -0.507    -0.944    -0.976       -0.962  -0.818           NaN            NaN     -0.769       -0.814      -0.624
b3_loto_rainfall          -0.826        -0.497 -0.829 -0.830 -0.640    -0.901    -0.964       -0.934  -0.594           NaN            NaN     -0.733       -0.774      -0.688
b3_seg_anthro             -0.734        -0.737 -0.880 -0.887 -0.891    -0.910    -0.964       -0.935     NaN        -0.177         -0.953     -0.741       -0.829      -0.774
b3_seg_weather            -0.795        -0.403 -0.797 -0.763 -0.475    -0.918    -0.967       -0.938     NaN         0.079         -0.957     -0.664       -0.719      -0.621
b3_weather                -0.818        -0.493 -0.822 -0.812 -0.569    -0.908    -0.966       -0.932     NaN         0.136         -0.953     -0.742       -0.778      -0.633
cm_anthro                 -0.767        -0.731 -0.900 -0.897 -0.906    -0.920    -0.971       -0.940     NaN         0.281         -0.957     -0.762       -0.851      -0.835
cm_demand                 -0.136         0.052 -0.022 -0.016  0.200    -0.655    -0.911       -0.747  -0.839           NaN            NaN      0.101       -0.066       0.059
cm_fsd                    -0.093         0.038 -0.027  0.006  0.226    -0.126    -0.120       -0.135  -0.063           NaN            NaN      0.062       -0.062       0.103
cm_weather                -0.849        -0.552 -0.871 -0.859 -0.687    -0.918    -0.974       -0.940     NaN         0.185         -0.953     -0.758       -0.786      -0.743

## Matrix (seed mean): sisdr_gain

cond               deepship_ship  deepship_tug   dem_A   dem_B   dem_H  fsd_boat  fsd_eval  fsd_weather  marven  marven_heard  marven_unseen  mbari_dry  mbari_storm  vbdmd_test
group                                                                                                                                                                           
b1_anthro                  0.912         0.839   0.140   0.105   0.042     0.497     0.067        0.390     NaN        11.166          0.257      0.301        0.185       0.271
b1_demand                  7.263         9.119  10.163  10.701  11.634     3.340     1.508        3.253   1.307           NaN            NaN     10.205        7.609       9.340
b1_fsd                     6.776         6.709   8.229   8.644   9.822     6.725     7.858        6.861   6.640           NaN            NaN      8.916        7.275       8.593
b1_loto_hurricane          0.352         0.270   0.002  -0.006  -0.018     0.130     0.045        0.310   1.333           NaN            NaN      0.108        0.381       0.035
b1_loto_lightning          0.233         0.107   1.452   2.368   8.163     0.318     0.087        0.319   0.202           NaN            NaN      0.314        0.370       6.266
b1_loto_rainfall           0.454         0.180   1.144   1.687   4.444     0.584     0.064        0.450   1.822           NaN            NaN      0.507        0.592       3.587
b1_weather                 0.350         0.127   0.837   1.382   7.672     0.558     0.129        0.607     NaN        10.589          0.339      0.192        0.330       5.147
b3_anthro                  1.494         2.414   0.510   0.369   0.404     0.677     0.091        0.487     NaN         9.924          0.238      0.872        0.546       0.725
b3_demand                  6.146         8.136   9.328   9.729  11.097     1.942     0.878        2.046   0.509           NaN            NaN      9.193        6.729       8.887
b3_fsd                     4.692         5.571   6.457   6.798   7.831     4.266     5.388        4.993   4.363           NaN            NaN      6.900        5.472       6.261
b3_loto_hurricane          0.281         0.142   0.005  -0.007  -0.023     0.173     0.117        0.317   1.099           NaN            NaN      0.067        0.285       0.065
b3_loto_lightning          0.499         0.608   2.030   2.396   9.801     0.344     0.050        0.301   0.215           NaN            NaN      0.702        0.601       7.088
b3_loto_rainfall           0.585         0.462   0.974   1.414   5.776     0.519     0.093        0.474   1.629           NaN            NaN      0.590        0.504       5.177
b3_seg_anthro              1.120         1.081   0.328   0.244   0.236     0.668     0.080        0.426     NaN         8.034          0.173      0.426        0.215       0.440
b3_seg_weather             0.470         0.846   1.209   1.270   7.554     0.491     0.041        0.366     NaN         7.597          0.237      0.455        0.380       6.025
b3_weather                 0.390         0.307   0.863   1.195   6.464     0.547     0.154        0.504     NaN         9.460          0.324      0.334        0.398       5.788
cm_anthro                  1.252         1.261   0.291   0.220   0.235     0.768     0.128        0.507     NaN        11.115          0.204      0.727        0.421       0.397
cm_demand                  6.743         8.593   9.599  10.213  10.905     2.762     1.266        2.945   1.061           NaN            NaN      9.627        6.969       9.254
cm_fsd                     6.198         6.673   7.708   8.401   9.413     5.971     7.126        6.339   6.043           NaN            NaN      7.862        6.438       8.415
cm_weather                 0.490         0.763   0.641   0.829   3.904     0.601     0.148        0.558     NaN        10.459          0.079      0.599        0.667       3.145

## Matrix (seed mean): gain_hp100

cond               deepship_ship  deepship_tug  dem_A  dem_B  dem_H  fsd_boat  fsd_eval  fsd_weather  marven  marven_heard  marven_unseen  mbari_dry  mbari_storm  vbdmd_test
group                                                                                                                                                                        
b1_anthro                  1.623         0.480  0.652  0.604  0.531     0.751     0.065        0.565     NaN        10.773          0.201      0.842        0.405       0.933
b1_demand                  4.542         4.059  4.065  3.686  2.820     2.786     1.608        2.867   1.434           NaN            NaN      4.145        4.383       3.242
b1_fsd                     4.275         3.613  3.075  2.841  2.373     5.439     7.342        6.075   5.194           NaN            NaN      3.597        4.435       2.682
b1_loto_hurricane            NaN           NaN    NaN    NaN    NaN     0.593     0.078        0.705     NaN           NaN            NaN        NaN          NaN         NaN
b1_loto_lightning            NaN           NaN    NaN    NaN    NaN     0.249     0.057        0.167     NaN           NaN            NaN        NaN          NaN         NaN
b1_loto_rainfall             NaN           NaN    NaN    NaN    NaN     0.526     0.068        0.510     NaN           NaN            NaN        NaN          NaN         NaN
b1_weather                 1.443         2.119  0.817  0.635  0.879     0.618     0.129        0.790     NaN         7.473          0.027      1.438        1.445       0.853
b3_anthro                  1.712         0.439  0.825  0.619  0.669     0.824     0.084        0.493     NaN         9.367          0.347      0.681        0.295       0.702
b3_demand                  3.510         3.270  3.013  2.779  2.029     1.551     0.944        1.534   0.433           NaN            NaN      3.403        3.555       2.527
b3_fsd                     2.443         2.217  1.698  1.583  0.758     3.201     4.914        4.157   3.008           NaN            NaN      2.317        2.894       1.449
b3_loto_hurricane            NaN           NaN    NaN    NaN    NaN     0.706     0.200        0.688     NaN           NaN            NaN        NaN          NaN         NaN
b3_loto_lightning            NaN           NaN    NaN    NaN    NaN     0.177     0.054        0.100     NaN           NaN            NaN        NaN          NaN         NaN
b3_loto_rainfall             NaN           NaN    NaN    NaN    NaN     0.590     0.137        0.490     NaN           NaN            NaN        NaN          NaN         NaN
b3_seg_anthro                NaN           NaN    NaN    NaN    NaN     0.879     0.087        0.520     NaN           NaN            NaN        NaN          NaN         NaN
b3_seg_weather               NaN           NaN    NaN    NaN    NaN     0.524     0.071        0.304     NaN           NaN            NaN        NaN          NaN         NaN
b3_weather                 1.429         1.628  0.779  0.555  0.860     0.555     0.178        0.573     NaN         6.542          0.457      1.147        0.954       0.958
cm_anthro                  1.911         0.559  0.809  0.748  0.537     0.924     0.086        0.651     NaN        10.503          0.327      0.838        0.394       0.955
cm_demand                  4.045         3.684  3.646  3.374  2.482     2.331     1.255        2.433   0.966           NaN            NaN      3.835        3.943       2.976
cm_fsd                     3.793         3.260  2.679  2.395  1.703     4.900     6.684        5.431   4.611           NaN            NaN      3.217        4.164       2.277
cm_weather                 1.678         2.035  0.901  0.654  0.857     0.642     0.146        0.758     NaN         7.514          0.034      1.568        1.412       0.908

## MarVEN per type, nr_g (demand and fsd models)

noise_type    bubble_curtain  hurricane  large_commercial_ship  lightning  rainfall
tag                                                                                
b1_demand             -0.001      0.993                  0.450      0.514     0.308
b1_demand_s2           0.015      0.996                  0.572      0.554     0.277
b1_demand_s3           0.001      0.991                  0.450      0.570     0.302
b1_fsd                 0.982      0.995                  0.863      0.877     0.811
b1_fsd_s2              0.983      0.995                  0.874      0.860     0.815
b1_fsd_s3              0.968      0.994                  0.835      0.866     0.832
b3_demand              0.003      0.989                  0.306      0.126     0.239
b3_demand_s2           0.010      0.994                  0.292      0.060     0.139
b3_demand_s3           0.007      0.992                  0.231      0.052     0.142
b3_fsd                 0.923      0.985                  0.648      0.686     0.664
b3_fsd_s2              0.859      0.988                  0.725      0.694     0.698
b3_fsd_s3              0.912      0.977                  0.560      0.678     0.731
cm_demand             -0.001      0.995                  0.499      0.513     0.161
cm_demand_s2          -0.008      0.994                  0.365      0.328     0.313
cm_demand_s3           0.009      0.994                  0.317      0.364     0.238
cm_fsd                 0.976      0.990                  0.839      0.858     0.781
cm_fsd_s2              0.975      0.989                  0.839      0.854     0.810
cm_fsd_s3              0.958      0.990                  0.810      0.854     0.818
