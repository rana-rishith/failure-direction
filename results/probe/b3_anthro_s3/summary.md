# probe report: b3_anthro_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.5574 -0.6068 -0.4787  0.3175   0.2533   0.4016 0.0000  -1.1636 active_balanced    -0.0023      0.3584 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9737 -0.9782 -0.9668  0.2021   0.1622   0.2346 0.0003  -1.7791 active_balanced    -0.7846      0.2765 active_balanced
       bubble_curtain     high  243     232    R1  0.4790  0.4547  0.5293  0.9744   0.9690   0.9787 0.0000  -0.2381 active_balanced     0.4739      0.9739 active_balanced
       bubble_curtain      low  233     224    R1  0.5628  0.5422  0.5787  0.9987   0.9984   0.9989 0.0001  -0.1175 active_balanced     0.5578      0.9987 active_balanced
            hurricane     high  210     203    R4 -0.8734 -0.8959 -0.8391  0.0541   0.0415   0.0676 0.0000  -1.7228           inert     0.6097      0.0542 active_balanced
            hurricane      low  236     231    R4 -0.9977 -0.9979 -0.9972  0.0018  -0.0014   0.0052 0.0001  -1.8296           inert    -0.7880      0.1961           inert
large_commercial_ship     high  239     229    R1  0.2001  0.1762  0.2257  0.9053   0.8918   0.9205 0.0001  -0.2140            over     0.1518      0.8667            over
large_commercial_ship      low  202     196    R1 -0.1254 -0.1806 -0.0879  0.9653   0.9617   0.9705 0.0003  -0.1362            over    -0.1630      0.9499            over
            lightning     high  249     245    R4 -0.7661 -0.8088 -0.7418  0.2953   0.2685   0.3174 0.0000  -1.4491 active_balanced    -0.7934      0.2930 active_balanced
            lightning      low  210     206    R4 -0.9893 -0.9910 -0.9869  0.2077   0.1901   0.2226 0.0012  -1.9141 active_balanced    -0.9913      0.2040 active_balanced
             rainfall     high  244     236    R4 -0.8498 -0.8611 -0.8272  0.0973   0.0914   0.1037 0.0000  -1.4823           inert    -0.8614      0.0812           inert
             rainfall      low  214     203    R4 -0.9884 -0.9900 -0.9821 -0.0585  -0.0940  -0.0253 0.0005  -1.8959           inert    -0.9889     -0.0860           inert
```