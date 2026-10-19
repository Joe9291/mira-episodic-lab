# Round 3.5 encode run

## qwen2.5-1.5b+p8

Thresholds (calibration split): actor tau=1.0285 acceptance 0.91 precision 0.9912 (681/748); partner tau=0.0 acceptance 1.0 precision 1.0 (748/748); action tau=0.0 acceptance 1.0 precision 1.0 (748/748); object tau=0.0 acceptance 1.0 precision 0.9987 (748/748); place tau=0.0 acceptance 1.0 precision 1.0 (748/748); event_day tau=structural acceptance - precision - (0/0)

### dev, best value (tau 0): complete records 0.945 (750 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 710 | 0 | 40 | 0 | 0.947 |
| partner | 748 | 0 | 2 | 0 | 0.997 |
| action | 750 | 0 | 0 | 0 | 1.000 |
| object | 749 | 0 | 1 | 0 | 0.999 |
| place | 750 | 0 | 0 | 0 | 1.000 |
| event_day | 750 | 0 | 0 | 750 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 15/15; gave:dev:1 12/10; gave:dev:2 14/14; gave:template:0 19/19; own_put:dev:0 46/46; own_put:dev:1 43/42; own_put:dev:2 38/38; own_put:template:0 44/44; placing:dev:0 41/41; placing:dev:1 55/55; placing:dev:2 48/48; placing:template:0 54/54; seen:dev:0 42/42; seen:dev:1 44/8; seen:dev:2 43/43; seen:template:0 63/61; went:dev:0 38/38; went:dev:1 27/27; went:dev:2 36/36; went:template:0 28/28

By role and absence: action:- 750/0/0; actor:You 300/0/0; actor:giver 58/0/2; actor:observed_person 352/0/38; event_day:- 750/0/0; object:absent 321/0/0; object:present 428/0/1; partner:You 58/0/2; partner:absent 690/0/0; place:- 750/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.750 | 1.000 | 0.600 | 0.167 | 0.900 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 0.800 | 1.000 | 0.800 | 0.200 | 1.000 | 0 |
| person:first | 0.750 | 1.000 | 0.700 | 0.250 | 1.000 | 0 |
| person:previous | 0.600 | 1.000 | 0.600 | 0.333 | 0.900 | 0 |

3.5 criteria on dev (best value (tau 0)): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL giver:find: success LM 0.750 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.600 >= 0.95
- FAIL giver:find: confident-error rate 0.167 <= 0.05
- FAIL person:current: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.800 >= 0.95
- FAIL person:current: confident-error rate 0.200 <= 0.05
- FAIL person:first: success LM 0.750 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.700 >= 0.95
- FAIL person:first: confident-error rate 0.250 <= 0.05
- FAIL person:previous: success LM 0.600 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.600 >= 0.95
- FAIL person:previous: confident-error rate 0.333 <= 0.05

### dev, thresholds: complete records 0.920 (750 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 691 | 57 | 2 | 0 | 0.921 |
| partner | 750 | 0 | 0 | 0 | 1.000 |
| action | 750 | 0 | 0 | 0 | 1.000 |
| object | 749 | 0 | 1 | 0 | 0.999 |
| place | 750 | 0 | 0 | 0 | 1.000 |
| event_day | 750 | 0 | 0 | 750 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 15/15; gave:dev:1 12/4; gave:dev:2 14/14; gave:template:0 19/19; own_put:dev:0 46/46; own_put:dev:1 43/42; own_put:dev:2 38/38; own_put:template:0 44/44; placing:dev:0 41/41; placing:dev:1 55/55; placing:dev:2 48/46; placing:template:0 54/53; seen:dev:0 42/41; seen:dev:1 44/4; seen:dev:2 43/43; seen:template:0 63/56; went:dev:0 38/38; went:dev:1 27/27; went:dev:2 36/36; went:template:0 28/28

By role and absence: action:- 750/0/0; actor:You 300/0/0; actor:giver 52/8/0; actor:observed_person 339/49/2; event_day:- 750/0/0; object:absent 321/0/0; object:present 428/0/1; partner:You 60/0/0; partner:absent 690/0/0; place:- 750/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.700 | 1.000 | 0.600 | 0.000 | 0.550 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 0.700 | 1.000 | 0.700 | 0.000 | 0.700 | 0 |
| person:first | 0.650 | 1.000 | 0.600 | 0.077 | 0.650 | 0 |
| person:previous | 0.500 | 1.000 | 0.500 | 0.000 | 0.300 | 0 |

