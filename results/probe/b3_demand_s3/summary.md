# probe report: b3_demand_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.7537 -0.7737 -0.7368 0.2326   0.2123   0.2545 0.0000  -1.3408 unknown    -0.8216      0.1397     unknown
               POOLED      low 1095     864 unknown -0.9872 -0.9902 -0.9846 0.0446   0.0366   0.0527 0.0001  -1.8891 unknown    -0.9867      0.0420     unknown
       bubble_curtain     high  243     232 unknown -0.9198 -0.9412 -0.9104 0.0089   0.0073   0.0130 0.0000  -1.7229 unknown    -0.9590      0.0034     unknown
       bubble_curtain      low  233     224 unknown -0.9985 -0.9988 -0.9981 0.0005  -0.0051   0.0093 0.0001  -1.9338 unknown    -0.9988     -0.0011     unknown
            hurricane     high  210     203 unknown  0.4024  0.2710  0.5654 0.9522   0.9357   0.9634 0.0000  -0.1515 unknown     0.0770     -0.0172     unknown
            hurricane      low  236     231 unknown  0.3031  0.2685  0.3265 0.9982   0.9979   0.9985 0.0000  -0.1470 unknown     0.0920      0.8955     unknown
large_commercial_ship     high  239     229 unknown -0.6843 -0.7388 -0.6306 0.4141   0.3663   0.4548 0.0000  -1.2094 unknown    -0.6745      0.3799     unknown
large_commercial_ship      low  202     196 unknown -0.9743 -0.9871 -0.9684 0.0907   0.0683   0.1231 0.0004  -1.8572 unknown    -0.9637      0.1340     unknown
            lightning     high  249     245 unknown -0.8068 -0.8349 -0.7789 0.0837   0.0730   0.0962 0.0000  -1.4426 unknown    -0.8548      0.0809     unknown
            lightning      low  210     206 unknown -0.9912 -0.9930 -0.9877 0.0091  -0.0057   0.0254 0.0001  -1.9168 unknown    -0.9921      0.0070     unknown
             rainfall     high  244     236 unknown -0.7714 -0.8013 -0.7348 0.2997   0.2783   0.3143 0.0000  -1.3111 unknown    -0.8478      0.2864     unknown
             rainfall      low  214     203 unknown -0.9915 -0.9924 -0.9851 0.0214   0.0062   0.0335 0.0003  -1.9056 unknown    -0.9916      0.0020     unknown
```