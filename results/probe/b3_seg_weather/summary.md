# probe report: b3_seg_weather

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.1035 -0.1516 -0.0661  0.7608   0.7147   0.7965 0.0000  -0.5668 active_balanced    -0.2380      0.5152 active_balanced
               POOLED      low 1095     864 R1/R4 -0.8072 -0.8958 -0.7486  0.8542   0.8107   0.8829 0.0002  -1.2783 active_balanced    -0.8224      0.7713 active_balanced
       bubble_curtain     high  243     232    R4 -0.9059 -0.9243 -0.8801 -0.0008  -0.0050   0.0025 0.0000  -1.7257           inert    -0.9542     -0.0093           inert
       bubble_curtain      low  233     224    R4 -0.9984 -0.9986 -0.9980 -0.0242  -0.0324  -0.0166 0.0000  -1.9338           inert    -0.9986     -0.0305           inert
            hurricane     high  210     203    R1  0.7809  0.7215  0.8346  0.9862   0.9805   0.9907 0.0000   0.0371 active_balanced    -0.1189      0.0473 active_balanced
            hurricane      low  236     231    R1  0.3973  0.3495  0.4604  0.9990   0.9989   0.9992 0.0001  -0.1734 active_balanced    -0.0513      0.9164 active_balanced
large_commercial_ship     high  239     229    R4 -0.7242 -0.7767 -0.6880  0.3319   0.3093   0.3456 0.0000  -1.3589 active_balanced    -0.6187      0.4383 active_balanced
large_commercial_ship      low  202     196    R4 -0.9827 -0.9886 -0.9788  0.0559   0.0314   0.0728 0.0004  -1.9051           inert    -0.9729      0.1208           inert
            lightning     high  249     245    R1  0.2364  0.2090  0.2551  0.8836   0.8686   0.9031 0.0001  -0.2554            over     0.2261      0.8833            over
            lightning      low  210     206    R1 -0.2220 -0.3372 -0.1508  0.9585   0.9535   0.9647 0.0002  -0.3235            over    -0.2176      0.9598            over
             rainfall     high  244     236    R1 -0.0281 -0.0527 -0.0163  0.8454   0.8383   0.8569 0.0000  -0.4718            over    -0.0550      0.8455            over
             rainfall      low  214     203    R1 -0.7210 -0.7752 -0.6406  0.8801   0.8657   0.8951 0.0005  -1.0353            over    -0.7222      0.8802            over
```