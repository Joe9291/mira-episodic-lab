# Round 4.1b - Continued memory instance (design, implementation and dev check, v2 for review)

Context: Astra's limit for round 4.1 (reviews/2026-10-22_r41impl_astra.txt and
2026-10-22_r41result_astra.txt): rounds 4.0 and 4.1 built a NEW memory instance for
every question, so they show correct reconstruction from each report prefix, but not that
one long-running instance, already queried, updates correctly when further reports
arrive; stale caches would stay hidden. She proposed a small follow-up on dev and hand
cases of the five 4.1 families, including a variant with an UNCHANGED query time, so that
a different time key cannot hide a stale cache. Rounds 4.0 and 4.1 and their holdouts
stay closed. v2 answers her review of v1 (reviews/2026-10-22_r41b_astra.txt): unique report
ids enforced by ingest, the hand cases run through one instance started empty, a restart
step, and DEV_OK bound to the expected counts.

Finding before the test: M (episodic_lab/r40_memory.py) had no way to receive reports
after construction, and it caches resolved versions per (fact, knowledge time). A
long-running M therefore needs an ingest step, and that step must drop cached results.

## 1. Implementation

episodic_lab/r41b_memory.py - LiveMemory = M (unchanged class) plus ingest(): a batch is
first checked as a whole - report shape, total order after the last stored report and
inside the batch, and report ids that are NEW to the store and unique inside the batch
(the rule of M's constructor; without it, the running instance could accept a repeated id
that a rebuild from the store refuses - Astra's v1 finding) - and only then appended to
the hash-chained ReportStore in one write, added to the per-fact index, and every cached
result of the affected facts is dropped for ALL knowledge times (a report of day d can
change the answer for any knowledge time >= d that was already asked; dropping all is the
simple safe rule). A refused batch changes neither the store, its seal nor any answer.
M's files are unchanged.

## 2. Protocol (bench/m3/run_round41b.py)

Per world of the round 4.1 dev split (5 families x 10 pairs x worlds A / B x 4 delays =
400 worlds), ONE LiveMemory on a file store:
- start with the reports of days <= d3 - 1;
- Q1 current @ d3 - 1; Q2 current @ d3 (c not yet received);
- ingest c; Q3 current @ d3 - the SAME query time as Q2; Q4 current @ d3 + 1;
- ingest the irrelevant reports of the delay; Q5 current @ now, Q6 history @ now,
  Q7 believed_at(d3 - 1) @ now (its cached knowledge time precedes c and must stay
  valid), Q8 why_changed(v = d3, k1 = d3 - 1, k2 = now);
- restart (Astra's v1 idea): the store is reopened (seal checked) as a NEW LiveMemory,
  Q5 is asked again to warm its cache at now, one further own observation of day now
  arrives; Q9 current @ now (same query time), Q10 history @ now;
- afterwards a second process reloads every final store (seal checked) and answers
  Q9-Q10 again.
Gold for every question: R on exactly the reports received so far. DEV_OK requires every
answer equal to R, the reload, and the expected counts (400 instances, 400 answers per
step, 200 Q2 / Q3 pairs in which c changes the gold).
Hand cases (tests/test_round41b.py): each of the 15 hand worlds of round 4.1 runs through
ONE instance started EMPTY; the reports arrive day by day; before each day block the
instance is queried at that day (so every hand world, including T4 / T5, crosses c with an
already queried instance); each of the 19 checks is answered as soon as its prefix has
arrived, at its own time and at its prefix day. Further unit tests: an explicit same-time
case, a repeated id (later day, other fact, and inside one batch) refused without
changing seal or answers and with the store still loadable, a restart followed by
ingest, a disk reload, and order violations refused.

## 3. Dev result (local, Python 3.13; docs/ROUND_4_1b_dev_SUMMARY.md)

DEV_OK: Q1-Q10 4,000 / 4,000 answers equal to R (400 per step); in 200 of the 400
Q2 / Q3 pairs (the A worlds) c changes the gold at the same query time, and the instance
followed every time; after the restart the reopened instance followed the new report at
the same query time in all 400 worlds; 400 final stores reloaded identically in a second
process; expected counts met. Unit tests: 6 / 6.
Mutation check (docs/ROUND_4_1b_mutation.json): without cache invalidation the instance
fails exactly where a query time repeats after new reports - Q3 (200 / 400, the A worlds)
and Q9 / Q10 after the restart (400 / 400) - and nowhere else; without the index update
it fails at Q3-Q6 and Q8-Q10; without the id check the generated sequences pass (they
never repeat an id) and the unit test catches it. All three are caught.

## 4. Claim and limits

Claim: on the 400 dev worlds of round 4.1 and the 15 hand worlds (19 checks), ONE
continued instance that was queried before c arrived answered every later question - at
the same and at later query times, current and historical operators - exactly as R on
the reports received so far (for the hand worlds: as the hand-computed answers); a
reopened instance continued correctly after a restart; the stores reloaded identically;
repeated report ids are refused without side effects. Limits: dev data only, no frozen
holdout (as proposed for this small follow-up); reports arrive in total order (out-of-order
arrival is refused, not handled); single process, no concurrent writers; no latency
measured; the GIVEN source policy within this generator.
Next: phase B - natural-language reports with structured questions, the resolver and
the source policy unchanged, and a parallel control with the correct structured reports
to separate extraction errors from memory errors (Astra's recommendation).
