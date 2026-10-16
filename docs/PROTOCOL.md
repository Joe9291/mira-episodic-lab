# Mira Episodic Lab - Research Protocol

Version 0.6 - DRAFT. Governs the exploratory pilot (milestones 0-5). It is not the
confirmatory preregistration: thresholds, sample size and the final arm list are fixed
in version 1.0, which needs the reviews of section 10 and the experiment lead's
signature. Version 0.2 integrated the reviews of 0.1; 0.3 integrated Astra's review of
milestones 0/1 (answer grammar, E5 categories, E7 semantics, identical early blocks,
frozen memory during tests, world-level statistics); 0.4 integrates Astra's review of
milestone 1.1 (binding by answer ambiguity, E4 on repeated content, model pinning,
result registration, narrower claims about frozen memory, two-level thresholds, seed
procedure); 0.5 integrates Astra's review of milestone 1.2 (balanced E3a quota, robust
result check, signature details); 0.6 integrates Astra's review of milestone 2 (O1
confusable evidence for lures and a positive-items selection criterion, strict cell
schema check, per-cell provenance and E1b counts, E3b subtypes and E5 uncertainty in the
summary) and round 2 of that review (the collector recomputes every published number
from the answer rows and makes the E1b fields mandatory). Reviews: `reviews/`.

## 1. Question and scope

**Research question.** Can language-model agents, using only free CPU compute, build and
operate a system that gives a small open-weight language model *functional episodic
memory*?

- Builders and operators: language-model agents (Claude writes, controls and is lead
  reviewer; Astra executes in the private repository and reviews independently in a
  separate chat). The experiment lead decides and signs; he runs nothing on his own
  computer. Gemini was removed as reviewer by the experiment lead on 2026-10-16 after
  repeatedly failing the proof of complete reading (`reviews/`).
- Compute: GitHub-hosted standard runners of this public repository only (4 vCPU,
  16 GB RAM, 14 GB SSD, at most 6 hours per job, at most 20 parallel jobs, no GPU).
  No paid service, no secret, no external API.
- Scope: behavioural, measurable memory functions of the *whole system* (model plus
  any memory mechanism). No claim about subjective experience, consciousness or
  "singularity". A positive result for an external-store arm shows a memory function of
  the system; a claim that Mira's architecture adds something needs the comparison with
  the simple-retrieval arm and the ablations (section 4).

## 2. Operational definition: criteria E1-E7

The closed-world assumption holds throughout: "none" means "not in the episodes
presented to the system".

| Id | Criterion | Test |
|---|---|---|
| E1a | Single external presentation | The environment presents each episode exactly once. Afterwards its raw text is available to the system only through the memory mechanism under test. Verified by code audit and run receipt. |
| E1b | Declared internal processing | Every arm reports, per episode: internal replays, tokens processed, optimizer steps (weight-based arms), store writes (store-based arms). These are reported, not hidden; arm comparisons state them. |
| E2 | Cue-based recall with binding | Questions cue an event by a combination of time, place, people, object or action and ask for a missing detail. People, places and objects recur across many episodes. Binding test per item: dropping any single cue detail leaves early episodes with *different* answers (for "who" questions: no person took part in all of them), so the full combination is needed for the answer. Question wording is drawn from paraphrase sets never used in encoding text. |
| E3a | Temporal order | Which of two events happened first. About a third of the early episodes are told later than their day. Every world has exactly 4 pairs whose presentation order agrees with their day order and 4 whose order is inverted, and every episode appears in at most one pair, so the strategies "the earlier told happened first" and "the later told happened first" both score exactly 50%. |
| E3b | State at a time | Latest state ("where was X last") and earlier states ("where was X on day d"), so overwriting the current state alone does not suffice. Both subtypes have their own minimum count and are reported separately. |
| E4 | Source memory | On which day an event happened, asked only for content (person, action, object) that occurs on at least two early days; the place tells the occurrences apart, so the content alone does not give the day. Episode identifiers are random tokens and reveal no order. |
| E5 | No confabulation | Lure questions built from known details in combinations that never occurred (same templates as E2); every pair of their details co-occurs in the early block. Reported per answer category: correct rejection, in-world false recall, uncertainty, other (format errors and out-of-world claims). Success needs a high correct-rejection rate AND a bounded in-world false-recall rate; false recall alone is never read as the full confabulation rate. |
| E6 | Retention under interference | Recall of early episodes after K further episodes, in two conditions with equal length: high-overlap (competing) and low-overlap follow-up episodes. Reported: immediate accuracy, delayed accuracy (absolute) and their ratio. |
| E7 | Use of memory for a decision | Decision items: "where do you go to meet the last person who handled object X" and "where do you go to meet the person who did Y" - each needs the episode that identifies the person AND that person's latest episode at another place. Executing the choice in a small environment is a later extension. |

