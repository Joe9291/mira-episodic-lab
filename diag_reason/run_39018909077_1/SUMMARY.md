# Round 3.1 diagnostic battery (exploratory)

Development target per sub-skill and channel: 0.95. Below target -> the prototype solves that sub-skill with an explicit operator (docs/STRATEGY.md).
free = generated text, strict grammar; cand = highest-likelihood allowed answer.
Modes: direct (no reasoning), think (Qwen3 thinking mode), cot (step-by-step instruction); reasoning modes have no candidate channel.

| model | mode | skill | n | free | cand | free by kind | cand by kind | pairs | meets target |
|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-0.5b | cot | S2 | 40 | 0.00 | - | content 0.00, letter 0.00 | - | free content 0.00, letter 0.00 | no |
| qwen2.5-0.5b | cot | S3 | 20 | 0.00 | - | lure 0.00, positive 0.00 | - |  | no |
| qwen2.5-0.5b | cot | S4 | 20 | 0.00 | - | link 0.00 | - |  | no |
| qwen2.5-0.5b | cot | S5 | 21 | 0.00 | - | missing 0.00, observed 0.00, reported 0.00 | - |  | no |
| qwen3-0.6b | cot | S2 | 40 | 0.45 | - | content 0.45, letter 0.45 | - | free content 0.00, letter 0.20 | no |
| qwen3-0.6b | cot | S3 | 20 | 0.40 | - | lure 0.10, positive 0.70 | - |  | no |
| qwen3-0.6b | cot | S4 | 20 | 0.00 | - | link 0.00 | - |  | no |
| qwen3-0.6b | cot | S5 | 21 | 0.62 | - | missing 0.57, observed 0.86, reported 0.43 | - |  | no |
| qwen3-0.6b | think | S2 | 40 | 0.82 | - | content 0.90, letter 0.75 | - | free content 0.90, letter 0.60 | no |
| qwen3-0.6b | think | S3 | 20 | 0.75 | - | lure 0.60, positive 0.90 | - |  | no |
| qwen3-0.6b | think | S4 | 20 | 0.60 | - | link 0.60 | - |  | no |
| qwen3-0.6b | think | S5 | 21 | 0.95 | - | missing 1.00, observed 0.86, reported 1.00 | - |  | free |
