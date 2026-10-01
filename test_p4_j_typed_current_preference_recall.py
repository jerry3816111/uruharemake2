from copy import deepcopy
import json
from pathlib import Path

import uruha_speaker_qualified_fact_p3 as p4f
import uruha_typed_current_preference_recall_p4 as p4j


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_j_typed_current_preference_recall_contract_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _row(memory_id, value, *, scope="drink", provenance=True):
    metadata = {
        "preference_semantics_schema": "uruha_current_preference_typed_state_p4_v1",
        "preference_semantics": "current_preference",
        "preference_scope": scope,
        "value": value,
    }
    if provenance:
        metadata.update(
            source_language="en",
            source_input_sha256="a" * 64,
            preference_scope_sha256="b" * 64,
        )
    return {"memory_id": memory_id, "metadata": metadata}


def _resolved(*active, historical=()):
    return {
        "active": list(active),
        "historical": list(historical),
        "decisions": {
            row["memory_id"]: {
                "partition": "eligible" if row in active else "historical",
                "reason": "active" if row in active else "newer_single_value",
            }
            for row in (*active, *historical)
        },
    }


def test_frozen_multilingual_exact_scope_queries_select_the_same_canonical_scope():
    for case in _contract()["positive_query_fixtures"]:
        result = p4j.classify_typed_current_preference_query_p4(case["input"])
        assert result["selected"] is True, case["id"]
        assert result["query_language"] == case["language"]
        assert result["scope"] == case["scope"]
        assert case["input"] not in repr(result)


def test_all_frozen_negative_queries_delegate_without_typed_answer_authority():
    for case in _contract()["negative_query_fixtures"]:
        result = p4j.classify_typed_current_preference_query_p4(case["input"])
        assert result["selected"] is False, case["id"]
        assert result["status"] == "not_selected"
        assert case["input"] not in repr(result)


def test_unique_active_exact_scope_record_wins_without_historical_or_negative_use(monkeypatch):
    fixture = _contract()["development_state_fixture"]
    active = _row(fixture["active_memory_id"], fixture["active_value"])
    historical = _row(fixture["historical_memory_id"], fixture["historical_value"])
    monkeypatch.setattr(
        p4j.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: _resolved(active, historical=(historical,)),
    )
    result = p4j.build_typed_current_preference_recall_contract_p4(
        "What is my current drink preference?", object()
    )
    assert result["status"] == fixture["expected_status"]
    assert result["selected_core_jp"] == fixture["expected_visible_output"]
    assert result["active_memory_id"] == fixture["active_memory_id"]
    assert result["answer_use_authorized"] is True
    assert result["historical_answer_use_count"] == 0
    assert result["explicit_negative_answer_use_count"] == 0
    assert result["episode_answer_use_count"] == 0
    assert result["profile_write_count"] == 0
    assert fixture["active_value"] not in repr(result)
    assert fixture["historical_value"] not in repr(result)


def test_no_active_exact_scope_record_abstains_without_episode_fallback(monkeypatch):
    monkeypatch.setattr(
        p4j.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: _resolved(),
    )
    result = p4j.build_typed_current_preference_recall_contract_p4(
        "我現在的飲料偏好是什麼？", object()
    )
    assert result["status"] == "no_active_typed_current_preference"
    assert result["answer_use_authorized"] is False
    assert result["selected_core_jp"] == "今の飲み物の好みは、記録から確認できない。"


def test_multiple_active_exact_scope_records_abstain_without_score_selection(monkeypatch):
    first = _row("current-a", "rooibos tea")
    second = _row("current-b", "barley tea")
    monkeypatch.setattr(
        p4j.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: _resolved(first, second),
    )
    result = p4j.build_typed_current_preference_recall_contract_p4(
        "私の今の飲み物の好みは何？", object()
    )
    assert result["status"] == "ambiguous_multiple_active_typed_current_preferences"
    assert result["candidate_count"] == 2
    assert result["answer_use_authorized"] is False
    assert "rooibos" not in repr(result)
    assert "barley" not in repr(result)


def test_missing_provenance_or_unsupported_localization_abstains_without_raw_value(monkeypatch):
    invalid = _row("invalid", "rooibos tea", provenance=False)
    monkeypatch.setattr(
        p4j.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: _resolved(invalid),
    )
    missing = p4j.build_typed_current_preference_recall_contract_p4(
        "What is my current drink preference?", object()
    )
    assert missing["status"] == "invalid_active_record_provenance"
    assert "rooibos tea" not in repr(missing)

    unsupported = _row("unsupported", "cloudberry tea")
    monkeypatch.setattr(
        p4j.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: _resolved(unsupported),
    )
    unknown = p4j.build_typed_current_preference_recall_contract_p4(
        "What is my current drink preference?", object()
    )
    assert unknown["status"] == "unsupported_active_value_localization"
    assert "cloudberry" not in repr(unknown)


