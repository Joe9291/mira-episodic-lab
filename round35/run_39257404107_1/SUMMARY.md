# Round 3.5 encode run

## qwen2.5-1.5b+p8

### res, best value (tau 0): complete records 0.994 (2974 texts)

| slot | correct | unknown | wrong | single-value (from text / from schema) | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 2970 | 0 | 4 | 0 (0 / 0) | 0.999 |
| partner | 2964 | 0 | 10 | 240 (0 / 240) | 0.996 |
| action | 2971 | 0 | 3 | 0 (0 / 0) | 0.999 |
| object | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| place | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| event_day | 2974 | 0 | 0 | 2974 (2974 / 0) | - |

By wording frame (distinct texts / complete records correct): gave:reserve:0 78/78; gave:reserve:1 76/76; gave:reserve:2 86/86; own_put:reserve:0 230/230; own_put:reserve:1 222/222; own_put:reserve:2 226/226; placing:reserve:0 229/229; placing:reserve:1 241/241; placing:reserve:2 219/205; seen:reserve:0 263/263; seen:reserve:1 275/272; seen:reserve:2 246/246; went:reserve:0 210/210; went:reserve:1 207/207; went:reserve:2 166/166

By role and absence: action:- 2971/0/3; actor:You 1261/0/0; actor:giver 240/0/0; actor:observed_person 1469/0/4; event_day:- 2974/0/0; object:absent 1367/0/0; object:present 1607/0/0; partner:You 240/0/0; partner:absent 2724/0/10; place:- 2974/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |

3.5 criteria on res (best value (tau 0)): all met


### res, thresholds: complete records 0.994 (2974 texts)

| slot | correct | unknown | wrong | single-value (from text / from schema) | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 2970 | 0 | 4 | 0 (0 / 0) | 0.999 |
| partner | 2964 | 0 | 10 | 240 (0 / 240) | 0.996 |
| action | 2971 | 0 | 3 | 0 (0 / 0) | 0.999 |
| object | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| place | 2974 | 0 | 0 | 0 (0 / 0) | 1.000 |
| event_day | 2974 | 0 | 0 | 2974 (2974 / 0) | - |

Schema-constrained controls (same candidates, decoder and thresholds, model scores replaced): uniform scores: complete records 0.000, slots decided 2974/17844, of these correct 1.000; random scores: complete records 0.000, slots decided 17844/17844, of these correct 0.327

By wording frame (distinct texts / complete records correct): gave:reserve:0 78/78; gave:reserve:1 76/76; gave:reserve:2 86/86; own_put:reserve:0 230/230; own_put:reserve:1 222/222; own_put:reserve:2 226/226; placing:reserve:0 229/229; placing:reserve:1 241/241; placing:reserve:2 219/205; seen:reserve:0 263/263; seen:reserve:1 275/272; seen:reserve:2 246/246; went:reserve:0 210/210; went:reserve:1 207/207; went:reserve:2 166/166

Class diagnostics (texts / wrong / unknown / smallest correct margin): adjective:blue 186/0/0/1.81; adjective:copper 199/0/0/2.25; adjective:cracked 217/0/0/2.89; adjective:heavy 201/0/0/1.03; adjective:silver 204/0/0/2.47; adjective:striped 202/0/0/1.96; adjective:tiny 199/0/0/3.05; adjective:wooden 199/0/0/0.66; frame:gave:reserve:0 78/0/0/3.59; frame:gave:reserve:1 76/0/0/2.47; frame:gave:reserve:2 86/0/0/1.3; frame:own_put:reserve:0 230/0/0/3.12; frame:own_put:reserve:1 222/0/0/1.03; frame:own_put:reserve:2 226/0/0/2.44; frame:placing:reserve:0 229/0/0/0.49; frame:placing:reserve:1 241/0/0/0.19; frame:placing:reserve:2 219/14/0/0.07; frame:seen:reserve:0 263/0/0/1.98; frame:seen:reserve:1 275/3/0/0.08; frame:seen:reserve:2 246/0/0/1.04; frame:went:reserve:0 210/0/0/4.23; frame:went:reserve:1 207/0/0/5.4; frame:went:reserve:2 166/0/0/0.73; role:action:- 2974/3/0/0.08; role:actor:You 1261/0/0/0.73; role:actor:giver 240/0/0/4.4; role:actor:observed_person 1473/4/0/0.07; role:event_day:- 2974/0/0/-; role:object:absent 1367/0/0/12.65; role:object:present 1607/0/0/0.66; role:partner:You 240/0/0/-; role:partner:absent 2734/10/0/0.16; role:place:- 2974/0/0/4.08

By role and absence: action:- 2971/0/3; actor:You 1261/0/0; actor:giver 240/0/0; actor:observed_person 1469/0/4; event_day:- 2974/0/0; object:absent 1367/0/0; object:present 1607/0/0; partner:You 240/0/0; partner:absent 2724/0/10; place:- 2974/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |

3.5 criteria on res (thresholds): all met


Original round 3.3 / 3.4 milestone rules on the LM system (res):

- PASS every case planned for intact, none, random, relevant_removed is available
- PASS swapped_binding and irrelevant_removed available in >= 90% of planned cases
- PASS informative cases (prediction != truth) >= 60% of planned for swap and relevant removal
- PASS intact: success 1.0 and pair success 1.0
- PASS no memory and random memory: pair success 0 (fixed, deterministic exploration policy)
- PASS swapped binding: action as predicted in >= 0.95 of informative cases
- PASS relevant episode removed: action as predicted in >= 0.95 of informative cases
- PASS irrelevant episode removed: success 1.0
- PASS availability: every planned case of intact, none, old_removed, last_removed, irrelevant_removed
- PASS availability: old_swapped in >= 90% of planned cases
- PASS informative cases >= 60% of planned (first goal: old_removed, old_swapped; current goal: last_removed)
- PASS episodic intact: success 1.0 for all goals, pair success 1.0 for the first goal
- PASS state_only: success 1.0 for the current goal, pair success 0.0 for the first goal
- PASS episodic none: pair success 0.0 for the first goal
- PASS old_removed, old_swapped: first goal as predicted >= 0.95 (informative); current and previous unchanged 1.0
- PASS last_removed: current goal as predicted >= 0.95 (informative); first goal unchanged 1.0
- PASS irrelevant_removed: success 1.0 for all goals

Comparison decodings (same encodings and thresholds; the primary result is the frozen decoding above):

- d2 (no schema rules F1/F2): complete records 0.979; 3.5 criteria NOT met; cells below 1 (success/pair): giver:find 0.938/0.925
- F1 only: complete records 0.983; 3.5 criteria NOT met; cells below 1 (success/pair): giver:find 0.938/0.925
- F2 only: complete records 0.991; 3.5 criteria met; cells below 1 (success/pair): every cell 1.000

Error consequences (0 world decisions wrong or not from memory; 0 wrong):


