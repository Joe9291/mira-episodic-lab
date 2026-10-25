# Round 4.3 - Source-bound consolidation of the long-term memory (design v3, approved 2026-10-24 - reviews/2026-10-24_r43v3_astra.txt; implementation notes in section 9)

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
the bound holdout numbers (sections 2, 4, 6). v3 answers her review of v2
(reviews/2026-10-24_r43v2_astra.txt): a full-state comparison of every checkpoint and of
every propagated state against an independently built reference state over ALL facts
(section 2, pass rule 8); the synthetic R comparison only for questions whose needed
knowledge time is >= c (pass rule 1); lossy controls separated from the integrity checks
of regular checkpoints (sections 5, 6); the digest partition counts only the claim
entries (section 3); a canonical ordering (section 2); expected counts bound per family
and operator in a frozen file (section 4).

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
reports plus the tail must answer every question q with needed_time(q) >= c exactly as R
on the full reports (needed_time: believed_at, digest_at -> t; why_changed -> k1; all
others -> now). A question with needed_time(q) < c is NOT compared there: a checkpoint at c
cannot reconstruct it by construction (Mode A uses an earlier checkpoint, Mode T answers
"compacted").
Full-state check (independent of the questions): the reference state at knowledge time k
is built by a separate module from R's own step function (R's table of claim rows, its
alive flag; the origin of a claim is the origin of the report whose id the claim carries)
over ALL facts of the world - asked facts, anchors and every distractor fact. For every
cut, the normalised claim set of C(c) (subject, attribute, id, value, valid_from, rank,
source, origin) must equal the reference state at c; and for every knowledge time that any
question uses (in Mode A and in Mode T within scope), the standing claims that H has
propagated from its checkpoint and the tail must equal the reference state at that time,
again over all facts. The dependency table above is a description of M's and R's actual
reads that these checks put to the test, not a substitute for them.
Canonical form: facts sorted by (subject, attribute); claims by id; value groups by the
canonical JSON of the value; every list of cited claims by id; canonical JSON = sorted
keys, separators "," and ":", ASCII escaping; the checkpoint hash and every byte-identity
check use this form.
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
k appears exactly once among the claim ENTRIES of support, agree and dissent over all
segments (the partition check; the separately reported current answer is not counted as
a claim entry).
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
The same numbers per family and per operator are frozen in config/round43_counts.json
(v1, SHA-256 9a88a2da3a5a883b34698afacfb68a989c50eb38be69f23139ad5f1e177d1d63; v2 after
Astra's implementation review, written by bench/m3/counts43.py, adds the expected numbers
of full-state comparisons, digest partition checks and conformance checks, the v1 keys
unchanged: SHA-256 3e390e95cf9ba3773e43b26c783d40bca0c467a850a8b9ddb1495255e111fe49); the
run must reproduce every key and every count of that file; any deviation fails the round.

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
Controls versus integrity: regular checkpoints always pass through every integrity check
(section 6 (4)); a control checkpoint is a deliberately altered starting state (K3's ids
lie above the prefix ids and contradict the source binding) and is loaded only through a
test-only path that skips the integrity checks and is unreachable from Modes A and T. The
controls test the propagation of state against their R counterpart; an integrity refusal
never counts as the predicted semantic failure of a control.

## 6. Measures and pass rule (fixed before any run)

Pass rule on the holdout (zero allowed errors everywhere; the numbers of section 4 bound):
(1) Mode A: every question identical to M, report ids included, in every world; M = R on
    every question; the digest of H = the digest computed from the full store = the
    digest of R; at every cut, R on C's synthetic reports plus the tail = R on the full
    reports for every question q with needed_time(q) >= c (and only for those).
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
    before any run of H and are computed before the freeze; if a control misses them then,
    the design is revised (with a new review) before the freeze; on the frozen holdout a
    control that misses them makes a full PASS impossible ("incomplete evidence") - it does
    not silently drop out, and any later adjustment is a new attempt.
(7) The 4.0 conformance set through Modes A and T at every cut.
(8) Full state: at every cut of every world the normalised claim set of C(c) equals the
    independent reference state over all facts; at every knowledge time used by a question
    the state H has propagated equals the reference state over all facts (section 2). A
    negative test (hand case): a checkpoint that loses the claims of one distractor fact
    no question asks about - with a recomputed self-hash and a matching trust record, so
    that only this check can find it - is detected.
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
every tamper and interrupted-write case of section 6 (4), the lost distractor fact of
section 6 (8), the digest's grouping (a conflict segment, an agreeing outranked claim, a
dissenting one, merged versions), the test-only loading path of the controls (not
reachable from Modes A and T).

