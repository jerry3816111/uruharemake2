"""B71 one-shot metadata-only selection of a third public source."""

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


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b71_source3_selection_preregistration_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b71_source3_selection_implementation_freeze_2026-09-20.json"


class B71ContractError(ValueError):
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


def expected_rows() -> list[dict[str, Any]]:
    return [
        {"row_id": "s3r0600", "context_seconds": [600.0, 780.0], "future_seconds": [781.0, 841.0]},
        {"row_id": "s3r1200", "context_seconds": [1200.0, 1380.0], "future_seconds": [1381.0, 1441.0]},
        {"row_id": "s3r1800", "context_seconds": [1800.0, 1980.0], "future_seconds": [1981.0, 2041.0]},
        {"row_id": "s3r2400", "context_seconds": [2400.0, 2580.0], "future_seconds": [2581.0, 2641.0]},
    ]


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b71_source3_selection_preregistration_v1":
        errors.append("schema")
    if contract.get("status") != "selection_rule_and_windows_frozen_before_source3_search_or_caption_access":
        errors.append("status")
    binding = contract.get("binding") or {}
    path = Path(root) / str(binding.get("path") or "")
    if not path.is_file():
        errors.append("binding_missing")
    elif sha256_file(path) != binding.get("sha256"):
        errors.append("binding_hash")
    discovery = contract.get("discovery") or {}
    if discovery != {
        "query": "ytsearch12:一ノ瀬うるは APEX 配信",
        "provider_result_limit": 12,
        "official_channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "excluded_video_ids": ["4y5GiQpgJgo", "Mlk5e3hBnb8"],
        "minimum_duration_seconds": 7200,
        "observable_metadata_fields": ["id", "duration", "channel_id", "title"],
        "selection_rule": "first provider-ranked result from the official channel, excluding both prior sources, with duration at least 7200 seconds",
        "caption_metadata_or_content_request_allowed": False,
        "retry_or_alternate_query_allowed": False,
    }:
        errors.append("discovery")
    if contract.get("frozen_rows") != expected_rows():
        errors.append("rows")
    execution = contract.get("execution") or {}
    if execution.get("provider_search_process_invocation_count_max") != 1 or execution.get("intent_without_result_is_terminal") is not True:
        errors.append("execution")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b71_provider_search_or_caption_access":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B71ContractError(";".join(errors))
    return {"valid": True, "provider_search_process_invocation_count_at_freeze": freeze.get("provider_search_process_invocation_count_at_freeze")}


def build_search_command(executable: str, contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    discovery = contract["discovery"]
    return [
        executable,
        "--ignore-config",
        "--quiet",
        "--no-warnings",
        "--flat-playlist",
        "--playlist-end",
        str(discovery["provider_result_limit"]),
        "--dump-single-json",
        "--skip-download",
        "--no-cache-dir",
        "--retries",
        "0",
        "--extractor-retries",
        "0",
        discovery["query"],
    ]


def select_source(document: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any] | None:
    contract = contract or load_contract()
    discovery = contract["discovery"]
    entries = document.get("entries") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise B71ContractError("search entries missing")
    for rank, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        video_id = entry.get("id")
        duration = entry.get("duration")
        if (
            isinstance(video_id, str)
            and video_id not in discovery["excluded_video_ids"]
            and entry.get("channel_id") == discovery["official_channel_id"]
            and isinstance(duration, (int, float))
            and float(duration) >= discovery["minimum_duration_seconds"]
            and isinstance(entry.get("title"), str)
        ):
            return {
                "source_id": f"youtube_{video_id}",
                "video_id": video_id,
                "channel_id": entry["channel_id"],
                "duration_seconds": float(duration),
                "title": entry["title"],
                "selection_rank": rank,
            }
    return None


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b71_source3_selection_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "query_sha256": sha256_bytes(contract["discovery"]["query"].encode("utf-8")),
        "excluded_video_ids": contract["discovery"]["excluded_video_ids"],
        "provider_search_process_invocation_count_max": 1,
        "caption_metadata_or_content_access_authorized": False,
        "contract_sha256": sha256_file(CONFIG_PATH),
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b71_source3_selection_result_v1":
        errors.append("schema")
    if result.get("status") not in {"selected", "no_eligible_source", "search_failed"}:
        errors.append("status")
    for field in ("caption_metadata_access_count", "caption_content_access_count", "model_call_count", "future_access_count", "retry_count", "fallback_count"):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("provider_search_process_invocation_count") != 1:
        errors.append("process_count")
    if result.get("raw_search_stdout_or_stderr_persisted") is not False:
        errors.append("raw_persistence")
    if result.get("status") == "selected":
        selected = result.get("selected_source") or {}
        if selected.get("video_id") in {"4y5GiQpgJgo", "Mlk5e3hBnb8"} or selected.get("channel_id") != "UC5LyYg6cCA4yHEYvtUsir3g" or selected.get("duration_seconds", 0) < 7200:
            errors.append("selection")
        if result.get("frozen_rows") != expected_rows():
            errors.append("rows")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_selection() -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B71ContractError("invalid contract: " + ";".join(report["errors"]))
    contract = load_contract()
    state_root = ROOT / contract["execution"]["state_root"]
    if state_root.exists():
        raise B71ContractError("B71 already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    result: dict[str, Any] = {
        "schema": "uruha_p3_b71_source3_selection_result_v1",
        "version": "1.0.0",
        "provider_search_process_invocation_count": 1,
        "caption_metadata_access_count": 0,
        "caption_content_access_count": 0,
        "model_call_count": 0,
        "future_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "raw_search_stdout_or_stderr_persisted": False,
        "claim_boundary": contract["claim_boundary"],
    }
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B71ContractError("yt-dlp unavailable before invocation")
    result["yt_dlp_version"] = b55_v2._tool_version(executable, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
    started = time.perf_counter()
    completed = subprocess.run(build_search_command(executable, contract), check=False, capture_output=True, timeout=60)
    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    result["search_returncode"] = completed.returncode
    stdout, stderr = completed.stdout or b"", completed.stderr or b""
    result["search_stdout_bytes_discarded"] = len(stdout)
    result["search_stderr_bytes_discarded"] = len(stderr)
    if completed.returncode != 0:
        result["status"] = "search_failed"
    else:
        try:
            document = json.loads(stdout)
            selected = select_source(document, contract)
        except (UnicodeDecodeError, json.JSONDecodeError, B71ContractError):
            result["status"] = "search_failed"
        else:
            if selected is None:
                result["status"] = "no_eligible_source"
            else:
                result["status"] = "selected"
                result["selected_source"] = selected
                result["frozen_rows"] = contract["frozen_rows"]
    stdout = stderr = b""
    completed = None
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B71ContractError("invalid result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B71 one-shot third-source selection")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B71 supports only one frozen selection")
    print(json.dumps(execute_selection(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
