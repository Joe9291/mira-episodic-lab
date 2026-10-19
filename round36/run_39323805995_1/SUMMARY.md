# Round 3.6 probe (development texts, best value)

qwen3-1.7b+q4: mean 6.49 s per question (max 8.02)

#### qwen3-1.7b+q4: 18/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 0/4 (0.000) |
| exact:object_current:absent | 2/4 (0.500) |
| exact:object_current | 2/8 (0.250) |
| exact:object_first:goal | 1/7 (0.143) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 1/7 (0.143) |
| exact:object_previous:goal | 0/7 (0.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 0/7 (0.000) |
| exact:person_current:goal | 1/3 (0.333) |
| exact:person_current:absent | 1/5 (0.200) |
| exact:person_current | 2/8 (0.250) |
| exact:person_first:goal | 0/7 (0.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 0/7 (0.000) |
| exact:person_previous:goal | 0/7 (0.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 0/7 (0.000) |
| exact:giver:goal | 0/3 (0.000) |
| exact:giver:absent | 0/5 (0.000) |
| exact:giver | 0/8 (0.000) |
| wrong_accepted | 0/5 (0.000) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 0/12 (0.000) |
| handled:CLARIFY | 1/5 (0.200) |
| handled:REFUSE | 12/12 (1.000) |
| recognised_ambiguity | 1/5 (0.200) |
| unnecessary | 47/52 (0.904) |
| family macro CLARIFY / REFUSE | 0.3333333333333333 / 1.0 |

Families (right / texts): CLARIFY:bare_noun 0/2; CLARIFY:first_name 0/2; CLARIFY:pronoun 1/1; REFUSE:count 2/2; REFUSE:event_relative 2/2; REFUSE:future 2/2; REFUSE:ownership 2/2; REFUSE:who_did 2/2; REFUSE:why 2/2

Wordings (right / texts): bare_noun:dev:0 0/2; count:dev:0 2/2; event_relative:dev:0 2/2; first_name:dev:0 0/2; future:dev:0 2/2; giver:dev:0 0/2; giver:dev:1 0/2; giver:dev:2 0/2; giver:template:0 0/2; object_current:dev:0 0/2; object_current:dev:1 0/2; object_current:dev:2 2/2; object_current:template:0 0/2; object_first:dev:0 0/2; object_first:dev:1 0/2; object_first:dev:2 0/1; object_first:template:0 1/2; object_previous:dev:0 0/2; object_previous:dev:1 0/1; object_previous:dev:2 0/2; object_previous:template:0 0/2; ownership:dev:0 2/2; person_current:dev:0 0/2; person_current:dev:1 0/2; person_current:dev:2 2/2; person_current:template:0 0/2; person_first:dev:0 0/2; person_first:dev:1 0/2; person_first:dev:2 0/1; person_first:template:0 0/2; person_previous:dev:0 0/2; person_previous:dev:1 0/1; person_previous:dev:2 0/2; person_previous:template:0 0/2; pronoun:dev:0 1/1; who_did:dev:0 2/2; why:dev:0 2/2

Error causes: wrong_intent 23; wrong_target 28

- 'Find Dorran Lunsey.': gold OK person_current Dorran Lunsey -> REFUSE unsupported None (None)
- 'Find Halsey Ostrin.': gold OK person_current Halsey Ostrin -> CLARIFY person_current None (no_referent)
- 'Find the basket.': gold CLARIFY object_current none -> REFUSE unsupported None (None)
- 'Find the blue ledger.': gold OK object_current blue ledger -> REFUSE unsupported None (None)
- 'Find the clock.': gold CLARIFY object_current none -> REFUSE unsupported None (None)
- 'Find the copper clock.': gold OK object_current copper clock -> REFUSE unsupported None (None)
- 'Find the person who gave you the striped basket.': gold OK giver striped basket -> CLARIFY giver None (no_referent)
- 'Find the person who gave you the wooden clock.': gold OK giver wooden clock -> CLARIFY giver None (no_referent)
- 'Find whoever handed you the blue kettle.': gold OK giver blue kettle -> CLARIFY giver None (no_referent)
- 'Find whoever handed you the blue map.': gold OK giver blue map -> CLARIFY giver None (no_referent)
- 'Go to Brenna.': gold CLARIFY person_current none -> REFUSE unsupported None (None)
- 'Go to Casimo.': gold CLARIFY person_current none -> REFUSE unsupported None (None)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> REFUSE unsupported None (None)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY giver None (no_referent)
- 'Go to the person you got the blue mirror from.': gold OK giver blue mirror -> CLARIFY giver None (no_referent)
- 'Go to the person you got the cracked map from.': gold OK giver cracked map -> CLARIFY giver None (no_referent)
- 'Go to the place the copper clock was in before it was last put somewhere.': gold OK object_previous copper clock -> CLARIFY object_previous None (no_referent)
- 'Go to the place where Brenna Marrow first appeared.': gold OK person_first Brenna Marrow -> CLARIFY object_first None (no_referent)
- 'Go to the place where Casimo Haverl first appeared.': gold OK person_first Casimo Haverl -> CLARIFY object_first None (no_referent)
- 'Go to where Quillon Lunsey was seen before the latest sighting.': gold OK person_previous Quillon Lunsey -> CLARIFY person_current None (no_referent)
- 'Go to where the copper kettle was first placed.': gold OK object_first copper kettle -> CLARIFY object_first None (no_referent)
- 'Go to where the cracked compass was before it was last placed.': gold OK object_previous cracked compass -> CLARIFY object_previous None (no_referent)
- 'Go to where the striped compass was before it was last placed.': gold OK object_previous striped compass -> CLARIFY object_previous None (no_referent)
- 'Go to where you first saw Elvie Ostrin.': gold OK person_first Elvie Ostrin -> CLARIFY object_first None (no_referent)
- 'Go to where you first saw Tamric Pellow.': gold OK person_first Tamric Pellow -> CLARIFY object_first None (no_referent)

qwen3-1.7b+q5: mean 96.78 s per question (max 170.86)

#### qwen3-1.7b+q5: 62/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 2/4 (0.500) |
| exact:object_current:absent | 3/4 (0.750) |
| exact:object_current | 5/8 (0.625) |
| exact:object_first:goal | 7/7 (1.000) |
| exact:object_first:absent | 0/0 |
| exact:object_first | 7/7 (1.000) |
| exact:object_previous:goal | 7/7 (1.000) |
| exact:object_previous:absent | 0/0 |
| exact:object_previous | 7/7 (1.000) |
| exact:person_current:goal | 2/3 (0.667) |
| exact:person_current:absent | 2/5 (0.400) |
| exact:person_current | 4/8 (0.500) |
| exact:person_first:goal | 7/7 (1.000) |
| exact:person_first:absent | 0/0 |
| exact:person_first | 7/7 (1.000) |
| exact:person_previous:goal | 7/7 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 7/7 (1.000) |
| exact:giver:goal | 3/3 (1.000) |
| exact:giver:absent | 5/5 (1.000) |
| exact:giver | 8/8 (1.000) |
| wrong_accepted | 0/45 (0.000) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 0/12 (0.000) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 12/12 (1.000) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 7/52 (0.135) |
| family macro CLARIFY / REFUSE | 1.0 / 1.0 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 2/2; REFUSE:event_relative 2/2; REFUSE:future 2/2; REFUSE:ownership 2/2; REFUSE:who_did 2/2; REFUSE:why 2/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 2/2; event_relative:dev:0 2/2; first_name:dev:0 2/2; future:dev:0 2/2; giver:dev:0 2/2; giver:dev:1 2/2; giver:dev:2 2/2; giver:template:0 2/2; object_current:dev:0 2/2; object_current:dev:1 0/2; object_current:dev:2 1/2; object_current:template:0 2/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 2/2; person_current:dev:0 2/2; person_current:dev:1 0/2; person_current:dev:2 2/2; person_current:template:0 0/2; person_first:dev:0 2/2; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 2/2; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 2/2; why:dev:0 2/2

Error causes: wrong_intent 7

- 'Find Dorran Lunsey.': gold OK person_current Dorran Lunsey -> REFUSE unsupported None (None)
- 'Find Halsey Ostrin.': gold OK person_current Halsey Ostrin -> REFUSE unsupported None (None)
- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY giver None (no_referent)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY giver None (no_referent)
- 'I need the blue clock - where is it?': gold OK object_current blue clock -> REFUSE unsupported None (None)
- 'Take me to the blue clock.': gold OK object_current blue clock -> REFUSE unsupported None (None)
- 'Take me to the blue map.': gold OK object_current blue map -> REFUSE unsupported None (None)

