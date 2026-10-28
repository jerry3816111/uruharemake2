"""Focused P4-F regressions for bounded explicit preference supersession."""

from copy import deepcopy
import json

import uruha_speaker_qualified_fact_p3 as fact


QUERY = "What kind of tea did I say I prefer?"
OLD = "I said I prefer herbal tea."
CORRECTION = "Correction: I do not prefer herbal tea anymore. I prefer black tea now."


def memory_item(user, memory_id, *, score=0.9, selected=True):
    return {
        "selected": selected,
        "text": f"User: {user} | Summary: bounded test | Uruha: うん。 | Mood: neutral",
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "source": "episode",
        "score": score,
    }


def build(*items):
    return fact.build_speaker_qualified_fact_contract_p3(
        QUERY,
        {"working_memory_items": list(items)},
    )


def test_explicit_same_item_correction_resolves_current_and_preserves_historical_provenance():
    contract = build(
        memory_item(OLD, "old-preference", score=0.82),
        memory_item(CORRECTION, "explicit-correction", score=0.96),
    )
    assert contract["status"] == "resolved_explicit_preference_supersession"
    assert contract["selected_speaker"] == "user"
    assert contract["candidate_count"] == 1
    assert contract["selected_core_jp"] == "今の好みは紅茶。前のハーブティーから更新してる。"
    assert contract["candidates"][0]["localized_value_jp"] == "紅茶"
    assert contract["candidates"][0]["temporal_status"] == "current"
    update = contract["supersession"]
    assert update["status"] == "applied"
    assert update["current_value_jp"] == "紅茶"
    assert update["revoked_value_jp"] == "ハーブティー"
    assert update["current_value_digest"] != update["revoked_value_digest"]
    assert update["correction_memory_id"] == "explicit-correction"
    assert update["correction_trace_id"] == "stored:episode:explicit-correction"
    assert update["historical_memory_id"] == "old-preference"
    assert update["historical_trace_id"] == "stored:episode:old-preference"
    assert update["history_preserved"] is True
    assert update["database_rewrite_count"] == 0
    assert contract["fact_memory_write_count"] == 0
    serialized = json.dumps(contract, ensure_ascii=False)
    assert OLD not in serialized
    assert CORRECTION not in serialized


def test_two_preferences_without_explicit_correction_remain_ambiguous():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item("I said I prefer black tea.", "other-preference"),
    )
    assert contract["status"] == "ambiguous_multiple_user_preferences"
    assert contract["selected_speaker"] is None
    assert "supersession" not in contract


def test_third_party_correction_does_not_update_the_user():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item(
            "Correction: Mina does not prefer herbal tea anymore. Mina prefers black tea now.",
            "third-party-correction",
        ),
    )
    assert contract["status"] == "resolved_unique_user_preference"
    assert contract["selected_core_jp"] == "あんたが好みって言ってたのはハーブティー。"
    assert "supersession" not in contract


def test_multiple_conflicting_explicit_corrections_abstain_without_score_selection():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item(CORRECTION, "correction-a", score=0.99),
        memory_item(
            "Correction: I do not prefer herbal tea anymore. I prefer unsweetened tea now.",
            "correction-b",
            score=0.20,
        ),
    )
    assert contract["status"] == "ambiguous_conflicting_explicit_corrections"
    assert contract["selected_speaker"] is None
    assert contract["selected_core_jp"] == "好みの更新が複数ある。今はどれが最新か断定しない。"
    assert "supersession" not in contract


def test_unsupported_new_value_localization_abstains_instead_of_using_old_value():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item(
            "Correction: I do not prefer herbal tea anymore. I prefer cloudberry tea now.",
            "unsupported-correction",
        ),
    )
    assert contract["status"] == "unsupported_supersession_localization"
    assert contract["selected_speaker"] is None
    assert contract["selected_core_jp"] == "その更新、今の記憶だけじゃ日本語で確実に整理できない。"
    assert "cloudberry" not in json.dumps(contract, ensure_ascii=False)
    assert "supersession" not in contract


def test_selected_correction_without_distinct_old_episode_does_not_claim_history():
    contract = build(memory_item(CORRECTION, "correction-only"))
    assert contract["status"] == "missing_superseded_preference_history"
    assert contract["selected_speaker"] is None
    assert "supersession" not in contract


def test_unselected_correction_is_ignored():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item(CORRECTION, "unselected-correction", selected=False),
    )
    assert contract["status"] == "resolved_unique_user_preference"
    assert contract["selected_core_jp"] == "あんたが好みって言ってたのはハーブティー。"
    assert "supersession" not in contract


def test_resolved_supersession_uses_direct_plan_graph_and_never_overrides_safety():
    contract = build(
        memory_item(OLD, "old-preference"),
        memory_item(CORRECTION, "explicit-correction"),
    )
    plan = fact._plan_from_contract(contract)
    assert plan["cognitive_mode"] == "direct"
    assert plan["response_mode"] == "direct_answer"
    assert plan["uncertainty"] == 0.08

    result = {
        "reply": contract["selected_core_jp"],
        "logic": {"memory_recall_contract": deepcopy(contract)},
        "runtime_trace": {
            "blackboard": [
                {"stage": "memory", "label": "working_memory", "payload": {}},
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    fact.materialize_speaker_qualified_fact_p3(result)
    node = result["runtime_trace"][fact.LABEL]
    assert node["status"] == "resolved_explicit_preference_supersession"
    assert node["supersession"]["historical_memory_id"] == "old-preference"
    assert "explicit_supersession_or_unique_or_abstain" in node["flow"]
    assert CORRECTION not in json.dumps(node, ensure_ascii=False)

    original_guard = fact._ORIGINAL_VISIBLE_GUARD

    def legacy_guard(_self, reply, logic, **_kwargs):
        return reply

    try:
        fact._ORIGINAL_VISIBLE_GUARD = legacy_guard
        logic = {
            "memory_recall_contract": deepcopy(contract),
            "semantic_route_m22": {"selected_type": "safety_sensitive"},
        }
        visible = fact.visible_guard_with_speaker_qualified_fact_p3(
            object(), "安全側の返答。", logic
        )
    finally:
        fact._ORIGINAL_VISIBLE_GUARD = original_guard
    assert visible == "安全側の返答。"
