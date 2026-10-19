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
