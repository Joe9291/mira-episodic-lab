# Round 4.0 - Long-term memory with updates, contradictions and sources (design v1b, draft for review)

Context: the experiment's five-phase plan (2026-10-20) puts phase 2 first - "an external
memory that keeps current and historical information reliably apart" - with the milestone
"B1 long-term test with real updates, contradictory statements, independent sources and
delayed recall". Rounds 3.3-3.5b built the basis: an append-only, hash-chained episodic
store, unknown-aware operators, history operators (current / first / previous) proven by
interventions, and an LM-written store (3.5b). What is missing are versioned statements,
updates that supersede, contradictions between sources of different reliability,
retractions, time-indexed recall and long delays.

Uncertainty removed: does an external episodic memory keep (a) what is true now, (b) what
was true at an earlier day and (c) what the agent believed at an earlier day apart under
updates, contradictions, retractions and long delays - and can it reconstruct WHY its
answer changed (which report, from which source, on which day)? Tested against systems that
cannot, with predicted interventions, so that a pass shows causal use of the stored
history, not plain retrieval.
v1b adds the event-anchored historical queries that Astra named as the next step when she
closed round 3.6 (reviews/2026-10-20_r36dev_astra.txt, Q3): "where was X immediately before
event Y?", with her three requirements (section 2, operator 7; section 3).

## 1. World and reports (generator with known truth)

Facts: attributes of entities that change over time - where an object is, who holds it,
where a person lives / works (values from the round 3 vocabularies). Every fact has a true
timeline (value per day).
Reports: the agent learns about facts only through reports, each an immutable event:
`{report_day, source, subject, attribute, value, valid_from, kind}` with
- `kind`: assert (a value from valid_from on), retract (an earlier report of this source
  was wrong), correct (an earlier value was wrong, here is the right one);
- `source`: the agent's own observation, a named person, a document; every source has a
  reliability level fixed in the world's rules and given to the agent (own observation >
  trusted person > hearsay); reliability may differ from truth on purpose (a trusted person
  can be wrong once - then a later correction by a source of at least the same level
  fixes it);
- `valid_from` can lie before `report_day` (late news: on day 9 the agent hears that the key
  was moved on day 5) - so "true on day t" (valid time) and "believed on day t" (knowledge
  time) differ.
