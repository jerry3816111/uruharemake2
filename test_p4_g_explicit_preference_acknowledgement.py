import hashlib
import json
from pathlib import Path

import uruha_explicit_preference_acknowledgement_p4 as p4g


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_g_preference_acknowledgement_contract_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_runtime_constants_match_the_frozen_contract():
    contract = _contract()
    assert p4g.AUTHORITATIVE_SURFACES == contract["authoritative_surfaces"]
    assert p4g.GENERIC_FORMAL_ACKNOWLEDGEMENTS == set(
        contract["generic_formal_acknowledgements"]
    )


def test_frozen_multilingual_positive_cases_select_the_exact_act():
    for case in _contract()["positive_cases"]:
        result = p4g.classify_explicit_preference_acknowledgement_p4(case["input"])
        assert result["selected"] is True, case["id"]
        assert result["act"] == case["act"]
        assert result["language"] == case["language"]
        assert result["raw_dialogue_persisted"] is False
        assert case["input"] not in repr(result)


def test_frozen_negative_cases_fail_closed():
    for case in _contract()["negative_cases"]:
        result = p4g.classify_explicit_preference_acknowledgement_p4(case["input"])
        assert result["selected"] is False, case["id"]
        assert result["status"] == "not_selected"


def test_only_allowlisted_generic_formal_acknowledgements_are_replaced():
    case = next(row for row in _contract()["positive_cases"] if row["id"] == "write_en")
    for generic in _contract()["generic_formal_acknowledgements"]:
        for reply in (generic, f"{generic}。", f" {generic}！ "):
            final, audit = p4g.apply_explicit_preference_acknowledgement_p4(reply, case["input"])
            assert final == _contract()["authoritative_surfaces"]["write"]
            assert audit["status"] == "casual_acknowledgement_committed"
            assert audit["surface_authority"] is True
            assert audit["surface_changed"] is True


def test_correction_uses_the_separate_bounded_surface():
    case = next(row for row in _contract()["positive_cases"] if row["id"] == "correction_ja")
    final, audit = p4g.apply_explicit_preference_acknowledgement_p4("了解しました。", case["input"])
    assert final == _contract()["authoritative_surfaces"]["correction"]
    assert audit["act"] == "correction"
    assert audit["language"] == "ja"
    assert audit["model_call_added"] is False
    assert audit["episode_write_count_changed"] is False
    assert audit["memory_ranking_changed"] is False
    assert audit["p4_f_supersession_or_recall_changed"] is False


def test_natural_non_generic_reply_is_unchanged_even_when_act_is_eligible():
    case = next(row for row in _contract()["positive_cases"] if row["id"] == "write_zh")
    original = "うん、その話はちゃんと覚えとく。"
    final, audit = p4g.apply_explicit_preference_acknowledgement_p4(original, case["input"])
    assert final == original
    assert audit["status"] == "eligible_surface_already_non_generic"
    assert audit["surface_authority"] is False
    assert audit["surface_changed"] is False


def test_negative_input_never_changes_even_a_generic_reply():
    for case in _contract()["negative_cases"]:
        final, audit = p4g.apply_explicit_preference_acknowledgement_p4(
            "了解しました。",
            case["input"],
        )
        assert final == "了解しました。", case["id"]
        assert audit["surface_authority"] is False


def test_visible_guard_wrapper_updates_existing_language_guard_without_raw_input(monkeypatch):
    monkeypatch.setattr(
        p4g,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: "了解しました。",
    )
    logic = {
        "visible_language_guard": {
            "schema": "uruha_visible_language_guard_v1",
            "changed": False,
            "repair_action": "none",
            "final_reply": "了解しました。",
        }
    }
    user_input = "Correction: I do not prefer chamomile tea anymore. I prefer black coffee now."
    final = p4g.visible_guard_with_explicit_preference_acknowledgement_p4(
        object(),
        "ignored",
        logic,
        user_input=user_input,
        memory_data={},
    )
    assert final == "ん、訂正の内容はそのまま覚えとく。"
    assert logic["visible_language_guard"]["changed"] is True
    assert logic["visible_language_guard"]["repair_action"] == p4g.LABEL
    assert logic["visible_language_guard"]["final_reply"] == final
    assert logic[p4g.LABEL]["raw_dialogue_persisted"] is False
    assert user_input not in repr(logic[p4g.LABEL])


def test_graph_materialization_inserts_trace_before_utterance():
    final = "ん、その好みは覚えとく。"
    _, audit = p4g.apply_explicit_preference_acknowledgement_p4(
        "了解しました",
        "I prefer chamomile tea. Please remember that as my current tea preference.",
    )
    result = {
        "reply": final,
        "logic": {p4g.LABEL: audit},
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": "visible_language_guard", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {"reply": final}},
            ]
        },
    }
    p4g.materialize_explicit_preference_acknowledgement_p4(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels == ["visible_language_guard", p4g.LABEL, "utterance"]
    payload = result["runtime_trace"][p4g.LABEL]
    assert payload["final_visible_surface_matches_contract"] is True
    assert payload["final_visible_surface_sha256"] == hashlib.sha256(final.encode()).hexdigest()


def test_product_entry_installs_the_adapter_after_existing_p3_surface_authorities():
    source = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert "from uruha_explicit_preference_acknowledgement_p4 import" in source
    assert "install_explicit_preference_acknowledgement_p4()" in source
    assert source.index("install_wait_and_see_authority_p3()") < source.index(
        "install_explicit_preference_acknowledgement_p4()"
    )
