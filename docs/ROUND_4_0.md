# Round 4.0 - Long-term memory with updates, corrections, contradictions, sources and event-anchored history (design v2, draft for review)

Context: the experiment's five-phase plan (2026-10-20) puts the external long-term memory
first, with the milestone "B1 long-term test with real updates, contradictory statements,
independent sources and delayed recall"; Astra named event-anchored historical queries as
the next step when she closed round 3.6. Rounds 3.3-3.5b built the basis (append-only
hash-chained store, unknown-aware operators, history operators proven by interventions,
an LM-written store). v2 answers Astra's review of v1b (reviews/2026-10-20_r40v1b_astra.txt):
historical validity and today's version status are separated by a two-time resolver
(section 2); three separate gold values (section 1); a complete transition table with
report ids and target references (section 2); "after" dropped, "before" defined through
the resolver; case numbers, integer error limits, denominators, an independent reference
and precise baseline failures (sections 4-5); compaction moved to a later round; a
persistence test added.

Uncertainty removed: does an external episodic memory, following a FIXED source policy,
keep apart (a) the best-supported state now, (b) the state at an earlier valid time as
reconstructed today, and (c) what it would have answered at an earlier knowledge time -
under state changes, late news, corrections, retractions, contradictions and many
interleaved irrelevant reports - and can it name the reports that changed an answer and
the state immediately before an anchor event? With predicted interventions, so that a
pass shows causal use of the stored history.
Claim limits (fixed now): the test checks the implementation of a GIVEN source policy
within this generator; it shows neither learned trustworthiness nor general truth
finding; "independent sources" means reports with different origins (section 1), not
different names.

## 1. World, reports and the three gold values

Facts: attributes of entities that change over time (where an object is, who holds it,
where a person is staying), values from the round 3 vocabularies. Every fact has a TRUE
timeline: one value per valid day.
Reports (immutable events; the only way the agent learns anything):
`{report_id, report_day, source, rank, origin, subject, attribute, kind, value, valid_from,
target_report_id}`
- `report_id`: stable, unique, never reused; reports are totally ordered by
  (report_day, report_id);
- `source` with a fixed `rank` from the world rules, given to the agent: own observation 3,
  trusted person 2, hearsay 1;
- `origin`: the underlying observation a report comes from (an own observation has its
  own origin; a person repeating another person's statement carries that statement's
  origin). Two reports are independent iff their origins differ;
- `kind`: `assert` (value holds from valid_from on), `correct` (replaces the value and/or
  valid_from of report target_report_id), `retract` (withdraws report target_report_id);
- `valid_from` may lie before report_day (late news).
Three gold values per question (computed by the generator and the reference, section 4):
- WORLD TRUTH: the true timeline (reported, never the pass criterion of M by itself);
- POLICY ANSWER NOW: what the source policy (section 2) yields from all reports known at
  question time - the pass criterion for current / valid_at / anchored;
- POLICY ANSWER THEN: what the policy yields from the reports known at an earlier
  knowledge time - the pass criterion for believed_at and why_changed.
Truth-determinable worlds: worlds in which every false report is corrected or retracted by
an entitled report before question time, and no conflict stays open; there the policy
answer now must also equal the world truth (reported as a separate measure). Other worlds
are kept on purpose (a standing false top-rank report, an open conflict): there the policy
answer and the truth may differ, and an "unknown" / "conflict" answer can be right - the
test allows lack of information.

## 2. Memory: two-time resolver over the immutable store

Store: the round 3 append-only, hash-chained EpisodeStore holds the reports unchanged.
Everything else is a pure function of the reports with report_day <= known_time.
Core resolver `value_at(s, a, valid_time v, known_time k)`:
1. take the reports about (s, a) with report_day <= k, in total order;
2. apply them to a table of CLAIMS (one claim per assert, keyed by its report_id) with the
   transition rules below;
3. for each valid_from day keep the claims that stand (not retracted) and decide the
   value of that day by rank: the highest-rank claims; one value -> that value; several
   different values at the highest rank -> an OPEN CONFLICT for that valid_from;
4. the timeline: each decided valid_from starts a version that lasts until the next
   decided valid_from; value_at(v, k) is the version whose interval contains v; none ->
   unknown (no observation); an open conflict whose interval contains v -> conflict
   (with the values and report ids).
