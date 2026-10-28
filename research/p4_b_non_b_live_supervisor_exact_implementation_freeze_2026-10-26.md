# P4-B non-B parity: exact live-supervisor implementation freeze

Status: **independently reviewed GO only for the listed fake-only source and
tests; NO-GO real HTTP/model/process, Safari or B Send.** Initial read-only
review found four contract gaps, and the first re-review found a PID-only
check-to-signal overclaim. Both were corrected above; the final independent
read-only review accepted only this fake implementation boundary. The
previous prospective design at `352223c` is a design baseline, not
executable authority. A separate patch review, committed-source audit,
read-only live preflight and explicit live-release decision are still
required before at most one synthetic non-B attempt. This does not change
the B question, gold, gate, or formal evidence.

## Before, single variable, allowed scope

Before: `compare_non_b_parity()` completes seven **injected fake** HTTP
operations and six fake OS observations under a five-second callback clock.
It has no independent process watchdog, durable attempt reservation, live
transport or PID cleanup. The old `_stop_exact()` may wait about five seconds
for TERM and two for KILL **per PID**, so sequential use cannot prove the
prospective T0+80 to T0+90 cleanup window. Existing 92 focused / 244 adjacent
tests remain the baseline, not evidence of actual provider parity.

Single variable: add one isolated, one-use supervisor/worker/transport around
the already frozen synthetic `fixed_transformed_request()` shape. The
observable delta remains `provider prompt_tokens - both-equal runner token
list length`; H0 is delta zero **only if** the source-conditioned BOS,
rendering and no-truncation predicates below hold. Failure is retained;
neither the fixture nor tolerance can be changed after observation.

Allowed implementation files after freeze review: new
`p4_b_non_b_parity_live_operator.py`, new
`test_p4_b_non_b_parity_live_operator.py`, this freeze, a concise result note,
and `CURRENT_TASK.md`. A shared-pure extraction from
`p4_b_non_b_usage_parity.py` would require a separate prospective amendment
and behavior-equivalence proof; it is **not** authorized here. Do not modify
the product gate/boot/ledger/Brain/Web, frozen question/gold, old zero-turn
operator, fake adapter, private research DB, or original dirty checkout.
Tests use injected fake transport, fake/ephemeral child processes and private
temporary directories only. No source change may silently launch Ollama.
The eventual run directory must be a new 0700 path outside the repository;
the existing private model clone is read-only and must not be rebuilt.

## API and single-use state machine

Implement one public operator entry, `supervise_once(*, run_dir, model_root,
clock, effects) -> receipt`, where `effects` is an explicit, injected bundle
for spawn/poll/reap, process observation, exact-PID signal, transport and
durable I/O. There is no executable default in tests; real effects are
selected only by an explicit later `--execute` path following the release
gates. The worker entry is `worker_once(*, binding, clock, observe_identity,
authorize_call, http_call) -> raw_free_summary`. The worker alone constructs
the fixed six-field request, render, token payloads and response; no raw
request, rendered text, token IDs, completion, environment or traceback-local
data may cross parent IPC or enter a public receipt. The worker cannot call
the old fake adapter because its five-second clock is not the live clock.

Parent, worker and durability helper exchange bounded (at most 4096 bytes)
length-prefixed canonical UTF-8 JSON frames. Unknown/duplicate fields,
noncanonical bytes, malformed length, stale sequence, wrong run/worker
witness, missing ACK or timeout are terminal. Grants bind exactly:
`run_id`, initial worker `(pid, ppid, start_sec, start_usec)`, operation
ordinal 1..7, target role and private loopback port, method, path, canonical
payload SHA-256 (or fixed null for GET), monotonic expiry, and a random
one-use nonce. The transport re-canonicalizes its *own* pending payload,
checks the bound grant immediately before send and atomically consumes it.
Only then may its sole private loopback HTTP client send. Any replay,
out-of-order, missing, mismatched or expired grant gives **zero HTTP**.

The seven external worker operations are immutable: daemon `GET
/api/version`, `GET /api/tags`, `POST /api/show`; daemon `POST
/v1/chat/completions` with `_debug_render_only`; runner `POST /tokenize`
with `add_special=false,parse_special=true`; runner `POST /tokenize` with
`add_special=false` and `parse_special` absent; daemon `POST
/v1/chat/completions` normal, with only client `timeout` and debug flag
removed. Six identity observations remain OS/filesystem-only:
`before_metadata`, `after_render`, `before_tokenize_true`,
`before_tokenize_default`, `before_completion`, `after_completion`.
Daemon-to-runner internal RPCs are **not** counted in seven external calls;
their generation count remains `unknown` without separate same-run evidence.

For each ordinal, a dedicated supervised I/O helper commits a 0600
`O_EXCL` allowlisted journal state (file fsync, atomic replace, containing
directory fsync) **before** parent ACK. Operation 7 additionally commits
`completion_attempt_spent=1` before its ACK. An ACK is never issued on a
missing, blocked or failed durability reply. Journal states are monotonic;
neither crash nor lost response refunds an ordinal or completion attempt.
Before operation 1, the helper must create an exclusive 0600 **zero-count**
journal, fsync that file and its containing directory, and receive a bounded
ACK. The 0700 run directory must be new and empty; any existing journal,
intent, receipt or run identifier is a terminal refusal, **not** a resume or
second-use path. A crashed run keeps every reservation and spent-completion
bit; this operator never issues a new grant against that run. A lost parent
or worker ACK after the durability barrier is also spent, not refundable.
The receipt separately records `reserved`, `granted`, `worker_issued` and
`on_wire=yes/no/unknown`; it must not infer wire delivery or a runner
generation from an attempt reservation. No retry, fallback or second
completion path exists.
`on_wire=yes` requires a bounded transport success observation; `no` requires
proof that the operation had **no grant** and its worker was reaped without
an authorized send. Once a grant may have reached a worker, ACK loss,
transport uncertainty or worker death is `unknown`, never `no` by default.

