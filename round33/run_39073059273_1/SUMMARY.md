# Round 3.3 summary (paired action worlds, explicit agent memory)

40 pairs per kind. Every case was decided by its own fresh isolated process that received only that case's store, seal and decision text. The evaluation units are the pairs: the cases are repeated conditions of the same worlds. The causal evidence is the intervention pattern; the memory-branch share only describes the policy.

| kind | intervention | n / planned | success | pair success | as predicted | informative n | as predicted (informative) | share decided via memory branch |
|---|---|---|---|---|---|---|---|---|
| hidden | intact | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |
| hidden | none | 80 / 80 | 0.21 | 0.00 | 1.00 | 63 | 1.00 | 0.00 |
| hidden | random | 80 / 80 | 0.21 | 0.00 | 1.00 | 63 | 1.00 | 0.00 |
| hidden | swapped_binding | 80 / 80 | 0.00 | 0.00 | 1.00 | 80 | 1.00 | 1.00 |
| hidden | relevant_removed | 80 / 80 | 0.21 | 0.00 | 1.00 | 63 | 1.00 | 0.00 |
| hidden | irrelevant_removed | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |
| moved | intact | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |
| moved | none | 80 / 80 | 0.21 | 0.00 | 1.00 | 63 | 1.00 | 0.00 |
| moved | random | 80 / 80 | 0.21 | 0.00 | 1.00 | 63 | 1.00 | 0.00 |
| moved | swapped_binding | 80 / 80 | 0.00 | 0.00 | 1.00 | 80 | 1.00 | 1.00 |
| moved | relevant_removed | 80 / 80 | 0.00 | 0.00 | 1.00 | 80 | 1.00 | 1.00 |
| moved | irrelevant_removed | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |
| giver | intact | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |
| giver | none | 80 / 80 | 0.17 | 0.00 | 1.00 | 66 | 1.00 | 0.00 |
| giver | random | 80 / 80 | 0.17 | 0.00 | 1.00 | 66 | 1.00 | 0.00 |
| giver | swapped_binding | 80 / 80 | 0.19 | 0.00 | 1.00 | 65 | 1.00 | 1.00 |
| giver | relevant_removed | 80 / 80 | 0.16 | 0.00 | 1.00 | 67 | 1.00 | 1.00 |
| giver | irrelevant_removed | 80 / 80 | 1.00 | 1.00 | 1.00 | 0 | - | 1.00 |

Store integrity in the decision process: cut-off store refused True, changed store refused True.

VERDICT COMPLETE - MILESTONE PASS

Development criteria (fixed before the GitHub run, after a local development run):

- PASS every case planned for intact, none, random, relevant_removed is available
- PASS swapped_binding and irrelevant_removed available in >= 90% of planned cases
- PASS informative cases (prediction != truth) >= 60% of planned for swap and relevant removal
- PASS intact: success 1.0 and pair success 1.0
- PASS no memory and random memory: pair success 0 (fixed, deterministic exploration policy)
- PASS swapped binding: action as predicted in >= 0.95 of informative cases
- PASS relevant episode removed: action as predicted in >= 0.95 of informative cases
- PASS irrelevant episode removed: success 1.0
