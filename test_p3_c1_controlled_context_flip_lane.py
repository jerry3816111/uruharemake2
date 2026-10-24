from copy import deepcopy
import json

import pytest

import p3_c1_controlled_context_flip_lane as c1


def _target_map(dataset, split):
    result = {}
    for pair in dataset["pairs"]:
        if pair["split"] != split:
            continue
        for variant in pair["variants"]:
            result[(pair["pair_id"], variant["variant_id"])] = variant[
                "expected_distribution"
            ]
    return result


def _prediction(item, condition, probabilities):
    selected = max(
        c1.TARGET_LABELS,
        key=lambda label: (
            probabilities[label],
            -c1.TARGET_LABELS.index(label),
        ),
    )
    value = {
        "schema": "uruha_p3_c1_interpretation_prediction_v1",
        "condition": condition,
        "pair_id": item["pair_id"],
        "variant_id": item["variant_id"],
        "input_sha256": item["input_sha256"],
        "probabilities": probabilities,
        "selected_interpretation": selected,
        "visible_reply_ja": "そういうことなら、無理に決めつけずに聞くよ。",
        "brief_evidence_anchor_ids": [item["evidence_anchors"][0]["id"]],
    }
    if condition == "SYSTEM_PRAGMATIC_STATE":
        value["pragmatic_state"] = {
            "literal_content": "表面の発話内容を保持する。",
            "communicative_intent": "文脈に合う意図を仮説として置く。",
            "affect_or_stance": "文字だけで確認できる姿勢に限定する。",
            "relationship_signal": "関係上の合図は断定しない。",
            "implicit_need_or_action_tendency": "必要なら低圧に確認する。",
            "alternative_hypothesis": "文字どおりの可能性も残す。",
            "unknowns": "音声特徴は利用できない。",
            "confidence": 0.7,
        }
    return value


def _prediction_batch(split, *, baseline_mode="flat", system_mode="target"):
    dataset = c1.load_dataset()
    packet = c1.build_prediction_packet(split, dataset)
    targets = _target_map(dataset, split)
    output = []
    for item in packet["items"]:
        target = targets[(item["pair_id"], item["variant_id"])]
        for condition, mode in (
            ("BASELINE_DIRECT", baseline_mode),
            ("SYSTEM_PRAGMATIC_STATE", system_mode),
        ):
            if mode == "target":
                probabilities = deepcopy(target)
            elif mode == "flat":
                probabilities = {
                    "LITERAL_READING": 0.34,
                    "PRAGMATIC_READING": 0.33,
                    "UNCERTAIN": 0.33,
                }
            elif mode == "always_pragmatic":
                probabilities = {
                    "LITERAL_READING": 0.05,
                    "PRAGMATIC_READING": 0.9,
                    "UNCERTAIN": 0.05,
                }
            else:
                raise AssertionError(mode)
            output.append(_prediction(item, condition, probabilities))
    return output


def test_contract_freezes_fair_strong_baseline_and_zero_execution():
    assert c1.validate_contract() == {"valid": True, "errors": []}
    contract = c1.load_contract()
    assert contract["fairness"]["baseline_may_reason_normally"] is True
    assert contract["fairness"]["baseline_literal_restriction"] is False
    assert contract["fairness"]["same_complete_observable_input"] is True
    assert contract["fairness"]["total_completion_token_ceiling_each_condition_item"] == 384
    assert all(value == 0 for value in contract["execution_limits"].values())


def test_dataset_has_balanced_splits_languages_and_exact_context_pairs():
    report = c1.validate_dataset()
    assert report["valid"] is True, report["errors"]
    assert report["counts"] == {
        "pairs": 18,
        "variants": 36,
        "by_split": {"dev": 6, "holdout": 6, "train": 6},
        "by_language": {"en": 6, "ja": 6, "zh": 6},
    }
    for pair in c1.load_dataset()["pairs"]:
        assert [row["variant_id"] for row in pair["variants"]] == c1.VARIANTS
        assert all(pair["surface_utterance"] in row["context_text"] for row in pair["variants"])
        assert pair["variants"][0]["expected_top1"] == "LITERAL_READING"
        assert pair["variants"][1]["expected_top1"] == "PRAGMATIC_READING"


def test_prediction_packet_strips_all_targets_and_private_truth_claims():
    packet = c1.build_prediction_packet("holdout")
    serialized = json.dumps(packet, ensure_ascii=False)
    assert packet["item_count"] == 12
    assert packet["targets_visible"] is False
    assert "expected_distribution" not in serialized
    assert "expected_top1" not in serialized
    assert "private_motive" not in serialized
    assert all(
        item["modality"]
        == {
            "text_available": True,
            "acoustic_summary_status": "unavailable",
            "acoustic_features": None,
        }
        for item in packet["items"]
    )