Transport accepts only exact bound `127.0.0.1` daemon/runner URLs and
ordinal-method-path pairs. Disable proxies (`ProxyHandler({})`), redirects
and cloud routing; require byte-equal effective URL and HTTP 200. Canonical
request body <=256 KiB; bounded response read <=2 MiB+1 and reject excess;
per-call timeout <= remaining deadline. No identity/version/warm-up call
outside the seven. Raw HTTP errors and daemon logs remain in private 0600
files; the public exception and receipt contain fixed codes only.

## Nonblocking clock and physical cleanup

`T0` is recorded immediately before pre-run source/model identity checks
and daemon startup, after selecting but not re-cloning the private model.
Preparation before T0 is separately measured. The parent is a nonblocking
watchdog: full SHA (including `_model_store`), daemon spawn/readiness, OS
observers, lsof/ps, journal and receipt fsync/replace execute only in
supervised helpers, never synchronously on its event loop. Parent polls IPC
and child exit with no unbounded wait; fake blocked hash/observer/fsync must
still cause work-stop and a witness-gated **cleanup attempt** by its
deadline. Every helper must have its initial raw-generation/PGID/argv/binary/
parent witness captured and ACKed before it enters any blocking callback;
helper launch/witness capture is itself bounded and cannot hold the parent
event loop. If that capture cannot finish, do not start the callback or
claim an owned process. If work completes or fails earlier, enter the same
cleanup immediately rather than waiting to 80.

The **latest** schedule, measured from T0, is:

| Monotonic interval | Required action |
|---|---|
| [0,80) s | Identity/readiness/at most seven granted HTTP; abort new work before 80.000. |
| [80,82) s | Revoke future grants. Concurrent bounded fresh witness checks; signal exact initial runner, daemon, worker, then work helpers with TERM, in that priority, without serial grace waits. |
| [82,85) s | Nonblocking poll/reap grace and record each exit. |
| [85,87) s | Recheck any still-live *initial* witness, then exact-PID KILL in the same priority. |
| [87,89) s | Nonblocking reap/exit proof, both private listeners vacant, original shared 11434 PID/raw/listener unchanged. |
| [89,90) s | A reserved, already-witnessed receipt helper commits one 0600 raw-free receipt with file+directory fsync, then itself exits/reaps. |

Keep the receipt helper alive through 80–89; “remaining work helpers” does
not include it. If an earlier receipt is necessary, use the same bounded
helper and still prove exit by 90. Signal only a PID whose *initial* raw
generation, PGID, argv/binary, parent and listener witness were captured
when it became visible, and whose corresponding fresh witness is identical
immediately before TERM or KILL. Use `raw_generation()` bracketing
`os.getpgid(pid)`; `raw_generation()` itself lacks PGID. The bounded signal
helper must execute fresh witness acquisition, second raw-generation check
and `os.kill(initial_pid, signal)` in one helper transaction without a
parent IPC check-then-signal gap; it returns only a fixed result code. A
blocked fresh-witness check or any change **detected through the final
pre-signal check** must cause no signal and `physical_stop_unproven`. Fake
controls must block this *cleanup* observer as well as the ordinary work
observer, and inject PID change at that final check. `os.kill` is PID-only:
the remaining final-check→syscall reuse race is **not** eliminated by a
same-helper transaction. It remains a cooperative-local residual risk,
not a generation-qualified OS signal guarantee; a later live release must
review it explicitly. No `killpg`.
Unknown/newly discovered child or changed witness is never retroactively
authorized for signaling. Signal/observation failures, still-owned ports,
changed 11434, delayed receipt or any action after 90 yield FAIL with
`physical_stop_unproven` and/or `cleanup_review_required`; later cleanup
cannot be called a <=90s pass. This is a **conditional, cooperative local
stop claim**, not protection against a malicious host or OS stall.

If receipt fsync/replace blocks or fails, return nonzero and fixed
`receipt_unavailable_review_required` where possible; never claim a durable
receipt or continue generation. Parent must still attempt identity-safe
cleanup. All child stdout/stderr remain private 0600; no traceback locals
are captured. Receipt allowlist: fixed status/failure code, request/render/
source/identity hashes and lengths, phase timestamps, six observation and
seven grant/send counts, spent/on-wire fields, per-PID cleanup codes, port
proof, usage/count/delta if valid, SHA call count/logical bytes/CPU/wall,
and permanently false `b_upper_bound_proven`/`b_send_authorized`.

## Source-conditioned token interpretation (not a fake boolean)

