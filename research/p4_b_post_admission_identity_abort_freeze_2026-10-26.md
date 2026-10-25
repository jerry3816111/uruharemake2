# P4-B post-admission private identity abort — prospective freeze

## Before evidence and single variable

At committed HEAD `04056b6`, `_CompletionProxy.create` revalidates the
private child before gate admission, admits the transformed M21 request, and
revalidates once more before SDK `create`. The second revalidation sits outside
the provider `try/finally`. A zero-provider reproduction using the real gate,
ledger proxy and a fake token-bound callback made the second check raise:
two identity checks, zero SDK calls, gate `attempted_provider_calls=1`,
`terminal_reason=""`, `actual_total_tokens=None`, and ledger `call_count=0`.
This is a reachable accounting gap, not evidence that the real B child sent a
model request. Production's prompt upper-bound callback is still absent.

Change only the terminal accounting when a *successfully admitted* request
fails its second private-child revalidation. Keep the original exception and
zero provider calls; reserve the existing one-attempt slot and write a fixed,
raw-free `pre_provider_revalidation_failed` terminal reason. Do not invent
provider usage: `actual_total_tokens` must remain `None` and the ledger must
record no completion call. A later attempt must remain denied. The legacy
`attempted_provider_calls` field denotes a reserved admission here, not an
observed physical SDK invocation; this patch does not rename its schema.

Allowed product files: `uruha_compute_ledger.py`,
`uruha_p4_b_resource_gate.py`. Allowed test file:
`test_p4_b_private_web_ledger_seam.py`. This freeze, one result note and
`CURRENT_TASK.md` may be added/updated. No changes to prompt, tokenizer,
model, B boot identity, baseline, formal data, Web response policy, or the
previously frozen results.

## Predeclared tests and negative controls

1. Focused red-before/green-after test must use actual gate admission with a
   fake token bound; fail only the second revalidation; assert original error,
   zero fake provider calls, gate terminal, admitted bound, no actual usage,
   and zero ledger calls. A subsequent attempt remains denied with that fixed
   terminal, without changing admitted bound, usage, or ledger count. Calling
   the terminal-recording method before any admission must not fabricate this
   terminal.
2. Pre-admission identity failure must not reserve an attempt or claim this
   post-admission terminal. Successful fake B admission must still reach one
   provider call and record valid usage. Gate/token-bound admission denial
   must retain its original reason with attempt 0, SDK 0 and ledger 0. If the
   fake provider itself raises after the second revalidation, the existing
   provider-error classification and one physical ledger call must remain,
   not be relabeled as a pre-provider failure. Existing non-B ledger tests
   must not regress. The prior test which monkeypatches admission to a no-op
   is not evidence for this new positive-admission failure case.
3. Run affected zero-model gate/ledger/bootstrap/Web tests, `py_compile` and
   `git diff --check`; retain any failure. Review exact changed paths and
   preserve unrelated `output/graduate_application_report/`.
4. No real Ollama, Web Send, Safari, DB write, download, deploy or human
   evaluation. The previous failed true B identity probe is not retried.
   Commit/push only scoped files to PR #435 and verify its exact head.

This is a source/fake terminal-accounting fix, **not** a B Send authorization.
It does not supply production token upper bounds, real daemon/runner identity,
20-second Safari evidence, full source/effect closure, or A author ratings.
M21's broader fallback/caught-error delivery is a separate product gate and
must not be declared solved by this patch.
