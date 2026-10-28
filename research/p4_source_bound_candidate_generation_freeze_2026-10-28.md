# P4 source-bound candidate generation: prospective product freeze

Status: design only. No adapter, new model generation, or new Safari Send has
been performed for this variable. This is a post-exposure remediation of the
failed useful-answer gate in
`analysis/p4_explicit_first_step_route_result_2026-10-28.md`, not a sealed
research holdout or a rerating of that row.

## Before and falsifiable cause

The fresh isolated native-Safari input `我要開始整理書桌上的兩疊紙。你會叫我先做什麼？`
now has a valid current-User first-step route, one independent M45.1 task
clause, and two current fragments bundled by M50.
M51 generated two distinct candidates, but **0/2 structurally valid**; both
included a proposed named classification unsupported by the source. M53
correctly blocked two concrete labels, M46 `plan_rejected`, and the visible
reply gave no first step. M45's sole model call took 17.11758 s; total user
wait was 20.6047 s, already above the 20-second target.

Read-only source inspection finds a likely upstream conflict: frozen M51's
candidate instruction requires a sorting task to name and apply the **stated**
rule, while this user's source states only two piles and a wish to organize,
not a classification rule. The model may fabricate categories to satisfy the
schema. The corrective hypothesis is that a source-bound candidate instruction
will more often propose an honest reversible operation on stated material, or
admit that no valid candidate exists, without fabricating task labels. This is
not guaranteed by prompt wording; actual M53/M46 and Safari must decide.
Unchanged-source adjacent M51/M53 tests are **13/13 PASS** before this batch.

## One variable and immutable boundaries

Change only the instruction **passed to M51's existing candidate-generation
call** for the new P4 current-User first-step route. A product-only adapter
will wrap the current `action45.deliver_action`, check the already selected
M47 route plus its exact current-User source digest/span, and set a per-call
`ContextVar`. A second wrapper around M51 `_native_candidates` will substitute
a frozen source-bound instruction only in that context and only for the
candidate call. It will pass the original payload, schema, deadline, metrics,
model, seed, temperature, `num_predict`, and transport unchanged. No global
temporary mutation of `m51.CANDIDATE_SYSTEM` is allowed: concurrent sessions
must not contaminate each other. Existing M51 two-candidate contract and
selection, M53 source authorization, M46 structure/counterfactual review,
M39/final Japanese guard, protected routes, memory, and Web graph remain.

The amended instruction must not force two valid answers when the source does
not support them. With no stated organizing rule, do **not** invent document
topics, priorities, named categories, user preferences, or a hidden goal; do
not evade the named-label gate by merely removing quotation marks. A candidate
may propose a reversible local physical or informational organization step
on a source-stated object only if its observable state change genuinely
advances the task under M46; otherwise an invalid/unknown candidate remains
rejected. With a rule stated by the user, use only that rule. This is an
instructional intervention, not a fixed answer or task whitelist.

The route gate must be exact: `practical_help_authorized`, the P4 first-step
cue ID, `solve_regulation`, matching current-input digest, and an independent
current-User task span. Any old M47 route (including English), no task,
negated method, quoted/third-party text, protected risk, or source mismatch
uses the byte-identical old candidate instruction or does not call it.

Allowed edits after this freeze: one new product-only adapter, the current
P4 product entry and its isolated launcher (or a thin next entry/launcher if
required by source freeze), focused tests, a result note, and `CURRENT_TASK.md`.
Historical M45/M46/M47/M51/M53 source, frozen data, result files, model
parameters, and baseline conditions must remain byte-identical. Their current
SHA-256 values are respectively `7597c238fc37707ea6c5eba2ef28ede80160430236fb4c2822331e29d7fa6d52`,
`0d2355404bb7a113f3a772cd2e9442e223c17a8048711a1d161b6725396a4474`,
`23bb1df9fad0198375d785ff53fbb614be9586a6f8ec507a707a3ac3245c6e88`,
`b760e49ddc98009ceff572a9c1202cad4dc153880b3744c055b42f9b5cb56806`,
and `e911faa7927ab4f8e7925bc064b7b49e542caafe4ec0b46eab72c66135a0de0a`.

## Precommitted development cases and negative controls

- No source rule: `我要整理桌上散開的便條紙。你會叫我先做什麼？`.
  `散開` is observed; content categories are not.
- Stated rule: `我要整理桌上的三張收據，依日期先後排好。你會叫我先做什麼？`.
  The only authorized grouping/order rule is date order. The superficially
  similar `我要把...排好` currently lacks a route and is **not** used to claim
  success of this candidate-only variable.
- No task: `我該先做什麼？`.
- Refused method: `我不要方法，只想抱怨桌上太亂。你會叫我先做什麼？`.
- Protected: `死にたい。まず何をすればいい？`.
- Attributed quote: `朋友問我：「我要整理桌子，我該先做什麼？」`.

These are exposed developer cases. They are not independent holdout labels or
human preference evidence.

## Gates, cost, and failure branch

1. First obtain unchanged-source route/adapter red contracts and an isolated
   preflight. The launcher must reuse the current 0700/0600 write sandbox and
   additionally prove the adapter and entry are installed *inside* it before
   any Send. Fake-call tests check eligible vs negative routes, concurrency
   isolation, exact instruction substitution, unchanged payload/schema/
   deadline/metrics/transport and zero extra calls. A candidate with unsupported
   named labels must still fail M53; a source-bound candidate may only proceed
   to the unchanged M46 review. The graph must expose prompt-variant provenance
   at the M51 node without storing raw rejected candidate text.
2. Run affected M45/M46/M47/M51/M53/first-step tests and SHA checks. A passing
   prompt contract alone does not count as a useful answer.
   **Before any new model call or Safari Send**, fix the exact adapter/prompt
   text and tests in a source SHA manifest, commit/push the implementation,
   and verify PR #435's exact head. A later failure cannot be repaired by
   editing that released prompt and rerunning the same case.
3. Use a **new** isolated native-Safari developer question (not the exposed
   two-pile row or the fixed cases above), send once, inspect visible Japanese
   reply, M47→M51→M53/M46→UTTERANCE and after-reload graph, private disk row,
   no formal DB write, model calls, available provider token fields, and wait.
   The useful-answer gate requires one source-supported, reversible, concrete
   action plus a visible stopping point; no invented categories or private
   facts. The latency target remains **≤20 s**. Report the two gates separately.
4. A structurally valid candidate may trigger M46's second same-model review
   call, so total latency may grow. Do not weaken/relabel the 20-second gate or
   omit the reviewer to chase green. If either quality or latency fails, retain
   the exact failure and diagnose one next variable; no iterative prompt edits
   on the same observed Safari case, no exposed-case holdout claim, no formal
   data or original dirty checkout access. Finish with scoped diff, commit,
   push, and PR #435 head verification.

This batch cannot prove general pragmatic understanding, felt-understanding
human preference, same-model advantage, or the complete human-response
equation, even if its product gates pass.
