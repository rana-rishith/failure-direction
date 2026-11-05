# probe report: b3_weather

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.0135 -0.0651  0.0226 0.7839   0.7516   0.8046 0.0000  -0.4458 active_balanced    -0.2042      0.5640 active_balanced
               POOLED      low 1095     864 R1/R4 -0.3724 -0.4592 -0.2913 0.9493   0.9422   0.9539 0.0002  -0.3417 active_balanced    -0.4746      0.8938 active_balanced
       bubble_curtain     high  243     232    R4 -0.9201 -0.9337 -0.9000 0.0312   0.0265   0.0381 0.0000  -1.7452           inert    -0.9438      0.0292           inert
       bubble_curtain      low  233     224    R4 -0.9972 -0.9977 -0.9969 0.0327   0.0241   0.0396 0.0001  -1.9322           inert    -0.9972      0.0336           inert
            hurricane     high  210     203    R1  0.6019  0.5187  0.6658 0.9795   0.9697   0.9837 0.0000  -0.0462 active_balanced    -0.2926      0.1312 active_balanced
            hurricane      low  236     231    R1  0.2350  0.1852  0.2938 0.9988   0.9986   0.9990 0.0001  -0.3071 active_balanced    -0.1698      0.9002 active_balanced
large_commercial_ship     high  239     229    R4 -0.7258 -0.7655 -0.7032 0.3515   0.3405   0.3650 0.0000  -1.3704 active_balanced    -0.5761      0.5059 active_balanced
large_commercial_ship      low  202     196    R4 -0.9670 -0.9825 -0.9565 0.1001   0.0692   0.1403 0.0007  -1.8552 active_balanced    -0.9365      0.3781 active_balanced
            lightning     high  249     245    R1  0.3221  0.2755  0.3443 0.9011   0.8906   0.9132 0.0001  -0.1358            over     0.3216      0.9021            over
            lightning      low  210     206    R1  0.0593 -0.0047  0.0975 0.9768   0.9735   0.9789 0.0002  -0.0627            over     0.0679      0.9772            over
             rainfall     high  244     236    R1  0.0744  0.0526  0.0908 0.8577   0.8460   0.8659 0.0000  -0.2920            over     0.0654      0.8593            over
             rainfall      low  214     203    R1 -0.2967 -0.3645 -0.2247 0.9527   0.9503   0.9548 0.0002  -0.1151            over    -0.2942      0.9520            over
```