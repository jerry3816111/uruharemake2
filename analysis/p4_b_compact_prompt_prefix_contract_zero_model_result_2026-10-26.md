# P4-B actual compact M21 prefix — scoped zero-model result

## Outcome and causal boundary

The previous committed partial result remains a failure: actual
`compact_request` preserved exactly one leading LF in M21's system prompt,
while the B gate required `You...` at byte zero. Its isolated fake route
stopped at `m21_request_drift`, fake provider 0 and ledger 0; neither
post-result full-route expectation had been exercised.

This prospective item changed one gate admission condition. It now accepts
the prior `You...` start **or** exactly `\nYou...` before the same literal
instruction. It does not strip, mutate, or normalize the request or change
the prompt-token callback, stage, model, generation budget, identity, or
post-result rules. Two LF, space, CRLF, banner, and altered instruction
remain denied before the fake provider.

## Evidence

| Check | Observation |
|---|---|
| Red before product change | Newly added prefix gate tests: **1 failed, 6 passed**. Only the exact single-LF positive was rejected as `m21_request_drift`; the old prefix and five negative shapes behaved as expected. |
| After narrow change | Focused gate plus actual compact→Brain/Web file: **44/44 passed**. Before removing their strict xfail markers, both full-route desired tests became `XPASS(strict)`, and the historical before-state assertion then failed because the gate now reached the fake SDK and returned terminal `missing_provider_usage`. That assertion was converted into a positive actual-prefix regression. |
| Actual transformed request | Isolated `compact_request`→M21 uses the original single-LF system bytes. The exact bytes admitted by the gate reach the fake SDK unchanged: physical fake provider **1**, ledger **1**, terminal `missing_provider_usage`. Missing token usage is unknown, not zero. |
| Brain/Web failure effects | On the missing-usage path, the error propagates before final role reply or saved episode; `web._run_turn` writes one raw-free private failure receipt at mode `0600`, with no conversation JSONL. This is Python/isolated fake-provider Web runtime evidence, **not** a browser-bound submit/Safari test for this exact error. |
| Adjacent tests | Twelve affected zero-model files: **189 passed** in **22.18s**, 9 pre-existing dependency warnings. Changed-file `py_compile` and `git diff --check` passed. Independent read-only scoped review: GO only for this source/fake patch. |

The callback in the direct gate test and the fake SDK see identical system
bytes. The full compact-route test independently checks the actual
transformed bytes and fake SDK bytes. No new real model calls, live Web
service, Safari Send, production DB, deployment, or human ratings occurred.
The fake bound (`1200`) does not establish the real Ollama 0.34.4 prompt-token
upper bound or actual runtime token cost. True daemon/runner identity,
source/effect closure, 20-second delivery, A author ratings and the full
product B release remain **NO-GO**. Earlier real/sandbox failures and the
previous partial report are not reclassified.

## Committed-source check

Scoped commit `b280b6a76db0651cccef7adbb09336782720b31a` was pushed to
open PR #435 with an exact remote head. A single read-only committed-HEAD
source snapshot passed **239/239 files** in `0.862276s`; gate SHA-256 was
`51dc6297175da6590b64250a51f9419f5aab89ca991af0e914f1e9aa5e9eea2f`,
ledger SHA-256 was
`ee48cf025443ac78d69a61b549bdae3d5f1d0fe08d6904476d31119eec5189e2`,
Brain SHA-256 was
`c1833a55ecb9c690decca66d1b90a6bdf075780db83066a5b9c6ea47bc0e7fff`,
and Web SHA-256 was
`2b541d6f3a1062ae3972df33676597fb42f60b8f19c9610338595f04fc90167a`.
This cached source check is not product response latency or B Send safety.

## Next necessary gate

Before any fourth true Ollama retry or Safari B Send, separately establish a
production-equivalent, fail-closed upper bound for the **transformed** M21
request against the actual Ollama model/template identity and the frozen
2000-token budget, then review the remaining true-product identity/effect
and delivery gates. Do not treat this fake bound as that oracle.
