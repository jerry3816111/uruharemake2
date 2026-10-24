from copy import deepcopy
import json

import p3_b68_future_batch_reader as reader
import p3_b68_multiwindow_future_aggregate_scoring as b68


def event(start, duration, text):
    return {"tStartMs": start, "dDurationMs": duration, "segs": [{"utf8": text}]}


def artifact(row_id, start, end, text="誰だ？"):
    return {
        "schema": "uruha_p3_b68_public_future_row_v1", "version": "1.0.0",
        "source_id": "youtube_4y5GiQpgJgo", "row_id": row_id,
        "future_seconds": [float(start), float(end)], "language_code": "ja",
        "track_type": "automatic", "format": "json3",
        "cues": [{"start_seconds": float(start + 1), "end_seconds": float(start + 2), "text": text}],
    }


def test_contract_binds_predictions_rows_and_unchanged_b66_metrics():
    assert b68.validate_contract() == {"valid": True, "errors": []}
    contract = b68.load_contract()
    assert contract["source"]["rows"] == b68.expected_rows()
    assert contract["source"]["unlock_all_rows_together"] is True
    assert contract["scoring"]["reuse_b66_proxy_marker_order_without_change"] is True
    assert contract["scoring"]["model_human_or_llm_judge_call_count_required"] == 0
    assert all(contract["denied_actions"].values())


def test_extract_batch_excludes_before_crossing_and_after_cues():
    events = []
    for row in b68.expected_rows():
        start, end = row["future_milliseconds"]
        events += [event(start - 1000, 500, "before"), event(start, 1000, row["row_id"]), event(end - 500, 1000, "cross")]
    artifacts = b68.extract_future_batch(json.dumps({"events": events}).encode())
    assert [item["row_id"] for item in artifacts] == ["r0600", "r1200", "r1800", "r2400"]
    assert all([cue["text"] for cue in item["cues"]] == [item["row_id"]] for item in artifacts)


def test_publish_and_fresh_batch_reader(monkeypatch, tmp_path):
    artifacts = [artifact("r0600", 781, 841), artifact("r1200", 1381, 1441), artifact("r1800", 1981, 2041), artifact("r2400", 2581, 2641)]
    root = tmp_path / "future"
    manifests = b68.publish_batch(artifacts, root, b68.load_contract())
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(root))
    batch = reader.read_batch([item["artifact_id"] for item in manifests])
    assert [row["artifact"]["row_id"] for row in batch["rows"]] == ["r0600", "r1200", "r1800", "r2400"]
    assert batch["context_content_returned"] is False


def test_aggregate_scores_counts_wins_and_means():
    rows = []
    for index in range(4):
        rows.append({
            "proxy_winner": "SYSTEM_PRAGMATIC_STATE" if index < 3 else "BASELINE_LITERAL",
            "scores": [
                {"condition": "BASELINE_LITERAL", "selected_label_hit": index == 3, "actual_label_probability": 0.2, "multiclass_brier": 1.0, "log_loss": 1.6},
                {"condition": "SYSTEM_PRAGMATIC_STATE", "selected_label_hit": index < 2, "actual_label_probability": 0.4, "multiclass_brier": 0.8, "log_loss": 1.0},
            ],
        })
    aggregate = b68.aggregate_scores(rows)
    assert aggregate["row_wins"] == {"BASELINE_LITERAL": 1, "SYSTEM_PRAGMATIC_STATE": 3, "TIE": 0}
    assert aggregate["BASELINE_LITERAL"]["mean_actual_label_probability"] == 0.2
    assert aggregate["SYSTEM_PRAGMATIC_STATE"]["top1_hits"] == 2


def test_contract_rejects_row_metric_or_judge_drift():
    contract = b68.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["rows"][0]["future_milliseconds"] = [780000, 840000]
    assert "rows" in b68.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["scoring"]["reuse_b66_proxy_marker_order_without_change"] = False
    assert "scoring:reuse_b66_proxy_marker_order_without_change" in b68.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["scoring"]["model_human_or_llm_judge_call_count_required"] = 1
    assert "scoring_calls" in b68.validate_contract(drifted)["errors"]


def test_implementation_freeze_matches_frozen_files():
    assert b68.validate_implementation_freeze() == {
        "valid": True,
        "future_outcome_access_count_at_freeze": 0,
    }
