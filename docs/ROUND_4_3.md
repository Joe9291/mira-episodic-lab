# Round 4.3 - Source-bound consolidation of the long-term memory (design v2, for review)

Context: the five-phase plan (2026-10-20) names three parts of phase 2: versioned
statements, contradictions, and source-bound consolidation ("quellengebundene
Verdichtung"). Rounds 4.0, 4.1 and 4.1b established the first two on structured reports
(holdout PASS; a continued instance with restart). Round 4.2 (phase B, language input)
was closed under option A on 2026-10-24 (development requirements not met, holdout not
evaluated); it does not change M. Astra placed compaction after phase B and asked for it
to be tested separately, "so that it stays recognisable whether an error comes from the
resolution logic or from information lost by compaction" (reviews/2026-10-20_r40v1b_astra.txt;
docs/ROUND_4_0.md section 6). This round adds nothing to the resolution logic: M, R, the
source policy and the report schema stay exactly as in round 4.0.
v2 answers Astra's review of v1 (reviews/2026-10-24_r43v1_astra.txt): an operator
dependency table and source binding by output role (sections 2, 6); strictly increasing
report ids as an explicit input contract, the highest id over ALL prefix reports
(section 2); "lossless" means the logical information, physical encoding is measured
separately (sections 2, 7); a digest with values per citation, agreeing vs dissenting
non-deciding claims and origins (section 3); K3 replaced by an id-renaming control and a
binding rule for non-discriminating controls (sections 5, 6); genesis cut, complete
cuts, composition under identical header parameters, the hashed payload, trust anchors
outside the checked data, sealed verification before deletion, interrupted writes, and
the bound holdout numbers (sections 2, 4, 6).

Uncertainty removed: can the memory replace its growing raw report log by a compact
consolidated state - so that (a) every answer stays exactly the answer of the full
memory, including the report ids it cites; (b) every consolidated item stays bound to
the original reports it comes from and can be verified against the archive; (c) when the
old log is actually deleted, every question that would need it is answered "compacted",
never with a wrong value; and (d) a source-bound digest per fact (versions merged, every
value with its supporting, agreeing and dissenting sources) is exactly reproducible by
the independent reference?
Claim limits (fixed now): structured reports of the round 4.0 / 4.1 generators only; the
fixed source policy of round 4.0; lossless consolidation of the logical information under
that policy (section 7 states what it cannot shrink); no language, no retrieval budget,
no summarisation by a language model.

## 1. What stays

Report schema, ReportStore (append-only, SHA-256 chained), M (episodic_lab/r40_memory.py),
R (episodic_lab/r40_reference.py), the transition rules and the operators current,
valid_at, believed_at, why_changed, conflicts, history, before - unchanged, files not
touched. The worlds are rebuilt by the generators' own functions (round 4.0: P1-P9, round
4.1: T1-T5; episodic_lab/r43_world.py, checked to reproduce the original worlds exactly
when given the old seeds: 1,120 of 1,120 dev world-delay instances) with NEW seeds
(r43-dev-1, r43-holdout-1), dev 10 / holdout 40 pairs per family, delays 0 / 50 / 200 /
500. The 4.0 conformance set (hand worlds) is run as well.

## 2. The consolidated state (checkpoint), its proof obligations and the two modes

