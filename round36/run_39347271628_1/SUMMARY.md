# Round 3.6 parse run

## qwen3-1.7b+q8

Thresholds (calibration split): intent {'tau': 19.829733252534425, 'acceptance': 0.6306122448979592, 'precision': 0.9902912621359223, 'accepted': 309, 'items': 490}; target {'tau': None, 'acceptance': 0.0, 'precision': None, 'accepted': 0, 'items': 176}
Calibration flow: {'distinct': 490, 'intent_items': 490, 'target_calibratable': 354, 'after_accepted_intent': 178, 'target_items': 176, 'target_accepted': 0}

### dev, best value (tau 0): parser criteria NOT met

#### LM parser (dev, best value (tau 0))

| measure | value |
|---|---|
| exact:object_current:goal | 14/28 (0.500) |
| exact:object_current:absent | 18/30 (0.600) |
| exact:object_current | 31/56 (0.554) |
| exact:object_first:goal | 10/10 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 10/10 (1.000) |
| exact:object_previous:goal | 4/10 (0.400) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 4/10 (0.400) |
| exact:person_current:goal | 6/10 (0.600) |
| exact:person_current:absent | 8/10 (0.800) |
| exact:person_current | 14/20 (0.700) |
| exact:person_first:goal | 10/10 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 10/10 (1.000) |
| exact:person_previous:goal | 10/10 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 10/10 (1.000) |
| exact:giver:goal | 10/10 (1.000) |
| exact:giver:absent | 10/10 (1.000) |
| exact:giver | 20/20 (1.000) |
| wrong_accepted | 4/103 (0.039) |
| false_ok:CLARIFY | 0/22 (0.000) |
| false_ok:REFUSE | 0/50 (0.000) |
| handled:CLARIFY | 22/22 (1.000) |
| handled:REFUSE | 50/50 (1.000) |
| recognised_ambiguity | 22/22 (1.000) |
| unnecessary | 33/136 (0.243) |
| family macro CLARIFY / REFUSE | 1.0 / 1.0 |

Families (right / texts): CLARIFY:bare_noun 11/11; CLARIFY:first_name 10/10; CLARIFY:pronoun 1/1; REFUSE:count 7/7; REFUSE:event_relative 9/9; REFUSE:future 12/12; REFUSE:ownership 8/8; REFUSE:who_did 8/8; REFUSE:why 6/6

Wordings (right / texts): bare_noun:dev:0 11/11; count:dev:0 7/7; event_relative:dev:0 9/9; first_name:dev:0 10/10; future:dev:0 12/12; giver:dev:0 4/4; giver:dev:1 7/7; giver:dev:2 6/6; giver:template:0 3/3; object_current:dev:0 10/10; object_current:dev:1 0/17; object_current:dev:2 10/18; object_current:template:0 11/11; object_first:dev:0 3/3; object_first:dev:1 4/4; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 0/2; object_previous:dev:1 1/1; object_previous:dev:2 1/5; object_previous:template:0 2/2; ownership:dev:0 8/8; person_current:dev:0 4/4; person_current:dev:1 0/3; person_current:dev:2 5/5; person_current:template:0 5/8; person_first:dev:0 4/4; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 3/3; person_previous:dev:0 5/5; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 8/8; why:dev:0 6/6

Error causes: wrong_intent 37

Rule baseline (development grammar): exact OK 136/136, handled CLARIFY 22/22 (1.000), handled REFUSE 50/50 (1.000), false OK CLARIFY 0/22 (0.000), false OK REFUSE 0/50 (0.000)
Paired with the baseline (distinct texts): both right 171; only model right 0; only rules right 37; both wrong 0

Control uniform scores: right 22/208; false OK CLARIFY 0/22 (0.000), REFUSE 0/50 (0.000)
Control random scores: right 37/208; false OK CLARIFY 0/22 (0.000), REFUSE 16/50 (0.320)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.500 | 1.000 | 0.500 | [0.237, 0.763] | 0.000 | 0.500 |
| moved:find | 0.250 | 1.000 | 0.200 | [0.057, 0.510] | 0.000 | 0.200 |
| giver:find | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| object:current | 0.700 | 1.000 | 0.700 | [0.397, 0.892] | 0.000 | 0.700 |
| object:first | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| object:previous | 0.400 | 1.000 | 0.400 | [0.168, 0.687] | 0.000 | 0.400 |
| person:current | 0.600 | 1.000 | 0.600 | [0.313, 0.832] | 0.000 | 0.600 |
| person:first | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |
| person:previous | 1.000 | 1.000 | 1.000 | [0.722, 1.000] | 0.000 | 1.000 |

