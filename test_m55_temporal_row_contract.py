from copy import deepcopy
import json

import pytest

from longitudinal_human_model.temporal import build_model_input
import audit_m55_real_person_longitudinal_readiness as readiness_m55
import m55_temporal_row_contract as temporal_m55


def synthetic_pack():
    contract_hash = temporal_m55.validate_contract_m55()["contract_hash"]
    common = {
        "sampling_slot_id": "synthetic-slot-01",
        "source_id": "synthetic-source-01",
        "source_published_at": "2026-01-01",
        "event_start_seconds": 0,
        "observable_input_start_seconds": 1,
        "prediction_cutoff_seconds": 10,
        "observable_behavior_start_seconds": 12,
        "observable_behavior_end_seconds": 18,
        "event_end_seconds": 20,
        "observable_input_paraphrase": "An observable task changes before the response.",
        "completed_event_summary": "OUTCOME-SUMMARY-ONE becomes historical only after second 18.",
        "behavior_label": "ask_or_check",
        "acceptable_behavior_labels": ["ask_or_check"],
        "annotation_confidence": 0.8,
        "context_family": "competitive_task",
        "observable_audience_relation": "familiar_peer",
        "independent_coder_count": 0,
        "review_status": "synthetic_engineering_only",
        "prediction_boundary_attestation": True,
        "outcome_excluded_from_input_attestation": True,
        "paraphrase_and_no_quote_attestation": True,
    }
    first = {"sample_id": "synthetic-m55-01", **common}
    second = {
        **common,
        "sample_id": "synthetic-m55-02",
        "sampling_slot_id": "synthetic-slot-02",
        "source_id": "synthetic-source-02",
        "source_published_at": "2026-01-02",
        "observable_input_paraphrase": "A second observable task appears on the next day.",
        "completed_event_summary": "OUTCOME-SUMMARY-TWO remains sealed for its own prediction.",
        "behavior_label": "support_or_reassure",
        "acceptable_behavior_labels": ["support_or_reassure"],
    }
    return {
        "schema": temporal_m55.SCHEMA,
        "version": "1.0.0",
        "data_kind": temporal_m55.SYNTHETIC_KIND,
        "status": "synthetic_compiler_contract_only",
        "dataset_id": "synthetic-m55-temporal-contract-v1",
        "target_id": "synthetic_m55_contract_subject",
        "contract_hash": contract_hash,
        "records": [first, second],
    }


def real_shaped_pack():
    pack = synthetic_pack()
    frame = temporal_m55.load_json(
        temporal_m55.ROOT / "datasets/public_persona_target_calibration_sampling_frame_v9.json"
    )
    sources = temporal_m55.load_json(
        temporal_m55.ROOT / "datasets/public_persona_target_calibration_source_metadata_v9.json"
    )
    slot = frame["sampling_slots"][0]
    source = next(row for row in sources["sources"] if row["source_id"] == slot["source_id"])
    start = slot["search_start_seconds"]
    record = pack["records"][0]
    record.update(
        sampling_slot_id=slot["sampling_slot_id"],
        source_id=slot["source_id"],
        source_published_at=source["published_at"],
        event_start_seconds=start,
        observable_input_start_seconds=start,
        prediction_cutoff_seconds=start + 1,
        observable_behavior_start_seconds=start + 2,
        observable_behavior_end_seconds=start + 3,
        event_end_seconds=start + 4,
        independent_coder_count=2,
        review_status="agreed_independent_codes",
    )
    pack.update(
        data_kind=temporal_m55.REAL_KIND,
        target_id="ichinose_uruha_public_persona",
        records=[record],
    )
    return pack


def test_contract_has_valid_bindings_nine_variables_and_fail_closed_authorization():
    report = temporal_m55.validate_contract_m55()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["variable_count"] == 9
    contract = temporal_m55.load_contract()
    assert contract["authorization"]["synthetic_fixture_authorizes_m56"] is False
    assert contract["authorization"]["m55_compiler_alone_authorizes_m56"] is False


def test_current_v9_event_schema_cannot_silently_substitute_whole_event_boundary():
    report = temporal_m55.audit_current_v9_boundary_gap()
    assert report["current_v9_event_start_available"] is True
    assert report["current_v9_event_end_available"] is True
    assert report["current_v9_alone_compilable"] is False
    assert report["missing_boundary_extension_fields"] == list(
        temporal_m55.BOUNDARY_EXTENSION_FIELDS
    )
    assert report["boundary_extension_required_before_target_temporal_compilation"] is True


