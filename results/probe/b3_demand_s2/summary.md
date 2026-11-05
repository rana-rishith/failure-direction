# probe report: b3_demand_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.7345 -0.7544 -0.7054  0.2521   0.2186   0.2850 0.0000  -1.2862 unknown    -0.8098      0.1319     unknown
               POOLED      low 1095     864 unknown -0.9858 -0.9893 -0.9838  0.0515   0.0432   0.0678 0.0001  -1.8899 unknown    -0.9870      0.0423     unknown
       bubble_curtain     high  243     232 unknown -0.9198 -0.9347 -0.9058  0.0124   0.0096   0.0167 0.0000  -1.7150 unknown    -0.9571      0.0079     unknown
       bubble_curtain      low  233     224 unknown -0.9986 -0.9988 -0.9982  0.0059  -0.0019   0.0122 0.0000  -1.9338 unknown    -0.9988      0.0034     unknown
            hurricane     high  210     203 unknown  0.5481  0.3646  0.6809  0.9585   0.9441   0.9681 0.0000  -0.0302 unknown     0.1433     -0.0923     unknown
            hurricane      low  236     231 unknown  0.4343  0.3794  0.4693  0.9988   0.9983   0.9989 0.0000  -0.0534 unknown     0.1080      0.8977     unknown
large_commercial_ship     high  239     229 unknown -0.6936 -0.7402 -0.6062  0.4333   0.3940   0.4705 0.0000  -1.2170 unknown    -0.6957      0.3734     unknown
large_commercial_ship      low  202     196 unknown -0.9765 -0.9824 -0.9681  0.1886   0.1684   0.2115 0.0007  -1.8468 unknown    -0.9694      0.1562     unknown
            lightning     high  249     245 unknown -0.8006 -0.8314 -0.7715  0.0894   0.0824   0.1024 0.0000  -1.4215 unknown    -0.8552      0.0878     unknown
            lightning      low  210     206 unknown -0.9910 -0.9934 -0.9874  0.0094   0.0013   0.0246 0.0001  -1.9183 unknown    -0.9922      0.0076     unknown
             rainfall     high  244     236 unknown -0.7075 -0.7546 -0.6664  0.3616   0.3263   0.3941 0.0000  -1.1955 unknown    -0.8119      0.3551     unknown
             rainfall      low  214     203 unknown -0.9911 -0.9922 -0.9848 -0.0216  -0.0448  -0.0071 0.0002  -1.9035 unknown    -0.9916     -0.0419     unknown
```