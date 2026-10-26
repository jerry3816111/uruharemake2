# P4-B non-B parity: live supervisor/transport prospective freeze

Status: **independently reviewed GO only as a prospective design baseline;
NO-GO for implementation, real HTTP/model/process and B Send**. The first
review found a blocking watchdog/hash and `killpg` boundary; the second
found synchronous journal fsync would also block the watchdog. The revised
design moved blocking work to supervised helpers, removed group signaling
and added durable single-use HTTP grants before both reviews returned
design-only GO. This follows the source/fake contract
at `6d9cfdb` and the prior non-B parity protocol. Its only intended new
capability is one safely attributable synthetic non-B prompt/usage
observation. It is not a new M, not a B token certificate and not product B
Send authority.

## Before, one variable, falsifiable result

Before: `compare_non_b_parity()` is deliberately fake-only, hard-caps its
injected callback clock at five seconds, returns a `fake_*` in-memory receipt
and cannot preserve one-attempt evidence if a callback hangs or its worker
dies. The older zero-turn operator and `probe.probe()` add their own version,
render and probe requests; whole-function reuse would exceed seven HTTP
operations. The old operator's 480-second line is observed, not an
independent watchdog. No actual same-run provider/tokenizer Δ exists yet.

One variable: introduce a separate **real-run operator** around the frozen
synthetic request. The declared test remains Δ = provider `prompt_tokens`
minus both-equal runner tokenizer list length, with H0 Δ=0 only when live
NumCtx/BOS/no-truncation and identity are proved. Nonzero Δ, unavailable
usage or any hard-gate failure is retained negative/`REVIEW_REQUIRED`, not a
retry or changed margin. A one-shot match would support only this synthetic
non-B request on this run; it does not bound B or establish answer quality.

## Staged authority and allowed files

This document alone authorizes **no implementation or real run**. After
independent design review, a separate implementation freeze must fix API,
allowed files and fake controls before edits. Candidate narrow files are a
new `p4_b_non_b_parity_live_operator.py`, its fake-only test, this freeze,
one result note and `CURRENT_TASK.md`. A narrow extraction of shared pure
validation from `p4_b_non_b_usage_parity.py` and its tests is allowed **only
if separately shown necessary and behavior-equivalent**; preserve its 5s
fake entry, status, 92 focused tests and false B authority. Do not change
product boot/gate/ledger/Brain/Web, compact planner, B question/gold,
holdout, private formal memory or original dirty checkout. Never wrap
`p4_b_private_zero_turn_operator.run_once()`, `probe.probe()` or
`probe._http_json()` as the seven-call experiment.

Release sequence: design review → exact implementation freeze and fake
negative controls → independent patch review and scoped committed source →
read-only live preflight → **at most one** synthetic non-B real-run attempt.
Any earlier FAIL stops this sequence. The same exposed fixture is not
renamed holdout; the B gate remains closed throughout.

## Proposed real-run boundary

An independent parent supervisor owns a new 0700 run directory, one-attempt
and seven-call durable journal, 0600 raw-free result/failure receipt, private
daemon lifecycle and monotonic watchdog. The parent runs a nonblocking
deadline event loop: full model/binary SHA, daemon spawn/readiness, HTTP,
OS probes, and journal/receipt fsync or replace must run in supervised
worker/helper processes with bounded IPC replies. The parent cannot
synchronously block on a hash, network or disk operation and still claim
an independent 90-second stop; blocked-hash, blocked-observer and
blocked-fsync fake controls must prove that it does not.
A single request worker derives the actual
six-field request with `fixed_transformed_request()` and performs the seven
operations through one injected private transport. No prompt, rendered text,
token IDs or completion text is sent to the parent IPC or persisted. Parent
and worker are distinct processes; a blocked worker cannot block watchdog
observations. The exact T0 is immediately before pre-run source/model
identity checks and daemon startup using an already selected private clone;
the observation/cleanup deadline is T0+90s. Any clone preparation before
T0 is separately measured and reported, never folded into a claim of
≤90s total setup. Reserve a prospective work stop at T0+80s and the last
10s for cleanup/verification; a missed deadline is FAIL even if later
cleanup succeeds.

