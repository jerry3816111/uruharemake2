"""Zero-model contracts for the opt-in quoted rewrite action."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import uruha_explicit_rewrite_action_p4 as rewrite


DATASET = Path(__file__).with_name("datasets") / "p4_explicit_rewrite_action_fresh_probe_2026-10-20.json"


def _case_users():
    return {row["id"]: row["user"] for row in json.loads(DATASET.read_text(encoding="utf-8"))["cases"]}


@pytest.mark.parametrize("case_id", ["T1", "T2", "T3"])
def test_frozen_positive_scope_is_current_turn_quote(case_id):
    scope = rewrite.classify_explicit_rewrite_action_p4(_case_users()[case_id])
    assert scope["eligible"] is True
    assert scope["source_role"] == "current_user_quoted_object_only"
    assert scope["source_sha256"] == rewrite._sha(scope["_source"])


@pytest.mark.parametrize("case_id", ["T4", "T5", "T6", "T7", "T8"])
def test_frozen_negative_and_controls_are_not_admitted(case_id):
    assert rewrite.classify_explicit_rewrite_action_p4(_case_users()[case_id])["eligible"] is False


@pytest.mark.parametrize("user", [
    "「分かった」を柔らかく言い換えて。『別の文』も。",
    "「分かったを柔らかく言い換えて。",
    "「パスワードを書いた」を柔らかく言い換えて。",
    "「殺して」を柔らかく言い換えて。",
    "「分かった」を英訳して柔らかく言い換えて。",
    "友達が「分かった」と言った。柔らかく言い換えたらしい。",
    "「分かった」の意味を柔らかく言い換えて。",
])
def test_ambiguous_unbalanced_reported_sensitive_or_definition_fails_closed(user):
    assert rewrite.classify_explicit_rewrite_action_p4(user)["eligible"] is False


@pytest.mark.parametrize("phrase,source,reason", [
    ("承知しました。", "了解です", "formal_register"),
    ("了解です", "了解です", "empty_long_or_source_copy"),
    ("分かったよ。明日行く。", "了解です", "new_future_promise"),
    ("分かったよ、病院だから。", "了解です", "new_reason"),
    ("3時に分かったよ。", "了解です", "new_number"),
    ("I understand", "了解です", "not_japanese_only"),
    ("「分かったよ」", "了解です", "unsafe_phrase_shape"),
])
def test_candidate_shape_rejects_mechanically_detectable_drifts(phrase, source, reason):
    assert rewrite._validate_phrase(phrase, source) == (False, reason)


def test_fake_model_one_call_receipts_usage_and_phrase_not_source():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content='{"rewrite_jp":"分かったよ。"}'))],
            usage=SimpleNamespace(prompt_tokens=33, completion_tokens=11),
        )

    fake = SimpleNamespace(client_logic=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), compute_ledger=None)
    phrase, receipt = rewrite._generate(fake, "かしこまりました", "友達に返す感じで柔らかく言い換えて")
    assert phrase == "分かったよ。"
    assert len(calls) == 1
    assert (calls[0]["model"], calls[0]["temperature"], calls[0]["max_tokens"], calls[0]["timeout"]) == ("qwen2.5:7b", 0, 80, 6.0)
    assert receipt["attempted_calls"] == receipt["completed_calls"] == 1
    assert (receipt["prompt_tokens"], receipt["completion_tokens"]) == (33, 11)
    assert isinstance(receipt["call_latency_seconds"], float)
    assert receipt["model_phrase_sha256"] == rewrite._sha(phrase)


def test_fake_model_malformed_or_exception_never_commits_candidate():
    def reply(content):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=content))], usage=None)

    for responder in (lambda **_: reply("not json"), lambda **_: reply('{"rewrite_jp":"承知しました"}'), lambda **_: (_ for _ in ()).throw(TimeoutError())):
        fake = SimpleNamespace(client_logic=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=responder))), compute_ledger=None)
        phrase, receipt = rewrite._generate(fake, "了解です", "柔らかく言い換えて")
        assert phrase is None
        assert receipt["attempted_calls"] == 1
        assert receipt["prompt_tokens"] == "unavailable"


def _fake_base_emit(self, event, tick):
    logic = tick["logic"]
    original = deepcopy(self.runtime.blackboard)
    candidate = logic["core_message_jp"]
    visible = self.override_visible or candidate
    self.right_brain.history.append({"role": "assistant", "content": candidate})
    logic["visible_language_guard"] = {"final_reply": candidate}
    logic["frame_preserving_visible_repair_p4"] = {"changed": bool(self.override_visible)}
    trace = {
        "cycle_index": 1,
        "blackboard": original + [{"stage": "surface", "label": "utterance", "payload": {"reply": visible}}],
        "selected_plan": {"core_message_jp": candidate},
    }
    self.runtime.turn_traces = [deepcopy(trace)]
    return {"reply": visible, "logic": logic, "runtime_trace": trace,
            "runtime_state": {"blackboard": deepcopy(trace["blackboard"]), "recent_turn_traces": [deepcopy(trace)]}}


def _fake_brain(override_visible=""):
    original_row = {"stage": "select", "label": "selected_plan", "payload": {"core_message_jp": "承知しました"}}
    return SimpleNamespace(runtime=SimpleNamespace(blackboard=[original_row], turn_traces=[]),
                           right_brain=SimpleNamespace(history=[]), override_visible=override_visible)


def _fake_tick():
    return {"logic": {"core_message_jp": "承知しました", "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                      "constraints": {"max_chars": 28}}, "route_info": {"route": "high_road"}}


def test_typed_override_is_single_candidate_and_graph_shadow_with_no_raw_source():
    brain = _fake_brain()
    tick = _fake_tick()
    event = {"user_input": _case_users()["T1"]}
    with patch.object(rewrite, "_ORIGINAL_EMIT", _fake_base_emit), patch.object(rewrite, "_generate", return_value=("分かったよ。", {"attempted_calls": 1, "completed_calls": 1})), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, event, tick)
    receipt = result["logic"][rewrite.LABEL]
    assert result["reply"] == "「分かったよ。」がいいかな。"
    assert receipt["status"] == "candidate_committed"
    assert receipt["candidate_equals_final"] is True
    assert receipt["candidate_equals_speak"] is True
    assert receipt["candidate_equals_final_guard"] is True
    assert receipt["graph_utterance_equals_final"] is True
    assert receipt["model_phrase_sha256"] != receipt["committed_visible_candidate_sha256"]
    assert result["runtime_trace"]["selected_plan"]["typed_rewrite_override"]["source"] == "current_turn_quote"
    shadow = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == "selected_plan")
    assert shadow["payload"]["typed_rewrite_original_plan_role"].startswith("shadowed")
    assert shadow["payload"]["core_message_jp"] == "承知しました"
    assert result["runtime_state"]["recent_turn_traces"][-1][rewrite.LABEL]["status"] == "candidate_committed"
    assert "かしこまりました" not in json.dumps(receipt, ensure_ascii=False)


def test_downstream_override_is_recorded_as_failure_not_hidden_by_reply_write():
    brain = _fake_brain(override_visible="うん")
    tick = _fake_tick()
    with patch.object(rewrite, "_ORIGINAL_EMIT", _fake_base_emit), patch.object(rewrite, "_generate", return_value=("分かったよ。", {"attempted_calls": 1})), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": _case_users()["T1"]}, tick)
    assert result["reply"] == "うん"
    assert result["logic"][rewrite.LABEL]["status"] == "downstream_surface_mismatch"


def test_flag_off_keeps_original_route_without_new_model_call():
    brain = _fake_brain()
    tick = _fake_tick()
    with patch.object(rewrite, "_ORIGINAL_EMIT", _fake_base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "0"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": _case_users()["T1"]}, tick)
    assert result["reply"] == "承知しました"
    assert rewrite.LABEL not in result["logic"]


def test_protected_route_never_calls_rewriter_even_for_eligible_text():
    brain = _fake_brain()
    tick = _fake_tick()
    tick["route_info"]["route"] = "low_road"
    with patch.object(rewrite, "_ORIGINAL_EMIT", _fake_base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": _case_users()["T1"]}, tick)
    assert result["reply"] == "承知しました"
    assert rewrite.LABEL not in result["logic"]


def test_rejected_model_candidate_keeps_original_route_with_cost_receipt():
    brain = _fake_brain()
    tick = _fake_tick()
    with patch.object(rewrite, "_ORIGINAL_EMIT", _fake_base_emit), patch.object(rewrite, "_generate", return_value=(None, {"attempted_calls": 1, "completed_calls": 1, "status": "formal_register"})), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": _case_users()["T1"]}, tick)
    assert result["reply"] == "承知しました"
    assert result["logic"]["core_message_jp"] == "承知しました"
    assert result["logic"][rewrite.LABEL]["status"] == "model_candidate_rejected_original_route_kept"
    assert result["logic"][rewrite.LABEL]["model_call"]["attempted_calls"] == 1


def test_web_entry_and_controller_resolve_without_model_or_server():
    script = """
import ast
from pathlib import Path
import uruha_web_ui_product_p4_explicit_rewrite_action as entry
import p4_explicit_rewrite_action_detached_control as controller
assert controller.ENTRYPOINT.name == 'uruha_web_ui_product_p4_explicit_rewrite_action.py'
tree = ast.parse(Path(entry.__file__).read_text(encoding='utf-8'))
def resolve(node):
    if isinstance(node, ast.Name): return vars(entry)[node.id]
    if isinstance(node, ast.Attribute): return getattr(resolve(node.value), node.attr)
    raise AssertionError(type(node).__name__)
targets = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)
           and isinstance(node.func, ast.Attribute)
           and (node.func.attr.startswith('install_') or node.func.attr == 'build_demo')]
assert all(callable(resolve(target)) for target in targets)
assert len(targets) == 20, len(targets)
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
