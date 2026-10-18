# Round 3.5 development probe

## qwen2.5-0.5b, scoring sum: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 32 | 48 |
| partner | 16 | 64 |
| action | 41 | 39 |
| object | 56 | 24 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 41/39; actor:You 32/0; actor:giver 0/16; actor:observed_person 0/32; event_day:- 80/0; object:absent 29/3; object:present 27/21; partner:You 16/0; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- actor: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'Gorvin Ambery')
- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'telescope' (true 'heavy telescope')
- actor: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'Casimo Marrow')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'hid' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- object: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'ladder' (true 'blue ladder')
- actor: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'You' (true 'Halsey Drummet')
- object: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'ledger' (true 'cracked ledger')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'hid' (true 'was')

## qwen2.5-0.5b, scoring mean: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 33 | 47 |
| partner | 15 | 65 |
| action | 40 | 40 |
| object | 56 | 24 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 40/40; actor:You 32/0; actor:giver 0/16; actor:observed_person 1/31; event_day:- 80/0; object:absent 28/4; object:present 28/20; partner:You 15/1; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- actor: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'Gorvin Ambery')
- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'telescope' (true 'heavy telescope')
- actor: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'Casimo Marrow')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'hid' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- object: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'ladder' (true 'blue ladder')
- actor: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'You' (true 'Halsey Drummet')
- object: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'ledger' (true 'cracked ledger')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'hid' (true 'was')

## qwen2.5-0.5b, scoring pmi: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 48 | 32 |
| partner | 0 | 80 |
| action | 72 | 8 |
| object | 5 | 75 |
| place | 45 | 35 |
| event_day | 80 | 0 |

By role: action:- 72/8; actor:You 0/32; actor:giver 16/0; actor:observed_person 32/0; event_day:- 80/0; object:absent 0/32; object:present 5/43; partner:You 0/16; partner:absent 0/64; place:- 45/35

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'put the heavy' (true 'heavy telescope')
- place: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'At Ashgrove Bridge' (true 'Ashgrove Bridge')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- object: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'spotted' (true 'none')
- place: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'Ashgrove Forge')
- actor: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'You')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'none')
- place: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'Ashgrove Garden')
- object: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'left the striped' (true 'striped map')
- actor: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'Ashgrove Market' (true 'You')
- actor: "At Ashgrove Market, on day 7, you put the striped mirror away." -> 'Ashgrove Market' (true 'You')
- action: "Day 1: at Wyndle Chapel, Brenna Haverl handed you the blue lantern." -> 'put' (true 'gave')
- action: "Day 2: at Wyndle Orchard, Dorran Haverl handed you the blue violin." -> 'put' (true 'gave')
- action: "You got the copper umbrella from Dorran Vesk at Lindmere Forge on day 4." -> 'was' (true 'gave')

