# Round 3.6 - LM-assisted goal/question parsing (design v3)

Uncertainty removed: can the same small language model, used the same way as in round 3.5b
(scores for given candidates, schema-constrained decoding, thresholds from a calibration
split, frozen before a blind holdout), turn FREE-LANGUAGE goals and questions into the
structured question specification the fixed memory operators use - and recognise questions
it must not answer from memory - on wordings it was not developed on? Name of the system:
"LM-assisted question parsing with given candidates".
Order (Astra, reviews/2026-10-19_r35b_reserve_astra.txt): the parser is checked first
against correct question specifications and with a CORRECT store, so that parser errors
stay identifiable; d3 stays frozen; the combination follows as a separate step (section 7).
v2 answers Astra's review of v1b (reviews/2026-10-19_r36v1_astra.txt): a complete decision
table (section 3), fixed frequencies, text separation and pairing (section 2), complete
specifications and denominators for every criterion (section 5), the time semantics bound
to the operators (section 1), actor questions as unsupported controls, Q1-Q4 as decided.
v3 answers her review of v2 (reviews/2026-10-19_r36v2_astra.txt): the generator conditions
per world kind (section 1), the target calibration only on texts with a defined gold target
and the behaviour with missing thresholds (section 3), the baseline's temporal-clause rule
and its information basis (section 3); planned tests for these: a giver world passes its
audit, a gold-unsupported text accepted as supported, only tau_target missing, a supported
previous question with a full "before ..." clause.

## 1. Question specification and time semantics

Gold specification of every question: `intent` (one of seven supported types or
`unsupported`) and, for a supported intent, `target` (a value or `none`).
- Supported types (the goals of rounds 3.3/3.4) with their operator meaning:
  object_current / object_first / object_previous: the target object's placing records
  (put, hid, left) ordered by event day - the latest / the earliest / the one before the
  latest (history_place); person_current / person_first / person_previous: the records
  mentioning the target person, same positions; giver: the unique person who gave the agent
  the target object, then that person's latest record. The target of object types and of
  giver is an object (adjective + noun), of person types a person (first + last name).
- Binding of the wordings to this meaning, by world kind (v3: the conditions apply only to
  the kind whose goals need them; checked on all five 3.5 splits, 210 worlds per kind):
  - object (history): the target object has exactly three placing records, never two
    consecutive ones at the same place, and occurs in no other event;
  - person (history): the target person has exactly three records, all "seen";
  - hidden / moved (goal object_current only): the target object has one / two placing
    records with a unique latest day and occurs in no other event;
  - giver (goal giver only): the target object occurs in exactly one event, a "gave" to the
    agent, and the giver has at least one record with a unique latest day;
  - every not-in-memory target (all kinds): absent from both worlds of the pair.
  Under the history conditions "latest placing / where it is now", "first placing / where
  it started", "the placing before the latest / before its last move / its previous spot /
  second-to-last place" and the person counterparts denote the same record. This is a
  property of THIS generator, not a claim about the wordings in general; the model-free
  audit checks exactly these per-kind conditions for every world of every split (a
  violation is a problem; the world is regenerated before any run).
- Outcomes: OK(intent, target) -> the operator answers; with no observation of the target
  the agent says it does not remember and explores. CLARIFY(reason) -> a clarification
  question, no movement; reasons no_referent (semantic) and low_confidence (model
  uncertainty) are reported separately. REFUSE -> "I cannot answer that from memory", no
  movement.
- Resolution rule of THIS round (Q1, decided): a question whose target is not fully given
  in the schema's terms - a pronoun without antecedent, a bare noun, a first name only - is
  answered with CLARIFY(no_referent), also when the store happens to contain one matching
  entity. This is a fixed rule of 3.6, not a claim that such questions are ambiguous in
  every context; resolution against memory is a later round.