The installed daemon/runner SHA and exact binary/argv, private GGUF SHA,
template/system/manifest SHA, tagged source revision and `VERSION=0.34.4`
must be bound in the run receipt. This is cooperative source/binary
conformance evidence, **not** a reproducible-build or code-signing proof.
Before interpreting delta, all of these predicates must be true on the
*same* private daemon/runner; otherwise `REVIEW_REQUIRED`:

1. Confirm the Go-rendered chat branch, not native `r.Chat`: the frozen
   model's no-renderer/no-native-chat criteria and exact `--no-jinja
   --chat-template chatml` runner argv; both render-only and normal request
   use the same immutable six-field source and model state. Ollama v0.34.4
   `server/routes.go` returns the debug render *after* prompt rendering but
   before `r.Completion`; the debug call may tokenize internally and is
   zero generation, **not** zero internal runner HTTP.
2. `server/prompt.go` may prune old messages before render. The fixed
   request has exactly system+latest user; assert the render contains both
   exact messages in order and the frozen model has no extra prepended
   messages/unknown branch. The read-only shared 487-byte config blob SHA
   `2f15b321...9ae419d` currently has null renderer/parser/messages and
   the frozen manifest has no message layer; these are historical source
   observations, **not** substitutes for private same-run validation. If
   message retention cannot be proved, do not
   claim untruncated *input* even if wrapper truncation is ruled out.
3. `leadingBOSForModel` on the selected branch and GGUF metadata must be
   reconciled. `llm/llama_server.go` strips `LeadingBOS` or `<bos>` only
   when `tokenizerAddsBOS()` is true (lfm2/gemma4 special cases or GGUF
   `tokenizer.ggml.add_bos_token`). Bind same-run GGUF `pre=qwen2`,
   `model=gpt2`, `add_bos_token=false` and the rendered prefix; record the
   derived *source-conditioned* BOS decision, not a callback's boolean.
4. Parse exactly one `-c` and one `-np` from the current runner argv,
   positive integers with `-c % -np == 0`, then set
   `effective_NumCtx=-c/-np`. In tagged v0.34.4
   `llm/llama_server.go`, `NewLlamaServer` places the same `opts` in both
   `llamaServerLaunchConfig.opts` and `llamaServerRunner.options`;
   `startLlamaServer` builds `-c=launch.opts.NumCtx * launch.numParallel`
   and `-np=launch.numParallel`; `completionPromptForRequest` reads
   `s.options.NumCtx`. This *source* derivation is valid for the observed
   normal request only if the same-run daemon model/request/default option
   inputs, launch branch, exact runner argv and PID/binary/model identity
   agree. Reconstruct and record the effective request `NumCtx` from the
   frozen model/options and bound daemon defaults; require it equals
   `-c/-np`, otherwise `REVIEW_REQUIRED` **before** operation 7. Bind the
   same PID/raw generation/PGID, parent, binary/GGUF and listener before
   both tokenizers and completion. Do not substitute trained
   `qwen2.context_length=32768` or an old runner.
5. In v0.34.4 `completionPromptForRequest`, after the BOS step, the
   unchanged-string branch fires if Go `len(prompt) < options.NumCtx`.
   Go string length is **UTF-8 bytes**. Therefore require
   `len(rendered.encode('utf-8')) < effective_NumCtx` as the clean
   source-conditioned no-wrapper-truncation predicate. Merely requiring
   `len(token_ids) < NumCtx` is insufficient when rendered bytes >=
   NumCtx. If the branch, context, media or normal request differs, report
   uncertainty; absence of a daemon truncation warning is not proof.
6. The two runner `/tokenize` token-ID lists must be byte-for-byte equal,
   nonempty and shorter than effective NumCtx. v0.34.4's Go `Tokenize`
   wrapper sends `add_special=false` with `parse_special` omitted; the
   `parse_special=true` list is only an empirical cross-check. `usage` must
   contain exact nonnegative integer prompt/completion/total with
   `total=prompt+completion`. The tagged runner's prompt count includes
   cached+new prompt tokens and OpenAI maps that metric to `prompt_tokens`;
   equal delta is *one same-run observation*, not proof of hidden internal
   token IDs, cache state or a universal B bound.

Tagged primary source for these predicates:
`https://github.com/ollama/ollama/blob/v0.34.4/server/routes.go`,
`server/prompt.go`, `llm/llama_server.go`, `openai/openai.go`, and
`middleware/openai.go` at the same tag. If a source predicate cannot be
matched to the installed binary/run, do **not** grant operation 7. All
then-knowable predicates above (Go render and complete ordered messages,
source/model/runner identity, BOS decision, request-to-runner NumCtx,
rendered UTF-8 byte threshold, equal token lists and pre-completion
identity) are mandatory before the single completion grant. Afterward,
revalidate the unchanged model/runner/branch and exact usage before
interpreting delta; failure remains `REVIEW_REQUIRED`, never an attempt
refund or a tuned expected margin.

## Fake tests, resource cap and release decision

### Prospective fake seven-operation process protocol amendment (2026-10-26)

