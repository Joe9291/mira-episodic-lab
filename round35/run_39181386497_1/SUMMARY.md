# Round 3.5 encode run

## qwen2.5-1.5b+p7

Thresholds (calibration split): actor tau=0.7481 acceptance 0.949 precision 0.9901 (710/748); partner tau=1.5882 acceptance 0.600 precision 0.9911 (449/748); action tau=0.0 acceptance 1.000 precision 1.0 (748/748); object tau=0.0 acceptance 1.000 precision 0.9987 (748/748); place tau=0.0 acceptance 1.000 precision 1.0 (748/748); event_day tau=none acceptance 0.000 precision - (0/0)

### dev, best value (tau 0): complete records 0.849 (750 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 720 | 0 | 30 | 0 | 0.960 |
| partner | 668 | 0 | 82 | 0 | 0.891 |
| action | 750 | 0 | 0 | 0 | 1.000 |
| object | 748 | 0 | 2 | 0 | 0.997 |
| place | 750 | 0 | 0 | 0 | 1.000 |
| event_day | 750 | 0 | 0 | 750 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 15/15; gave:dev:1 12/12; gave:dev:2 14/14; gave:template:0 19/19; own_put:dev:0 46/6; own_put:dev:1 43/14; own_put:dev:2 38/38; own_put:template:0 44/37; placing:dev:0 41/40; placing:dev:1 55/55; placing:dev:2 48/48; placing:template:0 54/53; seen:dev:0 42/42; seen:dev:1 44/15; seen:dev:2 43/43; seen:template:0 63/63; went:dev:0 38/32; went:dev:1 27/27; went:dev:2 36/36; went:template:0 28/28

By role and absence: action:- 750/0/0; actor:You 300/0/0; actor:giver 60/0/0; actor:observed_person 360/0/30; event_day:- 750/0/0; object:absent 321/0/0; object:present 427/0/2; partner:You 60/0/0; partner:absent 608/0/82; place:- 750/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 0.900 | 1.000 | 0.800 | 0.100 | 1.000 | 0 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 0.800 | 1.000 | 0.800 | 0.200 | 1.000 | 0 |
| person:first | 0.800 | 1.000 | 0.800 | 0.200 | 1.000 | 0 |
| person:previous | 0.600 | 1.000 | 0.600 | 0.333 | 0.900 | 0 |

3.5 criteria on dev (best value (tau 0)): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL giver:find: success LM 0.900 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.800 >= 0.95
- FAIL giver:find: confident-error rate 0.100 <= 0.05
- FAIL person:current: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:current: pair success 0.800 >= 0.95
- FAIL person:current: confident-error rate 0.200 <= 0.05
- FAIL person:first: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.800 >= 0.95
- FAIL person:first: confident-error rate 0.200 <= 0.05
- FAIL person:previous: success LM 0.600 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.600 >= 0.95
- FAIL person:previous: confident-error rate 0.333 <= 0.05

### dev, thresholds: complete records 0.000 (750 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 703 | 40 | 7 | 0 | 0.937 |
| partner | 428 | 318 | 4 | 0 | 0.571 |
| action | 750 | 0 | 0 | 0 | 1.000 |
| object | 748 | 0 | 2 | 0 | 0.997 |
| place | 750 | 0 | 0 | 0 | 1.000 |
| event_day | 0 | 750 | 0 | 0 | 0.000 |

By wording frame (distinct texts / complete records correct): gave:dev:0 15/0; gave:dev:1 12/0; gave:dev:2 14/0; gave:template:0 19/0; own_put:dev:0 46/0; own_put:dev:1 43/0; own_put:dev:2 38/0; own_put:template:0 44/0; placing:dev:0 41/0; placing:dev:1 55/0; placing:dev:2 48/0; placing:template:0 54/0; seen:dev:0 42/0; seen:dev:1 44/0; seen:dev:2 43/0; seen:template:0 63/0; went:dev:0 38/0; went:dev:1 27/0; went:dev:2 36/0; went:template:0 28/0

