"""B66 separately bound future-outcome unlock and deterministic proxy scoring."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56
import p3_b61_native_subtitle_cutoff_extractor as b61
import p3_b65_bounded_joint_prediction_interface as b65
import p3_b66_future_outcome_reader as future_reader


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b66_future_outcome_unlock_scoring_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b66_future_outcome_unlock_scoring_implementation_freeze_2026-09-20.json"


class B66ContractError(ValueError):
    pass


class B66ExecutionError(RuntimeError):
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
    if contract.get("schema") != "uruha_p3_b66_future_outcome_unlock_scoring_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_after_prediction_pair_before_future_outcome_access":
        errors.append("status")
    if contract.get("claim_level") != "single_real_row_deterministic_proxy_not_human_label_or_formal_m56":
        errors.append("claim_level")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    release_binding = (contract.get("bindings") or {}).get("b65_release") or {}
    if release_binding:
        release = load_json(Path(root) / release_binding["path"])
        if release.get("status") != "released_frozen_prediction_pair_for_separate_future_unlock":
            errors.append("release_status")
        next_stage = release.get("next_stage") or {}
        if next_stage.get("id") != "P3-B66" or next_stage.get("prediction_mutation_after_unlock_allowed") is not False:
            errors.append("release_next")
    prediction_binding = (contract.get("bindings") or {}).get("b65_saved_prediction") or {}
    if prediction_binding:
        prediction = load_json(Path(root) / prediction_binding["path"])
        if b65.validate_result(prediction) != {"valid": True, "errors": []}:
            errors.append("prediction_result")
        if prediction.get("status") != "prediction_pair_frozen" or prediction.get("result_hash") != "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe":
            errors.append("prediction_identity")
        if prediction.get("future_outcome_access_count") != 0:
            errors.append("prediction_future_boundary")
    source = contract.get("source") or {}
    if source != {
        "source_id": "youtube_4y5GiQpgJgo",
        "video_id": "4y5GiQpgJgo",
        "future_start_milliseconds": 3181000,
        "future_end_milliseconds": 3241000,
        "include_rule": "cue_start_gte_future_start_and_cue_end_lte_future_end",
        "selected_track_type": "automatic",
        "selected_language_code": "ja",
        "selected_format": "json3",
        "minimum_future_cue_count": 1,
    }:
        errors.append("source")
    private = contract.get("private_acquisition") or {}
    required_true = (
        "reuse_b61_native_downloader_command_and_private_file_contract",
        "private_full_caption_may_be_temporarily_observed",
        "private_full_caption_deleted_before_public_scoring",
    )
    if any(private.get(field) is not True for field in required_true):
        errors.append("private_true")
    if private.get("native_downloader_process_invocation_count_max") != 1 or private.get("maximum_private_caption_bytes") != 10485760:
        errors.append("private_limits")
    for field in (
        "retry_or_fallback_allowed",
        "cookies_login_paid_api_or_account_access_allowed",
        "raw_full_caption_stdout_stderr_filename_or_hash_persistence_allowed",
    ):
        if private.get(field) is not False:
            errors.append(f"private_denial:{field}")
    public = contract.get("public_outcome") or {}
    if public != {
        "root": "external_data/p3_b66_public_future_outcome",
        "artifact_schema": "uruha_p3_b66_public_future_outcome_v1",
        "manifest_schema": "uruha_p3_b66_public_future_outcome_manifest_v1",
        "persist_only_projected_future_window": True,
        "context_window_cues_persisted": False,
        "first_behavior_target_max_cues": 3,
        "first_behavior_target_max_seconds_from_first_cue": 12.0,
        "evidence_excerpt_max_characters": 120,
    }:
        errors.append("public_outcome")
    proxy = contract.get("observable_label_proxy") or {}
    expected_labels = [
        "direct_rejection",
        "ask_clarification",
        "defer_commitment",
        "pause_and_reassess",
        "accept_support_and_continue",
    ]
    if [rule.get("label") for rule in proxy.get("ordered_rules") or []] != expected_labels:
        errors.append("proxy_order")
    if proxy.get("default_label") != "acknowledge_then_continue" or proxy.get("proxy_is_not_human_ground_truth") is not True:
        errors.append("proxy_boundary")
    metrics = contract.get("frozen_metrics") or {}
    if metrics != {
        "primary": "actual_label_probability_higher_is_better",
        "selected_label_hit": True,
        "multiclass_brier": "sum_over_six_labels_squared_probability_error_lower_is_better",
        "log_loss": "negative_natural_log_of_actual_label_probability_with_floor_1e-15_lower_is_better",
        "descriptive_text_only": "normalized_japanese_character_bigram_jaccard",
        "winner_rule": "higher_actual_label_probability_then_lower_brier_then_tie",
        "prediction_or_metric_change_after_future_access_allowed": False,
    }:
        errors.append("metrics")
    execution = contract.get("execution") or {}
    if execution.get("model_or_judge_call_count_required") != 0 or execution.get("training_or_product_write_count_required") != 0:
        errors.append("execution")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b66_future_outcome_access":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B66ContractError(";".join(errors))
    return {
        "valid": True,
        "future_outcome_access_count_at_freeze": freeze.get("future_outcome_access_count_at_freeze"),
        "outcome_score_count_at_freeze": freeze.get("outcome_score_count_at_freeze"),
    }


def extract_future_artifact(raw_caption: bytes, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    try:
        document = json.loads(raw_caption)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B66ExecutionError("future_projection", "caption_json", "caption JSON") from exc
    events = document.get("events") if isinstance(document, dict) else None
    if not isinstance(events, list):
        raise B66ExecutionError("future_projection", "caption_json", "caption events")
    source = contract["source"]
    start_limit = source["future_start_milliseconds"]
    end_limit = source["future_end_milliseconds"]
    cues: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        start = event.get("tStartMs")
        duration = event.get("dDurationMs")
        segments = event.get("segs")
        if not isinstance(start, (int, float)) or not isinstance(duration, (int, float)):
            continue
        end = start + duration
        if start < start_limit or end > end_limit or end < start or not isinstance(segments, list):
            continue
        raw_text = "".join(
            segment.get("utf8", "")
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("utf8", ""), str)
        )
        normalized = " ".join(raw_text.split())
        if normalized:
            cues.append(
                {
                    "start_seconds": round(float(start) / 1000.0, 3),
                    "end_seconds": round(float(end) / 1000.0, 3),
                    "text": normalized,
                }
            )
    cues.sort(key=lambda cue: (cue["start_seconds"], cue["end_seconds"]))
    if len(cues) < source["minimum_future_cue_count"]:
        raise B66ExecutionError("future_projection", "no_future_cues", "no future cues")
    return {
        "schema": contract["public_outcome"]["artifact_schema"],
        "version": "1.0.0",
        "source_id": source["source_id"],
        "future_seconds": [3181.0, 3241.0],
        "language_code": "ja",
        "track_type": "automatic",
        "format": "json3",
        "cues": cues,
    }


def _exclusive_bytes(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def publish_future_artifact(
    artifact: dict[str, Any], public_root: Path, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = contract or load_contract()
    if public_root.exists() and any(public_root.iterdir()):
        raise B66ExecutionError("publication", "preexisting_public", "public root nonempty")
    public_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(public_root, 0o700)
    artifact_bytes = canonical_json(artifact).encode("utf-8")
    artifact_sha = sha256_bytes(artifact_bytes)
    artifact_id = f"p3-b66-{artifact_sha[:16]}"
    cues = artifact["cues"]
    manifest = {
        "schema": contract["public_outcome"]["manifest_schema"],
        "version": "1.0.0",
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_sha,
        "artifact_bytes": len(artifact_bytes),
        "source_id": contract["source"]["source_id"],
        "future_seconds": [3181.0, 3241.0],
        "language_code": "ja",
        "track_type": "automatic",
        "format": "json3",
        "cue_count": len(cues),
        "first_cue_start_seconds": cues[0]["start_seconds"],
        "last_cue_end_seconds": max(cue["end_seconds"] for cue in cues),
        "raw_full_caption_persisted": False,
        "context_window_cues_persisted": False,
        "prediction_result_hash": "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe",
    }
    manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    _exclusive_bytes(public_root / f"{artifact_id}.json", artifact_bytes)
    _exclusive_bytes(public_root / f"{artifact_id}.manifest.json", canonical_json(manifest).encode("utf-8"))
    os.chmod(public_root, 0o500)
    return manifest


def target_cues(artifact: dict[str, Any], contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    cues = artifact["cues"]
    first_start = float(cues[0]["start_seconds"])
    maximum = contract["public_outcome"]["first_behavior_target_max_cues"]
    horizon = contract["public_outcome"]["first_behavior_target_max_seconds_from_first_cue"]
    selected = [cue for cue in cues if float(cue["start_seconds"]) <= first_start + horizon][:maximum]
    if not selected:
        raise B66ExecutionError("outcome_target", "empty_target", "empty target")
    return selected


def normalize_proxy_text(text: str) -> str:
    return "".join(text.split()).casefold()


def classify_observable_label(text: str, contract: dict[str, Any] | None = None) -> tuple[str, str | None]:
    contract = contract or load_contract()
    normalized = normalize_proxy_text(text)
    for rule in contract["observable_label_proxy"]["ordered_rules"]:
        for marker in rule["markers"]:
            if normalize_proxy_text(marker) in normalized:
                return rule["label"], marker
    return contract["observable_label_proxy"]["default_label"], None


def character_bigram_jaccard(prediction: str, outcome: str) -> float:
    def grams(text: str) -> set[str]:
        normalized = normalize_proxy_text(text)
        if len(normalized) < 2:
            return {normalized} if normalized else set()
        return {normalized[index : index + 2] for index in range(len(normalized) - 1)}

    left = grams(prediction)
    right = grams(outcome)
    union = left | right
    return 0.0 if not union else len(left & right) / len(union)


def score_prediction(prediction: dict[str, Any], actual_label: str, outcome_text: str) -> dict[str, Any]:
    probabilities = prediction["probabilities"]
    actual_probability = float(probabilities[actual_label])
    brier = sum(
        (float(probability) - (1.0 if label == actual_label else 0.0)) ** 2
        for label, probability in probabilities.items()
    )
    return {
        "condition": prediction["condition"],
        "selected_behavior": prediction["selected_behavior"],
        "selected_label_hit": prediction["selected_behavior"] == actual_label,
        "actual_label_probability": round(actual_probability, 12),
        "multiclass_brier": round(brier, 12),
        "log_loss": round(-math.log(max(actual_probability, 1e-15)), 12),
        "character_bigram_jaccard": round(
            character_bigram_jaccard(prediction["predicted_next_content"], outcome_text), 12
        ),
    }


def choose_proxy_winner(scores: list[dict[str, Any]]) -> str:
    by_condition = {score["condition"]: score for score in scores}
    baseline = by_condition["BASELINE_LITERAL"]
    system = by_condition["SYSTEM_PRAGMATIC_STATE"]
    difference = system["actual_label_probability"] - baseline["actual_label_probability"]
    if abs(difference) > 1e-12:
        return "SYSTEM_PRAGMATIC_STATE" if difference > 0 else "BASELINE_LITERAL"
    brier_difference = system["multiclass_brier"] - baseline["multiclass_brier"]
    if abs(brier_difference) > 1e-12:
        return "SYSTEM_PRAGMATIC_STATE" if brier_difference < 0 else "BASELINE_LITERAL"
    return "TIE"


def _fresh_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["execution"]["state_root"]
    public_root = ROOT / contract["public_outcome"]["root"]
    if state_root.exists():
        raise B66ExecutionError("preflight", "preflight", "B66 already consumed")
    if public_root.exists() and any(public_root.iterdir()):
        raise B66ExecutionError("preflight", "preflight", "B66 public root nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b66_future_outcome_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_complete_score",
        "source_id": contract["source"]["source_id"],
        "future_seconds": [3181.0, 3241.0],
        "prediction_result_hash": "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe",
        "model_or_judge_call_authorized": False,
        "prediction_mutation_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b66_future_outcome_scored_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "future_seconds": [3181.0, 3241.0],
        "prediction_result_hash": "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe",
        "native_downloader_process_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "private_full_caption_access_count": 0,
        "private_full_caption_filename_persisted": False,
        "private_full_caption_hash_persisted": False,
        "raw_full_caption_persisted": False,
        "context_window_cues_persisted": False,
        "prediction_mutation_count": 0,
        "model_or_judge_call_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "future_outcome_access_count": 0,
        "outcome_score_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b66_future_outcome_scored_result_v1":
        errors.append("schema")
    if result.get("status") not in {"outcome_scored", "outcome_unlock_failed"}:
        errors.append("status")
    if result.get("future_seconds") != [3181.0, 3241.0]:
        errors.append("future_boundary")
    if result.get("prediction_result_hash") != "379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe":
        errors.append("prediction_identity")
    for field in (
        "private_full_caption_filename_persisted",
        "private_full_caption_hash_persisted",
        "raw_full_caption_persisted",
        "context_window_cues_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    for field in (
        "prediction_mutation_count",
        "model_or_judge_call_count",
        "training_write_count",
        "formal_m56_write_count",
        "production_memory_write_count",
        "retry_count",
        "fallback_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("native_downloader_process_invocation_count") not in {0, 1}:
        errors.append("process_count")
    if result.get("provider_http_request_count") != "unavailable":
        errors.append("provider_http_claim")
    forbidden = {"raw_caption", "full_caption", "context_cues", "prediction_text_mutated"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "outcome_scored":
        if result.get("native_downloader_process_invocation_count") != 1 or result.get("downloader_returncode") != 0:
            errors.append("downloader")
        if result.get("private_full_caption_access_count") != 1:
            errors.append("private_access")
        if result.get("private_full_caption_deleted_before_public_scoring") is not True or result.get("private_runtime_deleted_before_public_scoring") is not True:
            errors.append("private_delete")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("public_artifact")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("reader")
        if result.get("future_outcome_access_count") != 1 or result.get("outcome_score_count") != 2:
            errors.append("score_count")
        labels = b65.load_contract()["target"]["candidate_behavior_labels"]
        if result.get("actual_proxy_label") not in labels:
            errors.append("actual_label")
        scores = result.get("scores")
        if not isinstance(scores, list) or [row.get("condition") for row in scores] != ["BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"]:
            errors.append("scores")
        if result.get("proxy_winner") not in {"BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE", "TIE"}:
            errors.append("winner")
        excerpt = result.get("evidence_excerpt")
        if not isinstance(excerpt, str) or not excerpt or len(excerpt) > 120:
            errors.append("excerpt")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure")
        if result.get("outcome_score_count") != 0:
            errors.append("failure_score")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_future_unlock_and_score() -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B66ContractError("invalid B66 contract: " + ";".join(report["errors"]))
    contract = load_contract()
    prediction = load_json(ROOT / contract["bindings"]["b65_saved_prediction"]["path"])
    state_root, public_root = _fresh_roots(contract)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    result = _base_result(contract)
    projected = None
    private_runtime_path = None
    raw_caption = None
    started = time.perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        if yt_dlp is None:
            raise B66ExecutionError("tool_preflight", "tool_preflight", "yt-dlp unavailable")
        b61_contract = b61.load_contract()
        version = b55_v2._tool_version(yt_dlp, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
        if version != b61_contract["native_downloader"]["required_version"]:
            raise B66ExecutionError("tool_preflight", "tool_preflight", "yt-dlp version drift")
        result["yt_dlp_version"] = version
        with TemporaryDirectory(prefix="uruha-p3-b66-private-") as temporary:
            private_root = Path(temporary)
            private_runtime_path = private_root
            os.chmod(private_root, 0o700)
            result["native_downloader_process_invocation_count"] = 1
            download_started = time.perf_counter()
            try:
                completed = subprocess.run(
                    b61.build_native_downloader_command(private_root, b61_contract),
                    check=False,
                    capture_output=True,
                    timeout=b61_contract["native_downloader"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["downloader_elapsed_seconds"] = round(time.perf_counter() - download_started, 6)
                result["downloader_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["downloader_stderr_bytes_discarded"] = len(exc.stderr or b"")
                raise B66ExecutionError("native_downloader", "timeout", "downloader timeout") from None
            result["downloader_elapsed_seconds"] = round(time.perf_counter() - download_started, 6)
            result["downloader_returncode"] = completed.returncode
            stdout = completed.stdout or b""
            stderr = completed.stderr or b""
            result["downloader_stdout_bytes_discarded"] = len(stdout)
            result["downloader_stderr_bytes_discarded"] = len(stderr)
            if completed.returncode != 0:
                category = b56.classify_private_stderr(stderr)
                stdout = stderr = b""
                completed = None
                raise B66ExecutionError("native_downloader", category, "downloader exit nonzero")
            stdout = stderr = b""
            completed = None
            caption_path, raw_caption = b61.read_single_private_caption(private_root, b61_contract)
            result["private_full_caption_access_count"] = 1
            result["private_full_caption_bytes_discarded_after_projection"] = len(raw_caption)
            projected = extract_future_artifact(raw_caption, contract)
            caption_path.unlink()
            result["private_full_caption_deleted_before_public_scoring"] = True
            raw_caption = None
        result["private_runtime_deleted_before_public_scoring"] = not private_runtime_path.exists()
        manifest = publish_future_artifact(projected, public_root, contract)
        projected = None
        result["public_artifact_count"] = 1
        result["public_manifest_count"] = 1
        result["public_artifact_id"] = manifest["artifact_id"]
        result["public_artifact_sha256"] = manifest["artifact_sha256"]
        result["public_manifest_hash"] = manifest["manifest_hash"]
        result["public_future_cue_count"] = manifest["cue_count"]
        result["public_first_cue_start_seconds"] = manifest["first_cue_start_seconds"]
        result["public_last_cue_end_seconds"] = manifest["last_cue_end_seconds"]
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            future_reader.PUBLIC_ROOT_ENV: str(public_root),
        }
        child = subprocess.run(
            [sys.executable, str(ROOT / "p3_b66_future_outcome_reader.py"), "--read", manifest["artifact_id"]],
            cwd=str(ROOT),
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result["fresh_public_reader_count"] = 1
        result["fresh_public_reader_exit_code"] = child.returncode
        if child.returncode != 0:
            raise B66ExecutionError("fresh_public_reader", "public_reader", "reader rejected artifact")
        public_payload = json.loads(child.stdout)
        if public_payload["manifest"]["artifact_sha256"] != manifest["artifact_sha256"]:
            raise B66ExecutionError("fresh_public_reader", "public_reader", "artifact hash mismatch")
        result["future_outcome_access_count"] = 1
        target = target_cues(public_payload["artifact"], contract)
        outcome_text = " ".join(cue["text"] for cue in target)
        actual_label, matched_marker = classify_observable_label(outcome_text, contract)
        scores = [score_prediction(row, actual_label, outcome_text) for row in prediction["predictions"]]
        result["outcome_score_count"] = 2
        result["target_cue_count"] = len(target)
        result["target_first_cue_start_seconds"] = target[0]["start_seconds"]
        result["target_last_cue_end_seconds"] = max(cue["end_seconds"] for cue in target)
        result["actual_proxy_label"] = actual_label
        result["matched_proxy_marker"] = matched_marker
        result["evidence_excerpt"] = outcome_text[: contract["public_outcome"]["evidence_excerpt_max_characters"]]
        result["scores"] = scores
        result["proxy_winner"] = choose_proxy_winner(scores)
        result["proxy_is_not_human_ground_truth"] = True
        result["status"] = "outcome_scored"
    except Exception as exc:
        raw_caption = None
        projected = None
        result["status"] = "outcome_unlock_failed"
        if isinstance(exc, B66ExecutionError):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
        else:
            result["failure_stage"] = "unexpected"
            result["failure_category"] = "unknown"
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B66ContractError("invalid B66 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B66 unlock and score the frozen future outcome")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B66 supports only the frozen one-shot outcome unlock")
    result = execute_future_unlock_and_score()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "outcome_scored":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
