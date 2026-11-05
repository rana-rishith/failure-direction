# probe report: b1_fsd_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.0301 -0.0564  0.0070 0.7873   0.7768   0.7962 0.0000  -0.4654 unknown    -0.0583      0.7276     unknown
               POOLED      low 1095     864 unknown -0.1798 -0.2344 -0.1226 0.9566   0.9467   0.9643 0.0001  -0.2326 unknown    -0.2253      0.9095     unknown
       bubble_curtain     high  243     232 unknown -0.3296 -0.4568 -0.1796 0.6281   0.5604   0.7286 0.0000  -0.9831 unknown    -0.4549      0.6226     unknown
       bubble_curtain      low  233     224 unknown  0.3493  0.2941  0.4058 0.9965   0.9960   0.9968 0.0000  -0.2153 unknown     0.3205      0.9964     unknown
            hurricane     high  210     203 unknown  0.5449  0.4313  0.6588 0.9105   0.8820   0.9445 0.0000  -0.0571 unknown     0.5696     -1.2943     unknown
            hurricane      low  236     231 unknown  0.4595  0.4129  0.4905 0.9984   0.9980   0.9987 0.0000  -0.0242 unknown     0.1795      0.8648     unknown
large_commercial_ship     high  239     229 unknown -0.0960 -0.1413 -0.0343 0.7934   0.7689   0.8099 0.0000  -0.4533 unknown    -0.0972      0.7414     unknown
large_commercial_ship      low  202     196 unknown -0.6430 -0.7001 -0.5804 0.8733   0.8633   0.8898 0.0001  -0.5658 unknown    -0.6253      0.8327     unknown
            lightning     high  249     245 unknown  0.0203 -0.0301  0.0808 0.7872   0.7736   0.8042 0.0000  -0.3995 unknown    -0.0373      0.7867     unknown
            lightning      low  210     206 unknown -0.2541 -0.2938 -0.2136 0.9480   0.9379   0.9555 0.0001  -0.1714 unknown    -0.2685      0.9476     unknown
             rainfall     high  244     236 unknown -0.0648 -0.0969 -0.0351 0.7845   0.7680   0.7971 0.0000  -0.4881 unknown    -0.1065      0.7873     unknown
             rainfall      low  214     203 unknown -0.6064 -0.6611 -0.5261 0.8733   0.8614   0.8835 0.0001  -0.3140 unknown    -0.5963      0.8734     unknown
```