# Claude's strategy analysis after pilot M2 (written before Astra's answer; sealed until both are in)

## Supported conclusions
1. Reading is not the bottleneck: with exactly its evidence, qwen2.5-0.5b answers recall/state/when ~perfectly (O1 E2 1.00, E3b 1.00/0.97, E4 0.97).
2. Selection among similar episodes and abstention are the bottleneck: all 40 episodes in context (~1k tokens) -> E2 0.29, in-world false recall on binding lures 0.99; three confusable notes -> 0.99.
3. The A/B format does not measure temporal order for these models (constant letter, also with both dated episodes present).
4. The benchmark is solved 100% by S0 (regex + table).

## Not supported
- "LLMs cannot do episodic memory" / "context windows fail": only shows that 0.5B readers fail at conjunctive search over ~40 near-duplicate sentences; a larger reader would likely pass at this size.
- Any statement about weights-based memory (nothing run yet).
- Why the model confabulates (four hypotheses, none isolated).

## Thinking errors
D1 Benchmark ceiling: templated text means S0 = 100%. Any A3 that parses templates is S0 again; the benchmark cannot separate episodic memory from a database. Missing: free wording, pronouns/coreference, relative time ("two days later"), distractor content, synonym cues, scale beyond the context window (hundreds to thousands of episodes).
D2 Wrong place for binding and abstention: we test whether a tiny LM binds and abstains inside its prompt. In brain and in working ML systems binding is done by an index (hippocampus / conjunctive key), abstention by a familiarity/match decision, the reader only reads. A3 must take both away from the LM.
D3 Weak baseline: pilot gate = gain over A0, which is 0 by construction (no information). Gains must be measured against A1 and A2 (and S0 as ceiling).
D4 Generative scoring of tiny models measures instruction following and position bias: score answers by log-likelihood over the candidate set plus "none" (multiple-choice style), A/B both orders and averaged (contextual calibration); keep generation as secondary.
D5 Definition: the episodes are a narrated third-person world. Episodic memory is memory of the system's OWN experiences (what did I do / see / who told me, when, in which conversation). E4 "source" asks for a day; real source memory is "from whom / in which context did I learn it". Missing criteria: sequence recall ("what happened after X"), context-driven spontaneous recall (no explicit question cue), source monitoring (seen vs told), forgetting/consolidation dynamics.
D6 Pace: infrastructure and format details took most of the time; reviews per fix instead of per decision.

## Plan (fastest path)
Step 1 (A3 "hippocampal index", on the current benchmark, ~1 day): encoding = one pass per episode into a frame (who, partner, action, object, place, time, source) + raw text + position; extraction by the LM (prompted slot filling) with the regex only as a control; retrieval = parse cue into a partial frame, conjunctive match with pattern completion; abstain when no stored frame matches all cue features (decision outside the LM); time/state/decision logic over frames; LM reads only the retrieved episode(s). Likelihood scoring. Arms: A1, A2 (BM25 top-k), A3, A3 ablations (no abstention rule, no time, LM-binding instead of index), random retrieval, misbound store. Expected: A3 near S0; this proves the mechanism and exposes the benchmark ceiling.
Step 2 (benchmark v2 "hard"): free wording (larger grammar + LM paraphrases, checked for meaning), pronouns, relative time, distractor sentences, synonym cues, 500-5,000 episodes; acceptance rule: the template regex S0 must fall clearly (< 0.5), A1 must not fit the context. Then A3 (LM extraction) vs A2 vs truncated A1.
Step 3 (own-experience track): episodes are the agent's own interaction logs (turns, tool calls, outcomes); questions about its own past; source monitoring (told vs observed vs inferred).
Step 4: P1/C1 (single-presentation weight updates, consolidation from the A3 store by replay) as the research question on top of a working A3, not as the first route.

## What would count as episodic memory (and not a database with an LM in front)
- Encoding from raw experience without a hand-written schema parser (the extractor is learned/prompted, robust to wording).
- Retrieval from partial, paraphrased or contextual cues (pattern completion), not exact keys.
- Correct abstention on binding lures and familiarity-only cues.
- Temporal context: order, sequence, state at time, from relative time expressions.
- Source monitoring on its own experiences.
- Behavioural use in later decisions; retention under interference at a scale beyond the context.
- Honest limit: autonoetic/phenomenal aspects (Tulving) are not testable behaviourally; the claim stays functional.
