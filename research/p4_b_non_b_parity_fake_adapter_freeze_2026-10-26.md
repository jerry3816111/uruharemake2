# P4-B non-B parity: fake adapter implementation freeze

Status: **independently reviewed GO for source/fake implementation only;
NO-GO for real HTTP/model/process/Safari**. The first freeze review was
NO-GO on run-bound identity and NumCtx/BOS invariants; those contracts were
made executable and the revised freeze received GO. This is the first
implementation gate under the reviewed
`p4_b_non_b_prompt_usage_parity_prospective_2026-10-26.md`. It may establish
an executable comparison contract; it does **not** authorize an Ollama
request, B Send, Safari, a token upper bound, or a new M.

## Before, one variable, allowed files

Before: the post-compact M21 shape is checked by a two-call fake-only
render/tokenize helper; there is no controlled comparison against one
normal completion's provider `prompt_tokens`. The single variable here is
adding an isolated, fake-observed **non-B parity comparison** with the
predeclared Δ=0 hypothesis and explicit failure states. Do not change
product boot/gate/ledger/Brain/Web/compact planner, B question/gold,
model parameters, formal holdout or private data.

Allowed edits are this freeze, new `p4_b_non_b_usage_parity.py`, new
`test_p4_b_non_b_usage_parity.py`, one bounded result note in `analysis/`,
and `CURRENT_TASK.md`. There is **no real transport default, process
launcher, CLI, `--execute`, worker watchdog or product import** in this
implementation. A later real operator must get its own freeze/review.

## Exact fake API and preconditions

`fixed_transformed_request() -> dict` uses the **real**
`compact_request()` in a single-threaded, explicit temporary environment:
`URUHA_P4_COMPACT_JSON_SCHEMA=1`, optional source-event arm off. It creates
only the two literal synthetic messages frozen in the prospective protocol
and returns a deep-copied transformed request. Require its exact six fields,
JSON schema, 1,833 canonical UTF-8 bytes, SHA-256
`7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56`.
If code/env/fixture drifts, fixed-code error before any callback.

`compare_non_b_parity(*, request, daemon_binding, observe_identity,
http_call, clock, max_elapsed_seconds=5.0) -> dict` has no filesystem,
network or process
default. `request` must equal the fixed transformed request by canonical
digest, be deep-copied and unchanged throughout. `clock` is monotone,
finite; five seconds is a **fake failure threshold**, not the later 90s
physical supervisor. The seven permitted fake HTTP operations in order:

1. GET private `/api/version` — exactly Ollama 0.34.4.
2. GET private `/api/tags` — one `qwen2.5:7b`, frozen manifest digest.
3. POST private `/api/show` with only the frozen model name — frozen
   template/system strings (compare SHA, never include strings in receipt).
4. POST private `/v1/chat/completions` with copied request minus client
   `timeout`, plus `_debug_render_only=true`. Validate same model, empty
   assistant, zero usage, and rendered system→user branch.
5. POST private runner `/tokenize` with exact rendered string,
   `add_special=false, parse_special=true`.
6. POST same runner `/tokenize` with exact rendered string,
   `add_special=false`, `parse_special` **omitted**. Require exact token ID
   lists equal (nonempty lists of nonnegative exact ints), not just lengths.
7. POST private `/v1/chat/completions` with the **same** copied request
   minus client `timeout` and no debug flag. This is the sole normal
   completion attempt. Reject missing/malformed usage; exact integer
   `prompt_tokens>0`, `completion_tokens>0`,
   `total_tokens=prompt_tokens+completion_tokens`; a returned choice with
   nonempty string `message.content` is required, but its raw text is not
   exposed. Δ is provider prompt tokens
   minus the shared token-list length. Only Δ=0 with all gates clear is a
   non-B fake parity PASS; otherwise retain a fixed-code negative result.

`http_call(method, url, payload_or_none, remaining_seconds)` returns an
exact-key observation with `requested_url`, `effective_url`, `proxy_used`,
`redirected`, `status`, `body` (raw bytes ≤2 MiB). Both URL fields must equal
the caller-constructed URL byte-for-byte; both flags must be exact `false`
and status exact integer 200. Test missing and extra fields as well as
host/proxy/redirect negatives. The callback-provided URLs may only be
validated, never used to choose the next request target. It may raise a
raw exception; the adapter must produce a fixed-code error with no raw
`__context__`, receipt, repr or traceback leak. Derive 127.0.0.1 private
ports only from structured run-bound identity, never from request text;
reject 11434, foreign host, mismatched effective URL or >7 calls. Total
canonical request ≤256 KiB.

`daemon_binding` is an exact-key immutable caller-supplied run commitment:
`run_id`, `daemon_pid`, `daemon_port`, `daemon_raw_generation`,
`daemon_argv_sha256`, `daemon_binary_sha256`, `manifest_sha256`,
`template_sha256`, `system_sha256`, `gguf_sha256`, `daemon_url`.
Require distinct valid exact-int PIDs/ports when runner appears, non-11434
daemon port, private loopback `daemon_url=http://127.0.0.1:<port>`,
four-part raw generation and SHA fields. All frozen source/model digests
must match the constants from `p4_b_isolated_ollama_identity_probe`.
This is injected fake authority for mechanical tests, **not** a real-run
certificate. No caller-provided runner URL is trusted; construct that
URL from the later observed, validated runner port.

The positive unit fake may patch only the adapter's expected template/system
digests to hashes of synthetic short strings returned by fake `/api/show`;
the actual frozen digest preimages are not copied into this test. An
unpatched test must assert the production defaults equal the source probe's
frozen constants and that mismatched show data fail. Report this as a
mechanism test under synthetic hashes, never a live-model identity pass.

