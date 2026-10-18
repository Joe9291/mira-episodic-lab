# Round 3.5 development probe

## qwen2.5-0.5b: complete records 0.000 (80 texts)

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
- partner: "At Ashgrove Market on day 14, Halsey Drummet left the striped map while you were watching." -> 'You' (true 'none')
- object: "At Ashgrove Market, on day 13, you put the cracked ledger away." -> 'ledger' (true 'cracked ledger')
- object: "At Ashgrove Market, on day 8, you put the tiny map away." -> 'map' (true 'tiny map')
- actor: "At Ashgrove Orchard on day 1, Tamric Corland gave the tiny lantern to you." -> 'You' (true 'Tamric Corland')
- action: "At Brannick Chapel on day 4, you spotted Fenwick Tellin." -> 'put' (true 'was')
- action: "At Brannick Garden on day 13, you spotted Quillon Quist." -> 'hid' (true 'was')
- action: "At Brannick Garden on day 2, you spotted Brenna Brack." -> 'put' (true 'was')

