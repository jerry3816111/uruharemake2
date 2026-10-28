from copy import deepcopy
import json

import pytest

import p3_b65_bounded_joint_prediction_interface as b65
import p3_b66_future_outcome_reader as reader
import p3_b66_future_outcome_unlock_scoring as b66


def event(start, duration, text):
    return {"tStartMs": start, "dDurationMs": duration, "segs": [{"utf8": text}]}


def future_artifact():
    return {
        "schema": "uruha_p3_b66_public_future_outcome_v1",
        "version": "1.0.0",
        "source_id": "youtube_4y5GiQpgJgo",
        "future_seconds": [3181.0, 3241.0],
        "language_code": "ja",
        "track_type": "automatic",
        "format": "json3",
        "cues": [
            {"start_seconds": 3182.0, "end_seconds": 3183.0, "text": "左は誰だ？"},
            {"start_seconds": 3184.0, "end_seconds": 3185.0, "text": "確認する。"},
            {"start_seconds": 3190.0, "end_seconds": 3191.0, "text": "次へ行く。"},
            {"start_seconds": 3200.0, "end_seconds": 3201.0, "text": "範囲外の対象。"},
        ],
    }


def result_shell():
    scores = [
        {
            "condition": "BASELINE_LITERAL",
            "selected_behavior": "accept_support_and_continue",
            "selected_label_hit": False,
            "actual_label_probability": 0.05,
            "multiclass_brier": 1.4,
            "log_loss": 2.995732273554,
            "character_bigram_jaccard": 0.1,
        },
        {
            "condition": "SYSTEM_PRAGMATIC_STATE",
            "selected_behavior": "acknowledge_then_continue",
            "selected_label_hit": False,
            "actual_label_probability": 0.1,
            "multiclass_brier": 1.2,
            "log_loss": 2.302585092994,
            "character_bigram_jaccard": 0.2,
        },
    ]
    result = {
        "schema": "uruha_p3_b66_future_outcome_scored_result_v1",
        "version": "1.0.0",
        "status": "outcome_scored",
        "source_id": "youtube_4y5GiQpgJgo",
        "future_seconds": [3181.0, 3241.0],
        "prediction_result_hash": "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe",
        "native_downloader_process_invocation_count": 1,
        "provider_http_request_count": "unavailable",
        "downloader_returncode": 0,
        "private_full_caption_access_count": 1,
        "private_full_caption_filename_persisted": False,
        "private_full_caption_hash_persisted": False,
        "raw_full_caption_persisted": False,
        "context_window_cues_persisted": False,
        "private_full_caption_deleted_before_public_scoring": True,
        "private_runtime_deleted_before_public_scoring": True,
        "prediction_mutation_count": 0,
        "model_or_judge_call_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "future_outcome_access_count": 1,
        "outcome_score_count": 2,
        "public_artifact_count": 1,
        "public_manifest_count": 1,
        "fresh_public_reader_count": 1,
        "fresh_public_reader_exit_code": 0,
        "actual_proxy_label": "ask_clarification",
        "evidence_excerpt": "左は誰だ？確認する。",
        "scores": scores,
        "proxy_winner": "SYSTEM_PRAGMATIC_STATE",
    }
    b66._finalize_result(result)
    return result


def test_contract_binds_frozen_prediction_and_proxy_before_future_access():
    assert b66.validate_contract() == {"valid": True, "errors": []}
    contract = b66.load_contract()
    assert contract["source"]["future_start_milliseconds"] == 3181000
    assert contract["source"]["future_end_milliseconds"] == 3241000
    assert contract["observable_label_proxy"]["proxy_is_not_human_ground_truth"] is True
    assert contract["frozen_metrics"]["primary"] == "actual_label_probability_higher_is_better"
    assert contract["execution"]["model_or_judge_call_count_required"] == 0
    assert all(contract["denied_actions"].values())


