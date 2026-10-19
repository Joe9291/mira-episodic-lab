# Round 3.6 - LM-assisted goal/question parsing (design v2)

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
- Binding of the wordings to this meaning: in the generator every target object has exactly
  three placing records, never two consecutive ones at the same place, and occurs in no
  other event; every target person of the history kinds has exactly three records (all
  "seen"). Under these conditions "latest placing / where it is now", "first placing /
  where it started", "the placing before the latest / before its last move / its previous
  spot / second-to-last place" and the person counterparts denote the same record. This is
  a property of THIS generator, not a claim about the wordings in general; the model-free
  audit checks the three conditions for every world of every split (a violation is a
  problem, the world is regenerated before any run).
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
calibrated slot reaches >= 200 multi-value decisions after deduplication; the model-free
audit checks >= 300 multi-value target candidates and >= 300 distinct intent texts on cal
before any run).
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
the v1b table (four corrections before review, see the log); the new control wordings of
v2 (ownership, who-did, the reserve and development family fill-ins) go to Joe before the
implementation.
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
cal texts with >= 2 intent labels (all of them), correctness = decided label equals the
gold intent (ambiguous texts included with their gold intent); tau_target over the distinct
cal texts whose intent is ACCEPTED as a supported type with tau_intent, with >= 2 values
among admissible + none, correctness = decided value equals the gold target (`none` for
ambiguous texts). Rule as in 3.5: the threshold with the highest acceptance subject to
precision >= 0.99 and >= 200 accepted values; none qualifies -> the slot is always
unknown (every question CLARIFY). The structural rule of 3.5 is not used.
Error causes are logged per question (Astra's idea): gold target not among the
candidates, wrong intent, wrong target, low confidence (intent / target), understood but
no observation.
Baseline (Astra's idea: a small grammar, not single key words), built from the template
and development wordings only, rules in this precedence: (1) event-relative - a temporal
preposition (before / after) followed by a clause with its own subject and event verb
("before they gave you", "after X handed you") -> REFUSE; (2) giver - (gave / handed /
passed / got ... from / came from) with the agent as receiver, or "giver" -> giver; (3)
other unsupported markers - why / for what reason; how many / how often; will / going to /
tomorrow / next; belong / own / whose; "who" or "which person" followed by an action verb
-> REFUSE; (4) time - first / originally / initially / earliest / start out / land in
first -> first; before + (last / latest / most recent) / previous / prior / second-to-last
/ one ... back -> previous; otherwise current; (5) referent - a two-token lower-case span
after a determiner -> object type, a two-token capitalised name -> person type, otherwise
CLARIFY. Controls
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

Joe's meaning check of the new control wordings -> implementation (questions, generator
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
