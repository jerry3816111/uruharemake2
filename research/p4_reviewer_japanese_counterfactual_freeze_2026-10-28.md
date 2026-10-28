# P4 reviewer Japanese counterfactual: prospective product freeze

Status: **design only**. No source, model, or Safari Send for this variable yet.
This follows the exposed failure in
`analysis/p4_source_bound_candidate_generation_result_2026-10-28.md`.
It is not a sealed research holdout, a new grade of that row, or a waiver of
the 20-second product target.

## Before, causal hypothesis, and limit

The released source-bound M51 prompt was actually applied in one isolated
native-Safari turn. M47 authorized the exact current-User first-step task;
M51 produced two candidates, one structurally valid; M53 found no unsupported
named labels. The only hard M46 content violations were
`invalid_counterfactual_before_jp` and `invalid_counterfactual_after_jp`:
the same-model reviewer filled two Japanese-designated fields with Chinese
sentences. `group_by_rule` (plan) versus `structure_scaffold` (review) is
visible ambiguity, **not** a separate blocking condition while both are
allowed; frozen M46 source and
`test_two_allowed_mechanism_labels_are_visible_ambiguity_not_false_failure`
confirm this. M46 correctly withheld the action; visible reply lacked a
first step. The turn took 36.1007 s, 2 M45 model calls, and 2,944 reported
tokens. Unchanged M46/M51/source-bound adapter tests are **22/22 PASS**.

Falsifiable hypothesis: for a non-Japanese current-User source that reaches
this exact route and a structurally valid M51 plan, explicitly constraining
the existing M46 reviewer **instruction** to write its two counterfactual
`*_jp` free-text fields in Japanese will reduce Japanese-field contract failures.
It may not make the plan useful, pass all reviewer checks, or satisfy the
latency target; those remain separately measured.

## One variable and immutable boundary

Only replace the instruction passed to the **existing M46 counterfactual
review model call**, never its result, schema, payload, model, seed,
temperature, deadline, token cap, or transport. Append an explicit amendment
to the frozen M46 `REVIEW_SYSTEM`: `source_id` and `source_span` must remain
byte-exact original source evidence, even if Chinese/English; the **two free
text** fields `counterfactual_before_jp` and `counterfactual_after_jp` must
be concise natural Japanese with actual Japanese grammatical material.
`observed_progress_mechanism` remains its exact English schema enum and the
content/surface checks remain JSON booleans. The model must not translate or
replace the quoted source span, invent before-state facts, assert hidden
preferences, or soften a false content check merely to pass.
If no supportable before/after state exists, the reviewer must mark the
appropriate check false; M46 may reject. Do not put an example answer,
exposed handout phrase, or task-specific category in the amendment.

A new product-only adapter may wrap **only** current `action45._native_json`.
It must read the already released candidate adapter's per-turn
`_CONTEXT.get()` without mutating that context: the old adapter has already
checked the exact M47 receipt, current-User digest/task span/source and resets
the `ContextVar` in `finally`. Only `eligible is True`, `applied is True`,
`system == m46.REVIEW_SYSTEM`, and a schema containing both existing
counterfactual fields may substitute the review instruction. Preserve exact
identity of payload, schema, deadline, metrics, and underlying transport;
never temporarily mutate the global M46 prompt. Install after the released
candidate adapter so `m51.CandidateCaller` captures this wrapped underlying
transport: its candidate path still uses the released M51 instruction wrapper,
while only its review path receives the new M46 instruction. The reviewer
adapter must not claim application when no M51 candidate call occurred.

**Do not wrap `action45.deliver_action` again.** The released adapter's
`installed_source_bound_candidate_prompt_p4()` intentionally requires
that function's exact identity, and an outer wrapper would break both
idempotence and the sandbox preflight. The new adapter may add digest-only
prompt-variant metadata to the existing M45 metrics/trace (which the graph
already displays), but must not claim a new M46 node or alter call accounting, review booleans,
raw review text, or mental-state/factual memory. Concurrent eligible and
ineligible sessions must stay isolated by the existing `ContextVar`.

Do **not** modify these frozen/released files or their contracts:

| file | SHA-256 before this variable |
|---|---|
| `uruha_actionable_help_delivery_m45.py` | `7597c238fc37707ea6c5eba2ef28ede80160430236fb4c2822331e29d7fa6d52` |
| `uruha_goal_progress_delivery_m46.py` | `0d2355404bb7a113f3a772cd2e9442e223c17a8048711a1d161b6725396a4474` |
| `uruha_crosslingual_help_routing_m47.py` | `23bb1df9fad0198375d785ff53fbb614be9586a6f8ec507a707a3ac3245c6e88` |
| `uruha_state_changing_candidates_m51.py` | `b760e49ddc98009ceff572a9c1202cad4dc153880b3744c055b42f9b5cb56806` |
| `uruha_source_neutral_scaffold_m53.py` | `e911faa7927ab4f8e7925bc064b7b49e542caafe4ec0b46eab72c66135a0de0a` |
| `uruha_source_bound_candidate_prompt_p4.py` | `525bd27ff627c459164f3dd399e32009a423507e306cf1ecd775d1c4b4c5875f` |

Allowed new/edit scope **after design review**: one new reviewer adapter;
current `uruha_web_ui_product_p4_first_step_route.py` and
`p4_first_step_route_safe_isolated_product_launcher.py` for install/probe;
focused new/entry tests; pre-generation source/prompt/test SHA release;
result note and `CURRENT_TASK.md`. Do not edit frozen research data,
baseline, old result, production memory, original dirty checkout, or the
unrelated `output/graduate_application_report/`.

## Prospective controls and gates

First use fake transport/zero-model red tests, including eligible Chinese
source, Japanese source, and negative no-task, advice refusal, attributed
quote, protected risk, old English M47 route, mismatched source digest/span,
and simultaneous eligible/ineligible threads. Verify exactly one M46 review
instruction substitution, **zero added calls**, unchanged candidate prompt,
unchanged `action45.deliver_action`/released-adapter installer identity,
M53 rejection of unsupported labels, and old M46 rejection of a fake Chinese
counterfactual even when this adapter is installed. M46's test in which two
allowed mechanism labels disagree must remain passing. Run affected
M45/M46/M47/M51/M53/entry tests, compile, diff, SHA and real isolated sandbox
preflight. This proves wiring only, not output quality.

Before any new model call or Safari Send, fix exact adapter/prompt/test SHA
in a release manifest, commit/push the implementation and new input, and
verify PR #435 exact head. The **first** new developer-authored Safari input
is frozen now, pending route recheck immediately before release:

> 我要整理抽屜裡的幾張收據，還沒決定怎麼分。你會叫我先做什麼？

Read-only classifier currently returns `practical_help_authorized` with one
independent current-User task span. Use one fresh isolated 0700/0600 runtime,
one native Safari Send, and no formal DB. Observe the visible Japanese
reply, source-supported action and visible stopping point, M47→M51→M53→M46
→UTTERANCE after reload, M45-trace metadata about the M46 prompt and unchanged verifier, private
row, model calls/tokens, and user wait. The quality gate needs one concrete,
reversible source-supported first step without invented category/fact; the
latency gate remains **≤20.0 s**. If model still emits Chinese review fields,
M46 must reject (contract safety), and the failure stays recorded. If it
emits Japanese but rejects for another reason, report that exact reason.
If it delivers but takes >20 s, quality and latency receive separate
decisions. No rerun of the exposed handout row, no prompt editing on the
newly exposed receipt case, no weakening M46/M53, and no product-wide or
human-understanding claim from a single development turn.
