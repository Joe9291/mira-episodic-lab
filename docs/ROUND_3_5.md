# Round 3.5 - LM-assisted structured extraction for the action environment (design v2)

Uncertainty removed: can a small language model, used only as an extraction interface
(no reasoning; the operators keep that), write the episodic store of the round 3.3/3.4
environment well enough that the memory tasks still pass, on wordings and worlds it was
never developed on? Name of the system (Astra): "LM-assisted structured extraction with
given candidates" - the model chooses values for a fixed schema from candidates; the
claim is about this supported extraction system, not about free memory writing.

Order (Astra, `reviews/2026-10-18_results_decision_astra.txt`): encoder errors broken
down, uncertainty semantics of the history operators closed (both done, section 0), then
this encoder pilot in the TARGET environment with the goal parser fixed; the language
goal/question parser is a later, separate round; then both combined; then
context-dependent historical queries. v2 answers Astra's review of v1
(`reviews/2026-10-18_r35v1_astra.txt`).

## 0. Done before this design (development data, no new run)

Encoder error breakdown of round 3.2 run 2 (`bench/m3/encoder_errors.py`, 1,200 records,
development data). Corrected after Astra's v1 review: a slot the encoder declared invalid
counts as "unknown", never as correct (also when the truth is "no partner"); the partner
normalisation counts only where it was actually applied.

| slot | correct | unknown (declared) | wrong |
|---|---|---|---|
| day | 954 | 246 | 0 |
| actor | 1188 | 8 | 4 |
| partner | 1005 | 58 | 137 |
| action | 832 | 180 | 188 |
| object | 474 | 726 | 0 |
| place | 1191 | 5 | 4 |

