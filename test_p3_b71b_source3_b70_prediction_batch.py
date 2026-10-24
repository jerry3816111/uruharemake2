from copy import deepcopy
import json
from pathlib import Path

import pytest

import p3_b65_bounded_joint_prediction_interface as b65
import p3_b70_prediction_interface_reliability as b70
import p3_b71b_context_batch_reader as reader
import p3_b71b_source3_b70_prediction_batch as b71b


def caption_event(start, duration, text):
    return {"tStartMs": start, "dDurationMs": duration, "segs": [{"utf8": text}]}


def context_artifact(row_id, start, end):
    return {
        "schema": "uruha_p3_b71b_public_context_row_v1",
        "version": "1.0.0",
        "source_id": "youtube_j6Hlk9cY9LQ",
        "row_id": row_id,
        "context_seconds": [float(start), float(end)],
        "language_code": "ja",
        "track_type": "automatic",
        "format": "json3",
        "cues": [{"start_seconds": float(start + 1), "end_seconds": float(start + 2), "text": f"{row_id}の会話。"}],
    }


def prediction(row_id, condition):
    labels = b65.load_contract()["target"]["candidate_behavior_labels"]
    probabilities = {label: 0.1 for label in labels}
    probabilities["acknowledge_then_continue"] = 0.5
    return {
        "row_id": row_id,
        "condition": condition,
        "probabilities": probabilities,
        "selected_behavior": "acknowledge_then_continue",
        "predicted_next_content": "そのまま話を続けると思う。",
        "brief_evidence": "直前の流れが継続している。",
        "state_sha256": "a" * 64,
        "state_persisted": False,
        "raw_prompt_or_response_persisted": False,
        "input_weight_sum": 10.0,
        "normalization_applied": True,
        "normalization_decimal_places": 12,
        "residual_assigned_to": "acknowledge_then_continue",
        "selected_behavior_preserved": True,
        "normalization_contract": "p3_b70_v1",
    }


def completed_result():
    rows = ["s3r0600", "s3r1200", "s3r1800", "s3r2400"]
    conditions = ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]
    records, predictions = [], []
    for row_id in rows:
        for condition in conditions:
            records.append({"call_index": len(records) + 1, "row_id": row_id, "condition": condition, "status": "completed", "num_predict": 512, "prompt_tokens": 100, "completion_tokens": 100, "latency_seconds": 0.5})
            predictions.append(prediction(row_id, condition))
    result = {
        "schema": "uruha_p3_b71b_source3_b70_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_batch_frozen",
        "source_id": "youtube_j6Hlk9cY9LQ",
        "row_order": rows,
        "condition_order": conditions,
        "model": "qwen3.5:9b",
        "interface": "b65_joint_prompt_with_b70_probability_adapter",
        "native_downloader_process_invocation_count": 1,
        "downloader_returncode": 0,
        "private_full_caption_access_count": 1,
        "private_full_caption_filename_persisted": False,
        "private_full_caption_hash_persisted": False,
        "raw_full_caption_persisted": False,
        "future_cues_or_ranges_persisted": False,
        "private_full_caption_deleted_before_context_reader_and_model": True,
        "private_runtime_deleted_before_context_reader_and_model": True,
        "prediction_side_future_access_count": 0,
        "outcome_score_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "public_context_artifact_count": 4,
        "fresh_context_reader_count": 1,
        "fresh_reader_future_content_returned": False,
        "model_call_count": 8,
        "prediction_count": 8,
        "call_records": records,
        "predictions": predictions,
    }
    return b71b._finalize_result(result)


def test_contract_binds_source3_b65_and_same_b70_adapter_for_both_conditions():
    assert b71b.validate_contract() == {"valid": True, "errors": []}
    contract = b71b.load_contract()
    assert contract["source"]["rows"] == b71b.expected_rows()
    experiment = contract["prediction_experiment"]
    assert experiment["reuse_b65_joint_prompt_model_schema_and_options"] is True
    assert experiment["use_b70_parser_adapter_for_both_conditions"] is True
    assert experiment["model_call_count_exact"] == 8
    assert experiment["completion_token_ceiling_each_condition"] == 512
    assert all(contract["denied_actions"].values())


def test_source3_downloader_contract_changes_only_source_identity():
    contract = b71b._source3_downloader_contract(b71b.load_contract())
    assert contract["source"]["video_id"] == "j6Hlk9cY9LQ"
    command = b71b.b61.build_native_downloader_command(Path("/tmp/private"), contract)
    assert command[-1].endswith("j6Hlk9cY9LQ")
    assert command[command.index("--retries") + 1] == "0"


