# Round 3.1 diagnostic battery (exploratory)

Development target per sub-skill and channel: 0.95. Below target -> the prototype solves that sub-skill with an explicit operator (docs/STRATEGY.md).
free = generated text, strict grammar; cand = highest-likelihood allowed answer.
Modes: direct (no reasoning), think (Qwen3 thinking mode), cot (step-by-step instruction); reasoning modes have no candidate channel.

| model | mode | skill | n | free | cand | free by kind | cand by kind | pairs | meets target |
|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-0.5b | direct | S1 | 20 | 1.00 | 1.00 | day 1.00, object 1.00, person 1.00, place 1.00 | day 1.00, object 1.00, person 1.00, place 1.00 |  | free+cand |
| qwen2.5-0.5b | direct | S2 | 40 | 0.45 | 0.45 | content 0.40, letter 0.50 | content 0.40, letter 0.50 | free content 0.00, letter 0.00; cand content 0.00, letter 0.00 | no |
| qwen2.5-0.5b | direct | S3 | 20 | 0.40 | 0.30 | lure 0.00, positive 0.80 | lure 0.00, positive 0.60 |  | no |
| qwen2.5-0.5b | direct | S4 | 20 | 0.05 | 0.05 | link 0.05 | link 0.05 |  | no |
| qwen2.5-0.5b | direct | S5 | 21 | 0.52 | 0.52 | missing 0.00, observed 0.86, reported 0.71 | missing 0.00, observed 0.86, reported 0.71 |  | no |
| qwen3-0.6b | direct | S1 | 20 | 1.00 | 1.00 | day 1.00, object 1.00, person 1.00, place 1.00 | day 1.00, object 1.00, person 1.00, place 1.00 |  | free+cand |
| qwen3-0.6b | direct | S2 | 40 | 0.53 | 0.50 | content 0.55, letter 0.50 | content 0.50, letter 0.50 | free content 0.50, letter 0.00; cand content 0.40, letter 0.00 | no |
| qwen3-0.6b | direct | S3 | 20 | 0.35 | 0.40 | lure 0.10, positive 0.60 | lure 0.20, positive 0.60 |  | no |
| qwen3-0.6b | direct | S4 | 20 | 0.05 | 0.10 | link 0.05 | link 0.10 |  | no |
| qwen3-0.6b | direct | S5 | 21 | 0.48 | 0.48 | missing 0.29, observed 0.71, reported 0.43 | missing 0.29, observed 0.71, reported 0.43 |  | no |
