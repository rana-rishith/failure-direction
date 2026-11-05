# probe report: b3_loto_rainfall

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.4546 -0.5023 -0.3973  0.5720   0.5318   0.6008 0.0000  -0.8826 active_balanced    -0.5048      0.4901            over
               POOLED      low 1095     864 R1/R4 -0.9343 -0.9453 -0.9069  0.2830   0.2376   0.3237 0.0002  -1.7037            over    -0.8901      0.4213            over
       bubble_curtain     high  243     232    R4 -0.9210 -0.9398 -0.9011  0.0167   0.0142   0.0193 0.0000  -1.7481           inert    -0.9538      0.0128           inert
       bubble_curtain      low  233     224    R4 -0.9973 -0.9978 -0.9970 -0.0036  -0.0155   0.0028 0.0000  -1.9322           inert    -0.9973     -0.0068           inert
            hurricane     high  210     203    R1  0.6998  0.6061  0.7703  0.9813   0.9714   0.9871 0.0000   0.0427 active_balanced    -0.2161      0.1540 active_balanced
            hurricane      low  236     231    R1  0.4119  0.3562  0.4554  0.9990   0.9989   0.9992 0.0001  -0.0956 active_balanced    -0.0656      0.9153 active_balanced
large_commercial_ship     high  239     229    R4 -0.7509 -0.7912 -0.7347  0.3232   0.3170   0.3358 0.0000  -1.3709 active_balanced    -0.6244      0.4628            over
large_commercial_ship      low  202     196    R4 -0.9666 -0.9806 -0.9580  0.1434   0.0878   0.1760 0.0007  -1.8459            over    -0.9341      0.3951            over
            lightning     high  249     245    R1  0.3380  0.3086  0.3560  0.9109   0.8983   0.9242 0.0001  -0.1031            over     0.3308      0.9110            over
            lightning      low  210     206    R1  0.0698  0.0243  0.1136  0.9781   0.9753   0.9810 0.0002  -0.0786            over     0.0729      0.9783            over
             rainfall     high  244     236    R4 -0.4687 -0.4999 -0.4202  0.5912   0.5797   0.6040 0.0000  -0.8828            over    -0.4710      0.5918            over
             rainfall      low  214     203    R4 -0.9761 -0.9812 -0.9531 -0.2295  -0.3556  -0.0613 0.0003  -1.8036            over    -0.9759     -0.2509            over
```