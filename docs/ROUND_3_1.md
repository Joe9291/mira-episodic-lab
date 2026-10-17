# Round 3.1 - diagnostic battery (pre-registered with the code that runs it)

Purpose (docs/STRATEGY.md section 3): which reader sub-skills can a small model carry
itself, and which must the prototype memory do with explicit operators? Uncertainty
removed: the split between model and operators in round 3.2. Ends after this one run;
no prompt variants without a stated purpose.

- Models: qwen2.5-0.5b, qwen3-0.6b (pinned). Instruction v1 (no example values).
- Battery `episodic_lab/diagnostics.py`, seed "diag-m3", 121 cases, notes in the prompt:
  S1 extract (20: 5 place, 5 object, 5 person, 5 day), S2 compare (10 event pairs, each
  asked in both orders in a content form "which object first" and a letter form A/B =
  40), S3 binding (10 positive, 10 lure; always 3 notes, each matching a pair of cue
  details), S4 link (20; ambiguous without the link), S5 source (7 observed, 7 reported,
  7 report that does not exist; always the same 2 notes).
- Gold answers by construction, re-derived in tests by an independent solver.
- Channels: `free` = greedy text, strict answer grammar (as in the pilot); `cand` = the
  allowed answer with the highest log-probability as the complete reply (answer tokens
  plus end-of-turn token), candidates = all values of the asked type in the notes, one
  value not in the notes, and "none" where abstention is valid (not in S2).
- Development target: 0.95 per sub-skill and channel (not confirmatory; 20 cases).
- Decision rules, fixed now:
  - a sub-skill at >= 0.95 in a channel: the reader may carry it in round 3.2 through
    that channel;
  - free < 0.95 but cand >= 0.95: an output/interface problem; round 3.2 uses the
    candidate channel for it;
  - both < 0.95 for S2, S3, S4 or S5: an explicit operator (temporal comparison,
    conjunctive match with abstention, linking, source filter) does it in round 3.2;
  - both < 0.95 for S1 (extraction from a present episode): the language encoder is a
    problem of its own and is reported as such before round 3.2 relies on the reader.
- Reported in addition: per kind (S3 positive/lure, S5 observed/reported/missing), S2
  pair scores per form (both orders correct; constant letter 0, guessing 0.25).
- Five cases per model are shown to Joe for an independent check.

## Result (run 39016623785, commit 8b89d17, VERDICT COMPLETE)

| sub-skill | qwen2.5 free / cand | qwen3 free / cand | decision (rules above) |
|---|---|---|---|
| S1 extract | 1.00 / 1.00 | 1.00 / 1.00 | reader carries it |
| S2 compare | 0.45 / 0.45 (pairs 0) | 0.53 / 0.50 (content pairs free 0.50, cand 0.40; letter 0) | explicit operator |
| S3 binding | 0.40 / 0.30 (lures 0.00, positives 0.80 / 0.60) | 0.35 / 0.40 (lures 0.10 / 0.20) | explicit operator (conjunctive match + abstention) |
| S4 link | 0.05 / 0.05 | 0.05 / 0.10 | explicit operator |
| S5 source | 0.52 / 0.52 (missing 0.00) | 0.48 / 0.48 (missing 0.29) | explicit operator (source filter + abstention) |

Patterns: in S2 Qwen2.5 picks the object named first in the question in 18 of 20
content items and "A" in 20 of 20 letter items; Qwen3's content pair score (0.50 free)
equals the told-order baseline. In S4 Qwen2.5 answers the place of the episode named in
the relative clause in 19 of 20 cases; Qwen3 answers "none" in 12. The candidate
procedure used here does not remove the failures; that does not prove that output
format, candidate scoring and calibration play no part.

Consequence for round 3.2: the model is used as a reader for extraction only (single
episode, single detail); comparison, conjunctive matching with abstention, linking and
source filtering are explicit operators of the memory.

Independent check by Joe: the first case of every sub-skill (fixed rule), with both
models' answers.

## Round 3.1b - reasoning probe (pre-registered with its code)

