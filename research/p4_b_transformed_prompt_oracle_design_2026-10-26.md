# P4-B transformed-request token oracle — source-only design baseline

Status: **design for review, not authorization to call a model or send B**.
The completed exact-prefix fix (`b280b6a`) proves only an isolated fake
provider path. This card does not alter the fixed B question, gold, model,
2000-token cap, 256 completion cap, 20-second browser wait, baseline or
previous failures. It introduces no M number and no product code.

## Before evidence: where the missing proof lives

- `uruha_p4_b_private_child_bootstrap.py` constructs `P4BResourceGate()`
  with no prompt-bound callback. `validate_private_endpoint_binding()`
  explicitly requires that the constructor-time unused gate still have
  callback `None`. A test-injected integer such as `1200` is not a product
  token certificate; copying it into boot would violate this contract.
- `uruha_compact_planner_p2.compact_request()` rewrites the M21 system
  prompt, JSON format and `max_tokens` before the inner ledger gate.
  `_CompletionProxy.create()` revalidates the private child, asks the gate to
  admit that exact transformed request, revalidates again, then calls SDK.
  Any oracle must live at this transformed-request boundary, not count the
  earlier untransformed prompt or a separately reconstructed sample.
- The earlier private Ollama 0.34.4 probe used a **fixed non-B** request:
  render-only returned the template, and the same private runner's
  `/tokenize` returned 35 tokens for its own fixture. That observation is
  neither a B count nor an upper bound. Ollama's tagged source confirms
  `DebugRenderOnly` returns the rendered template before completion, while
  the normal completion passes `Prompt` and `LeadingBOS` to the runner
  ([v0.34.4 route](https://github.com/ollama/ollama/blob/v0.34.4/server/routes.go),
  [prompt construction](https://github.com/ollama/ollama/blob/v0.34.4/server/prompt.go)).
  Therefore equality between diagnostic token length and actual provider
  `prompt_tokens` cannot be assumed without a source argument and parity
  evidence, including BOS/special tokens, Unicode and JSON-schema shape.
- Current pre-create identity checks read at least ~18.73 GB of model bytes
  logically per generation; an earlier cached four-read microbenchmark was
  9.301121s, not a turn latency. Reusing the existing diagnostic helper's
  two 5s HTTP timeouts could add up to 10s *before* generation. No evidence
  yet shows the entire click-to-DOM path can fit the frozen 20s threshold.

## Chosen dependency order; no silent B release

1. **Next implementation item: product-disconnected, fake-HTTP-only
   request-specific diagnostic seam.**
   One input is the immutable/deep-copied M21 request *after* compact
   rewriting. One output is a raw-free diagnostic receipt: request digest,
   private daemon/runner/model/template identity digest, rendered-template
   digest, runner token count, BOS/special-token status, diagnostic call
   count, elapsed time, and an explicit `upper_bound_proven=false` until
   independently justified. Use the run-bound private endpoint only,
   no shared 11434, proxy, redirects, extra generation or prompt logging.
   A future *real* invocation would transmit the raw transformed request to
   the private loopback daemon and hold the raw rendered prompt in memory;
   `raw-free` describes only durable receipts, errors and public output, not
   the absence of in-process/network raw data. This next item uses fake HTTP
   only, so it sends no actual B prompt anywhere.
   Check identity before/after and refuse missing, changed, malformed,
   timed-out or mismatched data. This component is **not** wired into the
   product B gate and cannot make a B Send possible.
2. Separately freeze and review one same-shape **non-B** conformance probe
   against the same private daemon/runner: exact render/tokenize versus one
   real completion's reported `prompt_tokens`, with predeclared BOS margin,
   request bytes, model identity, HTTP counts and cost. This is a controlled
   generation and needs a fresh GO, not permission from item 1. A few
   observations may refute a bound; they cannot prove a universal bound
   without matching source-level reasoning and negative cases.
3. Non-B parity cannot issue the B bound: separately freeze the actual B
   **same transformed request** render/tokenize, issuance time and cost.
   Only after parity/source/cost evidence, prospectively design a one-shot
   gate activation **after** constructor validation and before the first B
   turn. Bind the same private run/child/runner, exact transformed request
   digest and bound to the SDK call; reject any concurrent mutation, reuse,
   missing identity, or `bound+256>2000`. Define terminal cleanup and raw-free
   receipt for diagnostic failures. Recheck the identity between diagnostic
   and SDK as far as the cooperative local threat model permits. Do not
   bypass the constructor `None` check or assign its private field directly.
   A non-B token count plus a margin must never be substituted for B.
4. Independently reassess the actual 20s browser deadline and all other B
   release gates: real daemon/runner identity, source/effect closure, A
   author ratings and on-only gold, no late-visible result, real Safari
   graph/utterance/memory/cost. A local oracle is one dependency, not a
   product pass or proof of an advantage over a strong LLM.

## Next item acceptance / stop rule

Allowed *next-item* code would be a standalone opt-in diagnostic helper and
its isolated tests only, plus a result note and `CURRENT_TASK.md`; no
bootstrap, gate, ledger, Brain, Web, model prompt, controller or production
data edits. Before code, freeze exact helper API, permitted files, fake HTTP
shapes, resource ceiling and negative controls, then obtain independent
review. Red tests must catch wrong endpoint, proxy/redirect, wrong model or
template, changed runner generation, malformed render/tokenize, raw leakage,
    timeout, request mutation and a false `upper_bound_proven=true`; green tests
    must observe two diagnostic calls and zero fake completions. The future
    freeze must count both HTTP calls, pre/post identity SHA work and total
    pre-SDK wall time with a hard stop; identity or time uncertainty leaves B
    closed. Run affected
regressions, diff review, scoped commit/push and exact PR check. A failed
negative control or an unbounded diagnostic becomes `REVIEW_REQUIRED` after
at most two grounded correction batches, not a weaker gate or a changed B
question. No real Ollama, Web or Safari in that next item.
