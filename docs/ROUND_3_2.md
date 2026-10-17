# Round 3.2 - agent memory from S0 (design v3, after Astra's reviews of v1 and v2)

Uncertainty removed: does an explicit episodic memory work as an agent memory (survives a
restart, answers from its own records, abstains correctly and only where it may), and
does a gain come from what is selected or from how it is processed? Ends with one run;
round 3.3 (action environment with causal interventions) starts from its result and is
prepared in parallel. Reviews: `reviews/2026-10-17_r32_astra.txt` (v1),
`reviews/2026-10-17_r32v2_astra.txt` (v2).

Basis: round 3.1/3.1b (docs/ROUND_3_1.md). Direct and instructed step-by-step answers of
both small readers fail at comparison, conjunctive matching with abstention, linking and
source filtering; extraction of a single detail works. Qwen3's whole thinking
configuration (thinking mode, its sampling and a 1024-token budget, changed together)
lifts all four, S5 to 20/21 (observed cases 6/7) - a reason for a limited later test,
not a reliability proof. The candidate procedure used did not remove the failures; it
does not prove that output format, scoring and calibration play no part.

## 1. Store (episodic_lab/memory.py)

Append-only JSON-lines file; one record per episode, written once and flushed; SHA-256
chain (changed, removed or reordered records are refused) plus an external seal (record
count and head hash kept outside the file) that also refuses a store whose last records
were cut off. Fields: identity (`id`, `stream`, `seq` = record time), `event_day`,
`actor`, `partner`, `action`, `object`, `place`, `source` (kind, by), original `text`,
`relations`, `encoder`. Derived state (latest place etc.) is computed at query time. The
runner's fingerprint uses a digest of the actual record contents, so any change of a
record in working memory while answering is detected.

## 2. Operators and scope

Every operator receives the records it may use and whether that set is the complete
store. Statuses: `ok`; `none_in_scope` and `no_observation` (only with a complete scope:
the cue's entities are known but the combination never occurred / an entity was never
recorded); `ambiguous`; `insufficient_evidence` (incomplete scope: no negative, no
"latest", no "last handler" may be concluded). Only `none_in_scope` maps to "none" in the
closed benchmark; everything that is not `ok` or `none_in_scope` answers "unknown". All
operators use the same semantics (compare_time included). Days that are not valid
integers (an encoder error) are treated as unknown, never compared.

Unknown values (v3): a record whose day, place, object, action or person is unknown (an
encoder error) is never evidence of absence or of order. `possible()` returns records
that could match a cue because a needed field is unknown: a find without exact hits but
with possible ones gives `insufficient_evidence`; possible records with other values make
a find `ambiguous`; latest/last-handler/state-at with an undated record of the person or
object that could change the answer give `ambiguous` or `insufficient_evidence`; an
undated or unknown record that cannot change the answer (same place, other person) does
not block it. Every `ok` result carries a non-empty string value.

## 3. Cells - reader and operators get the same selection, information and contract

| cell | selection | processing |
|---|---|---|
| lex3+reader / lex3+ops | BM25 over the raw texts, top 3; cannot certify completeness | LM reads the 3 notes / operators with incomplete scope |
| struct3+reader / struct3+ops | index scan over all records: all full matches of each event in the query first, best partial matches after; time-aware for "latest" (the person's most recent records), two-stage for E7 (the unique cue match, then its person's most recent records); certified complete when the full matches (or the latest-day records) fit into the 3 | LM reads the 3 notes / operators with the certified scope |
| full+ops (reference) | all records | operators, complete scope |
| random3+ops (control) | 3 records by a hash of the question | operators, incomplete scope |
| full+ops/lm-encoder | all records of a store written by the LM encoder | operators |

