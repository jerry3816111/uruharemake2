# P4 Han-only visible Japanese: bounded repair, product still FAIL

Status: **specific language leak blocked** in contracts and one fresh isolated
native-Safari turn; semantic preservation, useful answer, and 20-second target
**FAIL**. This is not general Chinese/Japanese identification or P4 acceptance.
Prospective contract: `research/p4_han_only_visible_japanese_boundary_freeze_2026-10-27.md`.

## Before → after on one exposed development input

The earlier isolated turn asked `桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？`
and visibly returned `整理筆記本`. The selected `core_message_jp` already had
that string; M49 said `not_required`, and the final guard had no rejection.
See `analysis/p4_private_trace_codec_fresh_safari_result_2026-10-27.md`.

The new source changes one decision threshold: a final surface with Han but
no kana is marked `han_only_japanese_unverified`. The existing checker feeds
M49's single source-first repair path and the last guard. It does not alter
global `has_japanese`, planner prompts, memory, codec, or formal data. A
rejected or still-Han-only proposal cannot be published unchanged.

In a **new** private Web/Safari session, the same input produced
`ん、その話もう少し聞かせて。` in the bubble and UTTERANCE node. M49 shows
`semantic_repair_rejected · authority false`. The expanded guard shows
`changed=true`, `repair_action=safe_japanese_persona_fallback`, initial
reason `han_only_japanese_unverified`, and no final rejection. After Safari
reload, USER SIGNAL, M49, guard, and UTTERANCE matched the persisted turn.
The sentence is natural Japanese but **does not answer which first action to
take**. Decoded `post_check.did_reply_cover_focus=false`; M45 practical-help
delivery is `not_applicable`. Do not count this as felt understanding.

## Verification, actual cost, and limits

- Unchanged-source adjacent baseline **33/33**. Two new contracts were red
  before source edit. Final combined guard/M49/candidate/actor/punctuation
  suite **140/140 passed**, 9 dependency/deprecation warnings, 17.72 s.
  Tests include Chinese/English sources, kana-bearing Japanese, a falsely
  successful Han-only authorizer, protected zero-call route, and the
  deliberate false rejection of genuine Japanese `継続`.
- Isolated preflight confirmed owner-only sandbox paths and zero calls before
  send. Safari's one new tab was closed (52→53→52), exact `7896` server
  stopped, no listener/PID 32139 remained. Private runtime evidence stays at
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-us7ztnud`.
  Formal DB and original dirty checkout were outside the sandbox's writable
  root. There is no durable screenshot; UI AX and disk trace are live evidence.
- Fresh private JSONL: **one 285,228-byte** versioned compressed row,
  SHA-256 `636b4b9d8a3f4a840bb263ba15eeeff470552cfbf6e2aa658ff84cbffcebbcee`,
  session `20261027_213202_8a6ae41b`, turn 1, 77 blackboard events.
  Strict production decoder returns the complete logical trace. M49 reports
  **one attempted and completed** source-first model call ending in
  `semantic_authority_rejected`, no surface authority. Token usage for that
  call is unavailable in this row; do not invent it.
- Observed user wait before/after was **10.5494→22.8112 s** (+12.2618 s),
  with the latter missing the 20 s target. Two non-randomized live turns do
  not isolate a causal latency effect; one extra repair call is observed.

## Failure and next variable

The model chose `intent=chat`, `surface_act=plain_reply`, and only a noun-like
core. Self-monitor detected low content density and post-check found focus
uncovered, yet no first-step answer was delivered. M49 could not certify a
source-bound translation; the final guard correctly refused the Han-only
surface and used a generic Japanese fallback. A stricter script firewall
cannot create a sourced practical step. It also conservatively rejects real
all-kanji Japanese; that cost is retained.

Next: independently freeze **source-bound first-action answer delivery** for
explicit one-step requests. Diagnose why this turn stayed plain chat; use a
multilingual developer-case family plus negative controls and require a
concrete, source-supported first step in natural Japanese, no invented
notebook contents, preserved persona/identity, matching graph, bounded call
and latency cost, then a new isolated Safari turn. Do not hardcode this prompt
or count a generic Japanese sentence as PASS. This repair proves nothing
about the full human-response equation, fair LLM advantage, 50-turn memory,
human preference, VRM/tools, or P4-B process containment.
