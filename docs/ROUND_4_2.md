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
| correction | correct | subject, attribute, change (the place or person / the day / both), reference; value if the change includes the place or person, else "keep"; valid_from if it includes the day, else "keep" |
| retraction | retract | subject, attribute, reference |
| anchor event | assert / no | person, place, day |

The note type is NOT given to the extractor: it is the first predicted slot (section 3).
Semantically absent "not stated" is a CANDIDATE with its own score; "keep" follows from
the predicted change (since candidates c42.5, development log 5; reviewed 2026-10-23); an
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
and the world's source names; the MODEL sees only the note text - the header is used only
by the candidate rules and the canonical resolution ("my" -> author, "today" /
"yesterday" / "not stated" -> report day; since c42.4, reviewed 2026-10-23); the generator's note type, the gold report and the inverse
parser of section 2 are never used on this path (they are used only for scoring and the
checks before freezing). Step 1: the slot "type" with the labels statement, repeated
statement, correction, retraction, meeting (each with a one-line description) is scored
and decided like every slot (its own tau; uncertain -> declined). Step 2: the predicted
type alone selects the further slots and their candidate sets from the table of section 2
(kind and repeat follow from the type); for a correction, the predicted change (decided
before value and valid_from, cands42.USES order) selects whether value and valid_from are
asked; a wrong change makes the report wrong even if the asked fields are right. A wrong but confident type therefore leads to
wrong or missing fields and is counted as an extraction error (the slot "type" has its
own precision and acceptance in the measures).
Given candidates: object, place and person spans of the note (1-3 tokens, the round 3.5
canonicalisation contract), the names of the world's sources, day numbers 0 ... report
day, the type, aspect and change labels, "not stated" where the note type allows it. Score:
total log-probability of the complete candidate answer after a fixed slot prompt (round
3.5 S1 procedure, prefix cached); for the label slots type, attribute and change plus an
additive offset per label (variant D, Astra's decision of 2026-10-23,
reviews/2026-10-23_r42dev_astra.txt): fitted per model and slot on the DISTINCT
development notes whose true type uses the slot (type: all notes), first label fixed at
0, grid step 0.25 in [-30, 30], objective = right top-1 choices (a tie is not right),
start at 0, fixed coordinate order, ties -> smallest L1 norm, then the lexicographically
smallest vector, stop after a full pass without change; then frozen. Margin: best
canonical value minus the best different one (corrected scores). Per slot a threshold
tau, calibrated on the full calibration split only, along the PREDICTED decision path (the
top-1 type selects the slots, the top-1 change selects value / since; a slot is right
only if its value equals the true value of that slot - a slot the true type does not have
or a "keep" field asked counts as wrong): the highest acceptance with precision of accepted values >= 0.99 and >= 200
accepted values (round 3.5 rule; a slot without a qualifying tau always declines). Any
required field below its tau -> the note is DECLINED (not stored). Declining is no safe
default: a declined correction or retraction can leave an outdated answer standing, and
every such answer counts fully as an end-to-end error (also in the stale measure).
Model: qwen2.5-1.5b (pinned; qualified in 3.5b) as the primary model; on development
only, qwen3-1.7b is compared, and the model with the higher rate of fully correct stored
notes on development is frozen (rule fixed now; with offsets fitted on development these
rates are development diagnostics, Astra 2026-10-23). The raw and the content-free
corrected scores (development log 7) are reported next to the official variant D only; the
official variant is not re-chosen from them. Prompts, normalisation and candidate
generator are developed on development only.

## 4. Scope, splits, worlds, delays

