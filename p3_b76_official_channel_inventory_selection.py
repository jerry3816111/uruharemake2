"""B76 one-shot official-channel metadata inventory selection repair."""

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
import p3_b75_real_episode_sampling_frame as b75


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b76_official_channel_inventory_selection_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b76_official_channel_inventory_selection_implementation_freeze_2026-09-20.json"


class B76Error(RuntimeError):
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


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b76_official_channel_inventory_selection_contract_v1" or contract.get("status") != "single_inventory_repair_frozen_before_official_channel_request_or_content_review":
        errors.append("identity")
    binding = contract.get("binding") or {}
    path = Path(root) / str(binding.get("path") or "")
    if not path.is_file():
        errors.append("binding_missing")
    elif sha256_file(path) != binding.get("sha256"):
        errors.append("binding_hash")
    inventory = contract.get("inventory") or {}
    if inventory != {
        "url": "https://www.youtube.com/channel/UC5LyYg6cCA4yHEYvtUsir3g/videos",
        "provider_entry_limit": 200,
        "official_channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "excluded_video_ids": ["4y5GiQpgJgo", "Mlk5e3hBnb8", "j6Hlk9cY9LQ"],
        "minimum_duration_seconds": 1800,
        "required_title_keywords_any": ["コラボ", "雑談", "対談", "飲酒", "質問", "恋バナ"],
        "selected_source_count_exact": 3,
        "selection_rule": "first three provider-ordered official channel upload entries satisfying the unchanged B75 exclusions duration and title keywords",
        "retry_alternate_tab_query_keyword_or_manual_selection_allowed": False,
    }:
        errors.append("inventory")
    slot = contract.get("slot_algorithm") or {}
    if slot != {
        "reuse_b75_build_slots_without_change": True,
        "slots_per_source_exact": 6,
        "source_relative_start_fractions": [0.10, 0.25, 0.40, 0.55, 0.70, 0.85],
        "search_region_seconds": 300,
        "unusable_without_replacement": True,
        "adjacent_monologue_substitution_allowed": False,
    }:
        errors.append("slot_algorithm")
    execution = contract.get("execution") or {}
    if execution.get("provider_inventory_process_invocation_count_max") != 1 or execution.get("intent_without_result_is_terminal") is not True:
        errors.append("execution")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b76_inventory_request_or_content_review":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / artifact["path"]
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B76Error("freeze:" + ";".join(errors))
    return {"valid": True}


def build_inventory_command(executable: str, contract: dict[str, Any] | None = None) -> list[str]:
    inventory = (contract or load_contract())["inventory"]
    return [
        executable, "--ignore-config", "--quiet", "--no-warnings", "--flat-playlist",
        "--playlist-end", str(inventory["provider_entry_limit"]), "--dump-single-json",
        "--skip-download", "--no-cache-dir", "--retries", "0", "--extractor-retries", "0",
        inventory["url"],
    ]