Delays: questions are asked after 0, 50, 200 or 500 later unrelated reports (distractors
with the same vocabulary), so recall is tested over long gaps.
Pairs: as in rounds 3.3-3.6, worlds A and B differ in exactly one report (an update, a
retraction, a contradicting report, a source level, or the position of an anchor event), so
a correct answer must depend on that report.
Anchored-query worlds (Astra's three requirements): (1) no shortcut - pairs whose current,
first and previous answers are identical in A and B but whose anchored answer differs;
(2) real history needed - the target has more than three relevant observations (5-8), and
in both worlds of a pair the anchored answer is an intermediate one that none of current /
first / previous holds; (3) causal binding - predicted interventions on the anchor (swap
the anchor to another day, remove it -> unknown), on the relevant observation (remove it ->
the next earlier version or unknown) and on irrelevant events (no change), each with the
answer or the unknown it must produce fixed before any run.

## 2. Memory: versioned statements over the immutable store

The episodic store stays append-only and chained (unchanged). On top of it a derived,
reproducible statement view: for each (subject, attribute) the versions with valid_from,
report day, source, level and the report it came from; a version is superseded by a later
valid_from or corrected / retracted by a report of at least the same level; two reports of
the same level that disagree about the same valid time form an open contradiction until a
higher-level or later same-level report resolves it. The view is a pure function of the
reports (rebuildable at any time from the store).
Operators (structured questions, the language interface returns later - round 3.6):
1. `current(s, a)` - the best-supported value now, or `conflict(values, sources)`, or
   unknown;
2. `valid_at(s, a, t)` - the value true on day t by everything known now;
3. `believed_at(s, a, t)` - what the agent would have answered on day t (only reports
   with report_day <= t);
4. `why_changed(s, a, t1, t2)` - the report(s) that change the answer between knowledge
   days t1 and t2 (source, day, kind), or "unchanged";
5. `conflicts(s, a)` - open contradictions with their sources;
6. `history(s, a)` - all versions with provenance;
7. `anchored(s, a, relation, anchor)` - the value of (s, a) immediately before / after an
   anchor event (an event identified by its own content, e.g. "Ida Voss gave you the old
   key"). The structured question holds target (s, a), relation (before / after) and anchor.
   Meaning of "immediately before", fixed here: the anchor's valid day d_Y is the valid day of
   the anchor event as known now; the answer is the version of (s, a) with the latest valid
   day strictly before d_Y (for "after": the earliest strictly after d_Y), taking only the
   versions that stand now (superseded, corrected and retracted reports excluded); a version
   on the same day as the anchor counts as neither (one event per entity and day in the
   generator - the audit checks it); no version before the anchor -> unknown ("no
   observation before Y"); an anchor that matches no stored event or several -> unknown
   (anchor not found / ambiguous anchor), never a guess.
Source-bound compaction (the plan's "quellengebundene Verdichtung"): old reports may be
condensed into statement versions that keep the ids of their source reports; the store
itself is never rewritten (compaction is a second, derived layer). Test: every answer
before and after compaction is identical, and every provenance id an answer cites
resolves to a stored report.

## 3. Systems and controls

- M: the memory of section 2.
- S1 state-only: one current value per (subject, attribute), last report wins (the cache
  baseline of round 3.4) - can answer `current` only and ignores levels, retractions,
  contradictions.
- S2 naive episodic: keeps all reports but answers by "latest report wins" - can answer
  history-like questions but ignores source levels, corrections and valid_from before
  report_day.
- S3 the round 3.4 history agent (current / first / previous only): must fail the
  anchored queries by construction of requirement (1) and (2).
- S0 no memory.
- Interventions on M's store with predicted answers: remove the update (answer reverts),
  remove the retraction, swap two sources' levels, move a late report earlier, remove the
  report that resolves a contradiction (conflict reappears), remove an irrelevant report
  (nothing changes).

## 4. Measures and criteria (draft)

Per question type and delay bucket, over world pairs (worlds A/B), with Wilson intervals:
- stale-answer rate: `current` answered with a superseded value (the failure mode named
  in the long-term memory literature, e.g. the "knowledge updates" category of
  LongMemEval);
- accuracy of `valid_at`, `believed_at`, `why_changed` (exact report ids), `conflicts`
  (precision and recall), unknown handling;
- compaction invariance and provenance resolution.
Proposed pass rule (M): every type >= 0.99 and pair success >= 0.95 in every delay bucket,
stale-answer rate <= 0.01, conflict recall >= 0.95 with <= 0.02 false conflicts, every
intervention as predicted in >= 0.95 of the informative cases, compaction invariance 1.0,
every cited id resolvable. Dissociations that must appear: S1 fails valid_at, believed_at,
why_changed and conflicts; S2 fails the source-level, correction and late-report cases; S0
fails everything; S3 fails every anchored query whose answer is an intermediate version.
A pass of M without these dissociations would mean the worlds are too easy and does not
count. The anchored-query interventions are part of the intervention criterion.
Joe's check: about 5 cases per round, chosen by rule (an update, a late report, a
contradiction, a correction by a higher source, a long delay).

## 5. Phases

A. Structured reports (truth events) - tests the memory logic; model-free, cheap, fully
   blind holdout of worlds (dev / holdout split, frozen before the holdout).
B. Reports written as free-text notes and read by the frozen 3.5b-style extraction
   (later, labelled "known note wordings" where it applies).
C. Questions in language - after a new attempt at the parser (3.6 holdout and reserve
   remain unused for that).

## Open questions for the review

Q1 Is the scope right for the first long-term milestone (bitemporal facts, sources with
   levels, corrections and retractions, delays, compaction), or should compaction move to
   a later round?
Q2 Source levels given to the agent (fixed world rule) vs. learned reliability from
   history - I propose given levels now, learned reliability later.
Q3 Criteria thresholds as proposed?
Q4 Delay buckets 0 / 50 / 200 / 500 reports - meaningful for a symbolic store (it should not
   degrade; the test becomes important with bounded or LM-based retrieval), or should
   phase A include a bounded store (fixed size with compaction) so that delay matters?
