# Round 3.5 - LM-assisted structured extraction for the action environment (design v1)

Uncertainty removed: can a small language model, used only as an extraction interface
(no reasoning; the operators keep that), write the episodic store of the round 3.3/3.4
environment well enough that the memory tasks still pass, on wordings it was never
developed on? Order and scope follow Astra's review of the results of 3.2 and 3.4 step 1
(`reviews/2026-10-18_results_decision_astra.txt`): encoder errors broken down first,
uncertainty semantics of the history operators closed, then an encoder pilot in the
TARGET environment with the question/goal parser fixed; the language parser is a later,
separate round; then both combined.

Name of the system (Astra): "LM-assisted structured extraction with given candidates" -
the model chooses values for a fixed schema from candidates; this is not "the LM writes
the memory" in a free sense.

## 0. Done before this design (development data, no new run)

**Encoder error breakdown of round 3.2 run 2** (`bench/m3/encoder_errors.py`, all 1,200
encoded records; development data, already seen):

| slot | correct | case only | base form | partner normalisation helped | noun without adjective | weekday | partner normalisation hid a role error | other |
|---|---|---|---|---|---|---|---|---|
| day | 954 | 0 | 0 | 0 | 0 | 246 | 0 | 0 |
| actor | 1188 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| partner | 294 | 0 | 0 | 754 | 0 | 0 | 120 | 32 |
| action | 832 | 170 | 177 | 0 | 0 | 0 | 0 | 21 |
| object | 474 | 147 | 0 | 0 | 567 | 0 | 0 | 12 |
| place | 1191 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |

Lossless normalisation (case, base form) would repair 494 slot values; it would still
leave most records wrong: records with every slot right after lossless normalisation,
per world, min 0.15 / median 0.375 / max 0.625. The remaining errors carry or lose
information: the object without its adjective (567; the noun alone was unique within the
world's episodes in all 567, but that uniqueness is only known after all episodes),
weekdays instead of the event day (246, concentrated in frames where the day stands in
the middle of the sentence: "N was at N on day D and ..." 65/211, "Day D: at N, ..."
91/199, "On day D, ..." 20/186, "Earlier, on day D, ..." 0/84), and the partner: the
declared normalisation (a repeated first person read as "no second person") helped 754
times and hid a role error 120 times. So Astra's objection holds: the failures are not
"mostly format"; the free-generation slot encoder loses identity, time and role
information.

**History operators with unknown fields** (`episodic_lab/history_agent.py`): a record
that could be about the target because a deciding field is unknown (unknown object or
action for an object; unknown actor or partner for a person) blocks a history answer
whenever it could take the asked position or tie with it (undated; not earlier than the
latest; not later than the first; not earlier than the one before the latest); without
any exact record but with possible ones the evidence is insufficient. Ties count only at
the positions a goal needs (same rule in the independent reference). Soundness test
against brute force: every ok answer equals the answer under EVERY completion of up to
three unknown fields (600 random stores in the suite; outside the suite 5 x 3,000 stores
with 0 violations, where the step-1 operators had 559-648 per 3,000). Round 3.4 step 1
rows are unchanged by this (no unknown fields in template records; re-run identical).

## 1. Data: worlds and wordings

- Worlds: the round 3.3 kinds (hidden, moved, giver) and the round 3.4 kinds (object,
  person history). Development series `env-dev35` / `hist-dev35` (10 pairs per kind);
  held-out series `env-ho35` / `hist-ho35` (40 pairs per kind), generated now, not looked
  at by any model before the qualification run.
- Wordings: every event type (observed placing, own placing, gave, seen, went) gets the
  current template plus 3 development paraphrases and 3 held-out paraphrases, written now
  and fixed in `episodic_lab/wordings35.py` before any model run. The held-out set
  includes frames that were hard in 3.2 (the day in the middle or at the end of the
  sentence, a second person in different positions, the object before the verb). Each
  episode's wording is drawn by a seeded hash, separately for development and held-out.

## 2. Encoder (fixed schema, given candidates)

- Slots: actor, partner, action, object, place, event_day.
- Candidates, generated generically from the sentence (no template knowledge): every
  contiguous span of 1-3 words without punctuation, every number, and "You" for the
  agent (the schema's name for "you"/"I"). Optional slots (partner, object) also get the
  candidate "none" = the field is absent in this episode. The action is a fixed label set
  of the schema (hid, left, put, gave, was, went) with one short description each.
- Score: total log-probability of the complete candidate answer including the end-of-turn
  token after a fixed slot prompt (the S1 procedure, `models.score_candidates`), computed
  with one shared prompt prefix per slot (key/value cache reused across candidates).
- Uncertainty ("unknown", different from "none"): if the margin between the best and the
  second-best score is below a threshold tau, the slot is stored as None and declared
  unknown. tau is chosen on the development data (the largest tau whose resulting
  confident slot values are at least 0.99 correct on development, per model) and then
  frozen. A missing value of an always-present slot is also unknown.
- Each distinct sentence is encoded once per model (paired worlds share all but one
  sentence; interventions reuse the encodings, Astra's idea).

## 3. Controls and upper bounds (model-free, before any model run)

- Candidate coverage: share of slots whose true value is among the candidates; must be
  1.0 on development AND held-out wordings, checked and reported before the run (else the
  candidate generator is fixed first).
- Extraction baselines without a model: (a) position rules (first name-like span = actor,
  last name-like span = place, first number = day, ...), (b) a word-list rule for the
  action. They show whether the LM adds anything beyond surface regularities; the
  held-out wordings include role swaps and similar object names for this.
- Cache baseline for round 3.4 (Astra): a memory with only the first, the previous and
  the latest place per entity, same experiences; expected to solve the three fixed
  history goals - reported so that the 3.4 claim is not over-read.

## 4. Phases

P1 development (GitHub, models qwen2.5-0.5b and qwen3-0.6b without thinking): record
quality per slot and per wording frame, tau, cost per record. First a timing run on a
fixed development slice (2 pairs per kind, both models) with an extrapolated cost; the
full development run only if every job fits into the 6-hour limit with the world matrix.
Prompts, normalisation, tau and the model are chosen on development data only; every
development iteration is logged.

P2 held-out qualification (GitHub, once, frozen configuration): on the held-out worlds
and wordings, (a) record quality: complete records all correct (all six slots) >= 0.95;
per slot accuracy; none/unknown/wrong reported separately; (b) memory tasks with the
fixed goal parser and the round 3.3/3.4 decision rules: per goal type (3.3 object, 3.3
giver, 3.4 current, first, previous) success at most 0.02 below the template encoder on
the same worlds; historical pair success reported separately; confident-error rate
(decisions taken from memory that are wrong) <= 0.05; results per world with their
spread (pairs/worlds are the units). These are technical acceptance rules, not a
statistical non-inferiority claim.

Pass -> the LM extraction may write the store of later rounds for these episode forms.
Then round 3.6: the goal/question parser by the same method, with ambiguous and
unsupported questions; then both combined; then context-dependent historical queries
("where was X immediately before event Y?") with pairs whose current, first and previous
values are identical, which the cache baseline cannot answer.
