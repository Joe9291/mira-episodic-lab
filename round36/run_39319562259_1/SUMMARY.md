# Round 3.6 probe (development texts, best value)

qwen2.5-1.5b+q5: mean 11.42 s per question (max 60.28)

#### qwen2.5-1.5b+q5: 49/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 2/4 (0.500) |
| exact:object_current:absent | 2/4 (0.500) |
| exact:object_current | 4/8 (0.500) |
| exact:object_first:goal | 7/7 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 7/7 (1.000) |
| exact:object_previous:goal | 7/7 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 7/7 (1.000) |
| exact:person_current:goal | 1/3 (0.333) |
| exact:person_current:absent | 1/5 (0.200) |
| exact:person_current | 2/8 (0.250) |
| exact:person_first:goal | 5/7 (0.714) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 5/7 (0.714) |
| exact:person_previous:goal | 7/7 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 7/7 (1.000) |
| exact:giver:goal | 3/3 (1.000) |
| exact:giver:absent | 5/5 (1.000) |
| exact:giver | 8/8 (1.000) |
| wrong_accepted | 11/51 (0.216) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 7/12 (0.583) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 4/12 (0.333) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 8/52 (0.154) |
| family macro CLARIFY / REFUSE | 1.0 / 0.3333333333333333 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 0/2; REFUSE:event_relative 0/2; REFUSE:future 2/2; REFUSE:ownership 0/2; REFUSE:who_did 0/2; REFUSE:why 2/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 0/2; event_relative:dev:0 0/2; first_name:dev:0 2/2; future:dev:0 2/2; giver:dev:0 2/2; giver:dev:1 2/2; giver:dev:2 2/2; giver:template:0 2/2; object_current:dev:0 2/2; object_current:dev:1 0/2; object_current:dev:2 0/2; object_current:template:0 2/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 0/2; person_current:dev:0 0/2; person_current:dev:1 0/2; person_current:dev:2 2/2; person_current:template:0 0/2; person_first:dev:0 2/2; person_first:dev:1 0/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 2/2; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 0/2; why:dev:0 2/2

Error causes: wrong_intent 20

- 'Find Dorran Lunsey.': gold OK person_current Dorran Lunsey -> CLARIFY giver None (no_referent)
- 'Find Halsey Ostrin.': gold OK person_current Halsey Ostrin -> CLARIFY giver None (no_referent)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY giver None (no_referent)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY giver None (no_referent)
- 'Go to the place where Brenna Marrow first appeared.': gold OK person_first Brenna Marrow -> CLARIFY object_first None (no_referent)
- 'Go to the place where Casimo Haverl first appeared.': gold OK person_first Casimo Haverl -> CLARIFY object_first None (no_referent)
- 'How many times was the blue basket moved?': gold REFUSE unsupported None -> CLARIFY person_first None (no_referent)
- 'How many times was the blue map moved?': gold REFUSE unsupported None -> OK object_previous blue map (None)
- 'I need the blue basket - where is it?': gold OK object_current blue basket -> OK giver blue basket (None)
- 'I need the blue clock - where is it?': gold OK object_current blue clock -> OK giver blue clock (None)
- 'Take me to the blue clock.': gold OK object_current blue clock -> OK giver blue clock (None)
- 'Take me to the blue map.': gold OK object_current blue map -> OK giver blue map (None)
- 'Where is Brenna Marrow now?': gold OK person_current Brenna Marrow -> CLARIFY object_current None (no_referent)
- 'Where is Dorran Marrow now?': gold OK person_current Dorran Marrow -> CLARIFY object_current None (no_referent)
- 'Where was Elvie Ostrin right before they gave you the silver mirror?': gold REFUSE unsupported None -> OK object_previous silver mirror (None)
- 'Where was Gorvin Drummet right before they gave you the striped compass?': gold REFUSE unsupported None -> OK object_previous striped compass (None)
- 'Who does the blue clock belong to?': gold REFUSE unsupported None -> OK giver blue clock (None)
- 'Who does the copper map belong to?': gold REFUSE unsupported None -> OK giver copper map (None)
- 'Who put the blue basket at Ashgrove Market?': gold REFUSE unsupported None -> OK giver blue basket (None)
- 'Who put the copper ledger at Brannick Station?': gold REFUSE unsupported None -> OK giver copper ledger (None)

qwen2.5-1.5b+q6: mean 18.65 s per question (max 34.81)

