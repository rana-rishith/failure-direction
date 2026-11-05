# probe report: cm_demand

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi   r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.4927 -0.5398 -0.4436  0.5331   0.5033   0.5650  1.6002  -1.7538 unknown    -0.5701      0.3994     unknown
               POOLED      low 1095     864 unknown -0.9805 -0.9843 -0.9771  0.0608   0.0369   0.0900  3.2411  -1.9173 unknown    -0.9804      0.0658     unknown
       bubble_curtain     high  243     232 unknown -0.9176 -0.9391 -0.9044  0.0077   0.0040   0.0119  1.6696  -1.8496 unknown    -0.9574      0.0013     unknown
       bubble_curtain      low  233     224 unknown -0.9981 -0.9985 -0.9977 -0.0125  -0.0173  -0.0073 13.6123  -1.9377 unknown    -0.9985     -0.0171     unknown
            hurricane     high  210     203 unknown  0.6163  0.4925  0.7040  0.9612   0.9502   0.9746  1.6224  -1.8793 unknown     0.1342     -0.7282     unknown
            hurricane      low  236     231 unknown  0.4329  0.3972  0.4765  0.9987   0.9984   0.9989  1.6120  -1.8331 unknown     0.1328      0.9074     unknown
large_commercial_ship     high  239     229 unknown -0.2677 -0.3113 -0.1968  0.6909   0.6733   0.7152  1.5301  -1.6942 unknown    -0.2483      0.6644     unknown
large_commercial_ship      low  202     196 unknown -0.9624 -0.9792 -0.9551  0.0999   0.0269   0.1516  2.2007  -1.9240 unknown    -0.9382      0.2139     unknown
            lightning     high  249     245 unknown -0.3534 -0.4058 -0.2930  0.6468   0.6311   0.6733  1.5412  -1.7138 unknown    -0.4361      0.6475     unknown
            lightning      low  210     206 unknown -0.9781 -0.9855 -0.9717  0.1841   0.1550   0.2297  3.6869  -1.9283 unknown    -0.9789      0.1849     unknown
             rainfall     high  244     236 unknown -0.7720 -0.8024 -0.7273  0.3483   0.3108   0.3734  1.6191  -1.6727 unknown    -0.8214      0.3434     unknown
             rainfall      low  214     203 unknown -0.9901 -0.9922 -0.9836 -0.0804  -0.0986  -0.0647 11.1160  -1.9169 unknown    -0.9908     -0.1043     unknown
```