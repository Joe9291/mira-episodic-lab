# Round 3.6 probe (development texts, best value)

qwen3-1.7b+q7: mean 10.80 s per question (max 62.00)

#### qwen3-1.7b+q7: 67/69 right

| measure | value |
|---|---|
| exact:object_current:goal | 4/4 (1.000) |
| exact:object_current:absent | 4/4 (1.000) |
| exact:object_current | 8/8 (1.000) |
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
| exact:person_previous:goal | 7/7 (1.000) |
| exact:person_previous:absent | 0/0 |
| exact:person_previous | 7/7 (1.000) |
| exact:giver:goal | 3/3 (1.000) |
| exact:giver:absent | 5/5 (1.000) |
| exact:giver | 8/8 (1.000) |
| wrong_accepted | 0/50 (0.000) |
| false_ok:CLARIFY | 0/5 (0.000) |
| false_ok:REFUSE | 0/12 (0.000) |
| handled:CLARIFY | 5/5 (1.000) |
| handled:REFUSE | 12/12 (1.000) |
| recognised_ambiguity | 5/5 (1.000) |
| unnecessary | 2/52 (0.038) |
| family macro CLARIFY / REFUSE | 1.0 / 1.0 |

Families (right / texts): CLARIFY:bare_noun 2/2; CLARIFY:first_name 2/2; CLARIFY:pronoun 1/1; REFUSE:count 2/2; REFUSE:event_relative 2/2; REFUSE:future 2/2; REFUSE:ownership 2/2; REFUSE:who_did 2/2; REFUSE:why 2/2

Wordings (right / texts): bare_noun:dev:0 2/2; count:dev:0 2/2; event_relative:dev:0 2/2; first_name:dev:0 2/2; future:dev:0 2/2; giver:dev:0 2/2; giver:dev:1 2/2; giver:dev:2 2/2; giver:template:0 2/2; object_current:dev:0 2/2; object_current:dev:1 2/2; object_current:dev:2 2/2; object_current:template:0 2/2; object_first:dev:0 2/2; object_first:dev:1 2/2; object_first:dev:2 1/1; object_first:template:0 2/2; object_previous:dev:0 2/2; object_previous:dev:1 1/1; object_previous:dev:2 2/2; object_previous:template:0 2/2; ownership:dev:0 2/2; person_current:dev:0 2/2; person_current:dev:1 0/2; person_current:dev:2 2/2; person_current:template:0 2/2; person_first:dev:0 2/2; person_first:dev:1 2/2; person_first:dev:2 1/1; person_first:template:0 2/2; person_previous:dev:0 2/2; person_previous:dev:1 1/1; person_previous:dev:2 2/2; person_previous:template:0 2/2; pronoun:dev:0 1/1; who_did:dev:0 2/2; why:dev:0 2/2

Error causes: wrong_intent 2

- 'Go to Ilsen Vesk.': gold OK person_current Ilsen Vesk -> CLARIFY giver None (no_referent)
- 'Go to Odile Lunsey.': gold OK person_current Odile Lunsey -> CLARIFY giver None (no_referent)

