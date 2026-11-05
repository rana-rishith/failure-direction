# probe report: b3_anthro_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.5574 -0.6070 -0.4725  0.3175   0.2585   0.4030 0.0000  -1.1636 active_balanced    -0.0023      0.3584 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9737 -0.9785 -0.9661  0.2021   0.1612   0.2319 0.0003  -1.7791 active_balanced    -0.7846      0.2765 active_balanced
       bubble_curtain     high  243     232    R1  0.4790  0.4547  0.5289  0.9744   0.9688   0.9786 0.0000  -0.2381 active_balanced     0.4739      0.9739 active_balanced
       bubble_curtain      low  233     224    R1  0.5628  0.5433  0.5781  0.9987   0.9984   0.9989 0.0001  -0.1175 active_balanced     0.5578      0.9987 active_balanced
            hurricane     high  210     203    R4 -0.8734 -0.8971 -0.8406  0.0541   0.0417   0.0677 0.0000  -1.7228           inert     0.6097      0.0542 active_balanced
            hurricane      low  236     231    R4 -0.9977 -0.9979 -0.9973  0.0018  -0.0015   0.0051 0.0001  -1.8296           inert    -0.7880      0.1961           inert
large_commercial_ship     high  239     229    R1  0.2001  0.1771  0.2240  0.9053   0.8924   0.9203 0.0001  -0.2140            over     0.1518      0.8667            over
large_commercial_ship      low  202     196    R1 -0.1254 -0.1780 -0.0888  0.9653   0.9620   0.9704 0.0003  -0.1362            over    -0.1630      0.9499            over
            lightning     high  249     245    R4 -0.7661 -0.8035 -0.7391  0.2953   0.2684   0.3175 0.0000  -1.4491 active_balanced    -0.7934      0.2930 active_balanced
            lightning      low  210     206    R4 -0.9893 -0.9911 -0.9870  0.2077   0.1905   0.2221 0.0012  -1.9141 active_balanced    -0.9913      0.2040 active_balanced
             rainfall     high  244     236    R4 -0.8498 -0.8628 -0.8290  0.0973   0.0914   0.1033 0.0000  -1.4823           inert    -0.8614      0.0812           inert
             rainfall      low  214     203    R4 -0.9884 -0.9900 -0.9819 -0.0585  -0.0948  -0.0263 0.0005  -1.8959           inert    -0.9889     -0.0860           inert
```