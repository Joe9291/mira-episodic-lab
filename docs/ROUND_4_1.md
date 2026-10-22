# Round 4.1 - Targeted stale-answer test (design v2, draft for review)

Context: round 4.0 phase A passed (docs/ROUND_4_0.md section 8), but its stale-answer
measure did not discriminate: 0 stale answers for every system, because the worlds mostly
ended with a fresh own observation. Astra recommended a small targeted test before phase
B: current questions immediately before and after a correction, retraction or conflict
change, before any further own observation confirms the state again, with the
current-state oracle S4 as positive control (reviews/2026-10-21_r40impl_astra.txt,
2026-10-22_r40result_astra.txt, 2026-10-22_r40result_v3_astra.txt). v2 answers her
review of v1 (reviews/2026-10-22_r41v1_astra.txt): two real current questions on report
prefixes instead of believed_at, the common property of the B worlds stated precisely,
S5 defined on prefixes with a complete exported state, the new hand cases in their own
fixture, failure classes with a fixed priority and an explicit over-update flag.

Uncertainty removed: does M switch its CURRENT answer immediately when an effective
correction, retraction, conflict creation, conflict resolution or higher-rank override
arrives - and does it keep its answer when the same report is ineffective - also after
up to 500 irrelevant reports? And in which way do simpler memories fail: by keeping the
previously accepted answer (stale) or by accepting an ineffective report (over-eager)?
Claim limits (fixed now): as in round 4.0 - the GIVEN source policy, within this
generator, on a frozen finite sample; no learned trust, no truth finding, no language.

## 1. What stays from round 4.0

M (episodic_lab/r40_memory.py), R (r40_reference.py), the report schema, the transition
rules, the hit definitions, the audit, the persistence test and the conformance set of
round 4.0 are used UNCHANGED (their files keep the hashes of the 4.0 freeze). New code:
a generator for the five families below, the baseline S5, about 10 new hand-computed
cases in their own fixture (tests/fixtures/r41_conformance.json, so the 4.0 hashes stay),
and a runner that writes every table of its summary directly from the evaluation rows
(Astra's idea: text and result files cannot diverge). The 4.1 freeze binds the 4.0 files
unchanged plus the new generator, S5, runner and fixture.

## 2. Families (pairs A / B differ only in the critical report c)

Every world: an own observation X (valid from d0), a report Q of a trusted person
(rank 2) making Y the current value (valid from d1 > d0), then c on day d3 - all
preparatory relevant reports lie on days <= d3 - 1, and there is NO relevant report
after c. The irrelevant reports of the delay (0, 50, 200, 500) follow c. Common property
of the worlds: in A, c changes the current policy answer; in B, the current policy answer
stays as it was before c (c itself may be ineffective, or effective without changing the
answer - see T3).
- T1 correction of the current claim: c corrects Q's report to Z; A: corrector of rank
  >= 2 (effective -> Z), B: hearsay (ineffective -> Y).
- T2 retraction of the current claim: c retracts Q's report; A: by Q (effective -> back
  to X; in every second pair there is no X, so the answer becomes unknown / no_version),
  B: by the other trusted person (ineffective -> Y).
- T3 conflict resolution: before c a second trusted person states Z for the same
  valid_from (open conflict {Y, Z}); c brings V: A: own observation (assert, or a
  correction of a conflicting claim, or of a lower hearsay claim outside the conflict -
  pair index mod 3; -> V), B: the same report from a hearsay source - an ineffective
  assert or correction in the first two variants; in the third the hearsay corrector may
  effectively correct the rank-1 claim, but the rank-2 conflict stays, so the current
  policy answer is unchanged in every B world.
- T4 conflict creation: c states Z for the same valid_from; A: the other trusted person
  with a different origin (-> conflict {Y, Z}), B: hearsay (-> Y).
- T5 higher-rank override: c states Z for the same valid_from; A: own observation
  (-> Z), B: hearsay (-> Y).

