# Round 3.6 parse run

## qwen3-1.7b+q7

Thresholds (calibration split): intent {'tau': None, 'acceptance': 0.0, 'precision': None, 'accepted': 0, 'items': 490}; target {'tau': None, 'acceptance': 0.0, 'precision': None, 'accepted': 0, 'items': 0}
Calibration flow: {'distinct': 490, 'intent_items': 490, 'target_calibratable': 354, 'after_accepted_intent': 0, 'target_items': 0, 'target_accepted': 0}

### dev, best value (tau 0): parser criteria NOT met

#### LM parser (dev, best value (tau 0))

| measure | value |
|---|---|
| exact:object_current:goal | 24/28 (0.857) |
| exact:object_current:absent | 29/30 (0.967) |
| exact:object_current | 52/56 (0.929) |
| exact:object_first:goal | 10/10 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 10/10 (1.000) |
| exact:object_previous:goal | 10/10 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 10/10 (1.000) |
| exact:person_current:goal | 8/10 (0.800) |
| exact:person_current:absent | 8/10 (0.800) |
| exact:person_current | 16/20 (0.800) |
| exact:person_first:goal | 10/10 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 10/10 (1.000) |
| exact:person_previous:goal | 10/10 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 10/10 (1.000) |
| exact:giver:goal | 9/10 (0.900) |
| exact:giver:absent | 10/10 (1.000) |
| exact:giver | 19/20 (0.950) |
| wrong_accepted | 1/128 (0.008) |
| false_ok:CLARIFY | 0/22 (0.000) |
| false_ok:REFUSE | 0/50 (0.000) |
| handled:CLARIFY | 22/22 (1.000) |
| handled:REFUSE | 49/50 (0.980) |
| recognised_ambiguity | 22/22 (1.000) |
| unnecessary | 8/136 (0.059) |
| family macro CLARIFY / REFUSE | 1.0 / 0.9814814814814815 |

Families (right / texts): CLARIFY:bare_noun 11/11; CLARIFY:first_name 10/10; CLARIFY:pronoun 1/1; REFUSE:count 7/7; REFUSE:event_relative 8/9; REFUSE:future 12/12; REFUSE:ownership 8/8; REFUSE:who_did 8/8; REFUSE:why 6/6

Wordings (right / texts): bare_noun:dev:0 11/11; count:dev:0 7/7; event_relative:dev:0 8/9; first_name:dev:0 10/10; future:dev:0 12/12; giver:dev:0 4/4; giver:dev:1 7/7; giver:dev:2 6/6; giver:template:0 2/3; object_current:dev:0 10/10; object_current:dev:1 16/17; object_current:dev:2 15/18; object_current:template:0 11/11; object_first:dev:0 3/3; object_first:dev:1 4/4; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 5/5; object_previous:template:0 2/2; ownership:dev:0 8/8; person_current:dev:0 4/4; person_current:dev:1 0/3; person_current:dev:2 5/5; person_current:template:0 7/8; person_first:dev:0 4/4; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 3/3; person_previous:dev:0 5/5; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 8/8; why:dev:0 6/6

Error causes: wrong_intent 9; wrong_target 1

Rule baseline (development grammar): exact OK 136/136, handled CLARIFY 22/22 (1.000), handled REFUSE 50/50 (1.000), false OK CLARIFY 0/22 (0.000), false OK REFUSE 0/50 (0.000)
Paired with the baseline (distinct texts): both right 198; only model right 0; only rules right 10; both wrong 0

Control uniform scores: right 22/208; false OK CLARIFY 0/22 (0.000), REFUSE 0/50 (0.000)
Control random scores: right 37/208; false OK CLARIFY 0/22 (0.000), REFUSE 16/50 (0.320)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.800 | 1.000 | 0.800 | [0.490, 0.943] | 0.000 | 0.800 |
| moved:find | 0.800 | 1.000 | 0.800 | [0.490, 0.943] | 0.000 | 0.800 |
| giver:find | 0.900 | 1.000 | 0.900 | [0.596, 0.982] | 0.000 | 0.900 |
| object:current | 0.900 | 1.000 | 0.900 | [0.596, 0.982] | 0.000 | 0.900 |
| object:first | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| object:previous | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| person:current | 0.800 | 1.000 | 0.800 | [0.490, 0.943] | 0.000 | 0.800 |
| person:first | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| person:previous | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |

