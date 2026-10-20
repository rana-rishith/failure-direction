# Stage 5 overnight diagnostics

## 1. R3 (anthro models on DeepShip ship), per-row nr_g, 3 seeds pooled

band   <0.2  0.2-0.5  0.5-0.8   >0.8  sarle_bc  median
arch                                                  
b1    0.203    0.445    0.332  0.020     0.362   0.420
b3    0.181    0.358    0.392  0.070     0.629   0.476
cm    0.172    0.381    0.401  0.045     0.515   0.466

Histogram, 12 bins from -0.2 to 1.0:

  b1    40   35   75  118  148  192  249  204  131  104   27    0
  b3   102   20   33   85  116  164  193  170  221  127   84    8
  cm    70   22   59   77  135  161  208  189  213  129   57    3

### by SNR (median [q25, q75])

     median                  q25                  q75              
arch     b1     b3     cm     b1     b3     cm     b1     b3     cm
snr                                                                
-15   0.227  0.230  0.273 -0.018 -0.266 -0.056  0.408  0.472  0.473
-10   0.333  0.248  0.335  0.083 -0.177  0.068  0.478  0.551  0.564
-5    0.421  0.497  0.502  0.243  0.259  0.282  0.587  0.683  0.666
 0    0.445  0.553  0.528  0.298  0.371  0.383  0.571  0.660  0.643
 5    0.456  0.542  0.514  0.331  0.367  0.374  0.598  0.665  0.646
 10   0.469  0.557  0.523  0.328  0.366  0.391  0.615  0.705  0.679
 15   0.426  0.478  0.469  0.314  0.361  0.322  0.548  0.600  0.611
 20   0.436  0.462  0.429  0.237  0.335  0.270  0.588  0.618  0.609

### by DeepShip class (resid = median nr_g minus the SNR-cell median)

                      n   nr_g  resid    d_g   gain
cls           arch                                 
Cargo         b1    291  0.439  0.008 -0.813  0.664
              b3    291  0.502  0.005 -0.690  1.260
              cm    291  0.483 -0.002 -0.768  1.077
Passengership b1    438  0.380 -0.032 -0.821  1.067
              b3    438  0.423 -0.052 -0.671  1.694
              cm    438  0.428 -0.047 -0.741  1.374
Tanker        b1    594  0.439  0.021 -0.778  1.021
              b3    594  0.512  0.034 -0.646  1.437
              cm    594  0.497  0.026 -0.721  1.273

### source-recording effect (after removing SNR-cell median)

      n_files  var_resid  share_between_files  file_resid_min  file_resid_max
arch                                                                         
b1         60     0.0574                0.520          -0.385           0.363
b3         60     0.3077                0.226          -0.424           0.401
cm         60     0.1302                0.330          -0.399           0.368

Spearman across files of per-file residual (do architectures agree on which recordings transfer?):

arch     b1     b3     cm
arch                     
b1    1.000  0.960  0.969
b3    0.960  1.000  0.981
cm    0.969  0.981  1.000

## 2. Full xcorpus matrix, nr_g (median per checkpoint, mean over seeds; seg models excluded)

cond2                marven_anthro  marven_weather  deepship_ship  deepship_tug  mbari_dry  mbari_storm  dem_A  dem_B  dem_H  vbdmd_test
arch fam                                                                                                                                
b1   anthro                  0.983           0.069          0.412         0.170      0.255        0.149  0.144  0.136  0.055       0.129
     demand                  0.027           0.522          0.867         0.800      0.876        0.845  0.908  0.901  0.898       0.882
     loto_hurricane          0.024           0.937          0.200         0.473      0.258        0.325  0.049  0.043  0.012       0.064
     loto_lightning          0.007           0.948          0.153         0.428      0.330        0.333  0.292  0.342  0.810       0.611
     loto_rainfall           0.017           0.957          0.216         0.427      0.328        0.294  0.317  0.357  0.779       0.519
     weather                 0.013           0.974          0.230         0.502      0.316        0.343  0.312  0.330  0.807       0.568
b3   anthro                  0.970           0.083          0.498         0.166      0.295        0.165  0.214  0.204  0.136       0.219
     demand                  0.033           0.315          0.804         0.727      0.824        0.789  0.871  0.864  0.876       0.859
     loto_hurricane          0.031           0.901          0.245         0.513      0.300        0.337  0.060  0.056  0.026       0.084
     loto_lightning          0.010           0.903          0.159         0.377      0.327        0.310  0.259  0.293  0.841       0.646
     loto_rainfall           0.039           0.933          0.246         0.464      0.313        0.283  0.309  0.306  0.763       0.534
     weather                 0.042           0.955          0.234         0.492      0.318        0.319  0.302  0.303  0.754       0.585
