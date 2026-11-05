# probe report: b1_fsd

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown  0.0578  0.0305  0.0841 0.8085   0.7982   0.8197 0.0000  -0.3913 unknown    -0.0864      0.7380     unknown
               POOLED      low 1095     864 unknown -0.1087 -0.1532 -0.0618 0.9624   0.9565   0.9689 0.0001  -0.2050 unknown    -0.1551      0.9190     unknown
       bubble_curtain     high  243     232 unknown -0.0480 -0.1317  0.0673 0.7821   0.7298   0.8265 0.0000  -0.7227 unknown    -0.1745      0.7745     unknown
       bubble_curtain      low  233     224 unknown  0.4361  0.3940  0.4614 0.9968   0.9964   0.9971 0.0000  -0.1416 unknown     0.4150      0.9968     unknown
            hurricane     high  210     203 unknown  0.7829  0.6898  0.8352 0.9599   0.9393   0.9734 0.0000   0.0572 unknown     0.5849     -1.0838     unknown
            hurricane      low  236     231 unknown  0.4986  0.4518  0.5329 0.9986   0.9983   0.9988 0.0001   0.0010 unknown     0.2254      0.8820     unknown
large_commercial_ship     high  239     229 unknown  0.0648  0.0273  0.1054 0.8304   0.8196   0.8413 0.0001  -0.2794 unknown    -0.1046      0.7552     unknown
large_commercial_ship      low  202     196 unknown -0.4661 -0.5453 -0.3990 0.9007   0.8871   0.9165 0.0000  -0.3032 unknown    -0.5056      0.8625     unknown
            lightning     high  249     245 unknown  0.0641  0.0146  0.1211 0.8014   0.7902   0.8161 0.0000  -0.3714 unknown    -0.0483      0.8003     unknown
            lightning      low  210     206 unknown -0.2196 -0.2414 -0.1574 0.9543   0.9483   0.9596 0.0001  -0.1393 unknown    -0.2340      0.9542     unknown
             rainfall     high  244     236 unknown -0.1315 -0.1817 -0.1000 0.7505   0.7324   0.7659 0.0000  -0.5886 unknown    -0.2256      0.7452     unknown
             rainfall      low  214     203 unknown -0.6456 -0.6877 -0.5187 0.8737   0.8644   0.8834 0.0001  -0.4273 unknown    -0.6232      0.8796     unknown
```