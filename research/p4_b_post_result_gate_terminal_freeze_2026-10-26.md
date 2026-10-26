# P4-B post-result gate terminal propagation — prospective freeze

## Before evidence and one variable

At committed HEAD `cf3a070`, the B ledger proxy records a physical SDK
completion and then calls `P4BResourceGate.observe_openai_result` in its
`finally`. For a fake M21 request admitted with a fake prompt bound, a fake
SDK response with no `usage` returned normally to the caller even though
the gate snapshot had `terminal_reason="missing_provider_usage"` and the
ledger had one generation call. Its aggregate `total_tokens=0` is a missing
value artifact, **not** proof of zero physical token use. `LeftBrain` now
rethrows B M21 exceptions, but no exception exists on this post-result path.

The single product variable is **propagate a B gate terminal detected after a
successful SDK return, before that response can be consumed as a candidate**.
The inner proxy must finish its existing physical-call ledger record and gate
usage audit, then raise a fixed `P4BResourceGateError` carrying the recorded
reason if the gate has become terminal. Do not falsely turn the physical
provider call into zero, invent usage, or change the one-admission rule. A
provider's original thrown exception must remain the original exception;
the post-result terminal check must not mask it. Non-B ledgers have no gate
and retain existing response behavior. This is not an Ollama tokenizer oracle
or a retrospective hard token cap.

Allowed product files: `uruha_compute_ledger.py`,
`uruha_p4_b_resource_gate.py` if a read-only gate terminal API is needed.
Allowed tests: `test_p4_b_resource_gate_zero_model.py`,
`test_p4_b_private_web_ledger_seam.py`, and one new isolated full-turn
`test_p4_b_post_result_gate_terminal_zero_model.py` if needed. This freeze,
one result note, and `CURRENT_TASK.md` may change. Do not alter prompts,
model, Web UI, Brain fallback policy, token callback availability, baseline,
formal data, prior result reports or controller source manifest shape.

## Predeclared acceptance and negative controls

1. Red-before/green-after inner proxy fake: missing usage, prompt use above
   proved bound, completion >256, and an over-2000 reported total each record
   one physical ledger call, preserve actual reported numbers or unknown, set
   the correct fixed terminal reason and **raise before returning a response**.
   With `bound+256<=2000` and internally consistent usage, an over-2000 total
   mathematically also breaches the prompt or completion cap; do not force
   the later `actual_token_budget_exceeded` branch to fire by weakening an
   earlier invariant. Valid usage
   returns once and records once. Pre-send gate denial still makes zero SDK
   and zero ledger call.
   These checks use integer usage values or `None`; malformed float/bool
   provider usage and the ledger's current coercion of them are not silently
   treated as exact reported-number evidence in this item.
2. Fake SDK `create` exception remains its original type/message and one
   physical ledger error call; the gate's diagnostic terminal does not mask
   it. A non-B ledger with the same fake missing-usage response returns it
   unchanged and records its ordinary partial-usage call.
3. Isolated fake compact-transform→M21→Brain/Web route: a missing-usage
   provider response cannot produce a final role reply, save an episode, or
   conversation JSONL; the private 0700 Web test directory gets a raw-free
   0600 terminal failure file with one physical generation and unknown token
   usage. B text browser-bound path uses the previous fail-closed cleanup;
   no native Safari is implied. If a full route fixture cannot safely avoid
   all other model entrypoints, retain the exact seam-only evidence and mark
   full-turn pending rather than issuing a real model call.
4. Run focused and adjacent B gate/ledger/compact, M21, Web receipt tests,
   changed Python compile and diff check. Review only scoped paths; preserve
   unrelated `output/graduate_application_report/`. Commit/push PR #435,
   verify exact head, and do one read-only committed-source snapshot.

No real Ollama B Send, real Web service, Safari, production DB, download,
deployment or human rating is authorized by this item. Previous exploratory
M31 local calls from the preceding repair are disclosed there and must not be
repeated. Production prompt upper bound is still absent; true daemon/runner
identity, source/effect closure, A author ratings and 20-second delivery
remain independent NO-GO gates. A gate check after the physical call can stop
visible delivery, but cannot retroactively prevent that call or prove the
same-model budget was respected.
