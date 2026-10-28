# P4-B non-B separate journal/worker: fake op1 slice (2026-10-26)

Status: **fake-only partial protocol evidence** under the existing exact
implementation freeze. This is not a live supervisor, token-parity result,
P4-B pass or authority for Ollama, Safari or B Send.

## Before and attributable change

Before, one witnessed child both created/reserved the journal and stood in
for the worker. The zero-count ACK ordering was tested, but an independent
durability helper and worker grant delivery were not. This slice adds a
private P(parent) + D(journal child) + W(no-HTTP worker stub) topology for
**op1 only**. D and W each send an initial macOS raw-generation/PGID witness
before any work. P verifies both, then permits D to durably create/readback
the zero journal. Only after its exact zero ACK does P allow W's op1 request;
only after D durably reserves/readbacks the grant, sends its proof and exits
normally does P deliver the grant to W. A valid W received ACK plus normal
exit is positive evidence of *receipt*, never of HTTP issue or wire delivery.

Ten one-shot, bounded canonical IPC edges carry only fixed allowlisted
frames. Each framed read requires exactly one frame and EOF; actual encoded
bytes are decoded and checked again **before** `os.write`, so an injected
encoder cannot place raw canary fields on IPC. Missing/wrong ACKs, partial
write, crash or durable ACK loss are terminal and never refund the run.
`worker_received_proven=false` means *not proved*, not "definitely not
received"; `durable_reserved=unknown` is retained after a possibly sent
reserve command without D's final proof. `on_wire=unknown` throughout.
The public `supervise_once()` remains fail-closed.

## Evidence and cost

| Check | Observation | Boundary |
|---|---:|---|
| New fake split controls | **20/20 passed** | Synthetic children; no real worker HTTP |
| Six affected operator/parity/identity test files | **339/339 passed, 10.92 s** | Test wall time, not product latency |
| Bad/lost/duplicate zero ACK; wrong W witness; post-durability grant or W ACK loss; partial reserve write; D/W crash; existing run | No false positive; disk may remain spent; no retry/refund | No op2–7 or live source/model |
| Blocked create/reserve fsync | Parent bounded, positive grant unproven | Reap may be child self-alarm, not witnessed stop |
| Injected nested raw before request or through encoder | Fixed failure; marker pipe confirms no canary bytes written to IPC | Not a hostile-host security guarantee |
| Independent read-only patch review | GO **only** for this fake protocol partial after pre-write encoded-byte fix | Not full freeze or live GO |
| `git diff --check` | clean | No Safari/visual acceptance |

There were **zero** real HTTP calls, model generations, Web turns, Safari
actions or B Sends; formal/private DB and original dirty checkout were not
used. The separate D/W processes are real short-lived synthetic test
children, but this topology has **no signal helper**. Its result deliberately
keeps `physical_stop_unproven=true` and `full_gate_pass=false` even when both
children exit normally. Thus it does not prove frozen T0+80/90 physical
cleanup, exact daemon/runner/port/11434 state, private stderr handling,
pre-reserved durable receipt, source-conditioned BOS/NumCtx/truncation, or
provider prompt-token parity. These lower-layer tests do not authorize a
real non-B attempt.

Next necessary safety slice: independently witnessed exact-PID TERM/KILL
cleanup for both D and W, including blocked witness/ineffective-signal and
actual waitpid-status controls, while retaining raw-free failure. After
that, a separate receipt helper, op2–7 transport/port/source controls,
full fake matrix, committed-source audit and read-only preflight still
precede any separately reviewed live release decision.
