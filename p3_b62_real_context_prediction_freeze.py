"""B62 same-model literal-vs-pragmatic predictions before future unlock."""

from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Callable

from longitudinal_human_model.baselines import OllamaProvider, ProviderError, _extract_json_object
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b60_caption_context_reader as public_reader


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b62_real_context_prediction_freeze_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b62_real_context_prediction_implementation_freeze_2026-09-20.json"


class B62ContractError(ValueError):
    pass


class B62ExecutionError(RuntimeError):
    def __init__(self, stage: str, category: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.category = category


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
    if contract.get("schema") != "uruha_p3_b62_real_context_prediction_freeze_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_before_any_real_context_model_call_or_future_outcome_access":
        errors.append("status")
    if contract.get("claim_level") != "single_real_row_exploratory_prediction_not_formal_m56":
        errors.append("claim_level")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    release_binding = (contract.get("bindings") or {}).get("b61_release") or {}
    if release_binding:
        release = load_json(Path(root) / release_binding["path"])
        if release.get("status") != "released_real_pre_cutoff_context":
            errors.append("release_status")
        if release.get("result", {}).get("public_artifact_sha256") != contract.get("input", {}).get("artifact_sha256"):
            errors.append("release_artifact")
    source = contract.get("input") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_seconds") != [3000.0, 3180.0]
        or source.get("future_outcome_seconds") != [3181.0, 3241.0]
        or source.get("cue_count") != 65
        or source.get("future_outcome_access_before_prediction_freeze_required") != 0
        or source.get("acquisition_module_import_allowed") is not False
    ):
        errors.append("input_boundary")
    labels = (contract.get("target") or {}).get("candidate_behavior_labels") or []
    if labels != [
        "acknowledge_then_continue",
        "accept_support_and_continue",
        "ask_clarification",
        "defer_commitment",
        "direct_rejection",
        "pause_and_reassess",
    ]:
        errors.append("labels")
    conditions = contract.get("conditions") or {}
    if set(conditions) != {"BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"}:
        errors.append("conditions")
    if conditions.get("BASELINE_LITERAL", {}).get("inference_about_emotion_intent_relationship_or_need_allowed") is not False:
        errors.append("baseline_boundary")
    if conditions.get("SYSTEM_PRAGMATIC_STATE", {}).get("private_thought_or_unseen_fact_assertion_allowed") is not False:
        errors.append("system_boundary")
    fairness = contract.get("fairness") or {}
    for field in (
        "same_base_model",
        "same_context_artifact",
        "same_target_and_label_contract",
        "same_two_call_graph",
        "same_options_per_call",
        "actual_prompt_completion_tokens_and_latency_recorded",
        "unequal_actual_token_use_must_be_reported",
    ):
        if fairness.get(field) is not True:
            errors.append(f"fairness:{field}")
    if fairness.get("same_completion_token_ceiling_per_condition") != 512:
        errors.append("token_ceiling")
    if fairness.get("representation_call_num_predict") != 256 or fairness.get("prediction_call_num_predict") != 256:
        errors.append("call_budget")
    model = contract.get("model") or {}
    if model.get("provider") != "local_ollama" or model.get("name") != "qwen3.5:9b":
        errors.append("model")
    if model.get("options") != {"temperature": 0, "seed": 260920, "num_ctx": 8192}:
        errors.append("options")
    output = contract.get("output_contract") or {}
    if output.get("probabilities_exactly_all_labels") is not True or output.get("probabilities_sum_tolerance") != 0.000001:
        errors.append("probability_contract")
    if output.get("predicted_next_content_language") != "ja" or output.get("predicted_next_content_max_characters") != 160:
        errors.append("content_contract")
    if output.get("representation_text_persistence_allowed") is not False or output.get("raw_prompt_or_model_response_persistence_allowed") is not False:
        errors.append("persistence")
    execution = contract.get("execution") or {}
    if execution.get("condition_order") != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
        errors.append("condition_order")
    if execution.get("model_call_count_exact") != 4 or execution.get("retry_or_condition_fallback_allowed") is not False:
        errors.append("execution")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b62_model_calls_or_future_access":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B62ContractError(";".join(errors))
    return {
        "valid": True,
        "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"),
        "future_outcome_access_count_at_freeze": freeze.get("future_outcome_access_count_at_freeze"),
    }