Control questions, agent behaviour per world: {'absent': {'explore': 74, 'refuse': 22, 'clarify': 4}, 'ambiguous': {'clarify': 100}, 'unsupported': {'refuse': 100}}

- FAIL exact specification object_current: 31/56 >= 0.95
- FAIL exact specification object_previous: 4/10 >= 0.95
- FAIL exact specification person_current: 14/20 >= 0.95
- FAIL wrong accepted specifications 4/103 <= 0.02
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 33/136 <= 0.05
- FAIL hidden:find: success LM 0.500 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.500 >= 0.95
- FAIL moved:find: success LM 0.250 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.200 >= 0.95
- FAIL object:current: success LM 0.700 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.700 >= 0.95
- FAIL object:previous: success LM 0.400 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.400 >= 0.95
- FAIL person:current: success LM 0.600 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.600 >= 0.95

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
| handled:REFUSE | 48/50 (0.960) |
| recognised_ambiguity | 3/22 (0.136) |
| unnecessary | 136/136 (1.000) |
| family macro CLARIFY / REFUSE | 1.0 / 0.9606481481481483 |

Families (right / texts): CLARIFY:bare_noun 11/11; CLARIFY:first_name 10/10; CLARIFY:pronoun 1/1; REFUSE:count 7/7; REFUSE:event_relative 8/9; REFUSE:future 12/12; REFUSE:ownership 8/8; REFUSE:who_did 7/8; REFUSE:why 6/6

Wordings (right / texts): bare_noun:dev:0 11/11; count:dev:0 7/7; event_relative:dev:0 8/9; first_name:dev:0 10/10; future:dev:0 12/12; giver:dev:0 0/4; giver:dev:1 0/7; giver:dev:2 0/6; giver:template:0 0/3; object_current:dev:0 0/10; object_current:dev:1 0/17; object_current:dev:2 0/18; object_current:template:0 0/11; object_first:dev:0 0/3; object_first:dev:1 0/4; object_first:dev:2 0/1; object_first:template:0 0/2; object_previous:dev:0 0/2; object_previous:dev:1 0/1; object_previous:dev:2 0/5; object_previous:template:0 0/2; ownership:dev:0 8/8; person_current:dev:0 0/4; person_current:dev:1 0/3; person_current:dev:2 0/5; person_current:template:0 0/8; person_first:dev:0 0/4; person_first:dev:1 0/2; person_first:dev:2 0/1; person_first:template:0 0/3; person_previous:dev:0 0/5; person_previous:dev:1 0/1; person_previous:dev:2 0/2; person_previous:template:0 0/2; pronoun:dev:0 1/1; who_did:dev:0 7/8; why:dev:0 6/6

Error causes: low_confidence 138

Rule baseline (development grammar): exact OK 136/136, handled CLARIFY 22/22 (1.000), handled REFUSE 50/50 (1.000), false OK CLARIFY 0/22 (0.000), false OK REFUSE 0/50 (0.000)
Paired with the baseline (distinct texts): both right 70; only model right 0; only rules right 138; both wrong 0

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

Control questions, agent behaviour per world: {'absent': {'clarify': 100}, 'ambiguous': {'clarify': 100}, 'unsupported': {'refuse': 96, 'clarify': 4}}

- FAIL exact specification object_current: 0/56 >= 0.95
- FAIL exact specification object_first: 0/10 >= 0.95
- FAIL exact specification object_previous: 0/10 >= 0.95
- FAIL exact specification person_current: 0/20 >= 0.95
- FAIL exact specification person_first: 0/10 >= 0.95
- FAIL exact specification person_previous: 0/10 >= 0.95
- FAIL exact specification giver: 0/20 >= 0.95
- FAIL wrong accepted specifications 0/0 <= 0.02
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
- FAIL person:current: confident-error rate undefined <= 0.05