By role and absence: action:- 750/0/0; actor:You 300/0/0; actor:giver 59/1/0; actor:observed_person 344/39/7; event_day:- 0/750/0; object:absent 321/0/0; object:present 427/0/2; partner:You 60/0/0; partner:absent 368/318/4; place:- 750/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 0.200 | 1.000 | 0.000 | - | 0.000 | 0 |
| moved:find | 0.200 | 1.000 | 0.000 | - | 0.000 | 0 |
| giver:find | 0.250 | 1.000 | 0.000 | - | 0.000 | 0 |
| object:current | 0.000 | 1.000 | 0.000 | - | 0.000 | 0 |
| object:first | 0.150 | 1.000 | 0.000 | - | 0.000 | 0 |
| object:previous | 0.200 | 1.000 | 0.200 | - | 0.000 | 0 |
| person:current | 0.400 | 1.000 | 0.400 | - | 0.000 | 0 |
| person:first | 0.100 | 1.000 | 0.000 | - | 0.000 | 0 |
| person:previous | 0.200 | 1.000 | 0.200 | - | 0.000 | 0 |

3.5 criteria on dev (thresholds): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL hidden:find: success LM 0.200 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.000 >= 0.95
- FAIL hidden:find: confident-error rate undefined <= 0.05
- FAIL moved:find: success LM 0.200 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.000 >= 0.95
- FAIL moved:find: confident-error rate undefined <= 0.05
- FAIL giver:find: success LM 0.250 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.000 >= 0.95
- FAIL giver:find: confident-error rate undefined <= 0.05
- FAIL object:current: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.000 >= 0.95
- FAIL object:current: confident-error rate undefined <= 0.05
- FAIL object:first: success LM 0.150 >= reference 1.000 - 0.02
- FAIL object:first: pair success 0.000 >= 0.95
- FAIL object:first: confident-error rate undefined <= 0.05
- FAIL object:previous: success LM 0.200 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.200 >= 0.95
- FAIL object:previous: confident-error rate undefined <= 0.05
- FAIL person:current: success LM 0.400 >= reference 1.000 - 0.02

### cal, best value (tau 0): complete records 0.869 (748 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 726 | 0 | 22 | 0 | 0.971 |
| partner | 673 | 0 | 75 | 0 | 0.900 |
| action | 748 | 0 | 0 | 0 | 1.000 |
| object | 747 | 0 | 1 | 0 | 0.999 |
| place | 748 | 0 | 0 | 0 | 1.000 |
| event_day | 748 | 0 | 0 | 748 | - |

By wording frame (distinct texts / complete records correct): gave:dev:0 16/16; gave:dev:1 16/16; gave:dev:2 18/18; gave:template:0 10/10; own_put:dev:0 32/5; own_put:dev:1 50/22; own_put:dev:2 57/57; own_put:template:0 43/27; placing:dev:0 35/33; placing:dev:1 53/53; placing:dev:2 43/42; placing:template:0 51/50; seen:dev:0 42/42; seen:dev:1 47/27; seen:dev:2 41/41; seen:template:0 59/59; went:dev:0 33/30; went:dev:1 33/33; went:dev:2 33/33; went:template:0 36/36

By role and absence: action:- 748/0/0; actor:You 317/0/0; actor:giver 60/0/0; actor:observed_person 349/0/22; event_day:- 748/0/0; object:absent 324/0/0; object:present 423/0/1; partner:You 60/0/0; partner:absent 613/0/75; place:- 748/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| moved:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| giver:find | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:first | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| object:previous | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:current | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1 |
| person:first | 0.900 | 1.000 | 0.900 | 0.100 | 1.000 | 0 |
| person:previous | 0.800 | 1.000 | 0.800 | 0.200 | 1.000 | 0 |

3.5 criteria on cal (best value (tau 0)): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL person:first: success LM 0.900 >= reference 1.000 - 0.02
- FAIL person:first: pair success 0.900 >= 0.95
- FAIL person:first: confident-error rate 0.100 <= 0.05
- FAIL person:previous: success LM 0.800 >= reference 1.000 - 0.02
- FAIL person:previous: pair success 0.800 >= 0.95
- FAIL person:previous: confident-error rate 0.200 <= 0.05