Binding scope: the nine round 4.0 families P1-P9 (they contain every note type, including
anchors and repeats); the round 4.1 families T1-T5 are NOT part of this round. Splits by
whole pairs as in round 3.5: development 10, calibration 30 (raised from 10 before any model
run, section 8), audit 5 (model-free checks), holdout 40 pairs per family; texts of different splits are disjoint (checked).
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
(6) in EVERY family x delay cell (9 x 2 cells), all three: (a) E right on >= 0.90 of all
    questions; (b) E right on >= 0.90 of the CRITICAL questions (those whose gold differs
    between the worlds A and B of the pair at that delay); (c) pair success >= 0.90, a
    pair counting only if both worlds answer all critical questions of that delay right;
    exact denominators (all questions = questions per world x 2 x 40; every pair has at
    least one critical question - guaranteed by the round 4.0 pair conditions); an empty
    or unexpected denominator fails the cell (added after Astra's late review of v3,
    reviews/2026-10-22_r42v3_astra_late.txt, before any evaluation against the pass rule);
(7) no collector error.
1 %, 99 % and 90 % are technical target values fixed in advance; the observed values are
empirical rates of this holdout. Freeze, single holdout run and repeat labelling as in
phase A.

## 7. Cost estimate

Measured (development logs 3-6, CPU runners, prefix cache, all eleven slots): about 40 s
per note. Development 2,270 + calibration 6,836 distinct notes for both models: about 210
CPU hours (96 jobs, about 11 hours on the 20-job matrix). Holdout 9,107 distinct notes for
the frozen model: about 101 CPU hours, about 6 hours on the 20-job matrix. (The design
estimate of about one second per slot, i.e. ~20 CPU hours for the holdout, was too low by
a factor of about five.)

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
- Development log 2 - probe 1 (run 39832819294, p2, c42.2, 80 development notes; median
  38 s / 42 s per note): raw top choices qwen2.5-1.5b / qwen3-1.7b - type 73 / 75 of 80,
  attribute 63 / 55 of 64, valid_from 39 / 48 of 48, ref_source 37 / 37 of 48; subject,
  value, ref_day, person, place, day all right for both. Errors: named sources answered as
  "you" / "me" (both models, with large margins), repeats in the frames "As X told me",
  "X reported on day N that", "According to X" taken as statements, "with" / "was
  actually with" read as location (qwen3), "keep" in value-only corrections taken as a day
  (qwen2.5). Development changes: candidates c42.3 (source: all world source names plus
  "my", "your", "you", to be copied from the note; aspect labels "place" / "person") and
  prompt p3 (type question with the cue phrases of repeats; aspect with cue words; copy
  instruction for the source). Probe 2 scores only the four affected slots (a development
  option of the encode job, refused for the real encode phase).
- Astra's late review of v3 (delivered after her APPROVE of v3; archived as
  reviews/2026-10-22_r42v3_astra_late.txt): pass rule 6 now binds the critical questions
  and pair success per cell (section 6). At that time two development probes had run
  (prompt development, raw top choices only); nothing had been evaluated against the pass
  rule. Implemented in analysis42.mark_critical / rule6 with tests, including her negative
  test (12 questions per world, the one critical question wrong in every pair: 91.7 % of
  all questions right, rule 6 rejects every cell), a pair-success test and an unexpected
  denominator test. Her ideas: a greedily reduced repair set is reported next to the full
  one (report only - a joint repair is not a minimal cause); calibration counts per slot
  are reported before the freeze (planned for the calibration encode).