#### qwen2.5-1.5b+q6: 48/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 3/4 (0.750) |
| exact:object_current:absent | 3/4 (0.750) |
| exact:object_current | 6/8 (0.750) |
| exact:object_first:goal | 7/7 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 7/7 (1.000) |
| exact:object_previous:goal | 7/7 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 7/7 (1.000) |
| exact:person_current:goal | 3/3 (1.000) |
| exact:person_current:absent | 3/5 (0.600) |
| exact:person_current | 6/8 (0.750) |
| exact:person_first:goal | 7/7 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 7/7 (1.000) |
| exact:person_previous:goal | 3/7 (0.429) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 3/7 (0.429) |
| exact:giver:goal | 3/3 (1.000) |
| exact:giver:absent | 4/5 (0.800) |
| exact:giver | 7/8 (0.875) |
| wrong_accepted | 12/55 (0.218) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 10/12 (0.833) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 0/12 (0.000) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 7/52 (0.135) |
| family macro CLARIFY / REFUSE | 1.0 / 0.0 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 0/2; REFUSE:event_relative 0/2; REFUSE:future 0/2; REFUSE:ownership 0/2; REFUSE:who_did 0/2; REFUSE:why 0/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 0/2; event_relative:dev:0 0/2; first_name:dev:0 2/2; future:dev:0 0/2; giver:dev:0 2/2; giver:dev:1 1/2; giver:dev:2 2/2; giver:template:0 2/2; object_current:dev:0 2/2; object_current:dev:1 2/2; object_current:dev:2 2/2; object_current:template:0 0/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 0/2; person_current:dev:0 1/2; person_current:dev:1 1/2; person_current:dev:2 2/2; person_current:template:0 2/2; person_first:dev:0 2/2; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 1/2; person_previous:dev:1 0/1; person_previous:dev:2 2/2; person_previous:template:0 0/2; pronoun:dev:0 1/1; who_did:dev:0 0/2; why:dev:0 0/2

Error causes: wrong_intent 20; wrong_target 1

- 'Find the blue ledger.': gold OK object_current blue ledger -> CLARIFY giver None (no_referent)
- 'Find the copper clock.': gold OK object_current copper clock -> OK giver copper clock (None)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY object_current None (no_referent)
- 'Go to the person you got the cracked map from.': gold OK giver cracked map -> CLARIFY giver None (no_referent)
- 'Go to where Quillon Lunsey was seen before the latest sighting.': gold OK person_previous Quillon Lunsey -> CLARIFY giver None (no_referent)
- 'Go to where you saw Casimo Haverl before you last saw them.': gold OK person_previous Casimo Haverl -> CLARIFY object_previous None (no_referent)
- 'Go to where you saw Tamric Pellow before you last saw them.': gold OK person_previous Tamric Pellow -> OK person_current Tamric Pellow (None)
- 'How many times was the blue basket moved?': gold REFUSE unsupported None -> OK giver blue basket (None)
- 'How many times was the blue map moved?': gold REFUSE unsupported None -> OK object_current blue map (None)
- 'Where did you see Brenna Marrow before the last time?': gold OK person_previous Brenna Marrow -> CLARIFY giver None (no_referent)
- 'Where is Dorran Marrow now?': gold OK person_current Dorran Marrow -> CLARIFY object_current None (no_referent)
- 'Where was Elvie Ostrin right before they gave you the silver mirror?': gold REFUSE unsupported None -> OK object_previous silver mirror (None)
- 'Where was Gorvin Drummet right before they gave you the striped compass?': gold REFUSE unsupported None -> CLARIFY object_previous None (no_referent)
- 'Where will the blue lantern be tomorrow?': gold REFUSE unsupported None -> OK giver blue lantern (None)
- 'Where will the copper clock be tomorrow?': gold REFUSE unsupported None -> OK giver copper clock (None)
- 'Who does the blue clock belong to?': gold REFUSE unsupported None -> OK giver blue clock (None)
- 'Who does the copper map belong to?': gold REFUSE unsupported None -> OK giver copper map (None)
- 'Who put the blue basket at Ashgrove Market?': gold REFUSE unsupported None -> OK object_current blue basket (None)
- 'Who put the copper ledger at Brannick Station?': gold REFUSE unsupported None -> OK object_current copper ledger (None)
- 'Why did Casimo Haverl put the wooden ladder there?': gold REFUSE unsupported None -> CLARIFY object_current None (no_referent)
- 'Why did Elvie Haverl put the copper kettle there?': gold REFUSE unsupported None -> OK object_current copper kettle (None)

