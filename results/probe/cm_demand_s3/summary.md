# probe report: cm_demand_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.6787 -0.7009 -0.6437  0.4079   0.3901   0.4293 1.1378  -1.7529 unknown    -0.7084      0.3181     unknown
               POOLED      low 1095     864 unknown -0.9824 -0.9855 -0.9789  0.1629   0.1468   0.1812 2.3880  -1.9173 unknown    -0.9819      0.1706     unknown
       bubble_curtain     high  243     232 unknown -0.9199 -0.9315 -0.9101 -0.0006  -0.0064   0.0077 1.1849  -1.8510 unknown    -0.9446     -0.0033     unknown
       bubble_curtain      low  233     224 unknown -0.9967 -0.9976 -0.9963  0.0291   0.0121   0.0473 5.6963  -1.9375 unknown    -0.9971      0.0306     unknown
            hurricane     high  210     203 unknown  0.2712  0.0797  0.4056  0.9018   0.8684   0.9322 1.1455  -1.8795 unknown    -0.0163     -1.3726     unknown
            hurricane      low  236     231 unknown  0.3925  0.3576  0.4261  0.9987   0.9984   0.9988 1.1474  -1.8323 unknown     0.1068      0.8884     unknown
large_commercial_ship     high  239     229 unknown -0.5467 -0.5992 -0.4908  0.5785   0.5443   0.5983 1.1286  -1.6933 unknown    -0.4853      0.5551     unknown
large_commercial_ship      low  202     196 unknown -0.9744 -0.9857 -0.9692 -0.0468  -0.1093   0.0335 2.4715  -1.9261 unknown    -0.9605      0.0713     unknown
            lightning     high  249     245 unknown -0.6451 -0.6839 -0.6069  0.4416   0.4045   0.4769 1.1197  -1.7144 unknown    -0.6853      0.4432     unknown
            lightning      low  210     206 unknown -0.9819 -0.9867 -0.9782  0.2546   0.2257   0.2917 2.4402  -1.9289 unknown    -0.9829      0.2552     unknown
             rainfall     high  244     236 unknown -0.7434 -0.7821 -0.7139  0.3631   0.3337   0.3752 1.1302  -1.6710 unknown    -0.7902      0.3493     unknown
             rainfall      low  214     203 unknown -0.9906 -0.9923 -0.9834 -0.0164  -0.0450   0.0052 6.9304  -1.9168 unknown    -0.9910     -0.0367     unknown
```