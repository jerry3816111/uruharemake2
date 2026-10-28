from copy import deepcopy
import json

import pytest

import uruha_human_response_equation_m54 as m54
from uruha_memory_observatory import collect_cognitive_graph


RAW_INPUT = "凌晨了，這段不應該被M54原文持久化。"


def runtime_result():
    return {
        "reply": "まだ頭が止まんないなら、今は一つだけ整理しよ。",
        "logic": {
            "user_input": RAW_INPUT,
            "source_semantic_atoms_m33": {"status": "verified", "atoms": [{"kind": "time", "digest": "a" * 64}]},
            "user_mental_state_hypothesis": {"status": "provisional", "confidence": 0.55, "alternatives": ["solve", "listen"]},
            "personhood_relationship_state_v2_13": {"status": "known_user", "confidence": 0.7},
            "implicit_desired_response_m26": {
                "distribution": [
                    {"policy_id": "solve_regulation", "outcome_weighted_probability": 3.0},
                    {"policy_id": "listen_presence", "outcome_weighted_probability": 1.0},
                ],
                "top_probability": 0.75,
            },
            "task_shape_m22": {"task": "emotional_bid", "input_mode": "text"},
            "human_response_distribution_m54": [
                {"behavior_id": "offer_one_step", "probability": 2.0},
                {"behavior_id": "invite_more", "probability": 1.0},
            ],
            "causal_outcome_calibration_m27": {"supported": 2, "contradicted": 1, "unknown": 3},
            "counterfactual_pragmatic_branch_m34": {"outcome": "unknown"},
        },
        "memory_data": {
            "longitudinal_user_model_v2_13": {"records": [{"record_id": "r1", "source_id": "s1"}]},
        },
        "runtime_trace": {
            "cycle_index": 54,
            "input_context": {"input_mode": "text"},
            "blackboard": [{"label": "utterance", "stage": "speak", "payload": {"reply_digest": "b" * 64}}],
            "memory_writes": [],
        },
        "runtime_state": {
            "recent_turn_traces": [{"cycle_index": 53, "trace_digest": "c" * 64}],
        },
    }


def test_contract_defines_all_variables_measurements_interventions_and_boundaries():
    contract = m54.load_contract()
    result = m54.validate_contract_m54(contract)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["variable_count"] == 9
    assert result["output_count"] == 3
    assert [row["id"] for row in contract["variables"]] == list(m54.EXPECTED_VARIABLE_IDS)
    for row in contract["variables"]:
        assert row["measurement"] and row["interventions"] and row["forbidden_claims"]


def test_contract_rejects_inferred_factual_promotion_and_unknown_as_success():
    contract = m54.load_contract()
    contract["variables"][3]["persistence"] = "factual_memory"
    contract["outcome_update"]["unknown_counts_as_success"] = True
    result = m54.validate_contract_m54(contract)
    assert result["valid"] is False
    assert "transient_state:inferred_promoted_to_factual" in result["errors"]
    assert "unknown_must_not_count_as_success" in result["errors"]


def test_runtime_snapshot_is_normalized_source_mapped_and_raw_free():
    snapshot = m54.build_snapshot_m54(runtime_result())
    assert snapshot["status"] == "contract_valid"
    assert snapshot["coverage"]["available_variables"] == 9
    assert snapshot["coverage"]["primary_behavior_distribution_available"] is True
    assert snapshot["coverage"]["secondary_policy_distribution_available"] is True
    primary = next(row for row in snapshot["outputs"] if row["role"] == "primary")
    secondary = next(row for row in snapshot["outputs"] if row["role"] == "secondary_interactive")
    assert primary["probability_sum"] == 1.0
    assert primary["distribution"] == [
        {"label": "offer_one_step", "probability": 0.666667},
        {"label": "invite_more", "probability": 0.333333},
    ]
    assert secondary["probability_sum"] == 1.0
    payload = json.dumps(snapshot, ensure_ascii=False)
    assert RAW_INPUT not in payload
    assert "凌晨了" not in payload
    assert all(row["raw_value_persisted"] is False for row in snapshot["variables"])