### cal, best value (tau 0): parser criteria NOT met

#### LM parser (cal, best value (tau 0))

| measure | value |
|---|---|
| exact:object_current:goal | 45/66 (0.682) |
| exact:object_current:absent | 44/73 (0.603) |
| exact:object_current | 83/127 (0.654) |
| exact:object_first:goal | 28/28 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 28/28 (1.000) |
| exact:object_previous:goal | 13/28 (0.464) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 13/28 (0.464) |
| exact:person_current:goal | 18/27 (0.667) |
| exact:person_current:absent | 22/27 (0.815) |
| exact:person_current | 40/54 (0.741) |
| exact:person_first:goal | 30/30 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 30/30 (1.000) |
| exact:person_previous:goal | 30/30 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 30/30 (1.000) |
| exact:giver:goal | 27/27 (1.000) |
| exact:giver:absent | 26/26 (1.000) |
| exact:giver | 51/51 (1.000) |
| wrong_accepted | 14/289 (0.048) |
| false_ok:CLARIFY | 0/6 (0.000) |
| false_ok:REFUSE | 0/136 (0.000) |
| handled:CLARIFY | 6/6 (1.000) |
| handled:REFUSE | 136/136 (1.000) |
| recognised_ambiguity | 6/6 (1.000) |
| unnecessary | 59/348 (0.170) |
| family macro CLARIFY / REFUSE | 1.0 / 1.0 |

Families (right / texts): CLARIFY:bare_noun 1/1; CLARIFY:first_name 5/5; REFUSE:count 20/20; REFUSE:event_relative 20/20; REFUSE:future 16/16; REFUSE:ownership 15/15; REFUSE:who_did 29/29; REFUSE:why 36/36

Wordings (right / texts): bare_noun:dev:0 1/1; count:dev:0 20/20; event_relative:dev:0 20/20; first_name:dev:0 5/5; future:dev:0 16/16; giver:dev:0 14/14; giver:dev:1 12/12; giver:dev:2 15/15; giver:template:0 10/10; object_current:dev:0 28/28; object_current:dev:1 0/30; object_current:dev:2 21/35; object_current:template:0 34/34; object_first:dev:0 10/10; object_first:dev:1 6/6; object_first:dev:2 4/4; object_first:template:0 8/8; object_previous:dev:0 0/8; object_previous:dev:1 7/7; object_previous:dev:2 1/8; object_previous:template:0 5/5; ownership:dev:0 15/15; person_current:dev:0 10/10; person_current:dev:1 0/11; person_current:dev:2 19/19; person_current:template:0 11/14; person_first:dev:0 8/8; person_first:dev:1 8/8; person_first:dev:2 8/8; person_first:template:0 6/6; person_previous:dev:0 8/8; person_previous:dev:1 7/7; person_previous:dev:2 5/5; person_previous:template:0 10/10; who_did:dev:0 29/29; why:dev:0 36/36

Error causes: wrong_intent 73

Rule baseline (development grammar): exact OK 348/348, handled CLARIFY 6/6 (1.000), handled REFUSE 136/136 (1.000), false OK CLARIFY 0/6 (0.000), false OK REFUSE 0/136 (0.000)
Paired with the baseline (distinct texts): both right 417; only model right 0; only rules right 73; both wrong 0

Control uniform scores: right 6/490; false OK CLARIFY 0/6 (0.000), REFUSE 0/136 (0.000)
Control random scores: right 37/490; false OK CLARIFY 0/6 (0.000), REFUSE 50/136 (0.368)

| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |
|---|---|---|---|---|---|---|
| hidden:find | 0.650 | 1.000 | 0.633 | [0.455, 0.781] | 0.000 | 0.633 |
| moved:find | 0.700 | 1.000 | 0.667 | [0.488, 0.808] | 0.000 | 0.667 |
| giver:find | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| object:current | 0.733 | 1.000 | 0.733 | [0.556, 0.858] | 0.000 | 0.733 |
| object:first | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| object:previous | 0.433 | 1.000 | 0.433 | [0.274, 0.608] | 0.000 | 0.433 |
| person:current | 0.667 | 1.000 | 0.667 | [0.488, 0.808] | 0.000 | 0.667 |
| person:first | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |
| person:previous | 1.000 | 1.000 | 1.000 | [0.886, 1.000] | 0.000 | 1.000 |

