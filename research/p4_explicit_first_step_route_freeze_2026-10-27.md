# P4 explicit first-step response-form route: prospective product freeze

Status: design only; source and new Safari acceptance not yet done. This is a
new product variable following a **failed** useful-answer gate, not a revision
to frozen M47 or a research holdout. Same-model review is not independent
human evidence.

## Before and hypothesis

Two isolated native-Safari rows (original and after the Han-only language
firewall) show the same current User request:
`桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？`
Both selected `intent=chat`, `surface_act=plain_reply`, and
`core_message_jp=整理筆記本`; M45 says `not_applicable`, self-monitor says
`low_speech_content_density`, and post-check says
`did_reply_cover_focus=false`. The second turn's final Japanese fallback
still gave no first step. This is documented in
`analysis/p4_han_only_visible_japanese_boundary_result_2026-10-27.md`.

Read-only M47 classification gives `no_explicit_help_route` for that Chinese
question, `我該先做什麼？`, and Japanese `まず何をすればいい？`; English `What should I do
first?` is authorized. Existing M47 Chinese positive patterns only cover
giving/telling steps or methods; its `OTHER_SOLUTION_REQUESTS` is an atom
deletion guard, not route authorization. Hypothesis: the missing *current-user
first-step response-form certificate* prevents the downstream help policy
from being selected. Opening that route is testable, but does **not** imply
the eventual M45/M46 action will be useful or meet the 20-second latency gate.

## Single variable and frozen boundary

Add a product-only overlay around the already-installed
`m47.classify_help_route_m47`. For a narrowly recognized **current User**
first-step question, return an M47-compatible `practical_help_authorized`
receipt with exact current-text cue offsets/digest, separate nonempty task
span(s), language, unique cue ID, `selected_policy=solve_regulation`, and
explicit `raw_dialogue_persisted=false`, `long_term_memory_write=false`.
Otherwise return the old M47 result unchanged. The wrapper must never
override old M47 `practical_help_forbidden` or a positive old route, protected
risk, an attributed/quoted example, a third-person request, or an ungrounded
first-step question with no separate current User task. No inference of
private intent. No hard-coded notebook answer or new reply template. Keep
`uruha_crosslingual_help_routing_m47.py` and its SHA-locked Web/test/results
byte-identical; existing M47 classifier, atom assignment, materializer,
graph and M45/M46 decision chain remain the implementation of record.

Allowed new files: one small route overlay, new current-product entry importing
the SHA-locked status-truth entry then installing the overlay, a thin isolated
launcher reusing status-truth preflight/sandbox, focused new tests, before/result
notes, and `CURRENT_TASK.md`. No changes to planner prompts, model, output
guard, memory, formal data, baselines, or old freeze thresholds. If runtime
proves overlay-only insufficient, retain failure and re-freeze a different
single handoff variable instead of silently broadening this batch.

## Precommitted developer cases and controls

Authorizing family (each has an independent task clause):

- ZH: `桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？`
- ZH variant: `我要開始寫報告，現在還是空白的。我該先做什麼？`
- JA: `ノートを整理したい。まず何をすればいい？`
- EN unchanged route control: `There are two notebooks. What should I do first?`

Fail-closed controls: `我該先做什麼？` without a task; `先做什麼只是標題。`;
`朋友問我：「我該先做什麼？」`; `朋友問我該先做什麼。`;
`友達が「まず何をすればいい？」と言った。`;
`不要給我方法，我只是在抱怨。`; `我不想要建議。報告還是空白的。我該先做什麼？`;
`死にたい。まず何をすればいい？`. For a negative-then-positive
correction, old M47 precedence remains authoritative; this batch may
conservatively abstain, but must not falsely authorize a forbidden route.
These are exposed developer examples, **not** holdout or human labels.

## Acceptance sequence and cost

1. Verify current HEAD's exact M47 classifier outputs and source hashes (done
   read-only), then obtain unchanged-source adjacent test baseline. Add red
   tests for the new entry/overlay; keep old M47 frozen test unmodified. The
   new isolated launcher must reuse old preflight **and additionally** probe
   the new entry and installed overlay inside the sandbox before any model
   or Safari operation; the old entry probe alone is insufficient.
2. Unit/contract gate: 3/3 new ZH/JA positives get exact source-bound route
   receipt; all listed negatives preserve old route or fail closed; old EN
   route is unchanged; no raw dialogue in receipt, no long-term mental-fact
   write, no new model call in the classifier. Check M47 materialization and
   graph route/delivery distinction. Run affected adjacent suites.
3. Fresh isolated native Safari using **a new**, non-holdout task question:
   compare old-vs-new route only where feasible without exposing formal data.
   Inspect actual bubble, M47/M45/M46/UTTERANCE and after-reload graph, private
   row, permission boundary, and exact 20-second target. A route PASS alone
   is not a useful-answer PASS: the final natural Japanese reply must give one
   concrete, reversible, source-supported first step and a stopping point,
   without inventing task details. A source-aware review is a proxy, not a
   human rating. Record model calls, available provider tokens, latency and
   disk bytes; unavailable metrics remain unavailable.
4. Preserve failed outputs, analyze cost/false positives, scoped diff review,
   commit/push existing branch, verify PR #435 exact head. If final answer or
   latency fails, leave product partial and freeze the next genuinely distinct
   variable. No P4-B real runner, formal DB, or long-conversation inference.
