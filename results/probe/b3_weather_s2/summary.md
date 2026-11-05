# probe report: b3_weather_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.0953 -0.1558 -0.0503  0.7774   0.7440   0.7994 0.0000  -0.5534 active_balanced    -0.2697      0.5145 active_balanced
               POOLED      low 1095     864 R1/R4 -0.3759 -0.4599 -0.2965  0.9489   0.9435   0.9543 0.0002  -0.2632 active_balanced    -0.4472      0.9067 active_balanced
       bubble_curtain     high  243     232    R4 -0.9177 -0.9329 -0.9013  0.0070   0.0042   0.0094 0.0000  -1.7459           inert    -0.9574      0.0014           inert
       bubble_curtain      low  233     224    R4 -0.9981 -0.9985 -0.9978 -0.0115  -0.0212  -0.0054 0.0000  -1.9331           inert    -0.9984     -0.0142           inert
            hurricane     high  210     203    R1  0.7845  0.7248  0.8310  0.9863   0.9780   0.9907 0.0000   0.0471 active_balanced    -0.1827      0.1417 active_balanced
            hurricane      low  236     231    R1  0.4797  0.4314  0.5048  0.9991   0.9989   0.9992 0.0000  -0.0599 active_balanced    -0.0081      0.9149 active_balanced
large_commercial_ship     high  239     229    R4 -0.7715 -0.7973 -0.7455  0.3251   0.3139   0.3329 0.0000  -1.4238 active_balanced    -0.6533      0.4573 active_balanced
large_commercial_ship      low  202     196    R4 -0.9702 -0.9834 -0.9618  0.1127   0.0747   0.1369 0.0005  -1.8641 active_balanced    -0.9426      0.3429 active_balanced
            lightning     high  249     245    R1  0.2553  0.2160  0.2870  0.8958   0.8860   0.9064 0.0001  -0.2226            over     0.2624      0.8965            over
            lightning      low  210     206    R1  0.0692 -0.0052  0.1059  0.9774   0.9734   0.9792 0.0002  -0.0889            over     0.0730      0.9775            over
             rainfall     high  244     236    R1 -0.0204 -0.0410  0.0164  0.8526   0.8419   0.8609 0.0000  -0.4442            over    -0.0230      0.8537            over
             rainfall      low  214     203    R1 -0.3124 -0.3880 -0.2646  0.9521   0.9491   0.9549 0.0003  -0.1703            over    -0.3304      0.9517            over
```