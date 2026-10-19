# Round 3.5 - LM-assisted structured extraction for the action environment (design v3)

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
(`reviews/2026-10-18_r35v1_astra.txt`), v3 her review of v2
(`reviews/2026-10-18_r35v2_astra.txt`).

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
717 normalisation cases with a truly absent partner (711 of them correct, 6 still declared
unknown and therefore not correct) and 120 cases in which it hid a role error. Records with every
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
template plus 3 development paraphrases, 3 holdout paraphrases and 3 reserve paraphrases,
all written before any model run (`episodic_lab/wordings35.py`), including frames that
were hard in 3.2 (day in the middle or at the end, the second person in different
positions, the object before the verb, passive roles such as "B was given the box by
A"). Use of the wording sets (Astra): development, calibration and audit worlds use
ONLY the template and the development paraphrases; the holdout and reserve paraphrases
are never used for the choice of model, prompts, normalisation, candidate generator or
thresholds. Checks, all model-free:
- meaning preservation: every paraphrase is generated from the structured event, and a
  per-paraphrase exact inverse parser must return exactly that event (roles, action,
  object, place, day) for every generated sentence;
- pair invariance: the wording of an episode is chosen by a hash of (pair seed, episode
  position), not of the world, so the two worlds of a pair differ only in the critical
  episode's place (checked like the 3.3/3.4 pair design);
- independent meaning check (Astra): a generator and its inverse parser can share a wrong
  role assumption, so one rendered example of EVERY template (development, holdout and
  reserve) is checked by a person (Joe) against the structured event (roles, action,
  object, place, day) before freezing;
- usage: per wording frame and split, both the number of episode occurrences and the
  number of distinct texts (= model evaluations, since encodings are shared) are
  reported; every holdout frame must have at least 30 distinct texts in the holdout.

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

Edge cases (fixed): equal scores of the two best canonical values give margin 0, which
is always "unknown"; a slot with only one canonical candidate is accepted (there is no
alternative) and counted separately; a rate with an empty denominator (e.g. no decision
taken from memory) is undefined and never passes a criterion.

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
reuse the encodings. Every recorded encoding keeps the score of every scored surface
candidate and its canonical value (so the max-merging is auditable), and the collector
re-derives choice, margin and unknown flag exactly.

## 3. Controls (model-free) and the reference

- Candidate coverage: share of slots whose true canonical value is among the candidates;
  must be 1.0 on development and audit (development wordings) before freezing. The
  holdout is only CHECKED after freezing. If its coverage is below 1.0, the holdout
  worlds AND the holdout paraphrases count as consumed (audit material); after the logged
  fix, the qualification uses new holdout worlds with the reserve paraphrases. If the
  reserve paraphrases are consumed as well, the result may only be claimed as transfer
  to new worlds with already known wordings, and is labelled so.
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
   >= reference - 0.02 in EVERY kind x goal cell; pair success >= 0.95 in every cell;
3. confident-error rate = wrong decisions taken from memory / all decisions taken from
   memory, per kind x goal, <= 0.05, with the coverage (decisions taken from memory / all)
   reported next to it;
4. results per world with their spread; pairs/worlds are the units. These are technical
   acceptance rules, not a statistical non-inferiority claim.
Memory interventions on the LM-written stores are evaluated separately against the
pre-registered intervention reference (action as predicted on informative cases) and
reported as causal memory use, never mixed into the success or error rates above.

Results: ENCODER_QUALIFIED (YES / NO / UNDECIDABLE) = the technical qualification by the
3.5 criteria above; it does NOT imply the milestone of rounds 3.3/3.4, whose rules are
stricter (intact success 1.0, pair success 1.0, the intervention criteria). Separately,
the collector applies the ORIGINAL 3.3 and 3.4 milestone rules unchanged to the LM system
on the holdout worlds and reports MILESTONE_ORIGINAL_RULES (PASS / FAIL); only that result
may be described as the milestone with the LM system.

Completeness contract as in rounds 3.2-3.4: schema, provenance (request hash, the run's
code commit), every planned report present and valid, the collector re-derives every
encoder decision from the recorded scores and re-runs operators and decisions; an
incomplete run gives no qualification (decision UNDECIDABLE).

ENCODER_QUALIFIED YES -> the LM extraction may write the store of later rounds for these
episode forms (with the wording claim the holdout supports, see section 3).
Then round 3.6: the goal/question parser by the same method, including ambiguous and
unsupported questions; then both combined; then context-dependent historical queries
(pairs with identical current, first and previous values but a different relevant
intermediate event, e.g. "where was X immediately before event Y?"), which the cache
baseline cannot answer.

## Review of v3 and adopted ideas

Astra APPROVE for v3 (`reviews/2026-10-18_r35v3_astra.txt`; the approval covers the
design, not the implementation or the model's performance). Her non-blocking ideas,
adopted: (1) slots with a single canonical candidate are reported as structurally fixed,
and accuracy is reported separately on the slots where the model had to choose between at
least two canonical values; precedence rule: a slot without a qualifying tau stays
unknown, also for single-candidate cases; (2) after a coverage repair the whole affected
configuration (development check, calibration, freeze) is redone before the reserve
wordings are used; (3) the prefix cache is checked on a small development slice: scores
and decisions with and without the cache must agree (tolerance 1e-4 in log-probability,
identical choices); (4) errors are also broken down by role and absence: giver vs
receiver, "You" vs observed persons, truly absent vs present partner/object.

## Implementation notes (before the timing run)

- Code: `episodic_lab/wordings35.py`, `env35.py`, `cands35.py`, `encoder35.py`,
  `analysis35.py`; `bench/m3/audit35.py`, `run_round35.py`, `collect_round35.py`;
  workflow `round35.yml`, request `config/round35.json`; tests `tests/test_round35.py`.
- Cache check tolerance: 1e-3 in log-probability (not 1e-4 as first written above): the
  cached and uncached forward passes compute the same values along different float32
  paths; the choices must be identical in every slot. Fixed before the timing run.
- Disjoint texts: dev, cal and aud share the development wordings, so a few short
  sentences coincided (5, 2, 2); a pair that would share a text with an earlier split is
  regenerated with the next attempt number (`env35.split_pairs`), now 0 shared texts.
  Holdout and reserve use other wordings and cannot share texts with the development
  splits.
- Round 3.3 goals on LM-written stores use unknown-aware operators (`analysis35.decide_env`:
  the object's latest placing via the history operator; the giver as the unique possible
  "gave" record, then `memory.latest`); on template stores they decide exactly like the
  round 3.3 agent (tested).
- The round 3.4 current-state baseline in the original-rules check reads the true events
  (perfect reading), because the template parser cannot read the new wordings.
- Decisions are taken in-process from stores rebuilt from the recorded encodings; the
  memory boundary is the store content (the process isolation was shown in 3.3/3.4).
- Model-free audit of dev, cal, aud (`audit35.py`): roundtrip, pair invariance, disjoint
  texts and coverage all pass (coverage 1.0 in every slot). Baselines without a model
  (rules built from the development wordings): complete records 0.73 / 0.71 / 0.69
  (dev / cal / aud; actor 0.78, place 0.71-0.73, other slots 1.0). Holdout coverage is
  checked only after the freeze.
- Independent meaning check: Joe checked all 50 sentences of the sheet
  (`reviews/2026-10-18_r35_meaning_check_sheet.md`) on 2026-10-18: "Passt" (all match).
  Claude's own cross-check, independent of the inverse parsers: every template rendered
  with all three placing verbs contains the person, the object, the place and the day
  exactly once and no other number; every own placing and "went" sentence names the agent
  (you / I / your), every "gave" sentence the receiver (you / me); 0 problems; and a manual
  reading of all 50 sentences for roles (giver/receiver, passives) and time reference.
  Wordings FROZEN: `episodic_lab/wordings35.py` SHA-256
  d0efe7670f275e9d41fe2ca367d52b63286df4648283618cedb0219ae6a6756a.

## Development log

1. Timing run (GitHub 39142347658, commit 0a5b90e; prompts p1, candidates c1): cache
   check OK for both models (max |cached - uncached| 1.6e-4 / 2.0e-4, identical choices);
   seconds per text 17.5 (qwen2.5-0.5b) and 29.1 (qwen3-0.6b), model loading 8 / 12 s;
   extrapolated: dev about 3.6 / 6.1 h, holdout about 14.5 / 24 h per model (chunks
   needed). Development look at the 168 timed texts (best value, tau 0): complete records
   0.089 / 0.101. Main errors: the actor of "seen" events and of placings answered as
   "You" or as an object or a verb (the schema's actor of "you spotted X" is X); "none"
   almost never chosen for absent objects (names and places chosen instead); the receiver
   "You" of gave events missed; the action "was" rarely chosen; the object without its
   adjective. Changes for the next development iteration (no holdout or reserve wording
   involved): typed candidates c2 (names = spans of capitalised tokens, objects = spans of
   lower-case tokens) and prompts p2 (each question names the schema field and its role:
   the reported person, the receiver, a thing not a person or place, "was" = a person seen
   or met). Coverage stays 1.0 on dev, cal and aud. Next: a probe phase on a stratified
   development slice (4 distinct texts per development frame, 80 texts) for quick
   iterations, qwen2.5-0.5b only (the faster model; qwen3-0.6b was not better on the
   timed texts); both models again in the full development run.
2. Probe 1 (GitHub 39151394097; p2, c2; qwen2.5-0.5b; 80 stratified development texts):
   complete records 0.000. The model answers "You" for nearly every actor and receiver
   (actor of observed persons 0/32, givers 0/16; receiver "none" 0/64) and the object
   without its adjective. Diagnosis: the approved score (total log-probability of the
   answer) prefers short, primed answers ("You", one-word nouns): a length and prior
   bias, not missing information. Next probe records, for the same prompts and
   candidates, two additional development measurements per candidate: the score without
   the note ("(no note)", cached per slot and surface) and the answer's token count, so
   that the approved sum score can be compared with a per-token mean and a calibrated
   (pointwise mutual information) score on the same encodings. A switch away from the
   approved score definition would be a design change and goes to Astra first.
3. Probe 2 (GitHub 39152703744; p2, c2; qwen2.5-0.5b; same 80 texts, null scores and
   token counts recorded): complete records 0.000 under every scoring mode. Sum and
   per-token mean behave alike ("You" for actors and receivers, nouns without adjective);
   the calibrated score (minus the score without the note) fixes the actors (48/48 of the
   non-"You" actors) and the action (72/80) but never chooses "You" or "none" and picks
   note-specific junk for objects and places. Offline sweep of a partial calibration
   (sum - a * null, per slot, on these 80 development texts): best per slot actor 69/80
   (a 0.25), action 72/80 (a 1.0), object 60/80 (a 0.25), place 80/80 (a 0), receiver at
   most 16/80 (only the "You" receivers; "none" is never chosen at any a). Reading: the
   0.5B model with this interface is far from the 0.95 criterion; no rescaling of its
   scores closes the gap. Next measurement (probe 3, before any design change): a
   few-shot prompt p3 (five worked examples per slot as earlier chat turns, development
   wordings only, names/places/objects outside the world vocabulary) and the larger model
   qwen2.5-1.5b (pinned in run 39154386597, revision 989aa798..., Apache-2.0; qwen2.5-3b
   pinned as well, revision aa8e7253..., Qwen research licence, not yet used: 12 GB of
   float32 weights are tight on the 16 GB runner). The design said "a larger model only
   if both fail, as a separate measured decision": qwen2.5-0.5b failed in the timing run
   and probes 1-2, qwen3-0.6b in the timing run (0.10); this probe measures, the decision
   goes to Astra with the evidence.
4. Probe 3 (GitHub 39154541100; 80 development texts; approved sum score unless noted):
   qwen2.5-0.5b+p3 complete records 0.075; qwen2.5-1.5b+p2 0.000 (actor 77, action 75,
   object 72 of 80, but the receiver 1/80); qwen2.5-1.5b+p3 0.713 (actor 79, receiver 59,
   action 80, object 79, place 80, day 80 of 80). The per-token mean is not better; the
   calibrated score fails for every variant (never "You"/"none"). So the worked examples
   and the larger model together make the difference; the receiver is the remaining weak
   slot (it names the narrator for own placings, or the actor of placings and sightings,
   and misses "You" in some gave sentences; wrong answers have margins overlapping the
   right ones, so a threshold alone will not fix it). Cost: 103 s per text (mean) for
   qwen2.5-1.5b+p3, because the examples lengthen every prompt. Changes for probe 4: p4 =
   p3 with an explicit receiver question (only given/handed/passed things have a
   receiver; all other events: none), and the key/value cache of the shared prompt head
   (system prompt + worked examples, identical for every note of a slot) reused across
   notes (`models.score_candidates_prefixed`, one cache per slot prompt, used only when
   the head is an exact token prefix); probes now include a cache check against the
   uncached scores (3 texts, all slots). Decision record: the 0.5B models are dropped
   for this round (failed in every measurement); qwen2.5-1.5b is the candidate model.
5. Probe 4 (GitHub 39165423016; qwen2.5-1.5b+p4): the shared prompt-head cache works -
   35 s per text instead of 103 (model loading 23 s), cache check OK (max diff 1.4e-4,
   identical choices). But the explicit receiver question p4 made the receiver worse
   (49/80, complete records 0.588; "You" receivers 5/16). Probe 5 compares p3 (now with
   the head cache) with p5: the receiver asked as a question about the narrator ("did the
   narrator receive something? You / none") and two more worked examples (a second gave,
   a placing by another person). The other slots stay as in p3.
6. Repository check (2026-10-19): the unit-test workflow had failed since commit 0a5b90e
   although the suite passed locally. Cause: the round 3.5 job tests ran the encode job
   on GitHub, where GITHUB_SHA is set, so the recorded code commit differed from the
   tests' expected "local" and the collector (correctly) reported a provenance mismatch.
   Fixed in the tests (GITHUB_SHA set to "local" for the test job). Since a70b5d8 the pin
   test also failed: qwen2.5-3b has the Qwen research licence ("other") while the test
   requires Apache-2.0; qwen2.5-3b (unused, too large in float32 for the runner) is
   removed from the pins and the pin request. No run result is affected: the failures
   were in the tests only; the round 3.5 runs record and verify their own provenance.
7. Probe 5 (GitHub 39171013100; qwen2.5-1.5b, head cache, cache checks OK): p3 reproduces
   probe 3 exactly (0.713), p5 reaches complete records 0.750 with every slot perfect
   (actor, action, object, place, day 80/80; "You" receivers 16/16) except absent
   receivers (44/64): "You" for 20 notes in which the narrator acts (own placings, "went"
   sentences) or watches a placing. The score gap You - none of these wrong answers
   (0.07-1.89) overlaps only the lowest right "You" gap (1.83; others 3.1-7.2). Probe 6
   compares two prompts with three more worked examples of exactly these kinds (receiver
   "none"): p6 also rewords the receiver question ("You only if another person gave ...
   to the narrator"), p7 keeps the p5 question.
8. Probe 6 (GitHub 39177280797; qwen2.5-1.5b, head cache, cache checks OK): p6
   (reworded receiver question + three examples) 0.750 - the absent receivers improve
   (60/64) but every "You" receiver is lost (0/16); p7 (the p5 question + the same three
   examples) 0.950: every slot perfect except 4 absent receivers (60/64), "You"
   receivers 16/16. Chosen for the development run: qwen2.5-1.5b with p7, candidates c2,
   the approved sum score, the shared prompt-head cache. The 0.95 on 80 probe texts is
   not a result; the full development and calibration runs decide whether the holdout is
   opened.
9. Development and calibration run (GitHub 39181386497; qwen2.5-1.5b+p7, 8 chunks per
   split, complete): best value (tau 0) complete records dev 0.849, cal 0.869; action,
   object, place, day almost perfect; errors concentrated in two places: the receiver
   "You" when the NARRATOR is the actor (own placings, "went": 81 of 82 receiver errors on
   dev) and the actor of "You met X" (seen:dev:1, 30 errors). With the thresholds,
   everything failed for two reasons: (a) a rule gap - the day is a single-candidate slot
   in every note, so calibration has no multi-value cases, no threshold qualifies, and
   the precedence rule makes every day unknown (complete records 0); (b) the receiver's
   threshold (1.59) accepts only 60%. The holdout stays closed (criteria not met on dev or
   cal). Development decisions below use the development split only.
   Proposals for Astra (design changes, measured here only): (1) decoding constraint
   "receiver differs from actor" - the receiver's choice excludes the chosen actor's value
   (a generic two-role constraint, like the declared normalisation of 3.2; applied in
   calibration and decision alike); (2) structurally fixed slots - a slot with only
   single-value cases in calibration accepts single values, and any choice in that slot
   stays unknown (closes the gap; the precedence rule still holds for slots whose
   calibration fails on real choices). Offline on the recorded p7 encodings, with both:
   receiver tau 0, dev complete records 0.933 (receiver 749/750), the remaining failures
   are the actor of "You met X" (40 unknown, 7 wrong) and, through it, giver and person
   cells. Next development run: p8 = p7 + two worked examples ("You met X ...", "you
   watched X leave ...", development wordings), with both decoding proposals switched on
   in the request (measurement).
10. Development and calibration run 2 (GitHub 39186450732; qwen2.5-1.5b+p8, decoding
   proposals "receiver differs from actor" and "structurally fixed slots" on): dev
   complete records 0.945 (best value) / 0.920 (thresholds), cal 0.957 / 0.901; the
   receiver is solved (dev 748-750/750), the remaining errors are the actor: "You met X"
   (36 of 40 dev errors; the extra worked example did not help), "you saw X at P" (2) and
   "You got ... from X" (2) - the model names the grammatical subject "You". Criteria not
   met (giver and person cells). Offline, on the recorded encodings of both runs (no new
   model run): proposal (3) joint role decoding - actor and receiver chosen jointly under
   the schema's role constraints (the receiver differs from the actor; a person seen,
   action "was", is never the narrator - the narrator's own movements are "went"), each
   slot then decided within its feasible values with the usual margin and threshold.
   Result with joint roles + structurally fixed slots: p8 dev complete records 0.999,
   cal 0.996, every 3.5 criterion met on dev AND cal, thresholds all 0 (day structural);
   p7 gives 0.995 / 0.995, also all criteria met. The joint decoding replaces proposal
   (1). These decoding rules are design changes and go to Astra before the holdout.
11. Review of the development result (Astra, 2026-10-19, reviews/2026-10-19_r35dev_astra.txt):
   A (1.5B model) APPROVE; B2 (structurally fixed slots) APPROVE; B1 (joint role decoding)
   and C (frozen configuration) REQUEST CHANGES - the decoder d1 used the provisional best
   action for its action-dependent constraint before the action's own decision, and its
   slot margins (after filtering by the chosen counterpart) could hide a second, equally
   good role pair. Decoder d2 (episodic_lab/encoder35.py, DECODER_VERSION):
   - decisions in a fixed order (action, actor, receiver, object, place, day); the action
     is decided first with its own rule; the narrator constraint applies only to an
     ACCEPTED "was" (an unknown action keeps the roles of every other possible action);
   - actor and receiver margins over ALL feasible role pairs: per actor value the best joint
     score over the feasible receivers, margins between these values; likewise for the
     receiver. Equally good best pairs leave their differing components unknown;
   - one function (`slot_view`/`decide_slot`) for calibration and application: calibration
     runs slot by slot in the decision order, and a later slot sees the earlier slots
     decided with their calibrated thresholds;
   - B2 implemented with the distinction asked for: basis "multi" / "single_only" / "none";
     a slot is STRUCTURAL only with basis "single_only", >= 200 single values and their
     precision >= 0.99 (a tightening: the same evidence bar as a threshold); "none" (no
     evaluable case) gives no threshold;
   - single values report their origin: from the note's candidates ("text") or left by the
     role constraints ("schema");
   - regression tests: tied action with the "was" constraint; "was" below its threshold;
     tied joint pairs with different components (both unknown) and with a shared actor
     (only the receiver unknown); a d1-overstated margin (competitor filtered away).
     Mutation check: provisional action, non-maximal pair score, dropped differ constraint,
     wrong origin, dropped single precision - each killed.
   Offline recomputation on the recorded p8 encodings (run 39186450732, no model calls):
   thresholds unchanged (action, actor, receiver, object, place 0.0 with acceptance 1.0 and
   precision >= 0.997 on 748 multi-value cases each; day STRUCTURAL: 748 single values from
   the text, precision 1.0); dev complete records 0.999, cal 0.996, every 3.5 criterion met
   on dev and cal (best value and thresholds), original 3.3/3.4 rules (17 checks) pass on
   dev and cal - identical to d1. Per role slot, d2 changed
   no value and no status; 831 of 2,996 role margins became smaller (receiver 619, actor
   212; the receiver of own placings no longer profits from the filtered "You"); the
   smallest role margin is 0.48. No single value came from the schema on dev/cal.
   Schema-constrained controls (same candidates, decoder and thresholds; model scores
   replaced): uniform scores decide only the day (750/4,500 slots, complete records 0.000);
   random scores decide every slot with 0.30 correct (complete records 0.001 dev / 0.000
   cal) - the result is carried by the model's scores, not by candidates and decoder.

## Frozen configuration for the holdout (proposal v2, after review 11)

config/round35_holdout_proposal.json (not enabled). Model qwen2.5-1.5b at the pinned
revision, prompt p8, candidates c2, score = sum log-probability, decoder d2 with joint
roles and structurally fixed slots, thresholds actor/receiver/action/object/place 0.0 and
day STRUCTURAL - recomputed with d2 on the calibration split of run 39186450732 (code
e582343). The request binds the code: `frozen.decoder_version` must equal the code's
DECODER_VERSION and `frozen.code_sha256` the SHA-256 of the eight round 3.5 code files
(wordings35, env35, cands35, encoder35, analysis35, models, run_round35, collect_round35);
the collector reports any mismatch as INCOMPLETE (ENCODER_QUALIFIED UNDECIDABLE), so a
code change after the freeze cannot pass unnoticed. Request hash and code commit: in the
review package.
After the approval (item 12) the binding covers the complete local import closure of the
jobs and the collector (25 files, bench/m3/freeze35.py; a test checks that no imported
local module is missing) and is checked three times: in the workflow before the plan (no
job starts on a mismatch), in every encode job before the model loads, and by the
collector.

Role of the calibration split: it was planned as an untouched threshold split; it has been
used as development evidence (runs 9 and 10, the decoder proposals were checked on it), so
its numbers are development values. The thresholds still come from it alone; the unused
holdout (ho, 40 pairs per kind) is the only independent test. The reserve split stays
closed.

## Holdout (after the approval)

12. Review of the decoder correction (Astra, 2026-10-19, reviews/2026-10-19_r35dev_v2_astra.txt):
   APPROVE on every point (A model, B1 decoder d2, B2 including the evidence bar, C frozen
   configuration); the holdout may be evaluated once after the coverage check. Adopted
   non-blocking ideas before the run: the freeze check also before the encoding (workflow
   plan and every encode job), and the hash binding extended from the eight round 3.5
   files to the complete local import closure (memory operators, history logic, reference
   rules, round 3.3/3.4 criteria). Neither changes a decision; both only stop a run whose
   code differs from the freeze. Planned: the five cases for Joe chosen systematically (a
   historical pair, a role change, the narrator as actor, and present error or abstention
   cases); the control statement stays narrow (the performance belongs to the whole system
   of model scores, candidates and schema constraints).
   Post-freeze coverage check (bench/m3/audit35.py --frozen, model-free, 2026-10-19,
   docs/ROUND_3_5_holdout_audit.json): no problems; disjoint texts; candidate coverage 1.0
   for every slot on dev, cal, aud and ho (2,974 distinct holdout texts); the position and
   word-list baseline on the holdout: all slots 0.647. The holdout is opened with
   config/round35.json = the proposal with "enabled": true (12 chunks; holdout notes have
   about 10% more candidates than development notes, about 2.7 h per chunk expected).

13. HOLDOUT RESULT (GitHub 39221095580, commit 4809114, request sha256 33b7f369..., all 12
   chunks OK, collector VERDICT COMPLETE, freeze checks passed): ENCODER_QUALIFIED = NO,
   MILESTONE_ORIGINAL_RULES = FAIL. The holdout worlds and holdout paraphrases are consumed.
   - Records (2,974 distinct texts): complete records 0.959 (criterion >= 0.95 met); place
     and day 1.000, object 0.998, actor 0.993, receiver 0.991, action 0.977. 122 records
     are wrong, each in exactly one slot (deduplicated texts; 122 slot errors). No unknown
     record field was observed (thresholds 0 still give unknown for ties, for an empty
     feasible set and for several candidates of a structural slot - none occurred).
   - Tasks: hidden, moved and every history cell 1.000 except object:first 0.988 (one
     confident error, rate 0.013 <= 0.05); giver:find 0.938, pair success 0.925 - the two
     failed criteria (success >= reference - 0.02, pair success >= 0.95). Of the 80 giver
     world decisions 74 came from memory (all right) and 6 were fallbacks (the giver not
     found -> exploration); 1 of the 6 explorations happened to reach the right place
     (r35-ho-6 B), 5 were wrong. (Corrected after Astra's review: the first report said 5
     fallbacks.)
   - Error mechanisms (bench/m3/cases35.py and the per-frame breakdown):
     (a) "It was day d when you set the X down at P." -> action "left" instead of "put"
         (69 of 231 texts of that frame; task-neutral, both are placings);
     (b) the object "heavy X" read as "X" (6 of 189 "heavy" objects; on dev already 1 of
         48 with the smallest correct margin of every adjective, 0.12 - a warning visible
         before the freeze that was not acted on); this caused 2 giver worlds (explore)
         and the one confident error (first placement of "heavy ledger" not recognised);
     (c) "the X came to you from Y" -> receiver "none" (9 of 75; 3 giver worlds explore);
     (d) "you saw X put ..." -> receiver "You" (17 of 232; task-neutral);
     (e) passive "... by X, and you saw it" -> actor "You" (13 of 246); "P was where you
         went" -> actor = the place name (5 of 180);
     (f) the two-part name "Halsey Tellin" shortened to "Halsey" (2: one placing, one
         giving; added after Astra's review - with (e) the 20 actor errors).
     The original criteria stay unchanged; the "heavy" signal (1 error in 48 on dev)
     violated no pre-registered class criterion - it leads to the class diagnostics of 3.5b.
   - Controls: uniform scores decide only the day (complete records 0.000), random scores
     0.299 of the slots correct; position/word-list baseline 0.647.
   - The original 3.3/3.4 rules fail where they demand perfection (intact success and
     pair success 1.0, swap/removal predictions >= 0.95, irrelevant removal 1.0).
   By the design (section 3) a further qualification needs a logged development fix and
   new worlds with the reserve paraphrases (the last unused wording set); the holdout
   wordings and worlds are now development/audit material.
14. Review of the holdout result (Astra, 2026-10-19, reviews/2026-10-19_r35holdout_astra.txt):
   NO / FAIL confirmed; count corrections (6 fallbacks of which 1 accidentally right; the
   two missing actor errors; 122 deduplicated records; thresholds 0 can still give
   unknown) - done in item 13. Round 3.5 stays NO / FAIL permanently. The continuation is
   round 3.5b with its own protocol: docs/ROUND_3_5b.md.
