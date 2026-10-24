# M56.3 Lease-Gated Formal Generation Runner · 2026-09-02

## Problem

M56.2 can prepare a private real-data run and issue a short-lived, single-use generation lease after the
live V7→V9→M55 evidence chain passes.  No frozen component yet consumes that lease to execute the B0–B5/Ours
matrix, measure the real resources, create a complete prediction commitment, and expose a scorer capability
only after every prediction is committed.  Calling Ollama from an ad-hoc loop would lose the frozen task order,
retry boundary, model binding, target isolation, and cost evidence needed for a formal comparison.

## Single attributable change

Add one formal generation state machine after the M56.2 lease:

`validated lease → frozen schedule → B4 summaries → 210 predictions → complete submission → SHA commitment → scoring release`

This milestone does not change the Equation, the seven conditions, prompts after seeing outcomes, scoring,
success thresholds, human labels, or frozen M54–M56.2 evidence.  It does not run while the live human gate is
closed and it does not read the outcome key.

## Required state machine

1. The separate M56.2 activation controller revalidates the standard prepared artifacts and live human gate
   immediately before consuming the receipt.  The generation runner receives only the resulting lease plus
   files from the permitted compartments; it never imports the private compilation or opens `scoring/`.
   Its public formal entry point has no injected provider, readiness, outcome, or retry parameter.
2. Revalidate the consumed receipt/lease pair and bind the lease hash to a content-addressed schedule.  The schedule contains
   every distinct non-empty B4 summary first and then all 30×7 prediction tasks in the already frozen order.
3. B0 is deterministic and performs zero model calls.  Every other prediction task performs exactly one local
   `qwen3.5:9b` call.  Every distinct non-empty B4 history summary performs exactly one additional call.  Ours
   receives the exact bound fit/state/transition artifacts; B5 never receives them.
4. Each call has one transport attempt, zero retry, zero fallback, fixed endpoint/model/options, deterministic
   prompt hash, strict JSON schema, and frozen input/output token budgets.  A transport, parse, schema, budget,
   artifact, model, or hardware error terminally fails that run and cannot create a commitment.
5. Measure actual prompt/completion tokens, latency, CPU time, process/Ollama memory observations, model digest,
   hardware fingerprint, provider durations, and upstream Equation artifact rematerialization CPU.  Do not infer
   missing resource fields or replace failed measurements with estimates.
6. Only a complete, valid submission may be written.  Create its SHA-256 commitment atomically before a
   separate scoring-release capability.  The release authorizes only the separate scorer to begin; it does not
   authorize a pass, result claim, production-memory write, deployment, retry, or outcome access by generation.
7. Generation code may open only the `generation`, `commitments`, and `telemetry` compartments.  It must not
   open, enumerate, hash, or accept content from `scoring/`.

## Acceptance while human data is unavailable

- current live execution remains denied before any schedule file, lease, model call, commitment, or scoring
  release is created;
- the public execution signature exposes no provider/readiness/outcome/retry injection;
- a 30-row real-shaped in-memory packet can build and validate the exact 210-task schedule and complete mock
  mechanics, but remains explicitly unleased and non-formal;
- missing/expired/consumed/mutated lease, schedule reorder/omission, outcome-key injection, model or hardware
  drift, wrong Equation artifact, malformed probability output, token overflow, retry/fallback, incomplete
  submission, post-commit mutation, and scoring-before-commit all fail closed;
- a distinct no-call synthetic rehearsal verifies state-machine wiring without creating human evidence,
  formal authority, private run files, or a model result;
- focused and compatibility tests pass and a read-only graphic explains where generation ends and scoring
  authority begins.

## Claim boundary

Passing M56.3 proves only that one future formally authorized generation run has a frozen, resource-audited,
no-retry execution and commitment path.  With the human gate still incomplete, the only valid current result is
denial and zero formal model calls.  This is not an M56 score, Equation V1 validity, real-person predictive
validity, Ours superiority, private mental truth, a solved human-brain equation, full-pipeline readiness, or
production readiness.
