# M57.3 Sanctioned Outcome-to-Analyzer Bridge — Acceptance

Date: 2026-09-04

Decision: **PASS as a bounded result-path engineering milestone; live formal M57 remains absent and M58 remains denied**

Single changed variable: add one sanctioned, crash-safe post-result bridge from the already committed M57.2
component predictions to the withheld observable outcome and the unchanged M57 analyzer. No M56 prediction, score,
model, sample, resource rule or M57 statistic was changed.

## Problem and why the bridge is necessary

Before M57.3, M57.2 had 30 rows and 90 source-bound, answer-free perception/retrieval/state predictions, but exactly
zero observed labels and zero decision ceilings. Its schema could not enter the frozen M57 analyzer. The M57 formal
entry also intentionally rejected any caller-built real bundle because a boolean `formal_authorization` could not be
trusted.

An attempted label reconstruction from the completed M56 aggregate score report was not viable: on the retained
30-row forged full chain, all 30 labels were ambiguous from the B5/Ours paired deltas. The bridge therefore does not
infer labels and its public APIs accept no labels, bundle, provider, readiness or authorization—only `run_id`.

## What was implemented

Before outcome access, the public path revalidates the exact M57.1 mode, every M57.2 evidence/schedule/capsule/ledger/
commitment artifact, and the complete M56.8/M56.10 gate/intent/checkpoint/report/result chain. Author-constructed
evidence is rejected before an M57.3 mode, intent or loader call.

M57.3 then holds the same per-run scoring lock and records:

1. a bridge mode binding the frozen M57 analyzer implementation and exact upstream hashes;
2. a no-retry intent before private diagnostic outcome access;
3. one separately named M57 diagnostic private-outcome load;
4. a private full-sync joined checkpoint containing 30 observed labels, the unchanged 90 pre-outcome component
   predictions, 30 post-outcome decision one-hot diagnostic ceilings and unavailable realization rows;
5. an aggregate result without per-sample labels and a SHA-bound result commitment.

The M57.3 diagnostic load is explicitly distinct from the one M56 scoring load. A successful complete research run
therefore has two named uses of the private outcome: one for the primary score and one for component localization.
Successful replay or restart from a valid checkpoint adds zero loads. Intent without checkpoint is terminal because a
restart cannot know whether the outcome was already opened.

The joined rows are mechanically projected to the exact accepted synthetic bundle shape and passed to the unchanged
`analyze_component_substitution_bundle`. The projection has no formal authority; the M57.3 wrapper is formal only when
the complete upstream evidence was real. M58 planning additionally requires a real formal result with one
unambiguous eligible leading stage; a merely valid or ambiguous formal bridge would not be enough.

## Isolated full-chain rehearsal

One temporary author-constructed run exercised M57.1 → M57.2 → M56.10 → M57.3:

- M56 scoring outcome loads: **1**;
- M57 diagnostic outcome loads: **1**;
- successful M57 replay additional loads: **0**;
- observed labels joined: **30**;
- unchanged pre-outcome component predictions: **90**;
- post-outcome decision ceilings: **30**;
- available stage rows: **120**;
- realization ratings/stage availability: **0 / unavailable**;
- real model calls / real target-outcome accesses: **0 / 0**;
- formal M57 result / M58 authority: **false / false**.

The unchanged analyzer returned no eligible recoverable effect on this deliberately uninformative mock distribution.
That is retained as an engineering result, not interpreted as a Uruha component finding.

## Failure analysis and fail-closed evidence

The first test command used the system Python 3.14 interpreter, which has no pytest package, so no test was collected.
The repository's existing Python 3.12 pytest executable was then used; no dependency was installed or relaxed.

The first focused run had two failed tests. One attempted to simulate a probability mutation by copying a second row,
but the deterministic mock produces identical probabilities for every row, so the payload had not actually changed.
The test now swaps two unequal label probabilities. The other expected a later error phrase, while the public path
correctly rejected the forged evidence earlier at the M57.2 formal-policy gate. The assertion now accepts the exact
earlier fail-closed boundary. No implementation rule was weakened.

