"""Zero-model contracts for the opt-in, formal-only advice surface edit."""

import hashlib
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import uruha_location_advice_act_handoff_p4 as advice
from uruha_semantic_persona_surface_m39 import verify_and_repair_surface_m39


USER = "小さなネジを見失わないようにしたい。どこに置くといい？"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _logic(user, core):
    cert = advice.classify_location_advice_act_p4(user)
    assert cert["eligible"]
    cert.update({
        "selected_handoff_status": "matched_full_planner",
        "selected_core_sha": _sha(core),
    })
    return {
        advice.LABEL: cert,
        "semantic_route_m22": {"selected_type": "general_conversation"},
    }


def _m39_guard(self, candidate, logic, user_input="", memory_data=None):
    visible, audit = verify_and_repair_surface_m39(user_input, candidate, logic)
    logic["semantic_persona_surface_verifier_m39"] = audit
    return visible


def _run(user, core, logic=None, guard=_m39_guard, enabled=True):
    logic = logic if logic is not None else _logic(user, core)
    with patch.dict(os.environ, {"URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE": "1" if enabled else "0"}), \
            patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", guard):
        visible = advice.visible_guard_with_location_advice_act_handoff_p4(
            SimpleNamespace(), core, logic, user_input=user,
        )
    return visible, logic


@pytest.mark.parametrize("core,expected", [
    ("机の角から離して置くと見つけやすいです", "机の角から離して置くと見つけやすいよ。"),
    ("机の角から離して置くと見つけやすいです。", "机の角から離して置くと見つけやすいよ。"),
    ("暗い棚に置くと見つけにくいです。", "暗い棚に置くと見つけにくいよ。"),
])
def test_safe_formal_only_candidate_preserves_prefix_and_m39_accepts(core, expected):
    visible, logic = _run(USER, core)
    receipt = logic[advice.LABEL]["formal_surface"]
    assert visible == expected
    assert receipt["status"] == "accepted_preserved"
    assert receipt["method"] == "terminal_i_adjective_desu_to_yo"
    assert receipt["prefix_identical"] is True
    assert receipt["source_prefix_sha"] == receipt["attempt_prefix_sha"] == _sha(expected[:-2])
    assert receipt["original_candidate_sha"] == logic[advice.LABEL]["guard_input_sha"] == _sha(core)
    assert receipt["attempt_sha"] == receipt["final_visible_sha"] == _sha(expected)
    assert receipt["final_same_as_attempt"] is True
    assert receipt["m39_action"] == "accept"
    assert receipt["m39_status"] == "accepted_verified_surface"
    assert receipt["model_calls_added"] == 0
    assert receipt["raw_reply_persisted"] is False

    result = {
        "logic": logic, "reply": visible,
        "runtime_trace": {"blackboard": [
            {"label": "semantic_persona_surface_verifier_m39", "payload": {}},
            {"label": "utterance", "payload": {"text": visible}},
        ]},
    }
    advice.materialize_location_advice_act_handoff_p4(result)
    assert result["runtime_trace"][advice.FORMAL_SURFACE_LABEL]["final_reply_match"] is True
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.index(advice.FORMAL_SURFACE_LABEL) < labels.index(
        "semantic_persona_surface_verifier_m39"
    ) < labels.index("utterance")
    assert result["runtime_trace"][advice.FORMAL_SURFACE_LABEL]["status"] == "accepted_preserved"


def test_old_entry_flag_off_still_uses_original_m39_fallback():
    core = "机の角から離して置くと見つけやすいです。"
    visible, logic = _run(USER, core, enabled=False)
    assert visible == "ん、そこもう少しだけ聞かせて。"
    assert "formal_surface" not in logic[advice.LABEL]
    assert logic["semantic_persona_surface_verifier_m39"]["action"] == "repair"


@pytest.mark.parametrize("core", [
    "机に置いてください。",
    "机に置きましょう。",
    "机の角を避けると便利です。",
    "机なら見つけやすいです？",
    "まず机へ。そこなら見つけやすいです。",
    "『机の上なら見つけやすいです。』",
    "机の上なら見つけやすいです。\n次も考えよう。",
    "先に確認した.机なら見つけやすいです。",
    "先に確認した\r机なら見つけやすいです。",
    "`机なら見つけやすいです`",
])
def test_unsupported_shape_never_attempts_new_edit(core):
    visible, logic = _run(USER, core)
    receipt = logic[advice.LABEL]["formal_surface"]
    assert receipt["status"] == "unsupported_surface_shape"
    assert receipt["attempt_sha"] is None
    assert receipt["original_candidate_sha"] == _sha(core)
    assert logic[advice.LABEL]["guard_input_sha"] == _sha(core)
    assert visible != "机の角から離して置くと見つけやすいよ。"