Status: **independently reviewed GO only for fake-only source/tests; NO-GO
real HTTP/model/process, Safari or B Send.** Two read-only design reviews
accepted this prospective protocol; neither reviewed implemented code or
authorized a live run. This amendment preserves every earlier failure,
data, resource and release gate above. It addresses an implementation
ambiguity exposed after the fake P+D/W/R op1 and receipt slices: the phrase
"for each ordinal, a dedicated supervised I/O helper commits" does not say
whether the helper must be a new PID per ordinal. Choosing one resident D is
an explicit prospective **fake-only override of helper cardinality**, not a
silent reinterpretation of that phrase. Reopening the journal in
seven new PIDs would add a new cross-process resume/lease protocol not
covered by this freeze. The proposed design is **one initially
witnessed, separate durability-only D process per one-use attempt**, alive
through operations 1..7, with an individually committed, fsynced, readback
and ACKed transition for each ordinal. D never sends HTTP, never reopens a
crashed run, and exits or is witnessed-stopped after the first terminal
failure. A self-alarm or child exit alone is not a witnessed stop; only the
existing signal-helper transaction and matching waitpid status may prove it.
A missing proof or D death is terminal; no new D or grant is issued
against that run. The existing journal still durably spends ordinal 7 before
its grant ACK. Independent design review must accept this amendment
before implementation; otherwise use distinct per-ordinal helpers only
after a separate prospective safe-reopen design.

The single next fake-only variable is the **process-backed seven-operation
grant/issue/result loop**, reusing the existing `worker_once()` behavior in
initially witnessed W. W alone builds the frozen request, rendered prompt,
token payloads and raw fake responses. The parent receives only bounded
canonical specs, proofs and a raw-free final summary. No change to frozen
question, score, source predicates, model parameters or existing in-process
worker contract is allowed. The old five-second `compare_non_b_parity()`
callback path is not the process worker.

For each ordinal, the planned order is W request/spec → P/D durable reserve
and readback proof → P/W grant → W enters its one-use local transport gate,
re-canonicalizes its *own* payload and exact URL/role/port/method/path/SHA/
expiry/worker witness/nonce, and consumes the nonce → W/P **issue-entry**
proof → P/D durable `worker_issued` proof → P/W issue ACK → W's sole injected
fake callback → W fixed bounded result evidence → P/D durable `on_wire`
update only after success → P/W result ACK. `worker_issued` means a
durably observed W **gate-entry/attempt**, not a parent-issued permission
and not proof that a byte reached the wire. If W dies after issue ACK but
before its fake callback, `worker_issued=1` and `on_wire=unknown` are both
honest. If it dies before issue-entry proof, `worker_issued=0` is only a
lower bound and never proves no send after a grant. A fake success is
labeled fake and never establishes real HTTP wire delivery. Any lost,
failed or uncertain fake callback, issue/result/`on_wire` ACK, or D/W crash
terminates the whole run with no next ordinal, no retry and no refund.
Only validated success plus all mandatory durable proofs/ACKs allows the
next ordinal.
`worker_once()` must run its existing six OS-only observation order and
source/BOS/NumCtx/rendered-byte/token checks **before** requesting operation
7. The final W summary needs exact seven-call/six-observation counts and
normal W exit; D's final canonical disk proof, D exit, D/W cleanup and the
existing prewitnessed R/S_R receipt gate remain separately required.

Child-to-parent grant-affecting replies use **per-ordinal one-shot pipes**:
one bounded canonical frame plus EOF before parent advances. This closes
the delayed duplicate/trailing-frame window on those edges. Parent-to-D/W
commands may use separately bounded persistent pipes only if an explicit
phase/ordinal/sequence state machine rejects stale/duplicate frames *when
received*, before any additional side effect; final EOF is required before
positive fake-run conclusion. Such a stream cannot prove that no future
delayed duplicate will arrive before the next grant and must not be used to
make that claim. A persistent stream without the state machine cannot be
called equivalent to the one-shot proof. Every forked child must close all
unowned inherited pipe ends before work, or EOF is not proof. Pipe layout
must be counted against
the observed macOS soft FD limit
(currently 256); if all required ends cannot be reserved before any work GO,
fail closed rather than silently dropping an EOF or witness barrier.
After operation 7, P closes both command writers; D and W must consume and
validate EOF **before** sending their final proof/summary and exiting
normally. A trailing or late frame is terminal, not ignored after a
positive summary. The parent must verify these exits and final child-to-P
one-shot frame+EOF before requesting R's final receipt.

Prospective fake acceptance includes 7/7 ordered unique reservations,
issue-entry proofs and injected sends, six OS-only observations, op7 spent
before ACK, R receipt counts, and targeted lost/duplicate/wrong
run/worker/nonce/ordinal/target role/method/port/path/payload/expiry,
blocked stage, crash,
source-pre-op7 and raw-canary negative controls. The process-backed fake
result must remain `fake_*`, `physical_stop_unproven=true`,
`full_gate_pass=false`; it does **not** establish private-port/11434
vacancy, real transport/proxy isolation, installed source/model identity,
T0+90 cleanup or provider parity. Those retain the unchanged release gates
below. A small red test and affected regressions precede any fake source
implementation; an independent patch review follows it.

### Prospective fake port/11434 witness amendment (2026-10-26)

Status: **design-reviewed for a fake-only implementation, not a live release**.
The seven-operation process loop is retained as the v1 historical partial
result. Its URL/grant checks do not prove listener vacancy or that the user's
shared 11434 listener was unchanged. This amendment changes only that
missing fake OS-witness gate; it does not change the seven requests, source
predicates, model, question, gold, score or T0+90 live claim.

