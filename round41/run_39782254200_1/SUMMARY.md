# Round 4.1 stale test - dev (attempt 1)

Verdict: **DEV_OK**

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
| M | 100/100 | 400/400 | 0/200 |
| S0 | 0/100 | 20/400 | 0/200 |
| S1 | 80/100 | 136/400 | 80/200 |
| S2 | 80/100 | 136/400 | 80/200 |
| S3 | 100/100 | 400/400 | 0/200 |
| S4 | 100/100 | 400/400 | 0/200 |
| S5 | 80/100 | 160/400 | 0/200 |

AFTER answers by failure class (priority right > stale > conflict > abstain > other), per family and world:

| system | class | T1|A | T1|B | T2|A | T2|B | T3|A | T3|B | T4|A | T4|B | T5|A | T5|B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M | right | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| M | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| M | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | right | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S0 | abstain | 40 | 40 | 20 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| S0 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | right | 0 | 40 | 0 | 40 | 16 | 0 | 0 | 0 | 40 | 0 |
| S1 | stale | 40 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S1 | other | 0 | 0 | 0 | 0 | 24 | 40 | 40 | 40 | 0 | 40 |
| S2 | right | 0 | 40 | 0 | 40 | 16 | 0 | 0 | 0 | 40 | 0 |
| S2 | stale | 40 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | other | 0 | 0 | 0 | 0 | 24 | 40 | 40 | 40 | 0 | 40 |
| S3 | right | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| S3 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S3 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | right | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| S4 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | abstain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S4 | other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | right | 40 | 0 | 40 | 0 | 40 | 0 | 0 | 0 | 40 | 0 |
| S5 | stale | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | conflict | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | abstain | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 |
| S5 | other | 0 | 40 | 0 | 20 | 0 | 40 | 40 | 40 | 0 | 40 |

Over-update flag (world B: BEFORE right, AFTER wrong) - flagged / denominator:

| system | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| M | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S0 | not evaluable | not evaluable | not evaluable | not evaluable | not evaluable |
| S1 | 0/40 | 0/40 | not evaluable | 40/40 | 40/40 |
| S2 | 0/40 | 0/40 | not evaluable | 40/40 | 40/40 |
| S3 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S4 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S5 | 40/40 | 40/40 | not evaluable | 40/40 | 40/40 |

Pairs fully right (BEFORE and AFTER, both worlds, all delays):

| system | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| M | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| S0 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S1 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S2 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S3 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| S4 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| S5 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |

Required B-indistinguishable cells (AFTER; min 8 pairs):

- S1|T1: 10
- S1|T2: 10
- S1|T3: 10
- S1|T4: 10
- S1|T5: 10
- S2|T1: 10
- S2|T2: 10
- S2|T3: 10
- S2|T4: 10
- S2|T5: 10
- S5|T1: 10
- S5|T2: 10
- S5|T3: 10
- S5|T4: 10
- S5|T5: 10

| intervention | cases | answer changed | unchanged | M = R | returns to previous answer |
|---|---|---|---|---|---|
| remove_change | 200 | 200 | 0 | 200 | 200 |
| irrelevant_control | 200 | 0 | 200 | 200 | 0 |

Conformance: round 4.0 set 56/56, round 4.1 set 19/19. Persistence: 400 stores, ok = True. Audit violations: 0.

Resources:

- R: 0.87 s, peak +0.12 MB traced
- R_interventions: 0.82 s, peak +0.12 MB traced
- M: 0.76 s, peak +0.09 MB traced
- M_interventions: 0.68 s, peak +0.07 MB traced
- baselines: 0.12 s, peak +0.01 MB traced
- audit: 1.46 s, peak +0.36 MB traced
- persist_write: 13.14 s, peak +1.17 MB traced
- persist_reload: 1.79 s, peak +0.0 MB traced
- process max RSS: 34.7 MB; reload subprocess max RSS: 34.7 MB
