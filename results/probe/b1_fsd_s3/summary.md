# probe report: b1_fsd_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.0301 -0.0520  0.0070 0.7873   0.7763   0.7959 0.0000  -0.4654 unknown    -0.0583      0.7276     unknown
               POOLED      low 1095     864 unknown -0.1798 -0.2337 -0.1231 0.9566   0.9473   0.9644 0.0001  -0.2326 unknown    -0.2253      0.9095     unknown
       bubble_curtain     high  243     232 unknown -0.3296 -0.4555 -0.1882 0.6281   0.5594   0.7286 0.0000  -0.9831 unknown    -0.4549      0.6226     unknown
       bubble_curtain      low  233     224 unknown  0.3493  0.2942  0.4106 0.9965   0.9960   0.9968 0.0000  -0.2153 unknown     0.3205      0.9964     unknown
            hurricane     high  210     203 unknown  0.5449  0.4435  0.6698 0.9105   0.8792   0.9445 0.0000  -0.0571 unknown     0.5696     -1.2943     unknown
            hurricane      low  236     231 unknown  0.4595  0.4105  0.4914 0.9984   0.9981   0.9987 0.0000  -0.0242 unknown     0.1795      0.8648     unknown
large_commercial_ship     high  239     229 unknown -0.0960 -0.1413 -0.0352 0.7934   0.7665   0.8074 0.0000  -0.4533 unknown    -0.0972      0.7414     unknown
large_commercial_ship      low  202     196 unknown -0.6430 -0.7001 -0.5798 0.8733   0.8633   0.8902 0.0001  -0.5658 unknown    -0.6253      0.8327     unknown
            lightning     high  249     245 unknown  0.0203 -0.0320  0.0785 0.7872   0.7746   0.8047 0.0000  -0.3995 unknown    -0.0373      0.7867     unknown
            lightning      low  210     206 unknown -0.2541 -0.2941 -0.2181 0.9480   0.9381   0.9553 0.0001  -0.1714 unknown    -0.2685      0.9476     unknown
             rainfall     high  244     236 unknown -0.0648 -0.0982 -0.0379 0.7845   0.7690   0.7973 0.0000  -0.4881 unknown    -0.1065      0.7873     unknown
             rainfall      low  214     203 unknown -0.6064 -0.6633 -0.5318 0.8733   0.8616   0.8826 0.0001  -0.3140 unknown    -0.5963      0.8734     unknown
```