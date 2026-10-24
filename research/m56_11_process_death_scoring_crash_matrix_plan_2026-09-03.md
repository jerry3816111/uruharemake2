# M56.11 Process-Death Scoring Crash Matrix Plan

Date: 2026-09-03
Status: prospective engineering-validation contract; frozen before implementation and before any real M56 target-outcome access
Single changed variable: failure-injection realism, from same-process exceptions to abrupt subprocess death

## Evidence gap proved before the change

M56.10 freezes a correct-looking intent/checkpoint state machine, but its focused tests inject ordinary Python
exceptions. Those exceptions can execute cleanup code; abrupt process death cannot. M56.9 separately proves that an
OS lock is released by process death, but the complete M56.10 state transitions had not been exercised across a new
process boundary.

A one-off temporary probe used `os._exit(71)` after the real fixture outcome loader and `os._exit(72)` after the
durable score checkpoint. The first restart rejected with zero reloads and committed a terminal failure; the second
completed from checkpoint with zero reloads. The positive probe is retained in
`analysis/m56_11_preimplementation_process_death_probe_2026-09-03.json`, but one ad-hoc probe is not a reproducible
acceptance harness.

## Single attributable change

Add a no-argument, test-only process-death crash matrix around the unchanged frozen M56.10 entry. Each case creates a
fresh temporary forged 30-row run, starts a separate Python process, uses a phase-specific monkeypatch to call
`os._exit`, then starts a clean parent-side M56.10 invocation. No fault hook is added to the formal runtime path.

The four frozen crash locations are:

1. after the M56.9 lock is acquired but before M56.10 state exists;
2. after the private outcome loader returns but before the score checkpoint exists;
3. after the full-sync checkpoint exists but before the canonical score report;
4. after the canonical score report exists but before the result commitment.

A full-sync test-only marker records that the child passed the actual outcome loader/checkpoint phase. It lives only
inside the temporary fixture and is deleted with it. The matrix output contains state booleans, exit codes, counts
and hashes—never outcome labels, source text or raw model output.

## Frozen success conditions

- each child exits with its preregistered distinct code and no Python cleanup path is relied upon;
- the same-run M56.9 lock can be reacquired after every child death;
- death before M56.10 state permits one later outcome load and completes with exactly one total load;
- death after the outcome load but before checkpoint leaves intent/no checkpoint; restart performs zero loads,
  commits terminal failure and does not create a result;
- death after checkpoint but before canonical report performs zero restart loads and completes the unchanged M56.4
  result from the checkpoint;
- death after canonical report but before result commitment performs zero restart loads and completes the same
  result without mutating the report;
- no case retries, falls back, calls a scorer model, touches the configured real private root or leaves a child alive;
- the harness validates its own immutable matrix schema/hash and rejects altered evidence;
- all M54-M56.10 frozen hashes remain unchanged and selected compatibility tests pass;
- matrix wall time/process-launch count are reported as fixture overhead, not production cost;
- a read-only graphical page explains all four crash points, restart behavior and the remaining power-loss boundary.

## Evidence boundary

M56.11 can show that the frozen M56.10 cooperative state machine behaves as specified after abrupt local child-process
death. It does not simulate sudden power loss, kernel/filesystem corruption, distributed execution or malicious host
modification. It adds no human label, real temporal row, formal prediction/outcome access, model-performance result,
Equation V1 validation, solved human-response equation, full-pipeline evidence or production authorization.
