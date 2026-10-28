# P4-B non-B parity operator: fake-only partial result (2026-10-26)

Status: **partial WIP, not a live-release GO or a P4-B pass**. This note is
about an isolated synthetic non-B operator contract. It is not a new B
measurement, a provider result, a Web/Safari result, or evidence for a
general human-response-equation claim. The frozen question, fixture, gate,
gold, production memory and original dirty checkout were not changed.

## Observable change and boundary

Before, `compare_non_b_parity()` had seven injected fake HTTP calls, six fake
identity observations and a five-second callback clock, but no durable
single-use grant journal. The new `p4_b_non_b_parity_live_operator.py` adds:

```
fixed synthetic request
    -> six injected OS-only identity observations
    -> seven ordinal/method/path/payload-bound fake grants
    -> fsynced single-use journal (operation 7 spent before ACK)
    -> injected fake responses + source-conditioned pre-completion checks
    -> raw-free fake parity summary
```

The journal starts with an exclusive, fsynced zero-count state, fails closed
on existing run directories and uncertain durability, and never refunds a
grant after lost ACK. The worker checks the frozen render, two equal
tokenizer lists, bound fake process identities, branch/BOS/NumCtx and Go
rendered UTF-8 byte threshold **before** operation 7. The reported signed
delta is fake response `prompt_tokens - runner token-list length`, not
observed provider parity. A callback can still block this worker. The
public `supervise_once()` intentionally raises
`process_supervisor_not_implemented` before callbacks or effects; it cannot
launch a daemon, issue real HTTP, or claim physical stop.

## Verification performed

| Evidence | Result | What it does not prove |
|---|---:|---|
| New fake-only tests | 85 passed in 0.56 s | Real worker, transport, watchdog, process cleanup or provider usage |
| New + adjacent old tests | 177 passed in 0.78 s | Full repository/runtime regression or production delivery |
| `git diff --check` | clean | Functional correctness |
| Independent read-only patch re-review | GO only for **partial fake WIP**; six identified local defects corrected | Live release, full freeze negative matrix or B Send |

The six corrected local defects were stale in-memory journal state after a
post-replace fsync failure, grant continuation after ACK failure, bool/int OS
witness equality, in-place grant mutation by a fake HTTP callback, premature
fake `on_wire=yes`, and conflicting/nonadjacent render-branch flags. The
positive and negative tests use injected responses and temporary directories;
they made **zero** real HTTP/model/process/Safari calls. Actual generation
tokens, provider latency, model cost and cold-load cost remain unmeasured.
The pytest wall time is a test-run cost only, not an application latency.

## Remaining release gates

The exact freeze's nonblocking process-backed parent, witnessed helper
startup, T0+80/90 watchdog, exact-PID TERM/KILL/reap and private-port/11434
proof, durable raw-free receipt, real transport's atomic grant consumption,
and blocked-helper/crash/cleanup negative controls are **not implemented**.
Same-run private source/model/binary evidence, full affected regression,
independent live preflight, a separate live GO, at most one synthetic non-B
attempt, graph/Safari acceptance and any B Send remain pending. `on_wire`
in the fake harness is a simulated observation, not a wire-level witness.

The next necessary implementation under the **same frozen task**, not a new
M or a changed research question, is a process-backed, nonblocking parent
plus receipt and isolated blocked-helper/cleanup tests. Preserve the
existing fail-closed public entry until that whole layer is independently
reviewed; do not use these 177 tests to authorize live effects.