def test_synthetic_pack_compiles_to_existing_temporal_schema_without_current_outcome_leak():
    result = temporal_m55.compile_temporal_dataset_m55(synthetic_pack())
    dataset = result["dataset"]
    audit = result["audit"]
    assert audit["future_leakage_violations"] == 0
    assert audit["current_outcome_summary_leak_count"] == 0
    assert audit["model_execution_authorized"] is False
    assert audit["formal_target_claim"] is False
    assert len(dataset["history"]) == 2
    assert dataset["samples"][0]["available_history_ids"] == []
    assert dataset["samples"][1]["available_history_ids"] == ["m55-history::synthetic-m55-01"]
    first_view = json.dumps(build_model_input(dataset, dataset["samples"][0]), ensure_ascii=False)
    second_view = json.dumps(build_model_input(dataset, dataset["samples"][1]), ensure_ascii=False)
    assert "OUTCOME-SUMMARY-ONE" not in first_view
    assert "OUTCOME-SUMMARY-ONE" in second_view
    assert "OUTCOME-SUMMARY-TWO" not in second_view
    assert "actual_observed_behavior" not in second_view
    assert "annotation_confidence" not in second_view


def test_compilation_is_deterministic():
    first = temporal_m55.compile_temporal_dataset_m55(synthetic_pack())
    second = temporal_m55.compile_temporal_dataset_m55(synthetic_pack())
    assert first["dataset"]["dataset_hash"] == second["dataset"]["dataset_hash"]
    assert first["audit"]["audit_hash"] == second["audit"]["audit_hash"]


def test_prediction_cutoff_must_be_strictly_before_behavior_start():
    pack = synthetic_pack()
    pack["records"][0]["prediction_cutoff_seconds"] = 12
    report = temporal_m55.validate_record_pack_m55(pack)
    assert report["valid"] is False
    assert "records[0]:prediction_boundary_order_invalid" in report["errors"]


def test_false_boundary_attestation_and_raw_payload_fail_closed():
    pack = synthetic_pack()
    pack["records"][0]["outcome_excluded_from_input_attestation"] = False
    pack["records"][0]["raw_text"] = "forbidden verbatim material"
    report = temporal_m55.validate_record_pack_m55(pack)
    assert report["valid"] is False
    assert "records[0].outcome_excluded_from_input_attestation:required" in report["errors"]
    assert any(error.startswith("forbidden_content_key:") for error in report["errors"])


def test_uncontracted_outcome_field_and_overlapping_events_fail_closed():
    pack = synthetic_pack()
    pack["records"][0]["observable_behavior_paraphrase"] = "must remain outcome-side"
    pack["records"][1]["source_id"] = pack["records"][0]["source_id"]
    pack["records"][1]["source_published_at"] = pack["records"][0]["source_published_at"]
    report = temporal_m55.validate_record_pack_m55(pack)
    assert report["valid"] is False
    assert any("observable_behavior_paraphrase" in error for error in report["errors"])
    assert any(error.startswith("records:overlap:") for error in report["errors"])


def test_synthetic_fixture_cannot_impersonate_two_human_review():
    pack = synthetic_pack()
    pack["records"][0]["independent_coder_count"] = 2
    pack["records"][0]["review_status"] = "agreed_independent_codes"
    report = temporal_m55.validate_record_pack_m55(pack)
    assert report["valid"] is False
    assert "records[0]:synthetic_must_not_impersonate_human_review" in report["errors"]


def test_real_shaped_pack_is_blocked_by_live_human_gate_even_if_row_shape_is_valid():
    pack = real_shaped_pack()
    assert temporal_m55.validate_record_pack_m55(pack)["valid"] is True
    with pytest.raises(PermissionError, match="human reliability"):
        temporal_m55.compile_temporal_dataset_m55(
            pack,
            readiness=readiness_m55.build_readiness_m55(),
        )


def test_graphical_contract_explains_cutoff_future_and_current_zero_rows_without_private_data():
    page = temporal_m55.render_temporal_contract_m55(human_row_count=0)
    for phrase in (
        "可觀察輸入 X",
        "cutoff",
        "未見行為 Y",
        "目前正式真人列：0",
        "現有 V9 單獨可編譯：否",
        "M56 仍禁止",
        "unavailable_not_inferred",
    ):
        assert phrase in page
    assert "token=" not in page
    assert "youtube.com" not in page
    assert "OUTCOME-SUMMARY" not in page


def test_contract_rejects_crosswalk_that_promotes_unknown_state():
    contract = temporal_m55.load_contract()
    contract["equation_variable_crosswalk"][3]["variable_id"] = "private_true_emotion"
    report = temporal_m55.validate_contract_m55(contract)
    assert report["valid"] is False
    assert "equation_variable_crosswalk_mismatch" in report["errors"]
