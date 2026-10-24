from copy import deepcopy
import json
import math

import pytest

import p3_b62_real_context_prediction_freeze as b62
import p3_b65_bounded_joint_prediction_interface as b65
import p3_b70_prediction_interface_reliability as b70


LABELS = b65.load_contract()["target"]["candidate_behavior_labels"]


def joint_output(probabilities=None, predicted="そうなんだ。もう少し話してみて。"):
    probabilities = probabilities or {label: value for label, value in zip(LABELS, [2, 3, 1, 1, 1, 2])}
    return {
        "state": {
            "observed_literal": "話題を続けている。",
            "interpretation": "会話を続けたい可能性がある。",
            "alternative": "単に独り言かもしれない。",
            "confidence": 0.6,
        },
        "probabilities": probabilities,
        "predicted_next_content": predicted,
        "brief_evidence": "直前の発話が継続している。",
    }


def test_contract_is_offline_and_keeps_b69_future_locked():
    assert b70.validate_contract() == {"valid": True, "errors": []}
    contract = b70.load_contract()
    assert contract["gate"]["model_call_count"] == 0
    assert contract["gate"]["network_request_count"] == 0
    assert contract["gate"]["future_access_count"] == 0
    assert contract["gate"]["b69_retry_count"] == 0
    assert all(contract["denied_actions"].values())


@pytest.mark.parametrize("condition", ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"])
def test_same_adapter_normalizes_drift_and_preserves_selected_behavior(condition):
    raw = joint_output()
    original_selected = max(LABELS, key=lambda label: (raw["probabilities"][label], -LABELS.index(label)))
    prediction = b70.parse_joint_output_normalized(json.dumps(raw, ensure_ascii=False), condition)
    assert math.fsum(prediction["probabilities"].values()) == pytest.approx(1.0, abs=1e-12)
    assert prediction["selected_behavior"] == original_selected
    assert prediction["residual_assigned_to"] == original_selected
    assert prediction["selected_behavior_preserved"] is True
    assert prediction["normalization_applied"] is True
    assert prediction["input_weight_sum"] == 10.0
    assert prediction["normalization_contract"] == "p3_b70_v1"


def test_normalization_is_deterministic_and_preserves_strict_order():
    weights = {label: value for label, value in zip(LABELS, [0.31, 0.21, 0.17, 0.13, 0.11, 0.09])}
    first, first_meta = b70.normalize_probability_weights(weights, LABELS)
    second, second_meta = b70.normalize_probability_weights(weights, LABELS)
    assert first == second
    assert first_meta == second_meta
    before_order = sorted(LABELS, key=lambda label: (-weights[label], LABELS.index(label)))
    after_order = sorted(LABELS, key=lambda label: (-first[label], LABELS.index(label)))
    assert after_order == before_order


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda values: values.pop(LABELS[-1]), "probability_labels"),
        (lambda values: values.__setitem__(LABELS[0], -0.1), "probability_value"),
        (lambda values: values.__setitem__(LABELS[0], float("inf")), "probability_value"),
        (lambda values: values.update({label: 0 for label in LABELS}), "probability_total"),
    ],
)
def test_invalid_weight_vectors_remain_rejected(mutation, reason):
    weights = {label: 1 for label in LABELS}
    mutation(weights)
    with pytest.raises(b62.B62ExecutionError) as captured:
        b70.normalize_probability_weights(weights, LABELS)
    assert b70.allowlisted_failure_reason(captured.value) == reason


def test_non_probability_language_gate_remains_unchanged():
    raw = joint_output(predicted="continue talking")
    with pytest.raises(b62.B62ExecutionError) as captured:
        b70.parse_joint_output_normalized(json.dumps(raw), "BASELINE_LITERAL")
    assert b70.allowlisted_failure_reason(captured.value) == "predicted_content_language"


def test_non_probability_state_gate_remains_unchanged():
    raw = joint_output()
    raw["state"].pop("alternative")
    with pytest.raises(b62.B62ExecutionError) as captured:
        b70.parse_joint_output_normalized(json.dumps(raw, ensure_ascii=False), "SYSTEM_PRAGMATIC_STATE")
    assert b70.allowlisted_failure_reason(captured.value) == "state_shape"


def test_failure_reason_is_allowlisted_without_exposing_raw_text():
    examples = {
        "invalid JSON": "json_invalid",
        "joint keys": "joint_shape",
        "state observed_literal": "state_field",
        "confidence": "state_confidence",
        "brief evidence": "brief_evidence",
        "probability sum": "probability_total",
        "unknown internal detail with user text": "other_schema",
    }
    for message, expected in examples.items():
        error = b62.B62ExecutionError("prediction", "schema", message)
        reason = b70.allowlisted_failure_reason(error)
        assert reason == expected
        assert "user text" not in reason


def test_adapter_does_not_mutate_input_document():
    raw = joint_output()
    original = deepcopy(raw)
    b70.parse_joint_output_normalized(json.dumps(raw, ensure_ascii=False), "BASELINE_LITERAL")
    assert raw == original
