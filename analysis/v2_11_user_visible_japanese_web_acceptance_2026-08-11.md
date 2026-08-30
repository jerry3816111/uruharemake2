# V2.11 user-visible Japanese Web acceptance — 2026-08-11

## Scope

This is bounded evidence for the V2.11 user-visible reply boundary. It verifies that
Chinese, English, and Japanese inputs can reach a natural Japanese reply in the local
Safari Web UI, while preserving the existing Uruha persona, scoped memory behavior,
self-identity, runtime trace, and writeback. It is not evidence of the unrun 114-call
fresh evaluation, external deployment, full-pipeline readiness, or production safety.

## Implementation boundary

- Added `uruha_visible_language_guard_v1` after self-monitoring and before reactive
  reply persistence/UI publication; the proactive path uses the same pre-publication
  boundary.
- Localizes audited known terms, rejects foreign-language/script leakage and trace
  artifacts, preserves only narrowly grounded ASCII proper nouns, and fails closed to
  short casual Japanese persona replies.
- Added semantic boundaries for self-identity, unknown favorite-color memory, Chinese
  input echo, malformed punctuation, and ungrounded/orphaned favorite confirmations.
- Canonicalizes `self_intro` to `うちは一ノ瀬うるは。そこは間違えてない。`, so an
  otherwise Japanese but awkward generated lead-in cannot weaken the identity answer.
- Corrected the Web runtime graph's USER SIGNAL source to the actual current turn.
- Prevented non-abusive tired-support prediction shock from routing to abuse pushback;
  separated strawberry preference, favorite-drink recall, and unknown favorite-color
  probes from unrelated laughter/food/memory categories.

## Unit and contract evidence

Interpreter:
`/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python`

1. Scoped V2.11 + graph + planner suite:
   `python -m unittest -v test_route_logic.py test_user_visible_japanese_guard_v2_11.py test_teacher_memory_observatory_v2_15.py test_planner_self_correction.py`
   — **94/94 passed**.
2. Existing surface/planner/proactive regression suite:
   `python -m unittest -v test_rightbrain_model_candidate_gate.py test_planner_self_correction.py test_proactive_dialogue.py test_uruha_logic.py`
   — **77/77 passed**.
3. `git diff --check` — passed with no whitespace errors.

These are unit/contract and regression results. They do not substitute for the real Web
rounds below or for the deferred fresh 114-call evaluation.

## Real Safari Web rounds

Browser URL: `http://127.0.0.1:7860/?node_graph=1`

All acceptance conversations used temporary DB directories outside the normal project
memory store, so their dialogue and writebacks do not contaminate the formal long-term
memory DB.

| Session / isolated DB | Input | Visible reply | Observed graph evidence | Result |
|---|---|---|---|---|
| `20260811_101953_f6fb2736` / `/tmp/uruha-v2-11-showcase.XuUzB5` | `我最喜歡草莓牛奶。` | `ストロベリーミルクが好きなんだな。そこは覚えとく。` | Actual USER SIGNAL; intent `分享喜好`; high-road decision; utterance + visible guard; profile/episode writeback | Chinese input to natural Japanese; preference grounded |
| same | `What is my favorite color? If I never told you, say you don't remember.` | `好きな色はまだ聞いてない。そこは勝手に埋めない。` | `memory_uncertain`; PROFILE still shows only `favorites=草莓牛奶`; high-road; utterance + guard; writeback | Did not reuse drink memory or fabricate a color |
| same | `What is my favorite drink? Don't make it up.` | `いちごミルクって言ってただろ。` | `recall_favorite`; retrieved PROFILE `favorites=草莓牛奶`; selected plan matches; high-road; utterance + guard; writeback | Known memory recalled correctly in Japanese |
| `20260811_102633_e4faa954` / `/tmp/uruha-v2-11-showcase.LtgnOe` | `你是誰？你自己叫什麼名字？請直接回答你是誰。` | `うちは一ノ瀬うるは。そこは間違えてない。` | Actual USER SIGNAL; `self_intro`; high-road; `canonical_self_identity_surface`; utterance; episodic writeback | Explicitly knows she is Uruha; natural, stable identity surface |
| same | `今日は疲れた。少しだけ話して。` | `また疲れてるなら、今日はもう休む方に寄せろって。` | `tired_support`; retrieved prior identity turn; high-road; selected plan; utterance + guard; episodic writeback | Japanese input; supportive but blunt Uruha persona retained |

For every accepted round, Safari's lower runtime node graph was inspected after the
reply completed. The displayed input, retrieved/profile memory where applicable,
intent/route/selected plan, final utterance, and writeback matched the same turn. Empty
retrieval on a fresh session was treated as an accurate state, not a missing claim.

The JSONL trace source is
`web_logs/uruha_web_conversation_log.jsonl`; each accepted reply records
`visible_language_guard.final_rejection_reasons=[]`. Diagnostic rounds that exposed
identity-name confusion, runtime transcript leakage, cross-category favorite reuse,
and an orphaned-particle favorite reply were not counted as acceptance evidence. Each
led to a narrow regression test and was rechecked after repair.

## Remaining limits

- This is local Safari + Gradio + live local Ollama evidence only. No public share,
  external deployment, or original dirty checkout was used.
- The evidence covers a bounded multilingual/persona/memory matrix, not every possible
  wording, proper noun, or model output.
- Favorite color is intentionally treated as unknown because this run did not contain a
  typed color fact; broader typed preference taxonomy remains future work.
- The previously deferred 114-call fresh local-model evaluation remains unrun, so this
  report must not be cited as full V2.11 or production readiness.

