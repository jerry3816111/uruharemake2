from copy import deepcopy
import json

import p3_b71c_future_batch_reader as reader
import p3_b71c_source3_future_aggregate_scoring as b71c


def event(start, duration, text): return {"tStartMs": start, "dDurationMs": duration, "segs": [{"utf8": text}]}


def artifact(row_id, start, end, text="誰だ？"):
    return {"schema": "uruha_p3_b71c_public_future_row_v1", "version": "1.0.0", "source_id": "youtube_j6Hlk9cY9LQ", "row_id": row_id, "future_seconds": [float(start), float(end)], "language_code": "ja", "track_type": "automatic", "format": "json3", "cues": [{"start_seconds": float(start + 1), "end_seconds": float(start + 2), "text": text}]}


def test_contract_binds_predictions_source3_and_unchanged_metrics():
    assert b71c.validate_contract() == {"valid": True, "errors": []}
    contract = b71c.load_contract()
    assert contract["source"]["rows"] == b71c.expected_rows()
    assert contract["source"]["unlock_all_rows_together"] is True
    assert contract["scoring"]["reuse_b66_proxy_marker_order_without_change"] is True
    assert contract["scoring"]["reuse_b68_aggregate_metrics_without_change"] is True
    assert all(contract["denied_actions"].values())


def test_extract_excludes_before_crossing_and_context_cues():
    events = []
    for row in b71c.expected_rows():
        start, end = row["future_milliseconds"]
        events += [event(start - 1000, 500, "before"), event(start, 1000, row["row_id"]), event(end - 500, 1000, "cross")]
    artifacts = b71c.extract_future_batch(json.dumps({"events": events}).encode())
    assert [item["row_id"] for item in artifacts] == ["s3r0600", "s3r1200", "s3r1800", "s3r2400"]
    assert all([cue["text"] for cue in item["cues"]] == [item["row_id"]] for item in artifacts)


def test_publish_and_fresh_reader_are_prediction_bound(monkeypatch, tmp_path):
    artifacts = [artifact("s3r0600", 781, 841), artifact("s3r1200", 1381, 1441), artifact("s3r1800", 1981, 2041), artifact("s3r2400", 2581, 2641)]
    root = tmp_path / "future"; manifests = b71c.publish_batch(artifacts, root, b71c.load_contract()); monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(root))
    batch = reader.read_batch([item["artifact_id"] for item in manifests])
    assert [row["artifact"]["row_id"] for row in batch["rows"]] == list(reader.ROW_BOUNDARIES)
    assert batch["context_content_returned"] is False
    assert all(item["prediction_batch_result_hash"] == b71c.PREDICTION_RESULT_HASH for item in manifests)


def test_contract_rejects_prediction_row_metric_or_judge_drift():
    contract = b71c.load_contract(); drifted = deepcopy(contract); drifted["source"]["rows"][0]["future_milliseconds"] = [780000, 840000]
    assert "source" in b71c.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract); drifted["scoring"]["reuse_b66_proxy_marker_order_without_change"] = False
    assert "scoring:reuse_b66_proxy_marker_order_without_change" in b71c.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract); drifted["scoring"]["model_human_or_llm_judge_call_count_required"] = 1
    assert "calls" in b71c.validate_contract(drifted)["errors"]


def test_result_accepts_complete_scoring_and_rejects_mutation():
    rows = [{"row_id": row, "scores": [], "proxy_winner": "TIE"} for row in ["s3r0600", "s3r1200", "s3r1800", "s3r2400"]]
    result = {"schema": "uruha_p3_b71c_source3_future_aggregate_result_v1", "version": "1.0.0", "status": "aggregate_scored", "prediction_batch_result_hash": b71c.PREDICTION_RESULT_HASH, "prediction_mutation_count": 0, "model_human_or_llm_judge_call_count": 0, "retry_count": 0, "fallback_count": 0, "training_write_count": 0, "formal_m56_write_count": 0, "production_memory_write_count": 0, "future_outcome_access_count": 4, "outcome_score_count": 8, "private_deleted_before_public_scoring": True, "public_artifact_count": 4, "rows": rows, "aggregate": {}}
    b71c._finalize(result); assert b71c.validate_result(result) == {"valid": True, "errors": []}
    result["prediction_mutation_count"] = 1; result = b71c._finalize({k: v for k, v in result.items() if k != "result_hash"})
    assert "prediction_mutation_count" in b71c.validate_result(result)["errors"]


def test_implementation_freeze_matches_frozen_files():
    assert b71c.validate_implementation_freeze() == {"valid": True, "future_access_count_at_freeze": 0}
