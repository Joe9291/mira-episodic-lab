# Pilot summary (exploratory)

Variant: v1 (episodic_lab/variants.py).

E3a pairs (variant v1 only) = share of order pairs answered correctly in BOTH A/B orders. Baselines: constant letter 0, uniform guessing 0.25, 'the earlier (or later) told event happened first' 0.5.

Means over worlds and both overlap conditions, final test. E5 = correct rejections; uncertain and other answers are not rejections. Trunc = share of answers cut off by the token limit. Format = share of all answers (both test points) inside the answer grammar (any category but 'other'), descriptive only; the scoring stays strict. O1 is diagnostic (evaluator-supplied evidence for every question; for lures three confusable notes, so the note count can signal a lure): its E5 and E6 columns are no memory results. A0 is the missing-evidence control with requested abstention.

| model | arm | worlds | E2 | E3a | E3a pairs | E3b at_day | E3b latest | E4 | E5 | E7 | E5 false recall | E5 uncertain | E5 other | format | trunc | E6 phase1 | E6 final high | E6 final low |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-0.5b | A0 | 5 | 0.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.03 | 0.81 | 0.00 | 0.00 | 0.00 | 0.19 | 0.79 | 0.01 | 0.01 | 0.01 | 0.01 |
| qwen2.5-0.5b | A1 | 5 | 0.29 | 0.50 | 0.00 | 0.45 | 0.28 | 0.11 | 0.00 | 0.12 | 0.99 | 0.00 | 0.01 | 0.99 | 0.00 | 0.26 | 0.21 | 0.25 |
| qwen2.5-0.5b | O1 (diagnostic) | 5 | 1.00 | 0.50 | 0.00 | 1.00 | 0.97 | 0.97 | 0.00 | 0.43 | 0.99 | 0.00 | 0.01 | 0.99 | 0.00 | 0.99 | 0.99 | 0.99 |
| qwen3-0.6b | A0 | 5 | 0.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| qwen3-0.6b | A1 | 5 | 0.27 | 0.50 | 0.00 | 0.10 | 0.07 | 0.21 | 0.63 | 0.00 | 0.35 | 0.00 | 0.02 | 0.99 | 0.00 | 0.26 | 0.22 | 0.26 |
| qwen3-0.6b | O1 (diagnostic) | 5 | 0.91 | 0.49 | 0.00 | 0.90 | 0.60 | 1.00 | 0.12 | 0.07 | 0.85 | 0.00 | 0.03 | 0.98 | 0.00 | 0.95 | 0.95 | 0.95 |
| smollm2-135m | A0 | 5 | 0.00 | 0.30 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.15 | 0.67 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | A1 | 5 | 0.00 | 0.34 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 | 0.00 | 0.94 | 0.20 | 0.53 | 0.00 | 0.00 | 0.00 |
| smollm2-135m | O1 (diagnostic) | 5 | 0.12 | 0.45 | 0.00 | 0.00 | 0.10 | 0.00 | 0.00 | 0.00 | 0.17 | 0.00 | 0.82 | 0.31 | 0.52 | 0.07 | 0.07 | 0.07 |
| smollm2-360m | A0 | 5 | 0.00 | 0.47 | 0.05 | 0.00 | 0.00 | 0.05 | 0.21 | 0.00 | 0.00 | 0.00 | 0.79 | 0.55 | 0.07 | 0.02 | 0.02 | 0.02 |
| smollm2-360m | A1 | 5 | 0.03 | 0.47 | 0.01 | 0.00 | 0.00 | 0.00 | 0.13 | 0.02 | 0.12 | 0.00 | 0.75 | 0.37 | 0.35 | 0.03 | 0.03 | 0.00 |
| smollm2-360m | O1 (diagnostic) | 5 | 0.49 | 0.50 | 0.00 | 0.50 | 0.35 | 0.95 | 0.28 | 0.42 | 0.34 | 0.00 | 0.39 | 0.77 | 0.03 | 0.66 | 0.66 | 0.66 |

## Model selection (protocol section 5): O1 on positive items only

Per world: share correct over final-test items E2, E3a, E3b, E4, E7 of both conditions (E5 lures excluded; the two A/B orientations of an E3a pair count 1/2 each). Threshold 0.8.

| model | worlds | mean | min world | meets threshold |
|---|---|---|---|---|
| qwen2.5-0.5b | 5 | 0.825 | 0.795 | yes |
| qwen3-0.6b | 5 | 0.713 | 0.667 | no |
| smollm2-135m | 5 | 0.131 | 0.093 | no |
| smollm2-360m | 5 | 0.547 | 0.465 | no |
