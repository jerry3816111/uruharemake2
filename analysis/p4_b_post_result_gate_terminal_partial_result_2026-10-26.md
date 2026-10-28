# P4-B post-result gate terminal — partial result / full-route NO-GO

## What changed

Before this prospective item, a real `P4BResourceGate` with a fake prompt
upper bound admitted an exact synthetic M21 request; a fake SDK response with
missing `usage` returned to the caller while the gate was
`missing_provider_usage`, with one physical ledger call. The ledger's
aggregate `total_tokens=0` in that case is a missing-value artifact, not
actual zero token use.

The inner ledger proxy now lets a successful SDK response finish its physical
ledger record and gate usage audit, then checks whether the gate is terminal
*before returning the response*. A terminal raises `P4BResourceGateError`
with the fixed reason. The original provider exception is not masked because
the new check is after the SDK `try/finally` success path. Non-B ledgers do
not take the new check. This is a source/fake **seam improvement**, not a
passed full Brain/Web product gate.

## Actual evidence and failed upper layer

| Layer | Observation |
|---|---|
| Focused before/after | Four new B post-result assertions failed before the product change (fake response returned despite terminal), one non-B control passed. After: **5/5 pass**. Missing usage, prompt > bound, completion >256, and over-2000 reported total all keep one physical call and raise the appropriate fixed terminal. The over-2000 case is already a completion-cap breach; no unreachable `actual_token_budget_exceeded` reason was forced. |
| Adjacent zero-model tests | Twelve files spanning B gate/ledger, private Web seam, M21, compute receipt, admission, compact planner and text-turn fail-closed: **196 passed, 2 strict xfailed in 47.67s**; 9 pre-existing dependency warnings. `py_compile`/`git diff --check` passed. The two xfails are *failed acceptance cases*, not passes. |
| Real compact request shape in isolated fake Brain | Actual compact-transformed M21 request starts with `\nYou are the Left Brain Planner...`; the B gate requires `You...` at byte 0. The gate returns `m21_request_drift` **before** token callback/SDK; fake provider calls 0, ledger calls 0, no episode. A dedicated passing regression checks this exact prefix and denial. |
| Desired full-route post-result test | **NO-GO / not exercised**. Two `strict=True` xfails retain the desired compact→Brain/Web expectation for a missing-usage physical call and zero final role/episode/conversation; both stop earlier at prompt prefix drift. They cannot be counted as post-result full-turn proof. Independent read-only review agrees with this boundary. |

The tests use integer or `None` usage fields. The ledger's current handling of
malformed float/bool usage has not been verified for exact reported-number
preservation here. The freeze's full-route requirement is unmet; this report
does not invoke its unrelated other-model-entry fallback clause to relabel
the prompt-prefix drift as a PASS. There was no real Ollama B Send, Web
service, Safari, production DB, deployment or human rating in this item.
No new local M31 exploratory calls were made here; the two preceding-item
accidental calls are disclosed separately.

Next necessary single variable: prospectively freeze the *exact* B M21
transformed system-prompt prefix contract, using the actual compact output
and a narrow gate acceptance rule, without silently altering the prompt or
loosening token/identity checks. Preserve the current full-route xfails, then
remove their xfail markers only if the actual request passes admission and
the missing-usage scenario reaches one fake provider call, is stopped before
visible reply/episode, and produces the private failure receipt. Production
token-bound proof, true daemon/runner identity, source/effect closure,
20-second Safari and A author ratings remain separate NO-GO gates.

## Committed-source check

Partial seam/failure-preserving commit
`009e98bc81119c059697a449248cf9d6970b0c90` was pushed to open PR #435
with an exact remote head. A single read-only committed-HEAD source snapshot
passed **239/239 files** in `0.868546s`; ledger SHA-256 was
`ee48cf025443ac78d69a61b549bdae3d5f1d0fe08d6904476d31119eec5189e2`
and resource-gate SHA-256 was
`07d55932629cd69f706356cf9596799b26c67688e63fc77ff3ba9ec78d68fa17`.
This is cached source closure, not B Send safety or response latency.
