"""B65 prospective bounded joint state-and-prediction interface."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib import error, request

from longitudinal_human_model.baselines import ProviderError
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b62_real_context_prediction_freeze as b62


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b65_bounded_joint_prediction_interface_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b65_bounded_joint_prediction_interface_implementation_freeze_2026-09-20.json"


class B65ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return b55_v1.canonical_json(value)


def sha256_bytes(payload: bytes) -> str:
    return b55_v1.sha256_bytes(payload)


def sha256_file(path: str | Path) -> str:
    return b55_v1.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return b55_v1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b65_bounded_joint_prediction_interface_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_new_interface_before_model_calls_or_future_access":
        errors.append("status")
    if contract.get("claim_level") != "single_real_row_interface_feasibility_not_prediction_accuracy_or_formal_m56":
        errors.append("claim_level")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b64_terminal_review") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "terminal_prediction_execution_failure_future_locked":
            errors.append("review_status")
        next_stage = review.get("next_stage") or {}
        if next_stage.get("id") != "P3-B65" or next_stage.get("not_a_b62_correction_or_retry") is not True:
            errors.append("review_next")
        if next_stage.get("future_outcome_unlock_authorized") is not False:
            errors.append("future_authorization")
    source = contract.get("input") or {}
    if source != {
        "source_id": "youtube_4y5GiQpgJgo",
        "context_seconds": [3000.0, 3180.0],
        "future_outcome_seconds": [3181.0, 3241.0],
        "public_root": "external_data/p3_b61_public_caption_context",
        "artifact_id": "p3-b60-7a690e386e094578",
        "artifact_sha256": "7a690e386e0945785f0dbe8d5573a2eda6f7ed6be64c28e01ee9e4cbbd5d0537",
        "cue_count": 65,
        "future_outcome_access_before_complete_prediction_pair_required": 0,
        "private_acquisition_module_import_allowed": False,
    }:
        errors.append("input_boundary")
    labels = (contract.get("target") or {}).get("candidate_behavior_labels")
    if labels != b62.load_contract()["target"]["candidate_behavior_labels"]:
        errors.append("labels")
    if list((contract.get("conditions") or {}).keys()) != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
        errors.append("conditions")
    fairness = contract.get("fairness") or {}
    for field in (
        "same_base_model",
        "same_context_artifact",
        "same_target_labels_and_output_schema",
        "same_single_call_graph",
        "same_options_and_completion_ceiling",
        "actual_prompt_completion_tokens_and_latency_recorded",
        "unequal_actual_token_use_must_be_reported",
    ):
        if fairness.get(field) is not True:
            errors.append(f"fairness:{field}")
    if fairness.get("completion_token_ceiling_each_condition") != 512:
        errors.append("token_ceiling")
    if fairness.get("model_call_count_exact") != 2:
        errors.append("call_count")
    if fairness.get("condition_order") != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
        errors.append("condition_order")
    model = contract.get("model") or {}
    if model != {
        "provider": "local_ollama",
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "name": "qwen3.5:9b",
        "timeout_seconds": 180,
        "think": False,
        "options": {"temperature": 0, "seed": 260920, "num_ctx": 8192, "num_predict": 512},
    }:
        errors.append("model")
    output = contract.get("joint_output_contract") or {}
    if output != {
        "same_json_schema_both_conditions": True,
        "state_fields": ["observed_literal", "interpretation", "alternative", "confidence"],
        "observed_literal_max_characters": 120,
        "interpretation_max_characters": 120,
        "alternative_max_characters": 120,
        "predicted_next_content_language": "ja",
        "predicted_next_content_max_characters": 160,
        "brief_evidence_max_characters": 120,
        "probabilities_exactly_all_labels": True,
        "probabilities_sum_tolerance": 0.000001,
        "state_text_persistence_allowed": False,
        "raw_prompt_or_model_response_persistence_allowed": False,
    }:
        errors.append("output_contract")
    execution = contract.get("execution") or {}
    if execution.get("retry_or_condition_fallback_allowed") is not False:
        errors.append("retry")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b65_model_calls_or_future_access":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B65ContractError(";".join(errors))
    return {
        "valid": True,
        "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"),
        "future_outcome_access_count_at_freeze": freeze.get("future_outcome_access_count_at_freeze"),
    }


def joint_schema(labels: list[str]) -> dict[str, Any]:
    short_string = lambda maximum: {"type": "string", "minLength": 1, "maxLength": maximum}
    state = {
        "type": "object",
        "properties": {
            "observed_literal": short_string(120),
            "interpretation": short_string(120),
            "alternative": short_string(120),
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["observed_literal", "interpretation", "alternative", "confidence"],
        "additionalProperties": False,
    }
    probabilities = {
        "type": "object",
        "properties": {label: {"type": "number", "minimum": 0, "maximum": 1} for label in labels},
        "required": labels,
        "additionalProperties": False,
    }
    properties = {
        "state": state,
        "probabilities": probabilities,
        "predicted_next_content": short_string(160),
        "brief_evidence": short_string(120),
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def joint_prompt(
    condition: str, artifact: dict[str, Any], contract: dict[str, Any]
) -> str:
    if condition not in contract["conditions"]:
        raise B65ContractError("unknown condition")
    labels = contract["target"]["candidate_behavior_labels"]
    condition_contract = contract["conditions"][condition]
    return canonical_json(
        {
            "task": contract["target"]["task"],
            "target": contract["target"]["reference_person"],
            "persona_boundary": contract["target"]["persona_boundary"],
            "observable_context": b62._context_text(artifact),
            "condition": condition,
            "state_rule": condition_contract["state_rule"],
            "alternative_rule": condition_contract["alternative_rule"],
            "candidate_behavior_labels": labels,
            "output_contract": {
                "state": {
                    "observed_literal": "Japanese, <=120 characters",
                    "interpretation": "Japanese, <=120 characters",
                    "alternative": "Japanese, <=120 characters",
                    "confidence": "number from 0 to 1",
                },
                "probabilities": {label: "number from 0 to 1" for label in labels},
                "predicted_next_content": "natural Japanese, <=160 characters",
                "brief_evidence": "Japanese, <=120 characters",
            },
            "constraints": [
                "Return only the JSON object matching the provider schema.",
                "Use only the observable context; do not invent private or unseen facts.",
                "Use every behavior label exactly once and make probabilities sum to 1.",
                "Keep the state concise, falsifiable, and within every character bound.",
            ],
        }
    )


class JointSchemaOllamaProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        timeout: int,
        labels: list[str],
        opener: Callable[..., Any] = request.urlopen,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.labels = labels
        self.opener = opener
        self.records: list[dict[str, Any]] = []

    def __call__(self, *, model: str, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        record: dict[str, Any] = {
            "call_index": len(self.records) + 1,
            "status": "invoked",
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "model_requested": model,
            "num_predict": int(options["num_predict"]),
            "prompt_tokens": "unavailable",
            "completion_tokens": "unavailable",
            "latency_seconds": "unavailable",
        }
        self.records.append(record)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": joint_schema(self.labels),
            "think": False,
            "options": options,
        }
        started = time.perf_counter()
        http_request = request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            record["status"] = "failed"
            record["latency_seconds"] = round(time.perf_counter() - started, 6)
            record["failure_class"] = type(exc).__name__
            raise ProviderError("joint-schema Ollama request failed") from exc
        elapsed = time.perf_counter() - started
        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            record["status"] = "failed"
            record["latency_seconds"] = round(elapsed, 6)
            record["failure_class"] = "ProviderResponseContract"
            raise ProviderError("Ollama response missing text")
        record.update(
            {
                "status": "completed",
                "response_sha256": sha256_bytes(body["response"].encode("utf-8")),
                "prompt_tokens": int(body.get("prompt_eval_count") or 0),
                "completion_tokens": int(body.get("eval_count") or 0),
                "latency_seconds": round(elapsed, 6),
                "model_reported": body.get("model") or model,
            }
        )
        return {"text": body["response"]}


def parse_joint_output(
    text: str, condition: str, contract: dict[str, Any]
) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise b62.B62ExecutionError("joint_output", "schema", "invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"state", "probabilities", "predicted_next_content", "brief_evidence"}:
        raise b62.B62ExecutionError("joint_output", "schema", "joint keys")
    state = value.get("state")
    required = {"observed_literal", "interpretation", "alternative", "confidence"}
    if not isinstance(state, dict) or set(state) != required:
        raise b62.B62ExecutionError("joint_output", "schema", "state keys")
    output = contract["joint_output_contract"]
    for field, bound_name in (
        ("observed_literal", "observed_literal_max_characters"),
        ("interpretation", "interpretation_max_characters"),
        ("alternative", "alternative_max_characters"),
    ):
        item = state[field]
        if not isinstance(item, str) or not item.strip() or len(item) > output[bound_name]:
            raise b62.B62ExecutionError("joint_output", "schema", f"state {field}")
    confidence = state["confidence"]
    if not isinstance(confidence, (int, float)) or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        raise b62.B62ExecutionError("joint_output", "schema", "confidence")
    if not isinstance(value["brief_evidence"], str) or not value["brief_evidence"].strip() or len(value["brief_evidence"]) > output["brief_evidence_max_characters"]:
        raise b62.B62ExecutionError("joint_output", "schema", "brief evidence")
    prediction = b62._parse_prediction(
        canonical_json(value),
        contract["target"]["candidate_behavior_labels"],
        output["predicted_next_content_max_characters"],
    )
    prediction.update(
        {
            "condition": condition,
            "state_sha256": sha256_bytes(canonical_json(state).encode("utf-8")),
            "state_persisted": False,
            "raw_prompt_or_response_persisted": False,
        }
    )
    return prediction


def _fresh_state_root(contract: dict[str, Any]) -> Path:
    root = ROOT / contract["execution"]["state_root"]
    if root.exists():
        raise b62.B62ExecutionError("preflight", "preflight", "B65 already consumed")
    root.mkdir(parents=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b65_prediction_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_complete_result",
        "artifact_sha256": contract["input"]["artifact_sha256"],
        "condition_order": contract["fairness"]["condition_order"],
        "model": contract["model"]["name"],
        "model_call_count_exact": 2,
        "completion_token_ceiling_each_condition": 512,
        "future_outcome_access_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b65_bounded_joint_prediction_result_v1":
        errors.append("schema")
    if result.get("status") not in {"prediction_pair_frozen", "prediction_failed"}:
        errors.append("status")
    if result.get("future_outcome_access_count") != 0 or result.get("outcome_score_count") != 0:
        errors.append("future_boundary")
    if result.get("retry_count") != 0 or result.get("fallback_count") != 0:
        errors.append("retry")
    records = result.get("call_records")
    if not isinstance(records, list) or result.get("model_call_count") != len(records):
        errors.append("accounting")
    if isinstance(records, list):
        for index, record in enumerate(records, start=1):
            if record.get("call_index") != index or record.get("num_predict") != 512:
                errors.append("call_record")
            if record.get("status") not in {"invoked", "completed", "failed"}:
                errors.append("call_status")
    forbidden = {"artifact_text", "cues", "state", "raw_prompt", "raw_response", "future", "outcome"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "prediction_pair_frozen":
        predictions = result.get("predictions")
        if result.get("model_call_count") != 2:
            errors.append("success_calls")
        if not isinstance(predictions, list) or [row.get("condition") for row in predictions] != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
            errors.append("predictions")
        else:
            labels = load_contract()["target"]["candidate_behavior_labels"]
            for row in predictions:
                if row.get("state_persisted") is not False or row.get("raw_prompt_or_response_persisted") is not False:
                    errors.append("persistence")
                try:
                    b62._parse_prediction(canonical_json(row), labels, 160)
                except Exception:
                    errors.append("prediction_contract")
        if result.get("completion_token_ceiling_by_condition") != {"BASELINE_LITERAL": 512, "SYSTEM_PRAGMATIC_STATE": 512}:
            errors.append("budget")
    elif not result.get("failure_stage") or not result.get("failure_category"):
        errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_joint_predictions(
    provider: JointSchemaOllamaProvider | None = None,
) -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B65ContractError("invalid B65 contract: " + ";".join(report["errors"]))
    contract = load_contract()
    state_root = _fresh_state_root(contract)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    active = provider or JointSchemaOllamaProvider(
        endpoint=contract["model"]["endpoint"],
        timeout=contract["model"]["timeout_seconds"],
        labels=contract["target"]["candidate_behavior_labels"],
    )
    result: dict[str, Any] = {
        "schema": "uruha_p3_b65_bounded_joint_prediction_result_v1",
        "version": "1.0.0",
        "source_id": contract["input"]["source_id"],
        "artifact_sha256": contract["input"]["artifact_sha256"],
        "model": contract["model"]["name"],
        "interface": "bounded_joint_state_and_prediction",
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }
    started = time.perf_counter()
    try:
        artifact = b62.load_public_context(b62.load_contract())
        predictions = []
        for condition in contract["fairness"]["condition_order"]:
            prompt = joint_prompt(condition, artifact, contract)
            response = active(
                model=contract["model"]["name"],
                prompt=prompt,
                options=contract["model"]["options"],
            )
            predictions.append(parse_joint_output(response["text"], condition, contract))
        artifact = None
        result["predictions"] = predictions
        result["status"] = "prediction_pair_frozen"
    except Exception as exc:
        result["status"] = "prediction_failed"
        if isinstance(exc, b62.B62ExecutionError):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
        elif isinstance(exc, ProviderError):
            result["failure_stage"] = "model"
            result["failure_category"] = "provider_or_schema"
        else:
            result["failure_stage"] = "unexpected"
            result["failure_category"] = "unknown"
        result["failure_class"] = type(exc).__name__
    result["call_records"] = active.records
    result["model_call_count"] = len(active.records)
    if result["status"] == "prediction_pair_frozen":
        result["completion_token_ceiling_by_condition"] = {"BASELINE_LITERAL": 512, "SYSTEM_PRAGMATIC_STATE": 512}
        result["actual_prompt_tokens_by_condition"] = {
            condition: int(active.records[index]["prompt_tokens"])
            for index, condition in enumerate(contract["fairness"]["condition_order"])
        }
        result["actual_completion_tokens_by_condition"] = {
            condition: int(active.records[index]["completion_tokens"])
            for index, condition in enumerate(contract["fairness"]["condition_order"])
        }
        result["latency_seconds_by_condition"] = {
            condition: float(active.records[index]["latency_seconds"])
            for index, condition in enumerate(contract["fairness"]["condition_order"])
        }
    result["total_elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B65ContractError("invalid B65 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B65 bounded joint prediction interface")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B65 supports only the frozen one-shot execution")
    result = execute_joint_predictions()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "prediction_pair_frozen":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