- Development log 3 - probe 2 (run 39851863283, p3, c42.3, the same 80 development notes,
  slots type, attribute, valid_from, ref_source only; median 12.6 s / 25.6 s per note):
  raw top choices qwen2.5-1.5b / qwen3-1.7b - type 76 / 79 of 80, attribute 62 / 55 of 64,
  valid_from 39 / 48 of 48, ref_source 42 / 45 of 48. Errors: qwen3-1.7b reads
  EVERY "has been with X" / "was actually with X" as a place (margins up to 15) although a
  worked example "was actually with Mara Lind" answers person - the nearest example
  "Correction to Pim's report of day 4: the green box was actually at Fern Hall" (place)
  wins; both models copy header words as the source ("Day 17, your own note. | Forget
  Gorvin's report ..." -> your; the author's name for another person's report);
  qwen2.5-1.5b still answers a day instead of "keep" in value-only corrections (8 of 9
  wrong cases) and reads "As X told me on day N" as a statement (4 cases). Development
  changes: candidates c42.4 and prompt p4 - the model sees only the note TEXT (the
  header's author and date are used only by the fixed rules: "my" -> author, "today" /
  "yesterday" / "not stated" -> report day; within section 3, whose inputs are the text,
  the header and the source names); aspect answers "at a place" / "with a person";
  contrastive worked examples (19, text only, outside the world vocabulary: every example
  frame that carries an aspect, a named source or a "keep" also appears with the other
  choice). Model-free checks: coverage on all four splits complete again (43,736 note
  occurrences), worked examples answer with candidates of their own text and use no world
  word (tests/test_round42_extractor.py), the encode job refuses any prompt but the current
  one (p1-p3 need their own candidate versions; they stay in the code for the log). Probe
  3: all ten slots on the same 80 notes, both models.
- Development log 4 - probe 3 (run 39866364037, p4, c42.4, the same 80 development notes,
  all ten slots; median 39 s / 40 s per note; cache check passed, max. difference
  1e-4): raw top choices qwen2.5-1.5b / qwen3-1.7b - type 80 / 78 of 80, attribute 58 /
  53 of 64, valid_from 43 / 48 of 48, ref_source 48 / 47 of 48; subject, value, ref_day,
  person, place, day all right for both. The header change removed every source error of
  qwen2.5-1.5b. Remaining errors: qwen2.5-1.5b answers "with a person" for retractions
  "about where ... is" (4) and the date-only correction "the move of ..." (1), margins up
  to 1.6 - the p4 examples were NOT balanced as intended (retractions 2 x person : 1 x
  place, the only date-only correction a handover), and the errors follow the majority;
  five value-only corrections still answered with the day of the earlier report instead
  of keep (margins up to 2.8). qwen3-1.7b now answers "at a place" for statements with
  "has had" and retractions "about who has" (margins up to 23) - with p3 it failed the
  other way ("with" -> place); its aspect follows the label wording, not the note.
  Development change: prompt p5 (candidates unchanged) - the contrast principle applied
  completely and checked by a test: within every note type as many place as person
  examples; per aspect a value-only and a date-only correction; as many "keep" as named
  days for since; every retraction frame with both aspects (25 examples); the since
  question says that the day of the earlier report is never the answer. Probe 4: slots
  type, attribute, valid_from, ref_source on the same 80 notes, both models (the other
  slots were right for both models in probe 3; the full encodes check them again).
- Development log 5 - probe 4 (run 39881855772, p5, c42.4, the same 80 development notes,
  slots type, attribute, valid_from, ref_source; median 16 s / 19 s per note; cache check
  passed): raw top choices qwen2.5-1.5b / qwen3-1.7b - type 80 / 75 of 80, attribute 62 /
  50 of 64, valid_from 40 / 48 of 48, ref_source 48 / 48 of 48. The balanced examples
  fixed qwen2.5-1.5b's aspect for retractions (2 errors left, margins <= 0.63); the
  sentence "the day of the earlier report is never the answer" made its "keep" errors
  worse (8 value-only corrections answered with the day of the earlier report, margins up
  to 3.3). qwen3-1.7b: aspect "at a place" for "has had" / "about who has" with margins up
  to 24 and repeats read as statements - its aspect follows the label wording in every
  version (p3, p4, p5); no further prompt work aims at it (it stays the comparison model of
  the fixed model rule, evaluated with the same frozen prompt). Development change:
  candidates c42.5 and prompt p6 - what a correction changes is its own label slot
  "change" (the place or person / the day / both); "keep" is no longer a candidate of
  value or since: a correction decides value only if it changes the place or person and
  since only if it changes the day, the other field is "keep" by that decision (same
  report contract, section 2; the decision order type -> change -> fields is the rule of
  section 3: candidates and slots follow from earlier predictions); the p5 since sentence
  is dropped; the corrections among the 25 examples are balanced over change x aspect
  (one each). Model-free checks: coverage on all four splits complete (43,736 note
  occurrences), oracle encodings reproduce the gold reports, example balance tested. In the
  calibration split, 1,078 correction occurrences change the value only, 80 the day only,
  80 both. Probe 5: slots type, attribute, change, value, valid_from, ref_source on the
  same 80 notes, both models.
- Development log 6 - probe 5 (run 39891511539, p6, c42.5, the same 80 development notes,
  slots type, attribute, change, value, valid_from, ref_source; median 25 s / 21 s per
  note; cache check passed): raw top choices qwen2.5-1.5b / qwen3-1.7b - type 80 / 75 of
  80, attribute 61 / 50 of 64, change 11 / 15 of 16, value 46 / 46 of 46, valid_from 36 /
  36 of 36, ref_source 48 / 48 of 48. The value / since errors are gone for both models;
  qwen2.5-1.5b now answers "both" for four value-only corrections and one date-only
  correction (margins up to 2.1, while its correct change answers have a median margin of
  1.6). Diagnosis (development data, report only): for qwen2.5-1.5b a constant offset per
  label would make change 16 / 16 and attribute 63 / 64 - its ranking of the notes is
  right, its label preference is skewed; for qwen3-1.7b's aspect even the best constant
  offset reaches only 59 / 64. Development option (NOT part of the approved scoring of
  section 3; to be reviewed before any use): label-prior correction ("contextual
  calibration", Zhao et al. 2021) for the label slots type, attribute and change - per
  label the model's probability after the same prompt with three content-free notes ("N/A",
  "[MASK]", empty), averaged; the corrected score is the raw score minus its logarithm (a
  constant per label and model, fitted to no data). The encodings stay raw; the correction
  is applied model-free in the analysis (analysis42.apply_priors, --priors). Next: a
  prior-only job (phase "prior", no notes) for both models with p6, then the raw and
  corrected choices of probe 5 side by side.
- Development log 7 - label priors (run 39901766514, phase prior, p6): qwen2.5-1.5b prefers
  "both" (change: log-prior -0.26 vs -1.92 / -2.50) and "retraction" / "statement"
  (type); qwen3-1.7b prefers "at a place" (-0.0 vs -9.1), "statement" (-0.0 vs -22 for
  "repeated statement") and "the place or person" / "both". Probe 5 with the correction,
  qwen2.5-1.5b / qwen3-1.7b (raw in brackets): type 75 (80) / 80 (75), attribute 61 (61) /
  56 (50), change 16 (11) / 16 (15); the other slots are not label slots. The
  parameter-free correction fixes change for both models and type for qwen3-1.7b, but
  overshoots qwen2.5-1.5b's type (four "As X told me" repeats and one "Update:" statement
  become corrections). A per-label offset fitted to data would keep qwen2.5-1.5b's type at
  80 and give change 16 and attribute 63 on these notes - in-sample, so no evidence by
  itself. The scoring decision (raw as approved / content-free correction / per-label
  offsets fitted on the calibration split before tau) goes to review; it is applied only
  model-free to the raw encodings, so the full development and calibration encodes run
  now with p6 / c42.5 for both models and serve every option.