Final coverage rejects missing M57.2 or M56.10 chains, author-constructed public execution/validation, upstream capsule
mutation, private outcome/hash/label mutation, pre-outcome probability mutation, observed-label mutation, decision
ceiling/timing mutation, checkpoint/result/commitment mutation, and intent-only retry. It also verifies checkpoint
restart without reload and that the aggregate result omits per-sample labels.

## Verification

- focused M57.3: **14/14 passed** after the frozen implementation artifact was added;
- adjacent M56.10 + M57/M57.1/M57.2/M57.3: **74/74 passed** in 94.30 seconds;
- selected M1/M2/M6/V7/V9/M54–M57.3 compatibility: **398/398 passed** in 185.00 seconds;
- Python compilation, six initial JSON artifacts, saved-rehearsal validation, frozen file hashes and Git whitespace
  checks passed;
- unchanged M57 projection analyzer is SHA-bound and its existing clear/tie behavior remains covered by the selected
  suite;
- no historical scorer, prediction, result, threshold, formal outcome or frozen analyzer file was edited.

These are selected repository suites and author-constructed full-chain mechanics, not every historical repository
test and not a formal model-performance run.

## Cost

Seven isolated full-chain fixtures measured:

- private join plus unchanged 20,000-bootstrap analyzer median **2.100255 s**, range **2.081292–2.125582 s**;
- complete fixture wall median **6.343483 s**;
- five M57.3 durable artifacts **214,530 bytes** per last run;
- 1 M56 fixture outcome load + 1 M57 fixture outcome load, with 0 replay loads;
- 90 mocked earlier component calls, but **0 real model calls** and **0 real target-outcome accesses**.

These numbers measure Python validation, hashing, full-sync writes and numeric bootstrap work. They do not measure
human annotation, the future 90 real local-model component calls, model energy/latency or production throughput.

## Safari graphical acceptance

Safari reused the existing M57.2 tab and loaded `http://127.0.0.1:7925/dashboard`. The page visibly showed the six-step
flow, separate M56 and M57 one-load purposes, successful replay zero, 30/90/30/120/0 stage counts, private checkpoint,
unchanged analyzer and aggregate-only boundary. It also retained `FORMAL M57 DENIED`, V7 `0/18 + 0/18`, real rows
`0/30`, formal result `0` and M58 denied.

The page had no form or visible horizontal overflow. Safari stayed **34 → 34** tabs, with no tab created or closed. The
read-only M57.3 test tab is safe to close. The local server was stopped. Evidence:

- `analysis/m57_3_safari_outcome_bridge_flow_2026-09-04.png`;
- `analysis/m57_3_safari_outcome_bridge_boundary_2026-09-04.png`;
- `analysis/m57_3_safari_outcome_analyzer_bridge_acceptance_2026-09-04.json`.

## Contribution to the human-response-equation goal

M57.3 closes a real falsifiability gap. A future aggregate Ours result can now be decomposed only through component
predictions that existed before the answer, labels read from the sanctioned private source, an explicit decision upper
bound and the already frozen statistics. This prevents a researcher or caller from silently choosing labels or
component outputs after seeing the result. The resulting aggregate can distinguish a recoverable observable stage,
an ambiguous interaction or no recoverable effect while preserving the error rather than inventing a cause.

This still does **not** show that any real Uruha component is wrong, that the independent annotations are correct, that
private emotion or intent was recovered, that Equation V1 is valid, that UruhaBrain beats B5, or that a human-response
equation has been solved. The hashes are cooperative integrity controls, not signatures against a malicious same-user
process. The public result intentionally omits row labels, while the private checkpoint still contains them.

## Next necessary milestone

M57.4 should provide the missing independently attributable component-evidence collection and quarantine path. M57.2
defines what two coders and a distinct adjudicator must contribute, but the project still has no collection instrument
that binds those identities, source viewing, timestamps, disagreement/adjudication and pre-outcome export into the real
manifest. M57.4 may test that workflow with clearly synthetic records, but it must not fabricate the three humans or
unlock the live path. M58 remains prohibited until the external V7/V9/M55/M56 chain and a real, unambiguous M57 result
exist.
