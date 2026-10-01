from copy import deepcopy

import p3_b51_temporal_forecast_bridge as bridge


def test_bridge_maps_task_a_to_existing_frozen_stack_without_execution():
    report = bridge.validate_temporal_forecast_bridge()

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["mapped_condition_count"] == 5
    assert report["related_work_count"] >= 6
    assert report["formal_model_calls"] == 0
    assert report["target_outcome_access"] == 0
    assert report["new_source_selected"] is False
    assert report["formal_result_created"] is False


def test_bridge_rejects_condition_remapping_that_weakens_primary_control():
    contract = bridge.load_bridge_contract()
    weakened = deepcopy(contract)
    for row in weakened["task_a_condition_mapping"]:
        if row["task_a_role"] == "strong_same_information_control":
            row["m56_condition_id"] = "B1_BASE_LLM"

    report = bridge.validate_temporal_forecast_bridge(weakened)

    assert report["valid"] is False
    assert "task_a_condition_mapping_mismatch" in report["errors"]


def test_bridge_rejects_any_attempt_to_authorize_outcome_access_or_generation():
    contract = bridge.load_bridge_contract()
    opened = deepcopy(contract)
    opened["execution_boundary"]["model_calls_authorized"] = True
    opened["execution_boundary"]["target_outcome_access_authorized"] = True

    report = bridge.validate_temporal_forecast_bridge(opened)

    assert report["valid"] is False
    assert "bridge_execution_boundary_open" in report["errors"]


def test_bridge_rejects_unpinned_related_work_or_missing_adopted_scope():
    contract = bridge.load_bridge_contract()
    unpinned = deepcopy(contract)
    unpinned["related_work_inputs"][0]["primary_url"] = ""
    unpinned["related_work_inputs"][0]["adopted_scope"] = ""

    report = bridge.validate_temporal_forecast_bridge(unpinned)

    assert report["valid"] is False
    assert "primary_2026_source_map_incomplete" in report["errors"]


def test_bridge_rejects_stale_or_replaced_dependency_hash():
    contract = bridge.load_bridge_contract()
    stale = deepcopy(contract)
    stale["bindings"]["temporal_row_contract"]["sha256"] = "0" * 64

    report = bridge.validate_temporal_forecast_bridge(stale)

    assert report["valid"] is False
    assert "binding_hash_mismatch:temporal_row_contract" in report["errors"]
