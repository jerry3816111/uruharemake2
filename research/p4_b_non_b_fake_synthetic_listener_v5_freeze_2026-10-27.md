# P4-B non-B v5 prospective synthetic listener/readiness freeze

Status (2026-10-27): **independent read-only design review GO only for a
scoped prospective freeze commit, then fake-only red/source/tests after
exact-head verification; NO-GO for live Ollama/HTTP/model/Safari/B Send**.
The review first found exact-wire, S_H EOF, deadline and continuity-claim
gaps; the revised contract resolved them. This is a
prospective fake-only amendment to
`p4_b_non_b_live_supervisor_exact_implementation_freeze_2026-10-26.md`,
not a release. V1–v4 contracts, results, byte schemas and failures remain
unchanged. It does not change the B question, source predicate, gold, model,
generation budget or formal evidence.

The single synthetic loopback LISTEN socket below is a **reviewed v5
exception** to v3/v4 tests' zero-socket fake boundary, within the user's
authorized local development scope. It does not authorize a provider socket, external network or
additional HTTP. Acceptance uses the existing project interpreter
`.venv/product_checks/bin/python` with locally observed `psutil 7.2.2`;
missing/different per-process observation support fails closed, with no
system Python or package-install fallback.

## Before, one variable and evidence boundary

At committed `7160bbf`, v4 proves that an initially witnessed O hashes a
23-byte operator-owned fixture and proves daemon-port vacancy before P sends
`W_GO`. It then releases W without a daemon process or readiness witness.
The test binding's daemon PID/argv/hashes are injected values, not an
installed source/model attestation. The one v5 variable is **whether a
separately supervised synthetic child owns a local LISTEN socket on the
exact bound private daemon port and O independently observes that fact
before W is released**. H's self-report or O's injected v2 port snapshot
alone is not readiness. A ready listener and correct installed source are
distinct hypotheses: neither proves the other. V5 does not authenticate
Ollama binary, argv, GGUF, source revision or the 4.4 GiB model store.

Allowed after design GO only: the fake-only operator, its test, this
freeze, one concise result, and `CURRENT_TASK.md`. The public
`supervise_once()` remains fail-closed. No model, provider HTTP, real
Ollama daemon/runner, production DB, original dirty checkout, or external
network is within this amendment. One test-only loopback LISTEN socket is
allowed; no accept, connect or HTTP request to it. The seven W operations
remain injected fake opener calls; `/api/version` is still ordinal 1,
never an eighth readiness probe.

## Phase-scoped FD and process topology

The v4 fake path reserves 123 pipes / 246 IPC endpoints at once and runs
eight fake children. The observed macOS soft `RLIMIT_NOFILE` is 256, so
reserving another 12 pipes up front (270 simultaneous endpoints) is
forbidden. V5 requests an explicit, narrow exception to the old
all-pipes-before-any-work-GO wording, **without relaxing any IPC proof**:

1. Reserve the unchanged 123 base pipes before D_GO. Obtain D's durable
   zero-count journal ACK and R's zero-journal preflight ACK exactly as v4.
2. While W has not received GO, and **before O forks**, atomically reserve
   12 additional one-shot pipes: O `o_ready_cmd`, `o_ready_proof`; H
   `h_initial`, `h_go`, `h_ready`, `h_stop`, `h_stopped`; S_H `initial`,
   `term`, `term_result`, `kill`, `kill_result`. Thus 24 extra endpoints
   are created only after consumed base parent ends have closed. The 135
   pairs / 270 endpoints are cumulative, never simultaneously open in P.
3. Check actual open-FD count and maximum numeric FD against the unchanged
   soft limit at both reservation barriers and around H's listener open;
   record measured parent/O/H peaks, not just the 123+24 arithmetic. No
   `ulimit` change is allowed. On partial allocation or insufficient
   headroom, close only newly acquired ends, start no O/H callback or W,
   issue zero grants/fake HTTP, attempt witnessed D/W cleanup and request
   R's already-preflighted raw-free 0600 failure receipt if R and durable
   I/O remain available. Do not retry against the one-use journal.

