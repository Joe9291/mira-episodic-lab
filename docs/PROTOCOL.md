# Mira Episodic Lab - Research Protocol

Version 0.1 - DRAFT, not yet preregistered. It becomes binding only after review and a
signed experiment-series authorization by the experiment lead (section 9).

## 1. Question and scope

**Research question.** Can language-model agents, using only free CPU compute, build and
operate a system that gives a small open-weight language model *functional episodic
memory*?

- Builders and operators: language-model agents (Claude writes and controls, Astra
  executes in the private repository, Gemini reviews). The experiment lead decides and
  signs; he does not run anything on his own computer.
- Compute: GitHub-hosted standard runners of this public repository only (4 vCPU,
  16 GB RAM, 14 GB SSD, at most 6 hours per job, at most 20 parallel jobs, no GPU).
  No paid service, no secret, no external API.
- Scope: behavioural, measurable memory functions (section 2). This protocol makes no
  claim about subjective experience, consciousness or "singularity".

## 2. Operational definition: criteria E1-E7

A system has functional episodic memory in this study if it meets all of:

| Id | Criterion | Test |
|---|---|---|
| E1 | Single-exposure encoding | Each episode is presented exactly once, during its encoding step, with a fixed and reported encoding budget (for weight updates: number of optimizer steps on that one presentation). After its encoding step the raw episode text is not available to the system except through the memory mechanism under test. Verified by code audit and by the run receipt. |
| E2 | Cue-based recall | Questions cue an event by time, place, entity, content or a combination and ask for a specific detail. |
| E3 | Temporal order and latest state | "Which happened first", "where is X now", "what did X last do". |
| E4 | Source memory | "On which day / in which episode did X happen". |
| E5 | No confabulation | Questions about events that never happened; the correct answer is "none". Measured as false-recall rate. |
| E6 | Retention under interference | Recall of early episodes after K further episodes have been encoded (K preregistered), relative to immediate recall. |
| E7 | Use of memory for action | Questions that require combining two remembered episodes to choose an option. |

## 3. Benchmark: synthetic episodic worlds

- A deterministic generator creates fictional worlds: invented people, places, objects,
  dates and actions. Each episode is a short narrative (about 100-250 tokens) of one event
  with time, place, participants and content.
- Ground truth is computed from the world state, never by a model. Every question has a
  structured answer (fields such as `who`, `where`, `when`, `episode_id`, or `none`).
- Question templates exist for every criterion E2-E7, including zero-event questions
  (E5) and multi-event cues.
- Contamination: worlds are generated freshly per run from a seed fixed after the
  protocol is signed (derived from the commit that starts the confirmatory series), so no
  model can have seen them in pre-training and no prompt can be tuned to them.
- Separation: the system under test receives only episodes (during encoding) and
  questions (during testing). Answers are scored by a separate evaluator step that holds
  the ground truth. No language model judges answers.

## 4. Systems under test (arms)

| Arm | Description | Role |
|---|---|---|
| A0 | Base model, no memory | Lower bound; guessing and confabulation rate |
| A1 | All episodes in the prompt (if they fit) | In-context reference, not episodic memory |
| A2 | Simple retrieval: lexical search over stored episode texts, top-k into the prompt | Standard external memory baseline |
| A3 | Mira memory: structured event store (time, place, entities, provenance), typed recency within claim families, retrieval into the prompt | Mira's architecture |
| P1 | Fast weights: one small LoRA update per episode, applied once at encoding; tested without episodes in context | Parametric single-exposure memory |
| P2 | Direct weight editing of facts (rank-one edits), if feasible on CPU | Alternative parametric memory |
| C1 | Complementary system: A3 store plus periodic consolidation into LoRA weights by replay ("sleep"); tested also with the store degraded | Consolidation |

Controls: **sham training** (same number of steps on unrelated text) for P1, P2 and C1;
**shuffled memory** (store filled from a different world) for A2, A3 and C1, to separate
memory use from guessing.

## 5. Models

