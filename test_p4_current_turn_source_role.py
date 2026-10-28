"""Zero-model checks for bounded current-turn source roles and safe admission."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import uruha_current_turn_source_role_p4 as roles
import uruha_explicit_rewrite_action_p4 as rewrite
from uruha_memory_observatory import collect_cognitive_graph


CASES = json.loads((Path(__file__).parent / "datasets" / "p4_current_turn_source_role_contract_2026-10-20.json").read_text(encoding="utf-8"))["cases"]
BY_ID = {case["id"]: case for case in CASES}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_frozen_cross_act_contract_and_raw_span_reconstruction(case):
    user = case["user"]
    certificate = roles.classify_current_turn_source_role_p4(user, cycle_index=7)
    assert (certificate["act"], certificate["quote_role"], certificate["rewrite_eligible"]) == (
        case["act"], case["quote_role"], case["rewrite_eligible"]
    )
    assert certificate["raw_input_sha256"] == hashlib.sha256(user.encode("utf-8")).hexdigest()
    assert certificate["cycle_index"] == 7
    assert certificate["authority_transfer_permitted"] is False
    if certificate["quote_role"] != "none":
        start, end = certificate["quote_content_span_raw"]
        assert user[start:end]
        assert hashlib.sha256(user[start:end].encode("utf-8")).hexdigest() == certificate["quote_raw_sha256"]
        left, right = certificate["outside_spans_raw"]
        assert left == [0, certificate["quote_span_raw"][0]]
        assert right == [certificate["quote_span_raw"][1], len(user)]
        outside_exact = user[left[0]:left[1]] + user[right[0]:right[1]]
        assert hashlib.sha256(outside_exact.encode("utf-8")).hexdigest() == certificate["outside_raw_sha256"]
    public = roles.public_source_role_certificate_p4(certificate)
    serialized = json.dumps(public, ensure_ascii=False)
    assert user not in serialized
    assert "_quote_nfkc" not in public and "_outside_nfkc" not in public


def test_raw_and_nfkc_are_separate_and_new_before_counterexamples_reverse():
    fullwidth = roles.classify_current_turn_source_role_p4(BY_ID["U1"]["user"])
    assert fullwidth["raw_input_sha256"] != fullwidth["normalized_input_sha256"]
    assert fullwidth["quote_raw_sha256"] != fullwidth["quote_normalized_sha256"]
    assert rewrite.classify_explicit_rewrite_action_p4(BY_ID["M1"]["user"])["eligible"] is False
    assert rewrite.classify_explicit_rewrite_action_p4(BY_ID["R4"]["user"])["eligible"] is True


def test_unquoted_instruction_is_not_mislabeled_as_ordinary_chat():
    instruction = roles.classify_current_turn_source_role_p4("この話を柔らかく言い換えて。")
    sensitive = roles.classify_current_turn_source_role_p4("認証コードの保管場所を教えて。")
    assert (instruction["act"], instruction["rewrite_eligible"]) == ("unquoted_request", False)
    assert (sensitive["act"], sensitive["rewrite_eligible"]) == ("protected", False)


@pytest.mark.parametrize("user", [
    "「荷物は２日遅れている」は柔らかく言い換えないで。",
    "「荷物は２日遅れている」は柔らかく言い換えた例だよ。",
    "友達が「まだ予約していない」を柔らかく言い換えてって頼んだ。",
    "「今日は行けない」を柔らかく言い換えて。あとで父に連絡して。",
    "「今日は行けない」を柔らかく言い換えて、今夜どうしたらいい？",
    "「今日は行けない」を柔らかく言い換えて。\n今夜は迎えに来て。",
    'Please rewrite “I cannot attend” in softer, casual Japanese and book a taxi.',
    'Please rewrite “I cannot attend” in softer, casual Japanese and pay the bill.',
    'Please rewrite “I cannot attend” in softer, casual Japanese and cancel my meeting.',
    "「今日は行けない」を明日の予定を確認して柔らかく言い換えて。",
])
def test_postfreeze_adversarial_non_commands_or_mixed_acts_abstain(user):
    assert roles.classify_current_turn_source_role_p4(user)["rewrite_eligible"] is False


@pytest.mark.parametrize("user", [
    "「遅れる」を自然で柔らかく言い換えて。",
    "「遅れる」を友達に自然に聞こえるよう柔らかく言い換えて。",
])
def test_style_modifier_does_not_become_second_act(user):
    assert roles.classify_current_turn_source_role_p4(user)["act"] == "single_rewrite"


@pytest.mark.parametrize("user", [
    "「予約した」を言い換えて。『別件』も。",
    "「予約したを柔らかく言い換えて。",
    "『予約した』を柔らかく言い換えて。",
])
def test_unknown_or_malformed_quote_never_gains_rewrite_authority(user):
    certificate = roles.classify_current_turn_source_role_p4(user)
    assert certificate["rewrite_eligible"] is False
    assert certificate["authority_transfer_permitted"] is False


def test_same_text_is_not_same_event_or_m32_parent_and_answer_does_not_decide():
    user = BY_ID["R4"]["user"]
    first = roles.classify_current_turn_source_role_p4(user, cycle_index=3)
    later = roles.classify_current_turn_source_role_p4(user, cycle_index=4)
    raw16 = first["raw_input_sha256"][:16]
    logic = {
        "literal_topic_projection_m29": {"input_digest": raw16},
        "semantic_authorization_m31": {"input_digest": raw16, "surface_authority": True, "response_jp": "A"},
        "semantic_commit_repair_m32": {"surface_authority": True, "source_m31_status": "semantically_authorized"},
    }
    audit1 = roles.audit_current_turn_lineage_p4(first, logic)
    audit2 = roles.audit_current_turn_lineage_p4(later, logic)
    assert audit1["m29_raw_digest_matches"] and audit1["m31_raw_digest_matches"]
    assert audit1["status"] == "same_text_but_event_and_parent_lineage_unproven"
    assert audit2["status"] == audit1["status"]
    assert audit1["authority_transfer_permitted"] is audit2["authority_transfer_permitted"] is False
    logic["semantic_authorization_m31"]["response_jp"] = "unrelated answer content"
    assert roles.audit_current_turn_lineage_p4(first, logic) == audit1
    logic["semantic_authorization_m31"]["input_digest"] = "0" * 16
    mismatch = roles.audit_current_turn_lineage_p4(first, logic)
    assert mismatch["m31_raw_digest_matches"] is False
    assert mismatch["authority_transfer_permitted"] is False


def _fake_brain():
    return SimpleNamespace(
        runtime=SimpleNamespace(cycle_index=7, blackboard=[], turn_traces=[]),
        right_brain=SimpleNamespace(history=[]),
    )


def _base_emit(brain, event, tick):
    logic = tick["logic"]
    reply = str(logic["core_message_jp"])
    brain.right_brain.history.append({"role": "assistant", "content": reply})
    logic["visible_language_guard"] = {"final_reply": reply}
    logic["frame_preserving_visible_repair_p4"] = {"changed": False}
    trace = {"cycle_index": 7, "blackboard": deepcopy(brain.runtime.blackboard) + [
        {"stage": "select", "label": "selected_plan", "payload": {"core_message_jp": reply}},
        {"stage": "surface", "label": "utterance", "payload": {"reply": reply}},
    ], "selected_plan": {}}
    brain.runtime.turn_traces = [deepcopy(trace)]
    return {"reply": reply, "logic": logic, "runtime_trace": trace,
            "runtime_state": {"blackboard": deepcopy(trace["blackboard"]), "recent_turn_traces": [deepcopy(trace)]}}


def _tick(route="high_road", **logic_extra):
    return {"logic": {"core_message_jp": "うん。", "surface_act": "plain_reply", "intent": "chat", "scene": "casual", **logic_extra},
            "route_info": {"route": route}}


def test_mixed_request_is_visible_as_mixed_but_never_calls_rewrite_model():
    brain = _fake_brain()
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": BY_ID["M1"]["user"]}, _tick())
    assert result["reply"] == "うん。"
    contract = result["logic"][roles.LABEL]
    assert contract["act"] == "mixed_request"
    assert contract["action_admission"] == "not_a_single_rewrite_request"
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels == ["selected_plan", roles.LABEL, "utterance"]
    assert result["runtime_state"]["recent_turn_traces"][-1][roles.LABEL] == contract
    assert BY_ID["M1"]["user"] not in json.dumps(contract, ensure_ascii=False)


def test_audience_is_not_reported_speech_and_candidate_handoff_graph_is_connected():
    brain = _fake_brain()
    tick = _tick()
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", return_value=("まだ予約してないんだ。", {"attempted_calls": 1, "completed_calls": 1})), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": BY_ID["R4"]["user"]}, tick)
    assert result["logic"][roles.LABEL]["act"] == "single_rewrite"
    assert result["reply"] == "「まだ予約してないんだ。」がいいかな。"
    assert result["logic"][rewrite.LABEL]["status"] == "candidate_committed"
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.index(roles.LABEL) < labels.index(rewrite.LABEL) < labels.index("utterance")
    assert result["runtime_trace"]["blackboard"][-1]["payload"]["reply"] == result["reply"]


def test_authoritative_m32_without_parent_or_protected_route_never_calls_model():
    for tick in (
        _tick(semantic_commit_repair_m32={"surface_authority": True}),
        _tick(route="low_road"),
    ):
        with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
            result = rewrite.emit_response_with_explicit_rewrite_action_p4(_fake_brain(), {"user_input": BY_ID["R4"]["user"]}, tick)
        assert result["reply"] == "うん。"
        assert result["logic"][roles.LABEL]["authority_transfer_permitted"] is False
    assert result["logic"][roles.LABEL]["action_admission"] == "protected_or_other_route_retained"


@pytest.mark.parametrize("authority", ["true", 1, None])
def test_malformed_m32_authority_fails_closed_before_model(authority):
    tick = _tick(semantic_commit_repair_m32={"schema": "uruha_deterministic_semantic_commit_m32", "surface_authority": authority})
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(_fake_brain(), {"user_input": BY_ID["R4"]["user"]}, tick)
    assert result["logic"][rewrite.LABEL]["model_call"]["attempted_calls"] == 0
    assert result["logic"]["semantic_commit_repair_m32"]["surface_authority"] == authority


@pytest.mark.parametrize("extra", [
    {"semantic_commit_repair_m32": {"schema": "wrong", "surface_authority": False}},
    {"semantic_authorization_m31": {"schema": "wrong", "surface_authority": False}},
    {"memory_recall_contract": {}},
    {"profile_grounding_shadow": {}},
    {"semantic_route_m22": {"schema": "wrong", "selected_type": "general_conversation"}},
])
def test_malformed_or_source_backed_contracts_fail_closed_before_model(extra):
    tick = _tick(**extra)
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(_fake_brain(), {"user_input": BY_ID["R4"]["user"]}, tick)
    assert result["logic"][rewrite.LABEL]["model_call"]["attempted_calls"] == 0
    assert result["logic"][roles.LABEL]["action_admission"] == "competing_authority_retained"


def test_factual_memory_route_preempts_rewrite_and_graph_keeps_m31_m32_authority():
    brain = _fake_brain()
    brain.runtime.blackboard = [
        {"stage": "validate", "label": "semantic_authorization_m31", "payload": {"surface_authority": True, "status": "semantically_authorized"}},
        {"stage": "validate", "label": "semantic_commit_repair_m32", "payload": {"surface_authority": True, "status": "deterministic_commit_repaired"}},
    ]
    user = BY_ID["R4"]["user"]
    digest16 = hashlib.sha256(user.encode("utf-8")).hexdigest()[:16]
    tick = _tick(
        semantic_route_m22={"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "factual_or_memory"},
        memory_recall_contract={"status": "matched"},
        semantic_authorization_m31={"schema": "uruha_semantic_authorization_m31", "input_digest": digest16, "surface_authority": True},
        semantic_commit_repair_m32={"schema": "uruha_deterministic_semantic_commit_m32", "surface_authority": True},
    )
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "1"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(brain, {"user_input": user}, tick)
    assert result["logic"]["semantic_authorization_m31"]["surface_authority"] is True
    assert result["logic"]["semantic_commit_repair_m32"]["surface_authority"] is True
    rows = result["runtime_trace"]["blackboard"]
    assert [row["payload"]["surface_authority"] for row in rows if row["label"] in {"semantic_authorization_m31", "semantic_commit_repair_m32"}] == [True, True]
    assert result["runtime_state"]["blackboard"] == rows
    assert result["runtime_state"]["recent_turn_traces"][-1]["blackboard"] == rows
    graph = collect_cognitive_graph({**result, "user_text": user})
    source_node = next(node for node in graph["nodes"] if node["label"] == roles.LABEL)
    assert "lineage_insufficient_for_authority_transfer" in source_node["detail"]
    assert any(node["label"] == "utterance" for node in graph["nodes"])


def test_flag_off_has_no_new_graph_or_candidate_call():
    with patch.object(rewrite, "_ORIGINAL_EMIT", _base_emit), patch.object(rewrite, "_generate", side_effect=AssertionError("must not call")), patch.dict(os.environ, {rewrite.FLAG: "0"}):
        result = rewrite.emit_response_with_explicit_rewrite_action_p4(_fake_brain(), {"user_input": BY_ID["R4"]["user"]}, _tick())
    assert roles.LABEL not in result["logic"]
    assert all(row["label"] != roles.LABEL for row in result["runtime_trace"]["blackboard"])
