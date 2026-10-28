# P4-B non-B split D/W cleanup: fake-only partial result (2026-10-26)

Status: **GO only for a fake-process partial WIP commit.** The exact
implementation freeze still says **NO-GO** to real Ollama/HTTP, model, Safari,
B Send and live release. Public `supervise_once()` remains fail-closed.

## Before and single change

The preceding split P+D(journal)+W(no-HTTP) op1 flow had durable zero ACK,
reservation proof and W received ACK, but a blocked D or W could be reaped by
its synthetic self-alarm without any independently witnessed stop. That alarm
was never physical-stop proof. This slice adds separate S_D/S_W signal
helpers, each initially witnessed before work GO, and bounded canonical
one-shot TERM/KILL command/result pipes. A helper brackets its fresh target
raw-generation/PGID observation, checks the original witness and signals
only the exact original PID; no `killpg` or parent-side observer/signal is
used. Parent labels `witnessed_term`/`witnessed_kill` only when the matching
helper result is `signal_sent` **and** exact `waitpid` reports that signal.

Independent review caught two real timing defects in the first patch: on
early failure cleanup waited until the work deadline, and serial D then W
response reads let a blocked D observer hide W's valid reply. The final patch
starts cleanup at the actual failure/completion time and multiplexes the two
bounded replies, retaining exact frame+EOF and canonical validation. A
parent cleanup exception now returns fixed `cleanup_unavailable`, closes
owned FDs and attempts bounded reap without leaking raw exception content.

## Evidence and limits

| Check | Result | Meaning |
|---|---:|---|
| Fake split tests | **33/33 passed** | Includes blocked D/W, initial witness failure/block, observer block/drift, ineffective TERM, KILL, IPC loss, early failure and parent exception. |
| Seven adjacent operator/identity/parity test files | **374/374 passed, 17.95 s** | Synthetic tests, not model latency or parity. |
| Early failure with a lingering W | **<0.65 s** with `work_seconds=0.8` | Regression threshold proves no wait-to-work-deadline before cleanup. |
| Blocked D cleanup observer with lingering W | W `witnessed_term`, D `unproven` | One blocked helper cannot hide the other child's witnessed stop. |
| Parent cleanup exception containing raw canary | Fixed failure code; canary absent; signal helpers reaped | Fail-closed fake exception boundary. |
| Independent read-only re-review | **GO only fake partial** | No live-release authority. |
| Diff/compile | `git diff --check` clean; both edited files compile | Local source hygiene. |

There were **zero** real HTTP/model calls, Web turns, Safari actions or B
Sends. No private/formal DB, original dirty checkout, or unrelated
`output/graduate_application_report/` was touched. All result paths still
set `physical_stop_unproven=true` and `full_gate_pass=false`. A child's
synthetic alarm or `reaped=true` alone is not a witnessed physical stop.
The PID final-check-to-`os.kill` reuse race remains documented, and this
partial witness excludes real argv/binary/listener/source/model identity.
It has no durable receipt helper, op2–7 real worker/transport, private-port
or shared-11434 proof, or actual T0+80/90-second enforcement. No graphical
or Safari acceptance is applicable/authorized for this fake-only slice.

Next necessary slice in the same frozen P4-B card: pre-reserved, separately
supervised durable raw-free receipt plus blocked fsync/replace/exit controls;
then finish the seven-operation fake transport/source/port matrix and
independent review before any committed-source/live preflight decision.