cm   anthro                  0.977           0.066          0.490         0.201      0.281        0.174  0.154  0.151  0.048       0.147
     demand                  0.026           0.507          0.840         0.797      0.862        0.821  0.900  0.888  0.901       0.884
     weather                 0.019           0.971          0.216         0.478      0.285        0.320  0.275  0.254  0.644       0.482

### d_g

cond2                marven_anthro  marven_weather  deepship_ship  deepship_tug  mbari_dry  mbari_storm  dem_A  dem_B  dem_H  vbdmd_test
arch fam                                                                                                                                
b1   anthro                  0.428          -0.964         -0.822        -0.791     -0.825       -0.898 -0.916 -0.926 -0.915      -0.849
     demand                 -0.946          -0.579         -0.040         0.052      0.137        0.017  0.086  0.058  0.182       0.090
     loto_hurricane         -0.961           0.111         -0.872        -0.617     -0.792       -0.831 -0.922 -0.932 -0.929      -0.874
     loto_lightning         -0.972           0.117         -0.893        -0.638     -0.775       -0.825 -0.841 -0.846 -0.578      -0.675
     loto_rainfall          -0.951           0.254         -0.880        -0.634     -0.814       -0.865 -0.883 -0.865 -0.673      -0.713
     weather                -0.954           0.259         -0.860        -0.568     -0.775       -0.819 -0.848 -0.834 -0.569      -0.669
b3   anthro                  0.323          -0.955         -0.699        -0.729     -0.730       -0.825 -0.874 -0.880 -0.873      -0.786
     demand                 -0.960          -0.727         -0.112         0.054      0.124       -0.059 -0.006  0.016  0.165       0.013
     loto_hurricane         -0.962          -0.038         -0.841        -0.506     -0.743       -0.792 -0.898 -0.905 -0.916      -0.860
     loto_lightning         -0.972          -0.094         -0.888        -0.674     -0.769       -0.814 -0.842 -0.840 -0.507      -0.624
     loto_rainfall          -0.952           0.101         -0.826        -0.497     -0.733       -0.774 -0.829 -0.830 -0.640      -0.688
     weather                -0.953           0.136         -0.818        -0.493     -0.742       -0.778 -0.822 -0.812 -0.569      -0.633
cm   anthro                  0.281          -0.957         -0.767        -0.731     -0.762       -0.851 -0.900 -0.897 -0.906      -0.835
     demand                 -0.948          -0.550         -0.116         0.046      0.131       -0.047  0.018  0.005  0.264       0.123
     weather                -0.953           0.185         -0.849        -0.552     -0.758       -0.786 -0.871 -0.859 -0.687      -0.743

### SI-SDR gain (dB)

cond2                marven_anthro  marven_weather  deepship_ship  deepship_tug  mbari_dry  mbari_storm  dem_A  dem_B  dem_H  vbdmd_test
arch fam                                                                                                                                
b1   anthro                  11.17            0.26           0.91          0.84       0.30         0.18   0.14   0.10   0.04        0.27
     demand                   0.58            1.80           7.13          9.21      10.09         7.69  10.11  10.75  11.62        9.25
     loto_hurricane           0.04            6.18           0.35          0.27       0.11         0.38   0.00  -0.01  -0.02        0.03
     loto_lightning           0.11            6.77           0.23          0.11       0.31         0.37   1.45   2.37   8.16        6.27
     loto_rainfall            0.21            7.26           0.45          0.18       0.51         0.59   1.14   1.69   4.44        3.59
     weather                  0.34           10.59           0.35          0.13       0.19         0.33   0.84   1.38   7.67        5.15
b3   anthro                   9.92            0.24           1.49          2.41       0.87         0.55   0.51   0.37   0.40        0.72
     demand                   0.49            0.70           5.97          7.91       8.86         6.59   9.21   9.59  10.95        8.88
     loto_hurricane           0.04            5.14           0.28          0.14       0.07         0.28   0.00  -0.01  -0.02        0.06
     loto_lightning           0.10            5.74           0.50          0.61       0.70         0.60   2.03   2.40   9.80        7.09
     loto_rainfall            0.25            6.22           0.59          0.46       0.59         0.50   0.97   1.41   5.78        5.18
     weather                  0.32            9.46           0.39          0.31       0.33         0.40   0.86   1.20   6.46        5.79
