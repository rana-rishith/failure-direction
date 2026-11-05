# probe report: b1_loto_lightning

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.7527 -0.7751 -0.7169  0.0609   0.0566   0.0693 0.0000  -1.3354           inert    -0.7942      0.0516           inert
               POOLED      low 1095     864 R1/R4 -0.9753 -0.9795 -0.9708  0.0299   0.0225   0.0394 0.0001  -1.8588           inert    -0.9693      0.0360           inert
       bubble_curtain     high  243     232    R4 -0.9323 -0.9442 -0.9239  0.0000  -0.0012   0.0025 0.0000  -1.7640           inert    -0.9618     -0.0051           inert
       bubble_curtain      low  233     224    R4 -0.9988 -0.9989 -0.9983 -0.0051  -0.0098   0.0012 0.0000  -1.9341           inert    -0.9989     -0.0077           inert
            hurricane     high  210     203    R1  0.7201  0.6511  0.7937  0.9894   0.9826   0.9922 0.0000   0.0538 active_balanced    -0.1874      0.2233 active_balanced
            hurricane      low  236     231    R1  0.4572  0.4187  0.4834  0.9992   0.9991   0.9994 0.0001  -0.0112 active_balanced     0.0166      0.9313 active_balanced
large_commercial_ship     high  239     229    R4 -0.8589 -0.8726 -0.8259  0.0559   0.0513   0.0591 0.0000  -1.5307           inert    -0.8170      0.0631           inert
large_commercial_ship      low  202     196    R4 -0.9866 -0.9901 -0.9811 -0.0094  -0.0255   0.0044 0.0000  -1.9077           inert    -0.9807      0.0064            over
            lightning     high  249     245    R4 -0.8462 -0.8759 -0.8196  0.0373   0.0335   0.0412 0.0000  -1.5455           inert    -0.8580      0.0370           inert
            lightning      low  210     206    R4 -0.9902 -0.9919 -0.9879 -0.0200  -0.0331  -0.0102 0.0001  -1.9160           inert    -0.9903     -0.0205            over
             rainfall     high  244     236    R1  0.2509  0.2415  0.2639  0.9168   0.9097   0.9270 0.0000  -0.0465            over     0.2471      0.9178            over
             rainfall      low  214     203    R1 -0.0705 -0.1166 -0.0266  0.9807   0.9793   0.9821 0.0004  -0.0055            over    -0.0797      0.9808            over
```