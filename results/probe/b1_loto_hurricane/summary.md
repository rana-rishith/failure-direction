# probe report: b1_loto_hurricane

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6959 -0.7353 -0.6120  0.3751   0.3494   0.3983 0.0000  -1.2397 active_balanced    -0.1026      0.5292 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9831 -0.9875 -0.9620  0.0869   0.0481   0.1941 0.0003  -1.7754 active_balanced    -0.8622      0.3471 active_balanced
       bubble_curtain     high  243     232    R4 -0.9538 -0.9625 -0.9437  0.0104   0.0090   0.0116 0.0000  -1.7814           inert    -0.9561      0.0106           inert
       bubble_curtain      low  233     224    R4 -0.9988 -0.9989 -0.9984  0.0030  -0.0009   0.0082 0.0000  -1.9341           inert    -0.9988      0.0031           inert
            hurricane     high  210     203    R4 -0.9592 -0.9692 -0.9455 -0.0080  -0.0089  -0.0074 0.0000  -1.8003           inert    -0.1787      0.0703           inert
            hurricane      low  236     231    R4 -0.9986 -0.9988 -0.9984 -0.0086  -0.0095  -0.0076 0.0000  -1.8292           inert    -0.8948      0.0539           inert
large_commercial_ship     high  239     229    R4 -0.7543 -0.7786 -0.7215  0.3563   0.3484   0.3685 0.0001  -1.3492 active_balanced    -0.6037      0.5157 active_balanced
large_commercial_ship      low  202     196    R4 -0.9667 -0.9837 -0.9611  0.1576   0.0987   0.2121 0.0010  -1.8445 active_balanced    -0.9360      0.4048 active_balanced
            lightning     high  249     245    R1  0.4370  0.4279  0.4530  0.9505   0.9443   0.9566 0.0001   0.0247 active_balanced     0.4405      0.9511 active_balanced
            lightning      low  210     206    R1  0.1984  0.1586  0.2293  0.9896   0.9885   0.9908 0.0005  -0.0225 active_balanced     0.2002      0.9897 active_balanced
             rainfall     high  244     236    R1  0.3013  0.2887  0.3166  0.9292   0.9218   0.9354 0.0000   0.0037            over     0.2975      0.9307            over
             rainfall      low  214     203    R1 -0.0255 -0.0631  0.0271  0.9837   0.9826   0.9851 0.0005   0.0105            over    -0.0276      0.9837            over
```