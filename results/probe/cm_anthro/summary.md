# probe report: cm_anthro

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4 -0.5504 -0.6287 -0.4703  0.4177   0.3500   0.4837 0.2109  -1.7357 hallucinate+inert    -0.1079      0.4197 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.9716 -0.9770 -0.9652  0.1460   0.1187   0.1799 0.3378  -1.8444 hallucinate+inert    -0.8006      0.1742 hallucinate+inert
       bubble_curtain     high  243     232    R1  0.3540  0.3104  0.3817  0.9786   0.9733   0.9823 0.2088  -1.8434  hallucinate+over     0.3558      0.9792  hallucinate+over
       bubble_curtain      low  233     224    R1  0.4962  0.4803  0.5163  0.9988   0.9987   0.9990 0.2076  -1.8118       hallucinate     0.4930      0.9989       hallucinate
            hurricane     high  210     203    R4 -0.9166 -0.9368 -0.8967  0.0325   0.0291   0.0367 0.2123  -1.8810  hallucinate+over     0.2236     -0.3240  hallucinate+over
            hurricane      low  236     231    R4 -0.9974 -0.9979 -0.9971  0.0331   0.0297   0.0380 0.4974  -1.8357 hallucinate+inert    -0.8100      0.0939 hallucinate+inert
large_commercial_ship     high  239     229    R1  0.2509  0.2295  0.2688  0.9285   0.9157   0.9350 0.2050  -1.6713 hallucinate+inert     0.1905      0.8982 hallucinate+inert
large_commercial_ship      low  202     196    R1 -0.0723 -0.1201 -0.0384  0.9760   0.9735   0.9775 0.1375  -1.4166  hallucinate+over    -0.1109      0.9654  hallucinate+over
            lightning     high  249     245    R4 -0.7322 -0.7907 -0.7073  0.3923   0.3653   0.4195 0.2131  -1.7090 hallucinate+inert    -0.7624      0.3915 hallucinate+inert
            lightning      low  210     206    R4 -0.9903 -0.9922 -0.9865  0.1567   0.1346   0.1690 0.7459  -1.9282 hallucinate+inert    -0.9924      0.1521 hallucinate+inert
             rainfall     high  244     236    R4 -0.8369 -0.8559 -0.8165  0.1285   0.1240   0.1333 0.2175  -1.6658 hallucinate+inert    -0.8583      0.1108 hallucinate+inert
             rainfall      low  214     203    R4 -0.9866 -0.9880 -0.9794 -0.1047  -0.1441  -0.0610 1.8538  -1.9122 hallucinate+inert    -0.9875     -0.1345 hallucinate+inert
```