## 3. Questions, logged values and failure classes

Per world two real CURRENT questions, each evaluated by every system on a report prefix
(Astra's v1 review): BEFORE - current on the prefix of all reports with day <= d3 - 1
(question day d3 - 1); AFTER - current on the full world (c and the irrelevant reports of
the delay; question day now). Because the irrelevant reports follow c, the BEFORE prefix is
the same at all four delays; it is therefore evaluated once per world, not four times.
Holdout: 5 families x 40 pairs x 2 worlds = 400 BEFORE answers plus 400 worlds x 4 delays
= 1,600 AFTER answers, 2,000 in total (dev: 10 pairs per family, 500 answers). believed_at
is not used (it would measure a baseline's historical strategy, not its state before c).
For every AFTER question the run logs the PREVIOUSLY ACCEPTED ANSWER (Astra's v1 idea) -
the gold BEFORE answer of the same world - and classifies every answer of every system in
this priority order (Astra's v1 idea): right; stale (equal to the previously accepted
answer under the hit definition); wrong conflict output; wrong abstention (unknown);
other wrong value. Stale rate: denominator = AFTER questions whose gold differs from the
previously accepted answer (the A worlds); numerator = stale answers. Over-update flag
(Astra's v1 idea): in a B world, the system's BEFORE answer was right and its AFTER
answer is wrong - the neutral report changed its answer.

## 4. Systems

M; S0-S4 as in round 4.0 (S3 and S4 are oracle baselines built from R; S4 is the positive
control: it must answer every current question right, otherwise the generator or R is
wrong); new S5 naive updater: on the report prefix it receives, it applies EVERY
correction and retraction to its target regardless of rank and source, and the latest
standing claim in the total order wins (rank, valid_from and conflicts ignored). Every
system answers BEFORE and AFTER from its own processing of the respective prefix; S3 and
S4 use R's history on that prefix.
Expected failure directions (not pass criteria): S1 and S2 stale on T1 / T2 in world A;
S5 over-eager in world B of T1, T2, T3, T5.
Visible states for B-indistinguishability (AFTER question, full world): S1 its value;
S2 its assert list (report day, id, valid_from, value); S5 its standing claims (id, value)
in total order - for each system exactly the information its answer uses.

## 5. Pass rule (fixed before any run)

Zero errors of M on all 2,000 holdout answers; M equal to R on every question; the round
4.0 conformance set plus about 10 new hand-computed cases (one per family and world
type, with the T2 variant without X and all three T3 variants; written before any run;
own fixture) 100 %; S4 right on every current question (positive
control); interventions as predicted by R - remove_change (remove c, with cascade:
world A must return to the previously accepted answer; >= 30 changed pairs at delay 0
per family) and the irrelevant control (all unchanged), reported per type with the
columns "answer changed" / "unchanged"; persistence test; audit clean; required
B-indistinguishable cells: S1, S2 and S5 on each of T1-T5 (15 cells) with >= 30 of the
40 holdout pairs (dev: 8 of 10). No other numeric threshold; failure classes and stale
rates of all systems are reported per family and delay.
Freeze as in round 4.0: worlds, questions, expected answers, intervention outcomes and
code hashes are written into the request after the implementation review, compared
before M runs; one holdout run; any repeat is labelled as a repeat.

## 6. Limits known in advance

- The test is narrow by design: one fact per world, the change is the last relevant
  report, no free text. It closes the gap of the non-discriminating stale measure of
  round 4.0, nothing more.
- S3 and S4 are oracles for the current answer; they will be right on current questions
  and are reported as controls, not as competitors.
- The BEFORE answer has no delay (the irrelevant reports follow c); delayed recall is
  tested only on the AFTER answer.
- Resource figures: total process memory (including the reload subprocess) and the
  complete answer computation are measured in this runner (Astra's idea from round 4.0).
