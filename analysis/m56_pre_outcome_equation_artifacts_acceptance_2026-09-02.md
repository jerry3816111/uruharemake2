# M56.1 Pre-Outcome Equation Artifacts Acceptance · 2026-09-02

## Decision

**Outcome-blind artifact engineering gate: PASS. Formal M56 execution: BLOCKED. Formal result: ABSENT.**

Before this unit, the frozen M56 submission accepted any three 64-character strings for the Ours fit,
state, and transition provenance.  That was sufficient to test submission shape but not sufficient to
show that Equation V1 had actually formed a mechanism state before the target behavior was revealed.

The new overlay materializes the three artifacts from the exact source-information object shared by B5
and Ours, validates their content, injects them only into the Ours request, binds their hashes into the
submission and wrapper receipt, and revalidates the full bundle before the separate scorer may join an
answer key.  The frozen M54, M55, and M56 files were not modified.

## What is now real rather than a placeholder

### Pre-outcome fit

For every cutoff, the fit artifact records:

- all and only history IDs whose `available_at` is no later than the cutoff;
- exact behavior-label counts under the frozen observable taxonomy;
- a deterministic Laplace-smoothed behavior prior;
- sparse observable behavior-to-behavior transition counts;
- the public/development person-parameter boundary and effective sample count;
- zero current-target-behavior access, zero private-state targets, zero raw-text persistence, and zero
  model calls.

This is an observable small-data fit.  It is not a learned biological or private psychological model.

### Nine-variable state snapshot

The state snapshot uses the exact M54 variable order.  It stores typed values or digests for current
observable input, observable history, structured behavior memory, observable context, the declared
person parameter, and operational uncertainty.  The current M56 source object contains no defensible
transient-state, relationship-state, or goal/need evidence, so `S`, `R`, and `N` remain
`unavailable_not_inferred` with null values and no evidence references.

### Observable transition trace

Consecutive same-target snapshots now expose newly available history IDs, behavior-count deltas,
effective-fit-size changes, and per-variable status/value-digest changes.  Same-target history is required
to be monotonic.  No trace claims an unobserved psychological transition, performs behavior prediction,
or generates language.

## Binding and anti-cheating evidence

- B5 and Ours keep the frozen byte-identical source object and source hash.
- Only Ours can materialize an Equation-bound request; attempting to attach the payload to B5 is rejected.
- The Ours row must cite the exact fit/state/transition content hashes and the canonical request hash.
- Any Equation artifact hash on B0–B5 is rejected.
- The wrapper receipt binds both the frozen M56 submission receipt and the entire artifact-bundle hash.
- The wrapper scorer revalidates the bundle and receipt before delegating to the frozen separate scorer.
- Changed values with recomputed outer bundle hash, placeholder `aaaa...` hashes, forbidden outcome keys,
  late history, non-monotonic history, stale content hashes, or submission/bundle mismatch all fail closed.

## Deterministic evidence and resources

- contract validation: PASS;
- focused suite including implementation freeze: **14/14 passed**;
- direct M54–M56 compatibility suite: **110/110 passed**;
- selected M1/M2/M54/V7/V9/M55/M56 compatibility suite: **170/170 passed**;
- Python compilation: PASS;
- `git diff --check`: PASS before final handoff documentation;
- contract hash: `32eac97730eddabc8eb11fea23223de37a0db28b739d6d3d6999e9f420c8495f`;
- deterministic two-cutoff artifact bundle hash:
  `1bd2353b2ef77ec8c4908ca6d8dae857dac36618474e8d113126d4c36406bf7d`;
- materialized artifacts: 2 fit + 2 state + 2 transition = **6**;
- artifact model calls: **0**;
- artifact target-outcome access: **0**;
- production-memory writes: **0**;
- private-state fabrication count: **0**.

The selected suites are scoped compatibility evidence, not every historical test in the repository.

## Two-cutoff observable example

| Cutoff | Available completed history | Fit n | Newly available history | S / R / N |
|---|---:|---:|---:|---|
| `artifact-demo-01` | 0 | 0 | 0 | unknown / unknown / unknown |
| `artifact-demo-02` | 1 | 1 | 1 | unknown / unknown / unknown |

The second cutoff can use one earlier completed observable behavior.  It cannot use its own later target
behavior.  Rebuilding the same packet produces byte-identical artifacts and the same bundle hash.

## Safari graphical acceptance

Safari reused the existing local M56 tab and navigated it to `127.0.0.1:7909/dashboard`.  The browser
remained at **28 tabs**; no tab was created or closed and no form was submitted.

The rendered page visibly showed:

1. `B5/Ours same source -> Fit -> State -> Transition -> one Ours call -> SHA commitment`;
2. the first cutoff with zero history and the second cutoff with one newly available history item;
3. `transient_state`, `relationship_state`, and `goal_need_state` retained as unknown;
4. five fail-closed attack paths;
5. current V7 `0/18 + 0/18`, real rows `0/30`, formal model calls `0`, and no formal result.

The desktop-width flow rendered without horizontal overflow.  Evidence:

- `analysis/m56_1_safari_pre_outcome_equation_artifact_flow_2026-09-02.jpeg`
- `analysis/m56_1_safari_pre_outcome_equation_artifact_boundary_2026-09-02.jpeg`

## Exact remaining boundary

This unit removes the arbitrary-placeholder provenance gap.  It does not remove the human-data gate:

- V7 independent ledgers: **0/18 and 0/18**;
- V9 independently reviewed Uruha events: **0/30**;
- real M55 temporal rows: **0/30**;
- formal M56 model calls: **0**;
- target outcome access during formal generation: **0**;
- formal M56 result: **not created**.

The current overlay intentionally permits only synthetic engineering packets.  After two distinct humans
pass V7 and the V9→boundary→adjudication→M55 chain creates 30 real rows, a separately frozen real-data
execution authorization must reuse these artifact semantics, revalidate every dependency hash, count the
actual deterministic CPU overhead and Ours prompt tokens, and preserve the existing token-sensitivity
rule.  Until then, this work does not support claims of real-person predictive validity, private mental
truth, Uruha fidelity, Ours superiority, a human-brain equation, full-pipeline readiness, or production
readiness.