cm   anthro                  11.12            0.20           1.25          1.26       0.73         0.42   0.29   0.22   0.23        0.40
     demand                   0.54            1.56           6.76          8.77       9.73         7.18   9.61  10.39  11.07        9.21
     weather                  0.08           10.46           0.49          0.76       0.60         0.67   0.64   0.83   3.90        3.14

## 3. Family bonus: nr_g(anthro model) - nr_g(weather model), same mixtures, seed-paired

mean over 3 seeds:

      marven_anthro  marven_weather  deepship_ship  deepship_tug  mbari_dry  mbari_storm  dem_A  dem_B  dem_H  vbdmd_test
arch                                                                                                                     
b1            0.970          -0.905          0.182        -0.332     -0.062       -0.194 -0.167 -0.194 -0.752      -0.439
b3            0.927          -0.873          0.264        -0.326     -0.023       -0.154 -0.089 -0.099 -0.617      -0.366
cm            0.958          -0.905          0.274        -0.277     -0.004       -0.147 -0.121 -0.103 -0.596      -0.335

range over seeds:

     marven_anthro marven_weather deepship_ship  deepship_tug     mbari_dry   mbari_storm         dem_A         dem_B         dem_H    vbdmd_test
arch                                                                                                                                             
b1    +0.97..+0.97   -0.92..-0.88  +0.16..+0.19  -0.36..-0.32  -0.07..-0.05  -0.22..-0.18  -0.19..-0.15  -0.21..-0.17  -0.78..-0.72  -0.46..-0.42
b3    +0.89..+0.95   -0.88..-0.87  +0.21..+0.33  -0.35..-0.31  -0.07..+0.06  -0.18..-0.11  -0.14..-0.01  -0.18..-0.00  -0.69..-0.53  -0.44..-0.29
cm    +0.95..+0.96   -0.91..-0.90  +0.24..+0.30  -0.29..-0.27  -0.03..+0.03  -0.17..-0.12  -0.17..-0.05  -0.16..-0.03  -0.69..-0.47  -0.38..-0.25

### family bonus by SNR (all archs and seeds averaged)

cond   deepship_ship  deepship_tug  mbari_dry  mbari_storm
snr                                                       
-15.0          0.873        -0.112      0.429        0.499
-10.0          0.322        -0.291      0.192        0.050
-5.0           0.358        -0.333     -0.027       -0.084
 0.0           0.253        -0.362     -0.049       -0.203
 5.0           0.187        -0.335     -0.098       -0.207
 10.0          0.119        -0.298     -0.091       -0.214
 15.0          0.140        -0.278     -0.066       -0.181
 20.0          0.156        -0.248     -0.045       -0.156

## 4. LOTO models with MarVEN split into heard weather / held-out weather / anthro (report's R1 pooled these)

c                  heard_weather  heldout_weather  anthro_unheard  deepship_ship  deepship_tug  mbari_dry  mbari_storm  dem_A  dem_H  vbdmd_test
tag                                                                                                                                             
b1_loto_hurricane          0.973           -0.008           0.024          0.200         0.473      0.258        0.325  0.049  0.012       0.064
b1_loto_lightning          0.982            0.020           0.007          0.153         0.428      0.330        0.333  0.292  0.810       0.611
b1_loto_rainfall           0.986            0.409           0.017          0.216         0.427      0.328        0.294  0.317  0.779       0.519
b3_loto_hurricane          0.953           -0.008           0.031          0.245         0.513      0.300        0.337  0.060  0.026       0.084
b3_loto_lightning          0.962            0.005           0.010          0.159         0.377      0.327        0.310  0.259  0.841       0.646
b3_loto_rainfall           0.978            0.487           0.039          0.246         0.464      0.313        0.283  0.309  0.763       0.534

per MarVEN type:

noise_type         bubble_curtain  hurricane  large_commercial_ship  lightning  rainfall
tag                                                                                     
b1_loto_hurricane           0.009     -0.008                  0.313      0.975     0.970
b1_loto_lightning          -0.001      0.998                  0.036      0.020     0.966
b1_loto_rainfall           -0.004      0.998                  0.323      0.972     0.409
b3_loto_hurricane           0.004     -0.008                  0.273      0.961     0.945
b3_loto_lightning          -0.001      0.997                  0.028      0.005     0.929
b3_loto_rainfall            0.010      0.997                  0.293      0.954     0.487
