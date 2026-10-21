# Round 4.0 - Long-term memory with updates, corrections, contradictions, sources and event-anchored history (design v4, approved 2026-10-21; implementation notes in section 7)

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
persistence test added. v3 answers her review of v2 (reviews/2026-10-20_r40v2_astra.txt):
the full semantics of corrections and retractions incl. chains, withdrawn and missing
targets (section 2); "truth-determinable" replaced by a measured "clean report state"
(section 1); baseline failures defined by pre-fixed pair properties instead of by the
baselines' answers (section 3); one fixed case table with zero allowed errors (section 5).
v4 answers her review of v3 (reviews/2026-10-21_r40v3_astra.txt): the day's value is
re-decided by rank after every effective report, so a new correction claim can resolve a
conflict (section 2); S2 on P4 / P6 removed from the required cells, both families are
negative controls (section 4); targets without a claim defined; removal cascades, baseline
states and R's memory use specified (section 3).

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
- `kind`: `assert` (value holds from valid_from on), `correct` (withdraws the claim of
  report target_report_id and states a new value and/or valid_from on the corrector's own
  authority, section 2), `retract` (withdraws the claim of report target_report_id);
- `valid_from` may lie before report_day (late news).
Three gold values per question (computed by the generator and the reference, section 4):
- WORLD TRUTH: the true timeline (reported, never the pass criterion of M by itself);
- POLICY ANSWER NOW: what the source policy (section 2) yields from all reports known at
  question time - the pass criterion for current / valid_at / anchored;
- POLICY ANSWER THEN: what the policy yields from the reports known at an earlier
  knowledge time - the pass criterion for believed_at and why_changed.
Clean report state (v3; replaces "truth-determinable", which did not guarantee truth - a
change that is never reported keeps an old value without any false report): a question
whose relevant reports contain no standing false claim and no open conflict. For these
questions the agreement of the policy answer with the world truth is REPORTED AS A
MEASUREMENT ONLY; it is no pass criterion and no claim. The test allows lack of
information everywhere: an unreported change or a retracted wrong update can leave an old
value standing, and "unknown" / "conflict" can be the right policy answer.

## 2. Memory: two-time resolver over the immutable store

Store: the round 3 append-only, hash-chained EpisodeStore holds the reports unchanged.
Everything else is a pure function of the reports with report_day <= known_time.
Core resolver `value_at(s, a, valid_time v, known_time k)`:
1. take the reports about (s, a) with report_day <= k, in total order;
2. apply them to a table of CLAIMS (one claim per assert and per effective correct, keyed
   by its report_id) with the transition rules below;