H and S_H increase the attempted positive topology from eight to ten
children. D stays durability-only; O/S_O stay observer and its exact-PID
signal helper. O receives its v5 readiness pipe ends because they exist
before O forks. O, S_O, H and S_H close *every* unowned inherited base/v5
pipe end immediately; P closes duplicate ends at handoff. In particular,
no H/S_H copy may hold `o_ready_proof`'s writer open. Every new H/O
readiness child-to-P edge must contain exactly one <=4096-byte canonical
`fake_seven_process_ipc_v1` frame plus EOF; S_H retains the existing
separate `_split` canonical frame+EOF schema. Wrong run/phase/sequence,
initial witness, field set, duplicate/trailing bytes, or missing EOF is
terminal. Existing `o_final` is reserved for its original post-cleanup
two-port proof and cannot be repurposed for readiness.

## Synthetic listener admission sequence

Only after P validates the entire v4 SHA/count + vacant daemon-port
composite proof may it fork H. H closes unowned ends, calls `setsid()`
before its initial witness, establishes its
actual `(pid, ppid, raw_generation, pgid)` witness, sends `h_initial`
frame+EOF, and waits. P validates exact initial PID/parent/witness; then
it forks independent S_H and validates S_H's initial frame+EOF **before**
H receives `h_go`. Failed initial capture starts no bind or W. H and S_H
use independent hard deadlines; their self-alarms are not witnessed stop.

`h_go` binds the existing private daemon port, H witness and a one-use
nonce. H alone creates one `AF_INET/SOCK_STREAM` socket bound to literal
`127.0.0.1:{daemon_port}` and calls `listen`; no wildcard/IPv6,
`SO_REUSEADDR`, `SO_REUSEPORT`, accept, connect, HTTP handling, model loading, subprocess
daemon or fallback port is allowed. Collision, missing permission or
blocked bind is failure. A v5-only test hook may stall, crash, close this
synthetic listener or print a raw canary at fixed H phases, but cannot
select a port or return a ready proof/identity. This test hook is limited
to phases before O's admission proof; it cannot certify or inject
post-admission continuity. H sends one strict `h_ready` frame+EOF only
after listening and normally retains the socket until planned stop. H's
frame alone never grants W authority.

P then sends `o_ready_cmd` with the bound port, H's initial witness and
nonce. In separate, already witnessed O, two `_fake_os_witness(H_pid)`
reads bracket the OS connection inspection and must equal H's initial
PID/parent/raw generation/PGID. Between them O queries the installed
per-process `psutil.Process(H_pid).net_connections(kind="tcp4")` and
requires a matching H-owned `AF_INET/SOCK_STREAM/LISTEN` endpoint on
literal `127.0.0.1:{daemon_port}`. Empty, incomplete, AccessDenied,
unsupported, changed witness, wrong owner/port/address/state, wildcard or
IPv6 cannot pass. No root-only system-wide query, H-provided owner flag or
injected `port_observe` snapshot may substitute. O sends only a bounded
port/witness/nonce-bound proof hash, not raw connection rows, on
`o_ready_proof` frame+EOF. P validates both H and O proof, checks with
nonblocking waitpid that both H and prewitnessed receipt helper R are still
live, and only then sends `W_GO`. An observed R death gives zero W_GO,
grant or fake opener; an R death after this check remains a cooperative
poll-to-GO race and is not H readiness evidence.
The OS observation-to-W_GO race is a stated cooperative limit; this
subverdict is a synthetic admission instant, not continuous readiness.
H remaining alive during seven operations does **not** prove its socket
stayed in LISTEN. A post-admission socket close with H alive is outside
this v5 verdict and must not be reported as a continuity PASS; a separate
later gate would need repeated independent OS observations to claim that.

Before each later ordinal grant P nonblockingly checks H has not exited.
An observed loss forbids any *subsequent* grant; already granted operations
are not refunded or recoded `on_wire=no`. A crash between checks remains
a residual race, not proof of uninterrupted readiness. No added identity
or source predicate may be silently inferred from H's Python PID or the
test binding's invented Ollama PID/hash.

## Exact v5 wire and verdict contract

Every v5 H/O frame retains the v4 canonical outer envelope
`{schema="fake_seven_process_ipc_v1",run_id,phase,seq,witness}` and has
**exactly** the following additional fields; no optional or unknown keys:

| Edge | Phase / seq | Exact additional fields |
|---|---|---|
| `h_initial` | `initial` / 0 | `role="H"` |
| `h_go` | `h_go` / 1 | `daemon_port` (bound non-bool int), `nonce` (lowercase 32-hex) |
| `h_ready` | `h_ready` / 1 | `daemon_port`, `nonce_sha256` (SHA of UTF-8 nonce), `listener_state="listening"` |
| `o_ready_cmd` | `o_ready_cmd` / 2 | `daemon_port`, `h_witness` (exact validated H initial witness), `nonce_sha256` |
| `o_ready_proof` | `o_ready_proof` / 2 | `daemon_port`, `h_witness_sha256`, `nonce_sha256`, `listener_observation_sha256` |
| `h_stop` | `h_stop` / 2 | no extra fields |
| `h_stopped` | `h_stopped` / 2 | `listener_closed=true` (exact bool) |

