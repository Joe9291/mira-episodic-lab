# Round 4.0 phase A - holdout (attempt 1)

Verdict: **PASS**

| criterion | ok |
|---|---|
| M_zero_errors | yes |
| conformance_100 | yes |
| M_equals_R_everywhere | yes |
| interventions_as_predicted | yes |
| persistence | yes |
| audit_clean | yes |
| required_cells_filled | yes |

| system | answers right | stale / den. | false conflicts / den. |
|---|---|---|---|
| M | 9600/9600 | 0/2080 | 0/5440 |
| S0 | 320/9600 | 0/2080 | 0/5440 |
| S1 | 2936/9600 | 0/2080 | 0/5440 |
| S2 | 6356/9600 | 0/2080 | 0/5440 |
| S3 | 7324/9600 | 0/2080 | 0/5440 |
| S4 | 3600/9600 | 0/2080 | 0/5440 |

Pairs right (all answers of both worlds at all four delays):

| system | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| M | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 |
| S0 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S1 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S2 | 27/40 | 40/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 40/40 |
| S3 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |
| S4 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 |

Required B-indistinguishable cells (min 30 pairs):

- S1|P1: 40
- S1|P2: 40
- S1|P3: 40
- S1|P5: 40
- S1|P9: 40
- S2|P3: 40
- S2|P5: 40
- S2|P7: 40
- S2|P8: 40
- S3|P9: 40
- S4|P1: 40
- S4|P2: 40
- S4|P3: 40
- S4|P5: 40
- S4|P9: 40

| intervention | cases | informative pairs (delay 0) | M = R | unchanged | cascades |
|---|---|---|---|---|---|
| remove_update | 160 | 40/40 | 160 | 0 | 0 |
| remove_late_report | 160 | 40/40 | 160 | 0 | 0 |
| remove_correction | 160 | 40/40 | 160 | 0 | 0 |
| remove_retraction | 160 | 40/40 | 160 | 0 | 0 |
| swap_ranks | 640 | 135/160 | 640 | 100 | 0 |
| remove_conflict_resolver | 160 | 40/40 | 160 | 0 | 0 |
| move_anchor | 160 | 40/40 | 160 | 0 | 0 |
| remove_anchor | 160 | 40/40 | 160 | 0 | 0 |
| remove_obs_before_anchor | 160 | 40/40 | 160 | 0 | 0 |
| irrelevant_control | 1440 | 0/360 | 1440 | 1440 | 171 |

Truth (measurement only): clean report state in 4320 of 5760 value questions; policy answer = world truth in 4108 of them.
Conformance: 56/56. Persistence: 2880 stores, ok = True. Audit violations: 0.

Resources:

- R: 16.55 s, peak +0.14 MB
- R_interventions: 18.41 s, peak +0.13 MB
- M: 5.64 s, peak +0.1 MB
- M_interventions: 5.49 s, peak +0.07 MB
- baselines: 2.94 s, peak +0.01 MB
- audit: 10.6 s, peak +0.38 MB
- persist_write: 87.46 s, peak +1.17 MB
- persist_reload: 12.5 s, peak +0.0 MB
