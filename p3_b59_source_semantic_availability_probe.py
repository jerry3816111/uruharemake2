"""B59 metadata-only public caption-track availability probe."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from typing import Any

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b59_source_semantic_availability_probe_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b59_source_semantic_availability_probe_implementation_freeze_2026-09-20.json"
)


class B59ContractError(ValueError):
    pass


class B59ExecutionError(RuntimeError):
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


def _source_locator(contract: dict[str, Any]) -> str:
    source = contract["source"]
    return source["locator_template"].replace("<video_id>", source["video_id"])


def build_probe_command(contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B59ContractError("yt-dlp unavailable")
    return [
        executable,
        "--ignore-config",
        "--quiet",
        "--no-warnings",
        "--no-playlist",
        "--skip-download",
        "--no-write-info-json",
        "--no-write-thumbnail",
        "--no-write-subs",
        "--no-write-auto-subs",
        "--no-write-comments",
        "--no-cache-dir",
        "--retries",
        "0",
        "--fragment-retries",
        "0",
        "--extractor-retries",
        "0",
        "--socket-timeout",
        "30",
        "--print",
        "%(subtitles)j",
        "--print",
        "%(automatic_captions)j",
        _source_locator(contract),
    ]


def _parse_track_map(line: str) -> dict[str, list[dict[str, Any]]]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise B59ExecutionError(
            "probe_output", "probe_output_contract", "track metadata JSON"
        ) from exc
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise B59ExecutionError(
            "probe_output", "probe_output_contract", "track metadata object"
        )
    for language, tracks in value.items():
        if not isinstance(language, str) or not isinstance(tracks, list):
            raise B59ExecutionError(
                "probe_output", "probe_output_contract", "track metadata shape"
            )
        if any(not isinstance(track, dict) for track in tracks):
            raise B59ExecutionError(
                "probe_output", "probe_output_contract", "track entry shape"
            )
    return value


def _choose_format(
    tracks: list[dict[str, Any]], preferred_formats: list[str]
) -> str | None:
    available = {
        track.get("ext")
        for track in tracks
        if isinstance(track.get("ext"), str)
    }
    return next((extension for extension in preferred_formats if extension in available), None)


def parse_private_probe_output(
    stdout_bytes: bytes, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = contract or load_contract()
    if not isinstance(stdout_bytes, bytes):
        raise TypeError("stdout_bytes must be bytes")
    try:
        text = stdout_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise B59ExecutionError(
            "probe_output", "probe_output_contract", "probe output encoding"
        ) from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 2:
        raise B59ExecutionError(
            "probe_output", "probe_output_contract", "probe output line count"
        )
    manual = _parse_track_map(lines[0])
    automatic = _parse_track_map(lines[1])
    target = contract["probe"]["target_language_code"]
    preferred = contract["probe"]["preferred_formats_in_order"]
    manual_tracks = manual.get(target) or []
    automatic_tracks = automatic.get(target) or []
    manual_format = _choose_format(manual_tracks, preferred)
    automatic_format = _choose_format(automatic_tracks, preferred)
    selected_type = None
    selected_format = None
    if manual_format is not None:
        selected_type = "manual"
        selected_format = manual_format
    elif automatic_format is not None:
        selected_type = "automatic"
        selected_format = automatic_format
    projection = {
        "manual_language_code_count": len(manual),
        "automatic_language_code_count": len(automatic),
        "manual_japanese_available": bool(manual_tracks),
        "automatic_japanese_available": bool(automatic_tracks),
        "selected_track_type": selected_type,
        "selected_language_code": target if selected_type is not None else None,
        "selected_format": selected_format,
    }
    manual.clear()
    automatic.clear()
    return projection


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b59_source_semantic_availability_probe_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_under_standing_authorization_before_metadata_request":
        errors.append("status")
    authorization = contract.get("authorization") or {}
    if authorization.get("resolver_process_invocation_count_max") != 1:
        errors.append("resolver_count")
    if authorization.get("caption_content_download_count_max") != 0:
        errors.append("content_count")
    if authorization.get("retry_or_fallback_authorized") is not False:
        errors.append("retry_authorization")
    if authorization.get("paid_api_login_cookie_or_account_access_authorized") is not False:
        errors.append("account_authorization")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b58_review_required") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "direct_audio_branch_closed_after_two_prospective_corrections":
            errors.append("review_status")
        if review.get("direct_audio_branch", {}).get("same_path_retry_authorized") is not False:
            errors.append("review_retry_boundary")
        if review.get("next_stage", {}).get("id") != "P3-B59":
            errors.append("review_next_stage")
    source = contract.get("source") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_start_seconds") != 3000.0
        or source.get("context_end_seconds") != 3180.0
        or source.get("hidden_future_start_seconds") != 3181.0
        or source.get("hidden_future_end_seconds") != 3241.0
    ):
        errors.append("source_boundary")
    probe = contract.get("probe") or {}
    if probe.get("required_version") != "2026.02.04":
        errors.append("probe_version")
    if probe.get("print_fields_in_order") != ["subtitles", "automatic_captions"]:
        errors.append("probe_fields")
    if probe.get("target_language_code") != "ja":
        errors.append("target_language")
    if not probe.get("preferred_formats_in_order"):
        errors.append("formats")
    if any(
        probe.get(field) != 0
        for field in (
            "network_retry_count",
            "fragment_retry_count",
            "extractor_retry_count",
        )
    ):
        errors.append("probe_retries")
    for field in (
        "cookies_or_browser_session_allowed",
        "playlist_allowed",
        "file_download_allowed",
        "caption_content_download_allowed",
        "metadata_sidecar_allowed",
        "cache_allowed",
        "provider_http_request_count_observable",
    ):
        if probe.get(field) is not False:
            errors.append(f"probe_denial:{field}")
    boundary = contract.get("private_metadata_boundary") or {}
    for field in (
        "raw_metadata_persistence_allowed",
        "track_url_text_persistence_allowed",
        "track_url_hash_persistence_allowed",
        "track_url_excerpt_or_query_key_persistence_allowed",
        "resolver_stdout_text_persistence_allowed",
        "resolver_stderr_text_persistence_allowed",
    ):
        if boundary.get(field) is not False:
            errors.append(f"private_denial:{field}")
    expected_projection = {
        "manual_language_code_count",
        "automatic_language_code_count",
        "manual_japanese_available",
        "automatic_japanese_available",
        "selected_track_type",
        "selected_language_code",
        "selected_format",
    }
    if set(boundary.get("allowed_public_projection_fields") or []) != expected_projection:
        errors.append("projection_fields")
    decision = contract.get("decision") or {}
    if decision.get("manual_track_preferred_over_automatic") is not True:
        errors.append("manual_preference")
    if decision.get("automatic_next_execution_allowed") is not False:
        errors.append("automatic_execution")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b59_metadata_request":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B59ContractError(";".join(errors))
    return {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": freeze.get(
            "resolver_process_invocation_count_at_freeze"
        ),
        "caption_content_download_count_at_freeze": freeze.get(
            "caption_content_download_count_at_freeze"
        ),
        "hidden_future_content_access_count_at_freeze": freeze.get(
            "hidden_future_content_access_count_at_freeze"
        ),
    }


def _fresh_state_root(contract: dict[str, Any]) -> Path:
    state_root = ROOT / contract["runtime_state"]["state_root"]
    if state_root.exists():
        raise B59ExecutionError("preflight", "preflight", "B59 already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema": "uruha_p3_b59_semantic_availability_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "resolver_process_max": 1,
        "caption_content_download_max": 0,
        "hidden_future_content_access_authorized": False,
        "prediction_authorized": False,
    }
    material["intent_hash"] = sha256_bytes(canonical_json(material).encode("utf-8"))
    return material


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b59_source_semantic_availability_probe_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "resolver_process_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "resolver_stdout_bytes_discarded": 0,
        "resolver_stderr_bytes_discarded": 0,
        "raw_metadata_persisted": False,
        "track_url_text_persisted": False,
        "track_url_hash_persisted": False,
        "track_url_excerpt_or_query_key_persisted": False,
        "private_metadata_cleared_before_result": False,
        "caption_content_download_count": 0,
        "hidden_future_content_access_count": 0,
        "manual_playback_count": 0,
        "semantic_inspection_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "paid_api_or_account_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b59_source_semantic_availability_probe_result_v1":
        errors.append("schema")
    if result.get("status") not in {"availability_probe_passed", "availability_probe_failed"}:
        errors.append("status")
    if result.get("resolver_process_invocation_count") not in {0, 1}:
        errors.append("resolver_count")
    if result.get("provider_http_request_count") != "unavailable":
        errors.append("provider_http_claim")
    for field in (
        "raw_metadata_persisted",
        "track_url_text_persisted",
        "track_url_hash_persisted",
        "track_url_excerpt_or_query_key_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    for field in (
        "caption_content_download_count",
        "hidden_future_content_access_count",
        "manual_playback_count",
        "semantic_inspection_count",
        "prediction_execution_count",
        "model_call_count",
        "training_write_count",
        "formal_m56_write_count",
        "production_memory_write_count",
        "paid_api_or_account_access_count",
        "retry_count",
        "fallback_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    forbidden_keys = {
        "raw_metadata",
        "track_url",
        "track_urls",
        "track_url_sha256",
        "resolver_stdout_text",
        "resolver_stderr_text",
        "caption_text",
        "transcript",
    }
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden_keys)
    if result.get("status") == "availability_probe_passed":
        if result.get("resolver_process_invocation_count") != 1:
            errors.append("success_resolver")
        if result.get("resolver_returncode") != 0:
            errors.append("success_returncode")
        if result.get("private_metadata_cleared_before_result") is not True:
            errors.append("success_clear")
        projection = result.get("availability_projection")
        expected = set(load_contract()["private_metadata_boundary"]["allowed_public_projection_fields"])
        if not isinstance(projection, dict) or set(projection) != expected:
            errors.append("success_projection")
        else:
            selected_type = projection.get("selected_track_type")
            selected_language = projection.get("selected_language_code")
            selected_format = projection.get("selected_format")
            if selected_type not in {None, "manual", "automatic"}:
                errors.append("selected_type")
            if (selected_type is None) != (selected_language is None or selected_format is None):
                errors.append("selection_consistency")
            if selected_language not in {None, "ja"}:
                errors.append("selected_language")
        if result.get("next_stage") not in {
            "caption_acquisition_design",
            "local_artifact_or_replacement_source_required",
        }:
            errors.append("next_stage")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure_classification")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_availability_probe() -> dict[str, Any]:
    validate_implementation_freeze()
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B59ContractError("invalid B59 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    state_root = _fresh_state_root(contract)
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["intent_filename"], _intent(contract)
    )
    result = _base_result(contract)
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        if yt_dlp is None:
            raise B59ExecutionError("tool_preflight", "tool_preflight", "yt-dlp unavailable")
        b55_contract = b55_v2.load_contract()
        yt_dlp_version = b55_v2._tool_version(
            yt_dlp, b55_contract["transport"]["yt_dlp_version_command"]
        )
        if yt_dlp_version != contract["probe"]["required_version"]:
            raise B59ExecutionError("tool_preflight", "tool_preflight", "yt-dlp version drift")
        result["yt_dlp_version"] = yt_dlp_version
        result["resolver_process_invocation_count"] = 1
        probe_start = perf_counter()
        try:
            completed = subprocess.run(
                build_probe_command(contract),
                check=False,
                capture_output=True,
                timeout=contract["probe"]["timeout_seconds"],
            )
        except subprocess.TimeoutExpired as exc:
            result["resolver_elapsed_seconds"] = round(perf_counter() - probe_start, 6)
            result["resolver_stdout_bytes_discarded"] = len(exc.stdout or b"")
            result["resolver_stderr_bytes_discarded"] = len(exc.stderr or b"")
            raise B59ExecutionError("resolver", "timeout", "probe timeout") from None
        result["resolver_elapsed_seconds"] = round(perf_counter() - probe_start, 6)
        result["resolver_returncode"] = completed.returncode
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
        result["resolver_stdout_bytes_discarded"] = len(stdout)
        result["resolver_stderr_bytes_discarded"] = len(stderr)
        if completed.returncode != 0:
            category = b56.classify_private_stderr(stderr)
            stdout = stderr = b""
            completed = None
            raise B59ExecutionError("resolver", category, "probe exit nonzero")
        projection = parse_private_probe_output(stdout, contract)
        stdout = stderr = b""
        completed = None
        result["private_metadata_cleared_before_result"] = True
        result["availability_projection"] = projection
        result["next_stage"] = (
            "caption_acquisition_design"
            if projection["selected_track_type"] is not None
            else "local_artifact_or_replacement_source_required"
        )
        result["status"] = "availability_probe_passed"
    except Exception as exc:
        result["private_metadata_cleared_before_result"] = True
        result["status"] = "availability_probe_failed"
        if isinstance(exc, B59ExecutionError):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
        else:
            result["failure_stage"] = "unexpected"
            result["failure_category"] = "unknown"
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - start_time, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B59ContractError("invalid B59 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["result_filename"], result
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B59 source semantic availability probe")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B59 supports only the frozen one-shot metadata probe")
    result = execute_availability_probe()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "availability_probe_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