The `h_*` envelope witness is H's exact initial witness; `o_ready_*`
uses O's. `h_witness_sha256` is SHA-256 of canonical H witness. The
normalized listener observation is exactly
`{pid,ppid,raw_generation,pgid,family:"AF_INET",type:"SOCK_STREAM",
status:"LISTEN",host:"127.0.0.1",port}` with the four identity fields
byte-equal to H initial and port byte-equal to binding; O may hash this
object only after validating its actual per-process OS row. P independently
computes the same canonical SHA from H initial + frozen socket literals,
then compares it to `listener_observation_sha256`. O/P also require the
matching nonce hash, port, H witness hash, frame and EOF. This is not an
assertion that P itself inspected the socket. For v5 only, existing
`o_final` and `o_final_proof` use seq 3 (not v4's seq 2); their field
sets remain unchanged. S_H uses the existing `_split` initial/TERM/KILL
frame schema with target role H, accepted **only** in the v5 path; the
v1–v4 signal validators must not be globally widened.

The v5 result key set is exactly the v4 result key set plus
`synthetic_listener_gate_proven`, `listener_observation_sha256`,
`continuous_listener_proven`, `daemon_stage_failure_code`, `h_reaped`,
`h_stop`, `h_term`, `h_kill`, `s_h_reaped`, `s_h_normal_exit`. The v5 R
receipt key set is exactly the v4 receipt key set plus those same ten
fields, with literal `snapshot_phase=`
`"after_d_w_h_o_cleanup_attempt_before_r_final_reap"`; v4 retains its
old snapshot literal. `synthetic_listener_gate_proven`,
`continuous_listener_proven`, `h_reaped`, `s_h_reaped` and
`s_h_normal_exit` are exact bools, and `continuous_listener_proven` is
permanently false. `listener_observation_sha256` is the exact expected
lowercase 64-hex SHA iff the entire H+O admission barrier passed; otherwise
null. It may remain present after a later H or R failure. `h_stop` uses
the existing exact `unproven|normal_exit|witnessed_term|witnessed_kill`
enum; `h_term`/`h_kill` use the existing `_SPLIT_CLEANUP_CODES` enum.

`daemon_stage_failure_code` is exactly one of `not_started`, `none`,
`phase2_fd_unavailable`, `h_initial_unavailable`,
`s_h_initial_unavailable`, `h_go_unavailable`, `h_ready_unavailable`,
`h_ready_mismatch`, `o_ready_unavailable`, `o_ready_mismatch`,
`h_lost_after_ready`, `h_stop_unavailable`, `h_cleanup_unproven`.
`not_started` applies when an earlier v4 gate prevents H work; `none`
requires successful v5 admission and normal H/S_H stop. An OS inspection
failure, denied access, blocked O, wrong owner or malformed/absent O frame
is `o_ready_unavailable` unless a complete well-formed but wrong proof
was actually received (`o_ready_mismatch`); do not invent a more specific
public cause from test-only knowledge. H bind failure, blocked callback,
crash or missing H frame likewise maps to `h_ready_unavailable`; a complete
wrong H frame maps to `h_ready_mismatch`.

Only v5 may use its new literal stage failure codes as top-level
`failure_code`. The first non-`none`/`not_started` stage code is retained.
Final top-level priority is (1) missing/unproven R durability or R normal
exit -> `receipt_unavailable_review_required`; (2) unproven H/S_H/D/W/O
cleanup -> `cleanup_review_required`; (3) non-`none` v4
`pre_stage_failure_code`; (4) non-`none`/`not_started` v5
`daemon_stage_failure_code`; (5) existing later work failure. A v4 failure
before R preflight retains its existing specific code. H/S_H normal
positive exit does not permit a signaled-stop PASS. Receipt stage fields
must equal P's validated values, while its provisional top-level code may
differ from P after R's own exit; no receipt predicts its own exit.

## Bounded fake clock, not a T0+90 claim

Let `B = work_deadline + cleanup_seconds + 0.10`, the v4 fake
`hard_deadline`. These are **latest** monotonic limits; successful or
failed work enters cleanup immediately, never waits for B. H planned
stop/proof is due by `B+0.08s`; S_H TERM/KILL response and H reap by
`B+0.25s`, with H/S_H hard lifetime `B+0.30s`. O final port proof is due
by `B+0.45s`, O/S_O witnessed cleanup/reap by `B+0.70s`, and their hard
lifetime is `B+0.72s`. R receipt fsync/replace/proof has a separate
deadline `B+1.20s`; R/S_R cleanup by `B+1.35s` and hard lifetime
`B+1.45s`. Work and any new H admission still stop at the original
`work_deadline`; no v5 callback extends the seven-operation budget. A
blocked S_H/O fresh witness may consume its allotted interval but cannot
consume R's reserved later interval. A missed limit is FAIL with fixed
codes and conditional raw-free R receipt; it is never a fake timing PASS.
No number here establishes actual T0+90 provider cleanup.

## Cleanup, receipt and acceptance

Positive order after W/D final proofs: send H one `h_stop`, require
`h_stopped` frame+EOF after listener close, exact normal waitpid exit and
normal S_H exit. On the normal path P closes both unused S_H TERM/KILL
command writers, drains/reaps S_H and verifies normal exit before O final;
otherwise S_H can wait for EOF and falsely look unfinished. A signal stop
is failure cleanup only and **never** qualifies for v5 PASS. Only then
may O perform its existing final daemon+runner
vacancy/11434 proof; O/S_O subsequently exit normally. On H block/crash
or failed planned stop, S_H may TERM/KILL only after its fresh same-helper
raw-generation/PGID/parent check. A witnessed signal stop needs both
`signal_sent` and the matching waitpid signaled status. Identity drift or
blocked fresh witness means **no signal** and unproven stop. H self-alarm,
H's own stopped frame, a vacant port or S_H's send report alone cannot
prove exit. The final-check-to-`os.kill` PID-reuse residual remains.
H/S_H cleanup precedes O final proof and R's separately reserved receipt
window. A blocked readiness/cleanup callback must leave P responsive and
R able to write a raw-free 0600 failure receipt when R/fsync remain usable.
If failure precedes W ordinal 5, runner port is unknown: never copy it
from the injected binding or claim the existing two-port post-vacancy
subverdict. R receipt snapshots before its own exit; it cannot predict
that exit, and R durability/exit failure dominates overall status.

Use strict distinct `fake_seven_process_result_v5` and
`fake_seven_process_receipt_v5` allowlists, pinned precisely below. A
first pre-W_GO cause is immutable; cleanup/R failures change overall
status without erasing it. A proven listener subverdict may remain true
after a later H/R failure, but overall v5 PASS requires normal H/S_H and
all prior child exits, O final two-port proof and durable R receipt/exit.
V1–v4 validators reject v5-only fields/codes and v5 cannot accept their
old readiness phase. Regardless of fake PASS,
`physical_stop_unproven=true`, `full_gate_pass=false`, and
`b_send_authorized=false`; source/model identity remains unproven.

Red-before-source tests must prove the present absence of H; then cover
positive v4→H/S_H→O LISTEN-owner→W_GO→7 fake calls→H stop→O final→R,
actual parent/O/H FD peaks <256, EOF with no inherited writers,
phase-2 allocation failure, H/S_H initial refusal, bind collision,
blocked/crashed H before/during/after ready and mid-run, wrong listener
owner/address/port/state, drifted raw generation/PGID, corrupt/duplicate/
trailing ready or O proof, blocked cleanup witness, TERM ignored/KILL
uncertainty, R failure before/after readiness, and printed canaries from
H/O/S_H. Pre-W_GO failures require zero W_GO/grants/fake opener plus
the durable zero journal and R failure receipt when available; mid-run
loss forbids only subsequent grants. V5-scoped socket sentinels allow
only H's exact local bind/listen: zero accept/connect/provider HTTP/model.
Preserve v1–v4 tests, run affected regression and independent patch review
before scoped commit/push/PR exact-head check.

Passing these tests would prove only a bounded synthetic process/listener
admission and cleanup *control path*. It cannot prove Ollama startup or
readiness, installed source/binary/argv/GGUF identity, the pre/post 4.4 GiB
model-store SHA calls, real seven HTTP sends, T0+90 physical cleanup,
Safari, B Send, model quality or the human-response equation. A separate
committed-source audit, read-only live preflight and explicit live GO are
still mandatory. The reviewed fake-only source scope becomes available only
after this exact freeze is committed/pushed and the PR head is checked.
