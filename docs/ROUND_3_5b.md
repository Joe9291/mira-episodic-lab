# Round 3.5b - one fix iteration of the LM-assisted extraction, qualified once on the reserve

Uncertainty removed: does the round 3.5 extraction system, corrected by two named schema
rules of this environment, meet the unchanged 3.5 criteria on NEW worlds with the LAST
unused wording set (the reserve paraphrases)? Round 3.5 itself stays ENCODER_QUALIFIED NO
and MILESTONE_ORIGINAL_RULES FAIL (docs/ROUND_3_5.md, items 13-14); this is a new
iteration with its own result. Approval of the plan: Astra, 2026-10-19
(reviews/2026-10-19_r35holdout_astra.txt: Q1 count corrections, Q2 F1 and F2 APPROVE as
named schema rules, Q3 APPROVE 3.5b; the decoder d3 and the freeze still need review).

## What changes (exactly F1 and F2; acceptance criteria unchanged)

Decoder d3 (episodic_lab/encoder35.py) = d2 plus two request options:
- F1 `object_two_tokens`: canonical object values are adjective + noun (two tokens) or
  "none" - a type rule of this environment's schema (objects are always adjective + noun;
  same-noun objects exist, so a bare noun is never a valid object). It acts on canonical
  values ("the heavy ledger" -> "heavy ledger" stays admissible). It does not guarantee a
  right choice: another wrong two-token value can still win.
- F2 `gave_receiver_self`: an ACCEPTED action "gave" admits only role pairs whose receiver
  is You - a generator invariant of this environment (all 1,260 giving events of the five
  splits go to the agent). It is a feasibility condition of the role pairs together with
  actor != receiver (no later overwrite of the receiver); with an unknown action it is
  inactive. Consequence for the claim: the receiver of a giving event is given by the
  schema, not extracted; a success is no evidence of general receiver recognition.
Everything else is frozen as in round 3.5: qwen2.5-1.5b (pinned), prompt p8, candidates
c2, sum score, joint roles, structurally fixed slots, criteria. The remaining error
mechanisms (left/put, the receiver "You" of observed placings, the passive actor, the
place as actor, shortened names) are not fixed and count fully in the record criterion;
"task-neutral" means neutral for the tested questions only.

## Development (known data only; reserve performance closed until after the freeze)

Offline from the recorded p8 encodings (no model calls): calibration on cal with d3 ->
action, actor, receiver, object, place tau 0.0 (precision 1.0 / 0.997 / 1.0 / 1.0 / 1.0;
receiver: 688 multi-value cases and 60 single values from the schema, object: 689 and
59), day STRUCTURAL (748 single values from the text, precision 1.0). dev complete
records 1.000, cal 0.997; every 3.5 criterion met on dev and cal. Class diagnostics (per
adjective, wording frame and role, with denominators): no class with an error or unknown
on dev; on cal 2 actor errors in one frame (placing:dev:0, 35 texts); the smallest correct
margins dev 0.37 (wooden; own_put:dev:2), cal 0.50 (heavy). The consumed holdout as audit
material (NOT a qualification; the rules were chosen after seeing its errors): d3 0.964,
criteria met; d2 0.959 not met; F1 only 0.961 not met (giver 0.963 / 0.950); F2 only
0.962 not met (giver 0.975 / 0.975, object:first 0.988).

## Qualification (once)

