# Round 4.1 stale test - holdout (attempt 1)

Verdict: **PASS**

| criterion | ok |
|---|---|
| M_zero_errors | yes |
| conformance_100 | yes |
| M_equals_R_everywhere | yes |
| S4_positive_control | yes |
| interventions_as_predicted | yes |
| persistence | yes |
| audit_clean | yes |
| required_cells_filled | yes |

Answers right (BEFORE: once per world; AFTER: per world and delay):

| system | BEFORE | AFTER | stale / denominator |
|---|---|---|---|
| M | 400/400 | 1600/1600 | 0/800 |
| S0 | 0/400 | 80/1600 | 0/800 |
| S1 | 320/400 | 536/1600 | 320/800 |
| S2 | 320/400 | 536/1600 | 320/800 |
| S3 | 400/400 | 1600/1600 | 0/800 |
| S4 | 400/400 | 1600/1600 | 0/800 |
| S5 | 320/400 | 640/1600 | 0/800 |

AFTER answers by failure class (priority right > stale > conflict > abstain > other), per family and world:

| system | class | T1|A | T1|B | T2|A | T2|B | T3|A | T3|B | T4|A | T4|B | T5|A | T5|B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M | right | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| M | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | right | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | abstain | 160 | 160 | 80 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| S0 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | right | 0 | 160 | 0 | 160 | 56 | 0 | 0 | 0 | 160 | 0 |
| S1 | stale | 160 | 0 | 160 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | other | 0 | 0 | 0 | 0 | 104 | 160 | 160 | 160 | 0 | 160 |
| S2 | right | 0 | 160 | 0 | 160 | 56 | 0 | 0 | 0 | 160 | 0 |
| S2 | stale | 160 | 0 | 160 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | other | 0 | 0 | 0 | 0 | 104 | 160 | 160 | 160 | 0 | 160 |
| S3 | right | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| S3 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | right | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| S4 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | right | 160 | 0 | 160 | 0 | 160 | 0 | 0 | 0 | 160 | 0 |
| S5 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | abstain | 0 | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | other | 0 | 160 | 0 | 80 | 0 | 160 | 160 | 160 | 0 | 160 |

Over-update flag (world B: BEFORE right, AFTER wrong) - flagged / denominator:

| system | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| M | 0/160 | 0/160 | 0/160 | 0/160 | 0/160 |
| S0 | not evaluable | not evaluable | not evaluable | not evaluable | not evaluable |
| S1 | 0/160 | 0/160 | not evaluable | 160/160 | 160/160 |
| S2 | 0/160 | 0/160 | not evaluable | 160/160 | 160/160 |
| S3 | 0/160 | 0/160 | 0/160 | 0/160 | 0/160 |
| S4 | 0/160 | 0/160 | 0/160 | 0/160 | 0/160 |
| S5 | 160/160 | 160/160 | not evaluable | 160/160 | 160/160 |

Pairs fully right (BEFORE and AFTER, both worlds, all delays):

| system | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| M | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 |
| S0 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S1 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S2 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S3 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 |
| S4 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 |
| S5 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |

Required B-indistinguishable cells (AFTER; min 30 pairs):

- S1|T1: 40
- S1|T2: 40
- S1|T3: 40
- S1|T4: 40
- S1|T5: 40
- S2|T1: 40
- S2|T2: 40
- S2|T3: 40
- S2|T4: 40
- S2|T5: 40
- S5|T1: 40
- S5|T2: 40
- S5|T3: 40
- S5|T4: 40
- S5|T5: 40

| intervention | cases | answer changed | unchanged | M = R | returns to previous answer |
|---|---|---|---|---|---|
| remove_change | 800 | 800 | 0 | 800 | 800 |
| irrelevant_control | 800 | 0 | 800 | 800 | 0 |

Conformance: round 4.0 set 56/56, round 4.1 set 19/19. Persistence: 1600 stores, ok = True. Audit violations: 0.

Resources:

- R: 3.35 s, peak +0.13 MB traced
- R_interventions: 3.24 s, peak +0.13 MB traced
- M: 2.65 s, peak +0.09 MB traced
- M_interventions: 2.55 s, peak +0.07 MB traced
- baselines: 0.44 s, peak +0.01 MB traced
- audit: 5.29 s, peak +0.35 MB traced
- persist_write: 47.42 s, peak +1.17 MB traced
- persist_reload: 6.46 s, peak +0.0 MB traced
- process max RSS: 57.2 MB; reload subprocess max RSS: 57.2 MB
