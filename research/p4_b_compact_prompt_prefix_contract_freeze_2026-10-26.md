# P4-B actual compact M21 prompt prefix — prospective contract freeze

## Before evidence and one variable

At committed HEAD `009e98b`, the actual source-only M21 system prompt begins
with exactly one newline before `You are the Left Brain Planner...`.
`compact_request` preserves that leading byte while replacing the old JSON
schema tail. The B gate currently checks `content.startswith("You are...")`
at byte zero. An isolated fake full Brain→Web probe observes an otherwise
eligible transformed request (`leftbrain_general_plan`, qwen2.5:7b,
temperature 0.1, timeout 20.0, max_tokens 256, JSON Schema) denied as
`m21_request_drift` with fake provider calls 0 and ledger calls 0. The two
post-result full-route expectations are retained as **strict xfails**, not
passed tests; the prior partial result is not rewritten.

The only product variable is the B gate's *exact system-prefix acceptance*:
allow its existing no-leading-newline shape **and exactly one leading `\n`**
before the same literal prefix. Do not trim or rewrite the prompt sent to the
model, change its token-bound callback input, or allow arbitrary whitespace,
CRLF, two newlines, banners or a different first instruction. Preserve all
other gate request/stage/usage/identity rules and `m21_request_drift` reason.
This aligns a gate with the already-existing product serialization; it is not
a new prompt, tokenizer proof, model behavior claim or B Send release.

Allowed product file: `uruha_p4_b_resource_gate.py` only. Allowed tests:
`test_p4_b_resource_gate_zero_model.py`,
`test_p4_b_post_result_gate_terminal_zero_model.py` (remove strict xfail only
after actual route exercises the intended outcome), and any existing
`test_p4_b_private_web_ledger_seam.py` assertion necessary for the no-newline
control. This freeze, one result note and `CURRENT_TASK.md` may change.
No controller, compact planner, Brain/Web, token oracle, prompt template,
baseline, formal data or prior report edits except this prospective note.

## Predeclared acceptance and negative controls

1. Focused red-before/green-after gate tests: both original `You...` and
   actual `\nYou...` prefix admit an otherwise exact fake request with one
   proved *fake* bound and one fake provider call. `\n\nYou...`, leading
   spaces, CRLF, altered header, prepended text and wrong stage remain denied
   before provider with `m21_request_drift` or existing stage reason. The
   callback must receive the exact unchanged transformed prompt bytes.
2. Actual `compact_request` path (not a manually normalized test string)
   reaches one fake provider with the single-newline system prompt. The two
   strict xfails from the preceding item may be removed only if actual
   compact→M21→Brain/Web missing-usage tests now observe physical provider1,
   ledger1/unknown token usage, gate `missing_provider_usage`, no role reply,
   no episode/conversation JSONL, and a raw-free 0600 private failure file.
   If any other mismatch remains, keep an explicit failed upper-layer result
   and do not expand this product variable to chase green.
   Convert the preceding item's explicit **before-state** regression
   `test_actual_compact_m21_prefix_drift_blocks_fake_provider_before_result`
   into a positive actual-prefix admission/post-result denial regression;
   preserve its prior provider0 observation in the result note rather than
   deleting historical evidence to make the suite green.
3. Run B gate/ledger/compact/M21/Web adjacent zero-model tests, changed-file
   syntax and diff checks, scoped diff review, commit/push PR #435 exact, and
   one read-only committed-source snapshot. Preserve unrelated
   `output/graduate_application_report/` and the original dirty checkout.

No real Ollama, Web service, Safari Send, production DB, deployment or human
rating here. The production prompt-token upper-bound oracle is still absent;
real daemon/runner identity, source/effect closure, 20-second delivery and A
author ratings remain NO-GO. Even if full fake route passes, it proves a
bounded source/fake failure path, not actual model generation or a general
human-response-equation advantage.
