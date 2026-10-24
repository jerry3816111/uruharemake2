# V2.11 idle-visible proactive suppression — 2026-08-11

## Finding

The observed line was not a random model-only event. The default runtime had an
idle-triggered publication chain:

1. `_autonomous_goal_candidates()` added a `proactive_ping` candidate after
   `AUTONOMOUS_IDLE_SECONDS * 3.4` when no proactive turn was pending.
2. `_build_proactive_turn()` used the fixed surface
   `静かだな。今なにしてんだよ。` for that candidate.
3. The Web timer called `poll_proactive_turn()`, consumed the pending turn, and appended
   it to chat without new user input.
4. The asynchronous event loop also allowed boredom/social-need thresholds accumulated
   during idle time to enqueue a visible `internal_urge` reply.

The same candidate system also had idle-timed unfinished-loop and remembered-topic
followups. Replacing the ping template would therefore not solve the product behavior.

## Minimal policy change

- Added `URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED`, default `false`.
- With the default, elapsed idle time cannot create a visible `proactive_followup`,
  `proactive_share`, or `proactive_ping` pending turn.
- A drive threshold reached only by timer/idle updates no longer enqueues a visible
  `internal_urge`; the timer result records
  `suppressed_idle_visible_proactive=true` for traceability.
- Private background work remains active: open-loop bookkeeping, latent rehearsal,
  consolidation, passive decay, memory/state diffs, and the observatory trace continue.
- Direct user messages are unchanged. The existing proactive builders and Web delivery
  path remain testable behind explicit operator opt-in; no replacement prompt/template
  was added.

## Test evidence

- Targeted proactive/runtime suite:
  `python -m unittest -v test_proactive_dialogue.py test_brain_core_modules.py`
  — **17/17 passed**.
- Scoped V2.11 language/graph/planner suite:
  `python -m unittest -v test_route_logic.py test_user_visible_japanese_guard_v2_11.py test_teacher_memory_observatory_v2_15.py test_planner_self_correction.py`
  — **94/94 passed**.
- Existing surface/planner/proactive/logic regression suite:
  `python -m unittest -v test_rightbrain_model_candidate_gate.py test_planner_self_correction.py test_proactive_dialogue.py test_uruha_logic.py`
  — **80/80 passed**.
- `git diff --check` — passed.

Regression cases cover plain idle, idle with an unfinished open loop and strong short-term
memory, boredom/social drive threshold, explicit opt-in compatibility, one-time delivery,
and Web polling of a deliberately opted-in pending turn.

## Isolated Safari Web evidence

- Session: `20260811_103958_834ecb84`
- Temporary DB: `/tmp/uruha-idle-suppression-web.aJh3x0`
- Test-only timing: `URUHA_AUTONOMOUS_IDLE_SECONDS=1`,
  `URUHA_AUTONOMOUS_MIN_INTERVAL_SECONDS=0.5`
- `URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED` was intentionally omitted, exercising the
  default-off policy.
- A direct Japanese message received one Japanese assistant reply and produced the normal
  input/decision/utterance/writeback graph.
- Background processing reached autonomous tick 6. Server traces showed
  `proactive_turn={}` while latent rehearsal and decay continued.
- Safari status remained `pending=none, last_delivered=none`.
- The number of visible assistant messages was 1 before and 1 after an additional
  15-second wait spanning multiple one-second idle thresholds and Web polls.
- The JSONL log contains exactly one `text` turn for the session and no
  `autonomous_proactive` turn.

## Evidence limit

This is a deterministic policy/regression result plus one accelerated local Safari Web
session. It does not prove every runtime host or externally modified configuration. An
operator can explicitly restore idle-visible behavior with the environment switch, so
deployments must keep the default or omit that switch to retain this behavior.

