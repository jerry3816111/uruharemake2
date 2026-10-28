from copy import deepcopy

import pytest

import m55_temporal_row_contract as temporal_m55
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56
import m56_pre_outcome_equation_artifacts as artifacts_m56
from test_m55_temporal_row_contract import synthetic_pack


def inputs():
    compiled = temporal_m55.compile_temporal_dataset_m55(synthetic_pack())
    split = preflight_m56.build_blinded_artifacts(compiled)
    packet = split["prediction_packet"]
    manifest = preflight_m56.build_fixture_run_manifest(packet)
    capsule = capsule_m56.build_execution_capsule(packet, manifest)
    bundle = artifacts_m56.materialize_artifact_bundle(packet, capsule, manifest)
    return split, packet, manifest, capsule, bundle


def bound_submission():
    split, packet, manifest, capsule, bundle = inputs()
    base = capsule_m56.build_synthetic_fixture_submission(capsule, packet, manifest)
    submission = artifacts_m56.bind_submission_to_artifacts(
        base, bundle, capsule, packet, manifest
    )
    receipt = artifacts_m56.create_equation_bound_receipt(
        submission, bundle, capsule, packet, manifest
    )
    return split, packet, manifest, capsule, bundle, submission, receipt


def rehash_bundle(bundle):
    bundle["artifact_bundle_hash"] = artifacts_m56.digest(
        {key: value for key, value in bundle.items() if key != "artifact_bundle_hash"}
    )


def rehash_submission(submission):
    submission["submission_hash"] = capsule_m56.digest(
        {key: value for key, value in submission.items() if key != "submission_hash"}
    )


def test_contract_freezes_dependency_bindings_nine_variables_and_no_authority():
    report = artifacts_m56.validate_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["binding_count"] == 7
    assert report["variable_count"] == 9
    contract = artifacts_m56.load_contract()
    assert tuple(contract["state"]["variable_ids"]) == artifacts_m56.EXPECTED_VARIABLE_IDS
    assert all(value is False for value in contract["authorization"].values())


def test_bundle_materializes_real_content_not_placeholder_hashes_and_is_deterministic():
    _, packet, manifest, capsule, first = inputs()
    second = artifacts_m56.materialize_artifact_bundle(packet, capsule, manifest)
    assert first == second
    report = artifacts_m56.validate_artifact_bundle(first, capsule, packet, manifest)
    assert report["valid"] is True
    assert report["fit_artifact_count"] == packet["sample_count"]
    assert report["state_snapshot_count"] == packet["sample_count"]
    assert report["transition_trace_count"] == packet["sample_count"]
    assert report["forbidden_key_count"] == 0
    hashes = []
    for row in first["sample_artifacts"]:
        hashes.extend(
            [
                row["fit_artifact"]["fit_artifact_hash"],
                row["state_snapshot"]["state_snapshot_hash"],
                row["transition_trace"]["transition_trace_hash"],
            ]
        )
    assert all(len(value) == 64 for value in hashes)
    assert not any(value in {"a" * 64, "b" * 64, "c" * 64} for value in hashes)


def test_first_cutoff_stays_empty_and_unknown_while_second_uses_only_completed_history():
    _, _, _, _, bundle = inputs()
    first, second = bundle["sample_artifacts"]
    assert first["fit_artifact"]["fit_basis"]["effective_sample_count"] == 0
    assert first["transition_trace"]["observable_delta"]["newly_available_history_ids"] == []
    assert second["fit_artifact"]["fit_basis"]["history_ids"] == [
        "m55-history::synthetic-m55-01"
    ]
    assert second["transition_trace"]["observable_delta"]["newly_available_history_ids"] == [
        "m55-history::synthetic-m55-01"
    ]
    assert second["transition_trace"]["observable_delta"]["fit_effective_sample_count_delta"] == 1
    for artifact_row in bundle["sample_artifacts"]:
        variables = {row["id"]: row for row in artifact_row["state_snapshot"]["variables"]}
        assert tuple(variables) == artifacts_m56.EXPECTED_VARIABLE_IDS
        for variable_id in ("transient_state", "relationship_state", "goal_need_state"):
            assert variables[variable_id]["status"] == "unavailable_not_inferred"
            assert variables[variable_id]["value"] is None
            assert variables[variable_id]["evidence_refs"] == []
        assert artifact_row["state_snapshot"]["coverage"]["private_state_fabrication_count"] == 0
    serialized = artifacts_m56.canonical(bundle)
    assert "An observable task changes" not in serialized
    assert "OUTCOME-SUMMARY" not in serialized


