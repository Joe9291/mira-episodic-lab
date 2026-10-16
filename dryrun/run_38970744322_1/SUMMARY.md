# Pilot summary (exploratory)

Variant: v1 (episodic_lab/variants.py).

E3a pairs (variant v1 only) = share of order pairs answered correctly in BOTH A/B orders. Baselines: constant letter 0, uniform guessing 0.25, 'the earlier (or later) told event happened first' 0.5.

Means over worlds and both overlap conditions, final test. E5 = correct rejections; uncertain and other answers are not rejections. Trunc = share of answers cut off by the token limit. Format = share of all answers (both test points) inside the answer grammar (any category but 'other'), descriptive only; the scoring stays strict. O1 is diagnostic (evaluator-supplied evidence for every question; for lures three confusable notes, so the note count can signal a lure): its E5 and E6 columns are no memory results. A0 is the missing-evidence control with requested abstention.

| model | arm | worlds | E2 | E3a | E3a pairs | E3b at_day | E3b latest | E4 | E5 | E7 | E5 false recall | E5 uncertain | E5 other | format | trunc | E6 phase1 | E6 final high | E6 final low |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| smollm2-135m | A0 | 1 | 0.00 | 0.19 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.09 | 0.67 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | A1 | 1 | 0.00 | 0.28 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 | 0.00 | 0.94 | 0.18 | 0.66 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | O1 (diagnostic) | 1 | 0.05 | 0.38 | 0.00 | 0.25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.12 | 0.00 | 0.88 | 0.24 | 0.57 | 0.03 | 0.03 | 0.03 |

## Model selection (protocol section 5): O1 on positive items only

Per world: share correct over final-test items E2, E3a, E3b, E4, E7 of both conditions (E5 lures excluded; the two A/B orientations of an E3a pair count 1/2 each). Threshold 0.8.

| model | worlds | mean | min world | meets threshold |
|---|---|---|---|---|
| smollm2-135m | 1 | 0.099 | 0.099 | no |
