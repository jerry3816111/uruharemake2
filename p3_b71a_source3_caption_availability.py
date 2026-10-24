"""B71A metadata-only Japanese caption availability for the frozen third source."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56
import p3_b59_source_semantic_availability_probe as b59
import p3_b69a_source2_caption_availability as b69a


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b71a_source3_caption_availability_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b71a_source3_caption_availability_implementation_freeze_2026-09-20.json"


class B71AError(RuntimeError):
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


def build_command(contract: dict[str, Any] | None = None) -> list[str]:
    return b69a.build_command(contract or load_contract())


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b71a_source3_caption_availability_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_before_source3_caption_metadata_request":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file() or sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding:{name}")
    source = contract.get("source") or {}
    expected_source = {
        "source_id": "youtube_j6Hlk9cY9LQ",
        "video_id": "j6Hlk9cY9LQ",
        "locator": "https://www.youtube.com/watch?v=j6Hlk9cY9LQ",
        "duration_seconds": 12883.0,
    }
    if source != expected_source:
        errors.append("source")
    probe = contract.get("probe") or {}
    if probe.get("required_yt_dlp_version") != "2026.02.04" or probe.get("resolver_process_invocation_count_max") != 1 or probe.get("caption_content_download_count_max") != 0:
        errors.append("probe_limits")
    if probe.get("target_language_code") != "ja" or not probe.get("preferred_formats_in_order"):
        errors.append("probe_target")
    for field in ("retry_or_fallback_allowed", "cookies_login_paid_api_or_account_access_allowed", "raw_stdout_stderr_or_track_url_persistence_allowed"):
        if probe.get(field) is not False:
            errors.append(field)
    release_binding = contract["bindings"]["source_selection_release"]
    release = load_json(Path(root) / release_binding["path"])
    if release.get("result", {}).get("video_id") != source.get("video_id") or release.get("next_stage", {}).get("caption_content_download_allowed") is not False:
        errors.append("selection")
    if any(value is not True for value in (contract.get("denied_actions") or {}).values()):
        errors.append("denied")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b71a_metadata_request":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B71AError("invalid freeze: " + ";".join(errors))
    return {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": freeze.get("resolver_process_invocation_count_at_freeze"),
        "caption_content_download_count_at_freeze": freeze.get("caption_content_download_count_at_freeze"),
    }


def _finalize(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b71a_source3_caption_availability_result_v1" or result.get("status") not in {"available", "unavailable", "probe_failed"}:
        errors.append("identity")
    if result.get("source_id") != "youtube_j6Hlk9cY9LQ":
        errors.append("source")
    if result.get("resolver_process_invocation_count") not in {0, 1} or result.get("caption_content_download_count") != 0:
        errors.append("counts")
    for field in ("retry_count", "fallback_count", "model_call_count", "future_content_access_count", "training_write_count", "production_write_count"):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("raw_stdout_stderr_or_track_url_persisted") is not False:
        errors.append("private")
    if result.get("status") == "available" and (result.get("selected_track_type") not in {"manual", "automatic"} or result.get("selected_language_code") != "ja" or not result.get("selected_format")):
        errors.append("available")
    if result.get("status") == "unavailable" and any(result.get(field) is not None for field in ("selected_track_type", "selected_language_code", "selected_format")):
        errors.append("unavailable")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("hash")
    return {"valid": not errors, "errors": errors}


def execute() -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    report = validate_contract(contract)
    if not report["valid"]:
        raise B71AError("invalid contract: " + ";".join(report["errors"]))
    state_root = ROOT / contract["execution"]["state_root"]
    if state_root.exists():
        raise B71AError("B71A already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    intent = {
        "schema": "uruha_p3_b71a_intent_v1",
        "source_id": contract["source"]["source_id"],
        "caption_content_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], intent)
    result = {
        "schema": "uruha_p3_b71a_source3_caption_availability_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "resolver_process_invocation_count": 0,
        "caption_content_download_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 0,
        "future_content_access_count": 0,
        "training_write_count": 0,
        "production_write_count": 0,
        "raw_stdout_stderr_or_track_url_persisted": False,
        "claim_boundary": contract["claim_boundary"],
    }
    started = time.perf_counter()
    try:
        executable = shutil.which("yt-dlp")
        version = b55_v2._tool_version(executable, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
        if version != contract["probe"]["required_yt_dlp_version"]:
            raise B71AError("yt-dlp version drift")
        result["yt_dlp_version"] = version
        result["resolver_process_invocation_count"] = 1
        completed = subprocess.run(build_command(contract), capture_output=True, timeout=120)
        result["resolver_returncode"] = completed.returncode
        result["resolver_stdout_bytes_discarded"] = len(completed.stdout or b"")
        result["resolver_stderr_bytes_discarded"] = len(completed.stderr or b"")
        if completed.returncode != 0:
            result.update({"status": "probe_failed", "failure_category": b56.classify_private_stderr(completed.stderr or b"")})
        else:
            projection = b59.parse_private_probe_output(completed.stdout or b"", b69a._b59_parse_contract(contract))
            result.update(projection)
            result["status"] = "available" if projection["selected_track_type"] else "unavailable"
        completed = None
    except Exception as exc:
        result.update({"status": "probe_failed", "failure_category": "preflight_or_contract", "failure_class": type(exc).__name__})
    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    _finalize(result)
    checked = validate_result(result)
    if not checked["valid"]:
        raise B71AError("invalid result: " + ";".join(checked["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    if not args.execute_once:
        parser.error("B71A supports only one frozen execution")
    result = execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] == "probe_failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
