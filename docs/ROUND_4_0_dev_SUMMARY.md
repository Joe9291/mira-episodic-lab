<!-- Copied from the results branch: round40/run_39573228533_1/SUMMARY.md (commit 5a44447, GitHub Actions, Python 3.12). Identical to the local run (Python 3.13) except the timings. -->
# Round 4.0 phase A - dev (attempt 1)

Verdict: **DEV_OK**

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
| M | 2400/2400 | 0/520 | 0/1360 |
| S0 | 80/2400 | 0/520 | 0/1360 |
| S1 | 736/2400 | 0/520 | 0/1360 |
| S2 | 1588/2400 | 0/520 | 0/1360 |
| S3 | 1832/2400 | 0/520 | 0/1360 |
| S4 | 900/2400 | 0/520 | 0/1360 |

Pairs right (all answers of both worlds at all four delays):

| system | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| M | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| S0 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S1 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S2 | 5/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 |
| S3 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| S4 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |

Required B-indistinguishable cells (min 8 pairs):

- S1|P1: 10
- S1|P2: 10
- S1|P3: 10
- S1|P5: 10
- S1|P9: 10
- S2|P3: 10
- S2|P5: 10
- S2|P7: 10
- S2|P8: 10
- S3|P9: 10
- S4|P1: 10
- S4|P2: 10
- S4|P3: 10
- S4|P5: 10
- S4|P9: 10

| intervention | cases | informative pairs (delay 0) | M = R | unchanged | cascades |
|---|---|---|---|---|---|
| remove_update | 40 | 10/10 | 40 | 0 | 0 |
| remove_late_report | 40 | 10/10 | 40 | 0 | 0 |
| remove_correction | 40 | 10/10 | 40 | 0 | 0 |
| remove_retraction | 40 | 10/10 | 40 | 0 | 0 |
| swap_ranks | 160 | 34/40 | 160 | 24 | 0 |
| remove_conflict_resolver | 40 | 10/10 | 40 | 0 | 0 |
| move_anchor | 40 | 10/10 | 40 | 0 | 0 |
| remove_anchor | 40 | 10/10 | 40 | 0 | 0 |
| remove_obs_before_anchor | 40 | 10/10 | 40 | 0 | 0 |
| irrelevant_control | 360 | 0/90 | 360 | 360 | 50 |

Truth (measurement only): clean report state in 1080 of 1440 value questions; policy answer = world truth in 1028 of them.
Conformance: 56/56. Persistence: 720 stores, ok = True. Audit violations: 0.

Resources:

- R: 2.15 s, peak +0.13 MB
- R_interventions: 2.43 s, peak +0.16 MB
- M: 0.74 s, peak +0.07 MB
- M_interventions: 0.74 s, peak +0.07 MB
- baselines: 0.4 s, peak +0.01 MB
- audit: 1.37 s, peak +0.34 MB
- persist_write: 15.06 s, peak +1.18 MB
- persist_reload: 1.59 s, peak +0.0 MB
