# P4-B non-B zero-journal ACK: fake staged slice (2026-10-26)

Status: **partial fake-only protocol evidence** under the same exact
implementation freeze. This follows the `8798caf` process-isolated op1
journal slice; it does not authorize a live supervisor, Ollama, Safari,
or B Send.

## Attributable change

Before, a witnessed child created the zero-count journal and immediately
reserved op1, sending only one final proof. A parent ACK barrier between
those durable states did not exist. Now the child stops after durable
zero-state creation/readback and sends exactly one fixed, sequence-1 zero
frame. The nonblocking parent requires matching run ID, zero counts,
SHA-256, canonical bytes **and pipe EOF** before sending the single `R`
command. Only then may the child reserve op1. Its sequence-2 final grant
proof is sent after both reservation commits/readback and accepted only
with exact frame plus EOF, normal child exit, worker witness binding and
signal-helper reap. No second run or refund exists.

The framed reader rejects trailing/duplicated frames even when a pipe read
returns only the first part. Unknown nested/raw fields are rejected before
child IPC and again by the parent. This change does not broaden the public
entry: `supervise_once()` still fails closed.

## Verification and limits

| Evidence | Observation | Boundary |
|---|---:|---|
| New fake staged/reader controls | 9 new tests | No real worker or provider |
| Operator and adjacent fake parity suite | **212/212 passed, 8.20 s** | Test runtime, not model latency |
| Bad zero ACK: wrong run/sequence, lost, duplicate, split-read duplicate | No `R`; disk remains zero-count | No independent durability helper |
| Broken `R` pipe | Valid zero ACK but no op1 reservation | No live transport delivery |
| Bad final sequence or split-read duplicate | Disk can remain spent; no accepted final proof | No refund or retry implied |
| Exact 4096-byte frame and trailing byte | Exact frame accepted only at EOF; trailing byte rejected | Local pipe contract only |
| Independent read-only patch review | GO **only** fake staged partial after fixing early-frame acceptance | Not a live release |
| `git diff --check` | clean | No 80/90-second physical-stop proof |

This is intentionally still a **single child** performing journal work and
representing the grant-bound worker identity. It demonstrates the ordering
barrier but not the freeze's separate supervised durability helper and
worker, worker-received grant ACK, op2–7, private transport, pre-reserved
receipt helper, exact source/model/readiness/port checks or complete
T0+80/90 schedule. A blocked child's reap can be its self-alarm; it is not
therefore a witnessed physical stop. `full_gate_pass=false` throughout.
No real HTTP/model/Web/Safari/B Send or formal/private DB write occurred.

Next necessary topology is parent + distinct journal helper + no-HTTP worker
stub: initial witnesses for both, zero ACK before worker op1 request,
durable op1 ACK before grant delivery, then exact cleanup. Preserve the
single-use disk on lost ACK. Only after broader fake matrix and another
review may receipt/transport/source preflight be considered; live remains
NO-GO under the original freeze.
