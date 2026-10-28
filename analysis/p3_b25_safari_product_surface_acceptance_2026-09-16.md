# P3-B25 Safari product surface acceptance

Date: 2026-09-16

## Outcome

**PASS after one directly observed Web-delivery repair.**

B24 had function, actual product-entry and runtime-graph evidence, but no browser-surface evidence.
B25 launched `uruha_web_ui_product` on localhost with a new temporary Chroma database, adaptive-model
path and conversation-log path. The only seeded episode stated that Taro liked red bowls and the user
preferred black coffee. The production database and normal conversation logs were not opened.

## Observed failure and repair

On the first Safari turn, the chat bubble displayed the correct reply, but Gradio failed before the
final graph payload because the parent directory of an environment-overridden Web log path did not
exist:

`FileNotFoundError: /tmp/.../web/turns.jsonl`

`uruha_web_ui.py` previously created only the repository-default `WEB_LOG_DIR`. It now also creates
the parent directories of the resolved `WEB_LOG_JSONL` and `WEB_LOG_TXT` paths. A subprocess
regression verifies separate nested override directories and confirms that importing the UI creates
only the directories, not log records.

## Safari evidence after repair

The server was restarted with a new isolated workspace and Safari was reloaded. One question was
entered through the real Text Input and Send controls:

- user: `What kind of coffee did I say I prefer?`
- chat bubble: `あんたが好みって言ってたのはブラックコーヒー。`
- page graph: `speaker_qualified_fact_p3` appeared before `selected_plan` and `utterance`;
- expanded node: `resolved_unique_user_preference`, English query, selected speaker `user`, one
  episode candidate, `raw_dialogue_persisted=false`;
- final utterance node showed the same Japanese sentence.

The isolated Web JSONL record independently matched the page:

- `assistant_reply` was the same Japanese sentence;
- `visible_surface_status=matched` and `final_visible_surface_matches_contract=true`;
- `bounded_slow_path_m21.route=deterministic_rule_plan`;
- general planner `model_call_attempted=false` and `model_call_completed=false`;
- cognitive stage total 0.0367 seconds inside a 20-second budget;
- surface delivery used 2 reply chunks, 3 lightweight updates and exactly 1 full graph commit.

Startup performed the existing local Ollama connectivity check. No planner generation, external
deployment, paid call, annotation, or production-database access was performed.

## Verification and cleanup

- 22 focused B24 plus Web-log-path tests passed in 25.01 seconds.
- 131 product Web/surface/memory affected tests passed in 68.02 seconds with 9 dependency warnings.
- `git diff --check` passed.
- The temporary server was stopped, the one Safari tab created for B25 was closed, and the two
  temporary workspaces were moved to Trash. The user's other 41 Safari tabs were left untouched.

Safari's computer-control surface did not provide a screenshot for the application, so the evidence
is the observed accessibility tree plus the matching isolated runtime log. This is browser-surface
delivery evidence for the exposed B24 case, not a fresh holdout, human preference judgment, or proof
of advantage over the direct baseline.