Proposed API, subject to implementation review:

- `supervise_once(*, run_dir, model_root, clock, spawn_worker, observe_os,
  active_limit_s=90) -> raw_free_receipt`: no real default for tests; the
  eventual explicit one-use operator binds committed source/binaries/model,
  owns all child PID witnesses and directs the supervised I/O helper to
  durably write success or failure receipts.
- `worker_once(*, daemon_binding, observe_identity, http_call,
  deadline, authorize_call) -> result`: same seven steps and six named
  OS-only observations as the fake contract, but a distinct **live** schema,
  not a fake PASS relabel. It constructs the fixed request **inside the
  worker**; neither request nor response crosses parent IPC. It sends a
  fixed operation number, method/path and canonical payload SHA to
  parent before each HTTP and waits for a single-use bound grant. A
  supervised I/O helper durably journals the call before parent ACK; for
  operation 7 it first fsyncs `completion_attempt_spent=1`. A missing,
  reused or mismatched grant must be rejected by the transport with zero
  HTTP. A blocked durability helper is never granted an ACK, while the
  parent watchdog remains free to clean up.
  This records an irrevocable **attempt reservation**, not proof that the
  HTTP bytes reached a runner. A crash, timeout, lost response or malformed
  usage cannot refund the one attempt; report actual on-wire completion as
  `yes/no/unknown` from separate evidence. No second completion or retry
  path exists.
- `PrivateLoopbackTransport(method,url,payload,remaining) -> exact six-key
  observation`: only the bound 127.0.0.1 daemon/runner ports and seven
  ordered method/path pairs with a matching unconsumed parent grant;
  `ProxyHandler({})`, no redirects, effective URL
  byte-equal, HTTP 200, request canonical ≤256 KiB, response read at most
  2 MiB+1, timeout no greater than remaining deadline, no hidden probe,
  retry or cloud route. The worker may not use another HTTP client.

OS-only listener readiness precedes operation 1; the single `/api/version`
is also the version check. There is no extra ready-version GET. Before the
first request, bind exact HEAD/live source, daemon binary/argv/raw generation,
private model clone/manifest/blobs, loopback listener, no proxy/cloud env
and shared 11434 witness. Render-only may lazy-load the runner. Parent
discovers/captures the runner during that phase; before either tokenizer
and completion, both parent and worker must agree on the same run-bound
runner PID/raw generation, parent, argv/binary/GGUF, listener and port.
Six worker observations remain OS/filesystem-only; no identity HTTP may
silently become an eighth call. After completion and before receipt, repeat
identity/model checks and verify private ports vacant after planned stop.

The real observer must derive `context_total=-c` and `parallel=-np` from
**this** runner argv, require integral `NumCtx=context_total//parallel`,
and verify both tokenizer ID lists are identical with length strictly below
NumCtx. `add_bos_token=false` must be tied to the frozen GGUF metadata and
the actual rendered/runner BOS branch; `leading_bos=""` and
`truncation_observed=false` cannot simply be copied from fake callback
booleans. If the tagged source plus live evidence leaves either uncertain,
stop as `REVIEW_REQUIRED` before interpreting Δ. Old runner values, trained
`qwen2.context_length=32768`, or a matching token count alone are invalid
substitutes.

The parent records `{pid, raw_generation, pgid, argv/binary, listener}` for
worker, daemon and runner, plus exact process witnesses for every hash,
observer and I/O helper, as each first becomes visible, bracketing PGID
observation with raw-generation rechecks. Existing `raw_generation()` does
**not** return PGID, though BSD process data contain it. The runner may
have a different PGID from the daemon. At deadline or normal exit, stop
runner → daemon → worker → remaining helpers; before each TERM/KILL verify
the exact initial
raw generation, PGID, argv/binary and listener/parent evidence, then signal
**only that exact PID**, never a process group. Group enumeration followed
by `killpg` has an unclosed scan→signal membership race. A child first
discovered at cleanup cannot be retroactively treated as an initial
run-bound witness; leave it untouched and mark `physical_stop_unproven`.
Verify exit, private listener vacancy and
shared 11434 unchanged. Unknown child/process identity yields
`physical_stop_unproven`/`cleanup_review_required`, never a blind signal
or a claimed hard 90s guarantee on an adversarial host.

