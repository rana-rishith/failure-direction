# probe report: b1_weather_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4  0.1468  0.1052  0.1758  0.8652   0.8418   0.8825 0.0000  -0.2584 active_balanced    -0.0938      0.6055 active_balanced
               POOLED      low 1095     864 R1/R4 -0.1948 -0.2666 -0.1381  0.9744   0.9722   0.9767 0.0003  -0.1522 active_balanced    -0.2907      0.9288 active_balanced
       bubble_curtain     high  243     232    R4 -0.9316 -0.9470 -0.9170  0.0020  -0.0004   0.0041 0.0000  -1.7641           inert    -0.9601     -0.0020           inert
       bubble_curtain      low  233     224    R4 -0.9986 -0.9988 -0.9983 -0.0089  -0.0133  -0.0035 0.0000  -1.9340           inert    -0.9988     -0.0111           inert
            hurricane     high  210     203    R1  0.7769  0.7280  0.8524  0.9852   0.9761   0.9893 0.0000   0.0453 active_balanced    -0.1769      0.0902 active_balanced
            hurricane      low  236     231    R1  0.5351  0.5113  0.5883  0.9992   0.9991   0.9994 0.0001  -0.0098 active_balanced     0.1136      0.9322 active_balanced
large_commercial_ship     high  239     229    R4 -0.7425 -0.7691 -0.7075  0.3923   0.3823   0.4015 0.0001  -1.3734 active_balanced    -0.5835      0.5475 active_balanced
large_commercial_ship      low  202     196    R4 -0.9621 -0.9813 -0.9564  0.1476   0.0834   0.2030 0.0011  -1.8400            over    -0.9221      0.4389            over
            lightning     high  249     245    R1  0.3634  0.3480  0.3802  0.9404   0.9320   0.9461 0.0001  -0.1104            over     0.3650      0.9409            over
            lightning      low  210     206    R1  0.0986  0.0588  0.1320  0.9865   0.9851   0.9876 0.0004  -0.1033            over     0.1143      0.9867            over
             rainfall     high  244     236    R1  0.2070  0.1913  0.2259  0.9048   0.8981   0.9141 0.0000  -0.1833            over     0.1994      0.9051            over
             rainfall      low  214     203    R1 -0.1281 -0.1717 -0.0925  0.9774   0.9757   0.9790 0.0005  -0.0759            over    -0.1313      0.9773            over
```