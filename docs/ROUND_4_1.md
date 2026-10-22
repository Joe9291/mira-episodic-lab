# Round 4.1 - Targeted stale-answer test (design v1, draft for review)

Context: round 4.0 phase A passed (docs/ROUND_4_0.md section 8), but its stale-answer
measure did not discriminate: 0 stale answers for every system, because the worlds mostly
ended with a fresh own observation. Astra recommended a small targeted test before phase
B: current questions immediately before and after a correction, retraction or conflict
change, before any further own observation confirms the state again, with the
current-state oracle S4 as positive control (reviews/2026-10-21_r40impl_astra.txt,
2026-10-22_r40result_astra.txt, 2026-10-22_r40result_v3_astra.txt).

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
a generator for the five families below, the baseline S5, and a runner that writes every
table of its summary directly from the evaluation rows (Astra's idea: text and result
files cannot diverge).

## 2. Families (pairs A / B differ only in the critical report c)

Every world: an own observation X (valid from d0), a report Q of a trusted person
(rank 2) making Y the current value (valid from d1 > d0), then c on day d3 - and NO
relevant report after c. The irrelevant reports of the delay (0, 50, 200, 500) follow c.
- T1 correction of the current claim: c corrects Q's report to Z; A: corrector of rank
  >= 2 (effective -> Z), B: hearsay (ineffective -> Y).
- T2 retraction of the current claim: c retracts Q's report; A: by Q (effective -> back
  to X; in every second pair there is no X, so the answer becomes unknown / no_version),
  B: by the other trusted person (ineffective -> Y).
- T3 conflict resolution: before c a second trusted person states Z for the same
  valid_from (open conflict {Y, Z}); c brings V: A: own observation (assert, or a
  correction of a conflicting claim, or of a lower claim outside the conflict - pair
  index mod 3; -> V), B: hearsay (the conflict stays).
- T4 conflict creation: c states Z for the same valid_from; A: the other trusted person
  with a different origin (-> conflict {Y, Z}), B: hearsay (-> Y).
- T5 higher-rank override: c states Z for the same valid_from; A: own observation
  (-> Z), B: hearsay (-> Y).

## 3. Questions, logged values and failure classes

Per world two questions (fixed case table): current (asked at now, after the irrelevant
reports) and believed_at(d3 - 1) (the answer just before c). Holdout: 5 families x 40
pairs x 2 worlds x 4 delays x 2 questions = 3,200 answers; dev 10 pairs per family.
For every current question the run logs the PREVIOUSLY ACCEPTED ANSWER - R's current
answer at the end of day d3 - 1 (Astra's idea) - and classifies every answer of every
system as: right; stale (wrong and equal to the previously accepted answer under the hit
definition); other wrong value; wrong conflict output; wrong abstention (unknown).
Stale rate: denominator = current questions whose gold differs from the previously
accepted answer; numerator = stale answers.

## 4. Systems

M; S0-S4 as in round 4.0 (S3 and S4 are oracle baselines built from R; S4 is the positive
control: it must answer every current question right, otherwise the generator or R is
wrong); new S5 naive updater: it applies EVERY correction and retraction to its target
regardless of rank and source, and the latest standing claim in the total order wins
(rank, valid_from and conflicts ignored; knowledge time respected for believed_at).
Expected failure directions (not pass criteria): S1 and S2 stale on T1 / T2 in world A;
S5 over-eager in world B of T1, T2, T3, T5.
Visible states for B-indistinguishability: S1 its value; S2 its assert list (report day,
id, valid_from, value); S5 its standing claims (id, value) in total order.

## 5. Pass rule (fixed before any run)

Zero errors of M on all 3,200 holdout answers; M equal to R on every question; the round
4.0 conformance set plus about 10 new hand-computed cases (one per family and world
type, written before any run) 100 %; S4 right on every current question (positive
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
- Resource figures: total process memory (including the reload subprocess) and the
  complete answer computation are measured in this runner (Astra's idea from round 4.0).
