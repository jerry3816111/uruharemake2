"""Zero-model contracts for the opt-in paper-credential visible boundary."""

import ast
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import uruha_location_advice_act_handoff_p4 as advice
from uruha_semantic_persona_surface_m39 import verify_and_repair_surface_m39


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_product_entry_startup_installer_chain():
    import uruha_web_ui_product_p4_credential_paper_visible as product_entry

    tree = ast.parse(Path(product_entry.__file__).read_text(encoding="utf-8"))

    def resolve(node):
        if isinstance(node, ast.Name):
            return vars(product_entry)[node.id]
        if isinstance(node, ast.Attribute):
            return getattr(resolve(node.value), node.attr)
        raise AssertionError(f"Unexpected startup expression: {type(node).__name__}")

    targets = [
        node.func for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and (node.func.attr.startswith("install_") or node.func.attr == "build_demo")
    ]
    assert len(targets) == 20
    assert all(callable(resolve(target)) for target in targets)
    assert callable(product_entry.install_location_advice_act_handoff_p4)


def test_product_entry_startup_installer_chain_resolves_without_serving():
    """Probe the import in a subprocess so it cannot alter later unit fixtures."""
    proc = subprocess.run(
        [sys.executable, __file__], capture_output=True, text=True, timeout=45,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


if __name__ == "__main__":
    _check_product_entry_startup_installer_chain()


@pytest.mark.parametrize("user", [
    "ログイン用のパスワードを書いた付箋をなくさないように、どこに置くといい？",
    "我把登入密碼寫在紙上，怕弄丟，放哪裡比較好？",
    "Where should I put a note with my PIN so I don't lose it?",
    "暗証番号を書いた紙をなくさないように、どこに置くといい？",
])
def test_direct_written_credential_advice_detected_independently_of_old_handoff(user):
    receipt = advice.classify_credential_paper_visible_p4(user)
    assert receipt["schema"] == advice.CREDENTIAL_VISIBLE_SCHEMA
    assert receipt["input_sha"] == _sha(user)
    assert receipt["eligible"] is True
    assert receipt["model_calls_added"] == 0
    assert receipt["receipt_raw_user_text_persisted"] is False


def test_old_handoff_does_not_control_new_multilingual_safety_classification():
    chinese = "我把登入密碼寫在紙上，怕弄丟，放哪裡比較好？"
    english = "Where should I put a note with my PIN so I don't lose it?"
    for user in (chinese, english):
        assert advice.classify_location_advice_act_p4(user)["eligible"] is True
        assert advice.classify_credential_paper_visible_p4(user)["eligible"] is True


@pytest.mark.parametrize("user", [
    "鉛筆をすぐ取れるように、どこに置くといい？",
    "パスワードを書いた紙は片づけた。鉛筆はどこに置くといい？",
    "パスワードを書いた紙はしまうけど、鉛筆はどこに置くといい？",
    "パスワードを書いた紙を捨てて鉛筆はどこに置くといい？",
    "パスワードを書いた紙はしまったけど、買い物メモはどこに置くといい？",
    "密碼寫在紙上，但買菜便條放哪裡比較好？",
    "パスワードを書いた紙はしまったけど、メモはどこに置くといい？",
    "PINを書いたメモは捨てたけど、メモはどこに置くといい？",
    "密碼寫在紙上，但便條放哪裡比較好？",
    "パスワードはあとで変える。鉛筆はどこに置くといい？",
    "暗証番号を書いた紙の置き場所はここでいい。",
    "パスワードを書いた紙はどこに置くかもう決めた。",
    "I know where to put a note with my PIN.",
    "I already stored a note with my PIN, and where should I put the note for groceries?",
    "I wrote my PIN on a note, but where should I put the paper for homework?",
    "友達が『PINを書いたメモはどこに置くといい？』と聞いた。私は答えない。",
    "友達が『PINを書いたメモはどこに置くといい？』と聞いた。鉛筆はどこに置くといい？",
    "He asked ‘Where should I put a note with my PIN?’",
    "He asked 'Where should I put a note with my PIN?",
    "He asked where should I put a note with my PIN?",
    "暗証番号を書いた紙の置き場所は提案しないで。今日は話だけ聞いて。",
    "パスワードを書いた紙はどこに置いた？",
    "パスワードを書いた紙をどこに置くべきか翻訳して。",
    "パスワードを書いた紙の置き方を説明する文章を自然な日本語に直して。",
    "薬を書いた紙はどこに置くといい？",
    "パスワードを書いた紙はどこに置くといい？『引用が閉じない",
    "パスワードを書いた紙はどこに置くといい？" + "長" * 301,
])
def test_other_objects_or_speech_acts_not_taken_over(user):
    receipt = advice.classify_credential_paper_visible_p4(user)
    assert receipt["eligible"] is False


def _logic(user, core):
    prior = advice.classify_location_advice_act_p4(user)
    prior.update({"selected_core_sha": _sha(core), "selected_handoff_status": "not_selected"})
    return {
        advice.LABEL: prior,
        "core_message_jp": core,
        "semantic_route_m22": {"selected_type": "general_conversation"},
    }


def _identity_guard(self, candidate, logic, user_input="", memory_data=None):
    logic["semantic_persona_surface_verifier_m39"] = {
        "action": "accept", "status": "accepted_verified_surface",
    }
    logic["visible_language_guard"] = {"final_reply": candidate}
    return candidate


def _real_m39_guard(self, candidate, logic, user_input="", memory_data=None):
    visible, audit = verify_and_repair_surface_m39(user_input, candidate, logic)
    logic["semantic_persona_surface_verifier_m39"] = audit
    logic["visible_language_guard"] = {"final_reply": visible}
    return visible


def _run(user, core, *, enabled=True, logic=None, guard=_identity_guard):
    logic = logic if logic is not None else _logic(user, core)
    flags = {
        "URUHA_P4_CREDENTIAL_PAPER_VISIBLE": "1" if enabled else "0",
        "URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE": "0",
    }
    with patch.dict(os.environ, flags), patch.object(advice, "_ORIGINAL_VISIBLE_GUARD", guard):
        visible = advice.visible_guard_with_location_advice_act_handoff_p4(
            SimpleNamespace(), core, logic, user_input=user,
        )
    return visible, logic


@pytest.mark.parametrize("user", [
    "ログイン用のパスワードを書いた付箋をなくさないように、どこに置くといい？",
    "我把登入密碼寫在紙上，怕弄丟，放哪裡比較好？",
    "Where should I put a note with my PIN so I don't lose it?",
])
def test_direct_credential_core_is_replaced_before_original_visible_guard(user):
    core = "机の上に置くのがいいよ。"
    visible, logic = _run(user, core)
    receipt = logic[advice.LABEL]["credential_paper_visible"]
    assert visible != core
    assert "机の上に置く" not in visible
    assert "人目" in visible
    assert receipt["original_candidate_sha"] == _sha(core)
    assert receipt["safe_candidate_sha"] == receipt["final_visible_sha"] == _sha(visible)
    assert receipt["final_same_as_safe_candidate"] is True
    assert receipt["m39_action"] == "accept"
    assert receipt["model_calls_added"] == 0


def test_flag_off_keeps_old_route_and_does_not_claim_new_authority():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    visible, logic = _run(user, core, enabled=False)
    assert visible == core
    assert "credential_paper_visible" not in logic[advice.LABEL]


def test_bounded_safe_surface_passes_actual_m39_audit():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    visible, logic = _run(user, core, guard=_real_m39_guard)
    assert visible != core
    assert logic["semantic_persona_surface_verifier_m39"]["action"] == "accept"
    assert logic[advice.LABEL]["credential_paper_visible"]["status"] == "accepted_preserved"


def test_protected_m39_route_preserves_surface_without_false_accept_claim():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    logic = _logic(user, core)
    logic["semantic_route_m22"]["selected_type"] = "safety_sensitive"
    visible, logic = _run(user, core, logic=logic, guard=_real_m39_guard)
    receipt = logic[advice.LABEL]["credential_paper_visible"]
    assert visible != core
    assert receipt["final_same_as_safe_candidate"] is True
    assert receipt["status"] == "preserved_protected_route"
    assert receipt["m39_action"] == "not_applicable"
    assert receipt["m39_status"] == "protected_route_not_modified"


def test_active_selected_policy_m39_repair_is_detected_not_called_safe_success():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    logic = _logic(user, core)
    logic["desired_response_policy_m18"] = "solve_regulation"
    visible, logic = _run(user, core, logic=logic, guard=_real_m39_guard)
    receipt = logic[advice.LABEL]["credential_paper_visible"]
    assert visible != core
    assert receipt["status"] == "post_guard_mismatch"
    assert receipt["m39_action"] == "repair"
    assert receipt["final_same_as_safe_candidate"] is False


def test_fictional_secret_value_is_not_echoed_into_safe_surface():
    user = "架空テスト用PIN 7316を書いたメモをなくさないよう、どこに置くといい？"
    core = "7316 のメモは机の上に置けばいいよ。"
    visible, logic = _run(user, core)
    assert "7316" not in visible
    assert logic[advice.LABEL]["credential_paper_visible"]["status"] in {
        "attempted_safe_surface", "accepted_preserved",
    }


def test_even_an_already_safe_selected_core_is_boundedly_replaced():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "人目に触れないように管理したほうがいい。"
    visible, logic = _run(user, core)
    assert visible != core
    receipt = logic[advice.LABEL]["credential_paper_visible"]
    assert receipt["original_candidate_sha"] == _sha(core)
    assert receipt["selected_core_safe_diagnostic"] == "not_established"
    assert receipt["status"] == "accepted_preserved"


def test_guard_changing_safe_candidate_cannot_claim_authorized_surface():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"

    def changed_guard(self, candidate, logic, user_input="", memory_data=None):
        logic["semantic_persona_surface_verifier_m39"] = {
            "action": "accept", "status": "accepted_verified_surface",
        }
        return "机の上に置くのがいいよ。"

    visible, logic = _run(user, core, guard=changed_guard)
    assert visible == core
    receipt = logic[advice.LABEL]["credential_paper_visible"]
    assert receipt["status"] == "post_guard_mismatch"
    assert receipt["final_same_as_safe_candidate"] is False


def test_stale_old_handoff_does_not_bypass_independent_safety_boundary():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    logic = _logic(user, core)
    logic[advice.LABEL]["input_sha"] = "stale"
    visible, logic = _run(user, core, logic=logic)
    assert visible != core
    assert logic[advice.LABEL]["credential_paper_visible"]["input_sha"] == _sha(user)


def test_graph_and_post_emit_receipt_detect_later_change():
    user = "暗証番号を書いた紙をなくさないように、どこに置くといい？"
    core = "机の上に置くのがいいよ。"
    visible, logic = _run(user, core)
    result = {
        "logic": logic,
        "reply": visible,
        "runtime_trace": {"blackboard": [
            {"label": "semantic_persona_surface_verifier_m39", "payload": {}},
            {"label": "utterance", "payload": {"reply": visible}},
        ]},
    }
    advice.materialize_location_advice_act_handoff_p4(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.index(advice.CREDENTIAL_VISIBLE_LABEL) < labels.index("utterance")
    assert result["runtime_trace"][advice.CREDENTIAL_VISIBLE_LABEL]["final_reply_match"] is True

    result["reply"] = "机の上に置くのがいいよ。"
    advice.materialize_location_advice_act_handoff_p4(result)
    receipt = result["runtime_trace"][advice.CREDENTIAL_VISIBLE_LABEL]
    assert receipt["final_reply_match"] is False
    assert receipt["status"] == "post_emit_mismatch"