## 3. Benchmark: synthetic episodic worlds

- A deterministic generator (own SHA-256 based generator, independent of Python
  versions) creates fictional worlds: invented people, places, objects, days and
  actions with deliberate feature overlap. Each episode is a short narrative of one
  event; some are told out of chronological order.
- Ground truth is computed from the world state, never by a model. Every question has a
  structured answer type (person, place, object, day, choice label, or `none`), and the
  generator checks that each question has exactly one correct answer.
- Answer grammar, fixed before use (parser version recorded with every answer): only the
  first line; after normalisation and removal of fixed leading filler phrases the rest
  must be exactly one allowed form (full name or its unique short form, "day n", "a"/"b",
  a rejection form, or an uncertainty form). Negations, several names, extra or
  contradicting attributes and unknown names are "other" and count as wrong. Raw answers
  are kept. Questions weigh equally within a world and worlds weigh equally.
- Default world: an early block of 30 episodes and 10 follow-up episodes (K = 10); per
  world 4 people, 4 places, 4 objects and 4 actions, so that details recur and recall
  items need the full combination of their cues (verified per item). The early block
  depends on the seed only; the high- and low-overlap versions of a world share it, and
  their early test items are identical. Larger worlds form a separate stress level.
- Minimum items per world (E2 8, E3a 4, E3b 6 with at least 3 per subtype, E4 4, E5 6,
  E7 3). World k of a series uses the first seed attempt `<series>-<k>-<attempt>` that
  meets them in both conditions; the rule depends only on the generator, never on any
  system's answers. Attempts and skipped seeds are reported; statements refer to the
  worlds this rule accepts (82 of 100 series worlds valid at the first attempt, none needing
  more than two further attempts; generator at lab commit f7d4402).
- Separation: the system receives episodes (encoding) and questions (testing) only. A
  separate evaluator step holds the ground truth. No language model judges answers.
- Clean state: every world starts with fresh model, adapter, optimizer and store state.
  Every answer must come from a fresh context: the adapter builds each prompt from
  scratch, with no chat history, key-value cache or other auxiliary store. The runner
  checks what it can see - the system's own digest of its memory plus a fingerprint of
  every other attribute of the system object - before and after each answer, and
  rejects any change. State outside the system object (globals, files) is excluded by
  code audit; for the model arms this is an acceptance criterion of milestone 2.
- Training targets of weight-based arms are derived only from the presented episode
  texts, never from the evaluator's ground truth.

## 4. Systems under test (arms) and controls

| Arm | Description | Role |
|---|---|---|
| S0 | Symbolic event manager: rule-based parser and database over the same texts | How far plain data handling solves the task |
| O1 | Oracle evidence (diagnostic): the target episode(s) of each question placed in the prompt; for E5 lures, confusable early episodes, one per pair of the lure's details (first in presentation order, deduplicated), so that no lure is answered from an empty context | Can the model use given evidence at all. Not a memory system: the evaluator supplies the evidence at every question, so its E5 and E6 values are no memory results. A lure always gets three notes, positive items one or two, so the note count can signal a lure: O1's E5 is no clean binding diagnosis (equal note counts would be needed for that) |
| A0 | Model, no memory: empty notes and the instruction to answer "none" when the notes lack the event | Missing-evidence control with requested abstention; guessing and confabulation floor |
| A1 | All episodes in the prompt (if they fit) | In-context reference, not episodic memory |
| A2 | Simple retrieval: lexical search, top-k episodes into the prompt | Standard external memory |
| A3 | Mira memory: structured event store (time, place, people, provenance), state tracking, retrieval | Mira's architecture |
| P1 | Fast weights: one small LoRA update per episode at encoding, answers without episodes in context | Parametric single-presentation memory |
| P2 | Rank-one weight edits | Conditional, only if milestone 0 shows it feasible |
| C1 | A3 store plus periodic consolidation into LoRA weights by replay | Consolidation |

Controls:
- **Random retrieval** (A2/A3): the same number of random episodes from the same world.
- **Misbound memory** (A2/A3/C1): a store with the same vocabulary and fact
  distribution but swapped bindings (who/where/when exchanged across episodes).
- **A3 ablations**: without time information, without provenance, without state-update
  logic; context and retrieval budgets equal to A3.
- **Sham training** (P1/P2/C1): the same number of steps and tokens on unrelated text.
- **C1 decomposition**: store without consolidation, consolidated weights without
  store, both; store corruption identical for A3 and C1; extra replay compute reported
  and matched where possible.
