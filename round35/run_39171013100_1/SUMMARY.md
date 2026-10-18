# Round 3.5 development probe

## qwen2.5-1.5b+p3, scoring sum: complete records 0.713 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 79 | 1 |
| partner | 59 | 21 |
| action | 80 | 0 |
| object | 79 | 1 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 32/0; actor:giver 15/1; actor:observed_person 32/0; event_day:- 80/0; object:absent 32/0; object:present 47/1; partner:You 11/5; partner:absent 48/16; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/3; gave:dev:2 4/4; gave:template:0 4/3; own_put:dev:0 4/3; own_put:dev:1 4/0; own_put:dev:2 4/4; own_put:template:0 4/2; placing:dev:0 4/3; placing:dev:1 4/1; placing:dev:2 4/1; placing:template:0 4/3; seen:dev:0 4/2; seen:dev:1 4/4; seen:dev:2 4/4; seen:template:0 4/4; went:dev:0 4/4; went:dev:1 4/4; went:dev:2 4/4; went:template:0 4/4

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- partner: "At Ashgrove Orchard on day 7, Tamric Corland left the copper basket while you were watching." -> 'Tamric Corland' (true 'none')
- partner: "At Brannick Forge on day 11, Odile Haverl put the silver basket while you were watching." -> 'Odile Haverl' (true 'none')
- object: "Day 10: at Wyndle Library, you watched Fenwick Haverl leave the heavy ledger." -> 'ledger' (true 'heavy ledger')
- actor: "You got the copper mirror from Marit Ambery at Sorrow Orchard on day 12." -> 'You' (true 'Marit Ambery')

## qwen2.5-1.5b+p3, scoring mean: complete records 0.688 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 79 | 1 |
| partner | 57 | 23 |
| action | 80 | 0 |
| object | 79 | 1 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 32/0; actor:giver 15/1; actor:observed_person 32/0; event_day:- 80/0; object:absent 32/0; object:present 47/1; partner:You 10/6; partner:absent 47/17; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/3; gave:dev:2 4/4; gave:template:0 4/2; own_put:dev:0 4/3; own_put:dev:1 4/0; own_put:dev:2 4/4; own_put:template:0 4/2; placing:dev:0 4/3; placing:dev:1 4/1; placing:dev:2 4/1; placing:template:0 4/3; seen:dev:0 4/1; seen:dev:1 4/4; seen:dev:2 4/4; seen:template:0 4/4; went:dev:0 4/4; went:dev:1 4/4; went:dev:2 4/4; went:template:0 4/4

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- partner: "At Ashgrove Orchard on day 7, Tamric Corland left the copper basket while you were watching." -> 'Tamric Corland' (true 'none')
- partner: "At Brannick Forge on day 11, Odile Haverl put the silver basket while you were watching." -> 'Odile Haverl' (true 'none')
- object: "Day 10: at Wyndle Library, you watched Fenwick Haverl leave the heavy ledger." -> 'ledger' (true 'heavy ledger')
- actor: "You got the copper mirror from Marit Ambery at Sorrow Orchard on day 12." -> 'You' (true 'Marit Ambery')

## qwen2.5-1.5b+p3, scoring pmi: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 47 | 33 |
| partner | 0 | 80 |
| action | 80 | 0 |
| object | 40 | 40 |
| place | 55 | 25 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 0/32; actor:giver 16/0; actor:observed_person 31/1; event_day:- 80/0; object:absent 0/32; object:present 40/8; partner:You 0/16; partner:absent 0/64; place:- 55/25

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'heavy telescope while' (true 'heavy telescope')
- place: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'Ashgrove Bridge')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- object: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'spotted' (true 'none')
- actor: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'You')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'none')
- place: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'Ashgrove Garden')
- object: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'left the striped' (true 'striped map')
- place: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'Halsey Drummet' (true 'Ashgrove Market')
- actor: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'Ashgrove Market' (true 'You')
- actor: "At Ashgrove Market, on day 7, you put the striped mirror away." -> 'Ashgrove Market' (true 'You')

