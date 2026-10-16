# Mira Episodic Lab - Research Protocol

Version 0.2 - DRAFT. Governs the exploratory pilot (milestones 0-5). It is not the
confirmatory preregistration: thresholds, sample size and the final arm list are fixed
in version 1.0, which needs a three-way review and the experiment lead's signature
(section 10). Changes from 0.1 follow the reviews by Gemini and Astra of 2026-10-16
(`reviews/`).

## 1. Question and scope

**Research question.** Can language-model agents, using only free CPU compute, build and
operate a system that gives a small open-weight language model *functional episodic
memory*?

- Builders and operators: language-model agents (Claude writes and controls, Astra
  executes in the private repository, Gemini and Astra review). The experiment lead
  decides and signs; he runs nothing on his own computer.
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
| E2 | Cue-based recall with binding | Questions cue an event by a combination of time, place, people, object or action and ask for a missing detail. People, places and objects recur across many episodes, so only the *combination* identifies an episode (binding test). Question wording is drawn from paraphrase sets never used in encoding text. |
| E3a | Temporal order | Which of two events happened first. Event time and presentation order partly differ (some episodes are told out of order), so presentation order alone does not answer it. |
| E3b | State at a time | Latest state ("where was X last") and earlier states ("where was X on day d"), so overwriting the current state alone does not suffice. |
| E4 | Source memory | On which day an event happened. The same content (same person, action, object) occurs in several episodes; episode identifiers are random tokens and reveal no order. |
| E5 | No confabulation | Lure questions built from known details in combinations that never occurred (same templates as E2). Measured as false-recall rate. |
| E6 | Retention under interference | Recall of early episodes after K further episodes, in two conditions with equal length: high-overlap (competing) and low-overlap follow-up episodes. Reported: immediate accuracy, delayed accuracy (absolute) and their ratio. |
| E7 | Use of memory for action | A small text environment asks the system to choose an action (for example, where to go to find an object); the choice is executed and scored. Each item needs two specific episodes, and the generator verifies that changing either episode changes the correct action. |

## 3. Benchmark: synthetic episodic worlds

- A deterministic generator (own SHA-256 based generator, independent of Python
  versions) creates fictional worlds: invented people, places, objects, days and
  actions with deliberate feature overlap. Each episode is a short narrative of one
  event; some are told out of chronological order.
- Ground truth is computed from the world state, never by a model. Every question has a
  structured answer type (person, place, object, day, choice label, or `none`), and the
  generator checks that each question has exactly one correct answer.
- Answer handling, fixed before use: normalisation (case, punctuation, articles,
  surrounding words such as "day"), a fixed list of accepted "none" forms, invalid or
  partial output counts as wrong, questions weigh equally within a world and worlds
  weigh equally.
- Starting size (from the reviews; revised only after milestone 0): about 20 episodes
  and 100 questions per world; larger worlds form a separate stress level.
- Separation: the system receives episodes (encoding) and questions (testing) only. A
  separate evaluator step holds the ground truth. No language model judges answers.
- Clean state: every world starts with fresh model, adapter, optimizer and store state.
  Test questions leave no trace usable later; weight-based arms answer without chat
  history, key-value cache or any other auxiliary store.
- Training targets of weight-based arms are derived only from the presented episode
  texts, never from the evaluator's ground truth.

## 4. Systems under test (arms) and controls

| Arm | Description | Role |
|---|---|---|
| S0 | Symbolic event manager: rule-based parser and database over the same texts | How far plain data handling solves the task |
| O1 | Oracle evidence: the correct episode(s) placed in the prompt | Can the model use the evidence at all |
| A0 | Model, no memory | Guessing and confabulation floor |
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

## 5. Models

- Small open-weight instruction models with permissive licences, CPU-feasible. Pilot
  candidates: SmolLM2-135M/360M-Instruct, Qwen2.5-0.5B-Instruct, Qwen3-0.6B. Licence,
  exact revision and SHA-256 of every model file are verified and pinned before first use.
- Greedy decoding. For Qwen3 the thinking mode is switched off (`enable_thinking=False`)
  and the suitability of this setting is checked in the pilot; otherwise the model is
  not used with greedy decoding.
- Selection rule: the smallest candidate whose O1 accuracy in the pilot is at least
  0.8. If none reaches it, the answer format is simplified first, then the next larger
  candidate is tried (this counts against the variant budget of section 7).

## 6. Measurement and statistics

- Unit of replication: the world. All arms run on the same worlds; arm differences are
  analysed as paired per-world differences.
- Primary estimates: the mean over worlds of per-world accuracy (or false-recall rate),
  with a 95% interval that respects the world structure (t-interval over worlds;
  bootstrap over worlds only as a check, because it is unreliable with few worlds).
- E5 false recall: a conservative upper bound that does not collapse to zero when no
  error occurs (exact binomial bound on the pooled count, using an effective sample
  size reduced by the design effect estimated in the pilot).
- E6: immediate and delayed accuracy each with intervals; success needs a minimum
  absolute delayed accuracy in addition to the ratio; a ratio is not reported when
  immediate accuracy is below the minimum.
- Thresholds are justified per question type from its chance level and a stated
  minimum practically relevant margin. Superiority claims (for example A3 over A2, P1
  over sham) are tested on paired differences with Holm correction across the
  preregistered claims. Overall success (all criteria jointly) needs no extra
  correction.
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

## 9. Compute plan

- Milestone 0 measures on the real runner: model loading, inference speed, one LoRA
  step per episode for the pilot models, and the cost of P2's statistics. World size,
  question count and the arm list for weight-based memory are set from these numbers.
- Each run is one workflow job with a declared budget below 5.5 hours; worlds and arms
  run as parallel jobs (at most 20). Parallel jobs shorten a series, not a single run.
- Model files are downloaded by pinned revision, checked against pinned SHA-256 values
  and cached.

## 10. Integrity and governance

- This repository is public. It holds only code, synthetic worlds, results and reviews.
  Nothing from the private repository except reviewed code; no private or blind
  material, no state documents, no secrets.
- Workflows run only on pushes to `main` and on manual start, never on pull requests
  from forks, and use no secrets.
- Every run writes a receipt: commit, configuration hash, model pins, seeds, world
  hashes, E1b processing counts, metrics, runtime. Results go to a separate `results`
  branch; every run, including failed ones, is listed.
- Version 1.0 fixes code, arms, thresholds and sample size. The experiment lead then
  signs one experiment-series authorization (protocol hash, model pins, maximum number
  of runs). The confirmatory world seed is the SHA-256 of that signature: fixed only
  after everything else, unpredictable to the agents, reproducible by anyone.
- Results are taken over into the private repository by hash manifest and recorded in
  its run register.
- Reviews are blind (no reviewer sees another's verdict first) and include a verbatim
  quote from the end of the document as proof of complete reading. Deterministic checks
  take precedence over model judgements.

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
   three-way review; signed experiment-series authorization.
7. Confirmatory series.
8. Report, import into the private repository, external review.