Add an independent, initially witnessed, OS-only port-observer child `O` and
its separately initially witnessed exact-PID signal child `S_O`. Keep `R`
separate and available to persist a raw-free failure receipt when `O` blocks.
Reserve five one-shot O pipes (initial, pre command/proof, final
command/proof) and five S_O pipes before any work GO. The complete fake
layout becomes 123 pipes / 246 endpoints; require unique descriptors and
`max(fd) < RLIMIT_NOFILE`, otherwise fail closed before work. Every forked
child closes unowned inherited ends. A blocked initial witness starts no
port callback; a blocked pre/final callback cannot block the parent event
loop or prevent an attempted witnessed O cleanup and independent R receipt.

Order: durable D zero ACK -> R zero-journal preflight ACK -> O and S_O
initial identity ACKs -> O pre command and
bounded canonical proof that the bound daemon private port is vacant, with
an explicit shared-11434 state/fingerprint digest -> W GO. The runner port
is **not** invented at preflight: it is first available in W's validated
ordinal-5 runner request and must agree with ordinal 6. This W spec is only
a port candidate, not independent runner PID/identity proof. After D/W
cleanup, O receives that candidate and makes a fresh final OS-only
observation: both bound private ports vacant and the shared-11434
state/fingerprint byte-identical to pre. Missing candidate, occupied port,
changed/unknown shared state, malformed/late/duplicate proof, O crash or
blocked callback is FAIL/unknown, never a positive vacancy claim. A v2
positive run requires O and S_O normal exits as well as the pre/post verdict;
the S_O witnessed-stop path is failure cleanup only. R remains available
to write the failure receipt after a blocked pre/final observation. No
signal may target the shared 11434 owner.

The injected fake port observer returns a strict phase-tagged, bounded
allowlist: `schema=fake_port_snapshot_v1`, pre/post phase, bound numeric
daemon port, `runner_port=null`/`runner_vacant=null` in pre, bound numeric
runner port and vacancy boolean in post, and shared 11434 state
(`vacant` with null fingerprint, or `listener` with a deterministic
OS-fingerprint SHA). A real `listener` fingerprint must cover at least the
observed owner PID, raw process generation and exact 11434 listener
endpoint/identity in a canonical OS observation; a caller-chosen arbitrary
digest is not live proof. Injected fake snapshots only test the contract.
An unknown state or malformed fingerprint fails. O
commands/proofs and public projection may expose only those two bound
numeric ports plus fixed booleans/codes/hashes, never raw lsof output,
callback strings, unrelated addresses, traceback, request or model content.
The v2 fake path is explicit opt-in; absent a `port_observe` callback the
original v1 result/receipt/status and tests remain unchanged, not silently
upgraded. Positive v2 fake results and R receipts use **v2 schemas**, with pre/post proof
hashes, vacancy/unchanged verdicts and O/S_O cleanup status. v1 schemas and
their old evidence remain unchanged. Even v2 positive keeps
`physical_stop_unproven=true`, `full_gate_pass=false`, and
`b_send_authorized=false`; fake injected observations do not establish a
real OS port proof, real HTTP, T0+90, installed identity or live authority.

Before source edits, add a red v2 contract test. Acceptance requires the
ordered positive gate and negative controls for pre occupied/unknown,
post occupied daemon or runner, 11434 drift, wrong runner port, pre/final
observer block or crash, O/S_O abnormal exit, duplicate/partial/stale IPC,
FD cap and raw canary. Preserve the previous 7/7 v1 regression, run the
affected suite and independent read-only patch review. No real daemon,
runner, HTTP, Safari or B Send is authorized by this amendment.

### Prospective W-owned fake transport amendment (2026-10-27)

Status: **independently design-reviewed GO only for v3 fake-only source/tests;
no real HTTP/model/daemon/runner, Safari or B Send authority**. Patch review,
committed-source audit and separate live release remain pending. The
committed v1/v2 fake paths already reject
the *injected callback's claims* of proxy use, redirect, wrong effective URL,
non-200 and overlong response. They do not construct a no-proxy/no-redirect
client, and lower-layer tests do not establish the supervised W→D/R failure
receipt for each transport fault. This amendment changes only that fake
transport contract; the seven requests, source conditions, score, model,
question, port witness and T0+90 claim remain fixed.

Add one explicit opt-in v3 fake path with a W-owned strict loopback request
constructor and an injected fake opener factory. V3 requires the v2
`port_observe` gate; it is mutually exclusive with the old `fake_http`
callback. The in-tree fake entry has no implicit real opener or direct socket
operation; an arbitrary injected callable is a trusted test effect, and
socket fail-sentinels establish zero sockets for the executed tests. Before
each fake exchange, W re-canonicalizes its own pending body,
checks <=256 KiB and the grant SHA, exact bound
`http://127.0.0.1:{private_port}{frozen_path}`, role/method/ordinal/worker/
nonce/expiry, then constructs `urllib.request.Request` and a client with
`ProxyHandler({})` plus a redirect-denying handler. W checks that the factory
received the explicit empty proxy handler, then validates the **returned
opener's installed handler inventory** before and after the fake callback:
zero active `ProxyHandler`/`proxy_open` handlers, exactly the expected
redirect-denying handler, and no competing redirect handler. Python's
`build_opener` does not install an empty `ProxyHandler` in `.handlers`, so
requiring one would be incorrect. Checking only the factory arguments is
insufficient because a fake factory may ignore them. The supplied fake
opener is invoked only after D has durably ACKed W's issue-entry; timeout is
positive and at most the remaining work/grant time. W checks response
status 200, byte-equal effective URL and bytes type. It repeatedly reads
at most the remaining allowance until EOF or cumulative bytes exceed
2 MiB, never requesting or retaining more than 2 MiB + 1; a short non-EOF
chunk is not mistaken for the end of a bounded response. A blocked read
remains subject to W's supervised hard deadline. No callback self-reported
`proxy_used=false` may substitute for checking the constructed handlers.
All exceptions and callback stdout/stderr are contained; public output and
R receipt use fixed codes/hashes only. W's existing one-use nonce/spend and
on-wire-unknown rules remain unchanged.