def test_both_conditions_receive_byte_identical_common_observable_input():
    item = c1.build_prediction_packet("dev")["items"][0]
    baseline = c1.build_prompt_payload("BASELINE_DIRECT", item)
    system = c1.build_prompt_payload("SYSTEM_PRAGMATIC_STATE", item)
    assert baseline["common_observable_input"] == system["common_observable_input"]
    assert baseline["common_input_sha256"] == system["common_input_sha256"]
    assert "additional_observable_state_fields" not in baseline
    assert len(system["additional_observable_state_fields"]) == 8


def test_input_mutation_or_target_leak_fails_before_prompt_build():
    item = c1.build_prediction_packet("dev")["items"][0]
    item["context_text"] += " leaked mutation"
    with pytest.raises(c1.C1ContractError, match="input hash mismatch"):
        c1.build_prompt_payload("BASELINE_DIRECT", item)


def test_prediction_validation_requires_japanese_grounded_output_and_system_state():
    item = c1.build_prediction_packet("dev")["items"][0]
    valid = _prediction(
        item,
        "SYSTEM_PRAGMATIC_STATE",
        {"LITERAL_READING": 0.8, "PRAGMATIC_READING": 0.1, "UNCERTAIN": 0.1},
    )
    assert c1.validate_prediction(valid, item, "SYSTEM_PRAGMATIC_STATE") == []
    broken = deepcopy(valid)
    broken["visible_reply_ja"] = "I understand you."
    broken["brief_evidence_anchor_ids"] = ["invented_anchor"]
    broken["pragmatic_state"].pop("unknowns")
    errors = c1.validate_prediction(broken, item, "SYSTEM_PRAGMATIC_STATE")
    assert "visible_reply_ja" in errors
    assert "brief_evidence_anchor_ids" in errors
    assert "pragmatic_state" in errors


def test_offline_metric_fixture_detects_target_alignment_without_human_claim():
    report = c1.score_predictions(_prediction_batch("holdout"), "holdout")
    assert report["conditions"]["SYSTEM_PRAGMATIC_STATE"]["mean_multiclass_brier"] == 0.0
    assert report["conditions"]["SYSTEM_PRAGMATIC_STATE"]["paired_context_flip_top1_accuracy"] == 1.0
    assert report["conditions"]["SYSTEM_PRAGMATIC_STATE"]["literal_control_overinterpretation_rate"] == 0.0
    assert report["comparison"]["system_minus_baseline_brier_improvement"] >= 0.03
    assert report["comparison"]["controlled_lane_success"] is True
    assert report["target_kind"] == "developer_authored_distribution_proxy_not_human_ground_truth"


def test_overinterpretation_control_can_fail_even_when_pragmatic_side_is_selected():
    predictions = _prediction_batch(
        "holdout", baseline_mode="target", system_mode="always_pragmatic"
    )
    report = c1.score_predictions(predictions, "holdout")
    system = report["conditions"]["SYSTEM_PRAGMATIC_STATE"]
    assert system["literal_control_overinterpretation_rate"] == 1.0
    assert system["pragmatic_underreading_rate"] == 0.0
    assert report["comparison"]["literal_overinterpretation_not_worse"] is False
    assert report["comparison"]["controlled_lane_success"] is False


def test_incomplete_duplicate_or_invalid_prediction_batch_fails_closed():
    predictions = _prediction_batch("dev")
    with pytest.raises(c1.C1ContractError, match="missing"):
        c1.score_predictions(predictions[:-1], "dev")
    duplicated = predictions + [deepcopy(predictions[0])]
    with pytest.raises(c1.C1ContractError, match="duplicate"):
        c1.score_predictions(duplicated, "dev")
    invalid = deepcopy(predictions)
    invalid[0]["probabilities"]["UNCERTAIN"] = 0.8
    with pytest.raises(c1.C1ContractError, match="probabilities:sum"):
        c1.score_predictions(invalid, "dev")


def test_readiness_is_offline_only_and_does_not_authorize_execution():
    readiness = c1.build_readiness_result()
    assert readiness["status"] == "offline_contract_dataset_and_metric_harness_ready_model_execution_not_started"
    assert readiness["pair_count"] == 18
    assert readiness["variant_count"] == 36
    assert readiness["prediction_item_counts"] == {"train": 12, "dev": 12, "holdout": 12}
    assert readiness["target_visibility_in_prediction_packets"] is False
    assert readiness["human_validated_targets"] is False
    assert readiness["independent_holdout"] is False
    assert readiness["model_execution_authorized_by_c1"] is False
    assert all(value == 0 for value in readiness["execution_counts"].values())


def test_implementation_freeze_hashes_every_c1_input_before_model_execution():
    validation = c1.validate_implementation_freeze()
    assert validation == {
        "valid": True,
        "frozen_artifact_count": 5,
        "model_calls_at_freeze": 0,
    }
