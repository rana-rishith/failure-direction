"""Baseline 3 — spectral/generative (SGMSE-style score-based diffusion).

Deliberately NOT implemented here. It is the one baseline that does not fit the
12 GB local card comfortably, and a half-working local copy is worse than none.

Two honest options, decide before Stage 1 rather than during:

* rent an A100/L40S, run the reference SGMSE+ implementation unmodified on two
  folds, and cite it as an external baseline;
* substitute a lighter spectral model (e.g. a complex-masking CNN) and say so
  explicitly in the paper, framing the generative family as future work.

Either is defensible. Silently training a shrunken diffusion model and calling
it SGMSE is not.
"""

RATIONALE = __doc__