The v3 result, W summary and R 0600 receipt must use distinct strict v3
schemas. They bind an ordered SHA of the seven validated request/result
contracts and a seven-call fake transport policy count; parent checks that
SHA against the request/result proof frames it actually received before
setting a v3 `transport_gate_proven` subverdict. This subverdict means
**only** that W's seven fake transport contracts have an ordered proof; it
is not overall run success and may stay true if R subsequently fails.
Positive v3 requires this subverdict, the v2 port gate, normal D/W/O/S_*
exits and durable R receipt. Any W exchange/proof mismatch, W block/crash
or raw transport content is terminal with `transport_gate_proven=false` and
a raw-free failure receipt where R is available. R's own later receipt/exit
failure changes overall status and `receipt_durable_proven`, not an already
established W-only subverdict; the receipt cannot predict its own final
exit. Existing v1/v2 schemas, default behavior and committed result
remain unchanged. No additional pipes or helper PIDs are allowed: the fake
resource cap remains 123 pipes/246 reserved endpoints and eight children;
the extra opener/request are W-local. FD exhaustion fails closed.

Before source edits: preserve a before trace showing current callback-only
checks, add red v3 positive and failure tests, then implement. Tests inject
only fake openers/responses and fail-sentinel all socket/connect and real
opener paths: **zero actual HTTP/model/provider calls**. Controls cover
empty proxy-handler map, redirect denial, exact request bytes and timeout;
wrong scheme/host/port/path/method/body SHA/nonce before opener call;
302/redirect, changed effective URL, installed-handler policy tamper before
or after exchange, non-200,
oversize response, blocked/raising exchange, raw printed canary, missing
or corrupt ordered summary, and R failure-receipt durability. Preserve v1
and v2 positives, run focused/affected regression and independent read-only
patch review before scoped commit/push/PR exact-head check.

Passing v3 would prove only the construction and fail-closed behavior of a
**fake injected** client seam. A fake opener can ignore policy, and these
tests do not prove real proxy bypass, real redirect behavior, network bytes,
installed model/source identity, physical cleanup by 90 seconds, Safari or
B Send. Public `supervise_once()` remains fail-closed; a separately reviewed
live opener, actual private-loopback observation and all other exact-freeze
gates are still mandatory before one real attempt.

### Prospective O-owned synthetic pre-hash amendment (2026-10-27)

Status: **independently design-reviewed GO only for v4 fake-only red tests,
source and tests; NO-GO for live HTTP/model/daemon/runner, Safari or B Send**.
Patch review, committed-source audit and separate live-release decision remain
pending. At committed `2bc453a`, v3 takes a
pre-supplied binding with hash-shaped strings but never reads a source/model
file. The exact live freeze requires supervised full SHA before daemon
startup, one pre and one post `_model_store` validation, and blocked-hash
watchdog controls. V4 changes one fake-only variable: a small, real
filesystem SHA-256 must be computed by a supervised child and verified by P
**before W_GO**. It does not claim the actual 4.4 GiB model-store calls,
source/binary conformance, true daemon-startup order or T0+90 stop.

The initially reviewed D is explicitly *durability-only* and must remain so.
Do not hash in D before `d_zero`: R would not complete its zero-journal
preflight, and a blocked hash would lose the otherwise available failure
receipt. Instead, v4 explicitly extends the existing O from fake OS-only
port observer to fake OS/filesystem evidence helper. Preserve the order
`D_ZERO -> R preflight ACK -> O initial witness -> S_O initial witness ->
O synthetic hash -> O existing pre-port observation -> P combined proof ->
W_GO`. The synthetic hash is not daemon startup; no daemon/runner is launched.
O and S_O are already in the v2/v3 eight-child graph. Reuse `o_pre` and
`o_pre_proof`, with exactly one v4 composite pre-proof frame and EOF; do not
add pipes or processes. The frozen peak remains 123 reserved pipes / 246 IPC
endpoints, subject to explicit FD-cap tests. O opens at most two transient
read-only FDs (fixture directory then leaf) after closing unowned ends and
closes both before the port observer callback. Record O's actual peak open
FDs separately from the 246 reserved IPC endpoints; do not silently raise
the macOS soft limit. O's hard deadline and S_O exact-witness cleanup
remain active during the hash; a self alarm alone is not witnessed stop.

