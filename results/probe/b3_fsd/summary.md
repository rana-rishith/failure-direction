# probe report: b3_fsd

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.1421 -0.1759 -0.1115 0.5791   0.5609   0.5948 0.0000  -0.4805 unknown    -0.1600      0.4740     unknown
               POOLED      low 1095     864 unknown -0.4805 -0.5115 -0.4503 0.9207   0.9039   0.9330 0.0000  -0.4030 unknown    -0.4770      0.8444     unknown
       bubble_curtain     high  243     232 unknown -0.1083 -0.2342 -0.0035 0.5191   0.3795   0.6113 0.0000  -0.7242 unknown    -0.1597      0.5129     unknown
       bubble_curtain      low  233     224 unknown -0.1166 -0.2797 -0.0329 0.9786   0.9757   0.9807 0.0000  -0.6532 unknown    -0.1474      0.9783     unknown
            hurricane     high  210     203 unknown  0.4489  0.3517  0.6046 0.8301   0.7583   0.8801 0.0000  -0.0871 unknown     0.6531     -3.5323     unknown
            hurricane      low  236     231 unknown  0.4144  0.3584  0.4498 0.9973   0.9963   0.9978 0.0000  -0.0280 unknown     0.2064      0.7876     unknown
large_commercial_ship     high  239     229 unknown -0.2926 -0.3506 -0.2274 0.5275   0.4997   0.5511 0.0000  -0.5934 unknown    -0.2980      0.4782     unknown
large_commercial_ship      low  202     196 unknown -0.7442 -0.8062 -0.6917 0.7607   0.7330   0.7875 0.0000  -0.5167 unknown    -0.7392      0.6945     unknown
            lightning     high  249     245 unknown -0.2390 -0.3070 -0.2004 0.4779   0.4266   0.5005 0.0000  -0.5835 unknown    -0.3380      0.4804     unknown
            lightning      low  210     206 unknown -0.4902 -0.5224 -0.4576 0.9114   0.8969   0.9216 0.0000  -0.3531 unknown    -0.4892      0.9124     unknown
             rainfall     high  244     236 unknown -0.1281 -0.1733 -0.0952 0.6379   0.6176   0.6572 0.0000  -0.4004 unknown    -0.1776      0.6374     unknown
             rainfall      low  214     203 unknown -0.8531 -0.8841 -0.7682 0.7153   0.6851   0.7332 0.0001  -0.7031 unknown    -0.8298      0.7369     unknown
```