def test_projection_excludes_crossing_and_future_cues():
    events = []
    for row in b71b.expected_rows():
        start, end = row["context_milliseconds"]
        events.extend([
            caption_event(start, 1000, row["row_id"]),
            caption_event(end - 500, 1000, "crosses"),
            caption_event(row["future_milliseconds"][0], 1000, "future"),
        ])
    artifacts = b71b.b69b.extract_context_batch(json.dumps({"events": events}).encode(), b71b.load_contract())
    assert [artifact["row_id"] for artifact in artifacts] == ["s3r0600", "s3r1200", "s3r1800", "s3r2400"]
    assert all([cue["text"] for cue in artifact["cues"]] == [artifact["row_id"]] for artifact in artifacts)
    assert all("future" not in json.dumps(artifact) for artifact in artifacts)


def test_reader_returns_four_source3_rows_and_no_future(monkeypatch, tmp_path):
    artifacts = [
        context_artifact("s3r0600", 600, 780),
        context_artifact("s3r1200", 1200, 1380),
        context_artifact("s3r1800", 1800, 1980),
        context_artifact("s3r2400", 2400, 2580),
    ]
    root = tmp_path / "public"
    manifests = b71b.publish_context_batch(artifacts, root)
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(root))
    batch = reader.read_batch([manifest["artifact_id"] for manifest in manifests])
    assert [row["artifact"]["row_id"] for row in batch["rows"]] == list(reader.ROW_BOUNDARIES)
    assert batch["future_content_returned"] is False


@pytest.mark.parametrize("condition", ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"])
def test_b70_adapter_normalizes_same_weight_vector_for_both_conditions(condition):
    labels = b65.load_contract()["target"]["candidate_behavior_labels"]
    raw = {
        "state": {"observed_literal": "会話中。", "interpretation": "継続したい。", "alternative": "独り言かもしれない。", "confidence": 0.5},
        "probabilities": {label: value for label, value in zip(labels, [2, 3, 1, 1, 1, 2])},
        "predicted_next_content": "もう少し話を続ける。",
        "brief_evidence": "直前の会話。",
    }
    parsed = b70.parse_joint_output_normalized(json.dumps(raw, ensure_ascii=False), condition)
    assert parsed["normalization_applied"] is True
    assert parsed["input_weight_sum"] == 10.0
    assert parsed["selected_behavior_preserved"] is True


def test_complete_result_requires_eight_b70_bound_predictions_and_locked_future():
    result = completed_result()
    assert b71b.validate_result(result) == {"valid": True, "errors": []}
    assert result["model_call_count"] == 8
    assert result["prediction_side_future_access_count"] == 0
    assert all(item["normalization_contract"] == "p3_b70_v1" for item in result["predictions"])


def test_result_rejects_partial_future_budget_or_missing_adapter():
    result = completed_result()
    result["model_call_count"] = 7
    result["call_records"] = result["call_records"][:7]
    result["prediction_count"] = 7
    result["predictions"] = result["predictions"][:7]
    result = b71b._finalize_result({key: value for key, value in result.items() if key != "result_hash"})
    assert "predictions" in b71b.validate_result(result)["errors"]
    result = completed_result()
    result["prediction_side_future_access_count"] = 1
    result["call_records"][0]["num_predict"] = 768
    result["predictions"][0]["normalization_contract"] = "other"
    result = b71b._finalize_result({key: value for key, value in result.items() if key != "result_hash"})
    report = b71b.validate_result(result)
    assert "prediction_side_future_access_count" in report["errors"]
    assert "records" in report["errors"]
    assert "adapter_or_persistence" in report["errors"]


def test_contract_drift_in_source_adapter_or_budget_fails():
    contract = b71b.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["video_id"] = "Mlk5e3hBnb8"
    assert "source" in b71b.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["prediction_experiment"]["use_b70_parser_adapter_for_both_conditions"] = False
    assert "experiment" in b71b.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["prediction_experiment"]["completion_token_ceiling_each_condition"] = 768
    assert "experiment" in b71b.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_caption_or_model(monkeypatch, tmp_path):
    monkeypatch.setattr(b71b, "ROOT", tmp_path)
    contract = b71b.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(Exception, match="already consumed"):
        b71b._fresh_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b71b.validate_implementation_freeze() == {"valid": True, "model_call_count_at_freeze": 0, "future_access_count_at_freeze": 0}
