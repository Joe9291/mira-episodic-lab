# Round 3.2 - agent memory from S0 (design v4, after Astra's reviews of v1, v2 and v3)

Uncertainty removed: does an explicit episodic memory work as an agent memory (survives a
restart, answers from its own records, abstains correctly and only where it may), and
does a gain come from what is selected or from how it is processed? Ends with one run;
round 3.3 (action environment with causal interventions) was prepared in parallel and
has meanwhile run on its own (model-free; docs/ROUND_3_3.md). Reviews: `reviews/2026-10-17_r32_astra.txt` (v1),
`reviews/2026-10-17_r32v2_astra.txt` (v2), `reviews/2026-10-17_r32v3_r33v2_astra.txt` (v3),
`reviews/2026-10-18_r32v4_astra.txt` (v4: APPROVE; her documentation and normalisation-count
ideas adopted before the run, the broader completion tests noted for later).

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

Unknown values (v3, completed in v4). A field is unknown if the encoder declared it so
(record `extra.unknown`; its value is then None - every invalid or missing LM slot) or if
a field every episode has (actor, action, place, a valid integer day) is missing. A
missing partner or object without that declaration means "none in this episode". An
unknown value is never evidence of absence, order or uniqueness. `possible()` returns
the records that match a cue or could match it through an unknown field; a person could
be the actor or the partner of a record in which either is unknown. Rules, the same in
every operator: find - no exact hit but possible ones -> `insufficient_evidence`,
possible records with another value of the asked field -> `ambiguous`; latest / last
handler - every record that could be the latest one about the person or object (exact
records of the latest known day, exact undated records, and possible records that are
undated or not earlier) must agree (same place / same known actor), else `ambiguous`;
only possible records -> `insufficient_evidence`; state_at - possible records of that day
or undated ones block a negative and must agree on the place; compare_time - a second
exact OR possible match of a side makes it non-unique -> `ambiguous` (checked before the
negative for a missing side). A record whose known fields contradict the cue is no
possible match, and a possible record that cannot change the answer (earlier than the
latest known day, same place, same actor) does not block it. Every `ok` result carries a
non-empty string value. Tests: Astra's counterexamples (unknown actor later than the
latest record; unknown object of a later event by another actor; a second possible
comparison match), the cases in which the unknown cannot change the answer, and a
soundness test against brute force: for 400 random small stores with up to three unknown
fields, every answer other than "unknown" (full store, and certified struct3 selections)
equals the answer under EVERY completion of the unknown fields (exact semantics on the
completed records); the v3 operators fail this test in many cases, v4 in none (also in
10 x 1,500 stores outside the test suite).

On a partial (uncertified) selection, positive answers (find, comparison, state on a day)
are drawn from the selected records; a contradicting record outside the selection can
make them wrong. This is the declared cost of partial retrieval and is what lex3 and
random3 measure; negatives, latest and last handler are never concluded there.

## 3. Cells - reader and operators get the same selection, information and contract

| cell | selection | processing |
|---|---|---|
| lex3+reader / lex3+ops | BM25 over the raw texts, top 3; cannot certify completeness | LM reads the 3 notes / operators with incomplete scope |
| struct3+reader / struct3+ops | index scan over all records: all full matches of each event in the query first, best partial matches after; time-aware for "latest" (the person's most recent records), two-stage for E7 (the unique cue match, then its person's most recent records); certified complete when the full matches (or the latest-day records) fit into the 3 | LM reads the 3 notes / operators with the certified scope |
| full+ops (reference) | all records | operators, complete scope |
| random3+ops (control) | 3 records by a hash of the question | operators, incomplete scope |
| full+ops/lm-encoder | all records of a store written by the LM encoder | operators |

`covered` means: the selection is certified sufficient for THIS question (not that the
store is complete). struct3 certifies only if all full and possible matches of each
event fit into the budget, or, for latest and last handler, if every record that could be
the latest one (same rule as the operators, possible records included) is selected. A
test shows that the operators on a certified selection give exactly the full-store answer
(status and answer) for every query of the random stores above.
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
recorded raw replies (declared unknown slots included), recomputes the misbound control,
checks provenance (request and pins hashes, one code commit, and that it is the code
commit of the run, passed by the workflow) and the restart flags. The encoder adoption
decision (separate file ENCODER_DECISION: ADOPT / KEEP / UNDECIDABLE) is drawn only from
the complete, fully validated set of the 15 planned world reports; with a missing or
invalid report the verdict is INCOMPLETE, the decision UNDECIDABLE, and the tables of the
valid reports are marked as diagnostics only. "Accuracy covered" is pooled over all
covered final items of a series (not averaged per world first).

## 5. LM encoder

Slot filling by single-detail questions (day, first person, second person or none,
action, object, place), one fresh chat per slot, v1-style instruction; every value is
type-checked; an invalid or (for an always-present slot) missing value is listed in
`invalid`, stored as None and declared unknown in the record; the raw reply is kept; it
never stops the run. A reply for the second person that repeats the first person is read
as "no second person" (a declared normalisation; a wrong partner is then a slot error
measured by the partner slot accuracy, like any valid but wrong value). S1
qualified person, place, object and day; the second person and the action are measured
here for the first time. Qualification rule for the LM encoder on the tested round 3.2 templates (fixed now): all_slots (share of
episodes with every slot right) >= 0.95 AND the full+ops/lm-encoder cell within 0.02 of
full+ops on positive final items AND its lure false recall <= 0.05. "Positive final
items" = E2, E3a, E3b, E4, E7 of the final test, the two A/B orientations of an E3a pair
weighing 1/2 each, pooled over both conditions within a world, then the mean over all 15
worlds; lure false recall the same way. Lure correct rejection and "unknown" are reported
next to it (a low false recall alone is no rejection). These are technical decision
rules for development, not reliability claims. Otherwise the regex
encoder is used and the limit is stated. An adoption holds only for the round 3.2
template episode formats; other formats (the round 3.3 environment with "You" and
object-free events, free wordings) need their own check (round 3.4: frozen LM encoder on
held-out wordings).

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

## 8. Runs

Run 1 (GitHub 39113777648, commit 9a946ec): VERDICT INCOMPLETE, encoder decision
UNDECIDABLE. 13 of 15 world reports valid; in dev-m3 world 5 and pilot-m2 world 0 the
collector could not replay the lex3 selections (diag_replay for lex3+reader and lex3+ops).
Cause: BM25 summed its per-term scores in the iteration order of a Python set, which
depends on the per-process hash seed; near-ties between notes could then fall
differently in the job and in the collector. Fix: a fixed (sorted) term order. A test
reproduces the failing case in subprocesses with different PYTHONHASHSEED values (it
fails on the old code and passes now), and the selections and operator results of all
deterministic cells over all 15 worlds are identical under three hash seeds. The
collector worked as intended: it refused the unreplayable reports and the incomplete
evaluation drew no encoder decision. The tables of run 1 were not used for anything;
the whole round is re-run on the fixed code (run 2), and only run 2 is evaluated.
