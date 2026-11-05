# probe report: b1_anthro_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6029 -0.6885 -0.5233  0.4176   0.3548   0.4813 0.0000  -0.8953 active_balanced     0.0467      0.4141 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9761 -0.9811 -0.9702  0.1134   0.0979   0.1280 0.0002  -1.7740 active_balanced    -0.8470      0.1237           inert
       bubble_curtain     high  243     232    R1  0.6687  0.6426  0.6923  0.9866   0.9842   0.9886 0.0000   0.0079 active_balanced     0.6711      0.9870 active_balanced
       bubble_curtain      low  233     224    R1  0.6752  0.6595  0.6872  0.9991   0.9989   0.9992 0.0001  -0.0074 active_balanced     0.6667      0.9991 active_balanced
            hurricane     high  210     203    R4 -0.9191 -0.9340 -0.8918 -0.0216  -0.0228  -0.0205 0.0000  -1.6206           inert     0.2543     -0.0878           inert
            hurricane      low  236     231    R4 -0.9982 -0.9984 -0.9979 -0.0129  -0.0153  -0.0117 0.0000  -1.8237           inert    -0.8553      0.0889           inert
large_commercial_ship     high  239     229    R1  0.2878  0.2725  0.3105  0.9330   0.9266   0.9414 0.0001   0.1307            over     0.2547      0.9107            over
large_commercial_ship      low  202     196    R1 -0.0571 -0.0970  0.0002  0.9801   0.9779   0.9824 0.0004  -0.0537            over    -0.0688      0.9716            over
            lightning     high  249     245    R4 -0.7349 -0.8079 -0.7092  0.3923   0.3646   0.4204 0.0000  -1.2122 active_balanced    -0.7541      0.3906 active_balanced
            lightning      low  210     206    R4 -0.9917 -0.9931 -0.9893  0.1032   0.0903   0.1167 0.0004  -1.9149           inert    -0.9931      0.1000           inert
             rainfall     high  244     236    R4 -0.8684 -0.8828 -0.8534  0.0963   0.0921   0.1017 0.0000  -1.3940           inert    -0.8774      0.0834           inert
             rainfall      low  214     203    R4 -0.9885 -0.9896 -0.9830 -0.0322  -0.0687  -0.0074 0.0003  -1.8866           inert    -0.9889     -0.0587           inert
```