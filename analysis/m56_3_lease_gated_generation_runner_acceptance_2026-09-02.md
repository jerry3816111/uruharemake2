# M56.3 Lease-Gated Formal Generation Runner Acceptance · 2026-09-02

## Decision

**Generation-runner engineering gate: PASS. Current formal generation: DENIED. Formal model result: ABSENT.**

M56.2 established the live human/data activation boundary and a single-use lease, but no frozen path yet
consumed that lease to run B0–B5/Ours, record actual resources, commit every prediction, and release a separate
scorer only afterward. M56.3 adds that missing state machine without changing M54–M56.2 frozen evidence.

The current run did not consume a lease or call a model. V7 remains `0/18 + 0/18`, so denial is the only valid
result.

## What actually changed

### A real formal entry point, not an ad-hoc loop

`execute_formal_generation(run_id)` is the only public formal-generation entry point. It has no provider,
readiness, outcome, retry, or fallback injection parameter. A separate M56.2 controller must already have
revalidated the human chain, consumed its receipt, and created the lease. The runner then opens only:

- `generation/` for the packet, authorized views, Equation artifacts, schedule, and final submission;
- `commitments/` for request, consumed receipt, lease, prediction commitment, and scoring release;
- `telemetry/` for the call ledger or terminal failure.

The runner has no scoring path and does not enumerate, hash, or load the outcome key.

### One irreversible execution order

The frozen order is:

1. validate the consumed receipt/lease and all permitted-side content bindings;
2. atomically write a lease-bound schedule;
3. run every distinct non-empty B4 history summary first;
4. run the 210 prediction tasks in the existing 30-row condition rotation;
5. validate the complete submission and resource ledger;
6. atomically write the submission and SHA-256 prediction commitment;
7. only then create a capability for the independent scorer to read `scoring/`.

B0 uses the exact deterministic Laplace prior with zero model calls. B1–B5 and Ours each get one model call per
sample; Ours is accounted as the already frozen semantic-model call role. Each distinct non-empty B4 history
adds exactly one separately recorded summary call.

### No-retry and actual-resource contract

The real path uses one fixed local Ollama endpoint and `qwen3.5:9b`. Each call has exactly one transport attempt,
zero retries, and zero fallback. It records actual prompt/completion tokens, wall latency, process CPU, process
and Ollama memory observations, four Ollama duration fields, model identity, prompt hash, and a hash—not the
content—of the raw response. Equation artifacts are deterministically rematerialized and their CPU time is
recorded before generation.

Transport, JSON, probability, evidence, token-budget, model, hardware, artifact, task-order, or resource failure
creates a terminal no-retry failure and cannot create a commitment or scoring release. A complete commitment
still does not authorize a pass, result claim, production-memory write, deployment, or retry.

## Fail-closed evidence

The focused suite verifies:

- the formal API exposes only `run_id`;
- current live denial creates no directory, lease, call, commitment, or scoring release;
- a deliberately forged 30-row real-shaped in-memory packet can build the full 210-task mechanics but cannot
  change the live authorization state;
- the schedule is complete, ordered, lease-bound, B4-first, and reports exactly 180 prediction calls when all
  forged histories are empty;
- B5 receives no Equation artifact while Ours receives the exact fit/state/transition content;
- a complete 210-row no-call mock submission can be validated, committed, and release the separate scorer
  mechanically;
- omitted/reordered tasks, retry/fallback, outcome injection, malformed probabilities, token overflow,
  expired/mutated authority, runtime/model drift, artifact drift, and post-commit mutation fail closed;
- the synthetic rehearsal has a separate schema, zero calls, zero humans, no lease, and no formal authority.

The forged packet, tokens, latency, and memory values are test fixtures only. They are not human labels, actual
formal model resources, or performance evidence.

## Tests

- focused M56.3 suite: **14/14 passed**;
- direct M54–M56.3 compatibility suite: **137/137 passed**;
- selected M1/M2/V7/V9/M54–M56.3 compatibility suite: **202/202 passed**;
- Python compilation: PASS;
- contract and six frozen dependency bindings: PASS;
- implementation freeze: PASS;
- formal model calls: **0**;
- target-outcome access by generation: **0**;
- formal prediction commitment: **absent**;
- formal scoring release: **absent**;
- formal result: **absent**;
- runner contract hash:
  `43eceb6055d1ba12a394caf2e37f01bd0cbe35026bf6aab9186bdbd985720b6e`;
- live audit hash:
  `402fc96fb3d09cbd7b53291ee67d40c62cbfa2264d5a65dca489f7aae98bccf9`;
- no-call rehearsal hash:
  `33f3b1896afee47b96b7243a0f944b441bfd8e0c471d6b6eed915224bd7a7306`.

## Safari graphical acceptance

Safari reused the existing M56.2 tab and navigated it to
`http://127.0.0.1:7911/dashboard`. Safari remained at **29 tabs**; no tab was created or closed and no form was
submitted.

The page visibly showed:

1. `DENIED NOW`, V7 `0/18 + 0/18`, zero lease, zero formal calls, and zero commitment;
2. the six mandatory stages from lease to separate scorer;
3. 30×7 task ordering, no-retry generation, and actual resource fields;
4. a hard generation/scoring split with outcome access only after complete SHA commitment;
5. V9 `0/30`, real rows `0/30`, calls `0`, result `0`, and an explicit evidence boundary.

The desktop-width page had no visible horizontal overflow. Evidence:

- `analysis/m56_3_safari_runner_state_machine_2026-09-02.png`
- `analysis/m56_3_safari_runner_boundary_2026-09-02.png`

The local page is read-only and can be safely closed. It does not contain or hold formal private data.

## Exact remaining boundary

M56.3 proves that a future authorized generation has a concrete, fail-closed runner and commitment path. It has
not exercised that path with real data or actual model calls, so it provides no actual token/latency/memory
result and no M56 score. The hashes are application-level drift controls under the frozen runner, not digital
signatures against an attacker who can rewrite code and all local files.

The next non-substitutable dependency remains two different humans completing V7. Until V7→V9→M55 produces
30 valid real cutoff-to-future rows, this work cannot establish real-person predictive validity, Equation V1
validity, Ours superiority, private mental truth, a solved human-brain equation, full-pipeline readiness, or
production readiness.

A process interruption after calls begin but before commitment is deliberately terminal and has no automatic
resume path. A new run would require a newly human-authorized receipt and lease. This preserves the no-hidden-
retry boundary, but it can waste completed calls and is a remaining operational limitation rather than evidence
of production resilience.
