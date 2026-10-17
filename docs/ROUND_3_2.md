# Round 3.2 - agent memory from S0 (design, for review before building)

Uncertainty removed: does an explicit episodic memory work as an agent memory (survives
a restart, answers from its own records, abstains correctly), and does a gain come from
retrieval, from the operators, or from both? Ends with one run on the development
worlds; the next round (3.3, action environment) starts from its result.

Basis: round 3.1 (docs/ROUND_3_1.md): the reader extracts single details reliably
(1.00 in both channels, both models) and fails at comparison, conjunctive matching with
abstention, linking and source filtering (0.05-0.53). So: the LM reads and extracts; the
memory compares, matches, links, filters and abstains.

## 1. Store (episodic_lab/memory.py, evolved from S0)

Append-only JSON-lines file; one record per episode, written once and flushed; never
rewritten. Record fields:

| group | fields |
|---|---|
| identity | `id` (random), `stream` (whose experience), `seq` (record order) |
| time | `event_day` (time of the reported event, may be missing), `seq` is the record time |
| content | `actor`, `partner`, `action`, `object`, `place` |
| source | `kind` (observed / own_action / reported / inferred), `by` (who reported) |
| original | `text` (the input exactly as received) |
| relations | list of `{type: corrects / same_event / derived_from, target: id}` |
| encoding | `encoder` ("regex" or "lm:<model>"), per-slot raw extractor output |

Current state (e.g. latest place of a person) is always derived from the records at query
time, never stored, so history cannot be overwritten and no view can drift.

## 2. Encoders (where the LM is used)

- **regex** (S0's template parser): control and ceiling.
- **lm**: slot filling by single-detail questions to the reader, the skill that round 3.1
  showed to be reliable: day, main person, other person (or none), action, object,
  place; one fresh chat per slot, v1 instruction, strict grammar with open values.
  Reported: accuracy per slot against the generator's truth (encoding-stage errors).
  Rule: if every slot is >= 0.95, the lm encoder becomes the main encoder from round 3.3
  on (the template parser must not be needed once wordings change in round 3.4).

## 3. Operators (explicit, with trace)

`find(cue)`, `compare_time(cue_a, cue_b)`, `state_at(person, day)`, `latest(person)`,
`link(cue_identifying_person, cue_answer)`, `by_source(kind, by)`. Every result carries
the episode ids used and the operation sequence. Negative results are three-valued:
`none_in_scope` (no matching event in a fully observed scope), `no_observation`
(nothing recorded about the cue's subject), `ambiguous` (several matches with different
answers). Only `none_in_scope` maps to "none" in the closed benchmark; the other two are
reported separately.

## 4. Comparison on the template benchmark

Question parsing into a structured query is shared by all cells (the template question
parser; an LM cue parser is a round 3.4 extension), so no cell gets a more precise query
than another.

| cell | retrieval | processing |
|---|---|---|
| lex+reader | BM25 over the raw texts, top 3 | the LM reads the retrieved notes and answers |
| struct+reader | conjunctive match over the records (pattern completion: most cue features matched), up to 3 | same LM reader |
| lex+ops | BM25 top 3 | explicit operators over the records of the retrieved episodes |
| struct+ops | conjunctive match | explicit operators (the full system) |
| reasoning reader | as struct+reader, with the LM in a reasoning mode | only if round 3.1b found a sub-skill >= 0.95 |

Controls: no memory (A0), all in prompt (A1), S0 reference, random retrieval (3 random
episodes) + operators, misbound store (participants, objects and places permuted across
records, marginals kept) + operators, encoder regex vs lm for struct+ops.

Error localisation per answer: encoding (record vs truth), retrieval (were all target
episodes retrieved), operation (result given the retrieved records), output/abstention.

## 5. Restart test (completion point)

Process 1 receives the episodes one by one and writes the store, then exits. Process 2 is
a fresh interpreter that receives only the store path, the fixed code and the public
questions (no world file, no chat history) and answers. Passed if: (a) process 2's
answers equal an in-process run on the same store; (b) with an empty store process 2
loses all episode-dependent accuracy (falls to the no-memory level); (c) a store file
with one byte changed is detected (per-record SHA-256 chain) and refused.

## 6. Worlds and models

Development series `dev-m3`, 10 new worlds (both overlap conditions), plus the five
`pilot-m2` worlds for paired comparison with the pilot's A0/A1/O1. Reader and lm encoder:
qwen2.5-0.5b (selected model). Expected on the template benchmark: struct+ops near 1.0
with the regex encoder; a working prototype, not a surprising finding. The informative
numbers are the cell differences, the lm encoder accuracy and the restart test.

## 7. Reported

Per cell and criterion: accuracy, lure false recall, the three negative kinds, error
stage; encoder slot accuracy; restart test (a)-(c); cost per cell (LM calls, tokens,
seconds).