## 9. Implementation notes (after the APPROVE of v3)

Astra approved v3 on 2026-10-24 (reviews/2026-10-24_r43v3_astra.txt). Implementation:
- episodic_lab/r43_consolidate.py - checkpoints (scratch and incremental, canonical JSON,
  own hash over the object without the hash field, header with cut, archive seal, highest
  prefix id, parent, resolver hash); H = M's class with only `_claims_at` replaced (the
  replay starts from the latest checkpoint <= k; M's file unchanged); Mode A (D = 5 from
  C(0)) and Mode T (one checkpoint + tail, "compacted" below the cut); H's digest from H's
  own standing claims with M's version function; the control test path `control_memory`
  (no integrity checks; Modes A and T only accept checked checkpoints); disk layout: the
  tail is a chain SEGMENT that continues the archive chain from the checkpoint's seal, and
  the write order is checkpoint file -> tail file -> trust record (temp + rename) -> removal
  of older files, so a crash leaves either the old or the new consistent pair.
- episodic_lab/r43_reference.py - only R's step function and table plus the original
  reports: the reference state over all facts (origin from the report whose id the claim
  carries; checked for corrections and repeats by the hand cases), R's effectiveness of
  every correction / retraction, R's digest (own code), the synthetic reports, and the
  control claim sets K1-K3 - derived from R's table, so the informative cases are known
  before any run of H (design section 5 says "the control's checkpoint"; deriving it from
  R instead of from H's checkpoint keeps the controls R-only).
- R's answers to the questions are computed on the reports of the asked fact and its
  anchor only (an optimisation: M keeps claims per fact and every correction / retraction
  targets a report of its own fact - audited on every world, 0 cross-fact targets on dev
  and holdout); the full-state check always uses the whole world.
- bench/m3/run_round43.py (phases audit / run, one job per family), collect_round43.py
  (bound counts per family and operator, every rule, the expected numbers of tamper (12 per
  world-delay instance), interrupted-write (3 in implementation v1 - historical; 10 since
  implementation v2, see below), persistence (1) and lost-fact cases (one per
  instance with an unasked fact, i.e. delays > 0: 3 / 4 of the instances)), freeze43.py
  (R only), .github/workflows/round43.yml (14 family jobs + collect), tests/test_round43.py
  (hand cases: proof obligation 1 for withdrawn, claimless and missing targets at every cut,
  citation roles, digest grouping incl. a conflict segment, composition and parent, every
  tamper and interrupted-write case, every field of the full-state comparison changed
  (Astra's idea), a highest prefix id that belongs to a retraction / an ineffective
  correction (Astra's idea), the lost unasked fact, the control path).
- Tamper cases: the claim cases use the first cut with claims and a tail; the tail cases use
  the genesis checkpoint with the whole world as its tail (every world has >= 2 reports).
- Development result (docs/ROUND_4_3_dev_SUMMARY.md; run locally on commit 9308fa8, two jobs):
  PASS - zero violations of every rule;
  16,672 cuts, 31,872 Mode A answers, 546,776 Mode T evaluations, 15,552 composition pairs,
  73,368 full-state comparisons (16,672 checkpoints, 5,840 Mode A times, 50,856 Mode T
  times), 13,440 tamper and 3,360 interrupted-write cases (implementation v1, historical;
  v2: 11,200, see below), 1,120 persistence checks and
  840 lost-fact tests, 544 conformance checks; controls: K1 61,420 informative cases from
  135 pairs, K2 4,040 from 60 pairs (families P1, P7, P8, T3, T4, T5 - where outranked
  claims exist), K3 126,828 from 140 pairs. Measures: logical size of the checkpoints 461,418
  claims for 583,544 prefix reports (79 %); canonical bytes 59.5 MB against 127.1 MB (47 %);
  after generic compression (gzip) the checkpoints are LARGER than the raw prefixes (13.0 MB
  against 12.1 MB) - the raw log compresses better than the consolidated JSON; the logical
  gain does not carry over to compressed bytes in these worlds.
- Holdout audit before the freeze (R only, freeze43.py without --write): bound counts equal
  to config/round43_counts.json, 0 id-contract violations, 0 K3 collisions; controls K1 240,184 informative cases from 540 pairs, K2 16,884 from 240 pairs,
  K3 503,144 from 560 pairs - each control sufficient (>= 30 cases, >= 10 pairs). The
  cross-fact audit was added to the audit after that dry run and counted separately on all
  4,480 holdout world-delay instances: 0 correction / retraction targets in another fact and
  0 missing targets (it is part of the audit the freeze runs).
- Joe's check: docs/ROUND_4_3_joe_cases.md (bench/m3/joe_cases43.py; five development cases
  chosen by rule).
- Astra's implementation review v1 (reviews/2026-10-25_r43impl_astra.txt, REQUEST CHANGES;
  package reviews/packages/LAB_R43_IMPL_v1.txt) - both deviations (controls from R's table;
  R's answers on the asked facts with the cross-fact audit) accepted; three changes
  required before the freeze, all done:
  (1) write protocol - a grown tail under the SAME checkpoint overwrote
      tail_<checkpoint>.jsonl before the new trust record was committed (her reproduction:
      a crash then left the old record pointing at an overwritten file). Now every state
      file is content-addressed and written only once (temp + rename, never overwritten):
      checkpoint_<hash>.json and tail_<hash>_<seal count>_<seal head>.jsonl; write_state
      writes checkpoint, tail and the local record; the caller commits the record to its
      EXTERNAL trusted copy and only then calls finish_state, which removes the files the
      committed record does not name. The interrupted-write cases now restart through the
      external record (the regular path): two scenarios (a new checkpoint; the same
      checkpoint with a grown tail) x (crash after step 1 / 2 / 3 before the external
      commit -> old state; after the commit, before and after finish_state -> new state) =
      10 cases per world-delay instance; her reproduction is a hand case.
  (2) the digest partition is checked in the full run for every digest answer of Mode A
      and every in-scope one of Mode T: its claim entries equal the standing claims of the
      fact at the digest's knowledge time (complete, equal fields, no duplicates).
  (3) completeness counters bound: config/round43_counts.json v2 (bench/m3/counts43.py,
      model-free from questions, cuts and the fixture) adds per family the expected numbers
      of full-state comparisons (checkpoints, Mode A times, Mode T times) and of digest
      partition checks (Mode A, Mode T) and the exact number of conformance checks (544);
      the collector requires the executed counts to equal them (holdout: 66,392 + 23,096 +
      200,088 full-state comparisons, 21,112 + 185,528 partition checks).
  Her improvement ideas, done: a test that R on the whole world and R on the asked facts
  agree (first pair of every family, delays 50 and 500); Mode A reads measured as claims
  loaded / reports applied / reports scanned; a freeze id (SHA-256 of the freeze) recorded
  in the freeze, the collector summary and RUN.txt of every run, so the freeze, the first
  holdout run and any repeat attempt are logged together.
  Development rerun (docs/ROUND_4_3_dev_SUMMARY.md): PASS, zero violations; the new
  counters: 11,200 interrupted-write cases, 52,216 digest partition checks (5,296 + 46,920),
  full-state comparisons 16,672 + 5,840 + 50,856, conformance 544 - all equal to the bound
  numbers.
- Astra's implementation review v2 (reviews/2026-10-25_r43impl_v2_astra.txt): the three
  changes confirmed; one start error found - a careless text replacement of mine had also
  changed the plan step of .github/workflows/round43.yml to open a file named literally
  "'$RUNNER_TEMP/code/config/round43.json'" (the copy under RUNNER_TEMP exists only in the
  collect job). Fixed (plan step reads config/round43.json after the checkout); the plan
  step was executed exactly as written in the workflow for run / holdout, audit / holdout
  and run / dev (all three produce the expected outputs and matrices), and the whole
  workflow was then run once on the DEVELOPMENT split in GitHub Actions (no holdout, no
  freeze) - see the next item. Her ideas: the Mode A read counters are now summed after
  the full-state checks (they cover all Mode A replays, answers and full-state checks);
  the older numbers of interrupted-write cases are marked as historical (implementation v1).
- Workflow check on the development split in GitHub Actions (run 40175548082, commit
  e62e72c, results branch round43/run_40175548082_1; no freeze, no holdout): plan, the 14
  family jobs (each with the unit tests) and the collector all succeeded; verdict PASS with
  exactly the numbers of the local development run (zero violations; 11,200 interrupted-
  write cases, 52,216 digest partition checks, 73,368 full-state comparisons, 544
  conformance checks; RUN.txt records the freeze id, here None). The Mode A read counters
  now include the full-state checks: 192,409 claims loaded, 26,652 reports applied,
  360,838 reports scanned.
- Astra's implementation review v3 (reviews/2026-10-25_r43impl_v3_astra.txt): APPROVE of the
  freeze of the checked state and the single holdout run. Freeze written by
  bench/m3/freeze43.py --write into config/round43.json (R only, H not run on the holdout
  before): per-family digests of worlds and R's answers, audit OK (bound counts, 0 id-
  contract violations, 0 K3 collisions, 0 cross-fact targets), controls sufficient, the
  counts-file and code hashes, and the freeze id. Her improvement idea (the plan-step test
  of the three configurations as an automated regression) is added AFTER the holdout run, so
  that the frozen and approved state is the one that runs.

## 10. Holdout result (attempt 1 - the only run)

Run 40176926486 on commit 7ecb696, freeze id e93142c93d5c4b0baa8592e41b0ba1d16d33fb25a7483ea66bc8e723844d814f
(results branch round43/run_40176926486_1; docs/ROUND_4_3_holdout_SUMMARY.md): 14 family jobs
and the collector succeeded; worlds and R's answers equal the freeze digests, the code equals
the frozen code. VERDICT: PASS - zero violations of every rule (1)-(8), every bound number
reproduced exactly:
- 560 pairs, 4,480 world-delay instances, 66,392 cuts; Mode A 126,540 answers identical to M
  (and M = R on every question, digests of H, of the full store and of R identical); Mode T
  2,135,976 evaluations - every in-scope answer identical to M, every question that needs a
  knowledge time before its cut answered "compacted"; R on every checkpoint written as
  synthetic reports equal to R on the full reports for every in-scope question;
- composition: 61,912 consecutive cut pairs byte-identical (incremental = scratch with the
  same parent; payload independent of the chain; every chain rebuilt in a second process
  identical);
- full state over ALL facts: 289,576 comparisons (66,392 checkpoints, 23,096 Mode A and
  200,088 Mode T knowledge times) equal to the independent reference state; 3,360 lost-fact
  negative tests detected;
- digest partition: 206,640 checks (21,112 Mode A, 185,528 Mode T) - every standing claim
  exactly once with equal fields;
- source binding by role on every answer: value evidence standing at its knowledge time,
  change evidence inside (k1, k2], effectiveness of every tail correction / retraction equal
  to R's;
- integrity: 53,760 tamper cases detected (12 per instance, incl. internally consistent
  forgeries and a cut-off tail found only through the trust record, and the id rule);
  44,800 interrupted-write cases restarted on the correct consistent state through the
  external trusted record; 4,480 persistence checks across processes;
- controls: H on each control claim set answered exactly as R on it; informative cases equal
  to the pre-freeze audit - K1 240,184 (540 pairs, all 14 families), K2 16,884 (240 pairs;
  P1, P7, P8, T3, T4, T5), K3 503,144 (560 pairs, all families): dropping the outranked
  claims (K2), keeping only the current version (K1) or losing the claim identities (K3)
  each produces wrong answers exactly where predicted;
- conformance set: 544 checks through Modes A and T at every cut.
Measures (report only): the checkpoints hold 1,843,840 claims for 2,332,104 prefix reports
(79.1 %) and 237.8 MB of canonical JSON for 508.1 MB (46.8 %); after gzip they are LARGER than
the compressed prefixes (51.8 MB against 48.4 MB, +7 %). Mode A, all replays incl. the
full-state checks: 762,749 claims loaded, 112,236 reports applied, 1,436,784 scanned.
Claim (within the limits fixed in advance): on the structured worlds of the round 4.0 / 4.1
generators and under the round 4.0 source policy, the memory's growing report log can be
replaced by a checkpoint of the standing claims plus the later reports without changing any
answer or any cited report id; every consolidated item stays bound to its original report
and verifiable against the archive; after the archive prefix is deleted the memory answers
"compacted" instead of a wrong value; and the source-bound digest (segments with
supporting, agreeing and dissenting claims and independent origins) is reproduced exactly by
the independent reference. This is the pass of a finite test suite (14 families x 40 pairs),
not a general error rate; it is about lossless consolidation of the logical state - the
measured gain is in what a question reads and in verifiable source binding, not in
compressed bytes (section 7); no language input, no retrieval budget, no LM summary.
Afterwards (not part of the run): Astra's idea from the implementation review v3 - the plan
step of the workflow executed for the three configurations as an automated regression test
(tests/test_round43_workflow.py; it fails on the old start error).
