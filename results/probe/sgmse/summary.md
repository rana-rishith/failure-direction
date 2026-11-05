# probe report: sgmse

- split `marven_test_v1` n=400 sha256 `73d68b28e52518a2...` - **partial coverage: 400 of 2280 (17.5%)**, medians cover only those rows
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band   n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 200     188 unknown  0.2915  0.2148  0.3317 0.9107   0.8900   0.9168 0.0010  -0.1704 unknown     0.1562      0.8558     unknown
               POOLED      low 200     192 unknown -0.1607 -0.2970 -0.0363 0.9758   0.9623   0.9797 0.0098  -0.5081 unknown    -0.2547      0.9359     unknown
       bubble_curtain     high  40      39 unknown  0.3493  0.2944  0.3904 0.9469   0.9057   0.9663 0.0009  -0.3480 unknown     0.2415      0.9464     unknown
       bubble_curtain      low  40      40 unknown  0.3441  0.1668  0.4788 0.9980   0.9974   0.9984 0.0032  -0.3723 unknown     0.3784      0.9983     unknown
            hurricane     high  40      40 unknown  0.4897  0.3988  0.7178 0.9231   0.9040   0.9593 0.0002  -0.0818 unknown     0.4362     -2.4198     unknown
            hurricane      low  40      40 unknown  0.3835  0.2497  0.4680 0.9986   0.9962   0.9991 0.0007  -0.0828 unknown     0.0544      0.8909     unknown
large_commercial_ship     high  40      40 unknown  0.2067  0.1352  0.3478 0.8743   0.8269   0.9177 0.0030  -0.0964 unknown     0.0876      0.8329     unknown
large_commercial_ship      low  40      40 unknown -0.1397 -0.3343 -0.0185 0.9629   0.9449   0.9765 0.0141  -0.2719 unknown    -0.1526      0.9477     unknown
            lightning     high  40      40 unknown  0.2090  0.0866  0.2928 0.9122   0.8765   0.9267 0.0019  -0.1986 unknown     0.1016      0.9136     unknown
            lightning      low  40      40 unknown -0.8557 -0.8923 -0.6867 0.8463   0.7965   0.8794 0.0309  -1.6525 unknown    -0.8647      0.8451     unknown
             rainfall     high  40      40 unknown  0.1426  0.0173  0.2749 0.8736   0.8465   0.9014 0.0014  -0.2050 unknown    -0.0068      0.8735     unknown
             rainfall      low  40      40 unknown -0.5555 -0.8102 -0.4235 0.9089   0.6718   0.9478 0.0173  -1.1769 unknown    -0.5842      0.9066     unknown
```