def test_ours_request_receives_validated_payload_and_b5_cannot_receive_it():
    _, packet, manifest, capsule, bundle = inputs()
    ours = next(
        row for row in capsule["prediction_tasks"]
        if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM
    )
    request = artifacts_m56.materialize_equation_generation_request(
        ours["task_id"], bundle, capsule, packet, manifest
    )
    assert request["condition_id"] == capsule_m56.PRIMARY_SYSTEM
    assert request["source_information_hash"] == ours["view"]["source_information_hash"]
    assert request["model_input"]["pre_outcome_fit_artifact"]["fit_artifact_hash"]
    assert request["model_input"]["pre_outcome_state_snapshot"]["state_snapshot_hash"]
    assert request["model_input"]["pre_outcome_transition_trace"]["transition_trace_hash"]
    assert request["target_access_count"] == 0
    b5 = next(
        row for row in capsule["prediction_tasks"]
        if row["condition_id"] == capsule_m56.PRIMARY_CONTROL
    )
    with pytest.raises(PermissionError, match="only for Ours"):
        artifacts_m56.materialize_equation_generation_request(
            b5["task_id"], bundle, capsule, packet, manifest
        )


def test_submission_receipt_and_separate_scorer_are_bound_to_artifact_content():
    split, packet, manifest, capsule, bundle, submission, receipt = bound_submission()
    validation = artifacts_m56.validate_bound_submission(
        submission, bundle, capsule, packet, manifest
    )
    assert validation["valid"] is True
    assert validation["bound_ours_row_count"] == packet["sample_count"]
    assert artifacts_m56.validate_equation_bound_receipt(
        receipt, submission, bundle, capsule, packet, manifest
    )["valid"] is True
    for row in submission["prediction_rows"]:
        if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM:
            assert row["fit_artifact_hash"] not in {"a" * 64, "b" * 64, "c" * 64}
        else:
            assert row["fit_artifact_hash"] is None
            assert row["state_snapshot_hash"] is None
            assert row["transition_trace_hash"] is None
    score = artifacts_m56.score_equation_bound_submission(
        submission,
        receipt,
        bundle,
        capsule,
        packet,
        manifest,
        split["split_report"],
        split["outcome_key"],
    )
    assert score["status"] == "synthetic_engineering_score_only"
    assert score["formal_result"] is False
    assert score["equation_artifact_audit"]["artifact_bundle_valid_before_score"] is True
    assert score["equation_artifact_audit"]["artifact_target_access_count"] == 0


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b["sample_artifacts"][0]["fit_artifact"]["fit_basis"].update(effective_sample_count=99),
        lambda b: b["sample_artifacts"][0]["state_snapshot"]["variables"][3].update(value="fabricated"),
        lambda b: b["sample_artifacts"][1]["transition_trace"]["observable_delta"]["newly_available_history_ids"].clear(),
        lambda b: b["sample_artifacts"][0].update(actual_observed_behavior="leak"),
    ],
)
def test_tampered_bundle_fails_closed(mutate):
    _, packet, manifest, capsule, bundle = inputs()
    changed = deepcopy(bundle)
    mutate(changed)
    rehash_bundle(changed)
    report = artifacts_m56.validate_artifact_bundle(
        changed, capsule, packet, manifest
    )
    assert report["valid"] is False
    assert report["errors"]