- Unsupported (Q2, decided) means: outside the fixed operator scope of this round (why, how
  many, future, ownership, event-relative history, who did an action), not that the stored
  information could never answer it. Questions about the actor of an observed placing ("Who
  put the X at P?") are unsupported controls here (no actor operator yet); the 17 known
  extraction errors of 3.5b stay development cases and are not fixed by this round.
- Gold per outcome: OK questions (known target or a target absent from the world):
  intent and target; ambiguous questions: their intent (fixed per wording, table below) and
  target `none`, expected CLARIFY; unsupported questions: intent `unsupported`, no target,
  expected REFUSE.

## 2. Data, frequencies, text separation, pairing

Worlds: the round 3.5 generator (env35 kinds hidden, moved, giver, object, person; pairs
differing in one critical episode) with new seeds `r36-{split}-{index}`; splits dev, cal,
aud, ho, res with 10, 30, 5, 40, 40 pairs per kind (cal enlarged from 10 so that every
calibrated slot can reach >= 200 multi-value decisions after deduplication; the model-free
audit checks on cal, before any run: >= 300 distinct intent-calibratable texts (every
text with a gold intent) and >= 300 distinct target-calibratable texts - a defined gold
target (gold-OK and gold-ambiguous texts; gold-unsupported texts have none) and >= 2
admissible values including `none` under the GOLD intent; a number of single candidates
does not count).
Questions per world pair - the SAME question texts and gold specifications in worlds A
and B (the world difference changes the answer, not the question): the pair's goals (1 for
hidden/moved/giver, 3 for object/person) and three controls, each a minimal contrast to a
goal of the pair where the wording allows it (Astra's idea): a not-in-memory question (same
type as the first goal, a vocabulary entity absent from both worlds), an ambiguous question
about the first goal's target (object targets, incl. giver: the bare-noun family with the
target's noun, or the pronoun family; person targets: the first-name family with the
target's first name; the gold intent is fixed per wording, see the table) and an
unsupported question (family below, filled with the pair's entities). Constant wordings
can only be chosen in the first split of their group; in cal and aud the ambiguous family
of an object target is therefore always the bare-noun family.
Wordings: per supported type the template plus 3 development, 3 holdout and 3 reserve
paraphrases; ambiguous families pronoun / bare noun / first name and unsupported families
why / count / future / ownership / event-relative / who-did - EVERY family has one
wording in each group (no family appears first in the holdout). Assignment: the wording
group follows the split (dev, cal, aud: template + development; ho: holdout; res: reserve);
within the group the wording and the control family are chosen by a hash of the pair seed
and the question role (uniform; deterministic).
Text separation and units: parser metrics and calibration count DISTINCT question texts
per split (a text asked in both worlds and in several pairs counts once). Texts are
disjoint across splits, with one fixed exception: constant wordings without a placeholder
("Where is it now?", "Where did they put it first?", "Find it.", "How many people have you
seen?") occur only in the first split of their group (dev, ho, res respectively), never in
cal or aud, and count once. Task metrics count world pairs. Holdout and reserve wordings and
worlds are never used in development.

| type | development | holdout | reserve |
|---|---|---|---|
| object_current | Where is the {o} now? / Take me to the {o}. / I need the {o} - where is it? | Where can I find the {o} at the moment? / Go get the {o}. / Which place has the {o} right now? | Locate the {o}. / Where should I look for the {o}? / Head to wherever the {o} is. |
| object_first | Where was the {o} put the very first time? / Take me to the first place the {o} was put. / Where did the {o} start out? | Where was the {o} originally placed? / Go to the {o}'s first location. / Before all the moving, where was the {o} put? | Where did the {o} get placed first? / Show me where the {o} was put initially. / Which place did the {o} land in first? |
| object_previous | Where was the {o} before its last move? / Go to the place the {o} was in before it was last put somewhere. / Where had the {o} been just before it was last placed? | Where was the {o} prior to the latest placing? / Take me to the {o}'s previous spot. / Before the {o} was put where it is now, where was it? | Where did the {o} sit before its most recent placing? / Go to the {o}'s second-to-last place. / One move back, where was the {o}? |
| person_current | Where is {x} now? / Go to {x}. / Take me to where {x} was last seen. | Where can I meet {x}? / Head to {x}'s last known spot. / Where did you see {x} most recently? | Find where {x} is. / Where was {x} last spotted? / Go wherever {x} was last. |
| person_first | Where did you see {x} for the first time? / Go to the place where {x} first appeared. / Where was {x} when you first saw them? | Take me to where you originally saw {x}. / Where did you first come across {x}? / Go to {x}'s earliest known place. | Where did {x} first show up? / Head to the first place you saw {x}. / Your first sighting of {x} - where was it? |
| person_previous | Where did you see {x} before the last time? / Go to where {x} was seen before the latest sighting. / Where was {x} the time before you last saw them? | Take me to {x}'s previous location. / Before the most recent sighting, where was {x}? / Where did you see {x} one time before the last? | Where was {x} seen just before the last sighting? / Go back one sighting: where was {x}? / Where did {x} appear before their latest appearance? |
| giver | Who gave you the {o}? Go to them. / Go to the person you got the {o} from. / Find whoever handed you the {o}. | Take me to the one who gave you the {o}. / Where is the person the {o} came from? / Go find the giver of the {o}. | The {o} - who gave it to you? Find them. / Locate the person who passed you the {o}. / Where is whoever gave you the {o}? |
| ambiguous: pronoun | Where is it now? (object_current) | Where did they put it first? (object_first) | Find it. (object_current) |
| ambiguous: bare noun | Find the {noun}. (object_current) | Take me to the {noun}. (object_current) | Where was the {noun} placed first? (object_first) |
| ambiguous: first name | Go to {first}. (person_current) | Where is {first} now? (person_current) | Locate {first}. (person_current) |
| unsupported: why | Why did {x} put the {o} there? | Why was the {o} hidden? | For what reason did {x} leave the {o} behind? |
| unsupported: count | How many times was the {o} moved? | How often did you see {x}? | How many people have you seen? |
| unsupported: future | Where will the {o} be tomorrow? | Who will take the {o} next? | Where is {x} going to be next week? |
| unsupported: ownership | Who does the {o} belong to? | Who owns the {o}? | Whose {o} is it? |
| unsupported: event-relative | Where was {x} right before they gave you the {o}? | Where was the {o} just before you met {x}? | Where did you go after {x} handed you the {o}? |
| unsupported: who-did | Who put the {o} at {p}? | Which person hid the {o}? | Who was the last person to move the {o}? |

The ambiguous wordings with a pronoun keep their family's constant text; for the
ambiguous families the intent in brackets is the gold intent. Meaning check: Joe checked
the v1b table (four corrections by Claude's cross-check before review: "gave me" -> "gave
you" twice, the colour question replaced by an ownership question, "today" removed); the control wordings of
v2 were checked by Joe and cross-checked by Claude (2026-10-19, all 27 kept; hard
negatives on purpose: "before they gave you", "after X handed you", "How often did you see
X?", "Where was the {noun} placed first?").
Model-free audit (before any model run): roundtrip of every question to its gold
specification with its wording's exact inverse; disjoint texts as specified; the
generator conditions of section 1; candidate coverage of every gold target (must be 1.0 on
dev, cal, aud; checked on ho/res only after the freeze); the calibration counts above; the
rule baseline on dev, cal, aud.

## 3. Parser and the complete decision table

Slots: `intent` (labels: the seven types and `unsupported`, each with a one-line
description) and `target` (candidates: capitalised 1-3 token spans for persons; lower-case
1-3 token spans directly after a determiner, possessive "'s" removed, for objects; plus
`none`). The model (qwen2.5-1.5b, pinned) scores every candidate as the complete answer to
a fixed slot question (sum log-probability; prompt development on development data only,
worked examples allowed); each distinct question is scored once and its parse reused over
worlds and store conditions; decisions are derived model-free from the recorded scores.
Decision table (decoder q1), in this order:
1. intent decided with its rule (margin to the best different label, threshold tau_intent;
   tie or below threshold -> unknown): unknown -> CLARIFY(low_confidence).
2. intent = unsupported (accepted) -> REFUSE (no target).
3. intent = supported type t (accepted): admissible target values for t - for object types
   and giver canonical lower-case values of exactly two tokens, for person types canonical
   capitalised values of exactly two tokens - plus `none`.
   a. no admissible value besides `none` -> CLARIFY(no_referent);
   b. otherwise the target is decided among the admissible values and `none` with
      tau_target: unknown -> CLARIFY(low_confidence); `none` accepted -> CLARIFY
      (no_referent); a value v accepted -> OK(t, v).
Every question therefore has exactly one outcome. A clear unsupported question needs no
target, so a missing referent never turns it into CLARIFY (step 2 precedes step 3).
Calibration (same steps as the application, in this order): tau_intent over all distinct
cal texts (every text has >= 2 intent labels), correctness = decided label equals the gold
intent (ambiguous texts with their gold intent, unsupported texts with `unsupported`);
tau_target over the distinct cal texts that have a defined gold target (gold-OK and
gold-ambiguous; gold-unsupported texts are EXCLUDED) and whose intent is ACCEPTED as a
supported type with tau_intent, with >= 2 values among admissible + none, correctness =
decided value equals the gold target (`none` for ambiguous texts). A gold-unsupported text
whose intent is accepted as supported counts as an intent error (calibration of
tau_intent, outcome evaluation, error cause "wrong intent"), never in the target
calibration. Rule as in 3.5: the threshold with the highest acceptance subject to
precision >= 0.99 and >= 200 accepted values; the structural rule of 3.5 is not used.
Missing thresholds follow the decision table: no tau_intent -> every question
CLARIFY(low_confidence); no tau_target only -> an accepted unsupported intent is still
REFUSE, a supported intent without admissible target is still CLARIFY(no_referent), every
other supported question CLARIFY(low_confidence).
Calibration flow reported per slot (Astra's idea): distinct texts -> calibratable texts ->
texts left after the accepted intent -> texts accepted by the threshold.
Error causes are logged per question (Astra's idea): gold target not among the
candidates, wrong intent, wrong target, low confidence (intent / target), understood but
no observation.
Baseline (Astra's idea: a small grammar, not single key words). Information basis: the
template and the DEVELOPMENT wordings only - word lists contain only words that occur
there; it was not tuned on holdout or reserve wordings, and the holdout will show what it
misses (e.g. "originally", "prior", "whose" are not in it). Rules in this precedence:
(1) temporal clause - "before" / "after" followed by a clause with a verb: if the clause
is about the target's OWN latest record (a placing or seeing verb - put, placed, moved,
saw, seen - together with a recency word - last, latest, now) it marks `previous` ("before
it was last put somewhere", "before you last saw them", "before the {o} was put where it is
now"); any other such clause (an event of another kind or another person: "before they
gave you", "after X handed you") -> REFUSE (event-relative); (2) giver - gave / got ...
from / handed with the agent as receiver -> giver; (3) other unsupported markers - why;
how many; will / tomorrow; belong; "who" followed by an action verb -> REFUSE; (4) time -
first / start out -> first; before + last / latest -> previous; otherwise current; (5)
referent - a two-token lower-case span after a determiner -> object type, a two-token
capitalised name -> person type, otherwise CLARIFY. Controls
as in 3.5: uniform and random scores through the same decoder.

## 4. Store conditions

Phase A (this round's qualification): the CORRECT store (oracle records from the structured
truth) with the LM parser, against the reference agent with the gold specification.
Phase B (section 7): the d3-written store.

## 5. Criteria (fixed before any run; denominators explicit)

On the holdout, distinct question texts unless stated otherwise:
1. per supported type: exact specification (outcome OK with the gold intent AND the gold
   target) >= 0.95 among the gold-OK texts of that type; known targets and targets absent
   from the world reported separately (the absent-target questions also need the right
   intent - several operators give the same no_observation);
2. wrong accepted specifications <= 0.02, denominator: all texts whose outcome is OK
   (numerator: OK with intent or target different from gold, gold-ambiguous and
   gold-unsupported texts included);
3. false OK <= 0.02 among the gold-ambiguous texts, and <= 0.02 among the gold-unsupported
   texts (each class separately);
4. correct handling >= 0.90 per class: CLARIFY (any reason) among gold-ambiguous texts,
   REFUSE among gold-unsupported texts;
5. unnecessary CLARIFY or REFUSE <= 0.05 among the gold-OK texts;
6. tasks with the correct store, per kind x goal over world pairs: success >= reference
   (gold specification) - 0.02, pair success >= 0.95, confident-error rate <= 0.05.
   Deliberately strict: with 80 world decisions per cell two wrong decisions already give
   0.975 and FAIL against a perfect reference.
Reported besides the criteria (Astra's ideas): a macro mean over control families (a
constant pronoun text counts once after deduplication, other families with many texts);
for gold-ambiguous texts the handling (CLARIFY of any reason, criterion 4) separately from
the recognition of the ambiguity (CLARIFY(no_referent)) - CLARIFY(low_confidence) is the
right action but no evidence of recognised ambiguity.
Results: PARSER_QUALIFIED (YES / NO / UNDECIDABLE) and, separately,
PARSER_MILESTONE_ORIGINAL_RULES (the original 3.3/3.4 rules on the correct store with the
LM parser), with the baseline, the controls, the error causes, class diagnostics per type,
family and wording, and Wilson intervals per cell. These are observed pass criteria, not
statistical reliability guarantees. The holdout control families are the same families as
in development with new wordings (v2 removes the "new family" asymmetry of v1b).
Completeness contract and freeze binding (decoder version, code hashes of the import
closure, checked before the plan, in every job and by the collector), one holdout run, the
reserve only by the logged procedure of 3.5b.

## 6. Order

Meaning checks (done) -> implementation (questions, generator
extension, candidates, decoder q1, baseline, analysis, collector, tests incl. mutation
proof with the 3.5b protocol) -> model-free audit -> timing slice and development probes on
dev -> dev/cal run -> calibration -> review and freeze -> holdout coverage check -> one
holdout run -> results.

## 7. Combination (separate step after PARSER_QUALIFIED; Q4 decided: do it)

The same holdout worlds in four combinations (Astra's table): correct store + gold
specification (reference); d3 store + gold specification (extraction effects); correct
store + LM parser (parser effects); d3 store + LM parser (joint behaviour). The parser
configuration and the evaluation of the combination are fixed before the combination's
results are seen; the d3 encodings of the new worlds' notes are produced only after
PARSER_QUALIFIED. Label: "new worlds with known note wordings and question wordings not
used in development". The combination is not an independent second confirmation of the
parser. Questions touching the concentrated 3.5b error class (actors of observed
placings) are unsupported here and counted separately.

## Review of v3 and implementation notes

Astra APPROVE for design v3, the implementation and the development phase
(reviews/2026-10-19_r36v3_astra.txt); code, tests and audit results are reviewed before the
freeze. Her non-blocking ideas, adopted: the baseline's word-list provenance is checked
automatically (baseline36.provenance(), a test requires it empty; function words listed
separately); threshold boundaries tested (tie at threshold 0, margin just below, margin
equal - and calibration and application agree); absolute counts per control family beside
the family macro mean; the model-vs-baseline comparison paired per text (both right, only
model, only rules, both wrong) together with the time per question.

Implementation notes (2026-10-19):
1. Text separation inside the development group. Section 2 asked for texts disjoint across
   splits except constants; within dev / cal / aud this is impossible for the low-entropy
   control families ("Find the {noun}." has 12 possible texts, "Go to {first}." 16) - the
   regeneration loop did not terminate. Implemented instead: pairs are regenerated only for
   failed generator conditions; parser metrics and calibration count every distinct text
   ONCE, in the first split (order dev, cal, aud, ho, res) where it occurs
   (env36.split_questions); the parse of a repeated text is reused for the task metrics.
   Holdout and reserve texts cannot occur in the development group (their wordings differ;
   the audit checks that no text is shared between groups). Counts on cal after this rule:
   490 distinct intent-calibratable and 348 target-calibratable texts (>= 300 each).
2. Round 3.6 worlds use the 3.5 generator with the seed prefix r36 (env35.generate_pair35
   got a backward-compatible prefix argument; all five 3.5 splits are byte-identical before
   and after, checked by hashing). The 3.5b freeze therefore no longer matches the current
   env35.py hash; the 3.5 test now checks that a freeze made from the current code matches
   and the old one differs only in env35.py. config/round35.json is disabled (done).
3. Disclosure: during the implementation the model-free candidate coverage (1.0) and the
   rule baseline were also computed on the holdout and reserve question texts, which the
   design reserves for after the freeze. This gives no information about the model's
   performance; the baseline (episodic_lab/baseline36.py) is not changed after that and its
   holdout numbers will be reported as they are (it was built from development wordings
   only; on development texts it is right on all 770 texts).
4. Small denominators on the holdout: about 28 distinct gold-ambiguous texts (1 pronoun, up
   to 12 bare-noun, up to 16 first-name texts); "false OK <= 0.02" then allows no false OK
   at all. This follows from the approved criteria and is reported with absolute counts.
5. Prompt q2 = q1 plus eight worked examples (vocabulary outside the worlds) for the first
   development probe beside q1.

## Development log

1. Model-free audit (dev group, docs/ROUND_3_6_audit_dev.json): no problems; coverage 1.0 on
   dev, cal, aud; calibration counts 490 / 348; rule baseline 208/208, 490/490, 72/72.
2. Probe 1 (GitHub 39310171530, 69 development texts, best value): q1 46/69 right, q2
   (worked examples) 42/69; about 11 s per question. Errors: unsupported questions almost
   never recognised (q1 0/12 refused, 11 accepted as OK) - the intent was scored as long
   label strings ("object_current", "unsupported") whose lengths differ under the sum
   score; "Where is X now?" / "Go to X." read as object questions; giver questions answered
   with target "none" (the target question asked what the request is "about"). Ambiguous
   questions were handled 5/5 by both.
3. Development change: prompts q3 / q4 - the intent as a multiple choice with equally short
   letter answers A-H (canonical value = the label), the target question asks for the
   complete object or full name WRITTEN in the request; q3 with the worked examples, q4
   without. Probe 2 compares both.
4. Probe 2 (GitHub 39314734322): q3 40/69, q4 48/69 right. Letters alone do not help.
   Offline look at the recorded intent scores (all four prompts): the supported types other
   than person_current rank the gold label first almost always; the gold label of
   unsupported questions ranks 4-6 (its label score is far lower for every text - a label
   prior), person_current ranks 2-4. Subtracting each label's mean score (a crude prior
   correction) raises q1 from 45 to 60 of 69 right intents. q3's target examples answered
   "none" three times in eight and biased the target towards none.
5. Development change: prompts q5 / q6 = q4 plus three RECORDED development slots for an
   offline comparison with a factorised decoder (answerable yes/no, kind object / person /
   giver, time latest / first / previous) and the content-free score of every label slot
   ("(no request)") for an offline prior correction; q5 with balanced per-slot worked
   examples (target "none" once), q6 without. The decision table q1 and its sum score stay
   the approved decoder; a factorised decoder or a prior-corrected score would be a design
   change and goes to Astra before any use.
6. Probe 3 (GitHub 39319562259): q5 49/69, q6 48/69 right. Offline comparison on the same
   encodings (q1 decoder with sum or prior-corrected intent; factorised decoder with sum or
   prior-corrected factors): no variant above 49/69; unsupported questions accepted as OK in
   7-11 of 12 by every variant that keeps the supported types (the factorised q6 decoder
   refuses 9/12 but then fails most supported questions). Conclusion after six prompt
   variants and four decoders: the limit is the model's ability to separate unsupported
   questions, not the prompt; the criterion "false OK <= 0.02 among unsupported" is out of
   reach with qwen2.5-1.5b. No further prompt iteration on this model.
7. Next development step (realistic within the constraints - free runner, float32 memory,
   Apache-2.0): one probe with Qwen3-1.7B (the largest Apache-2.0 model that fits in float32;
   Qwen3 support exists in models.py), prompts q4 and q5. A model change is a decision for
   Astra before any use beyond development (as in round 3.5).
8. Probe 4 (GitHub 39323805995, Qwen3-1.7B pinned at 70d244cc, Apache-2.0, float32): q4
   18/69 (without examples Qwen3 refuses or clarifies almost everything); q5 62/69 right -
   every unsupported question refused (12/12, no false OK), every ambiguous one clarified
   (5/5, all as no_referent), no wrong accepted specification (0/45); the 7 errors are all
   unnecessary refusals or clarifications of terse imperatives ("Find X.", "Go to X.",
   "Take me to the X.", "I need the X - where is it?"). Cost: q5 97 s per question against
   6.5 s for q4. Cause: the prefix cache fell back to the uncached path on every call -
   Qwen3's chat template formats the last assistant turn of messages[:-1] with think tags,
   so that rendering is not a token prefix of the full prompt.
9. Development changes: (a) models.py - the reusable head is now the longest common token
   prefix of the full prompt and the same conversation with an empty last turn (always an
   exact prefix of the prompt, so the scores are unchanged; every probe job checks prefixed
   against uncached scores); (b) prompt q7 = q5's worked examples plus two imperatives
   that are not development wordings ("Bring me to Tom Reed.", "Show me the old key."), only
   the two slots of the decision table.
10. Probe 5 (GitHub 39340224417, Qwen3-1.7B + q7): 67 of 69 development texts right; every
   unsupported question refused (12/12), every ambiguous one clarified as no_referent (5/5),
   no wrong accepted specification (0/50), 2 unnecessary clarifications ("Go to X." read as
   giver); 10.8 s per question (was 97 s); the cache check passed (largest difference
   1.3e-4, identical choices). Next: development and calibration run (dev and cal, 4 chunks
   each) with Qwen3-1.7B + q7 and the approved decision table q1.
