# Round 3.3 - paired action worlds with causal memory interventions (pre-registered)

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

Experience phase: every experience is encoded into an append-only, chained, sealed store
file. Decision phase: one fresh isolated interpreter receives only (store path, seal,
decision) and decides from the store with explicit operators (latest placing of the
object; the unique "gave" episode, then the giver's latest appearance). Without a
supported memory answer it explores: it goes to the first listed place (memory-free,
identical in both worlds of a pair). The environment scores the actions afterwards.

## Interventions (on the memory only) and predictions (from the environment's events)

| intervention | memory content | predicted action |
|---|---|---|
| intact | all experiences | the true place |
| none | empty | exploration place |
| random | equal number of irrelevant episodes, same vocabulary | exploration place |
| swapped_binding | hidden/moved: the critical episode exchanges its place with another object's placing episode; giver: the two "gave" episodes exchange their person | the place implied by the swapped binding |
| relevant_removed | the critical episode deleted | hidden: exploration; moved: the earlier place; giver: the giver's last appearance before |
| irrelevant_removed | one distractor deleted that mentions neither the object nor the people involved | the true place |

## Pass criteria (fixed now, all kinds)

1. intact: success 1.0 and pair success (both worlds right) 1.0;
2. none and random: pair success 0 (a memory-free agent cannot be right in both worlds);
3. swapped_binding and relevant_removed: the action equals the prediction in >= 0.95 of
   the cases where the prediction differs from the truth;
4. irrelevant_removed: success 1.0;
5. the decision process refuses a cut-off and a changed store.

The collector re-runs the whole deterministic job and must reproduce every row.

## What a pass shows, and what it does not

It shows, for an explicit, externally implemented agent memory: single experiences kept
across a restart in a declared memory, used for a later-announced goal, with the
behaviour depending causally and specifically on the relevant memory (swap moves the
decision in the predicted direction, irrelevant edits do nothing). It does not show:
robustness to free wording (the encoder is the template parser), an LM agent's ability
to use the memory, source monitoring with reports and corrections, or scale. These are
the extensions of round 3.4, one at a time.
