# Round 3.4 step 1 - history goals with an identical final state (v1, Astra APPROVE)

Uncertainty removed: in round 3.3 the object goals asked "where is X now?" (a memory that
keeps only the current state - latest place per object and person - would solve them as
well), and the giver goal already linked a historical episode (who gave X) to a current
one. New here: historical PLACE information that matters although the current state of
the paired worlds is identical, with intervention effects selective for different goals.
Episodic means that the history of single events is kept and can be used for a goal
chosen later. This step tests exactly that, as Astra proposed in her reviews of round
3.3 (`reviews/2026-10-17_r33_astra.txt`, `reviews/2026-10-17_r32v3_r33v2_astra.txt`).
Review of v1: `reviews/2026-10-18_r34v1_astra.txt` (APPROVE; her wording, test and scope
ideas adopted before the run, see the end of this document):

1. goal-independent storage: one store per world, written before any goal is handed to
   the agent, used unchanged for the different goals handed over afterwards (the
   generator creates all goal texts in advance; the agent sees none while storing);
2. paired worlds whose FINAL STATE is identical (every object's last place and every
   person's last appearance), checked explicitly; they differ only in an OLD episode;
3. changing the old episode changes the historical decision as predicted and leaves the
   current decision unchanged; changing the latest episode does the opposite (double
   dissociation);
4. a current-state-only baseline with the same experiences, the same encoder and the
   same decision rules for the goals it can answer, its stored information disclosed.

Ends with one GitHub run. No model inference (the language interface - frozen LM encoder
on held-out wordings - is the next step and keeps its limits stated until then).

## Environment (episodic_lab/history_env.py)

The round 3.3 world (6 places, 8 objects, 3 people plus "You", 14 days, one experience
per day, the same sentence templates and distractors). Two kinds, 40 pairs each, series
`hist-m34`:

- **object**: the target object is placed three times: day d1 "you put the X at P1"
  (the OLD, critical episode: P1 differs between world A and B), day d2 a person
  hides/leaves/puts it at P2, day d3 another person at F (the latest). P1(A), P1(B), P2,
  F are four different places. Distractors never involve the target object.
- **person**: the target person is seen three times: day d1 at Q1 (critical, differs
  between A and B), d2 at Q2, d3 at F. Distractor events that would involve the target
  person become "you went to <place>".

In both kinds one further day holds an irrelevant episode of the same type as the old one
(another person puts another object somewhere / another person is seen somewhere) at a
place that differs from the old place in both worlds: the swap partner of the
old_swapped intervention.

Goals, all three asked for every stored world (the store is written first; the goals
are handed over one by one afterwards and are never seen while encoding):

| goal | object kind | person kind | truth | A vs B |
|---|---|---|---|---|
| current | "Find the X." | "Find P." | latest place F | same |
| first | "Go to where the X was first placed." | "Go to where you first saw P." | P1 / Q1 | different |
| previous | "Go to where the X was before it was last placed." | "Go to where you saw P before you last saw them." | P2 / Q2 | same |

Decision text as in 3.3 ("You are in the hall. Goal: ... You can go to: <six places>.").

## Systems

- **episodic** (episodic_lab/history_agent.py): the round 3.3 agent memory (append-only,
  chained, sealed store, template encoder); the operators order the target's records by
  event day (placings of the object / appearances of the person) and take the latest,
  the first or the one before the latest; an undated record or two records on one day
  make the answer ambiguous; no supported answer -> explore (first listed place).
- **state_only** (baseline): reads the same experiences with the same encoder and keeps
  only the current state: last place per object (placing events) and last appearance per
  person. Stored information: one place per object and per person (disclosed per world).
  Decides the current goal from it like the episodic agent; for a historical goal it has
  no information and explores. Because the final state is identical in both worlds, its
  state - and therefore every decision - is identical in A and B (checked).

Every decision (system x world x intervention x goal) is taken by its own fresh isolated
interpreter that receives only one store (or state file), its seal and the decision text.

## Interventions (episodic memory only) and predictions

Predictions come from an independent reference (episodic_lab/history_reference.py) that
plans the interventions on the generator's structured events, applies them with its own
code and decides with its own rules; it uses neither the store, nor the operators, nor
the encoder. The memory side applies the same plan to the actually encoded store.

| intervention | memory change | predicted change |
|---|---|---|
| intact | none | - |
| none | empty memory | everything explores |
| old_removed | the old episode (d1) deleted | first -> P2/Q2; current and previous unchanged |
| old_swapped | the old episode exchanges its place with an irrelevant episode of the same type (another object's placing / another person's sighting) | first -> that place; current and previous unchanged |
| last_removed | the latest episode (d3) deleted | current -> P2/Q2, previous -> P1/Q1; first unchanged |
| irrelevant_removed | one episode mentioning neither target deleted | nothing changes |

## Two results: VERDICT and MILESTONE

VERDICT (COMPLETE / INCOMPLETE): schema, identity, provenance (request hash, the run's
code commit); design (in every pair: identical final state of objects and people,
identical decision texts, current and previous truths equal, first truths different, the
baseline's state identical in A and B); one store per world and intervention, used for
all three goals (same seal in every row of that world and intervention); the collector's
full re-run reproduces every row; cut-off and changed stores refused.

MILESTONE (PASS / FAIL), criteria fixed in this document BEFORE the first run of the code
(locally or on GitHub; the system is deterministic, so a local run would reveal the
result - the GitHub run then reproduces it); per kind:

1. availability: every planned case of intact, none, old_removed, last_removed and
   irrelevant_removed is available (80 per goal); old_swapped in >= 90% of the planned
   cases; informative cases (prediction differs from the truth) >= 60% of the planned
   cases for the first goal under old_removed and old_swapped and for the current goal
   under last_removed;
2. episodic, intact: success 1.0 for all three goals and pair success 1.0 for the first
   goal;
3. state_only: success 1.0 for the current goal and pair success 0.0 for the first goal;
4. episodic, none: pair success 0.0 for the first goal;
5. old_removed and old_swapped: first-goal action as predicted in >= 0.95 of the
   informative cases; current- and previous-goal actions equal to the intact action of
   the same world in 1.0 of the cases;
6. last_removed: current-goal action as predicted in >= 0.95 of the informative cases;
   first-goal action equal to the intact action in 1.0 of the cases;
7. irrelevant_removed: success 1.0 for all three goals.

Status note (v1, before the GitHub run): the unit test of the criteria (series
`hist-test`) failed on availability, and a count of the planned interventions over the
run series showed that the person kind lacked a swap partner in 10 of 80 planned cases
(old_swapped available in 87.5% < 90%; a first local run was stopped before its end). This was a design gap of the generator, fixed
there (the guaranteed same-type irrelevant episode above, now 80 of 80 in both kinds);
no criterion was changed.

## What a pass shows, and what it does not

It shows, for the explicit agent memory: the store keeps event history that a
current-state memory with the same experiences does not have; one goal-independently
written store serves different goals handed over later; the old and the latest episode control different
decisions (double dissociation), as predicted by an independent reference. The result is
expected by construction for a correct rule-based implementation; the round checks that
the implementation, the design (identical final state) and the evaluation hold. It does
not show robustness to free wording, an LM's ability to write or use the memory, reports
and corrections, or scale. Nor does it show that a full event history is needed: a small
cache of the first, the previous and the latest place per entity would answer these three
fixed goals as well (Astra); that baseline, and context-dependent historical queries that
such a cache cannot anticipate, belong to a later step. Statistical statements, if any,
treat pairs as units.

Before the LM encoder is used with these operators (round 3.4 step 2), the history
operators must handle unknown fields like the round 3.2 v4 operators: `target_records`
matches exactly, so a record with an unknown actor that could be an earlier sighting of
the person would be skipped; `possible()` and the declared unknowns must also govern the
first and previous positions. With the error-free template records of this step that
case cannot occur.