def test_query_wrapper_reads_profile_only_for_selected_query_and_keeps_contract_separate(monkeypatch):
    calls = []
    monkeypatch.setattr(
        p4j,
        "_ORIGINAL_QUERY_ALL_LAYERS",
        lambda _self, text: calls.append(text) or {"profile_structured": {}},
    )
    monkeypatch.setattr(
        p4j,
        "build_typed_current_preference_recall_contract_p4",
        lambda _text, _collection: {
            "schema": p4j.SCHEMA,
            "selected": True,
            "surface_authority": True,
            "status": "resolved_unique_active_typed_current_preference",
            "selected_core_jp": "今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。",
        },
    )
    memory = type("Memory", (), {"profile_col": object()})()
    selected = p4j.query_all_layers_with_typed_current_preference_recall_p4(
        memory, "What is my current drink preference?"
    )
    delegated = p4j.query_all_layers_with_typed_current_preference_recall_p4(
        memory, "What kind of tea did I say I prefer?"
    )
    assert calls == [
        "What is my current drink preference?",
        "What kind of tea did I say I prefer?",
    ]
    assert selected[p4j.LABEL]["surface_authority"] is True
    assert delegated[p4j.LABEL]["selected"] is False
    assert "typed_current_preferences" not in selected["profile_structured"]


def test_selected_contract_builds_direct_plan_but_nonselected_preserves_p4_f(monkeypatch):
    fixture = _contract()["development_state_fixture"]
    selected = {
        "schema": p4j.SCHEMA,
        "selected": True,
        "surface_authority": True,
        "status": fixture["expected_status"],
        "scope": "drink",
        "active_memory_id": fixture["active_memory_id"],
        "selected_core_jp": fixture["expected_visible_output"],
    }
    plan = p4j.rule_plan_with_typed_current_preference_recall_p4(
        object(), "What is my current drink preference?", {}, {p4j.LABEL: selected}
    )
    assert plan["planner_path"] == "typed_current_preference_recall_authority_p4"
    assert plan["core_message_jp"] == fixture["expected_visible_output"]
    assert plan["cognitive_mode"] == "direct"

    sentinel = {"planner_path": "p4_f_sentinel"}
    monkeypatch.setattr(p4j, "_ORIGINAL_RULE_PLAN", lambda *_args, **_kwargs: sentinel)
    delegated = p4j.rule_plan_with_typed_current_preference_recall_p4(
        object(), "What kind of tea did I say I prefer?", {}, {}
    )
    assert delegated is sentinel
    assert p4f.classify_speaker_qualified_fact_p3(
        "What kind of tea did I say I prefer?"
    )["selected"] is True


def test_surface_authority_is_exact_but_never_overrides_safety(monkeypatch):
    fixture = _contract()["development_state_fixture"]
    contract = {
        "schema": p4j.SCHEMA,
        "selected": True,
        "surface_authority": True,
        "status": fixture["expected_status"],
        "selected_core_jp": fixture["expected_visible_output"],
    }
    monkeypatch.setattr(p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "legacy")
    logic = {p4j.LABEL: deepcopy(contract), "semantic_route_m22": {"selected_type": "factual_or_memory"}}
    visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", logic
    )
    assert visible == fixture["expected_visible_output"]
    assert logic[p4j.LABEL]["final_visible_surface_matches_contract"] is True

    safety = {p4j.LABEL: deepcopy(contract), "semantic_route_m22": {"selected_type": "safety_sensitive"}}
    assert p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", safety
    ) == "legacy"


def test_materialized_graph_node_is_select_stage_and_raw_dialogue_free():
    fixture = _contract()["development_state_fixture"]
    payload = {
        "schema": p4j.SCHEMA,
        "selected": True,
        "surface_authority": True,
        "status": fixture["expected_status"],
        "active_memory_id": fixture["active_memory_id"],
        "selected_core_jp": fixture["expected_visible_output"],
        "raw_dialogue_persisted": False,
    }
    result = {
        "reply": fixture["expected_visible_output"],
        "logic": {p4j.LABEL: payload},
        "runtime_trace": {
            "blackboard": [
                {"stage": "retrieve", "label": "working_memory", "payload": {}},
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    p4j.materialize_typed_current_preference_recall_p4(result)
    node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == p4j.LABEL)
    assert node["stage"] == "select"
    assert node["payload"]["active_memory_id"] == fixture["active_memory_id"]
    assert node["payload"]["raw_dialogue_persisted"] is False
    assert "What is my current" not in repr(node)


def test_product_entry_installs_p4_j_after_p4_i_without_editing_core_runtime():
    entry = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert entry.index("install_multilingual_current_preference_p4()") < entry.index(
        "install_typed_current_preference_recall_p4()"
    )
    assert p4j.LABEL not in (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
