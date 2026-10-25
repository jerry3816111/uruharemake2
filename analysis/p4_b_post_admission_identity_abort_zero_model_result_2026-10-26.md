# P4-B post-admission identity abort — zero-model result (2026-10-26)

## Result and exact scope

The frozen single variable in
`research/p4_b_post_admission_identity_abort_freeze_2026-10-26.md` is now
implemented: if the B ledger has admitted the exact M21 request but the
second private-child revalidation raises before SDK `create`, the gate stores
the raw-free `pre_provider_revalidation_failed` diagnostic terminal. The
original exception still propagates. The sole admission remains reserved;
there is no fake provider invocation, no ledger completion record, and no
invented provider token usage (`actual_total_tokens=None`). This changes
in-memory gate accounting, not Web response policy or a durable turn receipt.

Before the edit, a direct zero-provider reproduction with the real gate and
ledger proxy plus a fake bound returned two identity checks, SDK calls 0,
`attempted_provider_calls=1`, `terminal_reason=""`, actual usage `None`,
ledger `call_count=0`. The new focused tests first failed **2/2** on the
missing terminal/method, then passed **13/13** after the narrow repair.

## Evidence and negative controls

| Check | Observation |
|---|---|
| Actual gate admission, second identity failure | Original synthetic error propagated; identity checks 2, provider 0; attempt reserved 1, admitted bound 1, fixed terminal, actual usage `None`, ledger 0. Sequential retry denied with the fixed reason. |
| Real compact transformation over ledger proxy | A precompact request was rewritten to the exact B JSON Schema request; second identity failure remained pre-SDK, compact audit attempted/not completed, provider 0, terminal fixed, ledger 0. |
| Before admission | First identity failure left gate attempt 0/terminal empty/ledger 0. Direct terminal-method call without admission could not fabricate a failure. Missing token-bound callback kept its original `prompt_upper_bound_unavailable` denial, attempt 0, provider 0, ledger 0. |
| Provider side and success | A fake provider exception kept `provider_error_or_missing_usage` and one *physical* ledger completion call. Successful fake B path kept valid usage total 2 and one ledger call. Non-B and other B gate cases were included in adjacent regression. |
| Affected regression | Seven files (`private_web_ledger_seam`, `resource_gate_zero_model`, `private_child_bootstrap`, `private_endpoint_binding`, `private_child_chain_zero_provider`, `private_constructor_seam`, `compact_planner_p2`) **222/222 passed in 203.37s** before the final test-only compact-path addition. After that addition, the three directly affected files **60/60 passed in 5.65s**. Changed Python `py_compile` and `git diff --check` passed. |

The new compact-path test initially failed because its test fixture had not
enabled `URUHA_P4_COMPACT_JSON_SCHEMA=1`; the gate correctly rejected the
resulting JSON-object request as `m21_request_drift`. Adding the required arm
to this isolated fixture made the test pass. No product code or gate assertion
was relaxed for that test setup correction.

All provider objects and token bounds here were fake; there was **no real
Ollama, Web Send, Safari, production DB, deployment or human evaluation**.
The independent read-only design and patch reviews approved only the scoped
source/fake repair. The diagnostic terminal is in memory, not a durable Web
receipt. The legacy field `attempted_provider_calls=1` means *admission
reserved*, not one physical SDK call in this pre-provider failure case. If a
concurrent extra attempt records a terminal first, existing first-terminal
semantics may retain that earlier reason; a fixed reason across arbitrary
interleavings is not established. Crash/`BaseException` paths are not covered.

Most importantly, `LeftBrain.think` still catches broad exceptions and may
convert a B gate/identity failure to a normal fallback plan, potentially
leading to a visible reply and episode writeback. This patch does **not**
establish whole-turn B fail-closed behavior. The next necessary single
variable is B-only propagation of this class of terminal error through the
turn/Web boundary, with isolated fake full-turn negative controls: no final
role reply or episode on B gate failure, durable terminal failure receipt,
while ordinary non-B fallback remains unchanged. Production prompt-token
upper bound, real daemon/runner identity, 20-second Safari delivery and A
author ratings remain NO-GO for true B Send.
