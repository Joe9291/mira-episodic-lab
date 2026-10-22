# Round 4.2 - Phase B: reports as notes in language, extracted by a small LM (design v2, draft for review)

Context: phase A (rounds 4.0, 4.1, 4.1b) showed that M, the fixed source policy and the
two-time resolver answer every structured question exactly - on reconstruction from
report prefixes and with one continued instance. Phase B replaces the STRUCTURED reports
by short notes in language, read by a small language model. Astra's guidance (reviews of
4.0 v2, 4.1 result, 4.1b v1): questions stay structured, the resolver and the source
policy stay unchanged; a parallel control with the correct structured reports separates
extraction errors from memory errors; administrative data (report ids, ranks) come from
the collector and the metadata policy, not from the language extraction; the first
extraction checks must cover correction / retraction references, source attribution and
valid times. v2 answers her review of v1 (reviews/2026-10-22_r42v1_astra.txt): two
separate comparisons per question and a cause analysis with follow-up and collector
errors (section 5); the false claim about declines removed (section 3); references
resolved only against already stored reports (section 1); an executable origin rule and
required fields per note type (sections 1-2); thresholds per family and delay with exact
denominators (section 6); the scope fixed to P1-P9 (section 4).

Uncertainty removed: can "LM-assisted structured extraction with given candidates" (the
system qualified in round 3.5b for episode notes) turn report notes into reports for M so
that the memory still answers the structured questions of phase A - and is every wrong
answer explained by identified extraction (or collector) errors, never by the memory?
Claim limits (fixed now): the claim is about the whole pre-frozen system (model, prompt,
candidates, thresholds, collector rules) on generated notes from fixed wording sets, at
delays 0 and 20; not about free reading of real conversations; the memory part stays the
GIVEN source policy.

## 1. Who decides what

Collector (deterministic, no LM): report_id (arrival order), report_day (the note's date
header), source = the note's AUTHOR (header), rank from the fixed metadata policy (own 3,
trusted 2, hearsay 1), origin, and the resolution of every reference.
Extractor (LM, candidates given) - per note the fields of its note type (section 2):
kind (assert / correct / retract), repeat (yes / no; only for assert), subject,
attribute, value or "keep", valid_from or "not stated" / "keep", and a reference given as
a source NAME and a DAY - never a report id. Three roles are kept apart: the author is
always the source; the quoted speaker of a repeated statement appears only in the
repeat's reference; the target of a correction or retraction appears only in its
reference.
Reference resolution: (source, day, subject, attribute) is matched ONLY against the
reports already stored in arm E (a gold reference never stands in for a missing E
report). Exactly one match -> resolved; none or several -> the note is declined
(logged with the reason).
Origin rule: a new note gets a new origin; a repeat (kind assert, repeat yes) gets the
origin of its resolved reference - which, if that report is itself a repeat, already
carries the origin of its own reference, so chains are followed automatically.
valid_from "not stated" means the report day (an assert that names no day speaks about
the day it is written); "keep" in a correction means the old value / old valid_from.
Anchor events are notes too ("Today I met Ida Voss at the old mill."): subject = the
event, value = its day (explicit, relative or "today").

## 2. Notes, required fields, wordings

Every report of the round 4.0 generator (families P1-P9) is rendered as a note from its
structured form. Note types and their required fields (all other fields are not asked):

| note type | kind / repeat | required fields |
|---|---|---|
| timely assert | assert / no | subject, attribute, value, valid_from ("not stated" allowed) |
| late assert ("back on day 4 ...") | assert / no | subject, attribute, value, valid_from |
| repeated statement | assert / yes | subject, attribute, value, valid_from, reference |
| correction | correct | subject, attribute, reference, value or "keep", valid_from or "keep" (not both "keep") |
| retraction | retract | subject, attribute, reference |
| anchor event | assert / no | subject (event), value (day) |

Semantically absent ("not stated", "keep") is a CANDIDATE with its own score; an
uncertain field (margin below its threshold) is a different state and declines the whole
note. Wordings: per note type the template plus 3 development, 3 holdout and 3 reserve
paraphrases, written before any model run; relative days ("yesterday", "two days ago")
occur in every split. Checks before freezing, as in round 3.5: an exact inverse parser per
paraphrase returns exactly the structured report; the wording of a note is chosen by a
hash of (pair seed, note position), so the worlds of a pair differ only in the critical
note; one rendered example of EVERY template is checked by Joe against the structured
report; per frame and split the number of distinct texts is reported (every holdout frame
>= 30).

## 3. Extraction method (from round 3.5b, re-qualified here)