A version that is later followed by a newer one is NOT removed: it keeps its interval
(state change). A correction or retraction changes the claims themselves, so the
reconstruction of the past changes for every known_time from that report on - and never
for earlier known_times (what was believed then stays as it was).
Transition rules (complete for 4.0):
| report | condition | effect |
|---|---|---|
| assert, valid_from not yet used | - | new claim; a state change if valid_from is after the other days, late news splitting an interval otherwise |
| assert, same valid_from as standing claims, same value | - | supports; no change of the value |
| assert, same valid_from, different value, higher rank than every standing claim there | - | its value decides that day (the lower claims stay stored, not deciding) |
| assert, same valid_from, different value, lower rank | - | stored, not deciding |
| assert, same valid_from, different value, equal to the highest rank | different origin from the deciding claim(s) | OPEN CONFLICT for that day |
| same, but the same origin | - | cannot occur: the generator never emits it (audit check) |
| correct (target t) | source rank >= rank of t's source | t's claim is replaced by the corrected value / valid_from |
| correct | lower rank | stored as an ineffective correction (no change) |
| retract (target t) | the same source as t | t's claim is withdrawn |
| retract | another source | stored as an ineffective retraction (no change) |
An open conflict is resolved only by (i) an assert of higher rank for the same valid_from,
or (ii) an effective correct / retract of one of the conflicting claims. A further assert
of equal rank resolves nothing (majorities are not used in 4.0).
Public operators (all derived from value_at; structured questions):
1. `current(s, a)` = value_at(now, now);
2. `valid_at(s, a, v)` = value_at(v, now) - the past as reconstructed today;
3. `believed_at(s, a, t)` = value_at(t, t) - what would have been answered on day t;
4. `why_changed(s, a, v, k1, k2)`: the SAME valid time v under two knowledge times k1 < k2.
   If value_at(v, k1) = value_at(v, k2): "unchanged". Otherwise the canonical explanation:
   replay the reports with k1 < report_day <= k2 in total order and list every report whose
   application changes value_at(v, .) (the ordered id list);
5. `conflicts(s, a)`: the open conflicts now, with values and report ids;
6. `history(s, a)`: the versions now with their intervals and deciding report ids;
7. `before(s, a, anchor)`: the anchor is an event identified by its content (for example
   "you met Ida Voss at the old mill"); d_Y = the valid day of the anchor event as resolved
   now; answer = value_at(d_Y - 1, now), i.e. the state immediately before the anchor.
   Unknown with a stated reason: anchor not found, anchor ambiguous (several matching
   events), no version before the anchor; conflict if an open conflict covers d_Y - 1.
   ("after" is not part of 4.0.) The generator puts no change of (s, a) on the anchor's day
   (audit check).
Reference case (fully tabulated; ranks own 3, trusted 2, hearsay 1). Truth for the key:
day 1-3 old mill, day 4-6 bridge, from day 7 library. Reports: r1 (day 1, own, assert old
mill from 1); r2 (day 6, Ana trusted, assert harbour from 4 - late and wrong); r3 (day 8,
Ben hearsay, assert forge from 7 - wrong); r4 (day 9, own, assert library from 7); r5
(day 10, Ana, correct r2: bridge from 4).
| known_time k | value_at(v=2, k) | value_at(v=5, k) | value_at(v=8, k) | believed_at(k) |
|---|---|---|---|---|
| 5 | old mill | old mill | old mill | old mill |
| 7 | old mill | harbour | harbour | harbour |
| 8 | old mill | harbour | forge | forge |
| 9 | old mill | harbour | library | library |
| 11 | old mill | bridge | library | library |
| truth | old mill | bridge | library | - |
why_changed(v=5, k1=7, k2=11) = [r5]; why_changed(v=8, k1=8, k2=9) = [r4]; before(anchor on
day 6) = value_at(5, now) = bridge; at k = 7 the policy answer for day 5 (harbour) differs
from the truth (bridge) - right by the policy then, wrong by the world.

## 3. Systems and controls

- M: section 2.
- R: an INDEPENDENT reference resolver for the gold values and the expected intervention
  outcomes - a separate, deliberately simple implementation (day-by-day replay over a full
  table, no indexes, no shared code with M except the report schema); M and R must agree on
  every question (a disagreement is a problem, not an error of M alone).
- S1 state-only: one value per (s, a) - the value of the last assert received wins (rank,
  valid_from, corrections and retractions ignored); every question is answered with that
  value.
- S2 naive episodic: all asserts kept with their valid_from; for an asked valid time the
  assert with the latest report_day among those whose valid_from is not after it wins
  (rank, corrections and retractions ignored; knowledge time respected).
- S3 bounded summary: per (s, a) only three versions with their valid_from - first,
  previous and current (the information of the round 3.4 history agent); before(...) is
  answered from these three (the latest stored version with valid_from < d_Y).
