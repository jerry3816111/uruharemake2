from copy import deepcopy

import uruha_typed_current_preference_recall_p4 as p4j


EXPECTED = "今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。"


def _selected(memory_id="p4-k-current", surface=EXPECTED):
    return {
        "schema": p4j.SCHEMA,
        "selected": True,
        "surface_authority": True,
        "answer_use_authorized": True,
        "status": "resolved_unique_active_typed_current_preference",
        "active_memory_id": memory_id,
        "selected_core_jp": surface,
        "raw_dialogue_persisted": False,
    }


def test_normalized_logic_recovers_selected_contract_from_current_turn_memory_data(monkeypatch):
    monkeypatch.setattr(p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "legacy")
    logic = {"semantic_route_m22": {"selected_type": "factual_or_memory"}}
    memory_data = {p4j.LABEL: _selected()}

    visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", logic, memory_data=memory_data
    )

    assert visible == EXPECTED
    assert logic[p4j.LABEL]["active_memory_id"] == "p4-k-current"
    assert logic[p4j.LABEL]["final_visible_surface_matches_contract"] is True


def test_recovered_contract_materializes_one_select_node_without_raw_dialogue(monkeypatch):
    monkeypatch.setattr(p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "legacy")
    logic = {"semantic_route_m22": {"selected_type": "factual_or_memory"}}
    visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", logic, memory_data={p4j.LABEL: _selected()}
    )
    result = {
        "reply": visible,
        "logic": logic,
        "runtime_trace": {
            "blackboard": [
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }

    p4j.materialize_typed_current_preference_recall_p4(result)

    nodes = [
        row for row in result["runtime_trace"]["blackboard"] if row["label"] == p4j.LABEL
    ]
    assert len(nodes) == 1
    assert nodes[0]["stage"] == "select"
    assert nodes[0]["payload"]["raw_dialogue_persisted"] is False
    assert nodes[0]["payload"]["final_visible_surface_matches_contract"] is True


def test_safety_route_never_recovers_surface_authority_from_memory_data(monkeypatch):
    monkeypatch.setattr(
        p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "安全側の既存回答"
    )
    logic = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
    visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", logic, memory_data={p4j.LABEL: _selected()}
    )
    assert visible == "安全側の既存回答"
    assert p4j.LABEL not in logic


def test_nonselected_or_invalid_memory_contract_delegates_unchanged(monkeypatch):
    monkeypatch.setattr(p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "legacy")
    for payload in (
        {"schema": p4j.SCHEMA, "selected": False, "surface_authority": False},
        {"schema": "wrong", "selected": True, "surface_authority": True},
        {},
    ):
        logic = {"semantic_route_m22": {"selected_type": "general_conversation"}}
        visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
            object(), "model output", logic, memory_data={p4j.LABEL: payload}
        )
        assert visible == "legacy"
        assert p4j.LABEL not in logic


def test_existing_valid_logic_contract_has_priority_over_memory_data(monkeypatch):
    logic_surface = "今の飲み物の好みは麦茶。前のじゃなくて、今の方ね。"
    monkeypatch.setattr(p4j, "_ORIGINAL_VISIBLE_GUARD", lambda *_args, **_kwargs: "legacy")
    logic = {
        p4j.LABEL: _selected("logic-current", logic_surface),
        "semantic_route_m22": {"selected_type": "factual_or_memory"},
    }
    memory_data = {p4j.LABEL: _selected("memory-current", EXPECTED)}

    visible = p4j.visible_guard_with_typed_current_preference_recall_p4(
        object(), "model output", logic, memory_data=memory_data
    )

    assert visible == logic_surface
    assert logic[p4j.LABEL]["active_memory_id"] == "logic-current"
