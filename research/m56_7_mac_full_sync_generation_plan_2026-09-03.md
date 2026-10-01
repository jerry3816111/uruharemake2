# M56.7 Mac Full-Sync Generation Commit Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before any real M56 generation call
Single changed variable: stable-storage commit boundary for formal-generation artifacts on the bound Mac

## Problem

M56.5 calls `fsync` on each newly written JSON file, and M56.6 prevents a second local writer.  However, neither
version synchronizes the directory entry that names a new intent, checkpoint, submission, ledger, commitment or
release.  A normal process crash is covered, but after a kernel crash or sudden power loss the model transport may
have completed while the checkpoint directory entry is absent after restart.  The surviving intent would then make
the single-use formal run terminal even though a valid response had existed in memory.

M56.7 changes only the write-completion boundary.  A generation artifact is not considered committed until the
serialized file and the parent directory have each passed ordinary `fsync` and macOS `F_FULLFSYNC`.  Prompts,
schedule, data, model, generation options, token budgets, checkpoint contents, retry policy, scoring and human gates
remain unchanged.

## Prospective state machine

1. Revalidate the standard permitted `run_id` and acquire the unchanged M56.6 one-host single-writer lock.
2. Reject a run that already contains M56.5 generation-state artifacts but has no M56.7 mode commitment; prior
   writes cannot be retroactively claimed as full-synced.
3. Install a context-local writer dispatcher.  Calls outside the M56.7 execution context retain the frozen M56.3
   writer and do not gain M56.7 authority.
4. Commit an immutable M56.7 mode artifact with file `fsync` + `F_FULLFSYNC` and parent-directory `fsync` +
   `F_FULLFSYNC` before M56.5 mode, schedule, intent or transport.
5. Delegate to the unchanged M56.5 state machine.  Every JSON artifact it creates, including terminal failures,
   passes the same file-and-directory barrier before the write returns.
6. A model intent is therefore durably named before transport.  A completed checkpoint is durably named before
   M56.5 may remove the matching intent.  If the intent deletion itself is not persisted, restart sees both and
   safely reuses the checkpoint without another call.
7. After unchanged M56.5 final validation, commit an immutable M56.7 durable-generation release binding the mode,
   submission, prediction commitment and scoring release hashes.

Older M56.5/M56.6 entry points remain frozen engineering artifacts.  A run executed through them cannot be called
M56.7-durable merely because its files happen to exist later.

## Success conditions

- The only formal-generation execution input remains `run_id`; no writer, provider, prediction, outcome, retry,
  fallback, durability or readiness override is accepted.
- Unsupported platform/full-sync calls fail before M56.5 delegate entry and before a model transport.
- The M56.7 mode must be the first M56.5-generation state for the run and must be durably committed.
- Exclusive create writes serialize before transport, synchronize the file, request `F_FULLFSYNC`, synchronize the
  parent directory and request directory `F_FULLFSYNC` before returning.
- A completed checkpoint is durably committed before matching intent removal.  Checkpoint-plus-intent remains a
  valid completed state; intent-only remains terminal and is never recalled.
- The unchanged forged 30-row path still has exactly 180 mock model calls, 210 predictions, zero retry/fallback,
  zero generation outcome access, a valid M56.4 pre-score report and one M56.7 release.
- Existing M54–M56.6 frozen hashes remain unchanged.
- Current live state remains V7 0/18 and 0/18, V9/real rows 0/30, formal calls/outcome access 0, and formal
  commitment/scoring release/result absent.
- A read-only graphical page explains intent, transport, checkpoint, directory durability, restart states, overhead
  and the evidence boundary to a non-expert.

## Evidence boundary

Fault injection, syscall-order checks and a forged full-path fixture can prove that the application invokes the
bound macOS durability barriers in the required order.  They cannot reproduce every storage-controller behavior or
prove survival of an actual power cut.  `F_FULLFSYNC` is the strongest local API requested here, not a digital
signature, malicious-host boundary, distributed transaction or guarantee against defective hardware.  M56.7 adds
no human labels, real temporal rows, fresh formal model predictions, actual model performance, Equation V1
validity, full-pipeline result, production readiness or solved human-response equation.