Input contract of this round: report ids strictly increase in the total order
(report_day, report_id) - r00001, r00002, ... (generator property; audited for every
world: 4,480 of 4,480 holdout and 1,120 of 1,120 dev world-delay instances). Uniqueness
in general is NOT implied by a maximum; under this contract it is.
A cut c is COMPLETE: it covers all reports with report_day <= c (the total order makes
this prefix well defined); c = 0 is the empty prefix (genesis).
Checkpoint C(c): for every fact (subject, attribute) - anchor events included, they are
facts like any other - the claims STANDING at knowledge time c, each with the fields the
resolver and the digest read: claim id (the report id that created it), value,
valid_from, rank, source, origin. Nothing else is kept: withdrawn claims, retract
reports, ineffective reports and every other report field are dropped.
Header: schema, cut day c, the seal of the archive prefix (count and head hash of the
report chain over all reports with report_day <= c), the highest report id over ALL
prefix reports (also retractions, ineffective and dropped reports), the hash of the parent
checkpoint (the fixed genesis value for C(0)), the SHA-256 of the resolver source
(episodic_lab/r40_memory.py), and the checkpoint's own hash = SHA-256 of the canonical
JSON of the checkpoint object WITHOUT the hash field.
Operator dependency table (what each answer needs; ids = what it cites):
| operator | needs | claim fields read | order | ids in the output |
|---|---|---|---|---|
| current, valid_at, believed_at (value_at(v, k)) | standing claims at k | valid_from, rank, value, id | valid_from | deciding claims of the version containing v |
| history, conflicts (at now) | standing claims at now | valid_from, rank, value, id | valid_from | deciding claims per version |
| before (at now) | standing claims of the anchor fact and of the fact at now | valid_from, rank, value, id | valid_from | deciding claims of the version containing d_Y - 1 |
| why_changed(v, k1, k2) | standing claims at k1 + every report with k1 < report_day <= k2, all fields | as the transition rules | total order of the reports | the reports in (k1, k2] whose application changes the answer for v |
| digest at k | standing claims at k | all six | valid_from, then id | support / agree / dissent claims (section 3) |
| a later correct / retract (transition) | the target among the standing claims | id, rank, source, value, valid_from | total order | - |
Proof obligation 1 (state): M's transition rules use a target claim only through "exists
and stands" (then its rank, source, value, valid_from); a target that is withdrawn,
claimless (an ineffective correction) or missing makes a correction or retraction
ineffective in all three cases alike, and report ids are never reused (contract). By
induction over the reports of (c, k]: the standing claims of every fact at every k >= c
are the same whether the replay starts from the full prefix or from C(c).
Proof obligation 2 (answers): by the table, every operator with all its knowledge times
>= c reads only standing claims at those times and, for why_changed, the reports of
(k1, k2] (all of them after c, since k1 >= c); so every answer - values, statuses and
cited ids - is the same. Both obligations are tested: by hand cases (one per equivalence
and per citation role, section 8) and on every world (section 6).
Hot memory H = the checkpoint + the tail (the reports with report_day > c, a chain segment
that starts at the archive head recorded in the checkpoint). H uses M's transition and
version functions unchanged (imported, not copied); only its starting claims differ - so
any difference to M is a consolidation error, never a resolution error. Tail ingest refuses
a report id at or below the checkpoint's highest id.
Independent check by R: every claim of C(c) is written as one synthetic assert report
(same id, value, valid_from, rank, source, origin; report_day c); R on these synthetic
reports plus the tail must answer every question with all knowledge times >= c exactly as
R on the full reports.
A checkpoint is built from scratch (replay of the archive prefix) or incrementally
(parent checkpoint + segment). Mode A (archive kept as cold storage): checkpoints every D
days (D = 5, fixed) including C(0); a question is answered from the latest checkpoint
whose cut is <= the smallest knowledge time it needs (believed_at, digest_at: t;
why_changed: k1; all others: now) plus the archive segment up to the needed time.
Mode T (truncated): only the latest checkpoint C(c) and the tail exist (the archive prefix
is deleted). Before the deletion C(c) is verified against the archive (rebuilt from
scratch with identical bytes, and the R check above) and this verification is sealed in a
trust record kept OUTSIDE the checkpoint and the tail (checkpoint hash, archive seal at c,
verification result); after the deletion a checkpoint is accepted only if it matches the
trust record. A question that needs a knowledge time < c is answered {"status":
"unknown", "reason": "compacted"} (why_changed: "compacted"); every other question is
answered from H.

## 3. Source-bound digest

digest(s, a) at knowledge time k: the history of (s, a) at k, consecutive versions with the
same status and the same value(s) merged into one segment:
{valid_from, valid_to, status, value | values, support, agree, dissent, independent_origins}
- every cited claim is given as {id, value, valid_from, source, rank, origin};
- support: the deciding claims of the merged versions, grouped by value (a conflict
  segment has one group per conflicting value);
