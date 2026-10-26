# P4-B non-B parity: exact live-supervisor implementation freeze

Status: **DRAFT for independent design review. NO-GO source edit, real
HTTP/model/process or B Send until the review explicitly accepts this exact
freeze.** The previous prospective design at `352223c` is a design baseline,
not executable authority. This document freezes the next *fake-controlled*
implementation scope; a later separate patch review, committed-source audit
and read-only live preflight are required before at most one synthetic non-B
attempt. It does not change the B question, gold, gate, or formal evidence.

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
The receipt separately records `reserved`, `granted`, `worker_issued` and
`on_wire=yes/no/unknown`; it must not infer wire delivery or a runner
generation from an attempt reservation. No retry, fallback or second
completion path exists.

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
still cause work-stop and cleanup by its deadline. If work completes or
fails earlier, enter the same cleanup immediately rather than waiting to 80.

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
`os.getpgid(pid)`; `raw_generation()` itself lacks PGID. No `killpg`.
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
   `effective_NumCtx=-c/-np`. Bind the same PID/raw generation/PGID,
   parent, binary/GGUF and listener before both tokenizers and completion.
   Do not substitute trained `qwen2.context_length=32768` or an old runner.
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
matched to the installed binary/run, stop before completion if possible;
never use a completed call to tune the expected margin.

## Fake tests, resource cap and release decision

Focused fake controls must prove a positive seven unique grants/sends,
six OS-only observations, op7 spent **before** ACK, two private ports
vacant/11434 unchanged, no raw leakage and 0600 journal/receipt. Negative
matrix: blocked HTTP at every stage; blocked hash/readiness/observer/
journal fsync/replace/receipt helper; worker/daemon/runner crash;
missing/replayed/wrong run/worker/nonce/ordinal/method/path/port/payload
grant; op8/second completion; proxy/redirect/wrong port/oversize;
deadline and spent ACK-loss; raw-generation/PID reuse/PGID change,
runner in separate PGID, unknown child, TERM ignored, failed KILL or
port/11434 drift; ambiguous `-c/-np`, BOS/branch/truncation, differing
token lists and raw canary in IPC/receipt/log. Each blocked callback must
leave the parent watchdog responsive and preserve a raw-free failure code.

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
