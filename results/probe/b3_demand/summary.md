# probe report: b3_demand

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.6921 -0.7163 -0.6604  0.3528   0.3227   0.3761 0.0000  -1.2076 unknown    -0.7549      0.2353     unknown
               POOLED      low 1095     864 unknown -0.9851 -0.9894 -0.9812  0.0400   0.0290   0.0503 0.0001  -1.8856 unknown    -0.9850      0.0388     unknown
       bubble_curtain     high  243     232 unknown -0.9195 -0.9350 -0.9042  0.0097   0.0063   0.0135 0.0000  -1.7168 unknown    -0.9530      0.0044     unknown
       bubble_curtain      low  233     224 unknown -0.9984 -0.9987 -0.9980 -0.0084  -0.0179  -0.0038 0.0000  -1.9337 unknown    -0.9986     -0.0091     unknown
            hurricane     high  210     203 unknown  0.2002  0.0642  0.4150  0.9341   0.9059   0.9498 0.0000  -0.2437 unknown     0.2306     -0.2006     unknown
            hurricane      low  236     231 unknown  0.3239  0.2785  0.3903  0.9982   0.9978   0.9985 0.0000  -0.0951 unknown     0.0958      0.8934     unknown
large_commercial_ship     high  239     229 unknown -0.5722 -0.6300 -0.4875  0.5078   0.4799   0.5478 0.0000  -0.9796 unknown    -0.5640      0.4798     unknown
large_commercial_ship      low  202     196 unknown -0.9759 -0.9870 -0.9695  0.1087   0.0730   0.1304 0.0005  -1.8647 unknown    -0.9650      0.1625     unknown
            lightning     high  249     245 unknown -0.7444 -0.7803 -0.7199  0.1908   0.1766   0.2107 0.0000  -1.3191 unknown    -0.7984      0.1878     unknown
            lightning      low  210     206 unknown -0.9880 -0.9909 -0.9843  0.0211  -0.0011   0.0375 0.0001  -1.9057 unknown    -0.9890      0.0194     unknown
             rainfall     high  244     236 unknown -0.7027 -0.7456 -0.6410  0.3996   0.3779   0.4137 0.0000  -1.1731 unknown    -0.7900      0.3889     unknown
             rainfall      low  214     203 unknown -0.9894 -0.9911 -0.9824 -0.0150  -0.0478   0.0030 0.0002  -1.8955 unknown    -0.9901     -0.0375     unknown
```