def test_post_cutoff_and_non_monotonic_history_fail_before_artifact_creation():
    demo_packet, _, _ = artifacts_m56.build_demo_packet()
    late_packet = deepcopy(demo_packet)
    late_history = late_packet["model_inputs"][1]["model_input"]["available_history"][0]
    late_history["available_at"] = "2026-01-03T00:00:00+00:00"
    late_packet["model_inputs"][1]["model_input_hash"] = preflight_m56.digest(
        late_packet["model_inputs"][1]["model_input"]
    )
    late_manifest = preflight_m56.build_fixture_run_manifest(late_packet)
    late_capsule = capsule_m56.build_execution_capsule(late_packet, late_manifest)
    with pytest.raises(ValueError, match="history must be completed"):
        artifacts_m56.materialize_artifact_bundle(late_packet, late_capsule, late_manifest)

    nonmonotonic_packet = deepcopy(demo_packet)
    first_history = deepcopy(
        nonmonotonic_packet["model_inputs"][1]["model_input"]["available_history"][0]
    )
    first_history.update(
        history_id="artifact-demo-history-A",
        available_at="2025-12-31T00:00:18+00:00",
        event_time="2025-12-31T00:00:01+00:00",
    )
    second_history = deepcopy(first_history)
    second_history.update(
        history_id="artifact-demo-history-B",
        available_at="2026-01-01T00:00:18+00:00",
        event_time="2026-01-01T00:00:01+00:00",
    )
    nonmonotonic_packet["model_inputs"][0]["model_input"]["available_history"] = [first_history]
    nonmonotonic_packet["model_inputs"][1]["model_input"]["available_history"] = [second_history]
    for row in nonmonotonic_packet["model_inputs"]:
        row["model_input_hash"] = preflight_m56.digest(row["model_input"])
    nonmonotonic_manifest = preflight_m56.build_fixture_run_manifest(nonmonotonic_packet)
    nonmonotonic_capsule = capsule_m56.build_execution_capsule(
        nonmonotonic_packet, nonmonotonic_manifest
    )
    with pytest.raises(ValueError, match="history must be monotonic"):
        artifacts_m56.materialize_artifact_bundle(
            nonmonotonic_packet, nonmonotonic_capsule, nonmonotonic_manifest
        )


def test_placeholder_rebinding_or_b5_artifact_exposure_is_rejected():
    _, packet, manifest, capsule, bundle, submission, _ = bound_submission()
    placeholder = deepcopy(submission)
    ours = next(row for row in placeholder["prediction_rows"] if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM)
    ours["fit_artifact_hash"] = "a" * 64
    rehash_submission(placeholder)
    report = artifacts_m56.validate_bound_submission(
        placeholder, bundle, capsule, packet, manifest
    )
    assert report["valid"] is False
    assert any("fit_artifact_hash" in error for error in report["errors"])

    exposed = deepcopy(submission)
    b5 = next(row for row in exposed["prediction_rows"] if row["condition_id"] == capsule_m56.PRIMARY_CONTROL)
    b5["state_snapshot_hash"] = bundle["sample_artifacts"][0]["state_snapshot"]["state_snapshot_hash"]
    rehash_submission(exposed)
    report = artifacts_m56.validate_bound_submission(
        exposed, bundle, capsule, packet, manifest
    )
    assert report["valid"] is False
    assert any("non_ours_artifact_exposure" in error for error in report["errors"])


def test_real_packet_kind_remains_blocked_without_new_authorization():
    _, packet, manifest, capsule, _ = inputs()
    packet = deepcopy(packet)
    packet["data_kind"] = temporal_m55.REAL_KIND
    with pytest.raises((PermissionError, ValueError)):
        artifacts_m56.materialize_artifact_bundle(packet, capsule, manifest)


def test_graphical_report_shows_real_artifacts_unknowns_and_formal_blocker():
    report = artifacts_m56.build_live_report()
    assert report["artifact_bundle_valid"] is True
    assert report["artifact_count"] == 6
    assert report["private_state_fabrication_count"] == 0
    assert report["formal_execution_authorized"] is False
    page = artifacts_m56.render_dashboard(report)
    for phrase in (
        "不再只放三串雜湊",
        "B5 / Ours",
        "Fit",
        "State",
        "Transition",
        "未知留白",
        "fit 樣本數是 0",
        "V7 0/18 + 0/18",
        "正式模型呼叫 0",
        "不證明它就是人類思考",
    ):
        assert phrase in page
    assert "OUTCOME-SUMMARY" not in page
    assert "youtube.com" not in page


def test_implementation_freeze_binds_contract_plan_module_and_tests():
    freeze = artifacts_m56.load_json(
        artifacts_m56.ROOT
        / "research/m56_pre_outcome_equation_artifacts_implementation_freeze_2026-09-02.json"
    )
    assert freeze["schema"] == "uruha_m56_pre_outcome_equation_artifacts_implementation_freeze_v1"
    assert freeze["formal_model_calls_at_freeze"] == 0
    assert freeze["target_outcome_access_at_freeze"] == 0
    assert freeze["production_memory_writes_at_freeze"] == 0
    assert freeze["real_v7_ledgers"] == "0/18 and 0/18"
    assert freeze["real_temporal_rows"] == "0/30"
    assert freeze["formal_result_created"] is False
    for relative, expected in freeze["frozen_files"].items():
        assert artifacts_m56.sha256_file(artifacts_m56.ROOT / relative) == expected
