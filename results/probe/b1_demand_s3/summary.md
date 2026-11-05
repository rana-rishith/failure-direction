# probe report: b1_demand_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.5387 -0.5813 -0.4941  0.5242   0.4948   0.5564 0.0000  -1.0874 unknown    -0.6249      0.4034     unknown
               POOLED      low 1095     864 unknown -0.9736 -0.9774 -0.9649  0.1862   0.1168   0.2346 0.0002  -1.7977 unknown    -0.9719      0.2056     unknown
       bubble_curtain     high  243     232 unknown -0.9281 -0.9443 -0.9212  0.0046   0.0014   0.0082 0.0000  -1.7560 unknown    -0.9563      0.0010     unknown
       bubble_curtain      low  233     224 unknown -0.9983 -0.9987 -0.9980 -0.0099  -0.0154  -0.0037 0.0001  -1.9332 unknown    -0.9985     -0.0118     unknown
            hurricane     high  210     203 unknown  0.1412 -0.0265  0.3915  0.9305   0.8992   0.9561 0.0000  -0.4199 unknown    -0.0148      0.1396     unknown
            hurricane      low  236     231 unknown  0.2782  0.1858  0.3169  0.9983   0.9975   0.9985 0.0001  -0.2600 unknown    -0.0037      0.9028     unknown
large_commercial_ship     high  239     229 unknown -0.2139 -0.3086 -0.1258  0.7391   0.7199   0.7593 0.0001  -0.4956 unknown    -0.2409      0.7012     unknown
large_commercial_ship      low  202     196 unknown -0.9611 -0.9769 -0.9489  0.0615  -0.0369   0.1438 0.0005  -1.7586 unknown    -0.9400      0.1948     unknown
            lightning     high  249     245 unknown -0.4310 -0.4734 -0.3793  0.6370   0.6196   0.6598 0.0000  -0.9292 unknown    -0.5010      0.6360     unknown
            lightning      low  210     206 unknown -0.9650 -0.9734 -0.9465  0.4312   0.3961   0.4558 0.0003  -1.8022 unknown    -0.9664      0.4339     unknown
             rainfall     high  244     236 unknown -0.7267 -0.7438 -0.6822  0.3869   0.3739   0.3975 0.0000  -1.2681 unknown    -0.7799      0.3775     unknown
             rainfall      low  214     203 unknown -0.9860 -0.9897 -0.9770 -0.1415  -0.2077  -0.0730 0.0002  -1.8438 unknown    -0.9862     -0.1639     unknown
```