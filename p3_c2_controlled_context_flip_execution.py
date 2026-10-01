"""Crash-safe, no-retry P3-C2 train-smoke and development execution runner."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import time
from typing import Any, Callable
from urllib import error, request

import p3_b70_prediction_interface_reliability as b70
import p3_c1_controlled_context_flip_lane as c1


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_c2_controlled_context_flip_execution_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_c2_controlled_context_flip_execution_implementation_freeze_2026-09-20.json"


class C2ContractError(ValueError):
    pass


class C2ProviderError(RuntimeError):
    def __init__(self, category: str, record: dict[str, Any]):
        super().__init__(category)
        self.category = category
        self.record = record


def canonical_json(value: Any) -> str:
    return c1.canonical_json(value)


def sha256_bytes(payload: bytes) -> str:
    return c1.sha256_bytes(payload)


def sha256_file(path: str | Path) -> str:
    return c1.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return c1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_c2_controlled_context_flip_execution_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_runner_contract_before_any_p3_c_model_call":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    plan = contract.get("execution_plan") or {}
    if plan.get("stage_order") != ["train_format_smoke", "dev_complete"]:
        errors.append("plan:stages")
    if plan.get("train_format_smoke_pair_ids") != ["train_zh_01", "train_en_02"]:
        errors.append("plan:smoke_pairs")
    expected_counts = {
        "train_format_smoke_item_count": 4,
        "train_format_smoke_model_call_count": 8,
        "dev_pair_count": 6,
        "dev_item_count": 12,
        "dev_model_call_count": 24,
        "total_model_call_ceiling": 32,
    }
    for field, value in expected_counts.items():
        if plan.get(field) != value:
            errors.append(f"plan:{field}")
    for field in (
        "smoke_must_complete_before_any_dev_call",
        "dev_must_complete_before_scoring",
        "terminal_on_provider_schema_language_or_accounting_failure",
    ):
        if plan.get(field) is not True:
            errors.append(f"plan:{field}")
    if plan.get("holdout_item_or_target_access_allowed") is not False:
        errors.append("plan:holdout")
    if plan.get("retry_or_fallback_allowed") is not False:
        errors.append("plan:retry")
    provider = contract.get("provider") or {}
    expected_provider = {
        "kind": "local_ollama_exact_json_schema",
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "model": "qwen3.5:9b",
        "timeout_seconds": 180,
        "think": False,
        "options": {
            "temperature": 0,
            "seed": 260920,
            "top_p": 1,
            "num_ctx": 8192,
            "num_predict": 384,
        },
        "probability_adapter": "p3_b70_v1",
        "raw_prompt_or_response_persistence_allowed": False,
    }
    if provider != expected_provider:
        errors.append("provider")
    output = contract.get("output_contract") or {}
    if output.get("common_model_fields") != [
        "probabilities",
        "visible_reply_ja",
        "brief_evidence_anchor_ids",
    ]:
        errors.append("output:common")
    if output.get("system_additional_field") != "pragmatic_state":
        errors.append("output:system")
    if output.get("probability_labels") != c1.TARGET_LABELS:
        errors.append("output:labels")
    if output.get("system_state_fields") != load_json(
        Path(root) / "configs/p3_c1_controlled_context_flip_lane_v1.json"
    )["conditions"]["SYSTEM_PRAGMATIC_STATE"]["additional_observable_state_fields"]:
        errors.append("output:state_fields")
    crash = contract.get("crash_safety") or {}
    required_crash_true = {
        "batch_intent_before_first_call",
        "per_call_intent_before_provider_invocation",
        "per_call_complete_after_validated_prediction",
        "intent_without_complete_is_terminal_and_never_reinvoked",
        "completed_call_can_be_reused_on_process_resume",
        "single_final_result",
    }
    if any(crash.get(field) is not True for field in required_crash_true):
        errors.append("crash_safety")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    path = Path(root) / FREEZE_PATH.relative_to(ROOT)
    if not path.is_file():
        raise C2ContractError("implementation freeze missing")
    freeze = load_json(path)
    errors: list[str] = []
    if freeze.get("schema") != "uruha_p3_c2_controlled_context_flip_execution_implementation_freeze_v1":
        errors.append("schema")
    if freeze.get("status") != "frozen_before_any_p3_c_model_call":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        artifact_path = Path(root) / str((artifact or {}).get("path") or "")
        if not artifact_path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(artifact_path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if freeze.get("p3_c_model_call_count_at_freeze") != 0:
        errors.append("model_calls")
    if freeze.get("holdout_access_count_at_freeze") != 0:
        errors.append("holdout")
    if errors:
        raise C2ContractError("invalid implementation freeze:" + ";".join(errors))
    return {"valid": True, "p3_c_model_calls_at_freeze": 0}


def output_schema(condition: str, anchor_ids: list[str]) -> dict[str, Any]:
    if condition not in c1.CONDITIONS:
        raise C2ContractError("unknown condition")
    probabilities = {
        "type": "object",
        "properties": {
            label: {"type": "number", "minimum": 0}
            for label in c1.TARGET_LABELS
        },
        "required": c1.TARGET_LABELS,
        "additionalProperties": False,
    }
    properties: dict[str, Any] = {
        "probabilities": probabilities,
        "visible_reply_ja": {"type": "string", "minLength": 1, "maxLength": 180},
        "brief_evidence_anchor_ids": {
            "type": "array",
            "items": {"type": "string", "enum": anchor_ids},
            "minItems": 1,
            "maxItems": len(anchor_ids),
            "uniqueItems": True,
        },
    }
    if condition == "SYSTEM_PRAGMATIC_STATE":
        state_fields = load_contract()["output_contract"]["system_state_fields"]
        state_properties = {
            field: (
                {"type": "number", "minimum": 0, "maximum": 1}
                if field == "confidence"
                else {"type": "string", "minLength": 1, "maxLength": 180}
            )
            for field in state_fields
        }
        properties["pragmatic_state"] = {
            "type": "object",
            "properties": state_properties,
            "required": state_fields,
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def prompt_for(condition: str, item: dict[str, Any]) -> str:
    payload = c1.build_prompt_payload(condition, item)
    payload["persona_expression_boundary"] = (
        "Reply in restrained casual natural Japanese consistent with the public Uruha persona case; "
        "do not claim to be the real person and do not invent private history or mental facts."
    )
    payload["output_contract"] = {
        "probabilities": {
            label: "finite nonnegative weight; all three labels required"
            for label in c1.TARGET_LABELS
        },
        "visible_reply_ja": "one natural Japanese user-visible reply, <=180 characters; never expose analysis",
        "brief_evidence_anchor_ids": "one or more IDs from the current evidence_anchors",
    }
    if condition == "SYSTEM_PRAGMATIC_STATE":
        payload["output_contract"]["pragmatic_state"] = {
            field: (
                "number from 0 to 1"
                if field == "confidence"
                else "concise falsifiable state, <=180 characters"
            )
            for field in load_contract()["output_contract"]["system_state_fields"]
        }
    payload["constraints"] = [
        "Return only the exact JSON object required by the provider schema.",
        "The probabilities may be weights; they will be normalized by the same frozen adapter for both conditions.",
        "Do not mention the analysis, labels, confidence, or alternatives in visible_reply_ja.",
        "Never use unavailable acoustic evidence.",
    ]
    return canonical_json(payload)


def build_execution_plan(contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    stages: list[tuple[str, dict[str, Any]]] = [
        ("train_format_smoke", c1.build_prediction_packet("train")),
        ("dev_complete", c1.build_prediction_packet("dev")),
    ]
    smoke_pairs = set(contract["execution_plan"]["train_format_smoke_pair_ids"])
    calls: list[dict[str, Any]] = []
    for stage, packet in stages:
        items = packet["items"]
        if stage == "train_format_smoke":
            items = [item for item in items if item["pair_id"] in smoke_pairs]
        for item_index, item in enumerate(items):
            condition_order = (
                c1.CONDITIONS
                if item_index % 2 == 0
                else list(reversed(c1.CONDITIONS))
            )
            for condition in condition_order:
                calls.append(
                    {
                        "call_index": len(calls) + 1,
                        "stage": stage,
                        "pair_id": item["pair_id"],
                        "variant_id": item["variant_id"],
                        "condition": condition,
                        "input_sha256": item["input_sha256"],
                    }
                )
    expected = contract["execution_plan"]["total_model_call_ceiling"]
    if len(calls) != expected:
        raise C2ContractError(f"execution plan count:{len(calls)}")
    return calls


def _items_for_execution() -> dict[tuple[str, str], dict[str, Any]]:
    packets = [c1.build_prediction_packet("train"), c1.build_prediction_packet("dev")]
    return {
        (item["pair_id"], item["variant_id"]): item
        for packet in packets
        for item in packet["items"]
    }


def parse_output(
    text: str, condition: str, item: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise C2ContractError("json_invalid") from exc
    common = {"probabilities", "visible_reply_ja", "brief_evidence_anchor_ids"}
    expected_keys = common | ({"pragmatic_state"} if condition == "SYSTEM_PRAGMATIC_STATE" else set())
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise C2ContractError("output_shape")
    try:
        probabilities, normalization = b70.normalize_probability_weights(
            value["probabilities"], c1.TARGET_LABELS
        )
    except Exception as exc:
        raise C2ContractError("probabilities") from exc
    selected = max(
        c1.TARGET_LABELS,
        key=lambda label: (probabilities[label], -c1.TARGET_LABELS.index(label)),
    )
    prediction = {
        "schema": "uruha_p3_c1_interpretation_prediction_v1",
        "condition": condition,
        "pair_id": item["pair_id"],
        "variant_id": item["variant_id"],
        "input_sha256": item["input_sha256"],
        "probabilities": probabilities,
        "selected_interpretation": selected,
        "visible_reply_ja": value.get("visible_reply_ja"),
        "brief_evidence_anchor_ids": value.get("brief_evidence_anchor_ids"),
    }
    if condition == "SYSTEM_PRAGMATIC_STATE":
        prediction["pragmatic_state"] = value.get("pragmatic_state")
    errors = c1.validate_prediction(prediction, item, condition)
    if errors:
        category = "language" if errors == ["visible_reply_ja"] else "prediction_contract"
        raise C2ContractError(category + ":" + ",".join(errors))
    return prediction, normalization


class ExactSchemaOllamaProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        timeout_seconds: int,
        opener: Callable[..., Any] = request.urlopen,
    ):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def invoke(
        self,
        *,
        call: dict[str, Any],
        model: str,
        prompt: str,
        schema: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "call_index": call["call_index"],
            "stage": call["stage"],
            "pair_id": call["pair_id"],
            "variant_id": call["variant_id"],
            "condition": call["condition"],
            "status": "invoked",
            "model_requested": model,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "schema_sha256": sha256_bytes(canonical_json(schema).encode("utf-8")),
            "input_sha256": call["input_sha256"],
            "num_predict": int(options["num_predict"]),
            "prompt_tokens": "unavailable",
            "completion_tokens": "unavailable",
            "latency_seconds": "unavailable",
            "raw_prompt_or_response_persisted": False,
        }
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "think": False,
            "options": options,
        }
        started = time.perf_counter()
        http_request = request.Request(
            self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(http_request, timeout=self.timeout_seconds) as response:
                response_body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            record.update(
                {
                    "status": "failed",
                    "latency_seconds": round(time.perf_counter() - started, 6),
                    "failure_category": "provider_transport_or_json",
                    "failure_class": type(exc).__name__,
                }
            )
            raise C2ProviderError("provider_transport_or_json", record) from exc
        elapsed = round(time.perf_counter() - started, 6)
        if not isinstance(response_body, dict) or not isinstance(response_body.get("response"), str):
            record.update(
                {
                    "status": "failed",
                    "latency_seconds": elapsed,
                    "failure_category": "provider_response_contract",
                    "failure_class": "ProviderResponseContract",
                }
            )
            raise C2ProviderError("provider_response_contract", record)
        text = response_body["response"]
        record.update(
            {
                "status": "completed",
                "response_sha256": sha256_bytes(text.encode("utf-8")),
                "prompt_tokens": int(response_body.get("prompt_eval_count") or 0),
                "completion_tokens": int(response_body.get("eval_count") or 0),
                "latency_seconds": elapsed,
                "model_reported": response_body.get("model") or model,
            }
        )
        return {"text": text, "record": record}


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if not path.exists():
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _batch_intent(contract: dict[str, Any], plan: list[dict[str, Any]]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_c2_batch_intent_v1",
        "status": "terminal_once_written",
        "contract_sha256": sha256_file(CONFIG_PATH),
        "implementation_freeze_sha256": sha256_file(FREEZE_PATH),
        "execution_plan_sha256": sha256_bytes(canonical_json(plan).encode("utf-8")),
        "model": contract["provider"]["model"],
        "model_call_ceiling": len(plan),
        "holdout_access_authorized": False,
        "retry_or_fallback_allowed": False,
    }
    value["intent_sha256"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _call_path(root: Path, call_index: int, suffix: str) -> Path:
    return root / "calls" / f"{call_index:03d}_{suffix}.json"


def _write_terminal_result(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    unhashed = deepcopy(result)
    result["result_sha256"] = sha256_bytes(canonical_json(unhashed).encode("utf-8"))
    _exclusive_json(root / "result.json", result)
    return result


def _result_validation(result: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_c2_controlled_context_flip_execution_result_v1":
        errors.append("schema")
    if result.get("status") not in {"dev_batch_complete", "terminal_incomplete"}:
        errors.append("status")
    if result.get("retry_count") != 0 or result.get("fallback_count") != 0:
        errors.append("retry")
    if result.get("holdout_input_access_count") != 0 or result.get("holdout_target_access_count") != 0:
        errors.append("holdout")
    if result.get("new_uruha_source_or_future_access_count") != 0:
        errors.append("uruha_access")
    if result.get("production_memory_write_count") != 0 or result.get("formal_m56_write_count") != 0:
        errors.append("write_boundary")
    if result.get("model_call_count", 0) > contract["execution_plan"]["total_model_call_ceiling"]:
        errors.append("call_ceiling")
    if result.get("status") == "dev_batch_complete":
        if result.get("model_call_count") != 32 or result.get("validated_prediction_count") != 32:
            errors.append("success_counts")
        if not isinstance(result.get("dev_score"), dict):
            errors.append("dev_score")
    else:
        if not result.get("failure_category") or not result.get("failed_call"):
            errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_sha256"}
    if result.get("result_sha256") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return errors


def execute_once(
    provider: Any | None = None,
    *,
    state_root: Path | None = None,
) -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    contract_validation = validate_contract(contract)
    if not contract_validation["valid"]:
        raise C2ContractError("invalid contract:" + ";".join(contract_validation["errors"]))
    plan = build_execution_plan(contract)
    items = _items_for_execution()
    root = state_root or (ROOT / contract["crash_safety"]["state_root"])
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    existing_result = root / "result.json"
    if existing_result.is_file():
        result = load_json(existing_result)
        errors = _result_validation(result, contract)
        if errors:
            raise C2ContractError("invalid existing result:" + ";".join(errors))
        return result
    intent = _batch_intent(contract, plan)
    intent_path = root / "batch_intent.json"
    if intent_path.is_file():
        if load_json(intent_path) != intent:
            raise C2ContractError("batch intent mismatch")
    else:
        _exclusive_json(intent_path, intent)
    active = provider or ExactSchemaOllamaProvider(
        endpoint=contract["provider"]["endpoint"],
        timeout_seconds=contract["provider"]["timeout_seconds"],
    )
    predictions: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for call in plan:
        call_intent_path = _call_path(root, call["call_index"], "intent")
        call_complete_path = _call_path(root, call["call_index"], "complete")
        call_failure_path = _call_path(root, call["call_index"], "failure")
        if call_complete_path.is_file():
            complete = load_json(call_complete_path)
            if complete.get("call") != call:
                raise C2ContractError("complete call mismatch")
            predictions.append(complete["prediction"])
            records.append(complete["record"])
            continue
        if call_intent_path.is_file():
            failure = {
                "schema": "uruha_p3_c2_controlled_context_flip_execution_result_v1",
                "version": "1.0.0",
                "status": "terminal_incomplete",
                "failure_category": "orphaned_call_intent_no_reinvocation",
                "failed_call": call,
                "model_call_count": call["call_index"],
                "validated_prediction_count": len(predictions),
                "call_records": records,
                "retry_count": 0,
                "fallback_count": 0,
                "holdout_input_access_count": 0,
                "holdout_target_access_count": 0,
                "new_uruha_source_or_future_access_count": 0,
                "production_memory_write_count": 0,
                "formal_m56_write_count": 0,
                "claim_boundary": contract["claim_boundary"],
            }
            return _write_terminal_result(root, failure)
        item = items[(call["pair_id"], call["variant_id"])]
        if item["input_sha256"] != call["input_sha256"]:
            raise C2ContractError("plan input hash mismatch")
        prompt = prompt_for(call["condition"], item)
        schema = output_schema(
            call["condition"], [anchor["id"] for anchor in item["evidence_anchors"]]
        )
        call_intent = {
            "schema": "uruha_p3_c2_call_intent_v1",
            "call": call,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "schema_sha256": sha256_bytes(canonical_json(schema).encode("utf-8")),
            "retry_allowed": False,
        }
        _exclusive_json(call_intent_path, call_intent)
        try:
            response = active.invoke(
                call=call,
                model=contract["provider"]["model"],
                prompt=prompt,
                schema=schema,
                options=contract["provider"]["options"],
            )
            prediction, normalization = parse_output(
                response["text"], call["condition"], item
            )
            complete = {
                "schema": "uruha_p3_c2_call_complete_v1",
                "call": call,
                "prediction": prediction,
                "normalization": normalization,
                "record": response["record"],
                "raw_prompt_or_response_persisted": False,
            }
            _exclusive_json(call_complete_path, complete)
            predictions.append(prediction)
            records.append(response["record"])
        except Exception as exc:
            if isinstance(exc, C2ProviderError):
                category = exc.category
                record = exc.record
            elif isinstance(exc, C2ContractError):
                category = str(exc).split(":", 1)[0]
                record = {
                    "call_index": call["call_index"],
                    "stage": call["stage"],
                    "pair_id": call["pair_id"],
                    "variant_id": call["variant_id"],
                    "condition": call["condition"],
                    "status": "completed_but_rejected",
                    "failure_category": category,
                    "raw_prompt_or_response_persisted": False,
                }
            else:
                category = "unexpected"
                record = {
                    "call_index": call["call_index"],
                    "status": "failed",
                    "failure_category": category,
                    "failure_class": type(exc).__name__,
                    "raw_prompt_or_response_persisted": False,
                }
            _exclusive_json(
                call_failure_path,
                {
                    "schema": "uruha_p3_c2_call_failure_v1",
                    "call": call,
                    "failure_category": category,
                    "record": record,
                    "retry_allowed": False,
                },
            )
            records.append(record)
            failure = {
                "schema": "uruha_p3_c2_controlled_context_flip_execution_result_v1",
                "version": "1.0.0",
                "status": "terminal_incomplete",
                "failure_category": category,
                "failed_call": call,
                "model_call_count": call["call_index"],
                "validated_prediction_count": len(predictions),
                "call_records": records,
                "retry_count": 0,
                "fallback_count": 0,
                "holdout_input_access_count": 0,
                "holdout_target_access_count": 0,
                "new_uruha_source_or_future_access_count": 0,
                "production_memory_write_count": 0,
                "formal_m56_write_count": 0,
                "claim_boundary": contract["claim_boundary"],
            }
            return _write_terminal_result(root, failure)
    dev_predictions = [
        prediction
        for prediction, call in zip(predictions, plan)
        if call["stage"] == "dev_complete"
    ]
    dev_score = c1.score_predictions(dev_predictions, "dev")
    result = {
        "schema": "uruha_p3_c2_controlled_context_flip_execution_result_v1",
        "version": "1.0.0",
        "status": "dev_batch_complete",
        "model": contract["provider"]["model"],
        "model_call_count": len(records),
        "validated_prediction_count": len(predictions),
        "smoke_prediction_count": 8,
        "dev_prediction_count": 24,
        "predictions": predictions,
        "call_records": records,
        "dev_score": dev_score,
        "actual_prompt_tokens_total": sum(int(row["prompt_tokens"]) for row in records),
        "actual_completion_tokens_total": sum(int(row["completion_tokens"]) for row in records),
        "model_latency_seconds_total": round(
            sum(float(row["latency_seconds"]) for row in records), 6
        ),
        "retry_count": 0,
        "fallback_count": 0,
        "holdout_input_access_count": 0,
        "holdout_target_access_count": 0,
        "new_uruha_source_or_future_access_count": 0,
        "production_memory_write_count": 0,
        "formal_m56_write_count": 0,
        "raw_prompt_or_response_persisted": False,
        "claim_boundary": contract["claim_boundary"],
    }
    _write_terminal_result(root, result)
    errors = _result_validation(result, contract)
    if errors:
        raise C2ContractError("invalid result:" + ";".join(errors))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-C2 controlled context-flip execution")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("P3-C2 supports only --execute-once")
    result = execute_once()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "dev_batch_complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
