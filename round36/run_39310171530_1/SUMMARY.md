# Round 3.6 probe (development texts, best value)

qwen2.5-1.5b+q1: mean 11.15 s per question (max 13.52)

#### qwen2.5-1.5b+q1: 46/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 2/4 (0.500) |
| exact:object_current:absent | 4/4 (1.000) |
| exact:object_current | 6/8 (0.750) |
| exact:object_first:goal | 7/7 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 7/7 (1.000) |
| exact:object_previous:goal | 7/7 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 7/7 (1.000) |
| exact:person_current:goal | 0/3 (0.000) |
| exact:person_current:absent | 0/5 (0.000) |
| exact:person_current | 0/8 (0.000) |
| exact:person_first:goal | 7/7 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 7/7 (1.000) |
| exact:person_previous:goal | 7/7 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 7/7 (1.000) |
| exact:giver:goal | 3/3 (1.000) |
| exact:giver:absent | 4/5 (0.800) |
| exact:giver | 7/8 (0.875) |
| wrong_accepted | 17/58 (0.293) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 11/12 (0.917) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 0/12 (0.000) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 5/52 (0.096) |
| family macro CLARIFY / REFUSE | 1.0 / 0.0 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 0/2; REFUSE:event_relative 0/2; REFUSE:future 0/2; REFUSE:ownership 0/2; REFUSE:who_did 0/2; REFUSE:why 0/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 0/2; event_relative:dev:0 0/2; first_name:dev:0 2/2; future:dev:0 0/2; giver:dev:0 2/2; giver:dev:1 1/2; giver:dev:2 2/2; giver:template:0 2/2; object_current:dev:0 2/2; object_current:dev:1 0/2; object_current:dev:2 2/2; object_current:template:0 2/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 0/2; person_current:dev:0 0/2; person_current:dev:1 0/2; person_current:dev:2 0/2; person_current:template:0 0/2; person_first:dev:0 2/2; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 2/2; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 0/2; why:dev:0 0/2

Error causes: wrong_intent 22; wrong_target 1

- 'Find Dorran Lunsey.': gold OK person_current Dorran Lunsey -> OK person_first Dorran Lunsey (None)
- 'Find Halsey Ostrin.': gold OK person_current Halsey Ostrin -> OK person_first Halsey Ostrin (None)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY object_first None (no_referent)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY object_current None (no_referent)
- 'Go to the person you got the cracked map from.': gold OK giver cracked map -> CLARIFY giver None (no_referent)
- 'How many times was the blue basket moved?': gold REFUSE unsupported None -> OK object_current blue basket (None)
- 'How many times was the blue map moved?': gold REFUSE unsupported None -> OK object_current blue map (None)
- 'Take me to the blue clock.': gold OK object_current blue clock -> OK object_first blue clock (None)
- 'Take me to the blue map.': gold OK object_current blue map -> OK object_first blue map (None)
- 'Take me to where Casimo Haverl was last seen.': gold OK person_current Casimo Haverl -> OK person_previous Casimo Haverl (None)
- 'Take me to where Casimo Marrow was last seen.': gold OK person_current Casimo Marrow -> OK person_previous Casimo Marrow (None)
- 'Where is Brenna Marrow now?': gold OK person_current Brenna Marrow -> CLARIFY object_current None (no_referent)
- 'Where is Dorran Marrow now?': gold OK person_current Dorran Marrow -> CLARIFY object_current None (no_referent)
- 'Where was Elvie Ostrin right before they gave you the silver mirror?': gold REFUSE unsupported None -> OK object_previous silver mirror (None)
- 'Where was Gorvin Drummet right before they gave you the striped compass?': gold REFUSE unsupported None -> CLARIFY object_previous None (no_referent)
- 'Where will the blue lantern be tomorrow?': gold REFUSE unsupported None -> OK object_current blue lantern (None)
- 'Where will the copper clock be tomorrow?': gold REFUSE unsupported None -> OK object_current copper clock (None)
- 'Who does the blue clock belong to?': gold REFUSE unsupported None -> OK object_current blue clock (None)
- 'Who does the copper map belong to?': gold REFUSE unsupported None -> OK object_current copper map (None)
- 'Who put the blue basket at Ashgrove Market?': gold REFUSE unsupported None -> OK object_current blue basket (None)
- 'Who put the copper ledger at Brannick Station?': gold REFUSE unsupported None -> OK object_first copper ledger (None)
- 'Why did Casimo Haverl put the wooden ladder there?': gold REFUSE unsupported None -> OK object_current wooden ladder (None)
- 'Why did Elvie Haverl put the copper kettle there?': gold REFUSE unsupported None -> OK object_current copper kettle (None)

