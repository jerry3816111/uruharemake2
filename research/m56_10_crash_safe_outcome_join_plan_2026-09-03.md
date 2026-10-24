# M56.10 Crash-Safe At-Most-Once Outcome Join Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before implementation and before any real M56 target-outcome access
Single changed variable: lifecycle of the one authorized private-outcome join across sequential restart

## Problem proved before the change

M56.9 prevents overlapping same-host scorers, but its lock is released when a process returns or dies. An isolated
forged 30-row run injected a failure after `load_outcome_inputs` and before the score report was written. The first
invocation opened the outcome once and left an access receipt but no report/result. A later M56.9 invocation opened
the same outcome again and completed: **one failed invocation + one restart -> two private outcome loads**. No real
M56 outcome was used. The immutable reproduction is
`analysis/m56_10_prechange_crash_window_reproduction_2026-09-03.json`.

## Why the guarantee is at-most-once, not unconditional exactly-once completion

Opening an existing private file and committing a new checkpoint are not one atomic filesystem transaction. If a
process dies after a durable intent but before a durable score checkpoint, a restart cannot prove whether the
outcome was never opened or was opened and the checkpoint was lost. Automatically opening it again would violate
at-most-once access; automatically claiming completion would invent a result.

M56.10 therefore freezes the strongest honest cooperative guarantee:

- an uninterrupted completed run performs exactly one private outcome load;
- a restart with a valid durable score checkpoint performs zero additional outcome loads and can finalize the same
  frozen M56.4 report/result;
- a restart with durable intent but no valid checkpoint is terminal and performs zero additional outcome loads;
- a completed sequential replay validates/reuses the checkpoint and performs zero additional outcome loads.

This sacrifices availability in the ambiguous crash window. It must not be described as unconditional exactly-once
completion, a distributed transaction or malicious-host protection.

## Single attributable change

Add one sanctioned entry point:

`valid M56.8 run -> M56.9 same-run OS lock -> M56.10 durable mode -> unchanged M56.8 gate -> unchanged M56.4 prescore/access receipt -> durable join intent -> one private outcome load -> unchanged M56.4 score construction -> durable private score checkpoint -> unchanged M56.4 report/result commitment`

The new mode, intent and checkpoint use the already frozen M56.7 macOS file and directory
`fsync + F_FULLFSYNC` writer. M56.4 scoring metrics, thresholds, B5-vs-Ours comparison, report fields and result
commitment content remain unchanged. M56.8 authorization and M56.9 lock checks remain unchanged.

## Required state machine

1. The only public parameter is `run_id`; no outcome, result, checkpoint, readiness, retry, wait or bypass injection.
2. The standard M56.8 run is validated before creating M56.10 state; the M56.9 lock is held throughout.
3. A new M56.10 mode may not be added retroactively to a run that already has an M56.8 gate, M56.4 outcome-access
   receipt, score report or result commitment.
4. Before the first outcome load, an immutable full-sync intent binds the exact M56.10 mode, M56.8 gate, M56.4
   access receipt, prediction release and expected outcome/split hashes.
5. After the one load, the unchanged M56.4 score report is full-sync committed inside the private scoring
   compartment as an immutable checkpoint before canonical report/result finalization.
6. A valid checkpoint is sufficient for restart; it must be fully revalidated against current frozen inputs and the
   immutable intent before use. Restart does not call `load_outcome_inputs`.
7. Intent without a valid checkpoint is an ambiguous terminal state. It records a durable terminal failure and may
   not retry, fall back, accept manual result injection or load the outcome again.
8. A canonical M56.4 score/report state without a matching M56.10 checkpoint is invalid and cannot be certified
   after the fact.
9. Historical M56.8/M56.9 APIs remain frozen and physically callable by same-host code; their direct use does not
   gain M56.10 authority.

## Frozen success conditions

- pre-change crash-window fixture remains two loads across two sequential invocations;
- uninterrupted M56.10 full path creates the unchanged seven-condition M56.4 report/result with exactly one load;
- a failure after durable checkpoint but before canonical result can restart to completion with total load count one;
- a failure after intent but before checkpoint causes all later sanctioned invocations to reject before outcome,
  leaving total load count no greater than one;
- two completed sequential invocations have total load count one and identical result hashes;
- a simultaneous contender is still rejected by the unchanged M56.9 lock before M56.8/outcome;
- missing, retroactive, mutated, malformed, symlink/hardlink/permissive-lock and mismatched checkpoint states fail
  closed without extra outcome access;
- old M54-M56.9 frozen hashes stay unchanged and selected compatibility tests pass;
- fixture cost and durable artifact counts are measured without calling a scorer model;
- live state remains V7 `0/18 + 0/18`, real temporal rows `0/30`, formal calls/outcome/result absent;
- a read-only graphical page explains completed, recoverable-checkpoint and ambiguous-terminal paths to a non-expert.

## Evidence boundary

M56.10 may support only a cooperative same-host sanctioned-path claim: completed runs load the private outcome once,
checkpointed restarts do not reload it, and ambiguous intent-only restarts fail closed. It cannot prove that the
outcome is physically unreadable through old APIs or direct filesystem access. It is not a distributed transaction,
malicious-host boundary, human label, real temporal row, formal performance result, Equation V1 validation, solved
human-response equation, full-pipeline evidence or production readiness.
