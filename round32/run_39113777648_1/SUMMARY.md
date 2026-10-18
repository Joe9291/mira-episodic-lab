# Round 3.2 summary (exploratory, template benchmark)

**INCOMPLETE evaluation: only the valid world reports are tabulated, as diagnostics; no decision is drawn from them.**

Means over worlds (both overlap conditions pooled within a world). Development worlds (dev-m3) and the pilot worlds already used (pilot-m2) are shown separately. E5 = correct rejection of binding lures; FR = in-world false recall; unknown = abstention. Coverage = share of final items whose selection was certified sufficient for the question; accuracy covered = accuracy on those items, pooled over all covered final items of the series; gold support = share of positive items whose gold target episodes were all selected (evaluator information, not an upper bound of accuracy).

## dev-m3 (9 worlds)

| cell | positives | E2 | E3a | E3b | E4 | E5 | E7 | E3a pairs | E5 FR | E5 unknown | coverage | accuracy covered | gold support | calls | prompt tokens | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 0.10 | 0.00 | 0.50 | 0.00 | 0.03 | 0.72 | 0.00 | 0.00 | 0.00 | 0.00 | - | - | - | 2259 | 191432 | 1647 |
| A1 | 0.32 | 0.31 | 0.50 | 0.47 | 0.10 | 0.00 | 0.17 | 0.00 | 0.98 | 0.00 | - | - | - | 2259 | 1971585 | 11260 |
| lex3+reader | 0.52 | 0.71 | 0.41 | 0.45 | 0.69 | 0.00 | 0.02 | 0.00 | 0.94 | 0.05 | 0.00 | - | 0.72 | 2259 | 470519 | 3114 |
| lex3+ops | 0.69 | 0.92 | 0.65 | 0.50 | 0.98 | 0.00 | 0.00 | 0.65 | 0.00 | 1.00 | 0.00 | - | 0.72 | 0 | 0 | 3 |
| struct3+reader | 0.52 | 0.60 | 0.47 | 0.49 | 0.57 | 0.00 | 0.33 | 0.00 | 0.94 | 0.05 | 1.00 | 0.39 | 1.00 | 2259 | 496520 | 3240 |
| struct3+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 2 |
| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 2 |
| random3+ops | 0.04 | 0.05 | 0.00 | 0.02 | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.04 | 0 | 0 | 2 |
| full+ops/lm-encoder | 0.10 | 0.06 | 0.04 | 0.21 | 0.15 | 0.24 | 0.01 | 0.04 | 0.00 | 0.76 | 1.00 | 0.12 | 1.00 | 4320 | 340032 | 3458 |

Operator statuses (final test):

| cell | ok | none_in_scope | no_observation | ambiguous | insufficient_evidence |
|---|---|---|---|---|---|
| lex3+ops | 0.52 | 0.00 | 0.00 | 0.00 | 0.48 |
| struct3+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| full+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| random3+ops | 0.03 | 0.00 | 0.00 | 0.00 | 0.97 |
| full+ops/lm-encoder | 0.07 | 0.09 | 0.03 | 0.34 | 0.48 |

## pilot-m2 (4 worlds)

| cell | positives | E2 | E3a | E3b | E4 | E5 | E7 | E3a pairs | E5 FR | E5 unknown | coverage | accuracy covered | gold support | calls | prompt tokens | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 0.09 | 0.00 | 0.50 | 0.00 | 0.00 | 0.84 | 0.00 | 0.00 | 0.00 | 0.00 | - | - | - | 1015 | 85867 | 735 |
| A1 | 0.28 | 0.30 | 0.50 | 0.30 | 0.09 | 0.00 | 0.15 | 0.00 | 0.99 | 0.00 | - | - | - | 1015 | 907876 | 4980 |
| lex3+reader | 0.50 | 0.64 | 0.49 | 0.50 | 0.53 | 0.00 | 0.03 | 0.00 | 0.95 | 0.05 | 0.00 | - | 0.70 | 1015 | 213432 | 1356 |
| lex3+ops | 0.68 | 0.86 | 0.67 | 0.50 | 0.97 | 0.00 | 0.00 | 0.67 | 0.00 | 1.00 | 0.00 | - | 0.70 | 0 | 0 | 2 |
| struct3+reader | 0.58 | 0.71 | 0.50 | 0.56 | 0.56 | 0.00 | 0.34 | 0.00 | 0.94 | 0.03 | 1.00 | 0.43 | 1.00 | 1015 | 224589 | 1427 |
| struct3+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 |
| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 |
| random3+ops | 0.07 | 0.08 | 0.00 | 0.06 | 0.14 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.06 | 0 | 0 | 1 |
| full+ops/lm-encoder | 0.13 | 0.11 | 0.03 | 0.11 | 0.38 | 0.22 | 0.00 | 0.03 | 0.00 | 0.78 | 1.00 | 0.14 | 1.00 | 1920 | 152206 | 1509 |

Operator statuses (final test):

| cell | ok | none_in_scope | no_observation | ambiguous | insufficient_evidence |
|---|---|---|---|---|---|
| lex3+ops | 0.52 | 0.00 | 0.00 | 0.00 | 0.48 |
| struct3+ops | 0.77 | 0.23 | 0.00 | 0.00 | 0.00 |
| full+ops | 0.77 | 0.23 | 0.00 | 0.00 | 0.00 |
| random3+ops | 0.04 | 0.00 | 0.00 | 0.00 | 0.96 |
| full+ops/lm-encoder | 0.09 | 0.08 | 0.01 | 0.34 | 0.47 |

## LM encoder (slot filling) vs template truth (valid worlds)

| actor | partner | action | object | place | event_day | all_slots | records with invalid slots | partner normalised to none |
|---|---|---|---|---|---|---|---|---|
| 0.991 | 0.878 | 0.683 | 0.390 | 0.991 | 0.789 | 0.214 | 757/1040 | 707/1040 |

LM encoder qualification for the tested round 3.2 templates (docs/ROUND_3_2.md): NOT DECIDABLE - the evaluation is incomplete (13 valid world reports); partial tables above are diagnostic only.

## Controls (valid worlds)

- misbound store + operators: E2 0.10, E5 FR 0.33
- restart (store file of full+ops): same answers 26/26, accuracy after restart 1.000, empty store on positive items 0.000, truncated refused 26/26, changed refused 26/26
