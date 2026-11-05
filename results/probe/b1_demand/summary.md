# probe report: b1_demand

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown -0.5290 -0.5665 -0.4781  0.5265   0.5018   0.5538 0.0000  -1.0628 unknown    -0.6143      0.4186     unknown
               POOLED      low 1095     864 unknown -0.9735 -0.9816 -0.9687  0.1542   0.1008   0.1937 0.0002  -1.8142 unknown    -0.9730      0.1723     unknown
       bubble_curtain     high  243     232 unknown -0.9270 -0.9400 -0.9154  0.0015  -0.0001   0.0052 0.0000  -1.7519 unknown    -0.9530     -0.0018     unknown
       bubble_curtain      low  233     224 unknown -0.9986 -0.9989 -0.9982 -0.0093  -0.0142  -0.0041 0.0001  -1.9338 unknown    -0.9988     -0.0112     unknown
            hurricane     high  210     203 unknown  0.3762  0.2123  0.5322  0.9478   0.9292   0.9638 0.0000  -0.1789 unknown     0.0271      0.1161     unknown
            hurricane      low  236     231 unknown  0.3738  0.3052  0.4177  0.9985   0.9978   0.9988 0.0001  -0.1426 unknown     0.1045      0.9134     unknown
large_commercial_ship     high  239     229 unknown -0.3565 -0.4234 -0.2866  0.6762   0.6441   0.7089 0.0001  -0.7046 unknown    -0.3186      0.6593     unknown
large_commercial_ship      low  202     196 unknown -0.9615 -0.9797 -0.9536  0.1492   0.0705   0.1979 0.0006  -1.7541 unknown    -0.9405      0.2340     unknown
            lightning     high  249     245 unknown -0.3931 -0.4364 -0.3308  0.6289   0.5977   0.6522 0.0001  -0.8400 unknown    -0.4764      0.6285     unknown
            lightning      low  210     206 unknown -0.9744 -0.9840 -0.9682  0.2517   0.2266   0.2853 0.0005  -1.8536 unknown    -0.9758      0.2529     unknown
             rainfall     high  244     236 unknown -0.6865 -0.7173 -0.6464  0.3754   0.3632   0.3900 0.0000  -1.2074 unknown    -0.7607      0.3656     unknown
             rainfall      low  214     203 unknown -0.9839 -0.9882 -0.9716 -0.1824  -0.3284  -0.0983 0.0003  -1.8202 unknown    -0.9849     -0.2097     unknown
```