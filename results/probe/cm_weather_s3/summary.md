# probe report: cm_weather_s3

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d             class  d_g_hp100  nr_g_hp100       class_hp100
               POOLED     high 1185     909 R1/R4  0.0710  0.0256  0.1005  0.8200   0.7948   0.8391 0.6110  -1.7455 hallucinate+inert    -0.2004      0.5480 hallucinate+inert
               POOLED      low 1095     864 R1/R4 -0.2786 -0.3570 -0.2268  0.9682   0.9654   0.9718 0.6657  -1.8363 hallucinate+inert    -0.4005      0.9077 hallucinate+inert
       bubble_curtain     high  243     232    R4 -0.9329 -0.9483 -0.9161  0.0077   0.0055   0.0105 0.6498  -1.8508 hallucinate+inert    -0.9493      0.0072 hallucinate+inert
       bubble_curtain      low  233     224    R4 -0.9983 -0.9986 -0.9980 -0.0082  -0.0134  -0.0031 5.0742  -1.9374 hallucinate+inert    -0.9984     -0.0091 hallucinate+inert
            hurricane     high  210     203    R1  0.5477  0.4786  0.6263  0.9786   0.9692   0.9852 0.6596  -1.8788  hallucinate+over    -0.2954     -0.5107  hallucinate+over
            hurricane      low  236     231    R1  0.3303  0.2911  0.3880  0.9990   0.9989   0.9991 0.6656  -1.8289       hallucinate    -0.1252      0.9114 hallucinate+inert
large_commercial_ship     high  239     229    R4 -0.7666 -0.7959 -0.7447  0.3580   0.3459   0.3660 0.6169  -1.6939 hallucinate+inert    -0.6470      0.4970 hallucinate+inert
large_commercial_ship      low  202     196    R4 -0.9648 -0.9822 -0.9575  0.1916   0.1160   0.2362 1.2055  -1.9222 hallucinate+inert    -0.9333      0.3995 hallucinate+inert
            lightning     high  249     245    R1  0.2668  0.2459  0.2860  0.9281   0.9173   0.9371 0.5874  -1.7115 hallucinate+inert     0.2702      0.9285 hallucinate+inert
            lightning      low  210     206    R1  0.0767  0.0221  0.1016  0.9841   0.9823   0.9855 0.4400  -1.7066  hallucinate+over     0.0804      0.9844  hallucinate+over
             rainfall     high  244     236    R1  0.1851  0.1690  0.1979  0.8862   0.8755   0.8938 0.5855  -1.6671 hallucinate+inert     0.1780      0.8865 hallucinate+inert
             rainfall      low  214     203    R1 -0.1760 -0.2313 -0.1113  0.9714   0.9692   0.9728 0.4335  -1.7122  hallucinate+over    -0.1789      0.9712  hallucinate+over
```