Control questions, agent behaviour per world: {'absent': {'explore': 236, 'refuse': 52, 'clarify': 12}, 'ambiguous': {'clarify': 300}, 'unsupported': {'refuse': 300}}

- FAIL exact specification object_current: 83/127 >= 0.95
- FAIL exact specification object_previous: 13/28 >= 0.95
- FAIL exact specification person_current: 40/54 >= 0.95
- FAIL wrong accepted specifications 14/289 <= 0.02
- FAIL unnecessary CLARIFY/REFUSE among gold-OK 59/348 <= 0.05
- FAIL hidden:find: success LM 0.650 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.633 >= 0.95
- FAIL moved:find: success LM 0.700 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.667 >= 0.95
- FAIL object:current: success LM 0.733 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.733 >= 0.95
- FAIL object:previous: success LM 0.433 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.433 >= 0.95
- FAIL person:current: success LM 0.667 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.667 >= 0.95

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
| handled:REFUSE | 130/136 (0.956) |
| recognised_ambiguity | 0/6 (0.000) |
| unnecessary | 348/348 (1.000) |
| family macro CLARIFY / REFUSE | 1.0 / 0.9629310344827586 |

Families (right / texts): CLARIFY:bare_noun 1/1; CLARIFY:first_name 5/5; REFUSE:count 20/20; REFUSE:event_relative 19/20; REFUSE:future 16/16; REFUSE:ownership 15/15; REFUSE:who_did 24/29; REFUSE:why 36/36

Wordings (right / texts): bare_noun:dev:0 1/1; count:dev:0 20/20; event_relative:dev:0 19/20; first_name:dev:0 5/5; future:dev:0 16/16; giver:dev:0 0/14; giver:dev:1 0/12; giver:dev:2 0/15; giver:template:0 0/10; object_current:dev:0 0/28; object_current:dev:1 0/30; object_current:dev:2 0/35; object_current:template:0 0/34; object_first:dev:0 0/10; object_first:dev:1 0/6; object_first:dev:2 0/4; object_first:template:0 0/8; object_previous:dev:0 0/8; object_previous:dev:1 0/7; object_previous:dev:2 0/8; object_previous:template:0 0/5; ownership:dev:0 15/15; person_current:dev:0 0/10; person_current:dev:1 0/11; person_current:dev:2 0/19; person_current:template:0 0/14; person_first:dev:0 0/8; person_first:dev:1 0/8; person_first:dev:2 0/8; person_first:template:0 0/6; person_previous:dev:0 0/8; person_previous:dev:1 0/7; person_previous:dev:2 0/5; person_previous:template:0 0/10; who_did:dev:0 24/29; why:dev:0 36/36

Error causes: low_confidence 351; wrong_intent 3

Rule baseline (development grammar): exact OK 348/348, handled CLARIFY 6/6 (1.000), handled REFUSE 136/136 (1.000), false OK CLARIFY 0/6 (0.000), false OK REFUSE 0/136 (0.000)
Paired with the baseline (distinct texts): both right 136; only model right 0; only rules right 354; both wrong 0

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

Control questions, agent behaviour per world: {'absent': {'clarify': 300}, 'ambiguous': {'clarify': 300}, 'unsupported': {'refuse': 288, 'clarify': 12}}

- FAIL exact specification object_current: 0/127 >= 0.95
- FAIL exact specification object_first: 0/28 >= 0.95
- FAIL exact specification object_previous: 0/28 >= 0.95
- FAIL exact specification person_current: 0/54 >= 0.95
- FAIL exact specification person_first: 0/30 >= 0.95
- FAIL exact specification person_previous: 0/30 >= 0.95
- FAIL exact specification giver: 0/51 >= 0.95
- FAIL wrong accepted specifications 0/0 <= 0.02
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
- FAIL person:current: confident-error rate undefined <= 0.05