V4 is a separate explicit opt-in on top of v3 (`fake_opener_factory` and
`port_observe` remain required; old `fake_http` is forbidden). The one
positive fixture is exactly ASCII `URUHA_P4B_FAKE_HASH_V4\n` (23 bytes),
pre-implementation SHA-256
`2d2078a1d31c931402d626a1321b74731099a9144b32d6aa37e6718c968e95a7`.
It is synthetic developer data, never a model or holdout. **No caller may
select a fixture file or expected digest.** Before reserving IPC endpoints,
P creates a unique 0700 directory with `tempfile.mkdtemp` under the
canonical local OS temp base, rejects a base inside the repository or
attempt `run_dir`, and creates only the fixed direct-child
`synthetic-prehash-v4.bin` with `O_EXCL|O_NOFOLLOW`, 0600, and exactly the
literal 23 bytes above. It fsyncs and closes this tiny fixture before the
attempt; it never reads a caller-provided model or production file. The
directory/path is absolute/canonical, neither leaf nor ancestor is a
symlink, and the leaf is same-UID, single-link regular. P records directory
and file `(st_dev, st_ino, st_uid, st_mode, st_nlink, st_size)` metadata
and the independent **literal** expected SHA/count, without hashing file
contents itself. If the canonical OS temp base cannot be shown disjoint
from the repository and run directory, fail before fixture creation. This
is a cooperative synthetic fixture confinement check, not a general
production-data allowlist. Retain the operator-created fixture until O/S_O
are reaped or safely proven stopped; do not delete it while they might
still access it. In tests, a v4-only injected hook runs in O at an explicit
`before_open` or `before_first_read` seam; it may stall, raise or mutate
**only this operator-owned fixture**, never return bytes/digest/success,
and its return value is ignored. The read hook fires once after safe open
and identity checks. Invalid v4 configuration is rejected before journal/
fork, without changing v1-v3 defaults. A fixture changed after pinning is
a run failure with an R receipt when R remains available.
No default private model path, real opener, socket or real daemon is added.
O rejects symlinks, hardlinks, wrong owner/mode, nonregular files, changed
path/device/inode, short or overlong read, wrong size, unavailable read and
files above 1 MiB. It opens the pinned fixture directory with no-follow/
directory/close-on-exec flags, then opens the fixed leaf relative to that
directory FD using `O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`. It matches
the pinned directory and leaf identity against `lstat`/`fstat` before
reading, rechecks path and FDs afterward, then closes both FDs before the
port callback. It reads in at most
64 KiB chunks, hashes the bytes actually read, and returns only digest and
exact count in IPC. This is a cooperative local file check, not protection
against every path race or malicious filesystem. Neither path nor file bytes may enter P's result,
R receipt, journal, public stdout/stderr or Web. P compares O's digest and
count to the independently pinned expectation, and checks the unchanged
port proof, canonical frame/EOF and initial witness before W_GO. A returned
digest alone is never source provenance or adversarial attestation.

Use strict distinct v4 result and R 0600 receipt schemas while retaining the
existing `fake_seven_process_ipc_v1` outer frame. On the existing `o_pre`
edge, v4 phase `o_pre_hash_port` has exactly the standard run/seq=1/O-witness
envelope plus `daemon_port`; path and pinned identity are inherited by O at
fork, never sent in IPC. On the existing `o_pre_proof` edge, v4 phase
`o_pre_hash_port_proof` has exactly the same envelope plus the six prior
pre-port proof fields (`port_sha256`, `daemon_port`, `daemon_vacant`,
`runner_port=null`, `runner_vacant=null`, `shared_11434_sha256`) and
`prehash_sha256` (lowercase 64 hex) plus `prehash_logical_bytes` (exact
non-bool int 0..1 MiB). Canonical frame <=4096 bytes and EOF are mandatory;
extra/missing/duplicated/trailing fields, wrong phase/seq/run/witness and
malformed digest/count are terminal at this barrier. O remains alive for the
later final port observation; its eventual abnormal exit makes the overall
v4 run unproven, without retroactively inventing a different hash result. A v2/v3
`o_pre_proof` never satisfies v4, and a v4 proof never satisfies v2/v3.
O isolates both descriptor-level and Python-stream stdout/stderr before
any injected hook or observer callback; raw canary never reaches parent,
receipt or test capture.

The v4 result/receipt extend v3 with exactly `prehash_gate_proven` (bool),
`prehash_sha256` (pinned SHA only after the *entire* SHA/count pair matches,
else null), `prehash_logical_bytes` (pinned count only after that same match,
else null), and `pre_stage_failure_code` (fixed enum `none`,
`pre_stage_unavailable`, `pre_stage_mismatch`, `port_pre_not_vacant`,
`port_helper_initial_unavailable`, `signal_helper_initial_unavailable`).
No raw path/bytes or test marker is allowed. V1/v2/v3 schemas and default
bytes remain unchanged. P first validates the exact frame and EOF; only
then checks the hash/count against independent frozen literals and marks
`prehash_gate_proven=true` with matching SHA/count. Thus `true` requires
both non-null matching values, and `false` requires both null; it may remain
true if a **later** port/W/R failure occurs. P then checks unchanged
daemon-port/vacancy/shared-11434 preproof before W_GO. A valid hash with
`daemon_vacant=false` keeps the prehash subverdict but uses existing
`port_pre_not_vacant`; a well-formed wrong hash/count or wrong expected
port uses `pre_stage_mismatch`. A missing/malformed/duplicate/trailing
composite proof cannot distinguish hash stall, port-observer stall or lost
IPC; use `pre_stage_unavailable`, never `hash_timeout`. No W_GO, grant or
fake HTTP follows any pre-stage failure; D zero-count journal and R's
available raw-free failure receipt are retained. Test-only markers may
attribute an injected block, not public receipt-level cause.

