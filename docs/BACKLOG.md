# Backlog (accepted ideas, not yet implemented)

Ideas from reviews that are not release conditions. Each is taken up in the milestone
named; until then the limit stated here applies when reading results.

| Source | Idea | Planned | Limit until then |
|---|---|---|---|
| Astra, M2 round 3 (1) | Check every cell against an expected item manifest (phase, qid, criterion, qtype) generated independently from series and index | M3 | Missing or renamed items are caught only through hashes, cross-cell equality and internal consistency |
| Astra, M2 round 3 (2) | Collector assigns A1 prompt inclusions to the episode's block (early: all questions, follow-up: final questions) instead of checking the set of values | M3 | A swap of counts between episodes would pass the collector (the runner test checks the assignment) |
| Astra, M2 round 3 (3) | `resources.peak_rss_mb` is the cumulative peak of the cell process since start (`ru_maxrss`), so the "low" value can contain the "high" peak; measure per condition separately if conditions are compared | M3 | Read it as the cell's memory ceiling only; measure larger models separately on the 4-core runner |
| Astra, M2 round 2 | Equal note counts for positive and lure items in O1, for a clean binding diagnosis | if O1-E5 is ever used | O1-E5 is no binding diagnosis (protocol section 4) |
| Astra, M2 round 1 | P1/P2/C1 frozen-weights check against the state after each encoding block | M4 | not applicable before M4 |
| Astra, pilot v1 round 2 (2) | v0-v1 comparison restricted to the common original items, separating the instruction change from the added E3a orientations | v1 analysis | - |
| Astra, pilot v1 round 2 (3) | Operationalise "pair score clearly above 0.5" (margin and decision rule) | protocol 1.0 | qualitative wording in exploratory reports only |

- (Astra, review of 3.2 v4) Broaden the completion (soundness) tests: some larger stores
  with still few unknown fields, to exercise the selection budget, ties and multi-stage
  links without a large combinatorial cost.
- (Astra, review of 3.4 step 1) A cache baseline (first, previous and latest place per
  entity) and context-dependent historical queries it cannot anticipate.
- (Astra, review of 3.4 step 1) Before round 3.4 step 2: history operators with unknown
  fields (possible() and declared unknowns for first/previous positions).
