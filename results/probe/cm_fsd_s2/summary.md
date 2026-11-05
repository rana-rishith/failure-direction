# probe report: cm_fsd_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown  0.0326  0.0080  0.0584 0.7755   0.7594   0.7866 2.0728  -1.7490 unknown    -0.0166      0.7147     unknown
               POOLED      low 1095     864 unknown -0.2137 -0.2629 -0.1706 0.9508   0.9401   0.9594 1.2949  -1.8040 unknown    -0.2425      0.8945     unknown
       bubble_curtain     high  243     232 unknown -0.0797 -0.1677  0.0334 0.7281   0.6711   0.7890 2.1382  -1.8471 unknown    -0.1381      0.7237     unknown
       bubble_curtain      low  233     224 unknown  0.3333  0.2900  0.3852 0.9956   0.9950   0.9959 2.0504  -1.9067 unknown     0.3077      0.9956     unknown
            hurricane     high  210     203 unknown  0.4663  0.3314  0.5493 0.8471   0.8002   0.8815 2.2111  -1.8783 unknown     0.3728     -4.6716     unknown
            hurricane      low  236     231 unknown  0.3913  0.3516  0.4174 0.9971   0.9966   0.9977 2.2450  -1.8334 unknown     0.2084      0.7804     unknown
large_commercial_ship     high  239     229 unknown  0.0248 -0.0016  0.0577 0.8046   0.7866   0.8249 2.0307  -1.6930 unknown    -0.0604      0.7305     unknown
large_commercial_ship      low  202     196 unknown -0.5992 -0.6293 -0.5502 0.8808   0.8636   0.8968 0.5359  -1.7631 unknown    -0.5910      0.8325     unknown
            lightning     high  249     245 unknown  0.1225  0.0803  0.1544 0.7731   0.7564   0.7887 1.9888  -1.7130 unknown     0.0523      0.7733     unknown
            lightning      low  210     206 unknown -0.3546 -0.3954 -0.2788 0.9366   0.9299   0.9417 0.8336  -1.7338 unknown    -0.3645      0.9366     unknown
             rainfall     high  244     236 unknown -0.0871 -0.1091 -0.0557 0.7394   0.7272   0.7524 1.9991  -1.6678 unknown    -0.1384      0.7373     unknown
             rainfall      low  214     203 unknown -0.7172 -0.7744 -0.5969 0.8456   0.8340   0.8584 0.2934  -1.6802 unknown    -0.7157      0.8446     unknown
```