3.5 criteria on dev (thresholds): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL giver:find: success LM 0.700 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.600 >= 0.95
- FAIL person:current: success LM 0.700 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.700 >= 0.95
- FAIL person:first: success LM 0.650 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.600 >= 0.95
- FAIL person:first: confident-error rate 0.077 <= 0.05
- FAIL person:previous: success LM 0.500 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.500 >= 0.95

### cal, best value (tau 0): complete records 0.957 (748 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 717 | 0 | 31 | 0 | 0.959 |
| partner | 748 | 0 | 0 | 0 | 1.000 |
| action | 748 | 0 | 0 | 0 | 1.000 |
| object | 747 | 0 | 1 | 0 | 0.999 |
| place | 748 | 0 | 0 | 0 | 1.000 |
| event_day | 748 | 0 | 0 | 748 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 16/16; gave:dev:1 16/16; gave:dev:2 18/18; gave:template:0 10/10; own_put:dev:0 32/32; own_put:dev:1 50/50; own_put:dev:2 57/56; own_put:template:0 43/43; placing:dev:0 35/33; placing:dev:1 53/53; placing:dev:2 43/43; placing:template:0 51/51; seen:dev:0 42/42; seen:dev:1 47/23; seen:dev:2 41/41; seen:template:0 59/54; went:dev:0 33/33; went:dev:1 33/33; went:dev:2 33/33; went:template:0 36/36

By role and absence: action:- 748/0/0; actor:You 317/0/0; actor:giver 60/0/0; actor:observed_person 340/0/31; event_day:- 748/0/0; object:absent 324/0/0; object:present 423/0/1; partner:You 60/0/0; partner:absent 688/0/0; place:- 748/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 0.800 | 1.000 | 0.800 | 0.200 | 1.000 | 0 |
| person:previous | 0.700 | 1.000 | 0.700 | 0.222 | 0.900 | 0 |

3.5 criteria on cal (best value (tau 0)): NOT met

- FAIL person:first: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.800 >= 0.95
- FAIL person:first: confident-error rate 0.200 <= 0.05
- FAIL person:previous: success LM 0.700 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.700 >= 0.95
- FAIL person:previous: confident-error rate 0.222 <= 0.05

### cal, thresholds: complete records 0.901 (748 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 675 | 67 | 6 | 0 | 0.902 |
| partner | 748 | 0 | 0 | 0 | 1.000 |
| action | 748 | 0 | 0 | 0 | 1.000 |
| object | 747 | 0 | 1 | 0 | 0.999 |
| place | 748 | 0 | 0 | 0 | 1.000 |
| event_day | 748 | 0 | 0 | 748 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 16/16; gave:dev:1 16/8; gave:dev:2 18/18; gave:template:0 10/10; own_put:dev:0 32/32; own_put:dev:1 50/50; own_put:dev:2 57/56; own_put:template:0 43/43; placing:dev:0 35/33; placing:dev:1 53/53; placing:dev:2 43/43; placing:template:0 51/50; seen:dev:0 42/36; seen:dev:1 47/7; seen:dev:2 41/41; seen:template:0 59/43; went:dev:0 33/33; went:dev:1 33/33; went:dev:2 33/33; went:template:0 36/36

By role and absence: action:- 748/0/0; actor:You 317/0/0; actor:giver 52/8/0; actor:observed_person 306/59/6; event_day:- 748/0/0; object:absent 324/0/0; object:present 423/0/1; partner:You 60/0/0; partner:absent 688/0/0; place:- 748/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.800 | 1.000 | 0.700 | 0.000 | 0.700 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 0.500 | 1.000 | 0.500 | 0.000 | 0.500 | 0 |
| person:first | 0.500 | 1.000 | 0.400 | 0.182 | 0.550 | 0 |
| person:previous | 0.700 | 1.000 | 0.700 | 0.000 | 0.400 | 0 |

3.5 criteria on cal (thresholds): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL giver:find: success LM 0.800 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.700 >= 0.95
- FAIL person:current: success LM 0.500 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.500 >= 0.95
- FAIL person:first: success LM 0.500 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.400 >= 0.95
- FAIL person:first: confident-error rate 0.182 <= 0.05
- FAIL person:previous: success LM 0.700 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.700 >= 0.95

