# probe report: b1_weather

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4  0.1002  0.0394  0.1326  0.8478   0.8218   0.8645 0.0000  -0.3575 active_balanced    -0.1657      0.6056 active_balanced
               POOLED      low 1095     864 R1/R4 -0.1785 -0.2685 -0.1207  0.9739   0.9716   0.9761 0.0003  -0.1531 active_balanced    -0.2960      0.9226 active_balanced
       bubble_curtain     high  243     232    R4 -0.9314 -0.9485 -0.9238  0.0005  -0.0008   0.0023 0.0000  -1.7659           inert    -0.9607     -0.0027           inert
       bubble_curtain      low  233     224    R4 -0.9984 -0.9987 -0.9981 -0.0185  -0.0244  -0.0122 0.0000  -1.9338           inert    -0.9987     -0.0199           inert
            hurricane     high  210     203    R1  0.7146  0.6035  0.7780  0.9818   0.9727   0.9893 0.0000   0.0067 active_balanced    -0.2996      0.2396 active_balanced
            hurricane      low  236     231    R1  0.4403  0.4041  0.4782  0.9991   0.9990   0.9993 0.0001  -0.1010 active_balanced     0.0089      0.9249 active_balanced
large_commercial_ship     high  239     229    R4 -0.7265 -0.7651 -0.6995  0.3983   0.3918   0.4042 0.0001  -1.3553 active_balanced    -0.5631      0.5610 active_balanced
large_commercial_ship      low  202     196    R4 -0.9629 -0.9815 -0.9584  0.0818   0.0236   0.1566 0.0009  -1.8439            over    -0.9276      0.3549            over
            lightning     high  249     245    R1  0.3402  0.3190  0.3554  0.9342   0.9238   0.9445 0.0001  -0.1534            over     0.3401      0.9342            over
            lightning      low  210     206    R1  0.1415  0.1057  0.1916  0.9860   0.9840   0.9873 0.0004  -0.0532            over     0.1489      0.9861            over
             rainfall     high  244     236    R1  0.1844  0.1563  0.2117  0.8988   0.8866   0.9086 0.0000  -0.1877            over     0.1781      0.9002            over
             rainfall      low  214     203    R1 -0.1111 -0.1471 -0.0712  0.9770   0.9747   0.9787 0.0005  -0.0545            over    -0.1141      0.9771            over
```