`observe_identity(stage)` is fake-injected OS-only evidence called at
**exactly six named stages** in this order: `before_metadata`,
`after_render`, `before_tokenize_true`, `before_tokenize_default`,
`before_completion`, `after_completion`. The first observation must have
`runner=None`; the `daemon` subrecord must already equal
`daemon_binding` field-for-field. `after_render` binds the newly loaded
runner and is the first stage that may derive its private URL. The
following four observations must be byte-equal to that complete
`after_render` observation. Subsequent observations must contain the same
run ID, daemon/runner PID and four-part raw generation, loopback ports,
parent relation, argv/binary/GGUF/manifest/template/system digests,
runner `-c` and `-np` values, and frozen `add_bos=false`/empty leading BOS
facts. Require exact typed fields and stable full identity. `-c/-np`
must be positive exact integers with integral effective context; require
token-list length **strictly below** effective context and no observed
truncation. A callback claiming HTTP identity checks, uncertain context,
runner rotation or model drift must fail before the next call. Fake tests
cannot prove a future real identity observer is honest.

For this fake adapter, each identity observation must have exactly
`run_id`, `daemon`, `runner`, `identity_http_calls`.
`identity_http_calls` is exact integer zero. `daemon` has exactly
`pid`, `port`, `raw_generation`, `argv_sha256`, `binary_sha256`,
`manifest_sha256`, `template_sha256`, `system_sha256`, `gguf_sha256`,
`url`; the frozen digests must match `p4_b_isolated_ollama_identity_probe`
constants. `runner` is `None` only in the first observation, then has
exactly `pid`, `parent_pid`, `port`, `raw_generation`, `argv_sha256`,
`binary_sha256`, `gguf_sha256`, `url`, `context_total`, `parallel`,
`add_bos_token`, `leading_bos`, `truncation_observed`. URLs are strict
`http://127.0.0.1:<port>` without paths; `runner.parent_pid` equals
`daemon.pid`; ports differ and neither is 11434. Raw generations are four
exact nonnegative integers starting with the corresponding PID; daemon and
runner PIDs are positive distinct exact integers. SHA fields are lowercase
64-hex strings. `context_total` represents live runner `-c`, `parallel`
represents `-np`; both are exact positive integers and
`context_total % parallel == 0`. Effective
`NumCtx=context_total // parallel`. The two tokenizer ID lists must be
identical and their common length must be **strictly less** than this
effective `NumCtx` before the normal completion is attempted.
`add_bos_token` and `truncation_observed` are exact `false` and
`leading_bos` is the empty string. Identity after render must be byte-equal
for all later observations; the daemon subrecord must be byte-equal even
across the initial runner-absent transition. This typed fake observation
does not replace same-run OS checks in the later real operator.
`runner.raw_generation[1]` must equal `daemon.pid`, the same value as
`runner.parent_pid`; a declared parent that disagrees with the raw process
generation is a negative control.

Receipt is private/in-memory, allowlisted raw-free: fixed schema/status,
request/render/identity SHA, request/render lengths, two tokenizer lengths,
provider usage and signed Δ, seven HTTP calls, six OS-only identity checks,
one external completion attempt, `internal_runner_generations="unknown"`,
elapsed, `upper_bound_proven=false`, `b_safari_send_authorized=false`.
Never persist prompt, rendered text, token IDs, response, exception text,
daemon logs or raw callback objects. No result, including fake PASS, can
set B authorization true.

## Red/green contract and next stop

Red tests first: exact fixture/env drift; request mutation; wrong/shared
host, proxy, redirect, status or model; metadata/template/system mismatch;
malformed/oversized/deep JSON (including nonfinite numbers, ambiguous
duplicate keys and invalid Unicode); malformed render; tokenize IDs mismatch;
runner missing/rotated, raw generation/argv/port/context/BOS drift;
context too small; bad clock/deadline; HTTP eighth or second completion;
usage missing/bool/negative or total mismatch; raw canary in exception
chain/receipt; false B authority. Positive fake asserts seven calls in
order, six OS-only identity observations, one fake normal completion,
Δ=0, unchanged input, no external side effect. A nonzero Δ must remain a
negative result, not trigger a modified margin/retry.

Focused: `.venv/product_checks/bin/python -m pytest -q
test_p4_b_non_b_usage_parity.py`. Adjacent: add
`test_p4_b_transformed_request_diagnostic.py`,
`test_p4_b_isolated_ollama_identity_probe.py`,
`test_p4_b_private_endpoint_binding.py` and compact planner tests. Python
compile, `git diff --check`, independent patch review, scoped commit/push
and exact PR head. **No live HTTP, model generation, Web or Safari in this
item.** If the freeze/API proves too broad or a negative control fails after
two grounded correction batches, keep `REVIEW_REQUIRED` rather than weaken
the predeclared parity hypothesis.

Real-run dependency is a separate minimal supervisor contract. In
particular, prior zero-turn operator `run()`/`probe.probe()` add calls and
must not be reused whole. A later watchdog must verify live worker,
daemon **and runner** PGIDs and raw generations; tagged runner process
attributes may detach it from an inherited group. An identity-uncertain
process cannot be blindly killed, so 90s physical stop is conditional and
must be reported as unproven if cleanup cannot be verified. Model-store
SHA checks read about 9.37 GB logically per pass; pre/post could total
~18.73 GB before binary hashing, and must be counted against the later
live wall budget. B remains closed throughout.