- agree: standing claims of the segment's versions that do not decide (outranked) but
  carry a value of the segment (the value, or one of the conflict values), grouped by
  value;
- dissent: standing claims of the segment's versions that do not decide and carry a
  different value;
- independent_origins: per value of the segment, the number of distinct origins among its
  support and agree claims (the policy's independence: different origin; a report count
  is not used);
- the lists are UNIONS over the merged versions - each claim keeps its own valid_from; a
  listed claim does not by itself support the whole segment;
- plus the answer value_at(k, k).
Every value in a digest appears with at least one cited claim, and every claim standing at
k appears exactly once (checked: the digest partitions the standing claims of the fact).
digest_at(t) is the digest at knowledge time t. R computes the digest independently from
its own table (a separate function in a new module, no shared code with H's digest; R's
file itself is not changed).

## 4. Cuts, questions and the bound numbers

Per world (pair world A or B, delay) the cut days are: 0 (genesis), every day from the
first to the last relevant report day + 1 (so every relevant report - correction,
retraction, late report, anchor - lies on each side of some cut), the days at 1/4, 1/2 and
3/4 of the irrelevant tail, and now; every cut is complete. Questions per world: the
family's questions (round 4.0 table; round 4.1: current) plus the consolidation
questions about the asked fact: current, history, conflicts and digest at now; valid_at(v)
for every valid_from v of a relevant report about the fact; believed_at(t) and
digest_at(t) for every relevant report day t; why_changed(v, k1 = t, k2 = now) for every
such v and every such t < now. Mode T: every question at every cut; Mode A: every question
once; composition: every consecutive pair of cuts.
Bound numbers (episodic_lab/r43_world.py, computed before any run of H):
| | dev | holdout |
|---|---|---|
| families x pairs | 14 x 10 = 140 | 14 x 40 = 560 |
| world-delay instances | 1,120 | 4,480 |
| cuts | 16,672 | 66,392 |
| questions (Mode A answers) | 31,872 | 126,540 |
| Mode T evaluations (cut x question) | 546,776 | 2,135,976 |
| composition pairs (cuts - instances) | 15,552 | 61,912 |
Holdout questions by operator: why_changed 53,524, believed_at 17,912, digest_at 16,632,
valid_at 14,632, current 8,160, history 5,760, conflicts 5,120, digest 4,480, before 320.
Any deviation from these numbers in the run fails the round.

## 5. Systems and lossy controls

H (Modes A and T), M (full store), R (reference, digest added). Lossy checkpoint controls
(each a deliberately reduced checkpoint, answered by the same H code):
- K1 current-only: per fact only the deciding claims of the current version at c.
- K2 deciding-only: the deciding claims of every version at c; outranked standing claims
  dropped (agree / dissent and any later re-emergence of an outranked claim are lost).
- K3 id-renamed (identity control): ALL standing claims kept, only their ids replaced by
  the fixed, collision-free, schema-conforming map rN -> r(99999 - N) (audited: no
  renamed id equals any id of the world - the highest id in all dev and holdout worlds is
  r00509, the lowest renamed id r99490); a later correction or retraction of a pre-cut
  report finds no target, and cited ids change.
A case (world, cut, question) is INFORMATIVE for a control if R, run on the control's
checkpoint written as synthetic reports plus the tail, answers differently from R on the
full reports - a property of the worlds, computed by R before any run of H. Prediction:
H on the control checkpoint answers exactly as R on it, so it fails exactly on the
informative cases (Mode T in-scope questions).

## 6. Measures and pass rule (fixed before any run)

Pass rule on the holdout (zero allowed errors everywhere; the numbers of section 4 bound):
(1) Mode A: every question identical to M, report ids included, in every world; M = R on
    every question; the digest of H = the digest computed from the full store = the
    digest of R; R on C's synthetic reports plus the tail = R on the full reports at every
    cut.
(2) Mode T: at every cut of every world, every question that needs no knowledge time < c
    identical to M; every question that needs one answered "compacted"; no other output.
