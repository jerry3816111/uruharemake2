# M55 Two-Coder Boundary Extension Tool Acceptance · 2026-09-01

## Decision

**Collection-tool engineering gate: PASS. Human evidence gate: BLOCKED. M55: INCOMPLETE. M56: NOT AUTHORIZED.**

This checkpoint makes the required prospective boundary work possible without changing frozen V7 or
V9 artifacts and without pretending that a program can replace two independent people. It adds no
real-person labels, performs no model calls, and does not access sealed future sources.

## The problem closed

V9 records the beginning and end of a completed observable event. That whole interval is appropriate
for behavior coding, but unsafe as a prediction input because it may already include the behavior being
predicted. M55 therefore needs each coder to independently mark:

```text
event start <= observable input start < prediction cutoff
prediction cutoff < observable behavior start < behavior end <= event end
```

The new instrument keeps those fields in a separate private ledger beside the coder's own V9 entry.
It never edits the V9 event and binds every extension row to the exact V9 entry digest.

## What was implemented

- a SHA-bound contract with 7 frozen dependencies and 17 required entry fields;
- one gitignored, atomically written private boundary ledger per coder;
- a token-gated local browser page that loads only one coder's V9 ledger and boundary ledger;
- a direct official-source link to the coder's own selected event time;
- separate pre-cutoff input paraphrase and completed-event historical summary fields;
- strict rejection of raw/verbatim/model/private-state keys, false attestations, stale V9 entry hashes,
  invalid time order, and non-finite time values;
- real initialization and serving blocked until the genuine V7 reliability lock passes;
- a second fail-closed check preventing a synthetic ledger from being served as real collection data;
- cross-coder comparison only after two complete, valid, distinct ledgers of the same data kind exist;
- a text-free comparison report containing only slot digests, interval IoU, cutoff differences, and
  digest-equality flags;
- no automatic timestamp averaging, text selection, formal record-pack authorization, M55 completion,
  or M56 authorization; every paired row requires explicit human adjudication;
- an outsider-readable synthetic dashboard showing two private lanes, X/cutoff/Y, divergence, the
  adjudication gate, and the remaining human-data dependency.

## Failure-oriented review

The implementation review found and closed four risks before freezing the tool:

1. Python infinity or NaN-like values could otherwise evade an ordinary nonnegative-number check;
2. a synthetic ledger could otherwise be passed to the real server after a valid V7 lock existed;
3. synthetic and real ledgers could otherwise be compared together;
4. the source V9 ledger could change after server start unless every page load revalidated its digest.

All four now fail closed. A source change produces HTTP 409 and a visible stop message rather than
continuing annotation against stale data.

## Evidence

### Contract and deterministic tests

- focused boundary/M55 suite: **32/32 passed**;
- M54 + V7 + V9 + M55 compatibility suite: **67/67 passed**;
- Python compilation: PASS;
- `git diff --check`: PASS;
- contract validation: PASS;
- contract hash: `52426afc62060eaf46c84eec9834c3f7ef78841f63c027b0c70043fd91a41e2e`;
- model calls: 0;
- production-memory writes: 0;
- target-content rows read or created by the synthetic demo: 0.

The first attempts used the system Python 3.14 and bundled Python, neither of which had pytest. No test
case ran in those attempts. The installed project test executable at Python 3.12 was then used. This is
an environment-selection failure, not a failed research result.

### Live readiness evidence

The refreshed readiness audit remains deliberately negative above the engineering layer:

- pre-content readiness: true;
- V7 human ledgers: 0/18 and 0/18;
- V9 independently reviewed Uruha events: 0/30;
- leakage-free real temporal rows: 0/30;
- real boundary collection authorized now: false;
- automatic cross-coder merge allowed: false;
- M55 complete: false;
- M56 authorized: false;
- blocker: `complete_two_independent_v7_18_slot_ledgers`;
- readiness report hash: `137489976bd2b49cdf721849fed2444b90ab1640cbcc40eb39805c748f5927eb`.

### Safari graphical evidence

Safari was inspected at `http://127.0.0.1:7904/dashboard`. The visible page showed:

- an explicit `synthetic tool demo, not a human result` warning;
- independent Coder A and Coder B lanes;
- input interval, locked cutoff, and future behavior interval for each lane;
- input IoU 0.80, behavior IoU 0.83, and a one-second cutoff difference;
- automatic merge forbidden;
- the full V7 → V9 → M55 boundary → human adjudication → 30-row dependency;
- Uruha boundary rows = 0 and M56 forbidden.

The page fit in the visible Safari window without overflow. The existing M55 tab was reused; Safari
remained at 27 tabs, with no tab opened or closed and no human form submitted.

## Contribution to the long-term equation objective

This closes a necessary measurement-instrument gap. If M55 later observes a behavior `Y`, the record
can now prove which evidence `X` ended before the prediction cutoff, rather than retroactively using a
completed event as input. It therefore improves temporal validity and future-leakage control for the
candidate human-response equation.

It does **not** yet show that Equation V1 predicts Uruha, that two people agree on the boundaries, that
any latent variable corresponds to private psychology, or that UruhaBrain beats B0–B5. Those require
the real V7 and V9 human work, explicit adjudication, compilation of 30 real rows, and a separately
frozen M56 comparison protocol.

## Exact continuation

1. Two different people independently finish the frozen V7 18-slot pilot.
2. Run the unchanged V7 reliability analyzer; preserve a failure and revise only through a new frozen
   pilot if the gate fails.
3. Only after a genuine pass, initialize each person's V9 and M55 boundary sites.
4. After both complete all 30 slots, compare without text exposure and run explicit human adjudication.
5. Compile exactly 30 leakage-free cutoff-to-future rows under the M55 temporal contract.
6. Freeze a separate M56 protocol before any B0–B5/Ours generation.

## Claim boundary

This is deterministic data-instrument and graphical-runtime evidence only. It is not a human label,
fresh model generation, real-person prediction, full-pipeline result, production authorization,
persona equivalence, human understanding, or a solved human-brain equation.
