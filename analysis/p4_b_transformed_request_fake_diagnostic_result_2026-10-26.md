# P4-B transformed-request fake diagnostic: bounded source result

Status: **PASS only for an isolated fake-HTTP diagnostic contract**. Product B
Send, real Ollama generation, real prompt-token upper bound and Safari remain
**NO-GO**. This is a necessary P4 B preflight dependency, not a new M result
or an improvement in visible reply quality.

## Before / change / observation

Before, boot still made `P4BResourceGate()` with no prompt-bound callback;
the only render/tokenize observation was a fixed **non-B** fixture with 35
tokens. No helper accepted the actual post-`compact_request()` M21 shape.
The new `p4_b_transformed_request_diagnostic.py` accepts that shape without
product wiring. It deep-copies and hashes the request, validates exact M21
fields, compares structured run-bound identity observations before/after,
and asks an injected fake transport for render-only plus runner tokenize.
It preserves the exact transformed wire fields except client-only `timeout`
and `_debug_render_only=true`; the rendered string is passed unchanged to
fake tokenize. The in-memory receipt exposes digests/counts only, never raw
request, rendered text or tokens. It always reports
`upper_bound_proven=false` and `b_safari_send_authorized=false`.

One success path uses a synthetic pre-compact request passed through the
**real** `compact_request()` function, then the new helper: exactly two fake
HTTP callbacks, two fake identity callbacks, zero completion callbacks,
unchanged source/request, and no B authority. The synthetic tokenize list
had three elements; **3 is not a B token measurement or bound**. A separate
deterministic fake-clock case reports 2.0s total when the four callbacks
each advance 0.5s, while another proves 0.25s request validation cost is
included and reduces the first HTTP timeout to 4.75s. These are clock
contract tests, not hardware latency measurements.

## Failure evidence and verification

- Initial red skeleton: 23 failed, 14 passed; the success path and callback
  observations were not implemented. Final focused: **47/47** in 0.26s.
- Final adjacent set (new diagnostic, old isolated probe, private binding,
  B resource gate, compact planner): **187/187** in 7.87s, eight existing
  dependency warnings. Python compile and Git whitespace check passed.
- Negative controls cover missing/extra request fields, wrong model/schema/
  exact prefix, shared or drifted endpoint, structured model/template/runner
  identity including bool-as-int generation, proxy/redirect/completion
  claims, wrong effective URL/status, oversized/malformed/deep JSON body,
  malformed render/tokenize, request mutation, raw exception context and
  deadline overrun before every later callback. An initial independent
  review found missing actual compact coverage; later reviews found raw
  `__context__`, deep JSON and timing gaps. Each was reproduced and closed
  before the final limited GO.

Resource ceiling in this **fake** item: 256 KiB canonical request, 2 MiB
per response, two HTTP callbacks, two identity callbacks, and a maximum
5s diagnostic failure threshold. A callback that physically blocks can
exceed the threshold before being rejected. The existing real product
pre-create identity path already reads about 18.73 GB of model bytes
logically per generation; this helper has not demonstrated how to reuse
that work and has not measured a real pre-SDK or click-to-DOM latency.

## Evidence boundary and next gate

The module has no built-in HTTP implementation, CLI, product entrypoint
wiring, DB write or gate activation. All identity and transport observations in this
result were injected fakes; a malicious or incorrect callback could lie.
The request/render digests may reveal low-entropy text by guessing and must
stay in private diagnostics, not a public graph/log. There was no real B
question sent, no fourth Ollama attempt, no Web/Safari run, no new visual
card, and no author A rating. Existing product graph evidence is unchanged.

Next: independently freeze/review a **same-shape non-B** private Ollama
render/tokenize-vs-one-completion parity experiment with actual prompt
usage, BOS/special-token and model/template identity accounting, exact
call/resource/deadline budget and no retry. A passing non-B observation
would still not issue the B-specific upper bound. Only a separate actual
transformed B request oracle, safe gate activation after constructor
validation, source/effect identity, 20s Safari and A author evidence could
reopen B Send review. Historical failed B attempts remain failed.
