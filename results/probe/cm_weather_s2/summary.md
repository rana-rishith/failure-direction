# probe report: cm_weather_s2

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4  0.0304 -0.0103  0.0578  0.8361   0.8093   0.8539 0.7466  -1.7511 hallucinate+inert    -0.2567      0.5800 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.2929 -0.3815 -0.2211  0.9687   0.9653   0.9718 0.8008  -1.8403 hallucinate+inert    -0.3879      0.9143 hallucinate+inert
       bubble_curtain     high  243     232    R4 -0.9306 -0.9513 -0.9182 -0.0011  -0.0036   0.0003 0.8058  -1.8509 hallucinate+inert    -0.9559     -0.0057 hallucinate+inert
       bubble_curtain      low  233     224    R4 -0.9986 -0.9988 -0.9982 -0.0090  -0.0142  -0.0044 6.3465  -1.9375 hallucinate+inert    -0.9987     -0.0104 hallucinate+inert
            hurricane     high  210     203    R1  0.6392  0.5263  0.6835  0.9805   0.9726   0.9877 0.8007  -1.8797  hallucinate+over    -0.3523     -0.2246  hallucinate+over
            hurricane      low  236     231    R1  0.4124  0.3666  0.4481  0.9991   0.9989   0.9992 0.8002  -1.8297       hallucinate    -0.0348      0.9193 hallucinate+inert
large_commercial_ship     high  239     229    R4 -0.7439 -0.7718 -0.7277  0.3924   0.3851   0.3996 0.7516  -1.6947 hallucinate+inert    -0.5996      0.5420 hallucinate+inert
large_commercial_ship      low  202     196    R4 -0.9632 -0.9820 -0.9576  0.1713   0.0989   0.2234 1.5026  -1.9234 hallucinate+inert    -0.9274      0.4154 hallucinate+inert
            lightning     high  249     245    R1  0.2478  0.2238  0.2699  0.9310   0.9199   0.9393 0.7166  -1.7114 hallucinate+inert     0.2522      0.9310 hallucinate+inert
            lightning      low  210     206    R1  0.0600  0.0254  0.1043  0.9847   0.9829   0.9860 0.5305  -1.7555  hallucinate+over     0.0726      0.9849  hallucinate+over
             rainfall     high  244     236    R1  0.0843  0.0650  0.0965  0.8859   0.8750   0.8940 0.6993  -1.6687 hallucinate+inert     0.0706      0.8858 hallucinate+inert
             rainfall      low  214     203    R1 -0.2040 -0.2580 -0.1874  0.9710   0.9687   0.9723 0.4914  -1.7381  hallucinate+over    -0.2178      0.9709  hallucinate+over
```