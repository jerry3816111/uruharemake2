# M56.10 Crash-Safe At-Most-Once Outcome Join Acceptance

Date: 2026-09-03
Decision: **PASS for cooperative same-host at-most-once outcome loading through the sanctioned M56.10 path; live formal scoring remains DENIED**

## Problem proved before the change

The frozen M56.9 lock closes only overlapping execution. An isolated forged 30-row run injected a failure after the
private outcome loader returned but before the M56.4 score report existed. The first invocation had one outcome load,
an access receipt and no report/result. A later sequential M56.9 invocation loaded the same outcome again and then
completed: **two invocations -> two outcome loads**.

This is retained in
`analysis/m56_10_prechange_crash_window_reproduction_2026-09-03.json`. It contains no real M56 target data.

## What changed

M56.10 adds one sanctioned public entry:

`execute_crash_safe_outcome_join_formal_scoring(run_id)`

It preserves the exact M56.8 authorization and M56.9 nonblocking same-run lock. Under that lock it commits:

1. an M56.10 full-sync mode before any M56.8/M56.4 outcome state;
2. the unchanged M56.8 durable scoring gate;
3. unchanged M56.4 prescore audit and access receipt;
4. a full-sync immutable join intent before the one permitted private outcome load;
5. the unchanged M56.4 score report inside a full-sync private checkpoint;
6. the unchanged canonical M56.4 score report and result commitment.

The new artifacts reuse the frozen M56.7 macOS file and directory `fsync + F_FULLFSYNC` writer. M56.4 metrics,
thresholds, B5-vs-Ours primary contrast, report content and result commitment content did not change.

## The honest guarantee

Opening an existing private answer and writing a new checkpoint cannot be one atomic filesystem transaction. M56.10
therefore does not claim unconditional exactly-once completion:

| Restart state | Additional outcome load | Result behavior |
|---|---:|---|
| no intent, no checkpoint | one authorized load | calculate and checkpoint |
| valid intent + valid checkpoint | **0** | validate and finalize the same report |
| intent without checkpoint | **0** | terminal fail; no retry or invented result |
| completed sequential replay | **0** | validate the existing checkpoint/result |

The intent-only state is deliberately unavailable because the process cannot know whether it stopped immediately
before or after opening the answer. Reading again could be a duplicate; claiming completion would invent evidence.

## Attributable result

| Isolated forged path | M56.9 before | M56.10 after |
|---|---:|---:|
| failure after outcome load, then restart | 2 total loads | **1 total load; terminal if no checkpoint** |
| completed run, then sequential replay | 2 total loads | **1 total load** |
| checkpoint exists, canonical result absent | M56.9 has no checkpoint | **restart completes with 0 additional loads** |
| overlapping contender | 1 owner load after M56.9 | **same 1 owner load; contender remains pre-outcome** |
| scorer model calls | 0 | 0 |

The uninterrupted M56.10 path still produced a valid seven-condition M56.4 report and valid unchanged result
commitment. Mutated checkpoints, checkpoint-without-intent, canonical-result-without-checkpoint and preexisting
M56.9 results were all rejected before any additional outcome load. Full evidence is in
`analysis/m56_10_crash_safe_outcome_join_state_evidence_2026-09-03.json`.

## Cost

Seven alternating paired 30-row deterministic fixture runs measured setup-free wall time:

| Condition | Median wall time | Durable JSON commits | Outcome loads | Scorer model calls |
|---|---:|---:|---:|---:|
| frozen M56.9 | 0.855593 s | 1 | 1 | 0 |
| M56.10 | 0.770818 s | 8 | 1 | 0 |
| observed paired difference | -0.080518 s | **+7** | 0 | 0 |

The negative local time difference was also present in an initial three-run observation. It is reported, not
interpreted as a speed improvement: the paths use different JSON writers and this short deterministic scoring
fixture is noisy. The attributable storage cost is seven additional full-sync JSON commits. Five completed
checkpoint replays had a median 0.278417 s, zero additional outcome loads and zero model calls.

Raw measurements are in
`analysis/m56_10_crash_safe_outcome_join_fixture_cost_2026-09-03.json`. They are not formal model latency or
production throughput.

## Tests

- focused M56.10 suite after freeze: **16/16 passed** in 12.07 seconds;
- direct M54-M56.10 compatibility: **240/240 passed** in 61.28 seconds;
- selected M1/M2/M6/V7/V9/M54-M56.10 compatibility: **305/305 passed** in 63.07 seconds;
- Python compilation, JSON parsing, contract/dependency hashes and implementation-freeze hashes: PASS;
- current formal model calls: **0**;
- current real target-outcome access: **0**;
- current formal score/result: **absent**.

Contract hash: `c2da60a56b7c8c1a86ab7d69938f96c308c4e144916fe1f7277d0b66cb747a04`

Live audit hash: `c60ebdd4ba0f830d90e27c08633768490d62af20d91bf111a2c4dbffd838d6aa`

Rehearsal hash: `582cce8480b636c4c5ea2161e14396f80b38ad194aedbd58adb1dbccaa3d32b1`

## Safari graphical acceptance

Safari reused the existing M56.9 local tab and navigated it to `http://127.0.0.1:7918/dashboard`. The tab count was
33 before and after; no user tab was opened or closed. The read-only page visibly showed:

- the reproduced change from two loads to one;
- the three states: not started, durable checkpoint and ambiguous intent-only;
- zero additional loads for checkpoint restart and terminal failure for ambiguous restart;
- V7 `0/18 + 0/18`, real rows `0/30`, and zero real outcome/result;
- the availability tradeoff and scientific evidence boundary.

The top and bottom were readable with no form or visible horizontal overflow:

- `analysis/m56_10_safari_state_machine_top_2026-09-03.png`
- `analysis/m56_10_safari_ambiguous_boundary_2026-09-03.png`

The 7918 local server was stopped. The remaining read-only tab is safe to close and holds no lock or private state.

## Honest boundary and long-term contribution

M56.10 prevents an eventual formal B5-vs-Ours experiment from silently reopening withheld answers after a completed
score or after an ambiguous crash on the new sanctioned path. It also makes the unavoidable recovery tradeoff
auditable instead of hiding it behind a second answer read. This improves the integrity of the future candidate
human-response-equation experiment; it does not improve the equation's predictive ability.

Historical M56.8/M56.9 APIs and direct filesystem access remain physically possible for same-host code, so this is
cooperative research authority, not an OS sandbox or malicious-host security boundary. There was no power-cut test;
hardware/filesystem failure outside the frozen macOS barrier remains possible. Intent-only failure is permanently
unavailable and cannot auto-complete.

The authoritative live state remains V7 `0/18 + 0/18`, V9 and real temporal rows `0/30`, with no formal model call,
real outcome access, prediction/result or human evidence. M56.10 does not prove model performance, Equation V1,
Uruha prediction advantage, a solved human-response equation, full-pipeline value or production readiness.

The next safe engineering milestone is M56.11 private scoring artifact confidentiality/integrity containment: prove
that the new outcome-derived checkpoint and canonical report remain confined to the private scoring compartment and
that the live/public observatory exposes only bounded aggregate state. The next non-substitutable scientific
dependency remains two different humans completing the frozen V7 pilot.
