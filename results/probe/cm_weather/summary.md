# probe report: cm_weather

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4  0.0600 -0.0065  0.0968  0.8407   0.8166   0.8646 0.6588  -1.7465 hallucinate+inert    -0.1722      0.6204 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.2453 -0.3183 -0.1869  0.9710   0.9673   0.9737 0.7065  -1.8364 hallucinate+inert    -0.3392      0.9198 hallucinate+inert
       bubble_curtain     high  243     232    R4 -0.9427 -0.9553 -0.9294  0.0026   0.0002   0.0049 0.7030  -1.8509 hallucinate+inert    -0.9565      0.0012 hallucinate+inert
       bubble_curtain      low  233     224    R4 -0.9986 -0.9988 -0.9982 -0.0064  -0.0110  -0.0025 5.8107  -1.9375 hallucinate+inert    -0.9986     -0.0069 hallucinate+inert
            hurricane     high  210     203    R1  0.6286  0.5252  0.7174  0.9792   0.9696   0.9864 0.7028  -1.8787  hallucinate+over    -0.2891      0.0234  hallucinate+over
            hurricane      low  236     231    R1  0.4214  0.3801  0.4771  0.9991   0.9990   0.9993 0.7063  -1.8289       hallucinate    -0.0032      0.9217 hallucinate+inert
large_commercial_ship     high  239     229    R4 -0.7379 -0.7658 -0.7130  0.4027   0.3951   0.4125 0.6609  -1.6942 hallucinate+inert    -0.5716      0.5791 hallucinate+inert
large_commercial_ship      low  202     196    R4 -0.9573 -0.9800 -0.9486  0.1776   0.1164   0.2208 1.2717  -1.9208 hallucinate+inert    -0.9061      0.4883  hallucinate+over
            lightning     high  249     245    R1  0.3085  0.2832  0.3264  0.9343   0.9241   0.9454 0.6356  -1.7114 hallucinate+inert     0.3155      0.9345 hallucinate+inert
            lightning      low  210     206    R1  0.1136  0.0677  0.1444  0.9853   0.9836   0.9867 0.4798  -1.7158  hallucinate+over     0.1235      0.9857  hallucinate+over
             rainfall     high  244     236    R1  0.1693  0.1370  0.1868  0.8925   0.8795   0.9021 0.6183  -1.6681 hallucinate+inert     0.1597      0.8935 hallucinate+inert
             rainfall      low  214     203    R1 -0.1722 -0.2308 -0.0983  0.9731   0.9714   0.9747 0.4047  -1.6964  hallucinate+over    -0.1703      0.9731  hallucinate+over
```