Reasons (from the raw replies, also for declared unknowns): object without its
adjective 567 (the noun alone was unique within the world in all 567 - known only after
all episodes), object or action differing only in letter case 147 / 170, action in the
base form 177, weekday instead of the event day 246 (strongly frame-dependent: "N was at
N on day D and ..." 65/211, "Day D: at N, ..." 91/199, "On day D, ..." 20/186, "Earlier,
on day D, ..." 0/84). Partner normalisation applied 837 times (= the collector's count):
it helped 717 times (711 stored as a correct "no partner"; in 6 further cases the partner
was also declared unknown, so they do not count as correct) and hid a role error 120
times. Records with every
slot correct, per world: as stored min 0.025 / median 0.212 / max 0.350; after lossless
normalisation only (case, base form, helpful partner normalisation; a declared unknown
partner never counts) min 0.138 / median 0.362 / max 0.600. Diagnosis: the free slot
encoder loses identity, time and role information; normalisation is not enough.

History operators with unknown fields (`episodic_lab/history_agent.py`): a record that
could be about the target because a deciding field is unknown blocks an answer whenever
it could take the asked position or tie with it; ties count only at the positions a goal
needs (same rule in the independent reference); soundness test against all completions
of up to three unknown fields. Round 3.4 step 1 rows unchanged (re-run identical).

## 1. Data splits, worlds and wordings

Splits by whole pairs (separate series, so identical notes cannot fall into two splits;
checked: the sets of episode texts of any two splits must be disjoint):

| split | use | pairs per kind |
|---|---|---|
| development (`*-dev35`) | prompts, normalisation, model choice, candidate generator, wordings | 10 |
| calibration (`*-cal35`) | the uncertainty thresholds only | 10 |
| audit (`*-aud35`) | model-free checks of candidates and wordings before freezing | 5 |
| holdout (`*-ho35`) | the single qualification run | 40 |

Kinds: the round 3.3 kinds hidden, moved, giver and the round 3.4 kinds object, person.
New in every 3.5 world (Astra's idea): a distractor object with the SAME noun as the
target and another adjective ("tiny umbrella" / "striped umbrella"), placed in
distractor episodes, so that dropping the adjective is a real binding error.

Wordings: per event type (observed placing, own placing, gave, seen, went) the current
template plus 3 development paraphrases and 3 holdout paraphrases, written before any
model run (`episodic_lab/wordings35.py`), including frames that were hard in 3.2 (day in
the middle or at the end, the second person in different positions, the object before
the verb). Checks, all model-free and done on development + audit before freezing:
- meaning preservation: every paraphrase is generated from the structured event, and a
  per-paraphrase exact inverse parser must return exactly that event (roles, action,
  object, place, day) for every generated sentence;
- pair invariance: the wording of an episode is chosen by a hash of (pair seed, episode
  position), not of the world, so the two worlds of a pair differ only in the critical
  episode's place (checked like the 3.3/3.4 pair design);
- usage: the number of episodes per wording frame and split is reported; every holdout
  frame must occur at least 30 times in the holdout.

## 2. Encoder: candidates, canonical values, scores, uncertainty

Slots: actor, partner, action, object, place, event_day.

Canonicalisation contract (fixed before any model run):
- tokens: maximal runs of letters, digits and apostrophes; punctuation is not a token
  and a span never crosses punctuation; candidate spans are 1-3 consecutive tokens;
- canonical values: names (person, place) keep the text's spelling of each word; objects
  are lower-cased with a leading article (the, a, an) removed; numbers become integers;
  "I", "me", "you", "You" become "You" (the schema's agent); the candidate "none" means
  the optional field (partner, object) is absent in this episode;
- action: a fixed label set of the schema (hid, left, put, gave, was, went), each with one
  short description; the model scores the labels;
- every surface candidate is mapped to its canonical value first; variants of one value
  are merged and the value's score is the MAXIMUM of its variants' scores;
- score: total log-probability of the complete candidate answer including the
  end-of-turn token after a fixed slot prompt (the S1 procedure,
  `models.score_candidates`), with the prompt prefix computed once per slot (key/value
  cache reused);
- margin: best canonical value's score minus the score of the best DIFFERENT canonical
  value.

Uncertainty ("unknown", different from "none"): a slot whose margin is below its
threshold tau_slot is stored as None and declared unknown; a missing value of an
always-present slot is also unknown. Threshold rule (Astra): on the calibration split,
per slot, among the observed margins (and 0), choose the tau with the HIGHEST acceptance
rate subject to precision of the accepted values >= 0.99 and at least 200 accepted
values; an empty accepted set never qualifies; ties go to the smaller tau; if no tau
qualifies, the slot is always stored as unknown (and the qualification will show it).
Precision and acceptance are reported per slot on calibration and holdout, and the
per-slot rule is compared on development with one common tau (reported). The 0.99 is an
observed calibration performance, not a guarantee for new wordings.

Each distinct sentence is encoded once per model; paired worlds and memory interventions
reuse the encodings. Every recorded encoding keeps the scores of all canonical values,
so the collector re-derives choice, margin and unknown flag exactly.

## 3. Controls (model-free) and the reference

- Candidate coverage: share of slots whose true canonical value is among the candidates;
  must be 1.0 on development and audit before freezing. The holdout is only CHECKED after
  freezing; if its coverage is below 1.0, that holdout becomes audit material, the fix is
  logged, and a new holdout series is generated - no fix is made against the final
  holdout.
- Extraction baselines without a model: (a) position rules (first name-like span = actor,
  last name-like span = place, first number = day, word after "the" = object), (b) a
  word-list rule for the action; they show whether the LM adds anything beyond surface
  regularities (role swaps, similar objects and varied frames are in the wordings).
- Reference system: the SAME operators and decision rules on a store written from the
  generator's structured truth (oracle encoding), so that a template encoder that cannot
  read the new wordings never lowers the bar.
- Cache baseline for round 3.4 (Astra): first, previous and latest place per entity, same
  experiences; expected to solve the three fixed history goals; reported so that the 3.4
  claim is not over-read.

## 4. Phases and the qualification

P1 timing: a fixed development slice (2 pairs per kind, both models, including the
longest sentences and the highest candidate counts), measuring model loading, encoding,
decisions and the collector's replay; the full development run only if every job fits
into the 6-hour limit with the world matrix.

P1 development (GitHub; qwen2.5-0.5b and qwen3-0.6b without thinking): record quality per
slot and per wording frame; prompts, normalisation, candidate generator and model chosen
on development only; every iteration logged. Then the thresholds on calibration. The
holdout is opened only if development and calibration already meet the criteria below
(else the round ends with a reported failure, no holdout run).

P2 holdout qualification (GitHub, once, frozen configuration). Encoder qualification and
success loss are measured on INTACT stores only:
1. records: complete records with every slot correct >= 0.95; a declared unknown is never
   correct (an unknown partner is not a correct "none"); per slot correct / unknown /
   wrong reported;
2. memory tasks with the fixed goal parser and the round 3.3/3.4 decision rules, per world
   kind and goal (3.3 hidden, moved, giver; 3.4 object and person x current, first,
   previous): success = mean over pairs of the mean over the pair's two worlds; LM system
   >= reference - 0.02 in EVERY kind x goal cell; pair success >= 0.95 in every cell
   (Astra's idea, adopted as a release criterion so that a pass also means the historical
   milestone with the LM system);
3. confident-error rate = wrong decisions taken from memory / all decisions taken from
   memory, per kind x goal, <= 0.05, with the coverage (decisions taken from memory / all)
   reported next to it;
4. results per world with their spread; pairs/worlds are the units. These are technical
   acceptance rules, not a statistical non-inferiority claim.
Memory interventions on the LM-written stores are evaluated separately against the
pre-registered intervention reference (action as predicted on informative cases) and
reported as causal memory use, never mixed into the success or error rates above.

Completeness contract as in rounds 3.2-3.4: schema, provenance (request hash, the run's
code commit), every planned report present and valid, the collector re-derives every
encoder decision from the recorded scores and re-runs operators and decisions; an
incomplete run gives no qualification (decision UNDECIDABLE).

Pass -> the LM extraction may write the store of later rounds for these episode forms.
Then round 3.6: the goal/question parser by the same method, including ambiguous and
unsupported questions; then both combined; then context-dependent historical queries
(pairs with identical current, first and previous values but a different relevant
intermediate event, e.g. "where was X immediately before event Y?"), which the cache
baseline cannot answer.
