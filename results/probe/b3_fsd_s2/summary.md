# probe report: b3_fsd_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.2545 -0.2836 -0.2194 0.5985   0.5869   0.6163 0.0000  -0.6477 unknown    -0.3027      0.4998     unknown
               POOLED      low 1095     864 unknown -0.5095 -0.5424 -0.4729 0.9125   0.9037   0.9206 0.0000  -0.4928 unknown    -0.5328      0.8535     unknown
       bubble_curtain     high  243     232 unknown -0.4567 -0.5418 -0.3962 0.3914   0.3192   0.5027 0.0000  -1.1378 unknown    -0.5428      0.3874     unknown
       bubble_curtain      low  233     224 unknown -0.4462 -0.5873 -0.3896 0.9515   0.9454   0.9579 0.0001  -1.0617 unknown    -0.4867      0.9502     unknown
            hurricane     high  210     203 unknown  0.4189  0.2770  0.5216 0.8612   0.8216   0.8958 0.0000  -0.1110 unknown     0.6262     -1.9186     unknown
            hurricane      low  236     231 unknown  0.4353  0.4019  0.4646 0.9978   0.9974   0.9982 0.0000  -0.0283 unknown     0.1784      0.8391     unknown
large_commercial_ship     high  239     229 unknown -0.2502 -0.3045 -0.1935 0.6229   0.5873   0.6504 0.0000  -0.5409 unknown    -0.2939      0.5473     unknown
large_commercial_ship      low  202     196 unknown -0.6401 -0.7297 -0.5892 0.8333   0.8097   0.8584 0.0000  -0.6086 unknown    -0.6772      0.7786     unknown
            lightning     high  249     245 unknown -0.2710 -0.2992 -0.2019 0.5005   0.4770   0.5219 0.0000  -0.6630 unknown    -0.3300      0.4994     unknown
            lightning      low  210     206 unknown -0.4738 -0.5113 -0.4474 0.9007   0.8853   0.9102 0.0000  -0.4138 unknown    -0.4885      0.9000     unknown
             rainfall     high  244     236 unknown -0.3543 -0.3902 -0.2946 0.6181   0.6009   0.6346 0.0000  -0.7273 unknown    -0.4371      0.6117     unknown
             rainfall      low  214     203 unknown -0.8362 -0.8659 -0.7625 0.7579   0.7438   0.7682 0.0000  -0.7365 unknown    -0.8386      0.7551     unknown
```