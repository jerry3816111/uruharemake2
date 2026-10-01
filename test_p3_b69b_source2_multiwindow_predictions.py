from copy import deepcopy
import json

import pytest

import p3_b65_bounded_joint_prediction_interface as b65
import p3_b69b_context_batch_reader as reader
import p3_b69b_source2_multiwindow_predictions as b69b


def caption_event(start, duration, text):
    return {"tStartMs": start, "dDurationMs": duration, "segs": [{"utf8": text}]}


def context_artifact(row_id, start, end):
    return {
        "schema": "uruha_p3_b69b_public_context_row_v1",
        "version": "1.0.0",
        "source_id": "youtube_Mlk5e3hBnb8",
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
    }


def completed_result():
    rows = ["s2r0600", "s2r1200", "s2r1800", "s2r2400"]
    conditions = ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]
    records, predictions = [], []
    for row_id in rows:
        for condition in conditions:
            records.append({
                "call_index": len(records) + 1,
                "row_id": row_id,
                "condition": condition,
                "status": "completed",
                "num_predict": 512,
                "prompt_tokens": 100,
                "completion_tokens": 100,
                "latency_seconds": 0.5,
            })
            predictions.append(prediction(row_id, condition))
    result = {
        "schema": "uruha_p3_b69b_source2_multiwindow_prediction_result_v1",
        "version": "1.0.0",
        "status": "prediction_batch_frozen",
        "source_id": "youtube_Mlk5e3hBnb8",
        "row_order": rows,
        "condition_order": conditions,
        "model": "qwen3.5:9b",
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
        "fresh_context_reader_exit_code": 0,
        "fresh_reader_future_content_returned": False,
        "model_call_count": 8,
        "prediction_count": 8,
        "call_records": records,
        "predictions": predictions,
    }
    return b69b._finalize_result(result)


def test_contract_binds_frozen_source2_rows_and_b65_interface():
    assert b69b.validate_contract() == {"valid": True, "errors": []}
    contract = b69b.load_contract()
    assert contract["source"]["rows"] == b69b.expected_rows()
    assert contract["source"]["source_id"] == "youtube_Mlk5e3hBnb8"
    experiment = contract["prediction_experiment"]
    assert experiment["model_call_count_exact"] == 8
    assert experiment["completion_token_ceiling_each_condition"] == 512
    assert all(contract["denied_actions"].values())


def test_source2_downloader_contract_changes_only_source_identity():
    contract = b69b._source2_downloader_contract(b69b.load_contract())
    assert contract["source"]["video_id"] == "Mlk5e3hBnb8"
    assert contract["source"]["source_id"] == "youtube_Mlk5e3hBnb8"
    command = b69b.b61.build_native_downloader_command(__import__("pathlib").Path("/tmp/private"), contract)
    assert command[-1].endswith("Mlk5e3hBnb8")
    assert "4y5GiQpgJgo" not in command[-1]
    assert command[command.index("--retries") + 1] == "0"


def test_context_projection_publishes_only_complete_context_cues():
    events = []
    for row in b69b.expected_rows():
        start, end = row["context_milliseconds"]
        events.extend([
            caption_event(start - 1000, 500, "before"),
            caption_event(start, 1000, row["row_id"]),
            caption_event(end - 500, 1000, "crosses"),
            caption_event(row["future_milliseconds"][0], 1000, "future"),
        ])
    artifacts = b69b.extract_context_batch(json.dumps({"events": events}).encode("utf-8"))
    assert [artifact["row_id"] for artifact in artifacts] == ["s2r0600", "s2r1200", "s2r1800", "s2r2400"]
    assert all([cue["text"] for cue in artifact["cues"]] == [artifact["row_id"]] for artifact in artifacts)
    assert all("future" not in json.dumps(artifact) for artifact in artifacts)


def test_public_batch_reader_returns_four_source2_rows_without_future(monkeypatch, tmp_path):
    artifacts = [
        context_artifact("s2r0600", 600, 780),
        context_artifact("s2r1200", 1200, 1380),
        context_artifact("s2r1800", 1800, 1980),
        context_artifact("s2r2400", 2400, 2580),
    ]
    root = tmp_path / "public"
    manifests = b69b.publish_context_batch(artifacts, root)
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(root))
    batch = reader.read_batch([manifest["artifact_id"] for manifest in manifests])
    assert [row["artifact"]["row_id"] for row in batch["rows"]] == list(reader.ROW_BOUNDARIES)
    assert batch["future_content_returned"] is False


def test_b69b_uses_exact_b65_prompt_schema_and_parser_contract():
    artifact = context_artifact("s2r0600", 600, 780)
    contract = b65.load_contract()
    for condition in ("BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"):
        prompt = b65.joint_prompt(condition, artifact, contract)
        assert json.loads(prompt)["condition"] == condition
        assert b65.joint_schema(contract["target"]["candidate_behavior_labels"])["additionalProperties"] is False


def test_complete_result_accepts_eight_predictions_with_futures_locked():
    result = completed_result()
    assert b69b.validate_result(result) == {"valid": True, "errors": []}
    assert result["model_call_count"] == 8
    assert result["prediction_side_future_access_count"] == 0
    assert result["outcome_score_count"] == 0


def test_result_rejects_partial_success_future_or_budget_drift():
    result = completed_result()
    result["model_call_count"] = 7
    result["call_records"] = result["call_records"][:7]
    result["prediction_count"] = 7
    result["predictions"] = result["predictions"][:7]
    result = b69b._finalize_result({key: value for key, value in result.items() if key != "result_hash"})
    assert "counts" in b69b.validate_result(result)["errors"]
    result = completed_result()
    result["prediction_side_future_access_count"] = 1
    result["call_records"][0]["num_predict"] = 768
    result = b69b._finalize_result({key: value for key, value in result.items() if key != "result_hash"})
    report = b69b.validate_result(result)
    assert "prediction_side_future_access_count" in report["errors"]
    assert "call_record" in report["errors"]


def test_contract_drift_in_source_rows_interface_or_future_fails():
    contract = b69b.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["video_id"] = "other"
    assert "source" in b69b.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["source"]["rows"][0]["future_milliseconds"] = [780000, 840000]
    assert "source_rows" in b69b.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["prediction_experiment"]["model"] = "qwen3.5:27b"
    assert "experiment" in b69b.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["source"]["prediction_side_future_access_before_complete_batch_required"] = 1
    assert "source_boundary" in b69b.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_caption_or_model(monkeypatch, tmp_path):
    monkeypatch.setattr(b69b, "ROOT", tmp_path)
    contract = b69b.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(Exception, match="already consumed"):
        b69b._fresh_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b69b.validate_implementation_freeze() == {
        "valid": True,
        "model_call_count_at_freeze": 0,
        "prediction_side_future_access_count_at_freeze": 0,
    }
