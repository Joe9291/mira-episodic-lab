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
