# Round 3.5 encode run

## qwen2.5-1.5b+p8

### ho, best value (tau 0): complete records 0.959 (2974 texts)

| slot | correct | unknown | wrong | single-value (from text / from schema) | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 2954 | 0 | 20 | 0 (0 / 0) | 0.993 |
| partner | 2947 | 0 | 27 | 0 (0 / 0) | 0.991 |
| action | 2905 | 0 | 69 | 0 (0 / 0) | 0.977 |
| object | 2968 | 0 | 6 | 0 (0 / 0) | 0.998 |
| place | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| event_day | 2974 | 0 | 0 | 2974 (2974 / 0) | - |

By role and absence: action:- 2905/0/69; actor:You 1208/0/5; actor:giver 239/0/1; actor:observed_person 1507/0/14; event_day:- 2974/0/0; object:absent 1296/0/0; object:present 1672/0/6; partner:You 230/0/10; partner:absent 2717/0/17; place:- 2974/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.938 | 1.000 | 0.925 | 0.000 | 0.925 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 0.988 | 1.000 | 0.975 | 0.013 | 1.000 | 0 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |

3.5 criteria on ho (best value (tau 0)): NOT met

- FAIL giver:find: success LM 0.938 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.925 >= 0.95

### ho, thresholds: complete records 0.959 (2974 texts)

| slot | correct | unknown | wrong | single-value (from text / from schema) | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 2954 | 0 | 20 | 0 (0 / 0) | 0.993 |
| partner | 2947 | 0 | 27 | 0 (0 / 0) | 0.991 |
| action | 2905 | 0 | 69 | 0 (0 / 0) | 0.977 |
| object | 2968 | 0 | 6 | 0 (0 / 0) | 0.998 |
| place | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| event_day | 2974 | 0 | 0 | 2974 (2974 / 0) | - |

Schema-constrained controls (same candidates, decoder and thresholds, model scores replaced): uniform scores: complete records 0.000, slots decided 2974/17844, of these correct 1.000; random scores: complete records 0.000, slots decided 17844/17844, of these correct 0.299

By role and absence: action:- 2905/0/69; actor:You 1208/0/5; actor:giver 239/0/1; actor:observed_person 1507/0/14; event_day:- 2974/0/0; object:absent 1296/0/0; object:present 1672/0/6; partner:You 230/0/10; partner:absent 2717/0/17; place:- 2974/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.938 | 1.000 | 0.925 | 0.000 | 0.925 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 0.988 | 1.000 | 0.975 | 0.013 | 1.000 | 0 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |

3.5 criteria on ho (thresholds): NOT met

- FAIL giver:find: success LM 0.938 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.925 >= 0.95

Original round 3.3 / 3.4 milestone rules on the LM system (holdout):

- PASS every case planned for intact, none, random, relevant_removed is available
- PASS swapped_binding and irrelevant_removed available in >= 90% of planned cases
- PASS informative cases (prediction != truth) >= 60% of planned for swap and relevant removal
- FAIL intact: success 1.0 and pair success 1.0
- PASS no memory and random memory: pair success 0 (fixed, deterministic exploration policy)
- FAIL swapped binding: action as predicted in >= 0.95 of informative cases
- FAIL relevant episode removed: action as predicted in >= 0.95 of informative cases
- FAIL irrelevant episode removed: success 1.0
- PASS availability: every planned case of intact, none, old_removed, last_removed, irrelevant_removed
- PASS availability: old_swapped in >= 90% of planned cases
- PASS informative cases >= 60% of planned (first goal: old_removed, old_swapped; current goal: last_removed)
- FAIL episodic intact: success 1.0 for all goals, pair success 1.0 for the first goal
- PASS state_only: success 1.0 for the current goal, pair success 0.0 for the first goal
- PASS episodic none: pair success 0.0 for the first goal
- PASS old_removed, old_swapped: first goal as predicted >= 0.95 (informative); current and previous unchanged 1.0
- PASS last_removed: current goal as predicted >= 0.95 (informative); first goal unchanged 1.0
- FAIL irrelevant_removed: success 1.0 for all goals

