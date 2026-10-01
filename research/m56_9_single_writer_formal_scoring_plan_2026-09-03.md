# M56.9 Single-Writer Formal Scoring Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before any real M56 target-outcome access
Single changed variable: same-host, same-run concurrent ownership of the M56.8 scoring delegate

## Problem proved before the change

M56.8 durably binds the M56.7 release before private outcome access, but it does not own an execution lock across
the unchanged M56.4 scorer.  An isolated 30-row forged fixture pre-created the valid M56.8 gate and M56.4 access
receipt, then started two M56.8 calls together.  Both calls reached `load_outcome_inputs`: private outcome loader
count was **2**, one caller completed, and the other failed on a concurrent immutable-result create.

This does not expose real data—the reproduction used only temporary forged inputs—but it disproves the operational
meaning of M56.4's `single_logical_private_outcome_join_authorized` receipt under concurrent launch.  The losing
caller is rejected too late, after it has already opened the withheld answer.

## Single attributable change

Add one new sanctioned scoring entry:

`valid M56.8 run -> per-run nonblocking OS lock -> unchanged M56.8 gate + M56.4 scorer -> release lock`

The lock is held across the complete M56.8 delegate.  A simultaneous contender for the same run must fail before
entering M56.8 and therefore before private outcome access or score/result writes.  Different run ids remain
independent.  This milestone does not change M56.8 release authorization, M56.4 metrics, result semantics, data,
model calls, prompts, thresholds, outcome key, human gates or scientific claims.

## Required boundary

1. The only new public entry is
   `execute_single_writer_durable_release_gated_formal_scoring(run_id)`; no caller may inject lock, outcome,
   scoring rule, result, readiness, retry, wait or bypass state.
2. Invalid or missing runs fail before a lock file or run directory is created.
3. A valid run uses a fixed lock file in its private telemetry compartment.  It must be a regular file owned by the
   current user, have exactly one hard link, deny group/world permissions, and retain descriptor/path identity.
4. Lock acquisition is nonblocking.  A simultaneous same-run contender may not wait, enter M56.8, open the outcome,
   write score/result artifacts, retry or fall back.
5. The owner holds the lock for the complete unchanged M56.8 call.  Normal return, exception and process death
   release OS ownership.  A stale lock filename or text is not authority and may be reused safely.
6. The historical M56.8 entry remains frozen.  Direct use does not gain M56.9 single-writer authority.
7. This lock closes only **overlapping** execution.  After the first owner releases the lock, a later sequential
   invocation can still enter frozen M56.8 and reopen the outcome.  Exactly-once access across process lifetimes
   requires a separate prospective milestone; M56.9 must not claim it.

## Frozen success conditions

- the pre-change two-caller fixture records two private outcome loads;
- after M56.9, two truly overlapping same-run callers produce exactly one delegate entry, one private outcome load,
  one success and one pre-delegate rejection;
- the rejected contender creates or mutates no M56.4/M56.8 score, result or failure artifact;
- missing run, symlink, hardlink, wrong owner and permissive lock-file cases fail closed;
- delegate exception and abrupt subprocess death release ownership without rewriting upstream semantics;
- different run ids do not block each other and stale lock content is not treated as active ownership;
- one full forged 30-row M56.8 score still produces the unchanged seven-condition report/result with zero scorer
  model calls;
- old M54-M56.8 frozen hashes remain unchanged and selected compatibility tests pass;
- live state remains V7 `0/18 + 0/18`, real temporal rows `0/30`, formal calls/outcome/result absent;
- a read-only graphical page shows the observed `2 outcome reads -> 1 outcome read` concurrency change and the
  sequential-replay limitation to a non-expert.

## Evidence boundary

M56.9 can support only a cooperative single-host concurrency claim: one same-run scorer owns the authorized M56.8
path at a time.  It is not a distributed lock, an OS sandbox, malicious-host protection, or an exactly-once outcome
access protocol across sequential restarts.  Forged fixtures are not human labels, real temporal rows, actual formal
performance, Equation V1 validity, a solved human-response equation, full-pipeline evidence or production readiness.