qwen2.5-1.5b+q2: mean 11.82 s per question (max 51.33)

#### qwen2.5-1.5b+q2: 42/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 1/4 (0.250) |
| exact:object_current:absent | 2/4 (0.500) |
| exact:object_current | 3/8 (0.375) |
| exact:object_first:goal | 7/7 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 7/7 (1.000) |
| exact:object_previous:goal | 7/7 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 7/7 (1.000) |
| exact:person_current:goal | 0/3 (0.000) |
| exact:person_current:absent | 0/5 (0.000) |
| exact:person_current | 0/8 (0.000) |
| exact:person_first:goal | 6/7 (0.857) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 6/7 (0.857) |
| exact:person_previous:goal | 7/7 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 7/7 (1.000) |
| exact:giver:goal | 1/3 (0.333) |
| exact:giver:absent | 3/5 (0.600) |
| exact:giver | 4/8 (0.500) |
| wrong_accepted | 16/50 (0.320) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 7/12 (0.583) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 3/12 (0.250) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 9/52 (0.173) |
| family macro CLARIFY / REFUSE | 1.0 / 0.25 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 0/2; REFUSE:event_relative 0/2; REFUSE:future 1/2; REFUSE:ownership 0/2; REFUSE:who_did 0/2; REFUSE:why 2/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 0/2; event_relative:dev:0 0/2; first_name:dev:0 2/2; future:dev:0 1/2; giver:dev:0 2/2; giver:dev:1 2/2; giver:dev:2 0/2; giver:template:0 0/2; object_current:dev:0 2/2; object_current:dev:1 0/2; object_current:dev:2 1/2; object_current:template:0 0/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 0/2; person_current:dev:0 0/2; person_current:dev:1 0/2; person_current:dev:2 0/2; person_current:template:0 0/2; person_first:dev:0 2/2; person_first:dev:1 1/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 2/2; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 0/2; why:dev:0 2/2

Error causes: wrong_intent 22; wrong_target 5

- 'Find Dorran Lunsey.': gold OK person_current Dorran Lunsey -> OK person_first Dorran Lunsey (None)
- 'Find Halsey Ostrin.': gold OK person_current Halsey Ostrin -> OK person_first Halsey Ostrin (None)
- 'Find the blue ledger.': gold OK object_current blue ledger -> OK object_first blue ledger (None)
- 'Find the copper clock.': gold OK object_current copper clock -> OK object_first copper clock (None)
- 'Find the person who gave you the striped basket.': gold OK giver striped basket -> CLARIFY giver None (no_referent)
- 'Find the person who gave you the wooden clock.': gold OK giver wooden clock -> CLARIFY giver None (no_referent)
- 'Find whoever handed you the blue kettle.': gold OK giver blue kettle -> CLARIFY giver None (no_referent)
- 'Find whoever handed you the blue map.': gold OK giver blue map -> CLARIFY giver None (no_referent)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY giver None (no_referent)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY giver None (no_referent)
- 'Go to the place where Casimo Haverl first appeared.': gold OK person_first Casimo Haverl -> CLARIFY person_first None (no_referent)
- 'How many times was the blue basket moved?': gold REFUSE unsupported None -> OK object_previous blue basket (None)
- 'How many times was the blue map moved?': gold REFUSE unsupported None -> OK object_previous blue map (None)
- 'I need the blue clock - where is it?': gold OK object_current blue clock -> OK object_first blue clock (None)
- 'Take me to the blue clock.': gold OK object_current blue clock -> OK giver blue clock (None)
- 'Take me to the blue map.': gold OK object_current blue map -> OK giver blue map (None)
- 'Take me to where Casimo Haverl was last seen.': gold OK person_current Casimo Haverl -> OK person_previous Casimo Haverl (None)
- 'Take me to where Casimo Marrow was last seen.': gold OK person_current Casimo Marrow -> OK person_previous Casimo Marrow (None)
- 'Where is Brenna Marrow now?': gold OK person_current Brenna Marrow -> CLARIFY object_current None (no_referent)
- 'Where is Dorran Marrow now?': gold OK person_current Dorran Marrow -> CLARIFY object_current None (no_referent)
- 'Where was Elvie Ostrin right before they gave you the silver mirror?': gold REFUSE unsupported None -> OK object_previous silver mirror (None)
- 'Where was Gorvin Drummet right before they gave you the striped compass?': gold REFUSE unsupported None -> OK object_previous striped compass (None)
- 'Where will the copper clock be tomorrow?': gold REFUSE unsupported None -> OK object_previous copper clock (None)
- 'Who does the blue clock belong to?': gold REFUSE unsupported None -> OK giver blue clock (None)
- 'Who does the copper map belong to?': gold REFUSE unsupported None -> OK giver copper map (None)

