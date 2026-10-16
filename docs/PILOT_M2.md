# Milestone 2 pilot - base run (v0) and the reason for variant v1

Exploratory. Run 38956502610 on commit 8e84108, results branch
`pilot/run_38956502610_1` (VERDICT COMPLETE, 60/60 cells, 43 min). Series `pilot-m2`,
worlds 0-4, both overlap conditions, arms A0, A1, O1, four pinned models. Numbers are
means over the five worlds and both conditions, final test, unless stated otherwise.

## Results

| model | O1 positives (selection) | A1 E2 | A0 E2 | A1-A0 E2 per world | A1 E5 false recall | O1 E5 false recall |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 0.844 (min world 0.826) | 0.28 | 0.00 | 0.19 0.20 0.32 0.35 0.34 | 0.99 | 0.97 |
| qwen3-0.6b | 0.557 | 0.23 | 0.00 | 0.38 0.15 0.29 0.12 0.24 | 0.34 | 0.68 |
| smollm2-360m | 0.298 | 0.01 | 0.00 | 0.06 0 0 0 0 | 0.17 | 0.01 |
| smollm2-135m | 0.109 | 0.00 | 0.00 | 0 0 0 0 0 | 0.06 | 0.06 |

- Selection rule (protocol section 5): qwen2.5-0.5b is the smallest model with O1
  accuracy on positive items >= 0.8 in v0. This holds for v0 only; the rule is applied
  anew to v1 over all four candidates.
- With its evidence in the prompt (O1), qwen2.5-0.5b answers recall, state and source
  items almost perfectly (E2 0.99, E3b at_day 1.00, latest 0.97, E4 1.00; E7 0.56).
- With all 40 episodes in the prompt (A1) it falls to E2 0.28 and claims an in-world
  value for 99% of the binding lures. A1 exceeds the E2 margin in the exploratory mean
  (+0.28; per world +0.19 to +0.35), which is no confirmatory pass with five worlds, and
  it misses the false-recall tolerance (0.10) by far. With only three confusable notes
  (O1 lures) it still claims a value for 97% of the lures.
- Observed: massive in-world false recall on binding lures. Not shown: why. Hypotheses,
  not isolated by this run: the model does not keep the bindings of the episodes apart;
  it does not follow the instruction for the negative case; it fails at comparing
  several conditions of a cue at once; or the answer decision itself is biased towards
  naming a value. O1's E5 is no clean binding diagnosis (note-count signal, protocol
  section 4). The results motivate a structured store (A3, milestone 3); whether A3
  helps has to be shown by the later comparison.
- E6 cannot be read from this run (A1 retention 0.27 at phase 1, 0.24 / 0.21 at the
  final test in the high / low condition, at a low level).

## Two measurement artefacts of the instruction (cause of variant v1)

1. **E3a is uninformative.** Qwen2.5, Qwen3 and SmolLM2-360M answer "A" to 97-100% of
   the A/B questions in ALL three arms, also with both episodes in the prompt (O1). The
   gold letter of each pair is drawn at random, so a constant "A" scores near 0.5 (the
   observed E3a values are 0.50-0.53) and measures nothing. Because it happens
   with the evidence present, it is a position preference, likely reinforced by the
   example "A" in the instruction. SmolLM2-135M answers "B" in O1 (97%).
2. **Example values are copied.** The instruction's examples ("Tom Hill", "Elm Court",
   "red door", "Day 3") are the whole answer in up to 45% of the non-choice answers
   (SmolLM2-360M A0 0.45, Qwen3 O1 0.23, Qwen2.5 A0 0.20); 58 of Qwen3's 64 O1 errors on
   E2 are a copied example ("red door" 48 times). Hypothesis: without the examples
   Qwen3's O1 value would be higher; whether removing them changes the performance is
   what v1 tests.

## Variant v1 (committed before it runs; episodic_lab/variants.py)

