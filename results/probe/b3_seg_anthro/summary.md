# probe report: b3_seg_anthro

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6069 -0.6517 -0.5591  0.3234   0.2673   0.3971 0.0000  -1.2663 active_balanced    -0.3340      0.3382 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9741 -0.9774 -0.9688  0.1662   0.1423   0.2003 0.0004  -1.8172           inert    -0.9272      0.1760           inert
       bubble_curtain     high  243     232    R1 -0.1513 -0.2752 -0.0568  0.8988   0.8867   0.9148 0.0000  -0.9006 active_balanced    -0.1529      0.8992 active_balanced
       bubble_curtain      low  233     224    R1 -0.7952 -0.8566 -0.7455  0.9620   0.9525   0.9710 0.0002  -1.6940 active_balanced    -0.8112      0.9653 active_balanced
            hurricane     high  210     203    R4 -0.8788 -0.8999 -0.8386  0.0326   0.0257   0.0408 0.0000  -1.7337           inert     0.6341      0.0029           inert
            hurricane      low  236     231    R4 -0.9982 -0.9985 -0.9978 -0.0050  -0.0074  -0.0030 0.0000  -1.8289           inert    -0.8656      0.0516           inert
large_commercial_ship     high  239     229    R1  0.1196  0.0910  0.1374  0.8999   0.8846   0.9080 0.0001  -0.2941            over     0.0559      0.8550            over
large_commercial_ship      low  202     196    R1 -0.4988 -0.6148 -0.4049  0.9283   0.9211   0.9329 0.0006  -0.7153            over    -0.5161      0.8974            over
            lightning     high  249     245    R4 -0.7425 -0.7882 -0.7116  0.3048   0.2839   0.3327 0.0000  -1.4281 active_balanced    -0.7795      0.3023 active_balanced
            lightning      low  210     206    R4 -0.9889 -0.9915 -0.9858  0.1710   0.1591   0.1940 0.0014  -1.9139           inert    -0.9918      0.1671           inert
             rainfall     high  244     236    R4 -0.8311 -0.8467 -0.8159  0.1073   0.0976   0.1132 0.0000  -1.4651           inert    -0.8600      0.0908           inert
             rainfall      low  214     203    R4 -0.9845 -0.9866 -0.9784 -0.1192  -0.1628  -0.0731 0.0005  -1.8757            over    -0.9863     -0.1482            over
```