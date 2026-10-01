# M56.11 Process-Death Scoring Crash Matrix Acceptance

Date: 2026-09-03
Decision: **PASS for the four preregistered abrupt local child-process death states; live formal scoring remains DENIED**

## Problem proved before the change

M56.10's focused failure tests raised regular Python exceptions. Those tests establish its state-machine contract, but
an exception can run cleanup code while an abruptly terminated process cannot. A temporary forged 30-row probe then
used `os._exit(71)` after the real fixture outcome loader and `os._exit(72)` after the durable score checkpoint. A
fresh parent process respectively observed an intent-only terminal state with zero reloads and a checkpoint recovery
with zero reloads. The probe is retained in
`analysis/m56_11_preimplementation_process_death_probe_2026-09-03.json`; it contains no real M56 target data.

## Single changed variable

M56.11 changes only **failure-injection realism: same-process exceptions -> abrupt subprocess death**. It adds a
no-argument engineering harness, `run_process_death_crash_matrix()`, around the unchanged frozen M56.10 runtime. Each
scenario creates a separate temporary forged run, launches a distinct child process, terminates that child with a
phase-specific `os._exit`, reaps it, and invokes M56.10 from a clean parent process.

The child-only monkeypatch does not install a fault hook in the formal runtime. A full-sync marker inside the
temporary fixture proves that the child passed the intended phase. The exported matrix contains only state booleans,
counts and hashes, never outcome labels, source text or raw model output.

## Attributable result

| Abrupt death phase | Exit | Child loads | Restart loads | Total loads | Restart result |
|---|---:|---:|---:|---:|---|
| lock acquired, before M56.10 state | 70 | 0 | 1 | **1** | completes normally |
| outcome returned, before checkpoint | 71 | 1 | **0** | **1** | terminal fail; no result |
| checkpoint committed, before report | 72 | 1 | **0** | **1** | completes from checkpoint |
| report committed, before result | 73 | 1 | **0** | **1** | completes; report hash unchanged |

All four observed exit codes matched the preregistration, all four children were reaped, the same-run OS lock was
reacquired, and no scenario retried, fell back or called a scorer model. The configured real private root and real
target outcomes were never accessed. The complete immutable evidence is in
`analysis/m56_11_process_death_scoring_crash_matrix_result_2026-09-03.json` with matrix hash
`d7346f14b492144746f5db75f929a488fb2634aeda46285f4c7db95234f51c33`.

The exit-71 behavior is deliberately unavailable, not an implementation failure. After an answer has been opened
but before a checkpoint exists, a new process cannot prove whether the old process finished the read. M56.10
therefore preserves at-most-once access by refusing to reopen the answer or invent a result.

## Cost

Three complete temporary matrices measured:

| Run | Matrix wall time | Child launches | Forged outcome loads | Scorer model calls |
|---|---:|---:|---:|---:|
| 1 | 5.115022 s | 4 | 4 | 0 |
| 2 | 5.129000 s | 4 | 4 | 0 |
| 3 | 5.164917 s | 4 | 4 | 0 |
| median | **5.129000 s** | 4 | 4 | 0 |

This is validation-harness cost: it includes four Python interpreter launches, four temporary forged-run
materializations and four restart validations. It is not added production-scoring latency or a throughput result.
Raw measurements are in
`analysis/m56_11_process_death_scoring_crash_matrix_fixture_cost_2026-09-03.json`.

## Tests

- focused M56.11 suite after freeze: **9/9 passed** in 5.18 seconds;
- direct M54-M56.11 compatibility: **249/249 passed** in 67.08 seconds;
- selected M1/M2/M6/V7/V9/M54-M56.11 compatibility: **314/314 passed** in 72.55 seconds;
- Python compilation, JSON parsing, contract/schema validation, dependency hashes and implementation-freeze hashes:
  PASS;
- current formal model calls: **0**;
- current real target-outcome access: **0**;
- current formal score/result: **absent**.

Contract hash: `83c3006cebfe2cf888b6afb7f5671432b9566e10a7b4485955cbee525d49927e`

Live audit hash: `64c0c2dceae44bc49a59b5fed720e7acc71e66d04fb929f0f3c23f54387b7b64`

## Safari graphical acceptance

Safari reused the existing M56.10 local tab and navigated it to `http://127.0.0.1:7919/dashboard`. The tab count was
33 before and after; no user tab was opened or closed. The read-only page visibly showed:

- all four `os._exit` phases and their distinct exit codes 70-73;
- exactly one total forged outcome read on every path;
- the intent-only path's terminal unavailability and the two checkpoint-based zero-reload recoveries;
- four reaped child processes, four matching exit codes, zero retry and zero scorer-model calls;
- a visible statement that the numbers come from the validated saved matrix rather than a handwritten result;
- V7 `0/18 + 0/18`, real rows `0/30`, zero real outcome/result and the scientific claim boundary.

The top and bottom were readable with no form or visible horizontal overflow:

- `analysis/m56_11_safari_process_death_matrix_top_2026-09-03.png`
- `analysis/m56_11_safari_process_death_boundary_2026-09-03.png`

The 7919 local server was stopped. The remaining read-only tab is safe to close and holds no lock or private state.

## Failure analysis and evidence boundary

This matrix validates real local process disappearance and OS-lock release. It does **not** simulate a sudden power
cut, kernel crash, filesystem corruption, incomplete hardware flush, distributed execution or a malicious same-host
program. The exit-71 path continues to sacrifice availability; M56.11 proves that this boundary is honored rather
than making every interruption recoverable.

The authoritative scientific state remains V7 `0/18 + 0/18`, V9 and real temporal rows `0/30`, with no formal model
call, real outcome access, prediction/result or human evidence. M56.11 therefore does not prove model performance,
Equation V1, Uruha prediction advantage, a solved human-response equation, full-pipeline value or production
readiness.

## Long-term contribution and next milestone

M56.11 strengthens the future human-response-equation experiment's evidence integrity: the scoring boundary is now
tested across actual process death rather than only recoverable exceptions. It changes no prediction, memory,
persona, Japanese surface or scientific score and must not be counted as evidence that the equation works.

The next safe single-variable engineering milestone is **M56.12 Outcome-Derived Artifact Containment and Public
Projection Audit**. Its pass condition is that private checkpoint/report/outcome-derived material is inaccessible to
public live renderers, logs and telemetry while a bounded aggregate status remains graphically observable, with no
per-sample label, raw source or hidden outcome leakage. The next non-substitutable scientific dependency remains two
different humans completing the frozen V7 pilot.
