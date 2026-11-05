# probe report: b3_anthro_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.4772 -0.5551 -0.4072  0.4146   0.3617   0.4895 0.0000  -1.1031 active_balanced    -0.0047      0.4150 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9682 -0.9741 -0.9618  0.3042   0.2471   0.3316 0.0003  -1.7754 active_balanced    -0.8000      0.3052 active_balanced
       bubble_curtain     high  243     232    R1  0.4617  0.4220  0.4964  0.9733   0.9687   0.9789 0.0000  -0.2737 active_balanced     0.4594      0.9729 active_balanced
       bubble_curtain      low  233     224    R1  0.5444  0.5251  0.5665  0.9986   0.9984   0.9987 0.0001  -0.1344 active_balanced     0.5406      0.9986 active_balanced
            hurricane     high  210     203    R4 -0.8624 -0.8992 -0.8047  0.0535   0.0432   0.0621 0.0000  -1.6943           inert     0.6566     -0.0058           inert
            hurricane      low  236     231    R4 -0.9976 -0.9980 -0.9970 -0.0015  -0.0050   0.0009 0.0001  -1.8285           inert    -0.8044      0.0984           inert
large_commercial_ship     high  239     229    R1  0.2193  0.1913  0.2377  0.9045   0.8973   0.9195 0.0001  -0.2210            over     0.1512      0.8682            over
large_commercial_ship      low  202     196    R1 -0.1918 -0.2544 -0.1636  0.9659   0.9620   0.9695 0.0004  -0.2440            over    -0.2341      0.9510            over
            lightning     high  249     245    R4 -0.7189 -0.7579 -0.6566  0.3968   0.3647   0.4201 0.0001  -1.3788 active_balanced    -0.7375      0.3935 active_balanced
            lightning      low  210     206    R4 -0.9856 -0.9878 -0.9802  0.3157   0.2976   0.3248 0.0016  -1.9008 active_balanced    -0.9879      0.3128 active_balanced
             rainfall     high  244     236    R4 -0.8283 -0.8494 -0.8124  0.1105   0.1016   0.1172 0.0000  -1.4613           inert    -0.8589      0.0925           inert
             rainfall      low  214     203    R4 -0.9866 -0.9881 -0.9806 -0.0626  -0.0938  -0.0131 0.0005  -1.8878           inert    -0.9870     -0.0910           inert
```