Control questions, agent behaviour per world: {'absent': {'explore': 94, 'refuse': 2, 'clarify': 4}, 'ambiguous': {'clarify': 100}, 'unsupported': {'refuse': 98, 'clarify': 2}}

- FAIL exact specification object_current: 52/56 >= 0.95
- FAIL exact specification person_current: 16/20 >= 0.95
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 8/136 <= 0.05
- FAIL hidden:find: success LM 0.800 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.800 >= 0.95
- FAIL moved:find: success LM 0.800 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.800 >= 0.95
- FAIL giver:find: success LM 0.900 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.900 >= 0.95
- FAIL object:current: success LM 0.900 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.900 >= 0.95
- FAIL person:current: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.800 >= 0.95

### dev, thresholds: parser criteria NOT met

#### LM parser (dev, thresholds)

| measure | value |
|---|---|
| exact:object_current:goal | 0/28 (0.000) |
| exact:object_current:absent | 0/30 (0.000) |
| exact:object_current | 0/56 (0.000) |
| exact:object_first:goal | 0/10 (0.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 0/10 (0.000) |
| exact:object_previous:goal | 0/10 (0.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 0/10 (0.000) |
| exact:person_current:goal | 0/10 (0.000) |
| exact:person_current:absent | 0/10 (0.000) |
| exact:person_current | 0/20 (0.000) |
| exact:person_first:goal | 0/10 (0.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 0/10 (0.000) |
| exact:person_previous:goal | 0/10 (0.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 0/10 (0.000) |
| exact:giver:goal | 0/10 (0.000) |
| exact:giver:absent | 0/10 (0.000) |
| exact:giver | 0/20 (0.000) |
| wrong_accepted | 0/0 |
| false_ok:CLARIFY | 0/22 (0.000) |
| false_ok:REFUSE | 0/50 (0.000) |
| handled:CLARIFY | 22/22 (1.000) |
| handled:REFUSE | 0/50 (0.000) |
| recognised_ambiguity | 0/22 (0.000) |
| unnecessary | 136/136 (1.000) |
| family macro CLARIFY / REFUSE | 1.0 / 0.0 |

Families (right / texts): CLARIFY:bare_noun 11/11; CLARIFY:first_name 10/10; CLARIFY:pronoun 1/1; REFUSE:count 0/7; REFUSE:event_relative 0/9; REFUSE:future 0/12; REFUSE:ownership 0/8; REFUSE:who_did 0/8; REFUSE:why 0/6

Wordings (right / texts): bare_noun:dev:0 11/11; count:dev:0 0/7; event_relative:dev:0 0/9; first_name:dev:0 10/10; future:dev:0 0/12; giver:dev:0 0/4; giver:dev:1 0/7; giver:dev:2 0/6; giver:template:0 0/3; object_current:dev:0 0/10; object_current:dev:1 0/17; object_current:dev:2 0/18; object_current:template:0 0/11; object_first:dev:0 0/3; object_first:dev:1 0/4; object_first:dev:2 0/1; object_first:template:0 0/2; object_previous:dev:0 0/2; object_previous:dev:1 0/1; object_previous:dev:2 0/5; object_previous:template:0 0/2; ownership:dev:0 0/8; person_current:dev:0 0/4; person_current:dev:1 0/3; person_current:dev:2 0/5; person_current:template:0 0/8; person_first:dev:0 0/4; person_first:dev:1 0/2; person_first:dev:2 0/1; person_first:template:0 0/3; person_previous:dev:0 0/5; person_previous:dev:1 0/1; person_previous:dev:2 0/2; person_previous:template:0 0/2; pronoun:dev:0 1/1; who_did:dev:0 0/8; why:dev:0 0/6

Error causes: low_confidence 186

Rule baseline (development grammar): exact OK 136/136, handled CLARIFY 22/22 (1.000), handled REFUSE 50/50 (1.000), false OK CLARIFY 0/22 (0.000), false OK REFUSE 0/50 (0.000)
Paired with the baseline (distinct texts): both right 22; only model right 0; only rules right 186; both wrong 0

Control uniform scores: right 22/208; false OK CLARIFY 0/22 (0.000), REFUSE 0/50 (0.000)
Control random scores: right 22/208; false OK CLARIFY 0/22 (0.000), REFUSE 0/50 (0.000)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| moved:find | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| giver:find | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| object:current | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| object:first | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| object:previous | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| person:current | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| person:first | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |
| person:previous | 0.000 | 1.000 | 0.000 | [0.000, 0.278] | - | 0.000 |

Control questions, agent behaviour per world: {'absent': {'clarify': 100}, 'ambiguous': {'clarify': 100}, 'unsupported': {'clarify': 100}}

- FAIL exact specification object_current: 0/56 >= 0.95
- FAIL exact specification object_first: 0/10 >= 0.95
- FAIL exact specification object_previous: 0/10 >= 0.95
- FAIL exact specification person_current: 0/20 >= 0.95
- FAIL exact specification person_first: 0/10 >= 0.95
- FAIL exact specification person_previous: 0/10 >= 0.95
- FAIL exact specification giver: 0/20 >= 0.95
- FAIL wrong accepted specifications 0/0 <= 0.02
- FAIL REFUSE among gold-REFUSE 0/50 >= 0.90
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 136/136 <= 0.05
- FAIL hidden:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.000 >= 0.95
- FAIL hidden:find: confident-error rate undefined <= 0.05
- FAIL moved:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.000 >= 0.95
- FAIL moved:find: confident-error rate undefined <= 0.05
- FAIL giver:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.000 >= 0.95
- FAIL giver:find: confident-error rate undefined <= 0.05
- FAIL object:current: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.000 >= 0.95
- FAIL object:current: confident-error rate undefined <= 0.05
- FAIL object:first: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:first: pair success 0.000 >= 0.95
- FAIL object:first: confident-error rate undefined <= 0.05
- FAIL object:previous: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.000 >= 0.95
- FAIL object:previous: confident-error rate undefined <= 0.05
- FAIL person:current: success LM 0.000 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.000 >= 0.95

### cal, best value (tau 0): parser criteria NOT met

#### LM parser (cal, best value (tau 0))

| measure | value |
|---|---|
| exact:object_current:goal | 61/66 (0.924) |
| exact:object_current:absent | 71/73 (0.973) |
| exact:object_current | 120/127 (0.945) |
| exact:object_first:goal | 28/28 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 28/28 (1.000) |
| exact:object_previous:goal | 28/28 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 28/28 (1.000) |
| exact:person_current:goal | 21/27 (0.778) |
| exact:person_current:absent | 22/27 (0.815) |
| exact:person_current | 43/54 (0.796) |
| exact:person_first:goal | 30/30 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 30/30 (1.000) |
| exact:person_previous:goal | 29/30 (0.967) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 29/30 (0.967) |
| exact:giver:goal | 27/27 (1.000) |
| exact:giver:absent | 26/26 (1.000) |
| exact:giver | 51/51 (1.000) |
| wrong_accepted | 0/329 (0.000) |
| false_ok:CLARIFY | 0/6 (0.000) |
| false_ok:REFUSE | 0/136 (0.000) |
| handled:CLARIFY | 6/6 (1.000) |
| handled:REFUSE | 133/136 (0.978) |
| recognised_ambiguity | 6/6 (1.000) |
| unnecessary | 19/348 (0.055) |
| family macro CLARIFY / REFUSE | 1.0 / 0.975 |

Families (right / texts): CLARIFY:bare_noun 1/1; CLARIFY:first_name 5/5; REFUSE:count 20/20; REFUSE:event_relative 17/20; REFUSE:future 16/16; REFUSE:ownership 15/15; REFUSE:who_did 29/29; REFUSE:why 36/36

Wordings (right / texts): bare_noun:dev:0 1/1; count:dev:0 20/20; event_relative:dev:0 17/20; first_name:dev:0 5/5; future:dev:0 16/16; giver:dev:0 14/14; giver:dev:1 12/12; giver:dev:2 15/15; giver:template:0 10/10; object_current:dev:0 28/28; object_current:dev:1 30/30; object_current:dev:2 28/35; object_current:template:0 34/34; object_first:dev:0 10/10; object_first:dev:1 6/6; object_first:dev:2 4/4; object_first:template:0 8/8; object_previous:dev:0 8/8; object_previous:dev:1 7/7; object_previous:dev:2 8/8; object_previous:template:0 5/5; ownership:dev:0 15/15; person_current:dev:0 10/10; person_current:dev:1 0/11; person_current:dev:2 19/19; person_current:template:0 14/14; person_first:dev:0 8/8; person_first:dev:1 8/8; person_first:dev:2 8/8; person_first:template:0 6/6; person_previous:dev:0 8/8; person_previous:dev:1 7/7; person_previous:dev:2 5/5; person_previous:template:0 9/10; who_did:dev:0 29/29; why:dev:0 36/36

Error causes: wrong_intent 22

Rule baseline (development grammar): exact OK 348/348, handled CLARIFY 6/6 (1.000), handled REFUSE 136/136 (1.000), false OK CLARIFY 0/6 (0.000), false OK REFUSE 0/136 (0.000)
Paired with the baseline (distinct texts): both right 468; only model right 0; only rules right 22; both wrong 0

Control uniform scores: right 6/490; false OK CLARIFY 0/6 (0.000), REFUSE 0/136 (0.000)
Control random scores: right 37/490; false OK CLARIFY 0/6 (0.000), REFUSE 50/136 (0.368)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.900 | 1.000 | 0.900 | [0.744, 0.965] | 0.000 | 0.900 |
| moved:find | 0.933 | 1.000 | 0.933 | [0.787, 0.982] | 0.000 | 0.933 |
| giver:find | 0.967 | 1.000 | 0.967 | [0.833, 0.994] | 0.000 | 0.967 |
| object:current | 0.933 | 1.000 | 0.933 | [0.787, 0.982] | 0.000 | 0.933 |
| object:first | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| object:previous | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| person:current | 0.767 | 1.000 | 0.767 | [0.591, 0.882] | 0.000 | 0.767 |
| person:first | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| person:previous | 0.967 | 1.000 | 0.967 | [0.833, 0.994] | 0.000 | 0.967 |

Control questions, agent behaviour per world: {'absent': {'explore': 280, 'refuse': 8, 'clarify': 12}, 'ambiguous': {'clarify': 300}, 'unsupported': {'refuse': 294, 'clarify': 6}}

- FAIL exact specification object_current: 120/127 >= 0.95
- FAIL exact specification person_current: 43/54 >= 0.95
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 19/348 <= 0.05
- FAIL hidden:find: success LM 0.900 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.900 >= 0.95
- FAIL moved:find: success LM 0.933 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.933 >= 0.95
- FAIL giver:find: success LM 0.967 >= reference 1.000 - 0.02
- FAIL object:current: success LM 0.933 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.933 >= 0.95
- FAIL person:current: success LM 0.767 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.767 >= 0.95
- FAIL person:previous: success LM 0.967 >= reference 1.000 - 0.02

### cal, thresholds: parser criteria NOT met

#### LM parser (cal, thresholds)

| measure | value |
|---|---|
| exact:object_current:goal | 0/66 (0.000) |
| exact:object_current:absent | 0/73 (0.000) |
| exact:object_current | 0/127 (0.000) |
| exact:object_first:goal | 0/28 (0.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 0/28 (0.000) |
| exact:object_previous:goal | 0/28 (0.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 0/28 (0.000) |
| exact:person_current:goal | 0/27 (0.000) |
| exact:person_current:absent | 0/27 (0.000) |
| exact:person_current | 0/54 (0.000) |
| exact:person_first:goal | 0/30 (0.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 0/30 (0.000) |
| exact:person_previous:goal | 0/30 (0.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 0/30 (0.000) |
| exact:giver:goal | 0/27 (0.000) |
| exact:giver:absent | 0/26 (0.000) |
| exact:giver | 0/51 (0.000) |
| wrong_accepted | 0/0 |
| false_ok:CLARIFY | 0/6 (0.000) |
| false_ok:REFUSE | 0/136 (0.000) |
| handled:CLARIFY | 6/6 (1.000) |
| handled:REFUSE | 0/136 (0.000) |
| recognised_ambiguity | 0/6 (0.000) |
| unnecessary | 348/348 (1.000) |
| family macro CLARIFY / REFUSE | 1.0 / 0.0 |

Families (right / texts): CLARIFY:bare_noun 1/1; CLARIFY:first_name 5/5; REFUSE:count 0/20; REFUSE:event_relative 0/20; REFUSE:future 0/16; REFUSE:ownership 0/15; REFUSE:who_did 0/29; REFUSE:why 0/36

Wordings (right / texts): bare_noun:dev:0 1/1; count:dev:0 0/20; event_relative:dev:0 0/20; first_name:dev:0 5/5; future:dev:0 0/16; giver:dev:0 0/14; giver:dev:1 0/12; giver:dev:2 0/15; giver:template:0 0/10; object_current:dev:0 0/28; object_current:dev:1 0/30; object_current:dev:2 0/35; object_current:template:0 0/34; object_first:dev:0 0/10; object_first:dev:1 0/6; object_first:dev:2 0/4; object_first:template:0 0/8; object_previous:dev:0 0/8; object_previous:dev:1 0/7; object_previous:dev:2 0/8; object_previous:template:0 0/5; ownership:dev:0 0/15; person_current:dev:0 0/10; person_current:dev:1 0/11; person_current:dev:2 0/19; person_current:template:0 0/14; person_first:dev:0 0/8; person_first:dev:1 0/8; person_first:dev:2 0/8; person_first:template:0 0/6; person_previous:dev:0 0/8; person_previous:dev:1 0/7; person_previous:dev:2 0/5; person_previous:template:0 0/10; who_did:dev:0 0/29; why:dev:0 0/36

Error causes: low_confidence 484

Rule baseline (development grammar): exact OK 348/348, handled CLARIFY 6/6 (1.000), handled REFUSE 136/136 (1.000), false OK CLARIFY 0/6 (0.000), false OK REFUSE 0/136 (0.000)
Paired with the baseline (distinct texts): both right 6; only model right 0; only rules right 484; both wrong 0

Control uniform scores: right 6/490; false OK CLARIFY 0/6 (0.000), REFUSE 0/136 (0.000)
Control random scores: right 6/490; false OK CLARIFY 0/6 (0.000), REFUSE 0/136 (0.000)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| moved:find | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| giver:find | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| object:current | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| object:first | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| object:previous | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| person:current | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| person:first | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |
| person:previous | 0.000 | 1.000 | 0.000 | [0.000, 0.114] | - | 0.000 |

Control questions, agent behaviour per world: {'absent': {'clarify': 300}, 'ambiguous': {'clarify': 300}, 'unsupported': {'clarify': 300}}

- FAIL exact specification object_current: 0/127 >= 0.95
- FAIL exact specification object_first: 0/28 >= 0.95
- FAIL exact specification object_previous: 0/28 >= 0.95
- FAIL exact specification person_current: 0/54 >= 0.95
- FAIL exact specification person_first: 0/30 >= 0.95
- FAIL exact specification person_previous: 0/30 >= 0.95
- FAIL exact specification giver: 0/51 >= 0.95
- FAIL wrong accepted specifications 0/0 <= 0.02
- FAIL REFUSE among gold-REFUSE 0/136 >= 0.90
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 348/348 <= 0.05
- FAIL hidden:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.000 >= 0.95
- FAIL hidden:find: confident-error rate undefined <= 0.05
- FAIL moved:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.000 >= 0.95
- FAIL moved:find: confident-error rate undefined <= 0.05
- FAIL giver:find: success LM 0.000 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.000 >= 0.95
- FAIL giver:find: confident-error rate undefined <= 0.05
- FAIL object:current: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.000 >= 0.95
- FAIL object:current: confident-error rate undefined <= 0.05
- FAIL object:first: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:first: pair success 0.000 >= 0.95
- FAIL object:first: confident-error rate undefined <= 0.05
- FAIL object:previous: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.000 >= 0.95
- FAIL object:previous: confident-error rate undefined <= 0.05
- FAIL person:current: success LM 0.000 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.000 >= 0.95