- Small open-weight instruction models with permissive licences, CPU-feasible. Pilot
  candidates: SmolLM2-135M/360M-Instruct, Qwen2.5-0.5B-Instruct, Qwen3-0.6B. Licence,
  exact revision and SHA-256 of every model file are verified and pinned before first use.
- Selection rule: the smallest candidate whose A1 recall in the pilot is at least 0.8
  on short worlds. If none reaches it, the answer format is simplified first, then the
  next larger candidate is tried.
- Decoding is greedy; seeds and library versions are pinned; deterministic algorithms
  are enabled where the library allows.

## 6. Measurement and statistics

- Scoring by exact match on normalised structured fields; per-criterion accuracy, E5
  false-recall rate, E6 retention ratio.
- Unit of replication: the world. Confirmatory runs use at least 10 independent worlds
  per arm (more if the pilot variance requires it; the number is fixed before the
  confirmatory series).
- 95% confidence intervals: Wilson intervals for proportions, bootstrap over worlds for
  differences between arms.
- Pilot (exploratory) and confirmatory data are strictly separated; pilot results are
  reported but never counted as confirmation.

## 7. Decision and pivot rules

- **Pilot gate.** An arm is carried into the confirmatory series only if its pilot E2
  recall exceeds A0 by at least 20 percentage points and its E5 false-recall rate is not
  higher than A0's.
- **Pivot rule.** If an arm fails the pilot gate, up to three *meaningfully different*
  variants are tried (for P1: target layers, rank, learning rate or encoding steps; for
  A3: store schema or retrieval). Each variant is written down with its reason before it
  runs; the same variant is never re-run with cosmetic changes. After three failed
  variants the arm is recorded as a negative result and the next mechanism is taken up.
- **Success (proposal; the numbers are fixed after the pilot and before the signed
  confirmatory series).** A system meets E1-E7 if E1 holds by audit; E2 recall lower CI
  bound >= 0.6 and above the A0 upper bound; E3 and E4 lower bounds >= 0.5; E5 false
  recall upper bound <= 0.1; E6 retention ratio >= 0.8 after K interfering episodes;
  E7 lower bound >= 0.5. The same thresholds apply to every arm.

## 8. Compute plan

- Every run is one GitHub Actions workflow job with a declared time budget below 5.5 h;
  independent worlds and arms run as parallel jobs (at most 20).
- Model files are downloaded from Hugging Face by pinned revision, checked against the
  pinned SHA-256 values and cached.
- Order of work: CPU-cheap arms first (A0-A3), then P1, P2, C1. Larger models only for
  mechanisms that passed the pilot.

## 9. Integrity and governance

- This repository is public. It holds only code, synthetic worlds and results. Nothing
  from the private repository except reviewed code, no private or blind material, no
  state documents, no secrets.
- Workflows run only on pushes to `main` and on manual start; never on pull requests
  from forks. They use no secrets.
- Every run writes a receipt: commit, configuration hash, model pins, seeds, world
  hashes, encoding budgets, metrics, runtime. Results are kept on a separate `results`
  branch; every run, including failed ones, is listed.
- Results are taken over into the private repository by hash manifest and recorded in
  its run register.
- Before the confirmatory series the experiment lead signs one experiment-series
  authorization: protocol hash, model pins, thresholds, maximum number of runs. Within
  it the agents run without further signatures; any change of protocol, thresholds or
  pinned code needs a new signature.
- Reviews by Gemini are sent part by part with a verbatim quote from the end of each
  part as proof of complete reading. Deterministic checks take precedence over model
  judgements.

## 10. Known limits

- Small models and synthetic worlds: positive results show a mechanism, not human-level
  memory; negative results at this scale do not rule out larger models.
- Functional criteria only.
- The agents build, run and evaluate; independent replication by a different pipeline
  or a human is required before any strong claim.

## 11. Milestones

1. Generator, question templates, scorer and their tests (no model).
2. Workflow, model pinning, A0 and A1 pilot.
3. A2 and A3 pilot.
4. P1 pilot, then P2 if feasible.
5. C1 pilot.
6. Thresholds and sample size fixed; signed experiment-series authorization.
7. Confirmatory series.
8. Report, import into the private repository, external review.
