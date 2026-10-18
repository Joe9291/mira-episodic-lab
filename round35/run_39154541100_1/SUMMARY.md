# Round 3.5 development probe

## qwen2.5-0.5b+p3, scoring sum: complete records 0.075 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 53 | 27 |
| partner | 16 | 64 |
| action | 68 | 12 |
| object | 79 | 1 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 68/12; actor:You 32/0; actor:giver 7/9; actor:observed_person 14/18; event_day:- 80/0; object:absent 32/0; object:present 47/1; partner:You 16/0; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/3; gave:template:0 4/3; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- actor: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'Gorvin Ambery')
- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'none')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'put' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- actor: "At Brannick Bridge on day 6, Halsey Ostrin gave the heavy ladder to you." -> 'You' (true 'Halsey Ostrin')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'put' (true 'was')
- actor: "Day 10: at Pellan Bridge, you watched Dorran Corland hide the cracked clock." -> 'You' (true 'Dorran Corland')
- object: "Day 10: at Wyndle Library, you watched Fenwick Haverl leave the heavy ledger." -> 'none' (true 'heavy ledger')

## qwen2.5-0.5b+p3, scoring mean: complete records 0.087 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 63 | 17 |
| partner | 16 | 64 |
| action | 69 | 11 |
| object | 79 | 1 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 69/11; actor:You 32/0; actor:giver 8/8; actor:observed_person 23/9; event_day:- 80/0; object:absent 32/0; object:present 47/1; partner:You 16/0; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/4; gave:template:0 4/3; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'none')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'You' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'put' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'put' (true 'was')
- actor: "Day 10: at Pellan Bridge, you watched Dorran Corland hide the cracked clock." -> 'You' (true 'Dorran Corland')
- object: "Day 10: at Wyndle Library, you watched Fenwick Haverl leave the heavy ledger." -> 'none' (true 'heavy ledger')
- actor: "Day 11: at Sorrow Forge, Yelda Brack handed you the blue violin." -> 'You' (true 'Yelda Brack')
- actor: "Day 1: at Pellan Forge, Juno Haverl handed you the tiny clock." -> 'You' (true 'Juno Haverl')

## qwen2.5-0.5b+p3, scoring pmi: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 48 | 32 |
| partner | 0 | 80 |
| action | 39 | 41 |
| object | 28 | 52 |
| place | 54 | 26 |
| event_day | 80 | 0 |

By role: action:- 39/41; actor:You 0/32; actor:giver 16/0; actor:observed_person 32/0; event_day:- 80/0; object:absent 0/32; object:present 28/20; partner:You 0/16; partner:absent 0/64; place:- 54/26

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'heavy telescope while' (true 'heavy telescope')
- place: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'Ashgrove Bridge')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'put' (true 'was')
- object: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'spotted' (true 'none')
- actor: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'You')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'At Ashgrove Garden' (true 'none')
- object: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'ladder away' (true 'blue ladder')
- place: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'Halsey Drummet' (true 'Ashgrove Market')
- actor: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'Ashgrove Market' (true 'You')
- actor: "At Ashgrove Market, on day 7, you put the striped mirror away." -> 'Ashgrove Market' (true 'You')
- place: "At Ashgrove Orchard on day 1, Tamric Corland gave the tiny lantern to you." -> 'Tamric Corland' (true 'Ashgrove Orchard')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'put' (true 'was')

## qwen2.5-1.5b+p2, scoring sum: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 77 | 3 |
| partner | 1 | 79 |
| action | 75 | 5 |
| object | 72 | 8 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 75/5; actor:You 32/0; actor:giver 16/0; actor:observed_person 29/3; event_day:- 80/0; object:absent 32/0; object:present 40/8; partner:You 1/15; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'You' (true 'none')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'hid' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- object: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'none' (true 'striped map')
- object: "At Brannick Bridge on day 6, Halsey Ostrin gave the heavy ladder to you." -> 'none' (true 'heavy ladder')
- object: "At Fenhollow Chapel on day 8, Sabeth Pellow gave the tiny umbrella to you." -> 'umbrella' (true 'tiny umbrella')
- action: "Day 10: Odile Vesk was at Mossgate Library." -> 'went' (true 'was')
- action: "Day 11: Casimo Marrow was at Thornby Bridge." -> 'went' (true 'was')
- actor: "You met Brenna Pellow at Ashgrove Library on day 1." -> 'You' (true 'Brenna Pellow')
- actor: "You met Brenna Pellow at Carrow Chapel on day 1." -> 'You' (true 'Brenna Pellow')
- actor: "You met Brenna Pellow at Thornby Mill on day 1." -> 'You' (true 'Brenna Pellow')