def load_public_context(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    input_contract = contract["input"]
    public_root = ROOT / input_contract["public_root"]
    previous = os.environ.get(public_reader.PUBLIC_ROOT_ENV)
    os.environ[public_reader.PUBLIC_ROOT_ENV] = str(public_root)
    try:
        inspection = public_reader.inspect_artifact(input_contract["artifact_id"])
    finally:
        if previous is None:
            os.environ.pop(public_reader.PUBLIC_ROOT_ENV, None)
        else:
            os.environ[public_reader.PUBLIC_ROOT_ENV] = previous
    if inspection["artifact_summary"]["artifact_sha256"] != input_contract["artifact_sha256"]:
        raise B62ExecutionError("input", "artifact_hash", "public artifact hash")
    path = public_root / f"{input_contract['artifact_id']}.json"
    payload = path.read_bytes()
    if sha256_bytes(payload) != input_contract["artifact_sha256"]:
        raise B62ExecutionError("input", "artifact_hash", "public artifact changed")
    artifact = json.loads(payload)
    if len(artifact.get("cues") or []) != input_contract["cue_count"]:
        raise B62ExecutionError("input", "cue_count", "public cue count")
    return artifact


def _context_text(artifact: dict[str, Any]) -> str:
    return "\n".join(
        f"[{cue['start_seconds']:.3f}-{cue['end_seconds']:.3f}] {cue['text']}"
        for cue in artifact["cues"]
    )


def representation_prompt(condition: str, artifact: dict[str, Any], contract: dict[str, Any]) -> str:
    common = {
        "target": contract["target"]["reference_person"],
        "persona_boundary": contract["target"]["persona_boundary"],
        "observable_context": _context_text(artifact),
        "constraints": ["Return JSON only.", "Use only the observable context.", "Do not invent private or unseen facts."],
    }
    if condition == "BASELINE_LITERAL":
        common.update(
            {
                "task": "Create a literal chronological representation without pragmatic, emotional, relational, or hidden-intent inference.",
                "output_contract": {
                    "literal_summary": "concise Japanese string",
                    "current_topic": "Japanese string",
                    "explicit_actions": ["Japanese strings"],
                },
            }
        )
    elif condition == "SYSTEM_PRAGMATIC_STATE":
        common.update(
            {
                "task": "Create a falsifiable pragmatic-state hypothesis from the observable context while keeping uncertainty explicit.",
                "output_contract": {
                    "observed_literal": "concise Japanese string",
                    "primary_hypothesis": "Japanese string",
                    "evidence": ["short Japanese strings tied to observed context"],
                    "confidence": "number from 0 to 1",
                    "alternative_hypothesis": "Japanese string",
                    "stance_or_emotion": "Japanese string or unknown",
                    "relationship_signal": "Japanese string or unknown",
                    "implicit_need": "Japanese string or unknown",
                    "next_action_tendency": "Japanese string",
                },
            }
        )
    else:
        raise ValueError("unknown condition")
    return canonical_json(common)


def _validate_representation(condition: str, value: dict[str, Any]) -> dict[str, Any]:
    if condition == "BASELINE_LITERAL":
        if set(value) != {"literal_summary", "current_topic", "explicit_actions"}:
            raise B62ExecutionError("representation", "schema", "literal schema")
        if not isinstance(value["literal_summary"], str) or not isinstance(value["current_topic"], str):
            raise B62ExecutionError("representation", "schema", "literal strings")
        if not isinstance(value["explicit_actions"], list) or any(not isinstance(item, str) for item in value["explicit_actions"]):
            raise B62ExecutionError("representation", "schema", "literal actions")
    else:
        required = {
            "observed_literal",
            "primary_hypothesis",
            "evidence",
            "confidence",
            "alternative_hypothesis",
            "stance_or_emotion",
            "relationship_signal",
            "implicit_need",
            "next_action_tendency",
        }
        if set(value) != required:
            raise B62ExecutionError("representation", "schema", "pragmatic schema")
        string_fields = required - {"evidence", "confidence"}
        if any(not isinstance(value[field], str) for field in string_fields):
            raise B62ExecutionError("representation", "schema", "pragmatic strings")
        if not isinstance(value["evidence"], list) or any(not isinstance(item, str) for item in value["evidence"]):
            raise B62ExecutionError("representation", "schema", "pragmatic evidence")
        confidence = value["confidence"]
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            raise B62ExecutionError("representation", "schema", "confidence")
    return value


def prediction_prompt(condition: str, representation: dict[str, Any], contract: dict[str, Any]) -> str:
    labels = contract["target"]["candidate_behavior_labels"]
    return canonical_json(
        {
            "task": contract["target"]["task"],
            "target": contract["target"]["reference_person"],
            "persona_boundary": contract["target"]["persona_boundary"],
            "condition": condition,
            "pre_cutoff_representation": representation,
            "candidate_behavior_labels": labels,
            "output_contract": {
                "probabilities": {label: "number from 0 to 1" for label in labels},
                "predicted_next_content": "natural Japanese, at most 160 characters",
                "brief_evidence": "one short Japanese sentence",
            },
            "constraints": [
                "Return JSON only.",
                "Use every label exactly once and make probabilities sum to 1.",
                "Do not invent private or unseen facts.",
                "Keep the prediction falsifiable and allow uncertainty.",
            ],
        }
    )


def _parse_prediction(text: str, labels: list[str], max_characters: int) -> dict[str, Any]:
    parsed = _extract_json_object(text)
    probabilities = parsed.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(labels):
        raise B62ExecutionError("prediction", "schema", "probability labels")
    checked: dict[str, float] = {}
    for label in labels:
        value = probabilities[label]
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0:
            raise B62ExecutionError("prediction", "schema", "probability value")
        checked[label] = float(value)
    total = sum(checked.values())
    if abs(total - 1.0) > 0.000001:
        raise B62ExecutionError("prediction", "schema", "probability sum")
    content = parsed.get("predicted_next_content")
    evidence = parsed.get("brief_evidence")
    if not isinstance(content, str) or not content.strip() or len(content) > max_characters:
        raise B62ExecutionError("prediction", "schema", "predicted content")
    if re.search(r"[\u3040-\u30ff]", content) is None:
        raise B62ExecutionError("prediction", "language", "predicted content not Japanese")
    if not isinstance(evidence, str):
        raise B62ExecutionError("prediction", "schema", "brief evidence")
    selected = max(labels, key=lambda label: (checked[label], -labels.index(label)))
    return {
        "probabilities": checked,
        "selected_behavior": selected,
        "predicted_next_content": content.strip(),
        "brief_evidence": evidence.strip()[:300],
    }


def _call(
    provider: Callable[..., dict[str, Any]],
    prompt: str,
    contract: dict[str, Any],
    *,
    num_predict: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    options = dict(contract["model"]["options"])
    options["num_predict"] = num_predict
    response = provider(model=contract["model"]["name"], prompt=prompt, options=options)
    if not isinstance(response.get("text"), str):
        raise B62ExecutionError("model", "provider", "missing model text")
    record = {
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "response_sha256": sha256_bytes(response["text"].encode("utf-8")),
        "prompt_tokens": int(response.get("prompt_tokens") or 0),
        "completion_tokens": int(response.get("completion_tokens") or 0),
        "latency_seconds": round(float(response.get("latency_seconds") or 0.0), 6),
        "model_reported": response.get("model_reported") or contract["model"]["name"],
        "num_predict": num_predict,
    }
    return response, record


def run_condition(
    condition: str,
    artifact: dict[str, Any],
    contract: dict[str, Any],
    provider: Callable[..., dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rep_prompt = representation_prompt(condition, artifact, contract)
    rep_response, rep_record = _call(
        provider,
        rep_prompt,
        contract,
        num_predict=contract["fairness"]["representation_call_num_predict"],
    )
    representation = _validate_representation(condition, _extract_json_object(rep_response["text"]))
    representation_hash = sha256_bytes(canonical_json(representation).encode("utf-8"))
    pred_prompt = prediction_prompt(condition, representation, contract)
    pred_response, pred_record = _call(
        provider,
        pred_prompt,
        contract,
        num_predict=contract["fairness"]["prediction_call_num_predict"],
    )
    prediction = _parse_prediction(
        pred_response["text"],
        contract["target"]["candidate_behavior_labels"],
        contract["output_contract"]["predicted_next_content_max_characters"],
    )
    prediction["condition"] = condition
    prediction["representation_sha256"] = representation_hash
    prediction["representation_persisted"] = False
    prediction["raw_prompt_or_response_persisted"] = False
    return prediction, [rep_record, pred_record]


def _fresh_state_root(contract: dict[str, Any]) -> Path:
    root = ROOT / contract["execution"]["result_state_root"]
    if root.exists():
        raise B62ExecutionError("preflight", "preflight", "B62 already consumed")
    root.mkdir(parents=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b62_prediction_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_complete_result",
        "artifact_sha256": contract["input"]["artifact_sha256"],
        "condition_order": contract["execution"]["condition_order"],
        "model": contract["model"]["name"],
        "model_call_count_exact": 4,
        "future_outcome_access_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b62_real_context_prediction_result_v1":
        errors.append("schema")
    if result.get("status") not in {"prediction_frozen", "prediction_failed"}:
        errors.append("status")
    if result.get("future_outcome_access_count") != 0 or result.get("outcome_score_count") != 0:
        errors.append("future_boundary")
    if result.get("training_write_count") != 0 or result.get("formal_m56_write_count") != 0 or result.get("production_memory_write_count") != 0:
        errors.append("write_boundary")
    forbidden = {"artifact_text", "cues", "representation", "raw_prompt", "raw_response", "future", "outcome"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "prediction_frozen":
        if result.get("model_call_count") != 4:
            errors.append("call_count")
        predictions = result.get("predictions")
        if not isinstance(predictions, list) or [row.get("condition") for row in predictions] != contract["execution"]["condition_order"]:
            errors.append("predictions")
        else:
            for row in predictions:
                if row.get("representation_persisted") is not False or row.get("raw_prompt_or_response_persisted") is not False:
                    errors.append("prediction_persistence")
                try:
                    _parse_prediction(canonical_json(row), contract["target"]["candidate_behavior_labels"], 160)
                except (B62ExecutionError, ProviderError):
                    errors.append("prediction_contract")
        records = result.get("call_records")
        if not isinstance(records, list) or len(records) != 4:
            errors.append("call_records")
        if result.get("completion_token_ceiling_by_condition") != {"BASELINE_LITERAL": 512, "SYSTEM_PRAGMATIC_STATE": 512}:
            errors.append("token_ceiling")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_prediction_freeze(
    provider: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B62ContractError("invalid B62 contract: " + ";".join(report["errors"]))
    contract = load_contract()
    state_root = _fresh_state_root(contract)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    result: dict[str, Any] = {
        "schema": "uruha_p3_b62_real_context_prediction_result_v1",
        "version": "1.0.0",
        "source_id": contract["input"]["source_id"],
        "artifact_sha256": contract["input"]["artifact_sha256"],
        "model": contract["model"]["name"],
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }
    started = perf_counter()
    call_records: list[dict[str, Any]] = []
    try:
        artifact = load_public_context(contract)
        active_provider = provider or OllamaProvider(
            endpoint=contract["model"]["endpoint"], timeout=contract["model"]["timeout_seconds"]
        )
        predictions = []
        for condition in contract["execution"]["condition_order"]:
            prediction, records = run_condition(condition, artifact, contract, active_provider)
            predictions.append(prediction)
            call_records.extend(records)
            result["model_call_count"] = len(call_records)
        artifact = None
        result["predictions"] = predictions
        result["call_records"] = call_records
        result["completion_token_ceiling_by_condition"] = {
            condition: contract["fairness"]["same_completion_token_ceiling_per_condition"]
            for condition in contract["execution"]["condition_order"]
        }
        result["actual_prompt_tokens_by_condition"] = {
            condition: sum(call_records[index]["prompt_tokens"] for index in (offset, offset + 1))
            for offset, condition in zip((0, 2), contract["execution"]["condition_order"])
        }
        result["actual_completion_tokens_by_condition"] = {
            condition: sum(call_records[index]["completion_tokens"] for index in (offset, offset + 1))
            for offset, condition in zip((0, 2), contract["execution"]["condition_order"])
        }
        result["latency_seconds_by_condition"] = {
            condition: round(sum(call_records[index]["latency_seconds"] for index in (offset, offset + 1)), 6)
            for offset, condition in zip((0, 2), contract["execution"]["condition_order"])
        }
        result["status"] = "prediction_frozen"
    except Exception as exc:
        result["call_records"] = call_records
        result["model_call_count"] = len(call_records)
        result["status"] = "prediction_failed"
        if isinstance(exc, B62ExecutionError):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
        elif isinstance(exc, ProviderError):
            result["failure_stage"] = "model"
            result["failure_category"] = "provider_or_schema"
        else:
            result["failure_stage"] = "unexpected"
            result["failure_category"] = "unknown"
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - started, 6)
    _finalize_result(result)
    validation = validate_result(result, contract)
    if not validation["valid"]:
        raise B62ContractError("invalid B62 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B62 freeze real-context predictions")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B62 supports only the frozen one-shot prediction execution")
    result = execute_prediction_freeze()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "prediction_frozen":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
