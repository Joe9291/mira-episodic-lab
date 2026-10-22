# Round 4.1b - Continued memory instance (design, implementation and dev check, for review)

Context: Astra's limit for round 4.1 (reviews/2026-10-22_r41impl_astra.txt and
2026-10-22_r41result_astra.txt): rounds 4.0 and 4.1 built a NEW memory instance for
every question, so they show correct reconstruction from each report prefix, but not that
one long-running instance, already queried, updates correctly when further reports
arrive; stale caches would stay hidden. She proposed a small follow-up on dev and hand
cases of the five 4.1 families, including a variant with an UNCHANGED query time, so that
a different time key cannot hide a stale cache. Rounds 4.0 and 4.1 and their holdouts
stay closed.

Finding before the test: M (episodic_lab/r40_memory.py) had no way to receive reports
after construction, and it caches resolved versions per (fact, knowledge time). A
long-running M therefore needs an ingest step, and that step must drop cached results.

## 1. Implementation

episodic_lab/r41b_memory.py - LiveMemory = M (unchanged class) plus ingest(): every new
report is appended to the hash-chained ReportStore (written to disk; shape and total
order are checked, a report out of order is refused), added to the per-fact index, and
every cached result of its fact is dropped for ALL knowledge times (a report of day d can
change the answer for any knowledge time >= d that was already asked; dropping all is the
simple safe rule). M's files are unchanged.

## 2. Protocol (bench/m3/run_round41b.py)

Per world of the round 4.1 dev split (5 families x 10 pairs x worlds A / B x 4 delays =
400 worlds), ONE LiveMemory on a file store:
- start with the reports of days <= d3 - 1;
- Q1 current @ d3 - 1; Q2 current @ d3 (c not yet received);
- ingest c; Q3 current @ d3 - the SAME query time as Q2; Q4 current @ d3 + 1;
- ingest the irrelevant reports of the delay; Q5 current @ now, Q6 history @ now,
  Q7 believed_at(d3 - 1) @ now (its cached knowledge time precedes c and must stay
  valid), Q8 why_changed(v = d3, k1 = d3 - 1, k2 = now);
- afterwards a second process reloads every final store (seal checked) and answers
  Q5-Q8 again.
Gold for every question: R on exactly the reports received so far.
Hand cases (tests/test_round41b.py): the 19 hand-computed checks of round 4.1 fed day by
day into one instance; before each new report day the instance is queried at that day,
and every check is answered both at its own time and at that earlier same query time;
plus an explicit same-time case and a disk reload.

## 3. Dev result (local, Python 3.13; docs/ROUND_4_1b_dev_SUMMARY.md)

DEV_OK: Q1-Q8 3,200 / 3,200 answers equal to R (400 per step); in 200 of the 400
Q2 / Q3 pairs (the A worlds) c changes the gold at the same query time, and the instance
followed every time; 400 stores reloaded identically in a second process. Unit tests: 4 / 4,
including the hand cases through one instance.
Mutation check (docs/ROUND_4_1b_mutation.json): without cache invalidation the instance
fails exactly at Q3 (200 / 400 wrong, the A worlds) and nowhere else - questions at a new
query time hide the stale cache, which is why the same-time variant matters; without the
index update it fails at Q3-Q6 and Q8. Both are caught; the hand-case test also catches
the missing invalidation.

## 4. Claim and limits

Claim: on the 400 dev worlds of round 4.1 and the 19 hand cases, ONE continued instance
that was queried before c arrived answered every later question - at the same and at
later query times, current and historical operators - exactly as R on the reports
received so far, and its store reloaded identically. Limits: dev data only, no frozen
holdout (as proposed for this small follow-up); reports arrive in total order (out-of-order
arrival is refused, not handled); single process, no concurrent writers; no latency
measured; the GIVEN source policy within this generator.
Next: phase B - natural-language reports with structured questions, the resolver and
the source policy unchanged, and a parallel control with the correct structured reports
to separate extraction errors from memory errors (Astra's recommendation).