3. for each valid_from day keep the claims that stand (not withdrawn) and decide the
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
| same, but the same origin | - | cannot occur: the generator never emits it, also not via a correction claim (audit check) |
| correct (target t) | t's claim stands and the corrector's rank >= the rank of t's claim | t's claim is withdrawn; a NEW claim is created with the correction's value and valid_from (t's valid_from if none is given) and with the CORRECTOR's source, rank and origin; its report id is the correction's id |
| correct | lower rank than t's claim | stored as an ineffective correction (no change) |
| retract (target t) | t's claim stands and the retracting source is the source of t's claim | t's claim is withdrawn |
| retract | another source | stored as an ineffective retraction (no change) |
| correct or retract | t's claim is already withdrawn (retracted or corrected before) | ineffective (no change), stored |
| correct or retract | t exists but never created a claim (t is a correct report that was itself ineffective) | ineffective (no change), stored - the generator does not emit it in original worlds; it can arise legitimately in a counterfactual world (for example after swapping ranks) and is then resolved by this row |
| correct or retract | t does not exist in the store | ineffective, stored with the flag "dangling reference" - the generator never emits it, and no intervention may create it (audit) |
| correct or retract | t is a retract report | cannot occur: the generator never emits it (audit) |
Conflicts are not a separate state machine: after EVERY effective report the value of
each affected valid_from day is decided again from the claims standing then (step 3). A
conflict therefore ends exactly when the highest-rank standing claims of that day agree
in value - through a higher-rank assert, a higher-rank claim created by a correction
(also when the corrected claim was not part of the conflict: r1 rank 1 asserts A; r2 and
r3, rank 2, independent, assert B and C -> conflict; r4 rank 3 corrects r1 to D -> D
decides, deciding id r4), a correction that changes or moves a conflicting claim, or a
retraction of a conflicting claim. A mere further claim of equal rank does not resolve an
existing conflict (majorities are not used in 4.0); a correction of equal rank can
withdraw a conflicting claim and replace it with an equal-rank claim that now agrees,
which ends the conflict (conformance world W5).
Consequences of the correction rule (fixed policy: a correction is a withdrawal plus a new
claim on the corrector's authority): (a) example r1 rank 1 asserts A; r2 rank 3 corrects r1
to B; r3 rank 2 asserts C for the same valid_from -> B decides (r2's claim has rank 3), the
deciding id is r2; (b) the original source of r1 cannot withdraw B afterwards: r1's claim
is already withdrawn (ineffective), and B belongs to r2's source - only r2's source can
retract it, and only a source of rank >= 3 can correct it; (c) several corrections of
the same target: the first effective one withdraws it, later ones that point to the
same target are ineffective; a further change must target the latest standing claim (the
previous correction) - the generator emits chains this way; (d) a correction or
retraction may target an assert or a correct report (a correction's claim can be
corrected or retracted), never a retract report.
Public operators (all derived from value_at; structured questions):
1. `current(s, a)` = value_at(now, now);
2. `valid_at(s, a, v)` = value_at(v, now) - the past as reconstructed today;
3. `believed_at(s, a, t)` = value_at(t, t) - what would have been answered on day t;
4. `why_changed(s, a, v, k1, k2)`: the SAME valid time v under two knowledge times k1 < k2.
   An answer is the triple (status, value or set of conflicting values); report ids do
   not count as a change. If the answers at k1 and k2 are equal: "unchanged" (also after
   A -> B -> A, and when only the evidence of an unchanged conflict changes - fixed by
   contract). Otherwise the canonical explanation: replay the reports with
   k1 < report_day <= k2 in total order and list every report whose application changes
   the answer for v (the ordered id list);
5. `conflicts(s, a)`: the open conflicts now, with values and report ids;
6. `history(s, a)`: the versions now with their intervals and deciding report ids;
7. `before(s, a, anchor)`: the anchor is an event identified by its content (for example
   "you met Ida Voss at the old mill"); d_Y = the valid day of the anchor event as resolved
   now; answer = value_at(d_Y - 1, now), i.e. the state immediately before the anchor.
   Unknown with a stated reason: anchor not found, anchor ambiguous (several matching
   events), no version before the anchor; conflict if an open conflict covers d_Y - 1.
   ("after" is not part of 4.0.) The generator puts no change of (s, a) on the anchor's day
   (audit check). The anchor is itself a report and follows the same rules: a corrected
   anchor date moves today's before(...) answer; a retracted anchor -> anchor not found; two
   standing anchor reports with different dates at the same rank -> anchor ambiguous
   (conformance cases).
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
  table, no indexes, no shared resolver logic or state preparation with M, only the report
  schema); it processes each report prefix once and answers all questions of that prefix
  (Astra's saving idea); it processes the worlds one after another and keeps only the
  answers at the prefixes that are needed, no state copy per irrelevant report; M and R
  must agree on every question (a disagreement is a problem, not an error of M alone).
- S0 no memory: always unknown (why_changed: unknown; conflicts: none; history: empty).
- S1 state-only: one value per (s, a) - the value of the last assert received wins (rank,
  valid_from, corrections and retractions ignored); every value question is answered with
  that value; why_changed: always "unchanged"; conflicts: none; history: one version.
- S2 naive episodic: all asserts kept with their valid_from; for an asked valid time the
  assert with the latest report_day among those whose valid_from is not after it wins
  (rank, corrections and retractions ignored; knowledge time respected); why_changed: its
  own answers at k1 and k2, "unchanged" if equal, else the asserts in (k1, k2] that change
  its own answer; conflicts: none; history: its own versions.
- S3 bounded summary: per (s, a) only three versions with their valid_from - first,
  previous and current (the information of the round 3.4 history agent); before(...) is
  answered from these three (the latest stored version with valid_from < d_Y); it keeps no
  knowledge times, so believed_at is answered like valid_at and why_changed with
  "unchanged"; conflicts: none; history: the three versions.
- S4 oracle current state (Astra's idea, a stronger state baseline): it receives the
  CORRECT current policy answer at question time (from R) but no history; current is
  always right, every historical question is answered with the current answer;
  why_changed: "unchanged"; conflicts: the conflict of the current answer, if any;
  history: one version.
Every baseline thus gives an allowed output for every operator, so a baseline error is
never a mere format error.
Interventions: each is a VALID counterfactual world - the report list is changed and a new,
consistent chain is built (never a corrupted chain): remove the update; remove the late
report; remove the correction; remove the retraction; swap the ranks of two sources;
remove the report that resolves a conflict; move the anchor to another day; remove the
anchor (-> unknown); remove the relevant observation before the anchor; add or remove an
irrelevant report (no change). The expected outcome of each is computed by R on the
counterfactual world before any run. Every intervention record lists the complete set of
removed report ids (the removal cascade below), so a result that rests on removing a
whole dependency is visible as such.
Control of the baseline-visible input: in a pair, worlds A and B have the same question
(text, structured fields, metadata), the same number of reports and the same report days;
only the content of the one critical report differs.
Baseline failures without circularity (v3): for every baseline B and phenomenon P, the
generator marks a pair as B-INDISTINGUISHABLE when everything B can see is identical in
worlds A and B - its complete stored state (for S3 the three stored versions WITH their
valid_from, for S1 the single value, for S2 the asserts with report_day, valid_from and
value, for S4 the current answer) and the question - while
the gold answer of at least one question of the phenomenon (same operator, same arguments,
same delay) differs between A and B. This is a property of the inputs, fixed before any
run and checked by the audit; on such a pair B can be right in at most one world. For
every marked pair the compared baseline states and the question are logged (including
report ids where the baseline uses them for its outputs). The
design (section 4) fixes in advance which (B, P) cells must contain at least 30
B-indistinguishable pairs (and which are not applicable by design); the evidence is that
M solves these pairs. Baseline results are reported on ALL cases (answers right and pair
success separately), not only on the marked pairs.
Interventions as valid counterfactual worlds: removing a report also removes every report
that refers to it (transitively), so no dangling reference arises; every counterfactual
world must pass the general generator audit (unique ids and total order, no equal-rank
same-origin conflict, no change of (s, a) on the anchor day, no dangling reference, no
reference to a retract report); the phenomenon's own conditions are not required there,
since an intervention may remove the phenomenon on purpose. A new hash chain alone is no
proof of a valid counterfactual.

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
Questions per world (fixed case table, v3):
| phenomenon | questions per world |
|---|---|
| P1 state change | current, valid_at (before the change), believed_at (before the change), history |
| P2 late news | current, valid_at (inside the late interval), believed_at (before the report day), why_changed (that valid day; before vs after the report day) |
| P3 correction | valid_at (corrected day), believed_at (before the correction), why_changed, history |
| P4 ineffective correction | valid_at, why_changed (gold "unchanged"), history |
| P5 retraction | current, valid_at, believed_at (before the retraction), why_changed |
| P6 ineffective retraction | current, valid_at, why_changed (gold "unchanged") |
| P7 open conflict | current or valid_at (gold conflict), conflicts, history |
| P8 conflict resolved by a higher rank | current, conflicts (gold none), why_changed |
| P9 anchored before (intermediate answer) | before, current |
That is 30 question kinds summed over P1-P9 (4+4+4+3+4+3+3+3+2); each
pair asks its phenomenon's questions in both worlds at each of the four delays (0, 50, 200,
500 interleaved irrelevant reports of the same vocabulary). Holdout: 40 pairs per
phenomenon -> 30 x 2 x 4 x 40 = 9,600 answers. A pair is one unit; the four delays are not
independent replications.
Minimum B-indistinguishable pairs (>= 30 of the 40 holdout pairs): S1 on P1-P3, P5, P9;
S2 on P3, P5, P7, P8; S3 on P9; S4 on P1-P3, P5, P9; other (B, P) cells are reported, not
required. P4 and P6 are NEGATIVE CONTROLS: an ineffective correction or retraction must
change nothing, which a baseline that ignores corrections and retractions also gets
right; M must match the gold there exactly (the ineffective report changes no answer;
why_changed "unchanged"), and no superiority over a baseline is required there.
Conformance set: about 50 hand-checkable cases, each with the expected answer AND the
expected provenance (deciding report ids, source, rank) written down by hand before any
run - every row of the transition table; the reference case of section 2 at every (v, k)
shown; the correction consequences (a)-(d) of section 2 (rank of a corrected claim,
retraction by the original source ineffective, retraction by the corrector, a second
correction of the same target, a correction chain, correcting or retracting a withdrawn
claim, correcting a correction); why_changed edge cases (A -> B -> A, a supporting report
with an unchanged value, a change of conflict evidence only); before(...) with every
unknown reason, a corrected anchor date, a retracted anchor and conflicting anchor dates;
interventions with cascading removal (removing a report that a correction targets); a
conflict resolved by a higher-rank correction of a claim outside the conflict (section 2);
a correction targeting an ineffective correction report.

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
- agreement with the world truth on the clean report state (measurement only, section 1).
Pass rule for M (v3, one count for everything): ZERO errors on all 9,600 holdout answers
(every operator x phenomenon x delay cell; the table above fixes every denominator), the
conformance set 100 %, M and R agree on every question, every intervention outcome as
predicted by R (an intervention case is informative when R's answer on the counterfactual
world differs from its answer on the original - a property of the worlds, computed before
any run; at least 30 informative cases per intervention type, except the irrelevant-report
control, which must leave every answer unchanged), the persistence test passes,
and the generator audit marks at least 30 B-indistinguishable pairs in each required cell
(section 4). With zero allowed errors a separate pair-success limit would be redundant;
pair success is reported as a measure. Stale answers and false conflicts are reported with
their denominators (above); under the zero-error rule both are zero for a pass.
This is the pass rule of a finite test suite: 40 independent pairs per phenomenon with zero
errors do not establish a general error rate below 1 %.
Baselines: results on all cases and on their B-indistinguishable pairs are reported; a pass
of M where a required cell has fewer than 30 such pairs does not count (the worlds would
be too easy for that baseline).
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

## 7. Implementation notes (phase A, after the APPROVE of v4)

Astra approved v4 on 2026-10-21 (reviews/2026-10-21_r40v4_astra.txt). Her four ideas and
every choice the design left open are fixed here; they are part of the implementation
review before the holdout freeze.
- Code: episodic_lab/r40_schema.py (the only module M and R share), r40_memory.py (M:
  hash-chained ReportStore and the resolver), r40_reference.py (R), r40_baselines.py,
  r40_world.py (generator, interventions, audit), r40_analysis.py; bench/m3/run_round40.py,
  bench/m3/freeze40.py; tests/test_round40.py; tests/fixtures/r40_conformance.json (56
  hand-computed checks in 10 worlds, written before M or R ran; world W10 pins
  before = value_at(d_Y - 1, now) with a change ON the anchor day, a case the generator
  never produces).
- Anchors: an anchor event is the fact (subject "event:<content>", attribute "day") with
  the day as value and valid_from 0, resolved by the same resolver at valid time 0: no
  standing claim -> anchor_not_found; standing claims with different days at the top rank
  (several matching events or conflicting dates) -> anchor_ambiguous; a correction of the
  day moves before(...). Unknown reasons: no_version (value questions), anchor_not_found,
  anchor_ambiguous, no_version_before.
- History: one version per decided valid_from (adjacent versions with equal values are
  not merged); the deciding ids of a version are all top-rank standing claims of that day.
- Delays: the irrelevant reports lie between the last relevant report and the question,
  5 per day; the question day is the day after. They use the same vocabulary (other
  objects, and the same object with the other attribute) and all kinds: asserts (some
  late), corrections and retractions of irrelevant asserts, repeats with the same origin,
  other anchor events.
- P7 (Astra's idea 2): even pairs have the conflict on the newest version and ask
  current; odd pairs add a later state change and ask valid_at inside the conflict.
- S2 ties (idea 2): the latest report in the total order (report_day, report_id) wins.
- Baselines in detail: S1 keeps only the value (its history has one version without
  valid_from or ids); S3 keeps the first, previous and current version of R's policy
  history at question time with valid_from and ids, and the current version of the
  anchor; S4 keeps R's current version (status, value(s), ids and since when). The
  compared states are exactly these (plus the question).
- To make S4 indistinguishable where it is required, P1, P2, P3, P5 (and odd P7 pairs)
  end with a later own observation, so that the current version is the same in A and B.
- Variants inside families: P3 / P4 correct the value, the valid_from or both (pair index
  mod 3); P5 / P6 retract a correction claim in every third pair (only its corrector may
  retract it - consequence (b) of section 2); P8 resolves the conflict by a higher assert,
  by a higher correction of a conflicting claim, or by a higher correction of a claim
  outside the conflict (Astra's v3 case), by pair index mod 3.
- Interventions run on world A at all four delays; "informative" is counted per pair at
  delay 0. swap_ranks swaps the critical report's source with the competing source, or
  with "self" when both have the same rank, and is skipped when no rank changes. The
  irrelevant control removes one irrelevant report (with its cascade) in odd pairs at
  delays > 0 and adds one otherwise.
- The audit decides whether a target ever created a claim with R's transition function
  (an audit use of R, never of M). Required cells on dev: 8 of 10 pairs (the holdout
  ratio 30 / 40).
- Freeze (idea 3): bench/m3/freeze40.py generates the holdout, lets R compute every
  expected answer (original and counterfactual) and writes the digests of worlds,
  questions, expected answers and interventions plus the SHA-256 of every code file into
  config/round40.json; the holdout run compares them before M runs and stops with
  FREEZE_MISMATCH otherwise. The request carries "attempt" and "repeat_of"; a repeat after
  a correction is labelled as such.
- Resources (idea 4): the run records wall time and the largest additional traced memory
  per kind of work (R, R on interventions, M, M on interventions, baselines, audit,
  persistence write and reload).

Dev run (2026-10-21, GitHub Actions run 39573228533, commit 5a44447; summary in
docs/ROUND_4_0_dev_SUMMARY.md; identical to a local run under another Python version
except the timings): DEV_OK on every criterion - M 2,400 / 2,400 answers right and equal
to R everywhere, 56 / 56 conformance checks, all 840 counterfactual cases as predicted
by R, 720 stores reloaded identically in a new process, no audit violation, all 15
required cells filled (10 / 10 pairs each). Baselines: S0 80, S1 736, S2 1,588, S3 1,832,
S4 900 of 2,400 answers; no baseline gets a single pair of a required cell right. Run
time on the runner 36.6 s in total (R 4.6 s with interventions, M 1.5 s, baselines 0.4 s,
audit 1.4 s, persistence 16.7 s); peak extra traced memory below 2 MB per kind of work;
the holdout (4 x the dev size) should need about 2.5 minutes.
Mutation check (docs/ROUND_4_0_mutation.json): 13 single changes of M, each run through
the full dev run in a fresh copy - all 13 fail at least one pass criterion.
Known limits of the generated data, stated before the holdout:
- Four mutants are caught ONLY by the hand-checked conformance set, because the
  generated worlds never exercise these paths: why_changed when only report ids change,
  a change on the anchor day (excluded by design), correcting an already withdrawn claim
  of the asked fact, an ambiguous anchor. The conformance set is a pass criterion, so the
  round covers them, but the generated holdout alone would not.
- The stale-answer measure is 0 for every system: it does not separate the systems in
  the dev data; the final own observations in several families contribute to that (P7
  with even index and P8 end differently). No particular resistance to stale answers can
  be derived from it; the exact hit criteria still count wrong answers outside this
  definition. Kept unchanged and reported as non-discriminating (Astra, implementation
  review).
- Truth measurement: 1,028 of 1,080 clean value questions agree with the world truth; all
  52 others are believed_at questions asked before a change was reported (Astra's v2
  counterexample) - by design, not an error.
- S2 gets every P2 and P9 pair fully right; S3 gets no pair of any family fully right,
  but many single answers (1,832 of 2,400; per operator in the results). The
  dissociation rests on the required cells, not on overall baseline scores.
- S3 and S4 are oracle baselines built from R: they test what bounded information
  allows, not a practical compacting memory.
- The irrelevant reports lie after the relevant ones (delayed recall and load), not
  among them; the results report states this.
- Measurement gaps in the resource figures (frozen code, so not changed before the
  holdout): M's answers on counterfactual worlds are computed outside the timed phase,
  and the reload process is a subprocess whose memory is not traced (its "0.0 MB" is no
  measurement).

Implementation review: APPROVE by Astra on 2026-10-21 (reviews/2026-10-21_r40impl_astra.txt)
- the holdout may be frozen with this code (lab main 94549fd) and run once. For the final
report she requires the evidence to stay separate: the four conformance-only paths are
secured by the fixed conformance cases, the generated holdout adds no coverage for them.
Her ideas for later: full process memory incl. the subprocess; truth agreement reported
separately for believed_at; a targeted stale test (questions right after a correction or
retraction, before a new own observation) in a follow-up round.