## qwen2.5-1.5b+p5, scoring sum: complete records 0.750 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 80 | 0 |
| partner | 60 | 20 |
| action | 80 | 0 |
| object | 80 | 0 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 32/0; actor:giver 16/0; actor:observed_person 32/0; event_day:- 80/0; object:absent 32/0; object:present 48/0; partner:You 16/0; partner:absent 44/20; place:- 80/0

By frame (texts/complete): gave:dev:0 4/4; gave:dev:1 4/4; gave:dev:2 4/4; gave:template:0 4/4; own_put:dev:0 4/1; own_put:dev:1 4/0; own_put:dev:2 4/4; own_put:template:0 4/0; placing:dev:0 4/4; placing:dev:1 4/1; placing:dev:2 4/4; placing:template:0 4/2; seen:dev:0 4/4; seen:dev:1 4/4; seen:dev:2 4/4; seen:template:0 4/4; went:dev:0 4/4; went:dev:1 4/0; went:dev:2 4/4; went:template:0 4/4

Examples of wrong slots:

- partner: "Day 10: you put the striped lantern down at Ashgrove Forge." -> 'You' (true 'none')
- partner: "Day 11: you put the wooden map down at Thornby Forge." -> 'You' (true 'none')
- partner: "Day 12: you put the blue map down at Thornby Station." -> 'You' (true 'none')

## qwen2.5-1.5b+p5, scoring mean: complete records 0.750 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 80 | 0 |
| partner | 60 | 20 |
| action | 80 | 0 |
| object | 80 | 0 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 32/0; actor:giver 16/0; actor:observed_person 32/0; event_day:- 80/0; object:absent 32/0; object:present 48/0; partner:You 16/0; partner:absent 44/20; place:- 80/0

By frame (texts/complete): gave:dev:0 4/4; gave:dev:1 4/4; gave:dev:2 4/4; gave:template:0 4/4; own_put:dev:0 4/1; own_put:dev:1 4/0; own_put:dev:2 4/4; own_put:template:0 4/0; placing:dev:0 4/4; placing:dev:1 4/1; placing:dev:2 4/4; placing:template:0 4/2; seen:dev:0 4/4; seen:dev:1 4/4; seen:dev:2 4/4; seen:template:0 4/4; went:dev:0 4/4; went:dev:1 4/0; went:dev:2 4/4; went:template:0 4/4

Examples of wrong slots:

- partner: "Day 10: you put the striped lantern down at Ashgrove Forge." -> 'You' (true 'none')
- partner: "Day 11: you put the wooden map down at Thornby Forge." -> 'You' (true 'none')
- partner: "Day 12: you put the blue map down at Thornby Station." -> 'You' (true 'none')

## qwen2.5-1.5b+p5, scoring pmi: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 47 | 33 |
| partner | 0 | 80 |
| action | 80 | 0 |
| object | 32 | 48 |
| place | 55 | 25 |
| event_day | 80 | 0 |

By role: action:- 80/0; actor:You 0/32; actor:giver 16/0; actor:observed_person 31/1; event_day:- 80/0; object:absent 0/32; object:present 32/16; partner:You 0/16; partner:absent 0/64; place:- 55/25

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'heavy telescope while' (true 'heavy telescope')
- place: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'Ashgrove Bridge')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'At Ashgrove Forge' (true 'none')
- object: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'on' (true 'none')
- actor: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'You')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'none')
- object: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'put the blue' (true 'blue ladder')
- place: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'Halsey Drummet' (true 'Ashgrove Market')
- actor: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'Ashgrove Market' (true 'You')
- actor: "At Ashgrove Market, on day 7, you put the striped mirror away." -> 'Ashgrove Market' (true 'You')
- place: "At Ashgrove Orchard on day 1, Tamric Corland gave the tiny lantern to you." -> 'Tamric Corland' (true 'Ashgrove Orchard')

Cache checks: r35_probe_qwen2.5-1.5b+p3_dev_0.json: max diff 1.45e-04, same choices True; r35_probe_qwen2.5-1.5b+p5_dev_0.json: max diff 1.32e-04, same choices True