Given candidates: object, place and person spans of the note (1-3 tokens, the round 3.5
canonicalisation contract), the names of the world's sources, day numbers 0 ... report
day, the kind, repeat and attribute labels, "not stated" / "keep" where the note type
allows them. Score: total log-probability of the complete candidate answer after a fixed
slot prompt (round 3.5 S1 procedure, prefix cached); margin: best canonical value minus
the best different one. Per slot a threshold tau, calibrated on the calibration split
only: the highest acceptance with precision of accepted values >= 0.99 and >= 200
accepted values (round 3.5 rule; a slot without a qualifying tau always declines). Any
required field below its tau -> the note is DECLINED (not stored). Declining is no safe
default: a declined correction or retraction can leave an outdated answer standing, and
every such answer counts fully as an end-to-end error (also in the stale measure).
Model: qwen2.5-1.5b (pinned; qualified in 3.5b) as the primary model; on development
only, qwen3-1.7b is compared, and the model with the higher rate of fully correct stored
notes on development is frozen (rule fixed now). Prompts, normalisation and candidate
generator are developed on development only.

## 4. Scope, splits, worlds, delays

Binding scope: the nine round 4.0 families P1-P9 (they contain every note type, including
anchors and repeats); the round 4.1 families T1-T5 are NOT part of this round. Splits by
whole pairs as in round 3.5: development 10, calibration 10, audit 5 (model-free checks),
holdout 40 pairs per family; texts of different splits are disjoint (checked).
Development, calibration and audit use only the template and development paraphrases;
holdout uses the holdout paraphrases. Delays: 0 and 20 irrelevant NOTES (also extracted);
the finding holds for these delays only.

## 5. Arms, comparisons and cause analysis

Arm G: the generator's correct structured reports. Arm E: the reports the collector
stored from the extracted notes. Same worlds, same structured questions (the round 4.0
case table), same M, same R. For every question two separate comparisons:
- memory correctness: M(E, q) == R(E, q) on exactly the stored E reports - must hold for
  every question (a failure is a memory failure);
- end-to-end correctness: M(E, q) against R(G, q) under the round 4.0 hit definition.
Cause analysis for every end-to-end error, per note of the asked fact and its anchor in
G, and per note stored into the asked fact or its anchor in E (an injected irrelevant
note):
- direct extraction error: a required field wrong (stored wrong) or uncertain (declined);
- follow-up error: the note's own fields were extracted correctly, but its reference
  could not be resolved (target declined or stored wrong earlier) or resolved to a wrong
  report because of an earlier error;
- injection: an irrelevant note stored into the asked fact (wrong subject or attribute);
- collector error: all fields extracted correctly, yet the stored report differs from G
  (should never occur; reported separately).
Repair check (Astra's idea, deterministic): for every end-to-end error, the erroneous
notes of the asked fact (direct, follow-up, injected) are replaced by their gold reports
in E (injected ones removed) and the question is answered again; it must then equal
R(G, q). An error that this does not repair is unexplained and counts against the claim.
Hand cases (before any model run, own fixture): a declined correction leaving the old
value, a missing reference target, a repeat chain, an injected irrelevant note, each with
the expected E store, answers and causes.
Measures, per slot: accepted / declined / wrong accepted, precision, acceptance; per note:
stored correct, declined (threshold / unresolved reference), stored wrong; references
resolved correctly / declined / resolved wrongly; injections; end-to-end answers right per
operator x family x delay, with the CRITICAL questions (those whose gold differs between
the worlds A and B of a pair) and pair success reported separately; uncertainty
intervals on the level of whole pairs (questions of one pair are not independent).

## 6. Pass rule (fixed before any run)

On the holdout, all of:
(1) memory correctness on every question (zero exceptions);
(2) every end-to-end error repaired by the repair check (zero unexplained errors);
(3) stored wrong notes <= floor(0.01 n) of all holdout notes; and in the asked facts:
    (relevant notes stored wrong + injected notes) <= floor(0.01 n_relevant), where
    n_relevant = the notes of the asked facts and their anchors in G;
(4) per slot, precision of accepted values >= 0.99 on the holdout; a slot with an empty
    accepted set has an undefined precision, which never passes (the round 3.5 rule) -
    so a slot without a qualifying tau fails the round;
(5) arm G right on every question (control);
(6) end-to-end: E right on >= 0.90 of the questions in EVERY family x delay cell (9 x 2
    cells); the critical questions and pair success per cell are reported next to it.
1 %, 99 % and 90 % are technical target values fixed in advance; the observed values are
empirical rates of this holdout. Freeze, single holdout run and repeat labelling as in
phase A.

## 7. Cost estimate

About 27 distinct notes per pair (relevant notes, the critical variant, 20 irrelevant
notes), 9 families x 40 pairs on the holdout -> about 10,000 notes x up to 7 slots; at about
one second per slot with the prefix cache, ~20 CPU hours, i.e. about an hour on a 20-job
matrix (as in round 3.6). Development and calibration together are about half.