- S0 no memory: always unknown.
Interventions: each is a VALID counterfactual world - the report list is changed and a new,
consistent chain is built (never a corrupted chain): remove the update; remove the late
report; remove the correction; remove the retraction; swap the ranks of two sources;
remove the report that resolves a conflict; move the anchor to another day; remove the
anchor (-> unknown); remove the relevant observation before the anchor; add or remove an
irrelevant report (no change). The expected outcome of each is computed by R on the
counterfactual world before any run.
Control of the baseline-visible input: in a pair, worlds A and B have the same question
(text, structured fields, metadata), the same number of reports and the same report days;
only the content of the one critical report differs.

## 4. Data, phenomena and case numbers

Phenomena (each with its own pairs): P1 state change; P2 late news; P3 correction by an
equal or higher rank; P4 ineffective correction (lower rank); P5 retraction by the own
source; P6 ineffective retraction (another source); P7 open conflict (equal rank,
different origins); P8 conflict resolved by a higher rank; P9 event-anchored before with
an intermediate answer - more than three relevant observations (5-8), current / first /
previous identical in A and B, the answer differs and is held by none of them.
Splits: dev 10 pairs per phenomenon, holdout 40 pairs per phenomenon (9 x 40 = 360 pairs,
720 worlds); the holdout is generated and frozen before any run of M on it (worlds only;
M is symbolic, so the holdout guards against generator-specific overfitting of the logic).
Questions per world: the operators that the phenomenon makes informative (each listed in
the generator's case table with its gold values), asked at delays of 0, 50, 200 and 500
interleaved irrelevant reports (same vocabulary). A pair counts as one unit; the four
delays are not independent replications.
Conformance set: about 30 hand-checkable cases - every row of the transition table, the
reference case of section 2 at every (v, k) shown, every unknown reason of before(...) -
with expected values written down by hand before any run.

## 5. Measures and pass rule (fixed before any run)

Hit definitions: current / valid_at / believed_at / before - the exact value, or the
exact outcome conflict (with the same set of values) or unknown (with the same reason);
why_changed - "unchanged", or exactly the canonical id list; conflicts - exactly the set of
open conflicts with values and ids; history - exactly the versions with intervals and ids.
Measures, per operator x phenomenon x delay and per pair (all four delays right):
- known answers, conflict outputs and unknown outputs separately;
- stale-answer rate: denominator = current questions in worlds where an update,
  correction or retraction made an older value outdated; numerator = the answer equals an
  outdated value;
- false conflicts: denominator = questions whose gold is not a conflict; numerator = a
  conflict output;
- truth agreement in the truth-determinable worlds (reported, section 1).
Pass rule for M (integer limits): the conformance set 100 %; on the holdout at most
floor(0.01 n) errors per operator x phenomenon cell (with these sizes: zero errors), pair
success >= 0.95 per phenomenon and delay bucket, stale-answer rate and false-conflict rate
within the same integer limit, M and R agree on every question, every intervention as
predicted by R in all informative cases with at least 30 informative cases per
intervention type, and the persistence test passes.
Required baseline failures, on INFORMATIVE cases only (the gold differs from that
baseline's answer, determined by R): S1 on P2-P9 valid_at / believed_at / why_changed /
before, S2 on P3-P8 (rank, correction, retraction, conflict), S3 on P9 - each with at most
the integer limit of correct answers on its informative cases; S0 is reported, and its
correct unknowns are counted where the gold is unknown. A pass of M without these
dissociations does not count.
Persistence test: the store is written to disk, the process ends, a new process loads it,
verifies the chain and answers the same questions identically.
Joe's check: about 5 cases per round, chosen by rule (a late report, a correction, a
conflict, an anchored question, a long delay).

## 6. Phases

A. Structured reports (this round): model-free, unbounded unchanged event store.
B. Reports as free-text notes read by an LM extractor - needs its own extraction
   qualification (source, origin, valid_from, kind and target references are new fields
   that the 3.5b PASS does not cover).
C. Questions in language - a new parser attempt; the 3.6 holdout / reserve groups keep
   their recorded status (LM-untested, evaluated technically and with the rule baseline
   before a freeze).
Later rounds: source-bound compaction (separately, so that resolution errors and
compaction losses stay distinguishable); a bounded retrieval budget (then access to the
full archive must be budgeted too); learned source reliability.
Relation to the literature: the target failure modes match the knowledge-update and
temporal-reasoning categories of long-term memory benchmarks such as LongMemEval; a
phase A pass is evidence for the symbolic memory logic inside this generator, not for an
agent on real conversations.