`pre_stage_failure_code` retains the first pre-stage failure. The top-level
`failure_code` reports the dominant final gate **after R preflight has
accepted** in order: unproven R receipt or R exit ->
`receipt_unavailable_review_required`; else an O/S_O initial witness
refusal **before the v4 command** keeps its specific existing initial code;
else unproven O/S_O/D/W cleanup or abnormal S_O exit **after the v4 command**
-> `cleanup_review_required`; else a non-`none` pre-stage code; else the
later existing port-final/W/transport/signal failure code. Initial-refusal
cleanup uncertainty remains
visible in per-PID stop/exit fields and never becomes a pass. Failures before
R preflight retain their prior specific code and never enter v4 hash work.
The per-PID `*_stop` and S_* exit fields
remain separate. A durable R receipt snapshots the state before its own
final exit and cannot predict that exit: its pre-stage fields equal the
parent's validated values, but its top-level status/failure_code may differ
from the final parent result if R then fails. Any such case remains strict
FAIL with `receipt_durable_proven=false`. If O/S_O initial witness fails,
map its specific code into `pre_stage_failure_code` and never call hash or
port observer.
`physical_stop_unproven=true`, `full_gate_pass=false` and
`b_send_authorized=false` remain permanent. V4 must not allow a pass when
O/S_O has not exited normally and R receipt is not durably proven.

Before implementation: add a red integrated v4 test proving no current
hash-before-W_GO path, then use the existing v3 seven-operation path with
one tiny fixture. Positive controls verify the exact digest/count, O hash
before unchanged port observation, seven unique fake requests, six OS-only
worker observations, op7 spent, 0700/0600 artifacts and no extra process or
pipe. Negative controls cover blocked/raising read hook; wrong digest/count;
symlink, replacement and >1 MiB file; missing/corrupt/duplicate/trailing
composite proof; O/S_O initial-witness refusal; blocked cleanup witness or
ineffective signal; raw printed canary; and FD exhaustion. Blocked hash
must leave P bounded, the port observer uncalled, zero grants/HTTP, and a
0600 raw-free R failure receipt if R is available. Preserve v1-v3 tests,
run focused and affected regression, independent patch review, then only
scoped commit/push/PR exact-head check. Test output is synthetic mechanism
evidence; it cannot satisfy real pre/post SHA, actual model/source identity,
readiness, production/Safari or a live release.

Focused fake controls must prove a positive seven unique grants/sends,
six OS-only observations, op7 spent **before** ACK, two private ports
vacant/11434 unchanged, no raw leakage, a durable initial zero-count journal
and 0600 journal/receipt. Negative
matrix: blocked HTTP at every stage; blocked hash/readiness/observer/
journal fsync/replace/receipt helper, including a blocked *cleanup-witness*
observer and blocked initial helper witness; worker/daemon/runner crash;
missing/replayed/wrong run/worker/nonce/ordinal/method/path/port/payload
grant; existing-run refusal, lost ACK/no refund, on-wire unknown after a
possibly delivered grant; op8/second completion;
proxy/redirect/wrong port/oversize;
deadline and spent ACK-loss; raw-generation/PID reuse/PGID change,
runner in separate PGID, PID change at final pre-signal check, unknown
child, TERM ignored, failed KILL or
port/11434 drift; ambiguous `-c/-np`, BOS/branch/truncation, differing
token lists, request-to-runner NumCtx mismatch, known source-predicate
failure before op7, and raw canary in IPC/receipt/log. Each blocked
callback must leave the parent watchdog responsive and preserve a raw-free
failure code; physical cleanup is PASS only with actual exit/port/receipt
proof by 90 seconds, not merely a responsive watchdog.

Cap one real attempt, <=7 **worker-issued external** HTTP, <=1 external
normal completion, <=256 KiB/request, <=2 MiB/response, <=256 output
tokens, T0-to-verified-cleanup-and-receipt <=90s or strict FAIL, zero
retry, zero paid or external-network/cloud calls (private loopback only).
`_model_store()` logically reads
4,683,088,190 bytes each time; freeze exactly one pre and one post
validation (>=9,366,176,380 bytes plus binary hashes). Four model-store
calls (>=18,732,352,760 bytes) are forbidden without a *prior* amendment.
Record actual SHA invocations, logical bytes, CPU/wall and cold-load time;
do not hide clone preparation before T0. No duplicate 4.4 GiB clone,
download, production DB, Web or Safari in this item.

Release order: independent design review of **this** freeze -> fake-only
source/tests -> focused and affected regression -> independent patch/diff
review -> scoped commit/push and PR exact-head check -> read-only live
preflight. Only a separately documented GO after all these gates can
authorize at most one synthetic non-B live attempt. A fake result remains
`fake_*`; a live receipt uses a distinct schema. On any stop/identity/BOS/
truncation uncertainty, leave `REVIEW_REQUIRED`; do not weaken the cap,
add an eighth HTTP, issue a fourth B call or send B in Safari. Even a
live delta zero would not prove B's prompt bound, 20-second Web delivery,
A author judgment, stronger-than-LLM performance or Goal completion.
