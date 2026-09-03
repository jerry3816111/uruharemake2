# M56.9 Single-Writer Formal Scoring Acceptance

Date: 2026-09-03
Decision: **PASS for overlapping same-host scoring ownership; live formal scoring remains DENIED**

## Problem proved before the change

The frozen M56.8 path durably validates the M56.7 release but owns no execution lock around the unchanged M56.4
scorer.  A temporary forged 30-row run with a valid M56.8 gate and access receipt was called by two threads at the
same time.  Both reached the private outcome loader: **2 callers -> 2 outcome loads**.  One completed and the other
failed only later with `FileExistsError` while creating `formal_score_commitment.json`.

The failure was therefore detected after the losing caller had opened the withheld answer.  This contradicted the
operational meaning of M56.4's single-logical-join receipt.  No real M56 data was used.

## What changed

M56.9 adds one new sanctioned entry point:

`execute_single_writer_durable_release_gated_formal_scoring(run_id)`

It accepts only `run_id`.  It first validates that the standard M56.8 inputs are genuine and unchanged, then obtains
a fixed per-run, nonblocking OS advisory lock in private telemetry.  The owner holds the lock across the complete,
unchanged M56.8 delegate.  A simultaneous same-run contender is rejected before entering M56.8, before private
outcome access and before score/result writes.

The lock rejects symlinks, non-regular files, wrong ownership, multiple hard links, permissive group/world modes and
descriptor/path identity drift.  Normal return, exception and process death release OS ownership; stale file text
is not authority.  Different run ids remain independent.

M56.8 authorization, M56.4 outcome/metric/result semantics, prediction contents, data, model, prompts, resources,
thresholds and human gates were not changed.

## Attributable concurrency result

| Same forged 30-row run | M56.8 before | M56.9 after |
|---|---:|---:|
| overlapping callers | 2 | 2 |
| entries into M56.8 scoring delegate | 2 | **1** |
| private outcome-loader calls | **2** | **1** |
| successful owner | 1 | 1 |
| loser rejected before M56.8/outcome | 0 | **1** |
| contender score/result writes | late collision | **0** |

The post-change owner still produced the unchanged seven-condition M56.4 report and result with zero scorer model
calls.  Evidence is retained in
`analysis/m56_9_single_writer_formal_scoring_concurrency_evidence_2026-09-03.json` and the full-path test.

## Deliberately retained failure boundary

M56.9 is not an exactly-once protocol across process lifetimes.  The test intentionally runs two calls one after the
other, after the first lock has been released.  Frozen M56.8 reopens the private outcome on the second invocation, so
the measured loader count remains **2**.  This failure is preserved in the contract, test, dashboard and evidence
JSON.  A future milestone must add crash-safe scoring completion/outcome-access continuation without changing this
frozen result.

## Fixture cost

The same deterministic 30-row scoring fixture was run three times per condition.  Setup was outside the measured
interval.

| Condition | Median wall time | Scorer model calls |
|---|---:|---:|
| frozen M56.8 | 0.724372 s | 0 |
| M56.9 lock + unchanged M56.8 | 0.855941 s | 0 |
| added by M56.9 | **0.131569 s** | **0** |

Raw values are in `analysis/m56_9_single_writer_formal_scoring_fixture_cost_2026-09-03.json`.  This is local
deterministic fixture cost, not formal model latency or production throughput.

## Tests

- focused M56.9 suite after freeze: **15/15 passed** in 4.62 seconds;
- direct M54-M56.9 compatibility after freeze: **224/224 passed** in 51.24 seconds;
- selected M1/M2/V7/V9/M54-M56.9 compatibility: **289/289 passed** in 51.81 seconds;
- Python compilation, JSON parsing, frozen dependency hashes, implementation-freeze hashes and diff check: PASS;
- current formal model calls: **0**;
- current real target-outcome access: **0**;
- current formal score/result: **absent**.

Contract hash: `2cd38c9af5a1588984cdd7e5ed4b929e99f0a9a7cfb7b65e9825958d9b81b46a`

Live audit hash: `9bcf7051bd6672800638c849c100512ece08735839e4db160061d21772c648a2`

Concurrency rehearsal hash: `528a810fbe24aec72ec824bdef4e7578bf682407f8f25e4094cd8cd9caa4d18d`

## Safari graphical acceptance

Safari reused the existing M56.8 local test tab and navigated it to `http://127.0.0.1:7917/dashboard`.  It had 33
tabs before and after; no tab was opened or closed.  The read-only page has no form and visibly shows:

- the actually reproduced before/after change, `2 outcome reads -> 1 outcome read`;
- valid-run check -> one OS owner -> unchanged M56.8 -> pre-outcome contender rejection;
- V7 `0/18 + 0/18`, real rows `0/30`, zero real outcome/result;
- the explicit warning that sequential replay can still reopen the outcome;
- the cooperative same-host and non-production evidence boundary.

The page was readable at the top and bottom without horizontal overflow:

- `analysis/m56_9_safari_concurrency_flow_2026-09-03.jpeg`
- `analysis/m56_9_safari_sequential_boundary_2026-09-03.jpeg`

The local port 7917 service was stopped after acceptance.  The remaining read-only Safari tab is safe to close and
does not hold a lock, private outcome or execution state.

## Honest boundary and long-term contribution

M56.9 prevents two overlapping cooperative scoring launches from opening the same sealed answer twice.  This makes
the eventual B5-vs-Ours candidate human-response-equation experiment less vulnerable to accidental duplicate
scoring and result-file races, while preserving the exact preregistered scorer.

It does not prevent later sequential re-entry, direct calls to historical APIs, same-host file access, distributed
launches or malicious code modification.  It adds no human labels, real temporal rows, fresh formal predictions,
actual model performance, Equation V1 validity, solved human-response equation, full-pipeline evidence or production
readiness.

The authoritative live state remains V7 `0/18 + 0/18`, V9 and real temporal rows `0/30`, with no formal call, real
outcome access, commitment or result.  Two different humans completing the frozen V7 pilot remain the next
non-substitutable scientific dependency.  The next safe engineering question is crash-safe exactly-once scoring
continuation across sequential restart; it must be a separately frozen single-variable milestone.