`covered` means: the selection is certified sufficient for THIS question (not that the
store is complete). struct3 certifies only if all full and possible matches (or all
records of the latest day, with no undated record of the person/object) fit into the 3.
Within a pair, the reader receives in its prompt exactly what the operators use: the
coverage line (complete for this question / partial selection), and, when covered, the
index's entity knowledge (whether every name in the question occurs in memory); and it
follows the same contract: "none" only for a covered selection without the event and
with every name known, "unknown" otherwise (and for latest/last questions on a partial
selection). A test shows that an ideal reader following this contract gives exactly the
operators' answers in every row. The struct3 retriever contains processing of its own
(time order, two stages); this is part of the "struct" method and is reported as such. Baselines A0 and A1 (v1
instruction) run on the same worlds. Removed from round 3.2 (decision): the
thinking-reader cell (about 38 s per answer; a small targeted source test later is more
useful than a costly repeat of all criteria) and the `by_source` operator (the template
benchmark has no source items; source filtering returns with the action environment).

## 4. Per-answer record and evaluation

Every answer row stores, besides raw answer and category: the selected record ids, the
scope flag, the operator status and trace (replayed deterministically after the run from
the record set of that test point, never while answering) and, as evaluator-only
information, whether all gold target episodes were selected ("gold support"; not an
upper bound of accuracy). Cost per cell: LM calls, prompt and new tokens. A failing cell
is recorded with its traceback and does not stop the others.

Reported separately per cell: coverage share, accuracy on covered items, abstention
("unknown") and false recall on lures, gold support, cost (calls, prompt tokens, seconds),
and the development worlds (dev-m3) apart from the already used pilot worlds (pilot-m2).
Expected cost per world (both conditions): about 2 x [4 (Q1 + Qf) + 6 E] model calls
(four LM cells, six encoder questions per episode), roughly 1,400 calls and 1-2 hours on
the runner, well inside the 6-hour job limit.

The collector trusts nothing: it regenerates world and questions from series and index
(hashes must match, every expected item answered exactly once), re-scores every row from
its raw answer, recomputes all summaries, re-runs the deterministic cells and compares
their raw answers, recomputes every diagnostic field of every selecting cell (selection,
coverage, entity note, operator value, status, trace, gold support) from the store of the
matching test point, rebuilds the LM-encoder cell from its recorded records with its
original encoder name (so record identities are reproduced), re-derives the encoder's
reference from the regenerated episodes and its cleaned values and invalid flags from the
recorded raw replies, recomputes the misbound control, checks provenance (request and
pins hashes, one code commit) and the restart flags.

## 5. LM encoder

Slot filling by single-detail questions (day, first person, second person or none,
action, object, place), one fresh chat per slot, v1-style instruction; every value is
type-checked; invalid values are kept as data (`invalid`) and never stop the run. S1
qualified person, place, object and day; the second person and the action are measured
here for the first time. Adoption rule for round 3.3 (fixed now): all_slots (share of
episodes with every slot right) >= 0.95 AND the full+ops/lm-encoder cell within 0.02 of
full+ops on positive final items AND its lure false recall <= 0.05. "Positive final
items" = E2, E3a, E3b, E4, E7 of the final test, the two A/B orientations of an E3a pair
weighing 1/2 each, pooled over both conditions within a world, then the mean over all 15
worlds; lure false recall the same way. Lure correct rejection and "unknown" are reported
next to it (a low false recall alone is no rejection). These are technical decision
rules for development, not reliability claims. Otherwise the regex
encoder is used in 3.3 and the limit is stated.

## 6. Restart test (completion point)

Exactly the store file of the full+ops cell and its seal are handed to a fresh isolated
interpreter that receives only the store path, the seal, the fixed code and the public
questions. Passed if: (a) answers equal the in-process answers; (b) with an empty store
no positive item is answered correctly; (c) a store with its last record cut off and (d)
a store with one changed record are refused.

## 7. Worlds, model, run

Development series `dev-m3` worlds 0-9 and `pilot-m2` worlds 0-4 (paired with the pilot),
both overlap conditions, v1 question sets. Reader and LM encoder: qwen2.5-0.5b (selected;
no switch to Qwen3 without a measured reason: both pass S1). Expected on the template
benchmark: full+ops and struct3+ops near 1.0; the informative results are the reader vs
operator difference at equal selection, the lex vs struct difference, the LM encoder
and the restart test.
