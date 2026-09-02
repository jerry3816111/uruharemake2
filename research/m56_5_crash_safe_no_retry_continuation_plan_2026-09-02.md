# M56.5 Crash-safe No-retry Formal Generation Continuation Plan

Date: 2026-09-02
Status: prospective engineering contract; frozen before any real M56 generation call
Single changed variable: recovery of already durably completed formal generation steps after a process interruption

## Problem

M56.3 correctly forbids retry and fallback, but it keeps all intermediate model results in process memory until the
entire 210-row prediction matrix is complete. A crash after many successful calls therefore invalidates the whole run
and wastes both compute and a human-authorized lease. That protects against hidden retry, but it is unnecessarily
fragile for a long local experiment.

M56.5 must distinguish two cases without reading outcomes:

1. a step has a complete, immutable, hash-bound checkpoint written after its one permitted transport call; it may be
   reused without calling the model again;
2. a step has an invocation-intent marker but no complete checkpoint; whether the model returned is ambiguous, so the
   run must fail terminally and may not call that step again.

This is crash recovery, not retry. It does not alter prompts, predictions, the M56.3 schedule, scoring, thresholds,
model settings, human data, or the private outcome compartment.

## Prospective state machine

1. Revalidate the consumed M56.2 receipt/lease and all M56.3 runner inputs.
2. Create or byte-validate the frozen M56.3 schedule.
3. Rematerialize the Equation bundle and commit one immutable CPU/audit checkpoint.
4. Walk summary and prediction steps in frozen schedule order.
5. For a deterministic step, commit its result directly with zero calls.
6. For a model step, atomically commit an invocation-intent marker before transport.
7. Perform exactly one transport attempt; retry and fallback remain zero.
8. Atomically commit one combined checkpoint containing the validated summary/prediction result and call telemetry,
   excluding raw response text and reasoning.
9. Remove only the matching intent marker. If both marker and valid checkpoint exist after a crash, accept the
   checkpoint and remove the redundant marker without another call. Marker without checkpoint is terminal.
10. When every scheduled step is present and valid, construct the unchanged M56.3 submission, call ledger,
    prediction commitment, and scoring release.

## Success conditions

- Public execution API accepts only `run_id`.
- Current live state remains denied with zero formal calls, outcome access, commitment, release, or result.
- An interrupted test-only run resumes from valid completed checkpoints and does not call completed task IDs again.
- Resumed and uninterrupted test-only runs produce identical prediction/summary content and both validate through
  the frozen M56.3 and M56.4 contracts.
- A lone intent marker, terminal failure, mutated checkpoint, wrong order, source drift, resource error, or output
  error fails closed without another call.
- Final call count equals the M56.3 schedule, with zero retry/fallback and zero generation outcome access.
- Checkpoints add no raw prompt/source copy beyond the unchanged M56.3 summary/prediction artifacts, and contain no
  raw model response, reasoning trace, private outcome, or private mental-state assertion.
- A read-only graphical page explains completed, resumable, ambiguous, terminal, and final states to a non-expert.

The SHA chain is an application-level accidental-drift control. As in M56.2–M56.4, it is not a digital signature
against an attacker who can rewrite both the checkpoint and every bound hash. The mutation gate refers to changed
content that no longer matches its committed hash or reconstruction contract; it does not claim hostile-host security.

## Evidence boundary

Synthetic and forged real-shaped fixtures may test interruption mechanics in temporary directories. They are not
human evidence, actual local-model resource evidence, fresh behavior prediction, Equation V1 validity, or a formal
M56 result. M56.5 does not weaken the two-human V7 gate and cannot authorize scoring, production memory writes,
deployment, or a broad human-equation claim.
