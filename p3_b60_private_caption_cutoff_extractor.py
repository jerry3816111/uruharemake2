"""B60 private full-caption acquisition with pre-cutoff-only public projection."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from time import perf_counter
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b60_private_caption_cutoff_extractor_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b60_private_caption_cutoff_extractor_implementation_freeze_2026-09-20.json"
)
PUBLIC_ROOT_ENV = "URUHA_P3_B60_PUBLIC_ROOT"


class B60ContractError(ValueError):
    pass


class B60ExecutionError(RuntimeError):
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
        raise B60ContractError("yt-dlp unavailable")
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
        "%(automatic_captions)j",
        "--print",
        "%(http_headers)j",
        _source_locator(contract),
    ]


def _private_headers(raw_headers: Any, contract: dict[str, Any]) -> dict[str, str]:
    if not isinstance(raw_headers, dict):
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "header object")
    allowed = {
        name.casefold(): name
        for name in contract["caption_get"]["allowed_request_header_names"]
    }
    forbidden = {
        name.casefold()
        for name in contract["caption_get"]["forbidden_request_header_names"]
    }
    selected: dict[str, str] = {}
    for name, value in raw_headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise B60ExecutionError("resolver_output", "resolver_output_contract", "header type")
        folded = name.casefold()
        if folded in forbidden:
            raise B60ExecutionError("resolver_output", "sensitive_header_rejected", "sensitive header")
        if folded not in allowed:
            continue
        if not value or len(value.encode("utf-8")) > 2048 or any(c in value for c in ("\r", "\n", "\x00")):
            raise B60ExecutionError("resolver_output", "resolver_output_contract", "header value")
        selected[allowed[folded]] = value
    if "User-Agent" not in selected:
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "User-Agent required")
    return selected


def parse_private_resolver_output(
    stdout_bytes: bytes, contract: dict[str, Any] | None = None
) -> tuple[str, dict[str, str]]:
    contract = contract or load_contract()
    try:
        text = stdout_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "encoding") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 2:
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "line count")
    try:
        captions = json.loads(lines[0])
        raw_headers = json.loads(lines[1])
    except json.JSONDecodeError as exc:
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "JSON") from exc
    source = contract["source"]
    if not isinstance(captions, dict) or not isinstance(captions.get(source["selected_language_code"]), list):
        raise B60ExecutionError("resolver_output", "selected_track_missing", "language track")
    matching = [
        item
        for item in captions[source["selected_language_code"]]
        if isinstance(item, dict) and item.get("ext") == source["selected_format"]
    ]
    if len(matching) != 1 or not isinstance(matching[0].get("url"), str):
        raise B60ExecutionError("resolver_output", "selected_track_missing", "format track")
    track_url = matching[0]["url"]
    parsed = urlsplit(track_url)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not (
        hostname == "youtube.com" or hostname.endswith(".youtube.com")
    ):
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "track URL")
    if parsed.username is not None or parsed.password is not None:
        raise B60ExecutionError("resolver_output", "resolver_output_contract", "track URL userinfo")
    headers = _private_headers(raw_headers, contract)
    captions.clear()
    return track_url, headers


def retrieve_private_caption(
    track_url: str,
    headers: dict[str, str],
    contract: dict[str, Any] | None = None,
    *,
    opener: Callable[..., Any] = urlopen,
) -> bytes:
    contract = contract or load_contract()
    request = Request(track_url, headers=headers, method="GET")
    limit = contract["caption_get"]["maximum_response_bytes"]
    try:
        with opener(request, timeout=contract["caption_get"]["timeout_seconds"]) as response:
            payload = response.read(limit + 1)
    except Exception as exc:
        raise B60ExecutionError("caption_get", "tls_or_network", "caption GET failed") from exc
    if not payload:
        raise B60ExecutionError("caption_get", "empty_response", "caption response empty")
    if len(payload) > limit:
        raise B60ExecutionError("caption_get", "response_too_large", "caption response too large")
    return payload


def extract_context_artifact(
    raw_caption: bytes, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = contract or load_contract()
    try:
        document = json.loads(raw_caption)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B60ExecutionError("cutoff_extraction", "caption_json", "caption JSON") from exc
    events = document.get("events") if isinstance(document, dict) else None
    if not isinstance(events, list):
        raise B60ExecutionError("cutoff_extraction", "caption_json", "caption events")
    cutoff = contract["cutoff_extraction"]
    start_limit = cutoff["context_start_milliseconds"]
    end_limit = cutoff["context_end_milliseconds"]
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
        if start < start_limit or end > end_limit or end < start:
            continue
        if not isinstance(segments, list):
            continue
        raw_text = "".join(
            segment.get("utf8", "")
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("utf8", ""), str)
        )
        normalized = " ".join(raw_text.split())
        if not normalized:
            continue
        cues.append(
            {
                "start_seconds": round(float(start) / 1000.0, 3),
                "end_seconds": round(float(end) / 1000.0, 3),
                "text": normalized,
            }
        )
    cues.sort(key=lambda cue: (cue["start_seconds"], cue["end_seconds"]))
    if len(cues) < cutoff["minimum_cue_count"]:
        raise B60ExecutionError("cutoff_extraction", "no_context_cues", "no context cues")
    return {
        "schema": contract["public_artifact"]["artifact_schema"],
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
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


def publish_context_artifact(
    artifact: dict[str, Any], public_root: Path, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = contract or load_contract()
    if public_root.exists() and any(public_root.iterdir()):
        raise B60ExecutionError("publication", "preexisting_public", "public root nonempty")
    public_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(public_root, 0o700)
    artifact_bytes = canonical_json(artifact).encode("utf-8")
    artifact_sha = sha256_bytes(artifact_bytes)
    artifact_id = f"p3-b60-{artifact_sha[:16]}"
    artifact_path = public_root / f"{artifact_id}.json"
    manifest_path = public_root / f"{artifact_id}.manifest.json"
    cues = artifact["cues"]
    manifest = {
        "schema": contract["public_artifact"]["manifest_schema"],
        "version": "1.0.0",
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_sha,
        "artifact_bytes": len(artifact_bytes),
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "language_code": "ja",
        "track_type": "automatic",
        "format": "json3",
        "cue_count": len(cues),
        "first_cue_start_seconds": cues[0]["start_seconds"],
        "last_cue_end_seconds": max(cue["end_seconds"] for cue in cues),
        "prediction_side_future_access_count": 0,
        "raw_caption_persisted": False,
        "track_url_persisted": False,
    }
    manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    _exclusive_bytes(artifact_path, artifact_bytes)
    _exclusive_bytes(manifest_path, canonical_json(manifest).encode("utf-8"))
    os.chmod(public_root, 0o500)
    return manifest


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b60_private_caption_cutoff_extractor_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_under_standing_authorization_before_caption_content_request":
        errors.append("status")
    authorization = contract.get("authorization") or {}
    if authorization.get("resolver_process_invocation_count_max") != 1:
        errors.append("resolver_count")
    if authorization.get("caption_get_invocation_count_max") != 1:
        errors.append("caption_get_count")
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
    release_binding = (contract.get("bindings") or {}).get("b59_release") or {}
    if release_binding:
        release = load_json(Path(root) / release_binding["path"])
        if release.get("status") != "released_metadata_only_caption_path_available":
            errors.append("release_status")
        result = release.get("result") or {}
        if [result.get("selected_track_type"), result.get("selected_language_code"), result.get("selected_format")] != ["automatic", "ja", "json3"]:
            errors.append("release_track")
    source = contract.get("source") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_start_seconds") != 3000.0
        or source.get("context_end_seconds") != 3180.0
        or source.get("hidden_future_start_seconds") != 3181.0
        or source.get("hidden_future_end_seconds") != 3241.0
        or [source.get("selected_track_type"), source.get("selected_language_code"), source.get("selected_format")] != ["automatic", "ja", "json3"]
    ):
        errors.append("source_boundary")
    resolver = contract.get("resolver") or {}
    if resolver.get("required_version") != "2026.02.04":
        errors.append("resolver_version")
    if resolver.get("print_fields_in_order") != ["automatic_captions", "http_headers"]:
        errors.append("resolver_fields")
    if any(resolver.get(field) != 0 for field in ("network_retry_count", "fragment_retry_count", "extractor_retry_count")):
        errors.append("resolver_retries")
    for field in (
        "cookies_or_browser_session_allowed",
        "playlist_allowed",
        "file_download_allowed",
        "caption_content_download_via_resolver_allowed",
        "metadata_sidecar_allowed",
        "cache_allowed",
        "provider_http_request_count_observable",
    ):
        if resolver.get(field) is not False:
            errors.append(f"resolver_denial:{field}")
    caption_get = contract.get("caption_get") or {}
    if caption_get.get("maximum_response_bytes") != 10485760:
        errors.append("response_limit")
    if set(caption_get.get("allowed_request_header_names") or []) != {"User-Agent", "Accept", "Accept-Language"}:
        errors.append("header_allowlist")
    if set(caption_get.get("forbidden_request_header_names") or []) != {"Cookie", "Authorization", "Proxy-Authorization", "Set-Cookie"}:
        errors.append("header_forbidden")
    cutoff = contract.get("cutoff_extraction") or {}
    if cutoff.get("context_start_milliseconds") != 3000000 or cutoff.get("context_end_milliseconds") != 3180000:
        errors.append("cutoff")
    if cutoff.get("include_rule") != "cue_start_gte_context_start_and_cue_end_lte_context_end":
        errors.append("include_rule")
    if cutoff.get("minimum_cue_count") != 1:
        errors.append("minimum_cues")
    if cutoff.get("post_cutoff_cue_persistence_allowed") is not False or cutoff.get("overlapping_cutoff_cue_persistence_allowed") is not False:
        errors.append("cutoff_persistence")
    separation = contract.get("capability_separation") or {}
    if separation.get("private_acquisition_may_temporarily_observe_full_caption") is not True:
        errors.append("private_raw_access")
    for field in (
        "private_raw_caption_persistence_allowed",
        "track_url_text_or_hash_persistence_allowed",
        "resolver_raw_output_persistence_allowed",
        "caption_response_raw_persistence_allowed",
        "prediction_side_import_of_acquisition_module_allowed",
    ):
        if separation.get(field) is not False:
            errors.append(f"separation:{field}")
    if separation.get("prediction_side_future_access_required") != 0:
        errors.append("prediction_future")
    if separation.get("private_material_cleared_before_fresh_public_reader") is not True:
        errors.append("private_clear")
    public = contract.get("public_artifact") or {}
    if public.get("fresh_reader_count") != 1 or public.get("fresh_reader_returns_caption_text") is not False:
        errors.append("reader_boundary")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b60_caption_content_request":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B60ContractError(";".join(errors))
    return {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": freeze.get("resolver_process_invocation_count_at_freeze"),
        "caption_get_invocation_count_at_freeze": freeze.get("caption_get_invocation_count_at_freeze"),
        "prediction_side_future_access_count_at_freeze": freeze.get("prediction_side_future_access_count_at_freeze"),
    }


def _fresh_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["runtime_state"]["state_root"]
    public_root = ROOT / contract["public_artifact"]["root"]
    if state_root.exists():
        raise B60ExecutionError("preflight", "preflight", "B60 already consumed")
    if public_root.exists() and any(public_root.iterdir()):
        raise B60ExecutionError("preflight", "preflight", "B60 public root nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b60_caption_cutoff_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "resolver_process_max": 1,
        "caption_get_max": 1,
        "prediction_side_future_access_authorized": False,
        "prediction_authorized": False,
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b60_private_caption_cutoff_extractor_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "resolver_process_invocation_count": 0,
        "caption_get_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "resolver_stdout_bytes_discarded": 0,
        "resolver_stderr_bytes_discarded": 0,
        "caption_response_bytes_discarded_after_projection": 0,
        "private_acquisition_full_caption_access_count": 0,
        "private_acquisition_may_include_post_cutoff_content": False,
        "prediction_side_future_access_count": 0,
        "track_url_persisted": False,
        "track_url_hash_persisted": False,
        "raw_resolver_output_persisted": False,
        "raw_caption_persisted": False,
        "post_cutoff_caption_persisted": False,
        "private_material_cleared_before_fresh_public_reader": False,
        "public_artifact_count": 0,
        "public_manifest_count": 0,
        "human_caption_display_count": 0,
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
    if result.get("schema") != "uruha_p3_b60_private_caption_cutoff_extractor_result_v1":
        errors.append("schema")
    if result.get("status") not in {"caption_context_published", "caption_context_failed"}:
        errors.append("status")
    if result.get("context_seconds") != [3000.0, 3180.0]:
        errors.append("context")
    if result.get("resolver_process_invocation_count") not in {0, 1} or result.get("caption_get_invocation_count") not in {0, 1}:
        errors.append("invocation_count")
    if result.get("provider_http_request_count") != "unavailable":
        errors.append("provider_http_claim")
    for field in (
        "track_url_persisted",
        "track_url_hash_persisted",
        "raw_resolver_output_persisted",
        "raw_caption_persisted",
        "post_cutoff_caption_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    for field in (
        "prediction_side_future_access_count",
        "human_caption_display_count",
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
    forbidden = {"track_url", "raw_caption", "caption_text", "cues", "future", "outcome"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "caption_context_published":
        if result.get("resolver_process_invocation_count") != 1 or result.get("caption_get_invocation_count") != 1:
            errors.append("success_invocations")
        if result.get("resolver_returncode") != 0:
            errors.append("success_resolver")
        if result.get("private_acquisition_full_caption_access_count") != 1 or result.get("private_acquisition_may_include_post_cutoff_content") is not True:
            errors.append("success_raw_scope")
        if result.get("private_material_cleared_before_fresh_public_reader") is not True:
            errors.append("success_clear")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("success_public")
        if int(result.get("public_cue_count", 0)) < 1:
            errors.append("success_cues")
        if float(result.get("public_first_cue_start_seconds", 0)) < 3000.0:
            errors.append("success_start")
        if float(result.get("public_last_cue_end_seconds", 999999)) > 3180.0:
            errors.append("success_end")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("success_reader")
        if result.get("fresh_reader_caption_text_returned") is not False:
            errors.append("success_text_return")
        if result.get("fresh_reader_artifact_sha256") != result.get("public_artifact_sha256"):
            errors.append("success_hash")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure_classification")
        if result.get("public_artifact_count") != 0 or result.get("public_manifest_count") != 0:
            errors.append("failure_public")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_caption_cutoff() -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B60ContractError("invalid B60 contract: " + ";".join(report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_roots(contract)
    b55_v1._exclusive_json(state_root / contract["runtime_state"]["intent_filename"], _intent(contract))
    result = _base_result(contract)
    manifest = None
    track_url = None
    headers = None
    raw_caption = None
    artifact = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        if yt_dlp is None:
            raise B60ExecutionError("tool_preflight", "tool_preflight", "yt-dlp unavailable")
        b55_contract = b55_v2.load_contract()
        version = b55_v2._tool_version(yt_dlp, b55_contract["transport"]["yt_dlp_version_command"])
        if version != contract["resolver"]["required_version"]:
            raise B60ExecutionError("tool_preflight", "tool_preflight", "yt-dlp version drift")
        result["yt_dlp_version"] = version
        result["resolver_process_invocation_count"] = 1
        resolver_start = perf_counter()
        try:
            completed = subprocess.run(
                build_resolver_command(contract), check=False, capture_output=True, timeout=contract["resolver"]["timeout_seconds"]
            )
        except subprocess.TimeoutExpired as exc:
            result["resolver_elapsed_seconds"] = round(perf_counter() - resolver_start, 6)
            result["resolver_stdout_bytes_discarded"] = len(exc.stdout or b"")
            result["resolver_stderr_bytes_discarded"] = len(exc.stderr or b"")
            raise B60ExecutionError("resolver", "timeout", "resolver timeout") from None
        result["resolver_elapsed_seconds"] = round(perf_counter() - resolver_start, 6)
        result["resolver_returncode"] = completed.returncode
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
        result["resolver_stdout_bytes_discarded"] = len(stdout)
        result["resolver_stderr_bytes_discarded"] = len(stderr)
        if completed.returncode != 0:
            category = b56.classify_private_stderr(stderr)
            stdout = stderr = b""
            completed = None
            raise B60ExecutionError("resolver", category, "resolver exit nonzero")
        track_url, headers = parse_private_resolver_output(stdout, contract)
        stdout = stderr = b""
        completed = None
        result["caption_get_invocation_count"] = 1
        get_start = perf_counter()
        raw_caption = retrieve_private_caption(track_url, headers, contract)
        result["caption_get_elapsed_seconds"] = round(perf_counter() - get_start, 6)
        result["caption_response_bytes_discarded_after_projection"] = len(raw_caption)
        result["private_acquisition_full_caption_access_count"] = 1
        result["private_acquisition_may_include_post_cutoff_content"] = True
        artifact = extract_context_artifact(raw_caption, contract)
        manifest = publish_context_artifact(artifact, public_root, contract)
        result["public_artifact_count"] = 1
        result["public_manifest_count"] = 1
        result["public_artifact_id"] = manifest["artifact_id"]
        result["public_artifact_sha256"] = manifest["artifact_sha256"]
        result["public_manifest_hash"] = manifest["manifest_hash"]
        result["public_cue_count"] = manifest["cue_count"]
        result["public_first_cue_start_seconds"] = manifest["first_cue_start_seconds"]
        result["public_last_cue_end_seconds"] = manifest["last_cue_end_seconds"]
        track_url = None
        headers = None
        raw_caption = None
        artifact = None
        result["private_material_cleared_before_fresh_public_reader"] = True
        environment = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", PUBLIC_ROOT_ENV: str(public_root)}
        child = subprocess.run(
            [sys.executable, str(ROOT / "p3_b60_caption_context_reader.py"), "--inspect", manifest["artifact_id"]],
            cwd=str(ROOT), env=environment, check=False, capture_output=True, text=True, timeout=60
        )
        result["fresh_public_reader_count"] = 1
        result["fresh_public_reader_exit_code"] = child.returncode
        if child.returncode != 0:
            raise B60ExecutionError("fresh_public_reader", "public_reader", "reader rejected artifact")
        inspection = json.loads(child.stdout)
        summary = inspection["artifact_summary"]
        result["fresh_reader_artifact_sha256"] = summary["artifact_sha256"]
        result["fresh_reader_caption_text_returned"] = summary["caption_text_returned"]
        if summary["cue_count"] != manifest["cue_count"]:
            raise B60ExecutionError("fresh_public_reader", "public_reader", "cue count mismatch")
        result["status"] = "caption_context_published"
    except Exception as exc:
        track_url = None
        headers = None
        raw_caption = None
        artifact = None
        result["private_material_cleared_before_fresh_public_reader"] = True
        if public_root.exists():
            os.chmod(public_root, 0o700)
            for path in public_root.iterdir():
                os.chmod(path, 0o600)
                path.unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "caption_context_failed"
        if isinstance(exc, B60ExecutionError):
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
        raise B60ContractError("invalid B60 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["runtime_state"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B60 private caption cutoff extractor")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B60 supports only the frozen one-shot caption extraction")
    result = execute_caption_cutoff()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "caption_context_published":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
