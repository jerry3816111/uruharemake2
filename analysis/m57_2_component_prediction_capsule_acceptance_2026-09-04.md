# M57.2 Pre-Outcome Component Prediction Capsule — Acceptance

Date: 2026-09-04

Decision: **PASS as a bounded engineering-prediction milestone; no formal M57 component result or M58 authority**

Single changed variable: turn the already frozen generic M57 stage plan into a concrete, sample-level, source-bound
evidence and substitution-prediction capsule before M56 outcome access. The M56 samples, original predictions, model,
hardware, decoding options, scoring and no-retry rules, and the frozen M57 statistics remain unchanged.

## Problem and why this layer is necessary

M57.1 proves that the five-stage diagnostic plan and exact M56 run context can be committed before the answer. It did
not bind a concrete evidence source for any sample, define which component value would actually replace the original,
schedule a downstream recomputation, or commit a replacement prediction. The retained pre-change probe measured:

- generic M57 stage plans: **5**;
- concrete evidence-manifest binding: **0**;
- component-prediction schedule binding: **0**;
- 30-row component-prediction capsule binding: **0**;
- real target-outcome access / formal M57 result: **0 / 0**.

Without M57.2, a future component prediction could be created after the M56 result and could not honestly support an
outcome-blind error-localization claim.

## What was implemented

The formal execution and validation APIs accept only `run_id`. Under the same nonblocking per-run lock as M56 scoring,
the executor requires the exact immutable M57.1 mode, rejects first execution after any M56 outcome-state marker, and
loads only the generation, commitment and telemetry compartments.

For each of the same 30 M56 samples, the manifest must bind all five stages to the exact source-information hash:

- **perception** — two distinct pre-outcome coders and a distinct adjudicator resolve an observable-only input
  representation;
- **retrieval** — two distinct pre-outcome coders and a distinct adjudicator select only history IDs available at or
  before the frozen cutoff;
- **state** — one source-bound observable proxy may replace only the six observable/derived state variables; transient,
  relationship and goal/need private variables are rejected;
- **decision** — unavailable before the withheld outcome; its one-hot value remains a later diagnostic ceiling and is
  not allowed in this capsule;
- **realization** — unavailable without independent blind human surface ratings.

Available perception, retrieval and state interventions remove the named original component and its downstream
artifacts, then ask the exact Ours model under the same provider options and input/output token budgets for a fresh
13-label probability distribution. The ordered schedule is full-synced before the first call. Every call records actual
tokens, latency, CPU, process/Ollama memory, duration fields, model identity and content hashes. The complete call
ledger, prediction capsule and hash commitment are then full-synced before any outcome may be opened.

The capsule includes the original M56 Ours distribution and all available replacement distributions but deliberately
has no observed label. This gives a later result bridge a bounded, verifiable input without letting M57.2 score itself.

## Isolated engineering rehearsal

One temporary, author-constructed 30-row evidence manifest made all three pre-outcome stages available. The response
provider was mocked, so the rehearsal measured mechanics rather than model quality:

- samples × available stages: **30 × 3**;
- ordered schedule steps: **150** (all five stages represented);
- available substitution predictions: **90/90**;
- mocked calls: **90**; real model calls: **0**;
- real target-outcome reads: **0**;
- decision availability before outcome: **false**;
- realization availability without human ratings: **false**;
- formal M57 results / M58 authority: **0 / false**.

The public formal API was then given the same author-constructed evidence. It rejected it before creating a schedule
and before any model call. Engineering validation can inspect such a fixture, but the fixture cannot mint formal
authority merely by being structurally complete.

## Failure analysis and fail-closed coverage

Tests reject missing or path-escaping runs, missing M57.1 mode, dependency drift, evidence/source hash drift, duplicate
sample order, post-cutoff history IDs, the same coder appearing twice, duplicate contribution IDs, an adjudicator who
is one of the coders, invented private-state variables, forbidden outcome keys and pre-outcome decision evidence.

Execution also fails terminally on model-identity drift, actual token-budget overflow, invalid probability mass or a
transport failure. Once a schedule or failure record exists, the same run ID cannot retry. A concurrent M56 outcome
join is denied while M57.2 holds the shared lock. Capsule resource options, call prompt hashes, ledger/capsule hashes,
call sets and partial output mutation all fail closed. A review also found that the first public validator returned a
forged engineering capsule as structurally valid even though the executor rejected it. That could let a future bridge
misuse `valid` without checking `data_kind`; the public validator now reports forged capsules invalid, while only an
explicitly named internal validator can inspect engineering fixtures. The old freeze hash test failed immediately after
this safety edit, as intended, and passed after the implementation freeze was regenerated.