- **Interference control** (E6): low-overlap follow-up episodes of equal length.
- **Shortcut strategies** (pilot): simple rule-based answerers that use only part of the
  cues (for example the most frequent object for a person and place, ignoring the
  action) are scored on the same items, so that frequency shortcuts are quantified
  rather than assumed absent.

## 5. Models

- Small open-weight instruction models with permissive licences, CPU-feasible. Pilot
  candidates: SmolLM2-135M/360M-Instruct, Qwen2.5-0.5B-Instruct, Qwen3-0.6B. Licence,
  exact revision and SHA-256 of every model file are verified and pinned before first use
  in the pilot. Exception: the exploratory feasibility measurement of milestone 0 resolved
  the current revision at run time and recorded it (no answers of any model were
  evaluated); those recorded revisions are the starting point of the pinning step of
  milestone 2, which records every file's SHA-256, and the pilot refuses any other bytes.
- Greedy decoding. For Qwen3 the thinking mode is switched off (`enable_thinking=False`)
  and the suitability of this setting is checked in the pilot; otherwise the model is
  not used with greedy decoding.
- Selection rule: the smallest candidate whose O1 accuracy in the pilot is at least
  0.8. O1 accuracy here is computed on positive items only (final test, criteria E2,
  E3a, E3b, E4, E7; E5 lures excluded): per world the share of correct answers over these
  items of both overlap conditions, then the mean over the pilot worlds (the lowest world
  is reported alongside). If none reaches it, the answer format is simplified first, then the next larger
  candidate is tried (this counts against the variant budget of section 7).

## 6. Measurement and statistics

- Unit of replication: the world. All arms run on the same worlds; arm differences are
  analysed as paired per-world differences.
- Target parameters for confirmatory decisions are defined on independent worlds: the
  probability that a new world meets a criterion's threshold, and for E5 the probability
  that a new world contains at least one in-world false recall. They are decided with
  exact one-sided Clopper-Pearson bounds over the world indicators. Version 1.0 fixes
  two levels separately: the per-world threshold (when a world passes) and the required
  probability that a new world passes.
- Descriptive estimates: the mean over worlds of per-world accuracy with a t-interval
  (approximate; zero width when all worlds score alike, which is no certainty) and a
  pooled E5 bound with a design-effect-reduced sample size (approximate). Paired arm
  differences are computed by world id.
- E6: accuracy on the same early items (E2, E4) at phase 1 and at the final test, in
  the high- and the low-overlap condition; success needs a minimum absolute delayed
  accuracy in addition to the ratio; a ratio is not reported when immediate accuracy is
  below the minimum.
- Thresholds are justified per question type from its chance level and a stated
  minimum practically relevant margin. Superiority claims (for example A3 over A2, P1
  over sham) are tested on paired differences with Holm correction across the
  preregistered claims. Overall success of one preselected arm (all criteria jointly)
  needs no extra correction; a claim that "at least one of several arms" succeeds
  is corrected for the number of arms.
- Sample size: fixed in version 1.0 from the pilot's per-world variance and the
  preregistered minimum effects, with the probability of detecting them stated.
- Pilot (exploratory) and confirmatory data are strictly separated.

## 7. Decision and pivot rules (pilot)

- **Pilot gate.** An arm advances if its paired gain over A0 on E2 is at least a margin
  stated with its reason before the pilot (default 0.20 absolute; lowered only with
  written justification if A0 is near ceiling), and its E5 false-recall rate stays
  within an absolute tolerance (default 0.10).
- **Variant budget.** Each arm has its base configuration plus at most three variants.
  Model, answer format and hyperparameter changes share this one budget. A variant is
  chosen after analysing why the previous one failed; it is committed as a configuration
  file with its reason *before* it runs, and every variant is reported.
- **Scope of a negative result.** Three failed variants are a negative result for those
  configurations and this compute budget, not a refutation of the mechanism.

## 8. Reporting

- Two axes for every arm: memory functions met (E1-E7) and cost (encoding, retrieval,
  storage, training compute).
- Error localisation along the chain: correctly extracted, stored, retrieved, answered.
- Stress levels: more episodes, more feature overlap, longer delays, new question
  wordings.
- Weight-based arms also report general abilities (simple language and reasoning
  checks) before and after encoding.
- Weight-based arms (P1, P2, C1) change weights while encoding, so their frozen-weights
  check compares against the state after each encoding block, not against the weights
  before the world (planned for milestone 4).

## 9. Compute plan