## qwen2.5-1.5b+p2, scoring mean: complete records 0.013 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 78 | 2 |
| partner | 1 | 79 |
| action | 75 | 5 |
| object | 74 | 6 |
| place | 80 | 0 |
| event_day | 80 | 0 |

By role: action:- 75/5; actor:You 30/2; actor:giver 16/0; actor:observed_person 32/0; event_day:- 80/0; object:absent 28/4; object:present 46/2; partner:You 1/15; partner:absent 0/64; place:- 80/0

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/1; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- action: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'hid' (true 'was')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'You' (true 'none')
- action: "Day 10: Odile Vesk was at Mossgate Library." -> 'went' (true 'was')
- actor: "Day 10: you put the striped lantern down at Ashgrove Forge." -> 'Ashgrove Forge' (true 'You')
- action: "Day 11: Casimo Marrow was at Thornby Bridge." -> 'went' (true 'was')
- object: "On day 1 you made your way to Lindmere Station." -> 'made your way' (true 'none')
- object: "On day 1 you made your way to Sorrow Library." -> 'made your way' (true 'none')
- object: "On day 1, you saw Varo Drummet hid the heavy kettle at Fenhollow Bridge." -> 'kettle' (true 'heavy kettle')
- actor: "You visited Ashgrove Forge on day 10." -> 'Ashgrove Forge' (true 'You')

## qwen2.5-1.5b+p2, scoring pmi: complete records 0.000 (80 texts)

| slot | correct | wrong |
|---|---|---|
| actor | 44 | 36 |
| partner | 0 | 80 |
| action | 75 | 5 |
| object | 38 | 42 |
| place | 54 | 26 |
| event_day | 80 | 0 |

By role: action:- 75/5; actor:You 0/32; actor:giver 15/1; actor:observed_person 29/3; event_day:- 80/0; object:absent 0/32; object:present 38/10; partner:You 0/16; partner:absent 0/64; place:- 54/26

By frame (texts/complete): gave:dev:0 4/0; gave:dev:1 4/0; gave:dev:2 4/0; gave:template:0 4/0; own_put:dev:0 4/0; own_put:dev:1 4/0; own_put:dev:2 4/0; own_put:template:0 4/0; placing:dev:0 4/0; placing:dev:1 4/0; placing:dev:2 4/0; placing:template:0 4/0; seen:dev:0 4/0; seen:dev:1 4/0; seen:dev:2 4/0; seen:template:0 4/0; went:dev:0 4/0; went:dev:1 4/0; went:dev:2 4/0; went:template:0 4/0

Examples of wrong slots:

- partner: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'none')
- object: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'heavy telescope while' (true 'heavy telescope')
- place: "At Ashgrove Bridge on day 6, Gorvin Ambery put the heavy telescope while you were watching." -> 'Gorvin Ambery' (true 'Ashgrove Bridge')
- partner: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'none')
- object: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'on day' (true 'none')
- place: "At Ashgrove Forge on day 7, you spotted Casimo Marrow." -> 'Casimo Marrow' (true 'Ashgrove Forge')
- actor: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'You')
- partner: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'Ashgrove Garden' (true 'none')
- object: "At Ashgrove Garden, on day 3, you put the blue ladder away." -> 'blue ladder away' (true 'blue ladder')
- place: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'Halsey Drummet' (true 'Ashgrove Market')
- actor: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'Ashgrove Market' (true 'You')
- actor: "At Ashgrove Market, on day 7, you put the striped mirror away." -> 'Ashgrove Market' (true 'You')
- action: "Day 10: Odile Vesk was at Mossgate Library." -> 'went' (true 'was')
- action: "Day 10: at Pellan Station, you watched Odile Brack leave the silver compass." -> 'went' (true 'left')
- action: "Day 10: at Wyndle Library, you watched Fenwick Haverl leave the heavy ledger." -> 'went' (true 'left')

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

