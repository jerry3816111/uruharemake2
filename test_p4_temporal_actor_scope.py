"""Developer fixtures for a new opt-in actor/scope product layer.

These are not independent holdout or Safari evidence.  The earlier exposed
schedule sentence is deliberately absent from every passing case here.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_temporal_actor_scope_p4 as actor_scope
from uruha_memory_observatory import _graph_signal


ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    ("text", "actor", "action", "authorized"),
    [
        (
            "先に日程を見てから連絡してもいい？",
            "user_self", "defer_reply_after_self_check", False,
        ),
        (
            "Can I check my calendar first and reply later?",
            "user_self", "defer_reply_after_self_check", False,
        ),
        (
            "我先確認時間再回覆你，可以嗎？",
            "user_self", "defer_reply_after_self_check", False,
        ),
        (
            "先に何がほしいか聞いて",
            "assistant", "ask_response_form_first", True,
        ),
        (
            "Please ask me first what kind of reply I want.",
            "assistant", "ask_response_form_first", True,
        ),
        (
            "你先問我想要什麼回覆。",
            "assistant", "ask_response_form_first", True,
        ),
        (
            "友達が「先に確認して」と言ってた。",
            "third_party", "unresolved", False,
        ),
        (
            "私は「先に確認して」と言った。",
            "unknown", "unresolved", False,
        ),
        (
            "「先に確認して」と言ってくれる？",
            "unknown", "unresolved", False,
        ),
        (
            "先に友達が予定を見てから返事してもいい？",
            "unknown", "unresolved", False,
        ),
        (
            "友達も先に予定を確認してから返事してもいい？",
            "unknown", "unresolved", False,
        ),
        (
            "まず彼女に何がほしいか聞いて。",
            "unknown", "unresolved", False,
        ),
        (
            "先生に返し方を先に聞いて。",
            "unknown", "unresolved", False,
        ),
        (
            "先に何がほしいか聞いてほしくない。",
            "unknown", "unresolved", False,
        ),
        (
            "先に確認して。",
            "unknown", "unresolved", False,
        ),
    ],
)
def test_typed_temporal_actor_scope_stays_source_bounded(
    text, actor, action, authorized
):
    row = actor_scope.classify_temporal_actor_scope_p4(text)
    assert row["actor"] == actor
    assert row["action"] == action
    assert row["assistant_request_authorized"] is authorized
    assert row["raw_dialogue_persisted"] is False
    assert row["private_state_truth_claimed"] is False
    assert text not in json.dumps(row, ensure_ascii=False)
    assert _graph_signal(row) != f"{len(row)} fields"


def test_separate_assistant_clause_survives_self_defer_and_reported_quote():
    mixed = actor_scope.classify_temporal_actor_scope_p4(
        "先に日程を見てから連絡してもいい？ それと、先に何がほしいか聞いて。"
    )
    quoted = actor_scope.classify_temporal_actor_scope_p4(
        "友達が「先に確認して」と言った。あなたは先に何がほしいか聞いて。"
    )
    quoted_comma = actor_scope.classify_temporal_actor_scope_p4(
        "友達が「先に確認して」と言った、あなたは先に何がほしいか聞いて。"
    )
    assert mixed["self_defer_observed"] is True
    assert mixed["actor"] == "assistant"
    assert mixed["assistant_request_authorized"] is True
    assert mixed["temporal_relation"] == "assistant_question_before_reply"
    assert quoted["source_kind"] == "mixed_direct_and_reported"
    assert quoted["assistant_request_authorized"] is True
    assert quoted_comma["source_kind"] == "mixed_direct_and_reported"
    assert quoted_comma["assistant_request_authorized"] is True
    assert quoted_comma["additional_clause_observed"] is True
    quoted_comma_gated = actor_scope.gate_base_explicit_request_p4(
        "友達が「先に確認して」と言った、あなたは先に何がほしいか聞いて。",
        adaptive.classify_explicit_desired_response_m25,
    )
    assert quoted_comma_gated["selected_policy"] == "calibrate_need"


def test_base_m25_clarifier_authority_requires_assistant_actor():
    original = adaptive.classify_explicit_desired_response_m25
    cases = {
        "先に日程を見てから連絡してもいい？": None,
        "友達が「先に確認して」と言ってた。": None,
        "先に確認して。": None,
        "先に何がほしいか聞いて": "calibrate_need",
        "Please ask me first what kind of reply I want.": "calibrate_need",
        "你先問我想要什麼回覆。": "calibrate_need",
    }
    for text, policy in cases.items():
        gated = actor_scope.gate_base_explicit_request_p4(text, original)
        assert gated["selected_policy"] == policy
        assert gated[actor_scope.LABEL]["input_digest"]
        if policy is None:
            assert gated["authority"] == "not_applicable"
    reported = actor_scope.gate_base_explicit_request_p4(
        "友達が「先に確認して」と言ってた。", original
    )
    assert reported[actor_scope.LABEL]["action"] == "reported_check_instruction"
    protected = actor_scope.gate_base_explicit_request_p4(
        "死にたい。先に何がほしいか聞いて", original
    )
    assert protected["protected_risk_cue"] is True
    assert protected["authority"] == "protected_risk_route"
    negated = actor_scope.gate_base_explicit_request_p4(
        "質問しないで、先に確認して。", original
    )
    assert "calibrate_need" in negated["negated_policies"]
    assert negated["selected_policy"] is None


def test_full_product_hook_keeps_classifier_plan_graph_and_reply_consistent():
    # Run the opt-in global monkey patches in a child process.  They must not
    # leak into unrelated pytest modules or released frozen entries.
    script = r'''
import json
import uruha_web_ui_product_p4_temporal_actor_scope as entry
import uruha_temporal_actor_scope_p4 as gate
import uruha_adaptive_person_model as adaptive
import uruha_executed_action_outcome_closure_p4 as p4_at
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph

entry.install_current_statement_source_authority_p4()
entry.install_third_party_question_evidence_p4()
entry.install_selected_offer_action_surface_fidelity_p4()
entry.install_reported_offer_source_scope_p4()
entry.install_hash_prefix_provenance_gate_p4()
entry.install_hash_prefix_event_transport_p4()
assert entry.install_temporal_actor_scope_p4() is True
assert entry.install_temporal_actor_scope_p4() is False
assert entry.RUNTIME is entry._prior.RUNTIME
rows = []
for text in (
    "先に日程を見てから連絡してもいい？",
    "先に何がほしいか聞いて",
    "友達が「先に確認して」と言ってた。",
    "Can I check my calendar first and reply later?",
    "你先問我想要什麼回覆。",
    "我先確認時間再回覆你，可以嗎？",
    "先に確認して。",
):
    base = p4_at._ORIGINAL_CLASSIFIER_P4_AT(text)
    projected = adaptive.classify_explicit_desired_response_m25(text)
    result = _IsolatedContractBrain().run_turn_debug(text)
    trace = result["runtime_trace"]
    actor = result["logic"][gate.LABEL]
    graph = collect_cognitive_graph(result)
    labels = [node["label"] for node in graph["nodes"]]
    blackboard = trace["blackboard"]
    rows.append({
        "actor": actor["actor"],
        "base_policy": base["selected_policy"],
        "projected_policy": projected["selected_policy"],
        "selected_policy": (
            (result["logic"].get("desired_response_decision_m18") or {})
            .get("selected") or {}
        ).get("policy_id"),
        "selected_action": actor["selected_surface_act"],
        "surface_status": actor["surface_status"],
        "reply": result["reply"],
        "selected_core": trace["selected_plan"]["core_message_jp"],
        "utterance": next(
            row["payload"]["reply"] for row in blackboard
            if row["label"] == "utterance"
        ),
        "graph_actor_count": labels.count(gate.LABEL),
        "graph_actor_signal": next(
            node["signal"] for node in graph["nodes"]
            if node["label"] == gate.LABEL
        ),
        "m25_after_actor": (
            labels.index(gate.LABEL) < labels.index("explicit_desired_response_m25")
        ),
    })
print(json.dumps(rows, ensure_ascii=False))
'''
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    rows = json.loads(completed.stdout.splitlines()[-1])
    assert len(rows) == 7
    assert [row["actor"] for row in rows] == [
        "user_self", "assistant", "third_party",
        "user_self", "assistant", "user_self", "unknown",
    ]
    for row in rows:
        assert row["base_policy"] == row["projected_policy"]
        assert row["reply"] == row["selected_core"] == row["utterance"]
        assert row["graph_actor_count"] == 1
        assert row["m25_after_actor"] is True
        assert "fields" not in row["graph_actor_signal"]
        assert not any("A" <= char <= "Z" for char in row["reply"])
    for index in (0, 3, 5):
        assert rows[index]["selected_action"] == "ack_user_self_deferred_reply_p4"
        assert rows[index]["surface_status"] == "self_defer_ack_visible"
        assert rows[index]["selected_policy"] is None
        assert "そのあと" in rows[index]["reply"]
    for index in (1, 4):
        assert rows[index]["selected_policy"] == "calibrate_need"
        assert rows[index]["surface_status"] == "assistant_question_visible"
        assert "？" in rows[index]["reply"]
    assert rows[2]["selected_policy"] is None
    assert rows[2]["selected_action"] == "ack_reported_check_instruction_p4"
    assert rows[2]["surface_status"] == "reported_instruction_ack_visible"
    assert "そう言ってた" in rows[2]["reply"]
    assert "今ほしい返し方" not in rows[2]["reply"]
    assert rows[6]["selected_policy"] is None
    assert "今ほしい返し方" not in rows[6]["reply"]


def test_negative_request_and_independent_task_do_not_gain_new_authority():
    original = adaptive.classify_explicit_desired_response_m25
    for text in (
        "Don't ask me first what kind of reply I want.",
        "先に何がほしいか聞いてほしくない。",
        "まず彼女に何がほしいか聞いて。",
        "先生に返し方を先に聞いて。",
    ):
        gated = actor_scope.gate_base_explicit_request_p4(text, original)
        assert gated[actor_scope.LABEL]["assistant_request_authorized"] is False
        assert gated["selected_policy"] != "calibrate_need"
        assert "已授權" not in _graph_signal(gated[actor_scope.LABEL])

    self_with_task = actor_scope.classify_temporal_actor_scope_p4(
        "先に日程を見てから連絡してもいい？ あと、先生宛のメール文を作って。"
    )
    assert self_with_task["additional_clause_observed"] is True
    comma_task = actor_scope.classify_temporal_actor_scope_p4(
        "先に日程を見てから連絡してもいい、あと先生宛のメール文を作って。"
    )
    assert comma_task["additional_clause_observed"] is True
    decision = {
        "state": {"explicit_desired_response_m25": {actor_scope.LABEL: self_with_task}},
        "selected": None,
    }

    def unchanged_apply(plan, _decision):
        return dict(plan), {}

    task_plan = {
        "intent": "draft_email", "scene": "casual",
        "core_message_jp": "先生へのメールを一緒に作るよ。",
    }
    task_result, _ = actor_scope.apply_temporal_actor_scope_to_plan_p4(
        task_plan, decision, unchanged_apply
    )
    assert task_result["intent"] == "draft_email"
    assert task_result["core_message_jp"] == task_plan["core_message_jp"]
    chat_result, _ = actor_scope.apply_temporal_actor_scope_to_plan_p4(
        {**task_plan, "intent": "chat"}, decision, unchanged_apply
    )
    assert "surface_act" not in chat_result


def test_visible_status_requires_actual_selected_action_and_exact_utterance():
    scope = actor_scope.classify_temporal_actor_scope_p4(
        "先に日程を見てから連絡してもいい？"
    )
    result = {
        "reply": "いや、先に確認しないで。返事はそのあとで。",
        "logic": {actor_scope.LABEL: scope},
        "runtime_trace": {
            "selected_plan": {"surface_act": "ack_user_self_deferred_reply_p4"},
            "blackboard": [],
        },
    }
    checked = actor_scope.materialize_temporal_actor_scope_p4(result)
    assert checked["logic"][actor_scope.LABEL]["surface_status"] == (
        "self_defer_ack_missing"
    )
    assistant_scope = actor_scope.classify_temporal_actor_scope_p4(
        "先に何がほしいか聞いて"
    )
    assistant_result = {
        "reply": "別の質問でいい？",
        "logic": {actor_scope.LABEL: assistant_scope},
        "runtime_trace": {
            "selected_plan": {"core_message_jp": "別の質問でいい？"},
            "blackboard": [],
        },
    }
    checked_assistant = actor_scope.materialize_temporal_actor_scope_p4(
        assistant_result
    )
    assert checked_assistant["logic"][actor_scope.LABEL]["surface_status"] == (
        "assistant_question_missing"
    )


def test_new_entry_and_controller_reuse_existing_gradio_and_private_launcher():
    entry = (ROOT / "uruha_web_ui_product_p4_temporal_actor_scope.py").read_text(
        encoding="utf-8"
    )
    controller = (ROOT / "p4_temporal_actor_scope_detached_control.py").read_text(
        encoding="utf-8"
    )
    assert "import uruha_web_ui_product_p4_hash_prefix_transport as _prior" in entry
    assert "demo = _base.build_demo()" in entry
    assert "server_name=_base.WEB_SERVER_NAME" in entry
    assert "install_temporal_actor_scope_p4()" in entry
    assert "p4_preference_fallback_detached_control as base_controller" in controller
    assert "uruha_web_ui_product_p4_temporal_actor_scope.py" in controller
