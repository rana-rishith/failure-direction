# probe report: b3_weather_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.0025 -0.0614  0.0438  0.7957   0.7555   0.8131 0.0000  -0.4354 active_balanced    -0.2419      0.4760 active_balanced
               POOLED      low 1095     864 R1/R4 -0.3694 -0.4474 -0.2929  0.9516   0.9467   0.9564 0.0002  -0.2954 active_balanced    -0.4514      0.8983 active_balanced
       bubble_curtain     high  243     232    R4 -0.9229 -0.9368 -0.9026  0.0109   0.0079   0.0136 0.0000  -1.7487           inert    -0.9553      0.0041           inert
       bubble_curtain      low  233     224    R4 -0.9985 -0.9988 -0.9980  0.0021  -0.0022   0.0080 0.0000  -1.9340           inert    -0.9987     -0.0018           inert
            hurricane     high  210     203    R1  0.7012  0.6354  0.7867  0.9843   0.9741   0.9891 0.0000   0.0257 active_balanced    -0.1903      0.1363 active_balanced
            hurricane      low  236     231    R1  0.3426  0.2993  0.4139  0.9989   0.9988   0.9991 0.0001  -0.1907 active_balanced    -0.1139      0.9079 active_balanced
large_commercial_ship     high  239     229    R4 -0.7685 -0.7884 -0.7443  0.2809   0.2739   0.2909 0.0000  -1.4234 active_balanced    -0.6603      0.4067 active_balanced
large_commercial_ship      low  202     196    R4 -0.9626 -0.9795 -0.9534 -0.0071  -0.0675   0.0835 0.0008  -1.8477            over    -0.9314      0.2854            over
            lightning     high  249     245    R1  0.2818  0.2503  0.3077  0.9046   0.8938   0.9185 0.0001  -0.1958            over     0.2754      0.9050            over
            lightning      low  210     206    R1  0.0528 -0.0017  0.0894  0.9766   0.9739   0.9793 0.0002  -0.0734            over     0.0655      0.9771            over
             rainfall     high  244     236    R1  0.1110  0.0918  0.1293  0.8650   0.8542   0.8733 0.0000  -0.2904            over     0.0974      0.8659            over
             rainfall      low  214     203    R1 -0.2972 -0.3596 -0.2224  0.9538   0.9522   0.9576 0.0002  -0.1430            over    -0.2982      0.9543            over
```