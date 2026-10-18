"""Zero-model checks for the current-turn placement-advice act receipt."""

import hashlib
import os
from types import SimpleNamespace
from unittest.mock import patch

import uruha_location_advice_act_handoff_p4 as advice

from uruha_location_advice_act_handoff_p4 import (
    SCHEMA,
    classify_location_advice_act_p4,
)


def test_direct_advice_across_objects_and_goal_wordings():
    cases = (
        "展示会のパンフレット、来場者が見つけやすい所にしたい。置き方の案ある？",
        "充電コードを片づけやすくしたい。どこに出しておくとよさそう？",
        "画材ケースを運びやすい位置にしたい。配置はどうする？",
        "予備の照明はどこに置くのがいい？",
        "Where should I put the welcome sign?",
    )
    for text in cases:
        receipt = classify_location_advice_act_p4(text)
        assert receipt["schema"] == SCHEMA
        assert receipt["input_sha"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert receipt["eligible"], (text, receipt)
        assert receipt["speech_act"] == "prospective_placement_advice_request"
        assert receipt["source_kind"] == "current_user"
        assert receipt["model_calls_added"] == 0
        assert not receipt["fact_location_authorized"]
        assert not receipt["private_intent_claimed"]


def test_goal_excerpt_is_only_from_current_text_and_generic_advice_has_no_goal():
    text = "展示台のポスター、入口から見えるようにしたい。どこに置くといい？"
    receipt = classify_location_advice_act_p4(text)
    assert receipt["eligible"]
    goal = receipt["goal_text"]
    start = receipt["goal_start"]
    assert goal and start is not None
    assert text[start:start + len(goal)] == goal
    generic = classify_location_advice_act_p4("替えの電池はどこに置くといい？")
    assert generic["eligible"]
    assert generic["goal_text"] == ""
    assert generic["goal_start"] is None


def test_existing_location_question_and_assertion_are_not_advice():
    cases = (
        "展示会のパンフレットはどこに置いた？",
        "充電コードの置き場、どこ？",
        "画材ケースは棚の下に置いた。",
        "Where did I put the welcome sign?",
    )
    for text in cases:
        receipt = classify_location_advice_act_p4(text)
        assert not receipt["eligible"], (text, receipt)
        assert not receipt["fact_location_authorized"]
        assert receipt["goal_text"] == ""
    assert classify_location_advice_act_p4(cases[1])["speech_act"] == "current_location_question"


def test_quote_report_and_wording_request_do_not_become_current_advice():
    cases = (
        "同僚が『工具箱はどこに置くといい？』と聞いた。",
        "『工具箱はどこに置くといい？』という文を短くして。",
        "友人が工具箱の置き方を提案したと言っていた。",
        "「コードはどこに置くといい？",
    )
    for text in cases:
        receipt = classify_location_advice_act_p4(text)
        assert not receipt["eligible"], (text, receipt)
    assert classify_location_advice_act_p4(cases[1])["reason"] == "wording_or_translation_request"
    assert classify_location_advice_act_p4(cases[3])["reason"] == "ambiguous_quote_scope"


def test_quoted_context_does_not_block_new_direct_user_request():
    text = "『前回の配置』はさておき、ポスターはどこに置くとよさそう？"
    receipt = classify_location_advice_act_p4(text)
    assert receipt["eligible"]
    assert receipt["goal_text"] == ""


def test_explicit_no_advice_and_sensitive_uses_fail_closed():
    cases = (
        ("工具箱の置き方はまだ提案しないで。今は話を聞いて。", "advice_explicitly_negated"),
        ("看板をどこに置くといい？　でもアドバイスはいらない。", "advice_explicitly_negated"),
        ("薬箱はどこに置いておくといい？", "sensitive_placement_context"),
        ("刃物をどこに保管するのがいい？", "sensitive_placement_context"),
        ("パスワードを書いた紙はどこに置くのがいい？", "sensitive_placement_context"),
    )
    for text, reason in cases:
        receipt = classify_location_advice_act_p4(text)
        assert not receipt["eligible"], (text, receipt)
        assert receipt["reason"] == reason
        assert receipt["goal_text"] == ""


def test_empty_and_overlong_input_are_bounded():
    assert classify_location_advice_act_p4("  ")["reason"] == "empty_input"
    long_input = "会場の案内板をどこに置くといい？" + "あ" * 301
    receipt = classify_location_advice_act_p4(long_input)
    assert not receipt["eligible"]
    assert receipt["reason"] == "outside_bounded_input"


def test_selected_and_visible_receipt_is_auditable_without_semantic_success_claim():
    text = "案内板を見つけやすい場所にしたい。置き方の案ある？"
    classified = advice.classify_location_advice_act_p4(text)
    selected = {
        "core_message_jp": "入口から見える位置に置く",
        "intent": "chat", "surface_act": "plain_reply",
        advice.LABEL: {**classified, "handoff_status": "passed_to_full_planner"},
    }
    runtime = SimpleNamespace(blackboard=[{"label": "selected_plan", "payload": {}}])
    fake = SimpleNamespace(runtime=runtime)
    with patch.object(advice, "_ORIGINAL_TICK", lambda self, event: {
        "logic": selected, "route_info": {"performed_route": "full_planner"},
    }):
        tick = advice.cognitive_tick_with_location_advice_act_handoff_p4(
            fake, {"user_input": text}
        )
    cert = tick["logic"][advice.LABEL]
    assert cert["selected_handoff_status"] == "matched_full_planner"
    assert cert["selected_core_sha"] == hashlib.sha256(
        selected["core_message_jp"].encode("utf-8")
    ).hexdigest()
    assert cert["semantic_goal_tie"] == "manual_product_review_required"
    assert runtime.blackboard[0]["label"] == advice.LABEL

    visible = "入口から見える位置なら、来た人も探しやすいな。"
    with patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", lambda *args, **kwargs: visible):
        assert advice.visible_guard_with_location_advice_act_handoff_p4(
            fake, "draft", tick["logic"], user_input=text,
        ) == visible
    result = {"logic": tick["logic"], "reply": visible,
              "runtime_trace": {"blackboard": list(runtime.blackboard)}}
    advice.materialize_location_advice_act_handoff_p4(result)
    receipt = result["runtime_trace"][advice.LABEL]
    assert receipt["final_guard_match"] is True
    assert receipt["final_reply_sha"] == hashlib.sha256(visible.encode()).hexdigest()
    assert result["runtime_trace"]["blackboard"][0]["payload"] == receipt


def test_post_guard_change_and_nonselected_handoff_are_not_claimed_as_success():
    text = "会場の看板はどこに置くといい？"
    fake = SimpleNamespace(runtime=SimpleNamespace(blackboard=[]))
    with patch.object(advice, "_ORIGINAL_TICK", lambda self, event: {
        "logic": {"core_message_jp": "適当な場所に置く"},
        "route_info": {"performed_route": "semantic_authorization_m31"},
    }):
        tick = advice.cognitive_tick_with_location_advice_act_handoff_p4(
            fake, {"user_input": text}
        )
    receipt = tick["logic"][advice.LABEL]
    assert receipt["selected_handoff_status"] == "not_selected"
    assert receipt["selected_core_vacuity_diagnostic"] == "known_vacuous_phrase"
    with patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", lambda *args, **kwargs: "入口に置く。"):
        advice.visible_guard_with_location_advice_act_handoff_p4(
            fake, "draft", tick["logic"], user_input=text,
        )
    result = {"logic": tick["logic"], "reply": "別の場所に置く。",
              "runtime_trace": {"blackboard": []}}
    advice.materialize_location_advice_act_handoff_p4(result)
    assert result["runtime_trace"][advice.LABEL]["final_guard_match"] is False


def test_noneligible_fact_route_only_gains_non_authoritative_audit_node():
    text = "会場の看板はどこに置いた？"
    original = {
        "intent": "recall", "surface_act": "plain_reply",
        "core_message_jp": "今は分からないな。",
        "memory_anchor": {"trace_id": "stored:episode:sample"},
    }
    fake = SimpleNamespace(runtime=SimpleNamespace(blackboard=[
        {"label": "selected_plan", "payload": {"intent": "recall"}},
    ]))
    with patch.object(advice, "_ORIGINAL_TICK", lambda self, event: {
        "logic": dict(original), "route_info": {"performed_route": "full_planner"},
    }):
        tick = advice.cognitive_tick_with_location_advice_act_handoff_p4(
            fake, {"user_input": text}
        )
    for key, value in original.items():
        assert tick["logic"][key] == value
    assert tick["logic"][advice.LABEL]["eligible"] is False
    assert tick["logic"][advice.LABEL]["model_calls_added"] == 0
    assert [row["label"] for row in fake.runtime.blackboard] == [
        advice.LABEL, "selected_plan",
    ]
    with patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", lambda self, reply, logic, **kwargs: reply):
        visible = advice.visible_guard_with_location_advice_act_handoff_p4(
            fake, "今は分からないな。", tick["logic"], user_input=text,
        )
    assert visible == "今は分からないな。"
    assert tick["logic"][advice.LABEL]["semantic_goal_tie"] == "not_applicable"


def test_m21_opt_in_passes_one_current_act_contract_without_extra_model_call():
    from uruha_brain_mac import LeftBrain

    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content="{}"),
        )])

    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create),
    ))
    brain = LeftBrain(client)
    current = "展示のポスター、見つけやすい位置にしたい。どこに置くといい？"
    mems = {"episodes": [], "wisdom": []}
    psyche = {"mood": "calm", "trust": 0.5}
    candidate = {"intent": "chat", "core_message_jp": "見える位置に置く"}
    with patch.object(brain, "_rule_based_plan", return_value=None), \
            patch.object(brain, "_normalize_candidate_bundle", return_value={
                "candidate_plans": [candidate], "internal_monologue": "",
            }), \
            patch.object(brain, "_run_multitick_planner", side_effect=lambda *args, **kwargs: dict(candidate)):
        with patch.dict(os.environ, {"URUHA_P4_LOCATION_ADVICE_ACT": "0"}):
            old = brain.think(current, mems, psyche)
        with patch.dict(os.environ, {"URUHA_P4_LOCATION_ADVICE_ACT": "1"}):
            new = brain.think(current, mems, psyche)
    assert len(calls) == 2
    old_prompt, new_prompt = [call["messages"][0]["content"] for call in calls]
    assert "[Current User placement-advice act" not in old_prompt
    assert "[Current User placement-advice act" in new_prompt
    assert "Do not turn an old stored position" in new_prompt
    assert advice.LABEL not in old
    assert new[advice.LABEL]["handoff_status"] == "passed_to_full_planner"
    assert new[advice.LABEL]["input_sha"] == hashlib.sha256(current.encode()).hexdigest()
    assert calls[0]["model"] == calls[1]["model"] == "qwen2.5:7b"
    assert calls[0]["temperature"] == calls[1]["temperature"] == 0.1
