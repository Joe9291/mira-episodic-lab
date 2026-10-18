# Round 3.2 summary (exploratory, template benchmark)

Means over worlds (both overlap conditions pooled within a world). Development worlds (dev-m3) and the pilot worlds already used (pilot-m2) are shown separately. E5 = correct rejection of binding lures; FR = in-world false recall; unknown = abstention. Coverage = share of final items whose selection was certified sufficient for the question; accuracy covered = accuracy on those items, pooled over all covered final items of the series; gold support = share of positive items whose gold target episodes were all selected (evaluator information, not an upper bound of accuracy).

## dev-m3 (10 worlds)

| cell | positives | E2 | E3a | E3b | E4 | E5 | E7 | E3a pairs | E5 FR | E5 unknown | coverage | accuracy covered | gold support | calls | prompt tokens | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 0.10 | 0.00 | 0.50 | 0.00 | 0.03 | 0.72 | 0.00 | 0.00 | 0.00 | 0.00 | - | - | - | 2488 | 210839 | 1834 |
| A1 | 0.31 | 0.31 | 0.50 | 0.46 | 0.09 | 0.00 | 0.17 | 0.00 | 0.98 | 0.00 | - | - | - | 2488 | 2172330 | 12620 |
| lex3+reader | 0.51 | 0.69 | 0.41 | 0.44 | 0.71 | 0.00 | 0.02 | 0.00 | 0.94 | 0.05 | 0.00 | - | 0.71 | 2488 | 518047 | 3476 |
| lex3+ops | 0.69 | 0.93 | 0.64 | 0.50 | 0.98 | 0.00 | 0.00 | 0.64 | 0.00 | 1.00 | 0.00 | - | 0.71 | 0 | 0 | 4 |
| struct3+reader | 0.51 | 0.58 | 0.47 | 0.49 | 0.56 | 0.00 | 0.31 | 0.00 | 0.95 | 0.04 | 1.00 | 0.38 | 1.00 | 2488 | 546447 | 3620 |
| struct3+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 2 |
| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 2 |
| random3+ops | 0.04 | 0.04 | 0.00 | 0.03 | 0.09 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.04 | 0 | 0 | 2 |
| full+ops/lm-encoder | 0.10 | 0.08 | 0.04 | 0.20 | 0.17 | 0.27 | 0.01 | 0.04 | 0.00 | 0.73 | 1.00 | 0.13 | 1.00 | 4800 | 377860 | 3844 |

Operator statuses (final test):

| cell | ok | none_in_scope | no_observation | ambiguous | insufficient_evidence |
|---|---|---|---|---|---|
| lex3+ops | 0.52 | 0.00 | 0.00 | 0.00 | 0.48 |
| struct3+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| full+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| random3+ops | 0.02 | 0.00 | 0.00 | 0.00 | 0.98 |
| full+ops/lm-encoder | 0.07 | 0.10 | 0.03 | 0.34 | 0.46 |

## pilot-m2 (5 worlds)

| cell | positives | E2 | E3a | E3b | E4 | E5 | E7 | E3a pairs | E5 FR | E5 unknown | coverage | accuracy covered | gold support | calls | prompt tokens | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 0.10 | 0.00 | 0.50 | 0.00 | 0.03 | 0.81 | 0.00 | 0.00 | 0.00 | 0.00 | - | - | - | 1242 | 105208 | 914 |
| A1 | 0.29 | 0.29 | 0.50 | 0.36 | 0.11 | 0.00 | 0.12 | 0.00 | 0.99 | 0.00 | - | - | - | 1242 | 1100766 | 6372 |
| lex3+reader | 0.51 | 0.69 | 0.49 | 0.51 | 0.56 | 0.00 | 0.03 | 0.00 | 0.96 | 0.04 | 0.00 | - | 0.69 | 1242 | 260001 | 1746 |
| lex3+ops | 0.66 | 0.89 | 0.61 | 0.50 | 0.97 | 0.00 | 0.00 | 0.61 | 0.00 | 1.00 | 0.00 | - | 0.69 | 0 | 0 | 2 |
| struct3+reader | 0.56 | 0.69 | 0.50 | 0.54 | 0.54 | 0.00 | 0.36 | 0.00 | 0.95 | 0.03 | 1.00 | 0.42 | 1.00 | 1242 | 273683 | 1821 |
| struct3+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 |
| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 |
| random3+ops | 0.05 | 0.07 | 0.00 | 0.05 | 0.11 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.05 | 0 | 0 | 1 |
| full+ops/lm-encoder | 0.12 | 0.09 | 0.03 | 0.12 | 0.33 | 0.22 | 0.00 | 0.03 | 0.00 | 0.78 | 1.00 | 0.13 | 1.00 | 2400 | 189650 | 1928 |

Operator statuses (final test):

| cell | ok | none_in_scope | no_observation | ambiguous | insufficient_evidence |
|---|---|---|---|---|---|
| lex3+ops | 0.50 | 0.00 | 0.00 | 0.00 | 0.50 |
| struct3+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| full+ops | 0.76 | 0.24 | 0.00 | 0.00 | 0.00 |
| random3+ops | 0.03 | 0.00 | 0.00 | 0.00 | 0.97 |
| full+ops/lm-encoder | 0.08 | 0.10 | 0.02 | 0.34 | 0.46 |

## LM encoder (slot filling) vs template truth (valid worlds)

| actor | partner | action | object | place | event_day | all_slots | records with invalid slots | partner normalised to none |
|---|---|---|---|---|---|---|---|---|
| 0.990 | 0.873 | 0.693 | 0.395 | 0.993 | 0.795 | 0.217 | 866/1200 | 837/1200 |

LM encoder qualification for the tested round 3.2 templates (docs/ROUND_3_2.md): all_slots 0.217 >= 0.95; positives full+ops/lm-encoder 0.107 vs full+ops 1.000 (at most 0.02 lower); lure false recall 0.000 <= 0.05 -> keep the template encoder; limit stated.

## Controls (valid worlds)

- misbound store + operators: E2 0.09, E5 FR 0.34
- restart (store file of full+ops): same answers 30/30, accuracy after restart 1.000, empty store on positive items 0.000, truncated refused 30/30, changed refused 30/30
