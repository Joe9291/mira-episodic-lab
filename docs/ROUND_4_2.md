# Round 4.2 - Phase B: reports as notes in language, extracted by a small LM (design v3, approved 2026-10-22 - reviews/2026-10-22_r42v3_astra.txt; implementation notes in section 8)

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
denominators (section 6); the scope fixed to P1-P9 (section 4). v3 answers her review of v2
(reviews/2026-10-22_r42v2_astra.txt): the note type is itself a predicted slot, and slot
and candidate choice depend only on visible input, fixed rules and earlier predictions
(section 3); the anchor report is constructed explicitly (section 1); the repair check
covers the same causes as the analysis, including anchors and reference dependencies,
and collector errors fail the round (sections 5-6).

Uncertainty removed: can "LM-assisted structured extraction with given candidates" (the
system qualified in round 3.5b for episode notes) turn report notes into reports for M so
that the memory still answers the structured questions of phase A - and is every wrong
answer explained by identified extraction (or collector) errors, never by the memory?
Claim limits (fixed now): the claim is about the whole pre-frozen system (model, prompt,
candidates, thresholds, collector rules) on generated notes from fixed wording sets, at
delays 0 and 20; not about free reading of real conversations; the memory part stays the
GIVEN source policy.

## 1. Who decides what

Collector (deterministic, no LM): report_id = the note's arrival number (r00001 for the
first note of a world, ...; a declined note leaves its number unused, so every stored E
report has the same id as the gold report of the same note), report_day (the note's date
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
Anchor events are notes too ("Today I met Ida Voss at the old mill."): the extractor
returns the person span, the place span and the day (explicit, relative or "today"); the
collector builds the complete report: kind assert, subject "event:met <person> at
<place>" (canonical spellings), attribute "day", value = the day, valid_from 0, origin
new.

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
| anchor event | assert / no | person, place, day |

The note type is NOT given to the extractor: it is the first predicted slot (section 3).
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

Extraction path (fixed): the inputs are only the note text, its header (author, date)
and the world's source names; the generator's note type, the gold report and the inverse
parser of section 2 are never used on this path (they are used only for scoring and the
checks before freezing). Step 1: the slot "type" with the labels statement, repeated
statement, correction, retraction, meeting (each with a one-line description) is scored
and decided like every slot (its own tau; uncertain -> declined). Step 2: the predicted
type alone selects the further slots and their candidate sets from the table of section 2
(kind and repeat follow from the type). A wrong but confident type therefore leads to
wrong or missing fields and is counted as an extraction error (the slot "type" has its
own precision and acceptance in the measures).
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
  (should never occur; every collector error fails the round, pass rule 7).
Repair check (deterministic): for every end-to-end error the REPAIR SET is formed from
the same scope as the analysis - every note whose E report differs from its G report
(declined, stored wrong, follow-up) that belongs to the asked fact or to its anchor
event, every note those reference (correction targets, repeated statements), transitively,
and every irrelevant note injected into the asked fact or its anchor. In a copy of E the
notes of the repair set are replaced by their gold reports (same ids, see section 1) and
injected reports are removed; the copy must pass the general round 4.0 audit (valid,
unique ids, total order); the question is answered again and must equal R(G, q). An error
that this does not repair is unexplained (pass rule 2). Every repair records the changed
note ids; a successful joint repair does not establish a minimal single cause.
Hand cases (before any model run, own fixture): a declined correction leaving the old
value, a missing reference target, a repeat chain, an injected irrelevant note, a wrong
anchor day, a wrongly predicted note type and a wrongly taken over origin, each with the
expected E store, answers, causes and repair set.
Per note the run logs the predicted type, the slots actually asked, every decision with
its margin, and the decline reason.
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
    cells); the critical questions and pair success per cell are reported next to it;
(7) no collector error.
1 %, 99 % and 90 % are technical target values fixed in advance; the observed values are
empirical rates of this holdout. Freeze, single holdout run and repeat labelling as in
phase A.

## 7. Cost estimate

About 27 distinct notes per pair (relevant notes, the critical variant, 20 irrelevant
notes), 9 families x 40 pairs on the holdout -> about 10,000 notes x up to 7 slots; at about
one second per slot with the prefix cache, ~20 CPU hours, i.e. about an hour on a 20-job
matrix (as in round 3.6). Development and calibration together are about half.

## 8. Implementation notes (after the APPROVE of v3)

- Astra's idea 1: the rows "timely assert" and "late assert" of section 2 are both the
  predicted type "statement"; its candidate space is the same for both: subject, attribute,
  value, and valid_from from {"not stated"} plus the days 0 ... report day.
- Astra's idea 2: a repeat that takes over, by the collector rule, the origin of a report
  that was itself extracted wrongly is a FOLLOW-UP error, not a collector error. A
  collector error is determined against the collector contract (section 1) applied to the
  extracted fields and the E history actually present at that moment - i.e. the collector
  did not do what its contract prescribes for those inputs.
