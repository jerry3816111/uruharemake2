# M57.4 Independently Attributable Component-Evidence Collection and Quarantine — Acceptance

Date: 2026-09-04

Decision: **PASS as a bounded collection-mechanics milestone; real component evidence is still 0 and formal M57/M58 remain denied**

Single changed variable: add the missing role-separated, pre-outcome collection and quarantine path that can project
two sealed coder ledgers plus one sealed adjudicator ledger into the exact frozen M57.2 evidence manifest. No M56
sample, prediction, model, answer, score or resource rule, and no M57 stage definition, statistic, threshold, M57.2
manifest rule or M57.3 result bridge was changed.

## Problem and why this milestone is necessary

M57.2 previously defined the finished 30-row component-evidence object, but the repository had no operational path
for two coders and a distinct adjudicator to produce it. Direct in-memory construction could not show which source a
role saw, when it was seen, whether the coders were independent, whether disagreements were preserved, or whether a
record changed after the target outcome became available. V7's existing 18-slot persona-source coding surface asks a
different research question and cannot substitute for the M57.2 component schema.

M57.4 therefore creates three private ledgers, source-view receipts, append-only revisions, independent coder seals,
a two-seal adjudication gate, computed disagreement flags and a pre-outcome export barrier. It makes a future human
collection auditable at the application level; it does not manufacture the missing humans.

## What was implemented

The public workflow has five frozen operations: initialize a three-role collection, record a source view, save a
source-bound entry, seal a role ledger and export the final manifest. A real collection requires three distinct
pseudonyms and explicit human, non-model and different-person attestations. Random role tokens are stored only as
SHA-256 hashes. A clearly private synthetic initializer exists only for mechanics tests.

Each action revalidates the exact M57.1 pre-outcome commitment and refuses to proceed if any M56 outcome-state marker
exists. Coders can see only the current permitted source and their own ledger. A save is impossible without a
server-timestamped view receipt; post-cutoff history identifiers, outcome fields and invented private-state fields
fail closed. Revisions are retained rather than overwritten, and a sealed ledger cannot change.

The adjudicator cannot see either coder contribution until both complete 30/30 ledgers are sealed and hash-valid.
The adjudicator resolves perception and retrieval while preserving both raw contributions, records a source-bound
observable state proxy, and cannot declare away a disagreement: the flags are computed from the two coder payloads.
Only after all 30 adjudications and the third seal may export create the exact M57.2 manifest. Export does not start
the 90 component predictions, open the target outcome, write production memory or authorize M58.

## Isolated complete rehearsal

One author-constructed run exercised the full workflow:

- three synthetic roles, 90 source views, 60 coder entries and 30 adjudicator entries;
- 60 perception and 60 retrieval contributions, 30 observable state proxies and 60 adjudications;
- two coder seals plus one adjudicator seal;
- six perception disagreements and eight retrieval disagreements, retained and resolved;
- one M57.2-shaped engineering manifest accepted by the explicitly internal validator and rejected by the public
  formal validator;
- successful identical export replay without an overwrite;
- zero real model calls, zero real target-outcome access, no M57.2 prediction execution and no M58 authorization.

The first rehearsal incorrectly reported 30/30 disagreements because the synthetic coders used different explanatory
prose on every row. That was a fixture-design error, not a desired result. Before freeze, the fixture was changed so
only deliberate semantic differences remain; the retained result is six perception and eight retrieval disagreements.

## Failure analysis and fail-closed evidence

The tests reject repeated pseudonyms, absent human attestations, unsafe run identifiers, wrong role tokens, coder
cross-ledger access, adjudicator access before both coder seals, save-before-view, post-cutoff history, forbidden answer
keys, private-state fabrication, partial seals, post-seal mutation, changed ledger/seal/manifest hashes, overwrite and
any outcome marker appearing before initialize/view/save/seal/export. A shuffled but otherwise valid roster is accepted;
JSON object key order is not treated as participant identity.

