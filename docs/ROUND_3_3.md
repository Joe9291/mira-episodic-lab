# Round 3.3 - paired action worlds with causal memory interventions (v2, after Astra's review)

Milestone-3 goal (docs/STRATEGY.md): an agent keeps a single experience across a process
restart, uses it for a goal announced later, and targeted interventions on exactly that
memory change its actual decision. This round tests that goal for the explicit agent
memory of round 3.2 (store + operators, template encoder), without model inference, as
Astra advised: the functional core first; the language interface (LM encoder of free
wordings, LM reader agents) is the next extension and its limited reach stays stated.

## Environment (episodic_lab/env.py)

Six places, eight objects, three people plus the agent ("You"). One experience per day,
14 days, given as a sentence: what the agent saw (someone hid / left / put an object
somewhere; someone was at a place), what it did itself (put an object somewhere; went
somewhere), what someone did to it (gave it an object). Then the goal and the current
observation: "You are in the hall. Goal: ... You can go to: <six places>." The
environment knows the true state and scores the action (going to a place).

Kinds (40 pairs each, series `env-m3`):
- **hidden**: the agent saw a person hide/leave/put the object at P; goal "Find the X".
- **moved**: the object was placed at P_old, later the agent put it at P; the later
  episode decides.
- **giver**: a person gave the agent the object; later the agent saw that person at P;
  goal "Find the person who gave you the X" (two episodes linked through the person; a
  second person gave another object).

Pairs: two worlds identical in every experience except the critical episode, identical
at decision time (same goal, same observation, same options); the critical episode makes
a different place correct. Distractors re-use people, places and objects (bindings).

## Agent and memory boundary (episodic_lab/env_agent.py, bench/m3/run_round33.py)

Experience phase: each world's experiences are encoded ONCE into an append-only, chained,
sealed store file; every intervention is derived from that encoded store and written as
a new sealed store. Decision phase: for EVERY case (world x intervention) a new isolated
interpreter (`python -I`) receives only that case's store path, seal and decision text
and decides from the store with explicit operators (latest placing of the object; the
unique "gave" episode, then the giver's latest appearance); it returns the action and the
operator result (status, record ids, trace), which is kept. Without a supported memory
answer it explores: it goes to the first listed place (memory-free, identical in both
worlds of a pair). The environment scores the actions afterwards.

## Reference path (episodic_lab/env_reference.py)

Interventions are planned, and their predictions computed, on the environment side from
the generator's structured events (`truth_content`), with this module's own counterfactual
application and decision rules. It uses neither the store, nor its operators, nor the
experience encoder; a test injects an encoding error and shows that the prediction stays
the same while the agent's decision changes.

## Interventions (on the memory only) and predictions (from the environment's events)

| intervention | memory content | predicted action |
|---|---|---|
| intact | all experiences | the true place |
| none | empty | exploration place |
| random | equal number of irrelevant episodes, same vocabulary | exploration place |
| swapped_binding | hidden/moved: the critical episode exchanges its place with another object's placing episode; giver: the two "gave" episodes exchange their person | the place implied by the swapped binding |
| relevant_removed | the critical episode deleted | hidden: exploration; moved: the earlier place; giver: the giver's last appearance before |
| irrelevant_removed | one distractor deleted that mentions neither the object nor the people involved | the true place |

## Two results: VERDICT and MILESTONE

VERDICT (COMPLETE / INCOMPLETE) = the evaluation is complete and reproducible: schema,
identity, provenance (request hash, code commit of the run), pair design, the collector's
full re-run reproduces every row, cut-off and changed stores are refused.

MILESTONE (PASS / FAIL) = all criteria below, in every kind; the workflow fails unless
VERDICT is COMPLETE and MILESTONE is PASS.

1. every planned case of intact, none, random and relevant_removed is available (80 per
   kind); swapped_binding and irrelevant_removed in >= 90% of the planned cases;
   informative cases (prediction differs from the truth) >= 60% of the planned cases for
   swapped_binding and relevant_removed;
2. intact: success 1.0 and pair success (both worlds right) 1.0;
3. none and random: pair success 0 - this follows from the FIXED, deterministic
   exploration policy (same action in both worlds, different correct places); for
   stochastic LM agents later it holds only with coupled random draws;
4. swapped_binding and relevant_removed: the action equals the prediction in >= 0.95 of
   the informative cases;
5. irrelevant_removed: success 1.0.

Status of these criteria: they were written after a local development run of the same
design (round 3.3 v1) and fixed before the GitHub run; the GitHub run is therefore a
reproduction and integrity check of a locally known result, not a test on unseen data.
Evaluation units are the pairs (40 per kind): the 1,440 decisions are repeated
conditions of the same worlds, so any later statistical statement treats pairs, not
decisions, as independent units. The column "share decided via memory branch" only
describes the policy; the causal evidence is the intervention pattern. The collector also
re-runs the two store-integrity probes and compares them with the stored result
(after Astra's v2 review; her ideas adopted before the run).

## What a pass shows, and what it does not

It shows, for an explicit, externally implemented agent memory: single experiences kept
across a restart in a declared memory, used for a later-announced goal, with the
behaviour depending causally and specifically on the relevant memory (swap moves the
decision in the predicted direction, irrelevant edits do nothing). It does not show:
robustness to free wording (the encoder is the template parser), an LM agent's ability
to use the memory, source monitoring with reports and corrections, or scale. These are
the extensions of round 3.4, one at a time. First extension (Astra's proposal, adopted):
a historical goal chosen after storage with an identical final state - both worlds end
with the same object and person locations and differ only in an earlier placing episode;
the goal is either "find X now" (same action in both worlds) or a historical one such as
"go to where X was first put" (different actions); removing or swapping the earlier
episode must change only the historical decision; plus a baseline that stores only the
current state (latest place per object/person and the relations the current goals need),
all systems with the same experiences and their stored information disclosed. Then the
frozen LM encoder on held-out wordings with unchanged operators, reports and corrections,
longer histories. The random control will add plausible wrong bindings with the same
target entities.

## Result (GitHub run 39073059273, code commit f230b7d)

Review: Astra APPROVE for v2 (`reviews/2026-10-17_r32v3_r33v2_astra.txt`), Claude lead
review APPROVE; her improvement ideas for the collector and wording were adopted before
the run. VERDICT COMPLETE, MILESTONE PASS (results branch, `round33/run_39073059273_1/`):
all 1,440 planned cases available (40 pairs per kind, every case in its own fresh
process); intact success and pair success 1.00 in all three kinds; no memory and random
memory pair success 0.00; swapped binding and relevant removal: action as predicted in
1.00 of the informative cases (hidden 80 and 63, moved 80 and 80, giver 65 and 67);
irrelevant removal success 1.00; cut-off and changed stores refused. As stated above, the
criteria were fixed after a local development run: this is a reproduction and integrity
check, a limited functional proof for this explicit memory implementation, not a test on
unseen data. The round 3.2 v4 operator changes (unknown fields) leave every row of this
run unchanged (checked by a local re-run on the v4 code: rows, summary and integrity
flags identical), because the environment's records have no unknown fields.