- Astra's idea 3, counted before any model run (structured reports of the round 4.0
  generator, delays 0 and 20, distinct notes): a 10-pair split per family yields 1,712
  statements, 107 repeats, 204 corrections, 148 retractions and 91 meetings. The slots
  person, place and day of meetings (91) and the correction-only slots (204) could not
  reach the 200 accepted values of the calibration rule. The calibration split is
  therefore enlarged to 30 pairs per family (about 270 meetings, 320 repeats, 610
  corrections, 440 retractions - to be confirmed by the model-free audit before any model
  run); development, audit and holdout stay as designed.
- Wordings and worlds (model-free, before any model run): episodic_lab/r42_wordings.py
  (per note type and attribute ten frames; correction clauses for value / date / both;
  relative days "today" / "yesterday" chosen by hash; references always "day N"),
  episodic_lab/r42_world.py (the P1-P9 families with phase B seeds; the irrelevant
  reports of a delay are drawn again until every correction, retraction and repeat has
  exactly one earlier report with its (source, day, subject, attribute) - only irrelevant
  reports ever needed it, at most 5 attempts), tests/test_round42.py: every frame of every
  note type, attribute and correction subtype round-trips through its exact inverse parser
  on all development reports (> 10,000 renderings); references unique in all splits;
  the notes of a pair differ at most in the critical note; header + text sets of the four
  splits are disjoint. Distinct notes: development 2,276, calibration 6,825, audit 1,134,
  holdout 9,101. bench/m3/wordings42_sheet.py writes the sheet for Joe's meaning check
  (one example of each of the 60 frames, every clause included).
- Joe's meaning check (2026-10-22): "passt" for all 60 examples, with the request to
  check again. Claude's second check found two ambiguities, both fixed and shown to Joe
  again: (a) a relative day inside a repeated statement ("Passing on what Dorran said on
  day 3: ... since yesterday") can be read relative to the repeating author's day or to
  the original speaker's day - repeats now always name the explicit day; (b) the meeting
  frame "Meeting on day 8 with ..." in a note by another person does not say whose
  meeting it was - it now reads "Your meeting ..." / "My meeting ...". All other frames
  unchanged; round-trip tests re-run.
- Joe confirmed the four changed examples ("passen") and asked for one more own check.
  An automatic scan of ALL generated notes of all four splits found three data problems
  (no frame problem), all fixed in the world generation and checked by tests: (c) a
  person "repeating" their own statement ("As Ilsen told me on day 14 ..." in Ilsen's own
  note; "According to I ...") - phase B worlds now contain no repeat by the speaker it
  repeats (the irrelevant set is drawn again); (d) a correction naming a day after its own
  report day ("from day 9" written on day 8; it came from the P3 / P4 family draw) - the
  family draw is repeated until no report names a future day; (e) an author's first name
  inside a person's name ("note from Brenna" next to "Brenna Lunsey") - the four sources
  now get the four first names that no person of the world carries. After the fixes the
  scan finds none of these and no doubled words, "on yesterday", "day 0" or self-named
  authors; distinct notes: development 2,270, calibration 6,836, audit 1,133, holdout
  9,107; the meaning-check sheet was regenerated with the unchanged frames.
- Extractor (before any model run): episodic_lab/cands42.py (candidate contract, slot truth
  for scoring), episodic_lab/encoder42.py (slot questions and seven worked examples
  outside the world vocabulary, prompt p1), bench/m3/run_round42_encode.py (phases timing /
  probe / encode, chunks), bench/m3/collect_round42.py, .github/workflows/round42.yml
  (the round 3.6 matrix pattern). Every one of the ten slots (type, subject, attribute,
  value, valid_from, ref_source, ref_day, person, place, day) is scored for every note, so
  the encoding does not depend on any decision; the slots a note USES and their allowed
  candidates ("not stated" only for statements, "keep" only for corrections) follow later,
  model-free, from the PREDICTED type alone. "not stated" has the canonical value of the
  report day (it merges with an explicit report day), "today" / "yesterday" the report day
  / the day before, "you" = the reader ("self"), "me" = the author. Model-free coverage
  audit on all four splits (43,736 note occurrences): the true value of every slot of the
  true type is among the candidates in every case. Timing slice: 20 development notes
  (one per gold type and development frame); probe slice: 80.
- Development log 1 - timing slice (run 39819460089, prompt p1, candidates c42.1, 20
  development notes): median 46 s per note for qwen2.5-1.5b and 55 s for qwen3-1.7b with
  63.5 scored candidates per note, 23.5 of them for the subject; cache check passed. Raw
  top choices (before any threshold), qwen2.5-1.5b / qwen3-1.7b: type 17 / 19 of 20,
  attribute 13 / 15 of 16, valid_from 10 / 11 of 12, ref_source 12 / 9 of 12, ref_day 11 /
  11 of 12, subject, value, person and place all right; typical errors: "keep" in
  value-only corrections taken as a day, "about who has" read as location, a repeat in the
  reader's own note given the source "me". Development changes: candidates c42.2 (subject
  = the one or two lower-case words after an article; coverage still complete on all
  splits, 2.3 instead of 23.5 subject candidates per note) and prompt p2 (sharper type,
  aspect, since and source questions; fourteen worked examples from template and
  development frames only). Next: probe of 80 development notes with p2 for both models.