- Instruction without any example value (FORMAT_V1: "the person's full name as written
  in the notes", ..., "the letter of the correct option, A or B").
- Every E3a pair is also asked with (A) and (B) swapped (same template, no further
  random draws: every other item is identical to v0). Item accuracy stays reported; in
  addition E3a "pairs" = share of pairs answered correctly in both orders. Baselines:
  a constant letter scores 0 pairs (and exactly 0.5 item accuracy); independent uniform
  guessing 0.25; "the earlier told event happened first" (or "the later told") 0.5,
  because half of the pairs are aligned and half inverted. A positive pair score alone
  therefore shows no understanding of time; it has to exceed 0.5 clearly.
- Model selection in v1: the two orientations of an E3a pair count 1/2 each, so E3a
  keeps its v0 weight and the extra questions do not change the rule (collector
  `selection_value`; without the halving 34/40 = 0.85 could fall to 38/48 = 0.79 with
  unchanged performance on the old items).
- Counts: `counts["E3a"]` stays the number of pairs, `counts["E3a_asked"]` is the number
  of E3a questions asked (twice the pairs), `counts["order_swapped"]` the added ones.
- After v1: v0-v1 differences are reported per world (paired); orientations, test points
  and overlap conditions are no independent worlds, uncertainty stays over five worlds.
- Everything else unchanged: same series and worlds (paired with v0), models, arms,
  scoring grammar, collector checks. This is variant 1 of 3 for A0, A1 and O1.

## Variant v1 results (run 38971676737, commit 9ed41e1)

VERDICT COMPLETE, 60/60 cells. Same worlds as v0; the comparison below uses only the
items common to v0 and v1 (final test, mean over the five worlds), so it isolates the
instruction change from the added E3a orientations.

- **Copied examples: gone.** Example echo fell to 0.00 in every model and arm (v0: up to
  0.44).
- **Qwen3 hypothesis supported (exploratory).** Qwen3 O1 E2 0.54 -> 0.91, higher in every
  world (0.75->0.88, 0.50->0.90, 0.53->1.00, 0.38->0.85, 0.53->0.95); E3b 0.46 -> 0.75.
  SmolLM2-360M O1 E2 0.03 -> 0.49. Qwen2.5 was hardly affected (O1 E2 0.99 -> 1.00, A1
  0.28 -> 0.29).
- **E3a A/B preference: NOT an instruction artefact.** Qwen2.5 and Qwen3 still answer
  "A" to 99-100% of the A/B questions in all arms, also with both dated episodes in the
  prompt (O1). Pair score 0.00 for every Qwen arm, at most 0.05 elsewhere (baselines:
  constant 0, guessing 0.25, told-order 0.5). The A/B letter format does not measure
  temporal order for these models at all.
- **Binding lures: unchanged.** Qwen2.5 in-world false recall A1 0.99, O1 0.99; Qwen3 A1
  0.35, O1 0.85 (v0 0.68: fewer "other" answers, more named values). A0 abstains more
  (Qwen2.5 A0 E5 0.46 -> 0.81, Qwen3 0.89 -> 1.00).
- **E7 for Qwen2.5 O1 0.56 -> 0.43** (find items mostly wrong: 15 of 38 correct). Noted,
  not explained.

Model selection v1 (rule applied anew; E3a orientations 1/2): qwen2.5-0.5b 0.825 (worlds
0.813, 0.795, 0.880, 0.814, 0.825), qwen3-0.6b 0.713, smollm2-360m 0.547, smollm2-135m
0.131. qwen2.5-0.5b stays the smallest model above 0.8, in both v0 and v1, with a thin
margin (one world below 0.8); E3a, constant at 0.5 for it, pulls the value down.

Reading (exploratory): the instruction artefact is fixed; the position preference on A/B
questions and the confabulation on binding lures are properties of these models under
this task, not of the example values. A different E3a answer format (naming a content
detail of the earlier event instead of a letter, still asked in both orders) is the
candidate for variant v2, to be decided with milestone 3.