@pytest.mark.parametrize("mutation", [
    lambda cert, logic: cert.update(schema="wrong"),
    lambda cert, logic: cert.update(source_kind="third_party"),
    lambda cert, logic: cert.update(input_sha="stale"),
    lambda cert, logic: cert.update(eligible=False),
    lambda cert, logic: cert.update(selected_handoff_status="not_selected"),
    lambda cert, logic: cert.update(selected_core_sha="stale"),
    lambda cert, logic: logic["semantic_route_m22"].update(selected_type="factual_or_memory"),
])
def test_wrong_or_protected_certificate_does_not_attempt(mutation):
    core = "机に置くと見つけやすいです。"
    logic = _logic(USER, core)
    mutation(logic[advice.LABEL], logic)
    visible, logic = _run(USER, core, logic=logic)
    if logic[advice.LABEL]["schema"] == advice.SCHEMA:
        assert logic[advice.LABEL]["formal_surface"]["attempt_sha"] is None
        assert logic[advice.LABEL]["formal_surface"]["status"] == "not_eligible"
    assert visible != "机に置くと見つけやすいよ。"


@pytest.mark.parametrize("user", [
    "ネジは机のどこに置いた？",
    "係の人が『ネジはどこに置くといい？』って言ってた。",
    "ネジの置き方はあとでいい。今は話を聞いて。",
    "暗証番号を書いた紙はどこに置くといい？",
])
def test_current_user_reclassification_rejects_other_acts_even_with_forged_cert(user):
    core = "机に置くと見つけやすいです。"
    logic = _logic(USER, core)
    logic[advice.LABEL]["input_sha"] = _sha(user)
    visible, logic = _run(user, core, logic=logic)
    assert logic[advice.LABEL]["formal_surface"]["status"] == "not_eligible"
    assert visible != "机に置くと見つけやすいよ。"


@pytest.mark.parametrize("core,policy", [
    ("私は寝ていないと見つけやすいです。", None),
    ("朝から机に置くと見つけやすいです。", None),
    ("机に置くと見つけやすいです。", "calibrate_need"),
])
def test_mixed_m39_violations_are_not_laundered(core, policy):
    user = "私は小さなネジを見失わないようにしたい。どこに置くといい？"
    logic = _logic(user, core)
    if policy:
        logic["desired_response_policy_m18"] = policy
    visible, logic = _run(user, core, logic=logic)
    assert logic[advice.LABEL]["formal_surface"]["status"] == "not_formal_only"
    assert logic[advice.LABEL]["formal_surface"]["attempt_sha"] is None
    assert visible != core.replace("です。", "よ。")


def test_guard_or_post_emit_change_cannot_be_claimed_as_preserved():
    core = "机に置くと見つけやすいです。"

    def changed_guard(self, candidate, logic, user_input="", memory_data=None):
        _, audit = verify_and_repair_surface_m39(user_input, candidate, logic)
        logic["semantic_persona_surface_verifier_m39"] = audit
        return "別の話にしよ。"

    visible, logic = _run(USER, core, guard=changed_guard)
    assert visible == "別の話にしよ。"
    assert logic[advice.LABEL]["formal_surface"]["status"] == "post_guard_mismatch"
    assert logic[advice.LABEL]["formal_surface"]["final_same_as_attempt"] is False

    visible, logic = _run(USER, core)
    result = {"logic": logic, "reply": "別の話にしよ。", "runtime_trace": {"blackboard": []}}
    advice.materialize_location_advice_act_handoff_p4(result)
    receipt = result["runtime_trace"][advice.FORMAL_SURFACE_LABEL]
    assert receipt["status"] == "post_emit_mismatch"
    assert receipt["final_reply_match"] is False


def test_nonstring_and_malformed_receipts_leave_original_route_unchanged():
    core = "机に置くと見つけやすいです。"
    logic = _logic(USER, core)

    def identity(self, candidate, logic, user_input="", memory_data=None):
        return candidate

    with patch.dict(os.environ, {"URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE": "1"}), \
            patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", identity):
        assert advice.visible_guard_with_location_advice_act_handoff_p4(
            SimpleNamespace(), None, logic, user_input=USER,
        ) is None
    assert "formal_surface" not in logic[advice.LABEL]

    logic[advice.LABEL] = "malformed"
    with patch.dict(os.environ, {"URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE": "1"}), \
            patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", identity):
        assert advice.visible_guard_with_location_advice_act_handoff_p4(
            SimpleNamespace(), core, logic, user_input=USER,
        ) == core
    assert advice.materialize_location_advice_act_handoff_p4({
        "logic": logic, "reply": core, "runtime_trace": {"blackboard": []},
    })["logic"][advice.LABEL] == "malformed"