Gap in round 3.1: Qwen3's thinking mode was switched off and no step-by-step reasoning
was allowed, so "the reader cannot compare / bind / link" may only hold for direct
answers. Uncertainty removed: whether explicit reasoning lets a small reader carry
S2-S5. It does not block round 3.2 (operators are used there in any case); it decides
whether an LM-reasoning reader is added to the round 3.2 comparison.

- Same battery cases S2-S5 (101 cases), same strict grammar, free channel only.
- think: Qwen3-0.6B thinking mode, recommended sampling (temperature 0.6, top-p 0.95,
  top-k 20), seeded per case (reproducible), up to 1024 new tokens; answer = text after
  the last </think>; a reply without </think> counts as cut off ("other").
- cot: Qwen3-0.6B (thinking off) and Qwen2.5-0.5B with a step-by-step instruction,
  greedy, up to 384 new tokens; answer = text after the last "Answer:".
- Reported in addition: new tokens per answer, share of cut-off replies, seconds.
- Rule: a sub-skill at >= 0.95 with reasoning is recorded as "LM reasoning can carry it at
  this cost" and that reader becomes one more cell of the round 3.2 comparison; the
  prototype still uses the explicit operator. Below 0.95: no further reasoning variants.
- The direct battery workflow re-runs once on this commit because its code changed (the
  summary function now handles runs without the candidate channel); its numbers must be
  identical to run 39016623785 (regression check).

### Round 3.1b result (run 39018909077, commit a5a680e, VERDICT COMPLETE)

| sub-skill | Qwen3 think | Qwen3 cot | Qwen2.5 cot (registered / post-hoc lenient) |
|---|---|---|---|
| S2 compare | **0.82** (content 0.90, pairs 0.90; letter 0.75, pairs 0.60) | 0.45 | 0.00 / 0.45 |
| S3 binding | **0.75** (lures 0.60, positives 0.90) | 0.40 (lures 0.10) | 0.00 / 0.10 |
| S4 link | **0.60** | 0.00 | 0.00 / 0.15 |
| S5 source | **0.95** (missing 1.00, observed 0.86, reported 1.00) | 0.62 | 0.00 / 0.38 |

- Qwen3's thinking configuration (thinking mode, its recommended sampling and a 1024-token
  budget, changed together) changes the picture: every sub-skill rises strongly over
  its direct value (S2 0.53 -> 0.82, S3 0.35 -> 0.75, S4 0.05 -> 0.60, S5 0.48 -> 0.95).
  Cost: 246 new tokens per answer on average, all 101 replies finished within 1024
  tokens, 38 s per answer on the runner (3840 s for 101 cases), versus about 1 s direct.
- An instructed step-by-step prompt does not reproduce this: Qwen3 cot stays near its
  direct values. Qwen2.5 cot scores 0.00 under the registered extraction rule because it
  almost never wrote the required "Answer:" line (format failure, 100 of 101 "other");
  a post-hoc lenient reading of its last line (not used for any decision) gives 0.10-0.45.
- S5 reaches the registered target with 20 of 21 cases; the observed-source cases alone
  are 6 of 7. This justifies a limited further test, not a general reliability claim.
- Decision by the registered rule: S5 meets 0.95 with thinking -> "LM reasoning can carry
  source filtering at about 38 s per answer". (Round 3.2 v1 planned a thinking-reader
  cell; after review it was removed from 3.2 in favour of a later small source test,
  docs/ROUND_3_2.md.) S2-S4 stay below 0.95 ->
  explicit operators; no further reasoning variants in this round.
- Correction of round 3.1's reading: "the reader cannot compare / bind / link" holds for
  direct answers and instructed step-by-step answers of these models, not for Qwen3 with
  its thinking mode, which comes within reach on S2/S3 and is at target on S5.

Infrastructure note: the dry run of commit a5a680e failed because several collectors
pushed to the results branch at the same time; its cells were unaffected and the next dry
run (d344be6) was complete. All collectors now retry the push after a rebase, and broad
or self-referential workflow triggers were removed so that unchanged checks do not rerun.
