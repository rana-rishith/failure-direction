# probe report: b1_fsd_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown  0.0728  0.0468  0.1071 0.8028   0.7971   0.8125 0.0000  -0.3546 unknown    -0.0712      0.7298     unknown
               POOLED      low 1095     864 unknown -0.1410 -0.2086 -0.0756 0.9607   0.9547   0.9687 0.0001  -0.1881 unknown    -0.2154      0.9186     unknown
       bubble_curtain     high  243     232 unknown  0.0383 -0.0779  0.1322 0.8111   0.7721   0.8537 0.0000  -0.6496 unknown    -0.1228      0.8062     unknown
       bubble_curtain      low  233     224 unknown  0.4860  0.4530  0.5275 0.9970   0.9965   0.9975 0.0000  -0.1045 unknown     0.4598      0.9969     unknown
            hurricane     high  210     203 unknown  0.8237  0.7636  0.8461 0.9630   0.9489   0.9739 0.0000   0.0612 unknown     0.5695     -1.4998     unknown
            hurricane      low  236     231 unknown  0.5243  0.4861  0.5626 0.9988   0.9984   0.9989 0.0001   0.0137 unknown     0.1598      0.8955     unknown
large_commercial_ship     high  239     229 unknown  0.1095  0.0793  0.1306 0.8370   0.8129   0.8540 0.0001  -0.2233 unknown    -0.0348      0.7627     unknown
large_commercial_ship      low  202     196 unknown -0.4807 -0.5301 -0.3814 0.9102   0.8982   0.9270 0.0001  -0.2842 unknown    -0.4879      0.8764     unknown
            lightning     high  249     245 unknown  0.0292 -0.0084  0.0616 0.7830   0.7701   0.7975 0.0000  -0.4286 unknown    -0.0928      0.7812     unknown
            lightning      low  210     206 unknown -0.3157 -0.3671 -0.2775 0.9487   0.9404   0.9549 0.0001  -0.2867 unknown    -0.3595      0.9483     unknown
             rainfall     high  244     236 unknown -0.1526 -0.1955 -0.1120 0.7263   0.7086   0.7439 0.0000  -0.5956 unknown    -0.2826      0.7241     unknown
             rainfall      low  214     203 unknown -0.6272 -0.6792 -0.5743 0.8696   0.8569   0.8772 0.0001  -0.3282 unknown    -0.6426      0.8684     unknown
```