During Safari form testing, accessibility element indices changed after each field update. The first multi-field
attempt therefore placed values in the wrong controls. No submission occurred. The page was reread, each field was
selected and corrected individually, and only the corrected form was submitted. Safari redirected from sample 1 to
sample 2. The private ledger then showed exactly one revision, two view receipts, the exact submitted values and zero
outcome/model access. A first command-line check incorrectly queried nonexistent top-level `revisions` and
`source_view_receipts` keys and returned zeros; checking the actual `entries` and `source_views` structure confirmed
the save. Neither checking mistake was hidden as a product success.

## Verification

- focused M57.4: **11/11 passed** in 70.81 seconds;
- adjacent M56.10 + M57/M57.1/M57.2/M57.3/M57.4: **85/85 passed** in 165.40 seconds;
- selected M1/M2/M6/V7/V9/M54–M57.4 compatibility: **409/409 passed** in 252.66 seconds;
- Python compilation, JSON parsing, screenshot format/hash/dimensions, saved-rehearsal validation, frozen file hashes,
  stopped local services and Git whitespace checks passed;
- no historical frozen scorer, predictor, analyzer, threshold, result or holdout artifact was edited.

These are selected repository suites and an author-constructed mechanics rehearsal. They are not formal component
observations, an independent human study or a complete repository test claim.

## Cost

Seven isolated full 90-view/90-entry/three-seal/one-export rehearsals measured a median **54.224564 seconds**, range
**54.176508–54.772366 seconds**, and exactly **685,646 bytes** across nine durable artifacts per run. All seven internal
engineering manifests were valid; none passed the public formal validator or became formal evidence.

This measures repeated Python validation, role-token checks, hashing, atomic writes and full-sync barriers. It excludes
human coding/adjudication time, real model latency, energy, adversarial identity security and production throughput.

## Safari graphical and functional acceptance

Safari displayed `http://127.0.0.1:7926/dashboard` with the two private coder lanes, dual-seal gate, adjudication and
M57.2 export boundary. It visibly retained `REAL HUMAN EVIDENCE 0`, V7 `0/18 + 0/18`, real rows `0/30`, outcome/model
access `0/0`, formal M57 denied and M58 denied. The page also displayed the 60/30/90 rehearsal counts and six/eight
disagreements without visible horizontal overflow.

The functional collector at `127.0.0.1:7927` used a temporary synthetic run. Coder A saw the permitted source,
available cutoff history and its own fields, but no Coder B content or target outcome. One corrected form submission
persisted exactly one revision and redirected to the next sample. Safari remained **35 → 35** tabs; no tab was created
or closed. An unrelated external-app prompt was cancelled. The reused M57.4 test tab is safe to close, and both local
servers were stopped. Evidence:

- `analysis/m57_4_safari_component_evidence_collection_acceptance_2026-09-04.json`;
- `analysis/m57_4_safari_component_evidence_flow_2026-09-04.png`;
- `analysis/m57_4_safari_component_evidence_boundary_2026-09-04.png`.

## Contribution to the human-response-equation goal

M57.4 closes a provenance gap between a theoretical component-evidence schema and a future falsifiable experiment.
If a later M57 result says that perception, retrieval or observable state is the leading recoverable error, the input
evidence can now be traced to two independent pre-outcome contributions, a preserved disagreement and a third-role
resolution instead of an author-built object written after seeing the answer.

It still does **not** establish that the three pseudonyms are three physical humans, that their labels are correct,
that a private emotion or intention was recovered, that any Uruha component caused an error, that Equation V1 is
valid, that UruhaBrain beats a baseline or that the human-response equation has been solved. Tokens and self-attestation
are cooperative provenance controls, not signatures or adversarial identity proof. Live counts remain V7 `0/18 +
0/18`, real temporal rows `0/30`, real M57 component rows `0/30`, formal M56/M57 results `0` and M58 denied.

## Next necessary milestone

M57.5 should add separate participant-capability issuance and token-surface hardening without modifying the frozen
M57.4 evidence semantics. The current coordinator receives all three bearer tokens, and the functional collector puts
one token in the command line and URL. The next wrapper should issue role capabilities through separate one-time,
permission-restricted envelopes, keep tokens out of argv/URL/browser history, establish a secure local cookie session,
and prove one role cannot derive or consume another role's capability. This still cannot prove physical identity;
external study oversight remains required. No formal result, target outcome or M58 work may begin.
