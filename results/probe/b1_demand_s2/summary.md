# probe report: b1_demand_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.4009 -0.4541 -0.3539  0.5720   0.5472   0.6012 0.0000  -0.8875 unknown    -0.5386      0.4605     unknown
               POOLED      low 1095     864 unknown -0.9786 -0.9811 -0.9705  0.1044   0.0685   0.1372 0.0002  -1.7962 unknown    -0.9758      0.1169     unknown
       bubble_curtain     high  243     232 unknown -0.9180 -0.9303 -0.9007  0.0148   0.0116   0.0197 0.0000  -1.7385 unknown    -0.9526      0.0097     unknown
       bubble_curtain      low  233     224 unknown -0.9977 -0.9981 -0.9974  0.0140   0.0069   0.0219 0.0001  -1.9324 unknown    -0.9981      0.0120     unknown
            hurricane     high  210     203 unknown  0.6786  0.4927  0.7369  0.9652   0.9523   0.9778 0.0000  -0.0042 unknown     0.0676      0.0516     unknown
            hurricane      low  236     231 unknown  0.4042  0.3697  0.4533  0.9990   0.9987   0.9991 0.0001  -0.1414 unknown     0.0084      0.9141     unknown
large_commercial_ship     high  239     229 unknown -0.1014 -0.1652 -0.0351  0.7784   0.7570   0.8006 0.0001  -0.3575 unknown    -0.1242      0.7371     unknown
large_commercial_ship      low  202     196 unknown -0.9518 -0.9735 -0.9432  0.1329  -0.0114   0.2289 0.0007  -1.6037 unknown    -0.9197      0.2850     unknown
            lightning     high  249     245 unknown -0.2809 -0.3593 -0.2184  0.6545   0.6319   0.6783 0.0001  -0.7002 unknown    -0.4195      0.6549     unknown
            lightning      low  210     206 unknown -0.9669 -0.9773 -0.9437  0.2281   0.1716   0.2876 0.0002  -1.7971 unknown    -0.9692      0.2290     unknown
             rainfall     high  244     236 unknown -0.6423 -0.7108 -0.6023  0.4302   0.4059   0.4494 0.0000  -1.1745 unknown    -0.7556      0.4205     unknown
             rainfall      low  214     203 unknown -0.9902 -0.9923 -0.9833 -0.0994  -0.1320  -0.0326 0.0002  -1.8855 unknown    -0.9903     -0.1140     unknown
```