def test_future_projection_excludes_context_overlap_and_after_end():
    raw = json.dumps(
        {
            "events": [
                event(3179000, 1000, "context"),
                event(3180000, 2000, "overlap"),
                event(3181000, 1000, "first"),
                event(3240000, 1000, "last"),
                event(3240500, 1000, "after"),
            ]
        }
    ).encode("utf-8")
    artifact = b66.extract_future_artifact(raw)
    assert [cue["text"] for cue in artifact["cues"]] == ["first", "last"]
    assert artifact["cues"][0]["start_seconds"] == 3181.0
    assert artifact["cues"][-1]["end_seconds"] == 3241.0


def test_publication_and_fresh_reader_enforce_future_only_artifact(monkeypatch, tmp_path):
    root = tmp_path / "public"
    manifest = b66.publish_future_artifact(future_artifact(), root)
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(root))
    payload = reader.read_artifact(manifest["artifact_id"])
    assert payload["manifest"]["artifact_sha256"] == manifest["artifact_sha256"]
    assert payload["artifact"]["future_seconds"] == [3181.0, 3241.0]
    assert all(cue["start_seconds"] >= 3181.0 for cue in payload["artifact"]["cues"])


def test_target_window_is_first_three_cues_within_twelve_seconds():
    selected = b66.target_cues(future_artifact())
    assert [cue["text"] for cue in selected] == ["左は誰だ？", "確認する。", "次へ行く。"]


def test_proxy_rule_order_is_deterministic_and_default_is_acknowledge():
    assert b66.classify_observable_label("無理。誰だ？")[0] == "direct_rejection"
    assert b66.classify_observable_label("左は誰だ？")[0] == "ask_clarification"
    assert b66.classify_observable_label("ちょっと待って")[0] == "pause_and_reassess"
    assert b66.classify_observable_label("次へ進む")[0] == "acknowledge_then_continue"


def test_frozen_scores_use_actual_label_probability_brier_log_loss_and_text_proxy():
    prediction_result = b66.load_json(
        b66.ROOT / "analysis" / "p3_b65_bounded_joint_prediction_result_2026-09-20.json"
    )
    scores = [
        b66.score_prediction(row, "ask_clarification", "左の足音、誰だ？確認する。")
        for row in prediction_result["predictions"]
    ]
    assert scores[0]["actual_label_probability"] == 0.05
    assert scores[1]["actual_label_probability"] == 0.1
    assert scores[1]["log_loss"] < scores[0]["log_loss"]
    assert b66.choose_proxy_winner(scores) == "SYSTEM_PRAGMATIC_STATE"
    assert scores[1]["character_bigram_jaccard"] > scores[0]["character_bigram_jaccard"]


def test_success_result_validator_accepts_proxy_but_not_prediction_mutation():
    result = result_shell()
    assert b66.validate_result(result) == {"valid": True, "errors": []}
    drifted = deepcopy(result)
    drifted["prediction_mutation_count"] = 1
    drifted = b66._finalize_result(
        {key: value for key, value in drifted.items() if key != "result_hash"}
    )
    report = b66.validate_result(drifted)
    assert "prediction_mutation_count" in report["errors"]


def test_contract_drift_in_prediction_future_metric_or_judge_fails():
    contract = b66.load_contract()
    drifted = deepcopy(contract)
    drifted["bindings"]["b65_saved_prediction"]["sha256"] = "0" * 64
    assert any(error.startswith("binding_hash") for error in b66.validate_contract(drifted)["errors"])
    drifted = deepcopy(contract)
    drifted["source"]["future_end_milliseconds"] = 3300000
    assert "source" in b66.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["frozen_metrics"]["winner_rule"] = "best-looking text"
    assert "metrics" in b66.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["execution"]["model_or_judge_call_count_required"] = 1
    assert "execution" in b66.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_future_access(monkeypatch, tmp_path):
    monkeypatch.setattr(b66, "ROOT", tmp_path)
    contract = b66.load_contract()
    state = tmp_path / contract["execution"]["state_root"]
    state.mkdir(parents=True)
    with pytest.raises(Exception, match="already consumed"):
        b66._fresh_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b66.validate_implementation_freeze() == {
        "valid": True,
        "future_outcome_access_count_at_freeze": 0,
        "outcome_score_count_at_freeze": 0,
    }
