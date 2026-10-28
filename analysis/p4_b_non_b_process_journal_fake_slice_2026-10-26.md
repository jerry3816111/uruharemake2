# P4-B non-B process journal: fake-only isolation slice (2026-10-26)

Status: **partial fake-only WIP** under the existing exact implementation
freeze. It is not a live supervisor, a provider parity result, a P4-B pass,
or authority for Ollama, Safari, or B Send.

## Before and one change

Before, `DurableJournal.create()` and `reserve()` could synchronously block
on file/directory fsync or replace. The previous private process watchdog
proved bounded response to a synthetic callback but was not connected to
journal I/O. This slice runs zero-journal creation and **only op1** reservation
inside a witnessed, disposable macOS fork child behind the existing GO
barrier. The parent never calls journal I/O; it accepts a bounded canonical
proof only after the child readbacks the committed state, exits normally,
and the cleanup helper is reaped. A real child's raw-generation witness is
bound into the fake grant; it does not reuse the fixed-PID unit fixture.

The proof IPC is limited to an exact grant allowlist plus journal SHA-256;
unknown nested fields and arbitrary callback data are rejected in the child
*before* a frame is written and checked again by the parent. The returned
schema remains `fake_process_journal_partial_v1`, always has
`full_gate_pass=false`, and never reports `on_wire=yes` or a worker-issued
HTTP call. `supervise_once()` is unchanged and fail-closed.

## Evidence and honest boundary

| Check | Observed result | What it does not show |
|---|---|---|
| New isolated fake journal/process controls | 14 new tests; 26/26 combined fake journal/watchdog tests | No real process/model/port topology |
| Operator plus adjacent fake parity suite | 203/203 passed in 6.90 s | Test runtime is not product/model latency |
| Blocked create file/dir fsync; reserve file/dir fsync; replace; post-ACK file/dir fsync | Parent returned within the test's 2 s ceiling, with no positive journal proof | Scaled timers are not a physical T0+90 s proof |
| Post-replace directory-sync failure; child death after commit; existing-run reuse | No proof/no refund; disk can remain spent, and retry does not mutate it | No cross-process seven-operation journal yet |
| Wrong child worker binding, int/float expiry byte drift, arbitrary nested raw canary, unreaped signal helper | Positive proof rejected; no raw canary in returned result | No live argv/binary/listener witness |
| `git diff --check` | clean | No production or Safari acceptance |

Independent read-only patch review: **GO only for this fake partial patch**
after correcting an initially exposed arbitrary frame payload and requiring
signal-helper reap. The review did not authorize live execution. A blocked
child's eventual reap can be its self-alarm; this table claims bounded
response and **no false durable proof**, not witnessed physical stop.

This deliberately **does not implement the freeze's zero-count ACK barrier**:
the same child performs `create()` then op1 before sending its single final
proof. `DurableJournal.reserve(ack=...)` records only that a local callback
returned, not that a parent or worker received a grant. It also is not the
required separate durability helper alongside a worker. Those are the next
protocol steps, followed by op2–7, transport consumption, reserved receipt
helper, blocked hash/readiness/cleanup and private/shared-port controls.
The public operator must remain NO-GO until those steps, patch review,
committed-source audit, read-only live preflight, and an explicit separate
live release decision. The 80/90-second physical stop, source-conditioned
token parity, B prompt bound, 20-second Web delivery, Safari and human
quality are all still unmeasured here. No formal DB, real HTTP, model,
Web turn, Safari action or B Send was used.