def test_missing_runtime_values_remain_unavailable_instead_of_fabricated():
    snapshot = m54.build_snapshot_m54({"reply": "うん。", "logic": {}, "runtime_trace": {}})
    status = {row["id"]: row["status"] for row in snapshot["variables"]}
    assert status["person_parameter"] == "available"
    assert all(value == "unavailable_not_inferred" for key, value in status.items() if key != "person_parameter")
    assert snapshot["coverage"]["primary_behavior_distribution_available"] is False
    assert snapshot["m55_readiness"]["real_person_temporal_data_ready"] is False


def test_single_variable_intervention_changes_only_target_and_does_not_claim_recompute():
    snapshot = m54.build_snapshot_m54(runtime_result())
    intervened = m54.intervene_snapshot_m54(snapshot, "relationship_state", {"status": "removed"})
    audit = intervened["intervention"]
    assert audit["changed_variables"] == ["relationship_state"]
    assert audit["single_variable_only"] is True
    assert audit["prediction_recomputed"] is False
    assert audit["raw_replacement_persisted"] is False
    assert snapshot["snapshot_hash"] != intervened["snapshot_hash"]


def test_unknown_intervention_target_fails_closed():
    with pytest.raises(ValueError, match="unknown M54 variable"):
        m54.intervene_snapshot_m54(m54.build_snapshot_m54(runtime_result()), "private_soul", {})


def test_equation_graph_connects_every_variable_to_prediction_and_update():
    snapshot = m54.build_snapshot_m54(runtime_result())
    graph = m54.graph_payload_m54(snapshot)
    node_ids = {row["id"] for row in graph["nodes"]}
    assert len(graph["nodes"]) == 13
    for variable_id in m54.EXPECTED_VARIABLE_IDS:
        node_id = f"m54-{variable_id}"
        assert node_id in node_ids
        assert any(edge["source"] == node_id and edge["target"] == "m54-output-observable_behavior_distribution" for edge in graph["edges"])
    assert any(edge["source"] == "m54-outcome-update" and edge["target"] == "m54-structured_memory" for edge in graph["edges"])
    assert any(edge["source"] == "m54-outcome-update" and edge["target"] == "m54-uncertainty_calibration" for edge in graph["edges"])


def test_trace_materialization_is_unique_connected_read_only_and_history_synced(monkeypatch):
    result = runtime_result()
    before_reply = result["reply"]
    before_memory = deepcopy(result["memory_data"])
    result["runtime_state"]["recent_turn_traces"] = [{"cycle_index": 54}]
    monkeypatch.setattr(m54, "_PREVIOUS_MATERIALIZE", lambda result, feedback=None: None)
    m54.materialize_trace_m54(result)
    m54.materialize_trace_m54(result)
    assert result["reply"] == before_reply
    assert result["memory_data"] == before_memory
    assert result["logic"][m54.LABEL]["runtime_effect"]["added_model_calls"] == 0
    rows = [row for row in result["runtime_trace"]["blackboard"] if row.get("label") == m54.LABEL]
    assert len(rows) == 1
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m54.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"] for edge in graph["edges"])


def test_render_card_explains_coverage_and_nonproof_boundary(monkeypatch):
    monkeypatch.setattr(
        "uruha_source_neutral_scaffold_m53.render_m53",
        lambda result: '<section class="m53-flow" aria-label="M53 source neutral scaffold"></section>',
    )
    result = runtime_result()
    result["logic"][m54.LABEL] = m54.build_snapshot_m54(result)
    html = m54.render_m54(result)
    for phrase in ("人類反應方程式候選 V1", "未知就保持未知", "主要真人行為分布", "不等於已證明人類方程式"):
        assert phrase in html


def test_contract_and_snapshot_hashes_are_deterministic():
    first = m54.build_snapshot_m54(runtime_result())
    second = m54.build_snapshot_m54(runtime_result())
    assert first["contract_hash"] == second["contract_hash"]
    assert first["snapshot_hash"] == second["snapshot_hash"]
