# probe report: dfn3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown  0.3421  0.3220  0.3582 0.8506   0.8367   0.8613 0.0001   0.0310 unknown     0.3175      0.8114     unknown
               POOLED      low 1095     864 unknown  0.0134 -0.0168  0.0473 0.9744   0.9727   0.9761 0.0007  -0.0883 unknown    -0.0152      0.9555     unknown
       bubble_curtain     high  243     232 unknown  0.2403  0.1522  0.3062 0.8480   0.7872   0.8870 0.0001  -0.2712 unknown     0.1633      0.8470     unknown
       bubble_curtain      low  233     224 unknown  0.1136  0.0613  0.1594 0.9944   0.9934   0.9950 0.0005  -0.3652 unknown     0.0914      0.9946     unknown
            hurricane     high  210     203 unknown -0.1979 -0.3865 -0.0494 0.6037   0.5362   0.7014 0.0000  -0.7373 unknown     0.5471     -2.0776     unknown
            hurricane      low  236     231 unknown  0.4172  0.3919  0.4505 0.9979   0.9976   0.9985 0.0002  -0.0103 unknown     0.3113      0.8509     unknown
large_commercial_ship     high  239     229 unknown  0.3738  0.3476  0.3978 0.8921   0.8747   0.9011 0.0003   0.1206 unknown     0.2889      0.8508     unknown
large_commercial_ship      low  202     196 unknown -0.1264 -0.2432 -0.0488 0.9599   0.9526   0.9641 0.0010  -0.0406 unknown    -0.1883      0.9436     unknown
            lightning     high  249     245 unknown  0.2734  0.2459  0.2989 0.8359   0.8172   0.8660 0.0003  -0.0326 unknown     0.2157      0.8457     unknown
            lightning      low  210     206 unknown -0.2029 -0.2539 -0.1579 0.9664   0.9624   0.9691 0.0008  -0.1845 unknown    -0.2261      0.9662     unknown
             rainfall     high  244     236 unknown  0.4507  0.4252  0.4694 0.8700   0.8553   0.8811 0.0002   0.1815 unknown     0.4035      0.8717     unknown
             rainfall      low  214     203 unknown -0.1911 -0.3281 -0.0703 0.9530   0.9477   0.9577 0.0009  -0.0071 unknown    -0.2072      0.9528     unknown
```