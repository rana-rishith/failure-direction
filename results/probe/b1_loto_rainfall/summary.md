# probe report: b1_loto_rainfall

- split `marven_test_v1` n=2280 sha256 `73d68b28e52518a2...`
- `class` is the registered 62.5 Hz basis (gate_universal.yaml, 29c1566);
  `class_hp100` is the 100 Hz band reported alongside it.
- CIs are 95% percentile bootstrap of the median, 2,000 resamples of base utterances.

```
           noise_type snr_band    n  n_base  rung     d_g  d_g_lo  d_g_hi    nr_g  nr_g_lo  nr_g_hi  r_add  delta_d           class  d_g_hp100  nr_g_hp100     class_hp100
               POOLED     high 1185     909 R1/R4 -0.6366 -0.6702 -0.6088  0.4771   0.4581   0.4943 0.0000  -1.2212 active_balanced    -0.6348      0.4872 active_balanced
               POOLED      low 1095     864 R1/R4 -0.9433 -0.9530 -0.9325  0.3033   0.2610   0.3375 0.0004  -1.7554            over    -0.9193      0.4191            over
       bubble_curtain     high  243     232    R4 -0.9297 -0.9438 -0.9144 -0.0010  -0.0026   0.0012 0.0000  -1.7657           inert    -0.9603     -0.0067           inert
       bubble_curtain      low  233     224    R4 -0.9987 -0.9989 -0.9982 -0.0090  -0.0131  -0.0059 0.0000  -1.9341           inert    -0.9988     -0.0120           inert
            hurricane     high  210     203    R1  0.7694  0.7175  0.8264  0.9852   0.9795   0.9903 0.0000   0.0323 active_balanced    -0.2304      0.1849 active_balanced
            hurricane      low  236     231    R1  0.5035  0.4730  0.5295  0.9992   0.9991   0.9994 0.0001  -0.0738 active_balanced     0.0772      0.9320 active_balanced
large_commercial_ship     high  239     229    R4 -0.7600 -0.7855 -0.7280  0.3585   0.3485   0.3666 0.0001  -1.4155 active_balanced    -0.6054      0.5161            over
large_commercial_ship      low  202     196    R4 -0.9612 -0.9813 -0.9558  0.1782   0.1335   0.2133 0.0012  -1.8497            over    -0.9298      0.4126            over
            lightning     high  249     245    R1  0.4356  0.4136  0.4552  0.9461   0.9394   0.9519 0.0001  -0.0636            over     0.4390      0.9464            over
            lightning      low  210     206    R1  0.1715  0.1262  0.2071  0.9876   0.9866   0.9891 0.0004  -0.0502            over     0.1758      0.9877            over
             rainfall     high  244     236    R4 -0.7121 -0.7323 -0.6894  0.4841   0.4743   0.4910 0.0000  -1.2951 active_balanced    -0.7187      0.4815            over
             rainfall      low  214     203    R4 -0.9876 -0.9906 -0.9799  0.0102  -0.0365   0.0487 0.0007  -1.8906            over    -0.9877     -0.0018            over
```