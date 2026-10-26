# P4-B non-B prompt/usage parity: source/fake result

Status: **PASS only for the injected fake contract; NO-GO for live Ollama,
physical 90-second stop, B token bound, B Send, Web/Safari or user-visible
quality.** This implements the reviewed
`research/p4_b_non_b_parity_fake_adapter_freeze_2026-10-26.md` under the
earlier prospective non-B protocol. It is a prerequisite of P4-B, not a new M.

## Before, intervention, measurable difference

Before this item, the transformed M21 request diagnostic exercised one
render-only and one tokenize **fake** call. It could not compare that count
with a normal completion's provider `prompt_tokens`. The sole intervention
adds `p4_b_non_b_usage_parity.py`, disconnected from the product, with only
injected fake HTTP, identity and clock callbacks. It calls real
`compact_request()` for a synthetic non-B fixture and checks its frozen
1,833-byte canonical SHA-256
`7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56`.
The positive fake then makes exactly seven callback operations (three
metadata, one render, two tokenize, one normal completion) and six OS-only
identity observations. Both tokenizer ID lists are equal and shorter than
the fake effective NumCtx. With three fake token IDs and fake provider
`prompt_tokens=3`, signed Δ is **0**. Changing only provider prompt usage to
4 while preserving a valid total yields **Δ=+1**, a retained mismatch with
no retry or B authority; a negative Δ is also covered. These are synthetic
counterexamples, not actual Qwen usage or an upper-bound measurement.

`/api/show` positive tests use two synthetic short strings and monkeypatched
expected hashes because the real frozen template/system preimages are not
part of the test fixture. Separate unpatched tests assert the production
defaults equal the frozen probe constants and reject the synthetic show
response. This checks the comparison mechanism, **not** a live-model
identity. Request, render, token IDs, response text and callback exceptions
are not persisted in the returned allowlisted in-memory receipt. It always
sets `upper_bound_proven=false` and `b_safari_send_authorized=false`.

## Red/green and controls

The initial red test module failed import before implementation. Later,
seven malformed-JSON counterexamples were observed red before the parser
fix (7 failed / 85 deselected) and green afterward: NaN/Infinity including
numeric overflow, duplicate keys and lone-surrogate keys/values in metadata
or completion. An independently found missing/empty completion-content
counterexample was also made fail-closed. Other negatives cover foreign or
shared 11434 URLs, proxy/redirect/status/extra fields, metadata/model drift,
raw process-generation and parent mismatch, runner rotation, NumCtx/BOS/
truncation uncertainty, unequal token ID lists, request/binding/payload
mutation, invalid usage, deadline and raw exception-chain leakage.

Final source/fake verification:

- Focused fake adapter test: **92/92 passed** (separate read-only reviewer
  run; same-model agent review, not external independent assessment).
- Eight affected test files: **244/244 passed in 15.63 seconds** on this
  machine, independently rerun by the coordinating agent. `py_compile`
  passed; scoped diff whitespace checks passed.
- New actual HTTP calls **0**, real completion **0**, Safari/Web turns **0**,
  formal DB writes **0**. Seven calls and one normal completion are fake
  callback counts only; no provider token spend or real latency was measured.
- Read-only second review: **GO only for scoped source/fake commit**. Its
  missing-content and malformed-JSON probes were incorporated before GO.

The fake adapter has no transport/process/file-write default or product
import. Fixed-code errors have no raw `__cause__` or `__context__`; malformed
usage/transport fails with `ParityError`, not a success receipt. This is
adequate for the in-memory fake contract, not for a future real operator:
that operator must write a private 0600 raw-free failure receipt and avoid
logging raw callbacks or traceback locals.

## Remaining gate and next dependency

This result does **not** establish that a real identity observer is honest,
that a daemon/runner can be physically stopped within 90 seconds, that a
real non-B request satisfies Δ=0, or that the actual B transformed request
has a safe prompt-token upper bound. It also says nothing about the 20-second
Safari turn, A author rating, answer quality, or the full system's advantage
over a strong LLM. No B Send or fourth B Ollama request is authorized.

Next necessary item: separately freeze/review a real-run supervisor and
transport, including live daemon **and runner** PGID/raw-generation checks,
one-attempt accounting, conditional 90-second stop, no-proxy/redirect,
private 0600 success/failure receipts, model/hash I/O and wall-time budget,
and fake cleanup negatives. Only after that gate may one synthetic non-B
real-run observation be considered; no B-specific bound follows from it.