During Safari automation, an initial key-combination spelling and a scroll without an element index were rejected by
the UI-control API. The documented `super+l`, explicit paste format and current HTML element index were then used.
These were tool-invocation errors, not page or research failures; they created no extra tab, submitted no form and
changed no formal data.

## Verification

- focused M57.2: **17/17 passed**;
- adjacent M54–M57.2 chain: **312/312 collected**, with the whole selected run below green;
- selected M1/M2/M6/V7/V9/M54–M57.2 compatibility: **403/403 passed** in 126.29 seconds after the validator-boundary repair;
- Python compilation, JSON parsing, frozen dependency hashes and Git whitespace checks passed;
- unchanged M57 clear fixture still identifies retrieval, and the tied fixture still abstains;
- no package, threshold, frozen outcome, scorer or prior milestone was modified.

These are selected repository suites and mocked engineering generation, not every historical repository test and not
a formal model-performance run.

## Cost

Seven isolated forged runs measured the M57.2 Python/hash/full-sync/mocked-call path:

- median **0.374307 s**, range **0.371192–0.401570 s**;
- last-run evidence, schedule, capsule, call ledger and commitment: **826,603 bytes** total;
- mocked calls per run: **90**; real model calls per run: **0**;
- real target-outcome access per run: **0**.

A future fully available formal capsule has a maximum of 90 local `qwen3.5:9b` calls. Actual prompt/completion tokens,
wall time, CPU, memory and Ollama durations will be taken from that run's call ledger. The current timings must not be
reported as model latency, energy use or production throughput.

## Safari graphical acceptance

Safari loaded `http://127.0.0.1:7924/dashboard` in the existing tab and visibly showed:

- M56 original prediction → component evidence → downstream recomputation → immutable prediction capsule;
- the three pre-outcome available layers and why decision/realization are unavailable;
- M57.1's five generic plans versus M57.2's 90 engineering predictions;
- 826,603 bytes, 90-call formal maximum and per-call resource-record requirement;
- `FORMAL M57 DENIED`, V7 `0/18 + 0/18`, real temporal rows `0/30`, formal result 0 and M58 denied;
- explicit `author-constructed / mocked` labelling and no visible card/horizontal overflow.

Safari remained at **34 → 34** tabs; none was created or closed. The read-only M57.2 tab is safe to close. The local
server was stopped. Evidence:

- `analysis/m57_2_safari_component_prediction_flow_2026-09-04.jpeg`;
- `analysis/m57_2_safari_component_prediction_boundary_2026-09-04.jpeg`;
- `analysis/m57_2_safari_component_prediction_acceptance_2026-09-04.json`.

## Contribution to the human-response-equation goal

M57.2 makes a future error-localization result meaningfully more falsifiable. It no longer says only “we planned to
replace memory”; it can show, for every timestamped sample, which pre-cutoff evidence was used, what replacement was
committed, which downstream information was removed, what the same model predicted after the intervention, and what
the computation cost—all before the answer was visible. This is a necessary bridge from an aggregate M56 win/loss to
testing whether perception, retrieval or observable computational state is a recoverable source of error.

It does **not** establish that the author-constructed annotations are correct, that any real Uruha component is wrong,
that a private emotion or intention was recovered, that Equation V1 is valid, that UruhaBrain beats a strong LLM, or
that a human-response equation has been solved. It also adds no product-facing memory, Japanese dialogue, VRM or
Function Calling capability in this milestone. Distinct coder/adjudicator IDs and content hashes are cooperative
provenance controls, not cryptographic proof that three real people supplied the records; a future formal collection
instrument must bind those records to its independently audited human ledgers.

## Next necessary milestone

M57.3 must be a result bridge, and it is result-dependent. It may run only for a real run that already contains a valid
M57.1 mode, complete M57.2 pre-outcome capsule and sanctioned M56.10 result. It must read the outcome exactly through
the existing authorized chain, add the decision diagnostic ceiling, preserve unavailable realization evidence, and
materialize the exact input expected by the unchanged M57 analyzer. It must never accept caller-supplied labels or
turn an engineering fixture into formal evidence.

The external scientific dependency remains unchanged: two different humans must first complete V7, followed by V9,
boundary/adjudication, 30 leakage-free temporal rows and authorized M56. No formal M57 result means no result-driven
M58 implementation or claimed leading component.
