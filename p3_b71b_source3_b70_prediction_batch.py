"""B71B source3 context-only acquisition and B70-bound paired predictions."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any

from longitudinal_human_model.baselines import ProviderError
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56
import p3_b61_native_subtitle_cutoff_extractor as b61
import p3_b62_real_context_prediction_freeze as b62
import p3_b65_bounded_joint_prediction_interface as b65
import p3_b69b_source2_multiwindow_predictions as b69b
import p3_b70_prediction_interface_reliability as b70
import p3_b71b_context_batch_reader as context_reader


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b71b_source3_b70_prediction_batch_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b71b_source3_b70_prediction_batch_implementation_freeze_2026-09-20.json"


class B71BContractError(ValueError):
    pass


class B71BExecutionError(RuntimeError):
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


def expected_rows() -> list[dict[str, Any]]:
    return [
        {"row_id": "s3r0600", "context_milliseconds": [600000, 780000], "future_milliseconds": [781000, 841000]},
        {"row_id": "s3r1200", "context_milliseconds": [1200000, 1380000], "future_milliseconds": [1381000, 1441000]},
        {"row_id": "s3r1800", "context_milliseconds": [1800000, 1980000], "future_milliseconds": [1981000, 2041000]},
        {"row_id": "s3r2400", "context_milliseconds": [2400000, 2580000], "future_milliseconds": [2581000, 2641000]},
    ]


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b71b_source3_b70_prediction_batch_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_before_source3_caption_content_model_calls_or_future_access":
        errors.append("status")
    if contract.get("claim_level") != "source3_prospective_development_replication_not_independent_holdout_or_formal_m56":
        errors.append("claim_level")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file() or sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding:{name}")
    source = contract.get("source") or {}
    if source.get("source_id") != "youtube_j6Hlk9cY9LQ" or source.get("video_id") != "j6Hlk9cY9LQ" or source.get("rows") != expected_rows():
        errors.append("source")
    if [source.get("selected_track_type"), source.get("selected_language_code"), source.get("selected_format")] != ["automatic", "ja", "json3"]:
        errors.append("track")
    if source.get("minimum_context_cues_each_row") != 1 or source.get("prediction_side_future_access_before_complete_batch_required") != 0:
        errors.append("source_boundary")
    private = contract.get("private_acquisition") or {}
    if private.get("native_downloader_process_invocation_count_max") != 1 or private.get("maximum_private_caption_bytes") != 10485760:
        errors.append("private_limits")
    for field in ("reuse_b61_native_downloader_command_and_private_file_contract", "private_full_caption_may_be_temporarily_observed", "private_full_caption_deleted_before_fresh_context_reader_and_model"):
        if private.get(field) is not True:
            errors.append(f"private_true:{field}")
    for field in ("retry_or_fallback_allowed", "cookies_login_paid_api_or_account_access_allowed", "raw_full_caption_or_any_future_cue_persistence_allowed"):
        if private.get(field) is not False:
            errors.append(f"private_false:{field}")
    expected_public = {
        "root": "external_data/p3_b71b_public_context_batch",
        "artifact_schema": "uruha_p3_b71b_public_context_row_v1",
        "manifest_schema": "uruha_p3_b71b_public_context_row_manifest_v1",
        "artifact_count_exact": 4,
        "fresh_reader_process_count": 1,
        "persist_only_context_cues": True,
        "future_cues_or_ranges_persisted": False,
    }
    if contract.get("public_context_batch") != expected_public:
        errors.append("public")
    expected_experiment = {
        "reuse_b65_joint_prompt_model_schema_and_options": True,
        "use_b70_parser_adapter_for_both_conditions": True,
        "condition_order": ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"],
        "row_order": ["s3r0600", "s3r1200", "s3r1800", "s3r2400"],
        "model": "qwen3.5:9b",
        "temperature": 0,
        "seed": 260920,
        "num_ctx": 8192,
        "think": False,
        "completion_token_ceiling_each_condition": 512,
        "model_call_count_exact": 8,
        "state_text_persistence_allowed": False,
        "raw_prompt_or_response_persistence_allowed": False,
    }
    if contract.get("prediction_experiment") != expected_experiment:
        errors.append("experiment")
    if b65.validate_contract() != {"valid": True, "errors": []} or b70.validate_contract() != {"valid": True, "errors": []}:
        errors.append("dependency")
    if (contract.get("execution") or {}).get("retry_or_condition_fallback_allowed") is not False:
        errors.append("retry")
    if any(value is not True for value in (contract.get("denied_actions") or {}).values()):
        errors.append("denied")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b71b_caption_content_model_calls_or_future_access":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B71BContractError("invalid freeze: " + ";".join(errors))
    return {"valid": True, "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"), "future_access_count_at_freeze": freeze.get("future_access_count_at_freeze")}


def _exclusive_bytes(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def publish_context_batch(artifacts: list[dict[str, Any]], public_root: Path, contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    if public_root.exists() and any(public_root.iterdir()):
        raise B71BExecutionError("publication", "preexisting_public", "public root")
    if [artifact["row_id"] for artifact in artifacts] != contract["prediction_experiment"]["row_order"]:
        raise B71BExecutionError("publication", "row_order", "row order")
    public_root.mkdir(parents=True, mode=0o700)
    os.chmod(public_root, 0o700)
    manifests = []
    for artifact in artifacts:
        payload = canonical_json(artifact).encode("utf-8")
        digest = sha256_bytes(payload)
        artifact_id = f"p3-b71b-{artifact['row_id']}-{digest[:16]}"
        cues = artifact["cues"]
        manifest = {
            "schema": contract["public_context_batch"]["manifest_schema"],
            "version": "1.0.0",
            "artifact_id": artifact_id,
            "artifact_sha256": digest,
            "artifact_bytes": len(payload),
            "source_id": artifact["source_id"],
            "row_id": artifact["row_id"],
            "context_seconds": artifact["context_seconds"],
            "language_code": "ja",
            "track_type": "automatic",
            "format": "json3",
            "cue_count": len(cues),
            "first_cue_start_seconds": cues[0]["start_seconds"],
            "last_cue_end_seconds": max(cue["end_seconds"] for cue in cues),
            "raw_full_caption_persisted": False,
            "future_cues_or_ranges_persisted": False,
        }
        manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
        _exclusive_bytes(public_root / f"{artifact_id}.json", payload)
        _exclusive_bytes(public_root / f"{artifact_id}.manifest.json", canonical_json(manifest).encode("utf-8"))
        manifests.append(manifest)
    os.chmod(public_root, 0o500)
    return manifests


def _source3_downloader_contract(contract: dict[str, Any]) -> dict[str, Any]:
    derived = deepcopy(b61.load_contract())
    derived["source"]["source_id"] = contract["source"]["source_id"]
    derived["source"]["video_id"] = contract["source"]["video_id"]
    return derived


def _fresh_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["execution"]["state_root"]
    public_root = ROOT / contract["public_context_batch"]["root"]
    if state_root.exists() or (public_root.exists() and any(public_root.iterdir())):
        raise B71BExecutionError("preflight", "preflight", "B71B already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b71b_prediction_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_complete_batch",
        "source_id": contract["source"]["source_id"],
        "row_order": contract["prediction_experiment"]["row_order"],
        "condition_order": contract["prediction_experiment"]["condition_order"],
        "model_call_count_exact": 8,
        "b70_adapter_bound": True,
        "future_access_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b71b_source3_b70_prediction_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "row_order": contract["prediction_experiment"]["row_order"],
        "condition_order": contract["prediction_experiment"]["condition_order"],
        "model": contract["prediction_experiment"]["model"],
        "interface": "b65_joint_prompt_with_b70_probability_adapter",
        "native_downloader_process_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "private_full_caption_access_count": 0,
        "private_full_caption_filename_persisted": False,
        "private_full_caption_hash_persisted": False,
        "raw_full_caption_persisted": False,
        "future_cues_or_ranges_persisted": False,
        "prediction_side_future_access_count": 0,
        "outcome_score_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    rows = ["s3r0600", "s3r1200", "s3r1800", "s3r2400"]
    conditions = ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]
    if result.get("schema") != "uruha_p3_b71b_source3_b70_prediction_result_v1" or result.get("status") not in {"prediction_batch_frozen", "prediction_batch_failed"}:
        errors.append("identity")
    if result.get("row_order") != rows or result.get("condition_order") != conditions:
        errors.append("order")
    for field in ("private_full_caption_filename_persisted", "private_full_caption_hash_persisted", "raw_full_caption_persisted", "future_cues_or_ranges_persisted"):
        if result.get(field) is not False:
            errors.append(field)
    for field in ("prediction_side_future_access_count", "outcome_score_count", "retry_count", "fallback_count", "training_write_count", "formal_m56_write_count", "production_memory_write_count"):
        if result.get(field) != 0:
            errors.append(field)
    records = result.get("call_records")
    if not isinstance(records, list) or result.get("model_call_count") != len(records):
        errors.append("accounting")
    elif any(record.get("call_index") != index or record.get("num_predict") != 512 for index, record in enumerate(records, start=1)):
        errors.append("records")
    if result.get("status") == "prediction_batch_frozen":
        if result.get("native_downloader_process_invocation_count") != 1 or result.get("downloader_returncode") != 0 or result.get("private_full_caption_access_count") != 1:
            errors.append("acquisition")
        if result.get("private_full_caption_deleted_before_context_reader_and_model") is not True or result.get("private_runtime_deleted_before_context_reader_and_model") is not True:
            errors.append("deletion")
        if result.get("public_context_artifact_count") != 4 or result.get("fresh_context_reader_count") != 1 or result.get("fresh_reader_future_content_returned") is not False:
            errors.append("public")
        predictions = result.get("predictions")
        pairs = [(row, condition) for row in rows for condition in conditions]
        if result.get("model_call_count") != 8 or result.get("prediction_count") != 8 or not isinstance(predictions, list) or [(item.get("row_id"), item.get("condition")) for item in predictions] != pairs:
            errors.append("predictions")
        else:
            labels = b65.load_contract()["target"]["candidate_behavior_labels"]
            for item in predictions:
                if item.get("normalization_contract") != "p3_b70_v1" or item.get("selected_behavior_preserved") is not True or item.get("state_persisted") is not False or item.get("raw_prompt_or_response_persisted") is not False:
                    errors.append("adapter_or_persistence")
                try:
                    b62._parse_prediction(canonical_json(item), labels, 160)
                except Exception:
                    errors.append("prediction_contract")
    elif not result.get("failure_stage") or not result.get("failure_category"):
        errors.append("failure")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("hash")
    return {"valid": not errors, "errors": errors}


def execute_prediction_batch(provider: b65.JointSchemaOllamaProvider | None = None) -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    report = validate_contract(contract)
    if not report["valid"]:
        raise B71BContractError("invalid contract: " + ";".join(report["errors"]))
    state_root, public_root = _fresh_roots(contract)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    b65_contract = b65.load_contract()
    active = provider or b65.JointSchemaOllamaProvider(endpoint=b65_contract["model"]["endpoint"], timeout=b65_contract["model"]["timeout_seconds"], labels=b65_contract["target"]["candidate_behavior_labels"])
    result = _base_result(contract)
    raw_caption = artifacts = private_runtime_path = None
    started = time.perf_counter()
    try:
        executable = shutil.which("yt-dlp")
        if executable is None:
            raise B71BExecutionError("tool_preflight", "tool_preflight", "yt-dlp")
        downloader_contract = _source3_downloader_contract(contract)
        version = b55_v2._tool_version(executable, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
        if version != downloader_contract["native_downloader"]["required_version"]:
            raise B71BExecutionError("tool_preflight", "tool_preflight", "version")
        result["yt_dlp_version"] = version
        with TemporaryDirectory(prefix="uruha-p3-b71b-private-") as temporary:
            private_root = Path(temporary)
            private_runtime_path = private_root
            os.chmod(private_root, 0o700)
            result["native_downloader_process_invocation_count"] = 1
            download_started = time.perf_counter()
            completed = subprocess.run(b61.build_native_downloader_command(private_root, downloader_contract), check=False, capture_output=True, timeout=downloader_contract["native_downloader"]["timeout_seconds"])
            result["downloader_elapsed_seconds"] = round(time.perf_counter() - download_started, 6)
            result["downloader_returncode"] = completed.returncode
            stdout, stderr = completed.stdout or b"", completed.stderr or b""
            result["downloader_stdout_bytes_discarded"] = len(stdout)
            result["downloader_stderr_bytes_discarded"] = len(stderr)
            if completed.returncode != 0:
                category = b56.classify_private_stderr(stderr)
                stdout = stderr = b""
                raise B71BExecutionError("native_downloader", category, "download")
            stdout = stderr = b""
            caption_path, raw_caption = b61.read_single_private_caption(private_root, downloader_contract)
            result["private_full_caption_access_count"] = 1
            result["private_full_caption_bytes_discarded_after_projection"] = len(raw_caption)
            artifacts = b69b.extract_context_batch(raw_caption, contract)
            caption_path.unlink()
            result["private_full_caption_deleted_before_context_reader_and_model"] = True
            raw_caption = None
        result["private_runtime_deleted_before_context_reader_and_model"] = not private_runtime_path.exists()
        manifests = publish_context_batch(artifacts, public_root, contract)
        artifacts = None
        result["public_context_artifact_count"] = len(manifests)
        result["public_context_artifacts"] = [{key: manifest[key] for key in ("row_id", "artifact_id", "artifact_sha256", "cue_count", "first_cue_start_seconds", "last_cue_end_seconds")} for manifest in manifests]
        environment = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", context_reader.PUBLIC_ROOT_ENV: str(public_root)}
        child = subprocess.run([sys.executable, str(ROOT / "p3_b71b_context_batch_reader.py"), "--read-batch", *[manifest["artifact_id"] for manifest in manifests]], cwd=str(ROOT), env=environment, check=False, capture_output=True, text=True, timeout=60)
        result["fresh_context_reader_count"] = 1
        result["fresh_context_reader_exit_code"] = child.returncode
        if child.returncode != 0:
            raise B71BExecutionError("fresh_context_reader", "public_reader", "reader")
        batch = json.loads(child.stdout)
        result["fresh_reader_future_content_returned"] = batch.get("future_content_returned")
        if result["fresh_reader_future_content_returned"] is not False:
            raise B71BExecutionError("fresh_context_reader", "future_boundary", "future")
        predictions = []
        for row in batch["rows"]:
            row_id = row["artifact"]["row_id"]
            for condition in contract["prediction_experiment"]["condition_order"]:
                prompt = b65.joint_prompt(condition, row["artifact"], b65_contract)
                before = len(active.records)
                try:
                    response = active(model=b65_contract["model"]["name"], prompt=prompt, options=b65_contract["model"]["options"])
                finally:
                    if len(active.records) > before:
                        active.records[-1].update({"row_id": row_id, "condition": condition})
                parsed = b70.parse_joint_output_normalized(response["text"], condition, b65_contract)
                parsed["row_id"] = row_id
                predictions.append(parsed)
        result.update({"predictions": predictions, "prediction_count": len(predictions), "status": "prediction_batch_frozen"})
    except Exception as exc:
        raw_caption = artifacts = None
        result["status"] = "prediction_batch_failed"
        if isinstance(exc, (B71BExecutionError, b62.B62ExecutionError)):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
            if isinstance(exc, b62.B62ExecutionError):
                result["failure_detail_allowlisted"] = b70.allowlisted_failure_reason(exc)
        elif isinstance(exc, ProviderError):
            result.update({"failure_stage": "model", "failure_category": "provider_or_schema"})
        else:
            result.update({"failure_stage": "unexpected", "failure_category": "unknown"})
        result["failure_class"] = type(exc).__name__
    result["call_records"] = active.records
    result["model_call_count"] = len(active.records)
    if result["status"] == "prediction_batch_frozen":
        result["actual_prompt_tokens_total"] = sum(int(record["prompt_tokens"]) for record in active.records)
        result["actual_completion_tokens_total"] = sum(int(record["completion_tokens"]) for record in active.records)
        result["model_latency_seconds_total"] = round(sum(float(record["latency_seconds"]) for record in active.records), 6)
        result["normalization_applied_count"] = sum(1 for prediction in result["predictions"] if prediction["normalization_applied"])
    result["total_elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B71BContractError("invalid result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B71B supports only one frozen execution")
    result = execute_prediction_batch()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "prediction_batch_frozen":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
