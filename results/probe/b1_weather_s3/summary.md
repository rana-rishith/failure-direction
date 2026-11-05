# probe report: b1_weather_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4  0.1446  0.1037  0.1788  0.8525   0.8292   0.8725 0.0000  -0.2973 active_balanced    -0.2099      0.5393 active_balanced
               POOLED      low 1095     864 R1/R4 -0.1734 -0.2601 -0.1227  0.9733   0.9705   0.9763 0.0003  -0.1743 active_balanced    -0.2972      0.9228 active_balanced
       bubble_curtain     high  243     232    R4 -0.9276 -0.9414 -0.9105 -0.0033  -0.0059  -0.0013 0.0000  -1.7569           inert    -0.9611     -0.0083           inert
       bubble_curtain      low  233     224    R4 -0.9986 -0.9988 -0.9981 -0.0120  -0.0220  -0.0076 0.0000  -1.9341           inert    -0.9988     -0.0179           inert
            hurricane     high  210     203    R1  0.7140  0.6429  0.7903  0.9837   0.9716   0.9888 0.0000   0.0097 active_balanced    -0.3502      0.1555 active_balanced
            hurricane      low  236     231    R1  0.4534  0.4022  0.4801  0.9992   0.9990   0.9993 0.0001  -0.1178 active_balanced     0.0081      0.9254 active_balanced
large_commercial_ship     high  239     229    R4 -0.7764 -0.8060 -0.7420  0.3271   0.3146   0.3369 0.0000  -1.4455 active_balanced    -0.6630      0.4524 active_balanced
large_commercial_ship      low  202     196    R4 -0.9677 -0.9812 -0.9600  0.1112   0.0643   0.1638 0.0009  -1.8601            over    -0.9413      0.3389            over
            lightning     high  249     245    R1  0.3386  0.3209  0.3617  0.9361   0.9269   0.9450 0.0001  -0.1725            over     0.3388      0.9370            over
            lightning      low  210     206    R1  0.1378  0.0908  0.1823  0.9862   0.9845   0.9876 0.0004  -0.0729            over     0.1411      0.9863            over
             rainfall     high  244     236    R1  0.2350  0.2215  0.2517  0.9059   0.8963   0.9156 0.0000  -0.1704            over     0.2343      0.9055            over
             rainfall      low  214     203    R1 -0.1153 -0.1597 -0.0824  0.9766   0.9743   0.9781 0.0005  -0.0618            over    -0.1188      0.9762            over
```