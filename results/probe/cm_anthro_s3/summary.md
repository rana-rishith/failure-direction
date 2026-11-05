# probe report: cm_anthro_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4 -0.5564 -0.6330 -0.5081  0.4531   0.3817   0.5274 0.2005  -1.7353 hallucinate+inert    -0.0776      0.4549 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.9724 -0.9771 -0.9664  0.1149   0.1016   0.1417 0.3308  -1.8433 hallucinate+inert    -0.8666      0.1129 hallucinate+inert
       bubble_curtain     high  243     232    R1  0.3626  0.3038  0.4326  0.9795   0.9749   0.9835 0.1977  -1.8435  hallucinate+over     0.3517      0.9813  hallucinate+over
       bubble_curtain      low  233     224    R1  0.5185  0.4916  0.5335  0.9989   0.9987   0.9989 0.1970  -1.8041       hallucinate     0.5033      0.9989       hallucinate
            hurricane     high  210     203    R4 -0.9132 -0.9284 -0.8891 -0.0023  -0.0070   0.0020 0.2032  -1.8811  hallucinate+over     0.2000     -0.4940  hallucinate+over
            hurricane      low  236     231    R4 -0.9984 -0.9986 -0.9980 -0.0003  -0.0036   0.0023 0.5270  -1.8359 hallucinate+inert    -0.8708      0.0263 hallucinate+inert
large_commercial_ship     high  239     229    R1  0.2309  0.2087  0.2504  0.9254   0.9126   0.9348 0.1962  -1.6719 hallucinate+inert     0.1915      0.8990 hallucinate+inert
large_commercial_ship      low  202     196    R1 -0.0862 -0.1390 -0.0409  0.9755   0.9729   0.9776 0.1261  -1.3885  hallucinate+over    -0.1297      0.9650  hallucinate+over
            lightning     high  249     245    R4 -0.7298 -0.7794 -0.7113  0.4208   0.3923   0.4543 0.2029  -1.7082 hallucinate+inert    -0.7542      0.4173 hallucinate+inert
            lightning      low  210     206    R4 -0.9914 -0.9928 -0.9880  0.1165   0.1047   0.1333 0.7435  -1.9283 hallucinate+inert    -0.9927      0.1122 hallucinate+inert
             rainfall     high  244     236    R4 -0.8444 -0.8641 -0.8261  0.1159   0.1118   0.1204 0.2070  -1.6671 hallucinate+inert    -0.8574      0.0985 hallucinate+inert
             rainfall      low  214     203    R4 -0.9869 -0.9879 -0.9792 -0.1293  -0.1769  -0.0634 1.6586  -1.9111 hallucinate+inert    -0.9874     -0.1606 hallucinate+inert
```