# P4-B transformed-request diagnostic: fake-HTTP implementation freeze

Status: prospective source/fake contract only. This does not authorize a real
Ollama request, a B Send, a browser turn, or a prompt-token upper bound. The
previous B failures and fixed B question/budgets remain unchanged. This is a
single dependency of the existing P4 delivery gate, not a new M milestone.

## Before and one variable

The product boot creates `P4BResourceGate()` with a `None` counter. The
earlier 35-token render/tokenize probe used a fixed non-B fixture. Therefore
there is no request-specific diagnostic for the *actual post-compact* M21
shape, much less a certified upper bound. Add only a standalone, opt-in
diagnostic seam that copies and checks that shape against a private fake
transport. Do not change the gate, constructor, ledger, compact planner,
Brain, Web, persona, model, prompt, formal data, or any result freeze.

Allowed files: new `p4_b_transformed_request_diagnostic.py`, new
`test_p4_b_transformed_request_diagnostic.py`, one result note under
`analysis/`, and `CURRENT_TASK.md`. This freeze itself is allowed.

## API and invariant

`diagnose_transformed_request(*, request, binding, identity_check, http_post,
clock, max_elapsed_seconds=5.0) -> dict` has no implicit transport, process,
model, filesystem, or product side effect. `binding` must be an exact
`PrivateEndpointBinding` whose run ID, two distinct non-11434 ports, loopback
base URL, raw generations, model/runner source commitments and private root
pass the existing binding-shape validation. The injected `identity_check`
receives `(binding, absolute_deadline)` twice. It returns an exact-key,
raw-free observation containing run ID, two PIDs and ports, both four-field
raw generations, both argv SHA-256 values, daemon/runner binary SHA-256,
manifest/template/system SHA-256, and the two effective loopback URLs.
Every field is compared with binding or the frozen model constants, then
the canonical observation digest is compared before/after. A caller-provided
digest alone is insufficient.

The injected `http_post` receives `(url, payload, timeout_seconds)` and
returns an exact-key fake observation with requested URL, effective URL,
proxy-used bool, redirected bool, completion-generated bool, HTTP status and
raw response bytes. Reject anything except identical expected URLs,
three false flags, status 200 and a JSON-object response of at most 2 MiB.
Those fake observations are not proof of a future real transport's behavior.
No built-in real HTTP default or CLI is provided.
The two exact URLs are derived from the binding, never from request data:
`http://127.0.0.1:<daemon>/v1/chat/completions` and
`http://127.0.0.1:<runner>/tokenize`. The fake must attest that it performed
no proxy, redirect or completion; this contract alone cannot verify a future
real transport, so no authorization bit follows from it.

Before any callback: require the exact six M21 request keys; model
`qwen2.5:7b`, 0.1 temperature, 20.0 client timeout, 256 output cap, frozen
JSON schema, two system/user text messages, and the B gate's exact system
prefix (`You...` or one leading LF) and `User Input: ` prefix. Deep-copy the
request, canonical-JSON hash the copy, and reject a request exceeding 256 KiB
canonical UTF-8. The request passed to render-only removes only the
client-side `timeout`, adds only `_debug_render_only=true`, and otherwise
preserves the transformed message, model, temperature, output cap and schema.
The tokenizer receives the exact returned rendered string with
`add_special=false, parse_special=true`. Its nonempty token list must contain
only nonnegative exact integers. Render-only must return the same model,
empty assistant content, zero usage and a nonempty rendered template that
contains the full system and user message in ChatML system→user marker order.
No completion call
is permitted. The original request's canonical digest must remain unchanged
after each callback. Identity digest must remain byte-equal. Clock readings
must be finite, nondecreasing real numbers. The 5s deadline is checked
before/after every callback; HTTP receives no more than the remaining time.
Callback overruns reject, but cannot themselves prove a physical hard stop
if a future real identity checker blocks.

Successful in-memory receipt is raw-free and allowlisted: schema/status,
post-compact request hash, rendered hash/character count, identity hash,
diagnostic token count, two HTTP calls, elapsed seconds, `add_special=false`,
`parse_special=true`, `leading_bos_gap_unresolved=true`,
`generated_completions=0`, `upper_bound_proven=false`, and
`b_safari_send_authorized=false`. Raw request, rendered prompt, response,
tokens and exception text must never appear in the receipt or fixed-code
errors. The two hashes can be dictionary-attacked for low-entropy input and
are **private diagnostics**, never public dashboard/log fields. No durable
output is written by this module.

## Negative controls and acceptance

Tests must use only temporary synthetic requests and injected fake callbacks:
wrong/shared endpoint or binding shape; extra/missing request keys; wrong
model/schema/template/prefix; request mutation; identity generation/digest
drift; wrong URL, a fake transport reporting proxy/redirect/completion,
malformed render or tokenize data, nonempty assistant/usage, missing or
noninteger tokens, oversized response, malformed/backward clock, raw leakage
and timeout. Success is exactly two diagnostic
HTTP calls, two identity checks, zero completion calls, unchanged request,
false upper-bound/Send flags. No physical network, Ollama, Web, Safari, DB,
formal answer, or real B text may be used in this item. Red tests first,
then focused and affected regressions, compile/diff review, result note,
scoped commit/push and PR exact-head check.

Resource accounting is two HTTP calls and two identity callbacks, plus
end-to-end diagnostic wall time and response/request byte limits. The 5s
local diagnostic deadline is a **failure threshold**, not a proven 20s
click-to-DOM budget. A future real oracle must avoid adding another pair
of full model SHA reads to the ledger's existing pair (about 18.73 GB
logical reads already), obtain independently reviewed transport/source
parity including BOS/special tokens, and only then design one-shot product
gate activation. Failure of any negative control leaves B closed.