config/round35b_reserve_proposal.json (not enabled until approval): split res (40 new
pairs per kind, reserve paraphrases), 12 chunks, decoder d3, thresholds above, bound to the
code by decoder version and SHA-256 of the full import closure (checked before the
workflow plan, in every encode job and by the collector). Order: Astra's review of d3 and
the freeze -> model-free reserve coverage check (bench/m3/audit35.py --reserve; a failure
consumes the reserve, then only transfer to new worlds with known wordings may be claimed)
-> one encode run -> ENCODER_QUALIFIED and MILESTONE_ORIGINAL_RULES on res.
Reported besides the primary result (collector, same encodings and thresholds): d2, F1
only, F2 only as comparisons (is d3 better on the same cases, or are the reserve wordings
easier?); single values fixed by the schema per slot ("from schema") and the accuracy of
the remaining model choices; class diagnostics with denominators; every wrong or
non-memory decision traced: wrong record fields -> policy (memory / fallback) -> action
right or wrong.
Stop rule: if the reserve result is NO, round 3.5 ends with the reported results, the LM
extraction does not write the stores of later rounds, and the next step is round 3.6 (the
goal/question parser) with structured input (Astra's preferred alternative B).

## Review of d3 and the mutation proof

Astra, 2026-10-19 (reviews/2026-10-19_r35b_d3_astra.txt): report corrections, decoder d3,
test contents, collector, offline recomputation and the freeze configuration APPROVE; the
mutation proof REQUEST CHANGES (python -B only stops WRITING bytecode; stale compiled files
can still be read) - the reserve may be audited and opened with exactly this configuration
once a clean proof exists. Clean proof (bench/m3/mutation35b.py, result
docs/ROUND_3_5b_mutation.json, RESULT PASS): no __pycache__ in the repository before and
after; every test run a fresh process with -B, PYTHONDONTWRITEBYTECODE=1 and its own new
empty PYTHONPYCACHEPREFIX (checked: no .pyc written); the freeze-binding test excluded; a
kill counts only as a FAILING substantive assertion. Baseline (20 tests) passes before
and after; after every mutant the file is restored byte-identically; the production files
match the proposed freeze.
Finding: under this protocol the mutant "calibration ignores the earlier slots'
thresholds" SURVIVED - in the earlier proof it had been counted as killed only because the
freeze-binding test fails for every code change. The code was right; a test was missing.
Added: test_calibration_uses_earlier_calibrated_thresholds (the action has no qualifying
threshold -> unknown -> the narrator constraint stays inactive -> the actor stays a real
choice; with threshold 0 the actor would become a single value). Rerun: all 11 mutants
killed by substantive assertions, none by an error. The decoder, the collector and the
freeze are unchanged (tests are not part of the frozen code).
Non-blocking ideas (not in the frozen code, done after the run as separate analysis):
class findings as texts / wrong fields / unknown fields plus affected records; decision
consequences with the memories used and the operator status; a paired change table d2 /
F1 / F2 / d3; uncertainty intervals over world pairs (criteria unchanged).

## Reserve coverage check and opening

Post-freeze, model-free (bench/m3/audit35.py --reserve, 2026-10-19,
docs/ROUND_3_5b_reserve_audit.json): no problems (roundtrip, pair invariance, disjoint
texts across dev/cal/aud/ho/res, >= 30 distinct texts per reserve frame); candidate
coverage 1.0 for every slot on res (2,974 distinct texts); every true object of all five
splits has exactly two tokens (F1 never excludes a true value); position/word-list
baseline on res: all slots 0.504. Opened with config/round35.json = the reserve proposal
with "enabled": true (unchanged otherwise).

## RESERVE RESULT (once; GitHub 39257404107, commit b400189)

config/round35.json sha256 5adb802d48825ce8b558db3e5837ca662e05b8b16e50211a0713b299659f54f8
(= the proposal with "enabled": true); freeze checks passed in the plan, all 12 encode jobs
and the collector; all 12 reports present and valid; VERDICT COMPLETE.

ENCODER_QUALIFIED = YES. MILESTONE_ORIGINAL_RULES = PASS (all 17 original round 3.3/3.4
checks). The reserve is consumed.
- Records (2,974 distinct texts): complete records 0.994; place, day, object 1.000; actor
  0.999, action 0.999, receiver 0.997 (240 receivers of giving events fixed by the schema
  rule F2, "from schema"; the accuracy of the remaining receiver choices 0.996). 17 records
  wrong, none unknown: the receiver "You" for an observed placing "You noticed on day d
  that X put the Y at P." (10) and its actor "You" (4), "X crossed your path" read as
  "left"/"went" (3).
- Tasks: every kind x goal cell success 1.000, pair success 1.000, confident-error rate
  0.000, coverage 1.000 (no fallback); Wilson 95% interval of each cell's pair success
  [0.912, 1.000] (40 pairs per kind).
- Controls: uniform scores 0.000 complete records; random scores 0.327 of the slots
  correct; position/word-list baseline 0.504.
- Comparison decodings on the same encodings (diagnosis only; d3 was pre-registered):
  d2 0.979, criteria NOT met (giver:find 0.938 / 0.925 - "X gave me the Y" read with
  receiver "none" in 35 of 78 texts); F1 only 0.983, NOT met (same); F2 only 0.991, met.
  Paired: relative to d2, d3 fixes 44 records and 5 giver world decisions and breaks
  none; F1 alone fixes 9 records (the "heavy" objects) and no decision.
- What the result shows: the system of the 1.5B model's scores, the given candidates and
  the schema-constrained decoder d3 writes the episodic store of this environment from
  free-text notes in unseen wordings well enough that every memory task and every
  original milestone rule of rounds 3.3/3.4 passes. What it does not show: general
  receiver recognition (the decisive F2 gives the receiver of every giving event; without
  it the giver task fails again), nor anything beyond this environment's schema, wordings
  of this kind and 40 pairs per kind.
- Post-run analysis (bench/m3/post35b.py, docs/ROUND_3_5b_post_res.md): paired change
  table, intervals, class findings with affected records; no decision consequences (no
  wrong or non-memory decision).
