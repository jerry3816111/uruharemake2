# M56.6 Single-writer Formal Generation Gate Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before any real M56 generation call
Single changed variable: prevention of concurrent local execution for the same formal-generation run id

## Problem

M56.5 makes one process resumable without retry, but it does not own the run exclusively. If two local processes
start the same authorized `run_id`, both can validate the same lease before either has advanced the state machine.
The exclusive intent write prevents two successful transports for one step, but the losing process can still record a
terminal failure while the first process is healthy. That can waste the single-use human authorization and invalidate
otherwise valid checkpoints.

M56.6 must establish one cooperative local writer before delegating to the unchanged M56.5 public execution path.
It must not change prompts, task order, data, model settings, retry policy, checkpoints, scoring, thresholds, human
evidence, or outcome isolation.

## Prospective state machine

1. Validate that `run_id` is one safe path component and resolve only its standard private formal-run directory.
2. Open one fixed, non-symlink, owner-only regular lock file in that run's telemetry compartment.
3. Acquire a non-blocking operating-system exclusive advisory lock.
4. Revalidate that the open descriptor and on-disk path are the same file.
5. Only the lock owner may call unchanged `execute_resumable_formal_generation(run_id)`.
6. A simultaneous contender fails before delegation, creates no M56.5 terminal failure, and performs no model call.
7. Normal return or Python exception releases the lock. Process death relies on the operating system closing the
   descriptor; the harmless lock-file inode may remain and be reused by a later process.

The lock is intentionally local and cooperative. It is not a distributed lease, a security boundary against an
administrator or same-host attacker, or evidence that the model experiment succeeded.

## Success conditions

- The only public execution parameter is `run_id`; no lock, provider, retry, prediction, outcome, or readiness
  override is accepted.
- The first holder delegates exactly once to the unchanged M56.5 entry point.
- A concurrent second holder is rejected before delegate entry, with zero additional transport and no terminal
  generation-failure artifact.
- An exception from M56.5 releases the operating-system lock without changing M56.5 failure semantics.
- Abrupt process exit releases ownership; a later process can acquire the existing lock file.
- Symlinks, non-regular files, wrong owner, multiple hard links, or group/world permission bits fail closed.
- Different run ids do not block one another.
- Current live state remains V7 0/18 and 0/18, V9 and real temporal rows 0/30, formal calls and outcome access 0,
  and formal commitment/release/result absent.
- A read-only graphical page explains the duplicate-start defect, one-writer gate, crash release, and scientific
  evidence boundary to a non-expert.

## Evidence boundary

Thread/process races and abrupt-exit fixtures may validate local mutual exclusion in temporary directories. They do
not constitute human labels, real temporal rows, fresh model generation, actual resource/performance evidence,
Equation V1 predictive validity, an M56 comparison, full-pipeline readiness, production readiness, or a solved
human-response equation. Two different humans completing frozen V7 remain the next non-substitutable scientific
dependency.