### cal, thresholds: complete records 0.000 (748 texts)

| slot | correct | unknown | wrong | single-value | accuracy where chosen |
|---|---|---|---|---|---|
| actor | 703 | 38 | 7 | 0 | 0.940 |
| partner | 445 | 299 | 4 | 0 | 0.595 |
| action | 748 | 0 | 0 | 0 | 1.000 |
| object | 747 | 0 | 1 | 0 | 0.999 |
| place | 748 | 0 | 0 | 0 | 1.000 |
| event_day | 0 | 748 | 0 | 0 | 0.000 |

By wording frame (distinct texts / complete records correct): gave:dev:0 16/0; gave:dev:1 16/0; gave:dev:2 18/0; gave:template:0 10/0; own_put:dev:0 32/0; own_put:dev:1 50/0; own_put:dev:2 57/0; own_put:template:0 43/0; placing:dev:0 35/0; placing:dev:1 53/0; placing:dev:2 43/0; placing:template:0 51/0; seen:dev:0 42/0; seen:dev:1 47/0; seen:dev:2 41/0; seen:template:0 59/0; went:dev:0 33/0; went:dev:1 33/0; went:dev:2 33/0; went:template:0 36/0

By role and absence: action:- 748/0/0; actor:You 317/0/0; actor:giver 59/1/0; actor:observed_person 327/37/7; event_day:- 0/748/0; object:absent 324/0/0; object:present 423/0/1; partner:You 60/0/0; partner:absent 385/299/4; place:- 748/0/0

| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |
|---|---|---|---|---|---|---|
| hidden:find | 0.200 | 1.000 | 0.000 | - | 0.000 | 0 |
| moved:find | 0.150 | 1.000 | 0.000 | - | 0.000 | 0 |
| giver:find | 0.300 | 1.000 | 0.000 | - | 0.000 | 0 |
| object:current | 0.100 | 1.000 | 0.100 | - | 0.000 | 0 |
| object:first | 0.300 | 1.000 | 0.000 | - | 0.000 | 0 |
| object:previous | 0.000 | 1.000 | 0.000 | - | 0.000 | 0 |
| person:current | 0.100 | 1.000 | 0.100 | - | 0.000 | 0 |
| person:first | 0.100 | 1.000 | 0.000 | - | 0.000 | 0 |
| person:previous | 0.300 | 1.000 | 0.300 | - | 0.000 | 0 |

3.5 criteria on cal (thresholds): NOT met

- FAIL complete records with every slot correct >= 0.95
- FAIL hidden:find: success LM 0.200 >= reference 1.000 - 0.02
- FAIL hidden:find: pair success 0.000 >= 0.95
- FAIL hidden:find: confident-error rate undefined <= 0.05
- FAIL moved:find: success LM 0.150 >= reference 1.000 - 0.02
- FAIL moved:find: pair success 0.000 >= 0.95
- FAIL moved:find: confident-error rate undefined <= 0.05
- FAIL giver:find: success LM 0.300 >= reference 1.000 - 0.02
- FAIL giver:find: pair success 0.000 >= 0.95
- FAIL giver:find: confident-error rate undefined <= 0.05
- FAIL object:current: success LM 0.100 >= reference 1.000 - 0.02
- FAIL object:current: pair success 0.100 >= 0.95
- FAIL object:current: confident-error rate undefined <= 0.05
- FAIL object:first: success LM 0.300 >= reference 1.000 - 0.02
- FAIL object:first: pair success 0.000 >= 0.95
- FAIL object:first: confident-error rate undefined <= 0.05
- FAIL object:previous: success LM 0.000 >= reference 1.000 - 0.02
- FAIL object:previous: pair success 0.000 >= 0.95
- FAIL object:previous: confident-error rate undefined <= 0.05
- FAIL person:current: success LM 0.100 >= reference 1.000 - 0.02

