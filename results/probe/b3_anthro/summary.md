# probe report: b3_anthro

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.4790 -0.5532 -0.3895  0.3689   0.3105   0.4537 0.0000  -1.0899 active_balanced     0.0038      0.3668 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9716 -0.9762 -0.9636  0.1795   0.1340   0.2084 0.0003  -1.7759           inert    -0.8217      0.2075 active_balanced
       bubble_curtain     high  243     232    R1  0.5494  0.5100  0.5915  0.9779   0.9733   0.9811 0.0000  -0.1807 active_balanced     0.5358      0.9783 active_balanced
       bubble_curtain      low  233     224    R1  0.5953  0.5773  0.6100  0.9987   0.9984   0.9989 0.0001  -0.0839 active_balanced     0.5789      0.9987 active_balanced
            hurricane     high  210     203    R4 -0.8811 -0.9087 -0.8362  0.0459   0.0342   0.0532 0.0000  -1.7334           inert     0.5607     -0.0340           inert
            hurricane      low  236     231    R4 -0.9978 -0.9981 -0.9975 -0.0041  -0.0065  -0.0015 0.0000  -1.8274           inert    -0.8257      0.0958           inert
large_commercial_ship     high  239     229    R1  0.2691  0.2489  0.2923  0.9102   0.9016   0.9205 0.0001  -0.1191            over     0.1959      0.8729            over
large_commercial_ship      low  202     196    R1 -0.1259 -0.1642 -0.0999  0.9664   0.9610   0.9697 0.0003  -0.1498            over    -0.1820      0.9521            over
            lightning     high  249     245    R4 -0.7193 -0.7815 -0.6735  0.3344   0.3042   0.3650 0.0001  -1.3662 active_balanced    -0.7635      0.3315 active_balanced
            lightning      low  210     206    R4 -0.9892 -0.9913 -0.9858  0.1842   0.1732   0.1945 0.0013  -1.9120           inert    -0.9918      0.1805           inert
             rainfall     high  244     236    R4 -0.8034 -0.8318 -0.7873  0.1168   0.1064   0.1224 0.0000  -1.4265           inert    -0.8478      0.0974           inert
             rainfall      low  214     203    R4 -0.9856 -0.9871 -0.9788 -0.0981  -0.1441  -0.0463 0.0004  -1.8856           inert    -0.9865     -0.1257           inert
```