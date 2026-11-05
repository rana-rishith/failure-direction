# probe report: b3_fsd_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.2036 -0.2378 -0.1749 0.5349   0.5150   0.5544 0.0000  -0.5672 unknown    -0.1715      0.4534     unknown
               POOLED      low 1095     864 unknown -0.4352 -0.4759 -0.3905 0.9195   0.9016   0.9312 0.0000  -0.3196 unknown    -0.4324      0.8379     unknown
       bubble_curtain     high  243     232 unknown -0.2016 -0.3384 -0.0841 0.3804   0.2870   0.5189 0.0000  -0.8068 unknown    -0.2695      0.3721     unknown
       bubble_curtain      low  233     224 unknown  0.0446 -0.0594  0.1455 0.9824   0.9791   0.9846 0.0000  -0.4539 unknown     0.0238      0.9823     unknown
            hurricane     high  210     203 unknown  0.2865  0.1474  0.4396 0.7011   0.6211   0.7613 0.0000  -0.2958 unknown     0.6469     -3.4299     unknown
            hurricane      low  236     231 unknown  0.3065  0.2437  0.3802 0.9965   0.9951   0.9971 0.0000  -0.0683 unknown     0.1671      0.7602     unknown
large_commercial_ship     high  239     229 unknown -0.3981 -0.4817 -0.3481 0.4305   0.3951   0.4573 0.0000  -0.7699 unknown    -0.3346      0.4283     unknown
large_commercial_ship      low  202     196 unknown -0.7862 -0.8173 -0.7218 0.7387   0.7123   0.7682 0.0001  -0.6537 unknown    -0.7478      0.6817     unknown
            lightning     high  249     245 unknown -0.2493 -0.3065 -0.2038 0.4959   0.4749   0.5281 0.0000  -0.6292 unknown    -0.2961      0.4965     unknown
            lightning      low  210     206 unknown -0.4581 -0.4996 -0.4133 0.8994   0.8826   0.9165 0.0000  -0.2828 unknown    -0.4685      0.9019     unknown
             rainfall     high  244     236 unknown -0.1824 -0.2088 -0.1360 0.6614   0.6416   0.6834 0.0000  -0.4702 unknown    -0.1987      0.6631     unknown
             rainfall      low  214     203 unknown -0.7824 -0.8343 -0.6507 0.7940   0.7782   0.8041 0.0000  -0.3638 unknown    -0.7736      0.7962     unknown
```