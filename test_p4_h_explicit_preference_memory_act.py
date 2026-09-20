import hashlib
import json
from pathlib import Path

import uruha_explicit_preference_acknowledgement_p4 as p4h


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_h_explicit_preference_memory_act_contract_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_frozen_positive_cases_build_exact_authoritative_contracts():
    contract = _contract()
    for case in contract["positive_cases"]:
        result = p4h.build_explicit_preference_memory_act_contract_p4(case["input"])
        assert result["selected"] is True, case["id"]
        assert result["act"] == case["act"]
        assert result["language"] == case["language"]
        assert result["plan_authority"] is True
        assert result["surface_authority"] is True
        assert result["selected_core_jp"] == contract["authoritative_surfaces"][case["act"]]
        assert result["raw_dialogue_persisted"] is False
        assert case["input"] not in repr(result)


def test_all_frozen_negative_cases_fail_closed():
    for case in _contract()["negative_cases"]:
        result = p4h.build_explicit_preference_memory_act_contract_p4(case["input"])
        assert result["selected"] is False, case["id"]
        assert result["status"] == "not_selected"


def test_rule_plan_owns_both_acts_before_delegated_rules(monkeypatch):
    sentinel = {"intent": "delegated"}
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_RULE_PLAN",
        lambda self, user_input, current_psyche, memory_data=None: sentinel,
    )
    contract = _contract()
    for case in contract["positive_cases"]:
        plan = p4h.rule_plan_with_explicit_preference_memory_act_p4(
            object(), case["input"], {}, {}
        )
        expected = contract["plans"][case["act"]]
        for key, value in expected.items():
            assert plan[key] == value, (case["id"], key)
        assert plan["constraints"]["casual_japanese_only"] is True
        assert plan["constraints"]["forbid_polite"] is True
        assert plan["explicit_preference_memory_act_contract_p4"]["raw_dialogue_persisted"] is False


def test_negative_rule_plans_delegate_unchanged(monkeypatch):
    sentinel = {"intent": "delegated"}
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_RULE_PLAN",
        lambda self, user_input, current_psyche, memory_data=None: sentinel,
    )
    for case in _contract()["negative_cases"]:
        plan = p4h.rule_plan_with_explicit_preference_memory_act_p4(
            object(), case["input"], {}, {}
        )
        assert plan is sentinel, case["id"]


def test_selected_act_owns_final_surface_regardless_of_prior_wording(monkeypatch):
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: reply,
    )
    arbitrary = [
        "了解しました。",
        "了解。茉莉花茶が今の飲み物だ",
        "はいはい、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。",
    ]
    for case in _contract()["positive_cases"]:
        for prior in arbitrary:
            logic = {"visible_language_guard": {"repair_action": "none"}}
            final = p4h.visible_guard_with_explicit_preference_acknowledgement_p4(
                object(), prior, logic, user_input=case["input"], memory_data={}
            )
            expected = _contract()["authoritative_surfaces"][case["act"]]
            assert final == expected, case["id"]
            audit = logic[p4h.LABEL]
            assert audit["plan_authority"] is True
            assert audit["surface_authority"] is True
            assert audit["status"] == "explicit_preference_memory_act_committed"
            assert logic["visible_language_guard"]["repair_action"] == p4h.LABEL


def test_safety_route_remains_authoritative_even_for_otherwise_selected_wording(monkeypatch):
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: "今は一人で抱えないで。",
    )
    case = next(row for row in _contract()["positive_cases"] if row["id"] == "write_en")
    logic = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
    final = p4h.visible_guard_with_explicit_preference_acknowledgement_p4(
        object(), "ignored", logic, user_input=case["input"], memory_data={}
    )
    assert final == "今は一人で抱えないで。"
    assert logic[p4h.LABEL]["status"] == "blocked_by_safety_sensitive_route"
    assert logic[p4h.LABEL]["surface_authority"] is False


def test_materialized_match_field_is_actual_exact_equality_only():
    contract = p4h.build_explicit_preference_memory_act_contract_p4(
        "今はほうじ茶が好き。今の好みとして覚えといて。"
    )
    audit = {
        **contract,
        "status": "explicit_preference_memory_act_committed",
        "surface_changed": True,
    }
    result = {
        "reply": "違う返答。",
        "logic": {p4h.LABEL: audit},
        "runtime_trace": {"blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]},
    }
    p4h.materialize_explicit_preference_acknowledgement_p4(result)
    payload = result["runtime_trace"][p4h.LABEL]
    assert payload["final_visible_surface_matches_contract"] is False
    assert result["runtime_trace"]["blackboard"][0]["stage"] == "select"

    result["reply"] = contract["selected_core_jp"]
    p4h.materialize_explicit_preference_acknowledgement_p4(result)
    payload = result["runtime_trace"][p4h.LABEL]
    assert payload["final_visible_surface_matches_contract"] is True
    assert payload["final_visible_surface_sha256"] == hashlib.sha256(
        contract["selected_core_jp"].encode()
    ).hexdigest()


def test_product_install_wraps_both_plan_and_visible_surface_after_p3_authorities():
    source = (ROOT / "uruha_explicit_preference_acknowledgement_p4.py").read_text(
        encoding="utf-8"
    )
    entry = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert "LeftBrain._rule_based_plan = rule_plan_with_explicit_preference_memory_act_p4" in source
    assert "RightBrain.enforce_user_visible_japanese" in source
    assert entry.index("install_wait_and_see_authority_p3()") < entry.index(
        "install_explicit_preference_acknowledgement_p4()"
    )
