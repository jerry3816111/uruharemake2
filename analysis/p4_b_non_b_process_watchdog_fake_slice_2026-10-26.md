# P4-B non-B process watchdog: fake-only slice (2026-10-26)

Status: **partial fake-only WIP**, not the frozen live supervisor, a provider
parity result, P4-B release, or Safari/B Send authority. This is a necessary
execution-safety slice under the existing exact implementation freeze, not a
new milestone or a change to the synthetic request, model, gold, or baseline.

## Before and actual change

Before this slice, `worker_once()` could run seven injected fake calls with a
durable grant journal, but a blocked injected callback could hold its thread.
`supervise_once()` correctly refused all execution. This slice adds a private
`_supervise_fake_callback_once()` experiment with **short-lived synthetic fork
children only**. The worker and separate signal helper each send an initial
macOS raw-generation/PGID witness while the work callback remains behind a
GO barrier. A missing, blocked, or inconsistent initial witness issues no GO.
The parent uses bounded pipe/select polling and `waitpid(WNOHANG)` rather
than executing the injected work or cleanup observer itself. The helper
rechecks the original PID/PPID/generation/PGID, with strict typed canonical
comparison, immediately before an exact-PID TERM or KILL; it never calls
`killpg`. Child self-timeout is a test-hygiene backstop, not a successful
cleanup proof. An exact `waitpid` signal exit status is required for the
fake `witnessed_child_reaped` outcome; a returned but ineffective signal
followed by self-timeout remains `physical_stop_unproven`.

The new result schema is permanently `fake_process_watchdog_partial_v1`
with `full_gate_pass=false`. `go_issued` reports only that the GO byte was
sent, **not** that the callback began. Pipe failures return fixed codes.
The public `supervise_once()` is unchanged and still raises
`process_supervisor_not_implemented` before effects or writes.

## Verification and limits

| Evidence | Result | Claim boundary |
|---|---:|---|
| New isolated process tests | 12/12 passed | Only synthetic fork children; macOS-dependent tests skip elsewhere |
| Prior journal/worker tests plus adjacent parity tests | 189/189 passed, 5.01 s | Test-run time, not product/model latency |
| Focused process tests repeated before final patch | 11/11 in three consecutive runs | Timing stability sampling, not a 90-second proof |
| `git diff --check` and post-test process listing | clean; no matching test child remains | Not a general orphan-process guarantee |
| Independent read-only review | GO only for this **fake partial** after fixed-code GO failure control | Not live release or complete freeze matrix |

The negative controls cover blocked work and initial/cleanup witnesses,
wrong or equal-in-Python but type-different identity, final observer drift,
ignored TERM followed by exact KILL, missing `waitpid` exit proof,
ineffective no-op signal, broken TERM command, and broken GO. Tests leave
the original dirty checkout, formal memory DB and unrelated untracked
`output/graduate_application_report/` untouched. They issue **zero** real
Ollama launches, HTTP calls, model generations, Web turns, Safari actions,
or B Sends.

## Still required before any live decision

This private fake slice is not connected to `worker_once()` or its durable
journal. It has no real source/model hashing, daemon/runner startup,
one-use transport grant consumption, private-port or shared 11434 proof,
reserved receipt helper, raw-free durable receipt, or T0+80/90 physical
cleanup test. Its scaled subsecond timers and incomplete argv/binary/listener
witness do **not** prove the exact freeze's 90-second live condition. The
same-helper final-check-to-`os.kill` PID-reuse race remains a documented
cooperative-local residual. Unhandled fork/pipe allocation failures and
arbitrary hostile child code are outside this partial proof.

Next necessary work under this same card is to connect the journal/worker
through a supervised process/transport boundary and durable receipt, add
blocked fsync/hash/readiness and port/11434/crash negative controls, and
obtain another independent patch review. Only then may committed-source
audit, read-only live preflight, and a separate live GO be considered. Even
a later non-B parity delta of zero would not prove the B token bound,
20-second Web delivery, Safari quality, or the full project Goal.