def select_sources(document: dict[str, Any], contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    inventory = contract["inventory"]
    entries = document.get("entries") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise B76Error("inventory entries missing")
    selected = []
    for rank, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        video_id, duration, title = entry.get("id"), entry.get("duration"), entry.get("title")
        entry_channel = entry.get("channel_id") or document.get("channel_id")
        if (
            isinstance(video_id, str)
            and video_id not in inventory["excluded_video_ids"]
            and entry_channel == inventory["official_channel_id"]
            and isinstance(duration, (int, float)) and float(duration) >= inventory["minimum_duration_seconds"]
            and isinstance(title, str) and any(keyword in title for keyword in inventory["required_title_keywords_any"])
        ):
            selected.append({
                "source_id": f"youtube_{video_id}", "video_id": video_id,
                "channel_id": inventory["official_channel_id"], "duration_seconds": float(duration),
                "title": title, "selection_rank": rank,
            })
            if len(selected) == inventory["selected_source_count_exact"]:
                break
    return selected


def b75_slot_contract() -> dict[str, Any]:
    contract = deepcopy(b75.load_contract())
    return contract


def _finalize(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b76_official_channel_inventory_result_v1" or result.get("status") not in {"frame_frozen", "insufficient_eligible_sources", "inventory_failed"}:
        errors.append("identity")
    for field in ("caption_metadata_access_count", "caption_content_access_count", "media_playback_count", "model_call_count", "outcome_access_count", "retry_count", "fallback_count"):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("provider_inventory_process_invocation_count") != 1 or result.get("raw_inventory_stdout_or_stderr_persisted") is not False:
        errors.append("execution")
    if result.get("status") == "frame_frozen":
        sources, slots = result.get("selected_sources") or [], result.get("sampling_slots") or []
        if len(sources) != 3 or len(slots) != 18 or slots != b75.build_slots(sources, b75_slot_contract()):
            errors.append("frame")
    candidate = deepcopy(result)
    expected_hash = candidate.pop("result_hash", None)
    if expected_hash != sha256_bytes(canonical_json(candidate).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_once() -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    validation = validate_contract(contract)
    if not validation["valid"]:
        raise B76Error("contract:" + ";".join(validation["errors"]))
    state_root = ROOT / contract["execution"]["state_root"]
    if state_root.exists():
        raise B76Error("B76 already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    intent = {
        "schema": "uruha_p3_b76_inventory_intent_v1", "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "inventory_url_sha256": sha256_bytes(contract["inventory"]["url"].encode("utf-8")),
        "filter_sha256": sha256_bytes(canonical_json({key: value for key, value in contract["inventory"].items() if key != "url"}).encode("utf-8")),
        "contract_sha256": sha256_file(CONFIG_PATH), "content_review_authorized": False,
    }
    intent["intent_hash"] = sha256_bytes(canonical_json(intent).encode("utf-8"))
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], intent)
    result: dict[str, Any] = {
        "schema": "uruha_p3_b76_official_channel_inventory_result_v1", "version": "1.0.0",
        "provider_inventory_process_invocation_count": 1,
        "caption_metadata_access_count": 0, "caption_content_access_count": 0, "media_playback_count": 0,
        "model_call_count": 0, "outcome_access_count": 0, "retry_count": 0, "fallback_count": 0,
        "raw_inventory_stdout_or_stderr_persisted": False, "claim_boundary": contract["claim_boundary"],
    }
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B76Error("yt-dlp unavailable before invocation")
    result["yt_dlp_version"] = b55_v2._tool_version(executable, b55_v2.load_contract()["transport"]["yt_dlp_version_command"])
    started = time.perf_counter()
    completed = subprocess.run(build_inventory_command(executable, contract), check=False, capture_output=True, timeout=90)
    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    result["inventory_returncode"] = completed.returncode
    stdout, stderr = completed.stdout or b"", completed.stderr or b""
    result["inventory_stdout_bytes_discarded"] = len(stdout)
    result["inventory_stderr_bytes_discarded"] = len(stderr)
    if completed.returncode != 0:
        result["status"] = "inventory_failed"
    else:
        try:
            sources = select_sources(json.loads(stdout), contract)
        except (UnicodeDecodeError, json.JSONDecodeError, B76Error):
            result["status"] = "inventory_failed"
        else:
            result["eligible_source_count_found"] = len(sources)
            result["selected_sources"] = sources
            if len(sources) != contract["inventory"]["selected_source_count_exact"]:
                result["status"] = "insufficient_eligible_sources"
            else:
                result["status"] = "frame_frozen"
                result["sampling_slots"] = b75.build_slots(sources, b75_slot_contract())
    stdout = stderr = b""
    completed = None
    _finalize(result)
    result_validation = validate_result(result)
    if not result_validation["valid"]:
        raise B76Error("result:" + ";".join(result_validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    if not args.execute_once:
        parser.error("B76 supports only --execute-once")
    print(json.dumps(execute_once(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