- Astra's review of the development decision (reviews/2026-10-23_r42dev_astra.txt, package
  reviews/packages/LAB_R42_DEV_DECISION.txt): APPROVE of the changes 1-5 and her own
  variant D - the additive label offsets fitted on DEVELOPMENT instead of calibration, tau
  then on the full calibration split (no halving; the two rare change classes have only 40
  distinct calibration notes each). Her requirements, implemented before any development
  evaluation: the change slot is subject to slot precision and the 200 rule like every slot;
  calibration and evaluation follow the PREDICTED decision path, a required field skipped by
  a wrong change stays in the report (analysis42.calibration_cases, slot_report:
  "wrongly_skipped"); per model and label slot the offset vector, raw and corrected top-1,
  tau, accepted values, errors and precision; for change also per class with distinct
  notes and occurrences (predicting "value" alone is right for 519 of 599 calibration
  corrections, 86.6 %); sections 2-4 and 7 updated (change, derived keep, 30 calibration
  pairs, measured cost). Her improvement ideas, done: tests for the three field paths of a
  correction, an uncertain change and a wrong change; grid-edge hits of the offsets are
  reported (fit_offsets "at_grid_edge"); to do at the freeze: one manifest with the raw
  score, prompt, candidate, offset and tau versions. Implementation: analysis42.fit_offsets
  / offset_rows / apply_offsets, analyse_round42.py fit / evaluate --scoring offsets (raw
  and prior reported next to it only).
