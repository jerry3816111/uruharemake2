"""B58 one-shot transport with private allowlisted extractor request headers."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import p3_b54_public_context_reader as public_reader
import p3_b54_unidirectional_context_extraction as b54
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b58_private_allowlisted_header_transport_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b58_private_allowlisted_header_transport_implementation_freeze_2026-09-19.json"
)


class B58ContractError(ValueError):
    pass


class B58ExecutionError(RuntimeError):
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


def build_resolver_command(contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B58ContractError("yt-dlp unavailable")
    return [
        executable,
        "--ignore-config",
        "--quiet",
        "--no-warnings",
        "--no-playlist",
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
        "-f",
        contract["resolver"]["format_selector"],
        "--print",
        "%(url)s",
        "--print",
        "%(http_headers)j",
        _source_locator(contract),
    ]


def _validate_media_url(value: str, contract: dict[str, Any]) -> str:
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != contract["resolver"]["required_scheme"]:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver URL scheme"
        )
    if not hostname.endswith(contract["resolver"]["allowed_host_suffix"]):
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver URL host"
        )
    if parsed.username is not None or parsed.password is not None:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver URL userinfo"
        )
    return value


def _private_header_subset(
    raw_headers: Any, contract: dict[str, Any]
) -> dict[str, str]:
    boundary = contract["private_request_boundary"]
    if not isinstance(raw_headers, dict):
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver header object"
        )
    forbidden = {name.casefold() for name in boundary["forbidden_header_names"]}
    allowed = {
        name.casefold(): name for name in boundary["allowed_header_names"]
    }
    selected: dict[str, str] = {}
    seen: set[str] = set()
    for raw_name, raw_value in raw_headers.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise B58ExecutionError(
                "resolver_output", "resolver_output_contract", "resolver header types"
            )
        folded = raw_name.casefold()
        if folded in seen:
            raise B58ExecutionError(
                "resolver_output", "resolver_output_contract", "duplicate header"
            )
        seen.add(folded)
        if folded in forbidden:
            raise B58ExecutionError(
                "resolver_output", "sensitive_header_rejected", "sensitive header"
            )
        if folded == "range" or folded not in allowed:
            continue
        encoded = raw_value.encode("utf-8")
        if (
            not raw_value
            or len(encoded) > boundary["maximum_header_value_bytes"]
            or any(character in raw_value for character in ("\r", "\n", "\x00"))
        ):
            raise B58ExecutionError(
                "resolver_output", "resolver_output_contract", "unsafe header value"
            )
        selected[allowed[folded]] = raw_value
    missing = [
        name for name in boundary["required_header_names"] if name not in selected
    ]
    if missing:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "required header missing"
        )
    return selected


def parse_private_resolver_output(
    stdout_bytes: bytes, contract: dict[str, Any] | None = None
) -> tuple[str, dict[str, str]]:
    contract = contract or load_contract()
    if not isinstance(stdout_bytes, bytes):
        raise TypeError("stdout_bytes must be bytes")
    try:
        text = stdout_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver output encoding"
        ) from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 2:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver output line count"
        )
    media_url = _validate_media_url(lines[0], contract)
    try:
        raw_headers = json.loads(lines[1])
    except json.JSONDecodeError as exc:
        raise B58ExecutionError(
            "resolver_output", "resolver_output_contract", "resolver header JSON"
        ) from exc
    return media_url, _private_header_subset(raw_headers, contract)


def build_direct_ffmpeg_command(
    media_url: str,
    private_headers: dict[str, str],
    output_path: Path,
    contract: dict[str, Any] | None = None,
) -> list[str]:
    contract = contract or load_contract()
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise B58ContractError("ffmpeg unavailable")
    headers = _private_header_subset(private_headers, contract)
    command = [executable, "-hide_banner", "-loglevel", "error", "-nostdin"]
    if "User-Agent" in headers:
        command.extend(["-user_agent", headers.pop("User-Agent")])
    if "Referer" in headers:
        command.extend(["-referer", headers.pop("Referer")])
    ordered_general = [
        name
        for name in contract["private_request_boundary"]["allowed_header_names"]
        if name in headers
    ]
    if ordered_general:
        block = "".join(f"{name}: {headers[name]}\r\n" for name in ordered_general)
        command.extend(["-headers", block])
    ffmpeg = contract["direct_ffmpeg"]
    command.extend(
        [
            "-ss",
            f"{ffmpeg['input_seek_seconds']:.6f}",
            "-i",
            media_url,
            "-t",
            f"{ffmpeg['output_duration_seconds']:.6f}",
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-vn",
            "-ac",
            str(ffmpeg["channels"]),
            "-ar",
            str(ffmpeg["sample_rate_hz"]),
            "-c:a",
            ffmpeg["codec"],
            str(output_path),
        ]
    )
    return command


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b58_private_allowlisted_header_transport_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_after_standing_user_authorization_before_resolver_or_media_request":
        errors.append("status")
    authorization = contract.get("authorization") or {}
    if authorization.get("overrides_b57_next_execution_authorized_false") is not True:
        errors.append("review_override")
    if authorization.get("resolver_process_invocation_count_max") != 1:
        errors.append("resolver_count")
    if authorization.get("direct_ffmpeg_process_invocation_count_max") != 1:
        errors.append("ffmpeg_count")
    if authorization.get("retry_or_additional_correction_authorized") is not False:
        errors.append("retry_authorization")
    if authorization.get("paid_api_login_cookie_or_account_access_authorized") is not False:
        errors.append("account_authorization")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b57_review_required") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "review_required_after_resolver_success_and_direct_ffmpeg_transport_failure":
            errors.append("review_status")
        if review.get("result", {}).get("failure_category") != "tls_or_network":
            errors.append("review_category")
        if review.get("next_execution_authorized") is not False:
            errors.append("review_prior_boundary")
    source = contract.get("source") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_start_seconds") != 3000.0
        or source.get("context_end_seconds") != 3180.0
        or source.get("hidden_future_start_seconds") != 3181.0
        or source.get("hidden_future_end_seconds") != 3241.0
    ):
        errors.append("source_boundary")
    resolver = contract.get("resolver") or {}
    if resolver.get("required_version") != "2026.02.04":
        errors.append("resolver_version")
    if resolver.get("format_selector") != "bestaudio/best":
        errors.append("resolver_format")
    if resolver.get("print_fields_in_order") != ["url", "http_headers"]:
        errors.append("resolver_fields")
    if any(
        resolver.get(field) != 0
        for field in (
            "network_retry_count",
            "fragment_retry_count",
            "extractor_retry_count",
        )
    ):
        errors.append("resolver_retries")
    for field in (
        "cookies_or_browser_session_allowed",
        "playlist_allowed",
        "file_download_allowed",
        "metadata_sidecars_allowed",
        "subtitles_allowed",
        "comments_allowed",
        "cache_allowed",
        "provider_http_request_count_observable",
    ):
        if resolver.get(field) is not False:
            errors.append(f"resolver_denial:{field}")
    if resolver.get("required_url_count") != 1:
        errors.append("resolver_url_count")
    if resolver.get("required_scheme") != "https" or resolver.get("allowed_host_suffix") != ".googlevideo.com":
        errors.append("resolver_url_boundary")
    boundary = contract.get("private_request_boundary") or {}
    if boundary.get("allowed_header_names") != [
        "User-Agent",
        "Referer",
        "Origin",
        "Accept",
        "Accept-Language",
    ]:
        errors.append("header_allowlist")
    if boundary.get("required_header_names") != ["User-Agent"]:
        errors.append("header_required")
    if set(boundary.get("forbidden_header_names") or []) != {
        "Cookie",
        "Authorization",
        "Proxy-Authorization",
        "Set-Cookie",
    }:
        errors.append("header_forbidden")
    if boundary.get("unlisted_non_sensitive_headers_disposition") != "drop":
        errors.append("header_unlisted")
    if boundary.get("range_header_disposition") != "drop_so_ffmpeg_manages_byte_ranges":
        errors.append("header_range")
    for field in (
        "url_text_persistence_allowed",
        "url_hash_persistence_allowed",
        "url_excerpt_or_query_key_persistence_allowed",
        "hostname_persistence_allowed",
        "header_name_persistence_allowed",
        "header_value_persistence_allowed",
        "header_hash_persistence_allowed",
        "resolver_stdout_text_persistence_allowed",
        "resolver_stderr_text_persistence_allowed",
    ):
        if boundary.get(field) is not False:
            errors.append(f"private_denial:{field}")
    ffmpeg = contract.get("direct_ffmpeg") or {}
    if ffmpeg.get("input_seek_seconds") != 3000.0 or ffmpeg.get("output_duration_seconds") != 180.0:
        errors.append("ffmpeg_boundary")
    if ffmpeg.get("codec") != "pcm_s16le" or ffmpeg.get("sample_rate_hz") != 16000 or ffmpeg.get("channels") != 1:
        errors.append("ffmpeg_audio")
    if ffmpeg.get("provider_byte_range_exactness_claim_allowed") is not False:
        errors.append("byte_range_claim")
    success = contract.get("success_gate") or {}
    if success.get("duration_tolerance_seconds") != 0.05:
        errors.append("success_tolerance")
    if success.get("public_profile") != "reserved_source_context":
        errors.append("success_profile")
    if success.get("fresh_reader_count") != 1:
        errors.append("success_reader")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b58_resolver_or_media_request":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B58ContractError(";".join(errors))
    return {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": freeze.get(
            "resolver_process_invocation_count_at_freeze"
        ),
        "direct_ffmpeg_process_invocation_count_at_freeze": freeze.get(
            "direct_ffmpeg_process_invocation_count_at_freeze"
        ),
        "hidden_future_media_request_count_at_freeze": freeze.get(
            "hidden_future_media_request_count_at_freeze"
        ),
    }


def _fresh_runtime_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    runtime = contract["runtime_state"]
    state_root = ROOT / runtime["state_root"]
    public_root = ROOT / runtime["public_root"]
    if state_root.exists():
        raise B58ExecutionError("preflight", "preflight", "B58 already consumed")
    if public_root.exists() and any(public_root.iterdir()):
        raise B58ExecutionError("preflight", "preflight", "B58 public root nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema": "uruha_p3_b58_header_transport_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "resolver_process_max": 1,
        "direct_ffmpeg_process_max": 1,
        "private_header_material_persistence_allowed": False,
        "hidden_future_authorized": False,
        "prediction_authorized": False,
    }
    material["intent_hash"] = sha256_bytes(canonical_json(material).encode("utf-8"))
    return material


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b58_private_allowlisted_header_transport_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "requested_context_seconds": [3000.0, 3180.0],
        "resolver_process_invocation_count": 0,
        "direct_ffmpeg_process_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "provider_byte_range_exactness_provable": False,
        "resolver_stdout_bytes_discarded": 0,
        "resolver_stderr_bytes_discarded": 0,
        "resolver_url_count": 0,
        "resolver_url_host_category": None,
        "private_allowlisted_header_count": 0,
        "signed_url_text_persisted": False,
        "signed_url_hash_persisted": False,
        "signed_url_excerpt_or_query_key_persisted": False,
        "header_names_persisted": False,
        "header_values_persisted": False,
        "header_hashes_persisted": False,
        "private_request_material_cleared_before_public_reader": False,
        "private_runtime_deleted_before_public_reader": False,
        "direct_ffmpeg_stdout_bytes_discarded": 0,
        "direct_ffmpeg_stderr_bytes_discarded": 0,
        "public_artifact_count": 0,
        "public_manifest_count": 0,
        "hidden_future_media_request_count": 0,
        "manual_playback_count": 0,
        "semantic_inspection_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "paid_api_or_account_access_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b58_private_allowlisted_header_transport_result_v1":
        errors.append("schema")
    if result.get("status") not in {"header_transport_passed", "header_transport_failed"}:
        errors.append("status")
    if result.get("requested_context_seconds") != [3000.0, 3180.0]:
        errors.append("context")
    if result.get("resolver_process_invocation_count") not in {0, 1}:
        errors.append("resolver_count")
    if result.get("direct_ffmpeg_process_invocation_count") not in {0, 1}:
        errors.append("ffmpeg_count")
    if result.get("provider_http_request_count") != "unavailable":
        errors.append("provider_http_claim")
    if result.get("provider_byte_range_exactness_provable") is not False:
        errors.append("byte_range_claim")
    for field in (
        "signed_url_text_persisted",
        "signed_url_hash_persisted",
        "signed_url_excerpt_or_query_key_persisted",
        "header_names_persisted",
        "header_values_persisted",
        "header_hashes_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    for field in (
        "hidden_future_media_request_count",
        "manual_playback_count",
        "semantic_inspection_count",
        "prediction_execution_count",
        "model_call_count",
        "formal_m56_write_count",
        "production_memory_write_count",
        "retry_count",
        "fallback_count",
        "paid_api_or_account_access_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    forbidden_keys = {
        "signed_url",
        "signed_url_sha256",
        "signed_url_excerpt",
        "signed_url_query_keys",
        "private_headers",
        "header_names",
        "header_values",
        "header_hashes",
        "resolver_stdout_text",
        "resolver_stderr_text",
        "direct_ffmpeg_stderr_text",
    }
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden_keys)
    if result.get("status") == "header_transport_passed":
        if result.get("resolver_process_invocation_count") != 1:
            errors.append("success_resolver")
        if result.get("direct_ffmpeg_process_invocation_count") != 1:
            errors.append("success_ffmpeg")
        if result.get("resolver_returncode") != 0 or result.get("direct_ffmpeg_returncode") != 0:
            errors.append("success_returncodes")
        if result.get("resolver_url_count") != 1 or result.get("resolver_url_host_category") != "googlevideo_cdn":
            errors.append("success_url")
        if int(result.get("private_allowlisted_header_count", 0)) < 1:
            errors.append("success_headers")
        if result.get("private_request_material_cleared_before_public_reader") is not True:
            errors.append("success_private_clear")
        if result.get("private_runtime_deleted_before_public_reader") is not True:
            errors.append("success_private_delete")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("success_public")
        if abs(float(result.get("public_artifact_duration_seconds", 0)) - 180.0) > 0.05:
            errors.append("success_duration")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("success_reader")
        if result.get("fresh_reader_artifact_sha256") != result.get("public_artifact_sha256"):
            errors.append("success_hash")
        if result.get("manifest_forbidden_field_count") != 0:
            errors.append("success_manifest")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure_classification")
        if result.get("public_artifact_count") != 0 or result.get("public_manifest_count") != 0:
            errors.append("failure_public")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_header_transport() -> dict[str, Any]:
    validate_implementation_freeze()
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B58ContractError("invalid B58 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_runtime_roots(contract)
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["intent_filename"], _intent(contract)
    )
    result = _base_result(contract)
    public_receipt = None
    private_root_path = None
    media_url = None
    private_headers = None
    ffmpeg_command = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        ffmpeg = shutil.which("ffmpeg")
        if yt_dlp is None or ffmpeg is None:
            raise B58ExecutionError("tool_preflight", "tool_preflight", "required tool unavailable")
        b55_contract = b55_v2.load_contract()
        yt_dlp_version = b55_v2._tool_version(
            yt_dlp, b55_contract["transport"]["yt_dlp_version_command"]
        )
        ffmpeg_version = b55_v2._tool_version(
            ffmpeg, b55_contract["transport"]["ffmpeg_version_command"]
        )
        if yt_dlp_version != contract["resolver"]["required_version"]:
            raise B58ExecutionError("tool_preflight", "tool_preflight", "yt-dlp version drift")
        if not ffmpeg_version.startswith(contract["direct_ffmpeg"]["required_version_prefix"]):
            raise B58ExecutionError("tool_preflight", "tool_preflight", "ffmpeg version drift")
        result["yt_dlp_version"] = yt_dlp_version
        result["ffmpeg_version"] = ffmpeg_version
        with TemporaryDirectory(prefix="uruha-p3-b58-private-") as temporary:
            private_root = Path(temporary)
            private_root_path = private_root
            os.chmod(private_root, 0o700)
            result["resolver_process_invocation_count"] = 1
            resolver_start = perf_counter()
            try:
                resolver_completed = subprocess.run(
                    build_resolver_command(contract),
                    check=False,
                    capture_output=True,
                    timeout=contract["resolver"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["resolver_elapsed_seconds"] = round(perf_counter() - resolver_start, 6)
                result["resolver_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["resolver_stderr_bytes_discarded"] = len(exc.stderr or b"")
                raise B58ExecutionError("resolver", "timeout", "resolver timeout") from None
            result["resolver_elapsed_seconds"] = round(perf_counter() - resolver_start, 6)
            result["resolver_returncode"] = resolver_completed.returncode
            resolver_stdout = resolver_completed.stdout or b""
            resolver_stderr = resolver_completed.stderr or b""
            result["resolver_stdout_bytes_discarded"] = len(resolver_stdout)
            result["resolver_stderr_bytes_discarded"] = len(resolver_stderr)
            if resolver_completed.returncode != 0:
                category = b56.classify_private_stderr(resolver_stderr)
                resolver_stdout = resolver_stderr = b""
                resolver_completed = None
                raise B58ExecutionError("resolver", category, "resolver exit nonzero")
            media_url, private_headers = parse_private_resolver_output(
                resolver_stdout, contract
            )
            result["resolver_url_count"] = 1
            result["resolver_url_host_category"] = contract["private_request_boundary"][
                "receipt_host_category"
            ]
            result["private_allowlisted_header_count"] = len(private_headers)
            resolver_stdout = resolver_stderr = b""
            resolver_completed = None
            output_path = private_root / "p3-b58-observable-context.wav"
            ffmpeg_command = build_direct_ffmpeg_command(
                media_url, private_headers, output_path, contract
            )
            result["direct_ffmpeg_process_invocation_count"] = 1
            ffmpeg_start = perf_counter()
            try:
                ffmpeg_completed = subprocess.run(
                    ffmpeg_command,
                    check=False,
                    capture_output=True,
                    timeout=contract["direct_ffmpeg"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["direct_ffmpeg_elapsed_seconds"] = round(
                    perf_counter() - ffmpeg_start, 6
                )
                result["direct_ffmpeg_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["direct_ffmpeg_stderr_bytes_discarded"] = len(exc.stderr or b"")
                media_url = None
                private_headers = None
                ffmpeg_command = None
                raise B58ExecutionError("direct_ffmpeg", "timeout", "ffmpeg timeout") from None
            result["direct_ffmpeg_elapsed_seconds"] = round(perf_counter() - ffmpeg_start, 6)
            result["direct_ffmpeg_returncode"] = ffmpeg_completed.returncode
            ffmpeg_stdout = ffmpeg_completed.stdout or b""
            ffmpeg_stderr = ffmpeg_completed.stderr or b""
            result["direct_ffmpeg_stdout_bytes_discarded"] = len(ffmpeg_stdout)
            result["direct_ffmpeg_stderr_bytes_discarded"] = len(ffmpeg_stderr)
            ffmpeg_returncode = ffmpeg_completed.returncode
            ffmpeg_category = b56.classify_private_stderr(ffmpeg_stderr)
            ffmpeg_stdout = ffmpeg_stderr = b""
            ffmpeg_completed = None
            ffmpeg_command = None
            media_url = None
            private_headers = None
            result["private_request_material_cleared_before_public_reader"] = True
            if ffmpeg_returncode != 0:
                raise B58ExecutionError(
                    "direct_ffmpeg", ffmpeg_category, "direct ffmpeg exit nonzero"
                )
            probe = public_reader._ffprobe_audio(output_path)
            result["private_artifact_bytes"] = output_path.stat().st_size
            result["private_artifact_duration_seconds"] = round(
                probe["duration_seconds"], 6
            )
            expected = contract["direct_ffmpeg"]["output_duration_seconds"]
            tolerance = contract["success_gate"]["duration_tolerance_seconds"]
            if abs(probe["duration_seconds"] - expected) > tolerance:
                raise B58ExecutionError(
                    "local_artifact_gate",
                    "duration_gate",
                    "private duration outside tolerance",
                )
            profile = b54.load_contract()["profiles"]["reserved_source_context"]
            public_receipt = b54._publish_artifact(output_path, public_root, profile)
            result["public_artifact_id"] = public_receipt["artifact_id"]
            result["public_artifact_sha256"] = public_receipt["artifact_sha256"]
            result["public_manifest_hash"] = public_receipt["manifest_hash"]
            result["public_artifact_duration_seconds"] = public_receipt[
                "observed_duration_seconds"
            ]
            result["public_artifact_count"] = 1
            result["public_manifest_count"] = 1
            output_path.unlink()
        result["private_runtime_deleted_before_public_reader"] = not private_root_path.exists()
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            public_reader.PUBLIC_ROOT_ENV: str(public_root),
        }
        child = subprocess.run(
            [
                sys.executable,
                str(ROOT / "p3_b54_public_context_reader.py"),
                "--inspect",
                public_receipt["artifact_id"],
            ],
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
            raise B58ExecutionError(
                "fresh_public_reader", "public_reader", "reader rejected artifact"
            )
        manifest = json.loads(child.stdout)["manifest"]
        result["fresh_reader_artifact_sha256"] = manifest["artifact_sha256"]
        result["manifest_forbidden_field_count"] = len(
            public_reader._forbidden_field_paths(manifest)
        )
        if result["manifest_forbidden_field_count"] != 0:
            raise B58ExecutionError(
                "fresh_public_reader", "forbidden_manifest", "forbidden field"
            )
        result["status"] = "header_transport_passed"
    except Exception as exc:
        media_url = None
        private_headers = None
        ffmpeg_command = None
        result["private_request_material_cleared_before_public_reader"] = True
        if private_root_path is not None:
            result["private_runtime_deleted_before_public_reader"] = (
                not private_root_path.exists()
            )
        else:
            result["private_runtime_deleted_before_public_reader"] = True
        if public_receipt is not None:
            (public_root / f"{public_receipt['artifact_id']}.json").unlink(missing_ok=True)
            (public_root / f"{public_receipt['artifact_id']}.wav").unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "header_transport_failed"
        if isinstance(exc, B58ExecutionError):
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
        raise B58ContractError("invalid B58 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["result_filename"], result
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B58 private allowlisted-header transport")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B58 supports only the frozen one-shot execution")
    result = execute_header_transport()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "header_transport_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