In a supervised I/O helper, create a private 0600 journal with `O_EXCL`,
fsync its initial zero-count state and containing directory. For each
operation, write an allowlisted new-state 0600 temporary file with
`O_EXCL`, fsync, atomically replace the journal and fsync the directory
**before the nonblocking parent grants ACK**. The final raw-free receipt
is a separate 0600 `O_EXCL` file with file/dir fsync in the same bounded
helper. A crash before ACK
cannot silently create a grant; a crash after ACK leaves that grant spent.
Retain only fixed codes, hashes, counts, timing and cost. If journal or
receipt persistence fails, stop with nonzero process status and
`receipt_unavailable_review_required` where possible; never continue
generation without the spent-attempt record or claim a durable receipt.
Keep `internal_runner_generations="unknown"` unless separate same-run
telemetry proves it; one external HTTP attempt does not count internal
runner work.
Daemons' stdout/stderr are private 0600 and may contain raw data; never copy
them to the public result, `CURRENT_TASK` or normal test output. Disable
traceback-local capture in the live operator. A receipt-write failure is a
hard stop; do not continue generation without durable attempt evidence.

## Resource ledger and fake stop controls

Hard caps: ≤7 **worker-issued external HTTP** including metadata (identity
observations are OS-only, never extra HTTP), exactly one normal
completion attempt maximum, ≤256 KiB each request, ≤2 MiB each response,
output ≤256 tokens, T0→cleanup/verification ≤90s or strict FAIL, 0 retry.
`probe._model_store()` hashes the **private** manifest and five blobs once
per call: lower-bound logical bytes **4,683,088,190**. Exactly one pre and
one post call would read ≥**9,366,176,380** bytes, plus daemon/runner
binary hashes; four calls would read ≥**18,732,352,760** bytes and are
forbidden unless the design is amended before a run. Record actual SHA
calls, logical bytes, wall/CPU and model-load/generation/cleanup phases.
Previously observed cached hash seconds are not a promise for this run.
No new model download, duplicate 4.4 GiB clone, formal DB write, Web or
Safari is permitted in this item.

Fake process/transport controls before any live run: blocked HTTP at each
stage and blocked hash, readiness, OS observer, journal/receipt fsync or
replace, or worker; expired clock; operation 8 or second completion;
missing/reused/mismatched ordinal-method-path-payload grant (zero HTTP);
proxy, redirect, wrong/shared port, response over cap;
worker/daemon/runner crash or raw-generation/PID reuse; runner in separate
PGID, PGID change and unknown child; TERM ignored, failed cleanup,
port still owned, attempt-journal or receipt fsync failure, raw canary in
exceptions/log/receipt; uncertain `-c/-np`, BOS or truncation. Positive
fake must show seven single-use grants/sends, one durable attempt before
operation 7,
six OS-only identity observations, both ports vacant and no impact on
11434. A blocked callback or disk helper must not prevent parent deadline
handling. Ollama daemon→runner internal RPC/generation counts remain
unknown; the seven-call cap is not a claim about those internal calls.

## Decision after review

If the fake process controls cannot prove bounded, identity-safe cleanup,
or if true run-time BOS/NumCtx and one-attempt accounting cannot be
observed within the fixed budget, return `REVIEW_REQUIRED` with the
smallest counterexample and cost. Do not weaken the 90s/7-call cap, change
the fixture, re-label fake as live or spend a live attempt to debug the
operator. Even a genuine one-shot Δ=0 does not authorize B Send, a B
prompt bound, a 20-second Safari claim, human preference or full-project
completion.

The next **exact implementation freeze** must specify the T0+80→+90s
TERM/KILL/exit/port-verification schedule (the old sequential `_stop_exact`
cannot simply be reused), the tagged-source and same-run observations for
`leading_bos`/no truncation, worker/daemon/runner `-c/-np` interpretation,
and fake-observer/IPC contracts. Until its fake controls and separate patch
review pass, this document does not permit a real attempt.
