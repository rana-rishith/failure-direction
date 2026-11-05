# probe report: cm_demand_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi   r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.6300 -0.6673 -0.6028  0.4536   0.4416   0.4673  1.1980  -1.7527 unknown    -0.6863      0.3778     unknown
               POOLED      low 1095     864 unknown -0.9852 -0.9885 -0.9823  0.0648   0.0403   0.0971  3.1941  -1.9185 unknown    -0.9845      0.0828     unknown
       bubble_curtain     high  243     232 unknown -0.9203 -0.9309 -0.9066  0.0003  -0.0029   0.0045  1.2440  -1.8510 unknown    -0.9571     -0.0050     unknown
       bubble_curtain      low  233     224 unknown -0.9984 -0.9987 -0.9981 -0.0240  -0.0298  -0.0169 10.0390  -1.9376 unknown    -0.9988     -0.0269     unknown
            hurricane     high  210     203 unknown  0.4984  0.3776  0.6707  0.9557   0.9190   0.9677  1.2057  -1.8792 unknown     0.1074     -0.8455     unknown
            hurricane      low  236     231 unknown  0.4220  0.3790  0.4604  0.9988   0.9984   0.9990  1.2132  -1.8324 unknown     0.1816      0.9063     unknown
large_commercial_ship     high  239     229 unknown -0.5082 -0.6025 -0.4060  0.6043   0.5750   0.6499  1.1823  -1.6925 unknown    -0.4519      0.5863     unknown
large_commercial_ship      low  202     196 unknown -0.9750 -0.9850 -0.9707  0.0512   0.0024   0.0972  2.7470  -1.9271 unknown    -0.9628      0.1188     unknown
            lightning     high  249     245 unknown -0.6071 -0.6554 -0.5467  0.4757   0.4523   0.5048  1.1823  -1.7142 unknown    -0.6707      0.4798     unknown
            lightning      low  210     206 unknown -0.9871 -0.9898 -0.9831  0.1388   0.1213   0.1564  3.8321  -1.9297 unknown    -0.9873      0.1385     unknown
             rainfall     high  244     236 unknown -0.6849 -0.7154 -0.6243  0.4166   0.4055   0.4348  1.1855  -1.6707 unknown    -0.7567      0.4062     unknown
             rainfall      low  214     203 unknown -0.9907 -0.9928 -0.9849 -0.0606  -0.0891  -0.0384  7.5264  -1.9168 unknown    -0.9907     -0.0769     unknown
```