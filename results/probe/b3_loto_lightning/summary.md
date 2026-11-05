# probe report: b3_loto_lightning

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.7400 -0.7731 -0.6937  0.0395   0.0358   0.0456 0.0000  -1.3088           inert    -0.8151      0.0203           inert
               POOLED      low 1095     864 R1/R4 -0.9780 -0.9810 -0.9722  0.0304   0.0212   0.0400 0.0001  -1.8596           inert    -0.9722      0.0231           inert
       bubble_curtain     high  243     232    R4 -0.9216 -0.9347 -0.9015  0.0014  -0.0027   0.0043 0.0000  -1.7427           inert    -0.9607     -0.0075           inert
       bubble_curtain      low  233     224    R4 -0.9985 -0.9988 -0.9981 -0.0054  -0.0123  -0.0006 0.0001  -1.9337           inert    -0.9989     -0.0127           inert
            hurricane     high  210     203    R1  0.7517  0.6891  0.8031  0.9885   0.9812   0.9910 0.0000   0.0596 active_balanced    -0.1302      0.1605 active_balanced
            hurricane      low  236     231    R1  0.4446  0.3876  0.4763  0.9991   0.9990   0.9992 0.0000  -0.0614 active_balanced     0.0053      0.9185 active_balanced
large_commercial_ship     high  239     229    R4 -0.8621 -0.8801 -0.8318  0.0378   0.0347   0.0414 0.0000  -1.5216           inert    -0.8379      0.0200           inert
large_commercial_ship      low  202     196    R4 -0.9893 -0.9925 -0.9834  0.0042  -0.0033   0.0107 0.0004  -1.9142           inert    -0.9850      0.0001           inert
            lightning     high  249     245    R4 -0.8602 -0.8771 -0.8290  0.0194   0.0165   0.0216 0.0000  -1.5424           inert    -0.8764      0.0185           inert
            lightning      low  210     206    R4 -0.9918 -0.9930 -0.9884 -0.0456  -0.0606  -0.0354 0.0001  -1.9178           inert    -0.9918     -0.0469            over
             rainfall     high  244     236    R1  0.0184  0.0022  0.0393  0.8602   0.8504   0.8720 0.0000  -0.2792            over     0.0092      0.8596            over
             rainfall      low  214     203    R1 -0.2813 -0.3204 -0.2278  0.9567   0.9540   0.9581 0.0002  -0.0914            over    -0.2829      0.9559            over
```