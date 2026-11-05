# probe report: cm_fsd

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base    rung     d_g  d_g_lo  d_g_hi   nr_g  nr_g_lo  nr_g_hi  r_add  delta_d   class  d_g_hp100  nr_g_hp100 class_hp100
               POOLED     high 1185     909 unknown  0.0433  0.0152  0.0640 0.7819   0.7703   0.7949 2.2712  -1.7520 unknown    -0.0611      0.7007     unknown
               POOLED      low 1095     864 unknown -0.2101 -0.2589 -0.1645 0.9550   0.9459   0.9646 1.7545  -1.8310 unknown    -0.2486      0.8983     unknown
       bubble_curtain     high  243     232 unknown -0.1221 -0.2086 -0.0223 0.6917   0.6491   0.7471 2.3117  -1.8476 unknown    -0.2615      0.6842     unknown
       bubble_curtain      low  233     224 unknown  0.2381  0.1875  0.2835 0.9954   0.9949   0.9961 2.3127  -1.9183 unknown     0.1986      0.9953     unknown
            hurricane     high  210     203 unknown  0.6065  0.4983  0.6413 0.8895   0.8607   0.9244 2.3686  -1.8790 unknown     0.3642     -5.4790     unknown
            hurricane      low  236     231 unknown  0.4369  0.3902  0.4533 0.9976   0.9970   0.9980 2.4496  -1.8336 unknown     0.2384      0.8036     unknown
large_commercial_ship     high  239     229 unknown  0.0068 -0.0345  0.0434 0.8132   0.7955   0.8275 2.2716  -1.6920 unknown    -0.1415      0.7303     unknown
large_commercial_ship      low  202     196 unknown -0.6033 -0.7067 -0.5584 0.8802   0.8637   0.8948 1.0508  -1.8505 unknown    -0.6336      0.8329     unknown
            lightning     high  249     245 unknown  0.0725  0.0522  0.1203 0.7756   0.7648   0.7960 2.2141  -1.7143 unknown    -0.0227      0.7739     unknown
            lightning      low  210     206 unknown -0.2691 -0.3245 -0.2181 0.9426   0.9376   0.9511 1.1561  -1.7625 unknown    -0.2951      0.9433     unknown
             rainfall     high  244     236 unknown -0.0409 -0.0686 -0.0006 0.7428   0.7299   0.7547 2.2111  -1.6690 unknown    -0.1331      0.7401     unknown
             rainfall      low  214     203 unknown -0.7167 -0.7741 -0.5908 0.8307   0.8138   0.8406 0.3596  -1.6483 unknown    -0.7058      0.8343     unknown
```