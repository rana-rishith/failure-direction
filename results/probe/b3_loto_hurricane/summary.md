# probe report: b3_loto_hurricane

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6634 -0.7068 -0.6029  0.3311   0.3150   0.3522 0.0000  -1.2896 active_balanced     0.0598      0.4564 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9824 -0.9880 -0.9690  0.0981   0.0441   0.1653 0.0002  -1.7967 active_balanced    -0.8301      0.2903 active_balanced
       bubble_curtain     high  243     232    R4 -0.9375 -0.9524 -0.9236  0.0132   0.0108   0.0152 0.0000  -1.7708           inert    -0.9384      0.0134           inert
       bubble_curtain      low  233     224    R4 -0.9982 -0.9985 -0.9979 -0.0138  -0.0210  -0.0086 0.0000  -1.9335           inert    -0.9982     -0.0136           inert
            hurricane     high  210     203    R4 -0.9102 -0.9324 -0.8881 -0.0025  -0.0028  -0.0012 0.0000  -1.7561           inert     0.5104      0.0666           inert
            hurricane      low  236     231    R4 -0.9978 -0.9981 -0.9976 -0.0143  -0.0161  -0.0122 0.0000  -1.8287           inert    -0.8258      0.0751           inert
large_commercial_ship     high  239     229    R4 -0.7892 -0.8162 -0.7586  0.3228   0.3146   0.3292 0.0000  -1.4513 active_balanced    -0.6778      0.4431 active_balanced
large_commercial_ship      low  202     196    R4 -0.9738 -0.9856 -0.9672  0.1405   0.1092   0.1709 0.0008  -1.8794 active_balanced    -0.9554      0.3168 active_balanced
            lightning     high  249     245    R1  0.3341  0.3169  0.3487  0.9258   0.9141   0.9329 0.0001  -0.1447 active_balanced     0.3374      0.9269 active_balanced
            lightning      low  210     206    R1  0.0873  0.0497  0.1215  0.9823   0.9802   0.9839 0.0003  -0.0917 active_balanced     0.0918      0.9823 active_balanced
             rainfall     high  244     236    R1  0.2011  0.1845  0.2182  0.8863   0.8796   0.8992 0.0000  -0.2043            over     0.1973      0.8886            over
             rainfall      low  214     203    R1 -0.2033 -0.2452 -0.1352  0.9658   0.9643   0.9688 0.0004  -0.0934            over    -0.2071      0.9665            over
```