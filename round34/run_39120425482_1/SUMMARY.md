# Round 3.4 step 1 summary (history goals, identical final state)

40 pairs per kind; every decision in its own fresh isolated process; one episodic store per world, written before any goal was handed to the agent. Evaluation units are the pairs. Stored information: episodic store 14-14 records per world; state-only baseline 3-10 entries (one place per object and person).

| kind | system | intervention | goal | n / planned | success | pair success | as predicted (informative, n) | unchanged vs intact |
|---|---|---|---|---|---|---|---|---|
| object | episodic | intact | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | intact | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | intact | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | irrelevant_removed | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | irrelevant_removed | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | irrelevant_removed | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | last_removed | current | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| object | episodic | last_removed | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | last_removed | previous | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| object | episodic | none | current | 80 / 80 | 0.20 | 0.20 | 1.00 (64) | 0.20 |
| object | episodic | none | first | 80 / 80 | 0.23 | 0.00 | 1.00 (62) | 0.23 |
| object | episodic | none | previous | 80 / 80 | 0.15 | 0.15 | 1.00 (68) | 0.15 |
| object | episodic | old_removed | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | old_removed | first | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| object | episodic | old_removed | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | old_swapped | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | episodic | old_swapped | first | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| object | episodic | old_swapped | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| object | state_only | intact | current | 80 / 80 | 1.00 | 1.00 | - | - |
| object | state_only | intact | first | 80 / 80 | 0.23 | 0.00 | - | - |
| object | state_only | intact | previous | 80 / 80 | 0.15 | 0.15 | - | - |
| person | episodic | intact | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | intact | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | intact | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | irrelevant_removed | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | irrelevant_removed | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | irrelevant_removed | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | last_removed | current | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| person | episodic | last_removed | first | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | last_removed | previous | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| person | episodic | none | current | 80 / 80 | 0.15 | 0.15 | 1.00 (68) | 0.15 |
| person | episodic | none | first | 80 / 80 | 0.16 | 0.00 | 1.00 (67) | 0.16 |
| person | episodic | none | previous | 80 / 80 | 0.23 | 0.23 | 1.00 (62) | 0.23 |
| person | episodic | old_removed | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | old_removed | first | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| person | episodic | old_removed | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | old_swapped | current | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | episodic | old_swapped | first | 80 / 80 | 0.00 | 0.00 | 1.00 (80) | 0.00 |
| person | episodic | old_swapped | previous | 80 / 80 | 1.00 | 1.00 | - | 1.00 |
| person | state_only | intact | current | 80 / 80 | 1.00 | 1.00 | - | - |
| person | state_only | intact | first | 80 / 80 | 0.16 | 0.00 | - | - |
| person | state_only | intact | previous | 80 / 80 | 0.23 | 0.23 | - | - |

Store integrity in the decision process: cut-off store refused True, changed store refused True.

VERDICT COMPLETE - MILESTONE PASS

Criteria (docs/ROUND_3_4.md, fixed before the first run of the code):

- PASS availability: every planned case of intact, none, old_removed, last_removed, irrelevant_removed
- PASS availability: old_swapped in >= 90% of planned cases
- PASS informative cases >= 60% of planned (first goal: old_removed, old_swapped; current goal: last_removed)
- PASS episodic intact: success 1.0 for all goals, pair success 1.0 for the first goal
- PASS state_only: success 1.0 for the current goal, pair success 0.0 for the first goal
- PASS episodic none: pair success 0.0 for the first goal
- PASS old_removed, old_swapped: first goal as predicted >= 0.95 (informative); current and previous unchanged 1.0
- PASS last_removed: current goal as predicted >= 0.95 (informative); first goal unchanged 1.0
- PASS irrelevant_removed: success 1.0 for all goals
