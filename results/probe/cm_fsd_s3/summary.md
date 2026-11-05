# probe report: cm_fsd_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.0166 -0.0400  0.0100 0.7549   0.7453   0.7632 2.1237  -1.7510 unknown    -0.0787      0.6665     unknown
               POOLED      low 1095     864 unknown -0.2735 -0.3075 -0.2297 0.9510   0.9444   0.9582 1.6152  -1.8376 unknown    -0.2990      0.8977     unknown
       bubble_curtain     high  243     232 unknown -0.3876 -0.4896 -0.2875 0.5544   0.5018   0.6102 2.1859  -1.8476 unknown    -0.5431      0.5478     unknown
       bubble_curtain      low  233     224 unknown  0.0661  0.0088  0.1270 0.9941   0.9930   0.9946 2.1808  -1.9179 unknown     0.0308      0.9941     unknown
            hurricane     high  210     203 unknown  0.4839  0.4030  0.5857 0.8816   0.8247   0.9184 2.2063  -1.8788 unknown     0.3021     -6.1488     unknown
            hurricane      low  236     231 unknown  0.3515  0.3084  0.3794 0.9973   0.9969   0.9978 2.3275  -1.8335 unknown     0.1188      0.7894     unknown
large_commercial_ship     high  239     229 unknown -0.1394 -0.1851 -0.0847 0.7552   0.7374   0.7720 2.1031  -1.6920 unknown    -0.2100      0.6819     unknown
large_commercial_ship      low  202     196 unknown -0.6199 -0.7028 -0.5712 0.8716   0.8544   0.8947 0.8560  -1.8336 unknown    -0.5962      0.8356     unknown
            lightning     high  249     245 unknown  0.0491  0.0127  0.0899 0.7646   0.7496   0.7843 2.0395  -1.7116 unknown    -0.0347      0.7643     unknown
            lightning      low  210     206 unknown -0.3469 -0.3930 -0.2910 0.9383   0.9284   0.9473 1.0673  -1.7880 unknown    -0.3742      0.9389     unknown
             rainfall     high  244     236 unknown -0.0063 -0.0366  0.0277 0.7578   0.7448   0.7732 2.0699  -1.6682 unknown    -0.0666      0.7583     unknown
             rainfall      low  214     203 unknown -0.7203 -0.7805 -0.6116 0.8606   0.8490   0.8690 0.6059  -1.8035 unknown    -0.7174      0.8606     unknown
```