- Milestone 0 (done, run 38915077515): on the standard runner a LoRA step on one
  100-token episode takes 0.35 s (SmolLM2-135M) to 1.95 s (Qwen3-0.6B); prompt
  processing runs at 120-790 tokens/s; peak memory 1.2-4.7 GB. Per-episode encoding (P1)
  is therefore minutes per world. Long all-episode prompts, chat templates and P2's full
  cost (activation statistics, covariance, solve, edit) are measured in the pilot.
- Each run is one workflow job with a declared budget below 5.5 hours; worlds and arms
  run as parallel jobs (at most 20). Parallel jobs shorten a series, not a single run.
- Model files are downloaded by pinned revision, checked against pinned SHA-256 values
  and cached (from milestone 2 on; see section 5 for the milestone 0 exception).
- Result registration: every run stores its outputs and a completeness verdict on the
  `results` branch even when a measurement or the collection of outputs fails; the
  verdict is checked field by field, and an incomplete run fails visibly.

## 10. Integrity and governance

- This repository is public. It holds only code, synthetic worlds, results and reviews.
  Nothing from the private repository except reviewed code; no private or blind
  material, no state documents, no secrets.
- Workflows run only on pushes to `main` and on manual start, never on pull requests
  from forks, and use no secrets.
- Every run writes a receipt: commit, configuration hash, model pins, seeds, world
  hashes, E1b processing counts, metrics, runtime. In the pilot every cell records the
  code commit, the SHA-256 of the pilot request and of the pins manifest, the model
  revision and weights digest, the SHA-256 of each world and question set, and per
  episode: encoding reads, prompt inclusions, tokens of the episode, prompt token
  equivalents (episode tokens x inclusions; tokenisation at text boundaries inside a
  full prompt can differ slightly) and the arm's declared replays, optimizer steps and
  store writes; per condition peak memory and the longest prompt; every answer row
  records its prompt length, answer length and whether the token limit cut it off. The
  collector validates the full cell schema and identity, recomputes every published
  number (summaries, E3b subtypes, E5 categories and false recall, E6 retention, token
  totals, E1b counts) from the rows and per-episode counts and requires exact agreement,
  requires one code commit and identical worlds and episode ids across arms and models,
  and marks the run INCOMPLETE if any cell or the summary fails. SUMMARY.md also gives a
  descriptive format-compliance rate (answers inside the answer grammar); the scoring
  stays strict. Results go to a separate `results`
  branch; every run, including failed ones, is listed.
- Version 1.0 fixes code, arms, thresholds and sample size. The experiment lead then
  signs one experiment-series authorization (protocol hash, model pins, maximum number
  of runs). Before signing, the exact authorization text (UTF-8, LF line ends, ending
  with LF) and its SHA-256 are committed to this repository, so the signed message is
  fixed in advance. Signing uses the experiment lead's existing Ed25519 key (key id
  bf5a705a0a014522, public key f86e778e8dd13de10e26e22238cd567174d8b468d895b960657215e2b0ba8426)
  over the bytes "MIRA-SIGNATURE-V1\ndomain: lab_experiment_series\nsha256: <hex>\n" (the
  same signed-text format as the private repository's tools/mira_signing.py, whose fixed
  domain list does not include this domain; the lab verifies it with its own code), where
  <hex> is the SHA-256 of the authorization text. The confirmatory world seed is the lowercase hex
  SHA-256 of the 64 signature bytes. Ed25519 signatures are deterministic (RFC 8032): the
  seed is unpredictable without the private key, cannot be chosen by the agents, and is
  reproducible by anyone from the published signature.
- Results are taken over into the private repository by hash manifest and recorded in
  its run register.
- Reviews are blind (no reviewer sees another's verdict first) and include a verbatim
  quote from the end of the document as proof of complete reading; a review without a
  correct quote is not counted. With two model reviewers, one of them the author,
  deterministic checks (tests, mutation tests, reference worlds) take precedence over
  model judgements, and independent replication remains required (section 11).

## 11. Known limits

- Small models and synthetic worlds: positive results show a mechanism at this scale;
  negative results do not rule out larger models.
- Functional criteria only.
- The agents build, run and evaluate; independent replication is required before any
  strong claim.

## 12. Milestones

0. Feasibility measurement on the runner (section 9).
1. Generator, question templates, scorer, symbolic arm S0 and their tests (no model).
2. Workflow, model pinning, O1, A0 and A1 pilot.
3. A2, A3, controls and ablations pilot.
4. P1 pilot; P2 only if milestone 0 allows.
5. C1 pilot.
6. Version 1.0: confirmatory core (A0-A3 with controls, at most one preselected
   weight-based arm; P2 and C1 as separate later series), thresholds, sample size;
   review by Astra and Claude (section 10); signed experiment-series authorization.
7. Confirmatory series.
8. Report, import into the private repository, external review.
