"""Source-independent reliability adapter for B65 joint prediction output."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import json
import math
from pathlib import Path
from typing import Any

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b62_real_context_prediction_freeze as b62
import p3_b65_bounded_joint_prediction_interface as b65


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b70_prediction_interface_reliability_gate_v1.json"


class B70ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return b55_v1.canonical_json(value)


def sha256_file(path: str | Path) -> str:
    return b55_v1.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return b55_v1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b70_prediction_interface_reliability_gate_contract_v1":
        errors.append("schema")
    if contract.get("status") != "development_gate_after_b69b_terminal_failure_without_b69_retry_or_future_access":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    release_binding = (contract.get("bindings") or {}).get("b69b_terminal_release") or {}
    if release_binding:
        release = load_json(Path(root) / release_binding["path"])
        if release.get("status") != "released_terminal_incomplete_batch_future_locked":
            errors.append("release_status")
        if release.get("b69c_future_unlock_authorized") is not False:
            errors.append("release_future_boundary")
        if (release.get("next_stage") or {}).get("id") != "P3-B70":
            errors.append("release_next")
    adapter = contract.get("adapter") or {}
    if adapter != {
        "input_kind": "exactly_one_finite_nonnegative_weight_for_each_frozen_behavior_label",
        "positive_total_required": True,
        "decimal_precision": 50,
        "output_decimal_places": 12,
        "residual_assignment": "first_maximum_input_weight_by_frozen_label_order",
        "selected_behavior_must_be_preserved": True,
        "same_adapter_for_both_conditions": True,
        "model_prompt_schema_options_or_token_budget_change": False,
    }:
        errors.append("adapter")
    expected_reasons = {
        "json_invalid", "joint_shape", "state_shape", "state_field", "state_confidence",
        "brief_evidence", "probability_labels", "probability_value", "probability_total",
        "predicted_content", "predicted_content_language", "other_schema",
    }
    if set(contract.get("allowlisted_failure_reasons") or []) != expected_reasons:
        errors.append("failure_reasons")
    gate = contract.get("gate") or {}
    if any(gate.get(field) != 0 for field in ("model_call_count", "network_request_count", "future_access_count", "b69_retry_count")):
        errors.append("resource_gate")
    if gate.get("development_fixtures_only") is not True:
        errors.append("fixture_gate")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def normalize_probability_weights(weights: dict[str, Any], labels: list[str], contract: dict[str, Any] | None = None) -> tuple[dict[str, float], dict[str, Any]]:
    contract = contract or load_contract()
    if not isinstance(weights, dict) or set(weights) != set(labels):
        raise b62.B62ExecutionError("prediction", "schema", "probability labels")
    decimals: dict[str, Decimal] = {}
    for label in labels:
        value = weights[label]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < 0:
            raise b62.B62ExecutionError("prediction", "schema", "probability value")
        decimals[label] = Decimal(str(value))
    total = sum(decimals.values(), Decimal(0))
    if total <= 0:
        raise b62.B62ExecutionError("prediction", "schema", "probability total")
    adapter = contract["adapter"]
    places = int(adapter["output_decimal_places"])
    quantum = Decimal(1).scaleb(-places)
    with localcontext() as context:
        context.prec = int(adapter["decimal_precision"])
        normalized = {
            label: (decimals[label] / total).quantize(quantum, rounding=ROUND_HALF_EVEN)
            for label in labels
        }
    first_maximum = max(labels, key=lambda label: (decimals[label], -labels.index(label)))
    residual = Decimal(1) - sum(normalized.values(), Decimal(0))
    normalized[first_maximum] += residual
    if normalized[first_maximum] < 0:
        raise b62.B62ExecutionError("prediction", "schema", "probability total")
    output = {label: float(normalized[label]) for label in labels}
    selected_after = max(labels, key=lambda label: (output[label], -labels.index(label)))
    if selected_after != first_maximum or abs(math.fsum(output.values()) - 1.0) > 0.000001:
        raise B70ContractError("normalization invariant")
    metadata = {
        "input_weight_sum": float(total),
        "normalization_applied": abs(float(total) - 1.0) > 0.000001,
        "normalization_decimal_places": places,
        "residual_assigned_to": first_maximum,
        "selected_behavior_preserved": True,
    }
    return output, metadata


def parse_joint_output_normalized(text: str, condition: str, b65_contract: dict[str, Any] | None = None) -> dict[str, Any]:
    b65_contract = b65_contract or b65.load_contract()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise b62.B62ExecutionError("joint_output", "schema", "invalid JSON") from exc
    if not isinstance(value, dict):
        raise b62.B62ExecutionError("joint_output", "schema", "joint keys")
    labels = b65_contract["target"]["candidate_behavior_labels"]
    normalized, metadata = normalize_probability_weights(value.get("probabilities"), labels)
    adapted = deepcopy(value)
    adapted["probabilities"] = normalized
    prediction = b65.parse_joint_output(canonical_json(adapted), condition, b65_contract)
    prediction.update(metadata)
    prediction["normalization_contract"] = "p3_b70_v1"
    return prediction


def allowlisted_failure_reason(exc: BaseException) -> str:
    message = str(exc)
    mapping = {
        "invalid JSON": "json_invalid",
        "joint keys": "joint_shape",
        "state keys": "state_shape",
        "state observed_literal": "state_field",
        "state interpretation": "state_field",
        "state alternative": "state_field",
        "confidence": "state_confidence",
        "brief evidence": "brief_evidence",
        "probability labels": "probability_labels",
        "probability value": "probability_value",
        "probability sum": "probability_total",
        "probability total": "probability_total",
        "predicted content not Japanese": "predicted_content_language",
        "predicted content": "predicted_content",
    }
    reason = mapping.get(message, "other_schema")
    if reason not in load_contract()["allowlisted_failure_reasons"]:
        raise B70ContractError("failure reason escaped allowlist")
    return reason