- Full encode (run 39902326532, dev + cal, both models, p6 / c42.5, 24 chunks): one job
  (qwen2.5-1.5b, calibration chunk 10) failed after 90 minutes because the hosted runner
  lost the connection to GitHub (infrastructure, no output); it is encoded again alone
  after the run.
- Variant D offsets fitted and frozen (before any calibration or development evaluation;
  inputs: the 2,270 distinct development notes of run 39902326532, all 24 development
  chunks of both models OK): config/round42_offsets_qwen2.5-1.5b+p6.json and
  config/round42_offsets_qwen3-1.7b+p6.json. Right top-1 raw -> corrected on the fit set,
  qwen2.5-1.5b: type 2,269 -> 2,270 of 2,270 (repeated statement -0.5), attribute 2,131 ->
  2,144 of 2,194 (with a person +0.5), change 149 -> 198 of 200 (both -2.25);
  qwen3-1.7b: type 2,239 -> 2,264 (repeated statement +22), attribute 1,457 -> 2,116
  (with a person +25), change 197 -> 199 (the day +0.25). No offset at the grid edge.
  In-sample by construction (development diagnostics); tau follows on the calibration
  split once its last chunk is re-encoded.
- Development evaluation (development diagnostics; calibration: run 39902326532 plus the
  re-encoded chunk, run 39924576993 - all 96 cells OK; offsets frozen before; holdout
  untouched). qwen2.5-1.5b, variant D: tau 0 for every slot except attribute (0.52) and
  change (1.47); calibration precision of accepted values: attribute 0.9901 (6,183 of
  6,547 accepted), change 0.9977 (443 of 547), every other slot 1.0. Development: 2,099 of
  2,270 distinct notes fully correct stored, 170 declined, 1 wrong; end to end 1,090 of
  1,200 (0.908); pairs 70 of 90; pass rule 6 met in 10 of 18 cells (P1, P2, P7, P8, P9 at
  both delays), failed in P3 (0.675 of all questions), P4, P5, P6. Memory correctness on
  every question, no unexplained error, no collector error. Direct causes of the 110 wrong
  answers: declined notes only - aspect uncertain (statements "X has had the Y since day
  N": 46 of 145 declined on development, 161 of 513 on calibration; retractions "about
  where ... is"; value-only corrections "was actually at X"), change uncertain (corrections
  "Please fix X's report of day N - the Y was actually with X": 16 of 17 development, 45 of
  48 calibration), and retractions whose aspect was accepted wrong (their reference then
  matched no stored report and the collector declined them - safe, but an error). Change per class on
  calibration (out-of-sample for the offsets): value 509 of 519, date 40 of 40, both 18 of
  40 right top-1 (development, in-sample: 10 of 12). Report-only variants: raw - no tau
  for change and valid_from (on the predicted path the raw "both" answers ask valid_from
  for value-only corrections), 76 notes stored, 160 of 1,200 right; content-free prior -
  no tau for change, ref_source, ref_day, 1,028 stored, 596 right. qwen3-1.7b, variant D:
  attribute tau 13.0, 612 stored, 358 of 1,200 right, 0 of 18 cells. Model rule (fully
  correct stored development notes): qwen2.5-1.5b (2,099) over qwen3-1.7b (612). Even
  with offsets fitted on these development notes, pass rule 6 fails in four families; the
  errors are systematic per wording (as in round 3.6). Decision on how to continue goes to
  review (reviews/packages/LAB_R42_DEV_RESULT.txt).
