# probe report: cm_anthro_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4 -0.5427 -0.6049 -0.4628  0.4157   0.3488   0.5101 0.2190  -1.7358 hallucinate+inert    -0.0197      0.4118 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.9719 -0.9768 -0.9655  0.1167   0.1020   0.1405 0.3531  -1.8476 hallucinate+inert    -0.8013      0.1358 hallucinate+inert
       bubble_curtain     high  243     232    R1  0.4005  0.3489  0.4382  0.9797   0.9759   0.9830 0.2203  -1.8447  hallucinate+over     0.3954      0.9794  hallucinate+over
       bubble_curtain      low  233     224    R1  0.4518  0.4316  0.4713  0.9987   0.9986   0.9989 0.2234  -1.8278       hallucinate     0.4454      0.9987       hallucinate
            hurricane     high  210     203    R4 -0.9088 -0.9254 -0.8825  0.0250   0.0196   0.0285 0.2200  -1.8811  hallucinate+over     0.2969     -0.5000  hallucinate+over
            hurricane      low  236     231    R4 -0.9975 -0.9980 -0.9970  0.0196   0.0171   0.0234 0.5306  -1.8359 hallucinate+inert    -0.8083      0.0813 hallucinate+inert
large_commercial_ship     high  239     229    R1  0.2537  0.2385  0.2718  0.9275   0.9162   0.9340 0.2076  -1.6703 hallucinate+inert     0.1874      0.8967 hallucinate+inert
large_commercial_ship      low  202     196    R1 -0.0737 -0.1242 -0.0363  0.9759   0.9740   0.9781 0.1339  -1.4360  hallucinate+over    -0.1215      0.9654  hallucinate+over
            lightning     high  249     245    R4 -0.7398 -0.7812 -0.7020  0.3900   0.3624   0.4169 0.2193  -1.7087 hallucinate+inert    -0.7618      0.3909 hallucinate+inert
            lightning      low  210     206    R4 -0.9909 -0.9926 -0.9881  0.1183   0.1055   0.1319 0.8191  -1.9282 hallucinate+inert    -0.9930      0.1134 hallucinate+inert
             rainfall     high  244     236    R4 -0.8333 -0.8534 -0.8116  0.1269   0.1220   0.1313 0.2225  -1.6658 hallucinate+inert    -0.8508      0.1087 hallucinate+inert
             rainfall      low  214     203    R4 -0.9865 -0.9884 -0.9804 -0.0938  -0.1338  -0.0545 1.8126  -1.9130 hallucinate+inert    -0.9871     -0.1236 hallucinate+inert
```