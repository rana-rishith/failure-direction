# probe report: b1_anthro_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.5703 -0.6464 -0.5013  0.3913   0.3397   0.4658 0.0000  -0.9392 active_balanced     0.0297      0.3894 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9724 -0.9756 -0.9662  0.1727   0.1428   0.1961 0.0003  -1.7730 active_balanced    -0.8648      0.1806           inert
       bubble_curtain     high  243     232    R1  0.6075  0.5900  0.6315  0.9859   0.9833   0.9886 0.0000  -0.0533 active_balanced     0.6065      0.9859 active_balanced
       bubble_curtain      low  233     224    R1  0.6060  0.5890  0.6193  0.9990   0.9988   0.9992 0.0002  -0.0736 active_balanced     0.5892      0.9990 active_balanced
            hurricane     high  210     203    R4 -0.9194 -0.9448 -0.8960 -0.0030  -0.0065  -0.0008 0.0000  -1.6934           inert     0.3089     -0.0353           inert
            hurricane      low  236     231    R4 -0.9984 -0.9986 -0.9981  0.0041   0.0025   0.0067 0.0000  -1.8253           inert    -0.8748      0.0884           inert
large_commercial_ship     high  239     229    R1  0.2340  0.2130  0.2571  0.9293   0.9189   0.9377 0.0001   0.0470            over     0.1949      0.9010            over
large_commercial_ship      low  202     196    R1 -0.0428 -0.0838 -0.0050  0.9796   0.9770   0.9818 0.0005  -0.0792            over    -0.0969      0.9705            over
            lightning     high  249     245    R4 -0.7569 -0.8036 -0.7214  0.3716   0.3444   0.3917 0.0000  -1.3052 active_balanced    -0.7715      0.3685 active_balanced
            lightning      low  210     206    R4 -0.9904 -0.9923 -0.9874  0.1776   0.1700   0.1889 0.0005  -1.9137 active_balanced    -0.9924      0.1731 active_balanced
             rainfall     high  244     236    R4 -0.8520 -0.8728 -0.8309  0.1287   0.1228   0.1330 0.0000  -1.4056           inert    -0.8636      0.1100           inert
             rainfall      low  214     203    R4 -0.9850 -0.9860 -0.9783 -0.1059  -0.1714  -0.0560 0.0004  -1.8674            over    -0.9856     -0.1351            over
```