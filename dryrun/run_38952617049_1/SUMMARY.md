# Pilot summary (exploratory)

Means over worlds and both overlap conditions, final test. E5 = correct rejections; uncertain and other answers are not rejections. Trunc = share of answers cut off by the token limit. Format = share of all answers (both test points) inside the answer grammar (any category but 'other'), descriptive only; the scoring stays strict. O1 is diagnostic (evaluator-supplied evidence for every question; for lures three confusable notes, so the note count can signal a lure): its E5 and E6 columns are no memory results. A0 is the missing-evidence control with requested abstention.

| model | arm | worlds | E2 | E3a | E3b at_day | E3b latest | E4 | E5 | E7 | E5 false recall | E5 uncertain | E5 other | format | trunc | E6 phase1 | E6 final high | E6 final low |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| smollm2-135m | A0 | 1 | 0.00 | 0.38 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.13 | 0.31 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | A1 | 1 | 0.00 | 0.25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.00 | 0.97 | 0.14 | 0.67 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | O1 (diagnostic) | 1 | 0.00 | 0.62 | 0.50 | 0.12 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.16 | 0.43 | 0.00 | 0.00 | 0.00 |

## Model selection (protocol section 5): O1 on positive items only

Per world: share correct over final-test items E2, E3a, E3b, E4, E7 of both conditions (E5 lures excluded). Threshold 0.8.

| model | worlds | mean | min world | meets threshold |
|---|---|---|---|---|
| smollm2-135m | 1 | 0.149 | 0.149 | no |
