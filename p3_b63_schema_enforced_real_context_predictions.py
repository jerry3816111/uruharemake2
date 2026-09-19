"""B63 JSON-schema-enforced correction of the frozen B62 prediction run."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import time
from typing import Any, Callable
from urllib import error, request

from longitudinal_human_model.baselines import ProviderError
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b62_real_context_prediction_freeze as b62


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b63_schema_enforced_real_context_predictions_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b63_schema_enforced_real_context_predictions_implementation_freeze_2026-09-20.json"


class B63ContractError(ValueError):
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
    if contract.get("schema") != "uruha_p3_b63_schema_enforced_real_context_predictions_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_b62_execution_remediation_before_model_calls_or_future_access":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b62_review") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "prediction_not_frozen_after_first_representation_schema_failure":
            errors.append("review_status")
        if review.get("next_stage", {}).get("id") != "P3-B63":
            errors.append("review_next")
        if review.get("next_stage", {}).get("future_outcome_unlock_authorized") is not False:
            errors.append("future_authorization")
    inherited = contract.get("inherited_experiment") or {}
    expected = {
        "source_id": "youtube_4y5GiQpgJgo",
        "artifact_sha256": "7a690e386e0945785f0dbe8d5573a2eda6f7ed6be64c28e01ee9e4cbbd5d0537",
        "condition_order": ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"],
        "model": "qwen3.5:9b",
        "temperature": 0,
        "seed": 260920,
        "num_ctx": 8192,
        "representation_num_predict": 256,
        "prediction_num_predict": 256,
        "completion_token_ceiling_each_condition": 512,
        "model_call_count_exact": 4,
        "future_outcome_access_before_complete_result_required": 0,
    }
    if inherited != expected:
        errors.append("inherited_experiment")
    enforcement = contract.get("schema_enforcement") or {}
    if enforcement != {
        "provider_format": "json_schema",
        "additional_properties_allowed": False,
        "same_field_names_and_types_as_b62": True,
        "probability_sum_still_validated_after_generation": True,
        "natural_japanese_still_validated_after_generation": True,
    }:
        errors.append("schema_enforcement")
    accounting = contract.get("accounting_repair") or {}
    for field in (
        "record_invocation_before_http_request",
        "record_completion_or_failure_at_provider_boundary",
        "failed_call_counted_as_invocation",
        "unavailable_token_or_latency_must_not_be_zero_filled",
    ):
        if accounting.get(field) is not True:
            errors.append(f"accounting:{field}")
    if accounting.get("raw_prompt_or_response_persistence_allowed") is not False:
        errors.append("accounting:persistence")
    execution = contract.get("execution") or {}
    if execution.get("endpoint") != "http://127.0.0.1:11434/api/generate" or execution.get("timeout_seconds") != 180:
        errors.append("endpoint")
    if execution.get("retry_or_condition_fallback_allowed") is not False:
        errors.append("retry")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b63_model_calls_or_future_access":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B63ContractError(";".join(errors))
    return {
        "valid": True,
        "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"),
        "future_outcome_access_count_at_freeze": freeze.get("future_outcome_access_count_at_freeze"),
    }


def _string_schema() -> dict[str, Any]:
    return {"type": "string", "minLength": 1}


def schema_for_prompt(prompt: str, labels: list[str]) -> dict[str, Any]:
    payload = json.loads(prompt)
    output = payload.get("output_contract") or {}
    if "literal_summary" in output:
        properties = {
            "literal_summary": _string_schema(),
            "current_topic": _string_schema(),
            "explicit_actions": {"type": "array", "items": _string_schema()},
        }
    elif "observed_literal" in output:
        properties = {
            "observed_literal": _string_schema(),
            "primary_hypothesis": _string_schema(),
            "evidence": {"type": "array", "items": _string_schema(), "minItems": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "alternative_hypothesis": _string_schema(),
            "stance_or_emotion": _string_schema(),
            "relationship_signal": _string_schema(),
            "implicit_need": _string_schema(),
            "next_action_tendency": _string_schema(),
        }
    elif "probabilities" in output:
        properties = {
            "probabilities": {
                "type": "object",
                "properties": {label: {"type": "number", "minimum": 0, "maximum": 1} for label in labels},
                "required": labels,
                "additionalProperties": False,
            },
            "predicted_next_content": {"type": "string", "minLength": 1, "maxLength": 160},
            "brief_evidence": {"type": "string"},
        }
    else:
        raise B63ContractError("unknown prompt output contract")
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


class SchemaOllamaProvider:
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
            "format": schema_for_prompt(prompt, self.labels),
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
            raise ProviderError("schema-enforced Ollama request failed") from exc
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
        return {
            "text": body["response"],
            "latency_seconds": elapsed,
            "prompt_tokens": record["prompt_tokens"],
            "completion_tokens": record["completion_tokens"],
            "total_duration_ns": int(body.get("total_duration") or 0),
            "model_reported": record["model_reported"],
        }


def _fresh_state_root(contract: dict[str, Any]) -> Path:
    root = ROOT / contract["execution"]["state_root"]
    if root.exists():
        raise b62.B62ExecutionError("preflight", "preflight", "B63 already consumed")
    root.mkdir(parents=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b63_prediction_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_complete_result",
        "artifact_sha256": contract["inherited_experiment"]["artifact_sha256"],
        "condition_order": contract["inherited_experiment"]["condition_order"],
        "model": contract["inherited_experiment"]["model"],
        "model_call_count_exact": 4,
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
    if result.get("schema") != "uruha_p3_b63_schema_enforced_prediction_result_v1":
        errors.append("schema")
    if result.get("status") not in {"prediction_frozen", "prediction_failed"}:
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
            if record.get("call_index") != index or record.get("status") not in {"invoked", "completed", "failed"}:
                errors.append("call_record")
            if record.get("status") != "completed":
                for field in ("prompt_tokens", "completion_tokens"):
                    if record.get(field) == 0:
                        errors.append("zero_filled_unavailable")
    forbidden = {"artifact_text", "cues", "representation", "raw_prompt", "raw_response", "future", "outcome"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "prediction_frozen":
        if result.get("model_call_count") != 4:
            errors.append("success_calls")
        predictions = result.get("predictions")
        if not isinstance(predictions, list) or [row.get("condition") for row in predictions] != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
            errors.append("predictions")
        else:
            labels = b62.load_contract()["target"]["candidate_behavior_labels"]
            for row in predictions:
                try:
                    b62._parse_prediction(canonical_json(row), labels, 160)
                except Exception:
                    errors.append("prediction_contract")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_schema_predictions(
    provider: SchemaOllamaProvider | None = None,
) -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B63ContractError("invalid B63 contract: " + ";".join(report["errors"]))
    if b62.validate_contract() != {"valid": True, "errors": []}:
        raise B63ContractError("inherited B62 contract invalid")
    contract = load_contract()
    inherited = b62.load_contract()
    state_root = _fresh_state_root(contract)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    active = provider or SchemaOllamaProvider(
        endpoint=contract["execution"]["endpoint"],
        timeout=contract["execution"]["timeout_seconds"],
        labels=inherited["target"]["candidate_behavior_labels"],
    )
    result: dict[str, Any] = {
        "schema": "uruha_p3_b63_schema_enforced_prediction_result_v1",
        "version": "1.0.0",
        "source_id": inherited["input"]["source_id"],
        "artifact_sha256": inherited["input"]["artifact_sha256"],
        "model": inherited["model"]["name"],
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
        artifact = b62.load_public_context(inherited)
        predictions = []
        for condition in inherited["execution"]["condition_order"]:
            prediction, _ = b62.run_condition(condition, artifact, inherited, active)
            predictions.append(prediction)
        artifact = None
        result["predictions"] = predictions
        result["status"] = "prediction_frozen"
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
    if result["status"] == "prediction_frozen":
        result["completion_token_ceiling_by_condition"] = {"BASELINE_LITERAL": 512, "SYSTEM_PRAGMATIC_STATE": 512}
        result["actual_prompt_tokens_by_condition"] = {
            "BASELINE_LITERAL": sum(int(record["prompt_tokens"]) for record in active.records[:2]),
            "SYSTEM_PRAGMATIC_STATE": sum(int(record["prompt_tokens"]) for record in active.records[2:]),
        }
        result["actual_completion_tokens_by_condition"] = {
            "BASELINE_LITERAL": sum(int(record["completion_tokens"]) for record in active.records[:2]),
            "SYSTEM_PRAGMATIC_STATE": sum(int(record["completion_tokens"]) for record in active.records[2:]),
        }
        result["latency_seconds_by_condition"] = {
            "BASELINE_LITERAL": round(sum(float(record["latency_seconds"]) for record in active.records[:2]), 6),
            "SYSTEM_PRAGMATIC_STATE": round(sum(float(record["latency_seconds"]) for record in active.records[2:]), 6),
        }
    result["total_elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B63ContractError("invalid B63 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B63 schema-enforced real-context predictions")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B63 supports only the frozen one-shot schema correction")
    result = execute_schema_predictions()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "prediction_frozen":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
