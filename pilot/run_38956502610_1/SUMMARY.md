# Pilot summary (exploratory)

Means over worlds and both overlap conditions, final test. E5 = correct rejections; uncertain and other answers are not rejections. Trunc = share of answers cut off by the token limit. Format = share of all answers (both test points) inside the answer grammar (any category but 'other'), descriptive only; the scoring stays strict. O1 is diagnostic (evaluator-supplied evidence for every question; for lures three confusable notes, so the note count can signal a lure): its E5 and E6 columns are no memory results. A0 is the missing-evidence control with requested abstention.

| model | arm | worlds | E2 | E3a | E3b at_day | E3b latest | E4 | E5 | E7 | E5 false recall | E5 uncertain | E5 other | format | trunc | E6 phase1 | E6 final high | E6 final low |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-0.5b | A0 | 5 | 0.00 | 0.53 | 0.00 | 0.00 | 0.07 | 0.46 | 0.00 | 0.00 | 0.00 | 0.54 | 0.64 | 0.02 | 0.03 | 0.03 | 0.03 |
| qwen2.5-0.5b | A1 | 5 | 0.28 | 0.53 | 0.53 | 0.23 | 0.11 | 0.01 | 0.11 | 0.99 | 0.00 | 0.01 | 0.99 | 0.00 | 0.27 | 0.24 | 0.21 |
| qwen2.5-0.5b | O1 (diagnostic) | 5 | 0.99 | 0.50 | 1.00 | 0.97 | 1.00 | 0.00 | 0.56 | 0.97 | 0.00 | 0.03 | 0.99 | 0.00 | 0.99 | 0.99 | 0.99 |
| qwen3-0.6b | A0 | 5 | 0.00 | 0.53 | 0.00 | 0.00 | 0.00 | 0.89 | 0.00 | 0.00 | 0.00 | 0.11 | 0.94 | 0.00 | 0.00 | 0.00 | 0.00 |
| qwen3-0.6b | A1 | 5 | 0.23 | 0.53 | 0.10 | 0.05 | 0.20 | 0.65 | 0.04 | 0.34 | 0.00 | 0.01 | 0.99 | 0.00 | 0.28 | 0.22 | 0.22 |
| qwen3-0.6b | O1 (diagnostic) | 5 | 0.54 | 0.53 | 0.65 | 0.28 | 1.00 | 0.05 | 0.17 | 0.68 | 0.00 | 0.28 | 0.78 | 0.00 | 0.71 | 0.71 | 0.71 |
| smollm2-135m | A0 | 5 | 0.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.14 | 0.41 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | A1 | 5 | 0.00 | 0.39 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 | 0.00 | 0.94 | 0.15 | 0.51 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | O1 (diagnostic) | 5 | 0.05 | 0.45 | 0.00 | 0.05 | 0.00 | 0.00 | 0.02 | 0.06 | 0.00 | 0.94 | 0.18 | 0.49 | 0.03 | 0.03 | 0.03 |
| smollm2-360m | A0 | 5 | 0.00 | 0.53 | 0.00 | 0.00 | 0.05 | 0.69 | 0.00 | 0.00 | 0.00 | 0.31 | 0.67 | 0.02 | 0.02 | 0.02 | 0.02 |
| smollm2-360m | A1 | 5 | 0.01 | 0.53 | 0.00 | 0.03 | 0.00 | 0.08 | 0.00 | 0.17 | 0.00 | 0.74 | 0.27 | 0.39 | 0.02 | 0.01 | 0.00 |
| smollm2-360m | O1 (diagnostic) | 5 | 0.03 | 0.53 | 0.00 | 0.00 | 0.95 | 0.72 | 0.05 | 0.01 | 0.00 | 0.26 | 0.73 | 0.02 | 0.39 | 0.39 | 0.39 |

## Model selection (protocol section 5): O1 on positive items only

Per world: share correct over final-test items E2, E3a, E3b, E4, E7 of both conditions (E5 lures excluded). Threshold 0.8.

| model | worlds | mean | min world | meets threshold |
|---|---|---|---|---|
| qwen2.5-0.5b | 5 | 0.844 | 0.826 | yes |
| qwen3-0.6b | 5 | 0.557 | 0.500 | no |
| smollm2-135m | 5 | 0.109 | 0.067 | no |
| smollm2-360m | 5 | 0.298 | 0.216 | no |