(3) Composition: for every consecutive pair of cuts, C(c2) built incrementally from C(c1)
    and the segment is byte-identical to C(c2) built from scratch WITH THE SAME header
    parameters (in particular the same parent hash; different parent chains give
    different bytes by design); the claim payload is identical whatever the chain; C(c)
    built in a new process is byte-identical.
(4) Integrity, trust anchors and persistence: the expected checkpoint hash and the final
    tail seal are kept outside the checked data (trust record); detected on load: a claim
    value or rank changed, a claim removed or added (each also WITH a recomputed self-hash,
    i.e. internally consistent - detected only through the trust record), the archive seal
    changed, the parent hash changed, a tail record changed, removed or reordered, the tail
    cut off at its end (a valid shorter chain - detected only through the trust record), a
    tail report id at or below the checkpoint's highest id; interrupted writes (a crash
    after writing the new checkpoint but before the trust record, and after the trust
    record but before the tail is rotated) are detected on restart and the last consistent
    state is used - never a mismatched pair; a checkpoint and its tail written to disk and
    reloaded in a new process answer every question identically.
(5) Source binding by output role (checked against R at the respective times):
    value evidence - every id in a value / conflict answer, history, conflicts or digest
    (support, agree, dissent) is a claim standing at that answer's knowledge time, with
    the cited fields equal to R's; change evidence - every why_changed id is a report with
    k1 < report_day <= k2, present in the archive segment (Mode A) or the tail (Mode T),
    and the list equals R's; target references - for every tail correction / retraction
    its effectiveness under H equals that under R, and an effective one's target is a claim
    of C or of the tail.
(6) Lossy controls: H on each control checkpoint answers exactly as R on it (so each
    control fails exactly on its informative cases); each control has >= 30 informative
    cases from >= 10 distinct pairs, reported with their numbers of pairs, families and
    operators (several cuts of one pair are not independent cases). These counts are known
    before any run of H; a control that misses them makes a full PASS impossible - it does
    not silently drop out (the design would be revised before the freeze).
(7) The 4.0 conformance set through Modes A and T at every cut.
Measures (report only): size of C(c) against the archive prefix - logical (claims vs
reports) and physical bytes, the latter also after a shared dictionary / generic
compression, reported SEPARATELY from the removal of logical information; reports and
claims read per question in Mode A / T against a full replay; digest segments against
history versions, agree / dissent counts; time. This is the pass rule of a finite test
suite (14 families x 40 pairs); zero errors do not establish a general error rate.
Joe's check (about 5 cases, chosen by rule): a cut between a report and its correction; a
late report whose valid_from lies before the cut; a conflict opened before and resolved
after a cut; an anchored question whose anchor lies before the cut; a Mode-T answer
"compacted".

## 7. Known limits (stated in advance)

Under the round 4.0 policy any standing claim can still be corrected or retracted later,
so lossless consolidation cannot drop standing claims: the logical state shrinks only by
the withdrawn claims, the correction / retraction / ineffective reports and the unread
fields; physical encoding can save further bytes without removing information (measured
separately). In worlds that are mostly assertions the logical gain is small; the gain is
mainly in what a question has to read. A real reduction needs a policy decision - for
example a finality horizon (claims older than H days can no longer be targeted); even then
source evidence may not simply be deleted, because history ids, cited ids and the digest's
agree / dissent still need it. That is a different policy and NOT part of this round.
Questions about knowledge times before a deleted prefix are unanswerable by construction -
Mode T makes that explicit instead of hiding it.

## 8. Cost and tests

Model-free. Development locally; the holdout (generated and frozen before any run of H on
it) in GitHub Actions, split by family (about 2.1 million Mode T evaluations plus the R
checks per cut and per control: a few CPU hours). Hand cases (tests): every equivalence of
proof obligation 1 (a correction / retraction of a withdrawn, a claimless and a missing
target, each before and after a cut), every citation role of section 6 (5), composition,
every tamper and interrupted-write case of section 6 (4), the digest's grouping (a
conflict segment, an agreeing outranked claim, a dissenting one, merged versions).
