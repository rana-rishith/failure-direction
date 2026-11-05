# probe report: b1_anthro

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6116 -0.6746 -0.5231  0.3253   0.2784   0.3860 0.0000  -1.1566 active_balanced     0.0833      0.3234 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9769 -0.9813 -0.9713  0.0819   0.0680   0.0927 0.0002  -1.7828           inert    -0.8180      0.0884           inert
       bubble_curtain     high  243     232    R1  0.6867  0.6610  0.6995  0.9880   0.9860   0.9897 0.0000  -0.0676 active_balanced     0.6754      0.9884 active_balanced
       bubble_curtain      low  233     224    R1  0.6269  0.6106  0.6479  0.9991   0.9990   0.9992 0.0002  -0.0670 active_balanced     0.6172      0.9991 active_balanced
            hurricane     high  210     203    R4 -0.9100 -0.9254 -0.8799  0.0049   0.0010   0.0089 0.0000  -1.7467           inert     0.4740     -0.0156           inert
            hurricane      low  236     231    R4 -0.9979 -0.9981 -0.9975 -0.0228  -0.0247  -0.0214 0.0000  -1.8266           inert    -0.8237      0.0529           inert
large_commercial_ship     high  239     229    R1  0.2991  0.2763  0.3217  0.9343   0.9244   0.9412 0.0001   0.0083            over     0.2593      0.9084            over
large_commercial_ship      low  202     196    R1  0.0005 -0.0396  0.0360  0.9813   0.9787   0.9835 0.0005  -0.0474            over    -0.0342      0.9729            over
            lightning     high  249     245    R4 -0.7828 -0.8356 -0.7515  0.3018   0.2835   0.3262 0.0000  -1.4333 active_balanced    -0.8050      0.2978 active_balanced
            lightning      low  210     206    R4 -0.9923 -0.9940 -0.9902  0.0599   0.0495   0.0689 0.0003  -1.9203           inert    -0.9938      0.0557           inert
             rainfall     high  244     236    R4 -0.8624 -0.8789 -0.8478  0.1128   0.1097   0.1182 0.0000  -1.4726           inert    -0.8779      0.0981           inert
             rainfall      low  214     203    R4 -0.9888 -0.9896 -0.9838 -0.0359  -0.0745  -0.0047 0.0004  -1.8925           inert    -0.9891     -0.0625           inert
```