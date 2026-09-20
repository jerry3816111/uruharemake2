"""B75 one-shot metadata-only source selection and prospective episode search frame."""

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
CONFIG_PATH = ROOT / "configs" / "p3_b75_real_episode_sampling_frame_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b75_real_episode_sampling_frame_implementation_freeze_2026-09-20.json"


class B75Error(RuntimeError):
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
    if contract.get("schema") != "uruha_p3_b75_real_episode_sampling_frame_contract_v1":
        errors.append("schema")
    if contract.get("status") != "source_selection_and_slot_algorithm_frozen_before_search_or_content_review":
        errors.append("status")
    binding = contract.get("binding") or {}
    path = Path(root) / str(binding.get("path") or "")
    if not path.is_file():
        errors.append("binding_missing")
    elif sha256_file(path) != binding.get("sha256"):
        errors.append("binding_hash")
    if contract.get("lane_separation") != {
        "this_lane": "observational_public_uruha_stimulus_response_prediction",
        "controlled_context_flip_lane_is_separate": True,
        "natural_future_is_not_assumed_to_supply_same_surface_context_pairs": True,
        "controlled_cases_may_not_be_scored_as_observed_uruha_future": True,
    }:
        errors.append("lane_separation")
    discovery = contract.get("discovery") or {}
    expected_discovery = {
        "query": "ytsearch24:一ノ瀬うるは コラボ 雑談",
        "provider_result_limit": 24,
        "official_channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "excluded_video_ids": ["4y5GiQpgJgo", "Mlk5e3hBnb8", "j6Hlk9cY9LQ"],
        "minimum_duration_seconds": 1800,
        "required_title_keywords_any": ["コラボ", "雑談", "対談", "飲酒", "質問", "恋バナ"],
        "selected_source_count_exact": 3,
        "observable_metadata_fields": ["id", "duration", "channel_id", "title"],
        "selection_rule": "first three provider-ranked official-channel results excluding prior sources, duration at least 1800 seconds, and containing any frozen title keyword",
        "caption_media_or_content_access_allowed": False,
        "retry_or_alternate_query_allowed": False,
    }
    if discovery != expected_discovery:
        errors.append("discovery")
    slot = contract.get("slot_algorithm") or {}
    if slot != {
        "slots_per_source_exact": 6,
        "source_relative_start_fractions": [0.10, 0.25, 0.40, 0.55, 0.70, 0.85],
        "search_region_seconds": 300,
        "candidate_rule": "first chronologically qualifying stimulus-response event wholly inside the frozen search region",
        "qualifying_event_requires_external_stimulus": True,
        "qualifying_event_requires_uruha_response": True,
        "speaker_or_stimulus_attribution_required": True,
        "unusable_region_is_preserved_without_replacement": True,
        "adjacent_monologue_substitution_allowed": False,
        "target_response_may_not_be_viewed_during_source_or_slot_selection": True,
    }:
        errors.append("slot_algorithm")
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
    if freeze.get("status") != "frozen_before_b75_search_or_content_review":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / artifact["path"]
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B75Error("freeze:" + ";".join(errors))
    return {"valid": True}


def build_search_command(executable: str, contract: dict[str, Any] | None = None) -> list[str]:
    discovery = (contract or load_contract())["discovery"]
    return [
        executable, "--ignore-config", "--quiet", "--no-warnings", "--flat-playlist",
        "--playlist-end", str(discovery["provider_result_limit"]), "--dump-single-json",
        "--skip-download", "--no-cache-dir", "--retries", "0", "--extractor-retries", "0",
        discovery["query"],
    ]


def select_sources(document: dict[str, Any], contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    discovery = contract["discovery"]
    entries = document.get("entries") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise B75Error("search entries missing")
    selected = []
    for rank, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        video_id, duration, title = entry.get("id"), entry.get("duration"), entry.get("title")
        eligible = (
            isinstance(video_id, str)
            and video_id not in discovery["excluded_video_ids"]
            and entry.get("channel_id") == discovery["official_channel_id"]
            and isinstance(duration, (int, float))
            and float(duration) >= discovery["minimum_duration_seconds"]
            and isinstance(title, str)
            and any(keyword in title for keyword in discovery["required_title_keywords_any"])
        )
        if eligible:
            selected.append({
                "source_id": f"youtube_{video_id}", "video_id": video_id,
                "channel_id": entry["channel_id"], "duration_seconds": float(duration),
                "title": title, "selection_rank": rank,
            })
            if len(selected) == discovery["selected_source_count_exact"]:
                break
    return selected


def build_slots(sources: list[dict[str, Any]], contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    contract = contract or load_contract()
    slot = contract["slot_algorithm"]
    rows = []
    for source_index, source in enumerate(sources, start=1):
        duration = source["duration_seconds"]
        for slot_index, fraction in enumerate(slot["source_relative_start_fractions"], start=1):
            start = round(duration * fraction, 3)
            end = round(min(start + slot["search_region_seconds"], duration), 3)
            rows.append({
                "slot_id": f"b75-s{source_index}-r{slot_index:02d}",
                "source_id": source["source_id"],
                "source_selection_rank": source["selection_rank"],
                "relative_start_fraction": fraction,
                "search_region_seconds": [start, end],
                "selection_instruction": slot["candidate_rule"],
                "unusable_without_replacement": True,
            })
    return rows


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b75_real_episode_sampling_frame_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "query_sha256": sha256_bytes(contract["discovery"]["query"].encode("utf-8")),
        "slot_algorithm_sha256": sha256_bytes(canonical_json(contract["slot_algorithm"]).encode("utf-8")),
        "contract_sha256": sha256_file(CONFIG_PATH),
        "provider_search_process_invocation_count_max": 1,
        "content_review_authorized": False,
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _finalize(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    errors = []
    if result.get("schema") != "uruha_p3_b75_real_episode_sampling_frame_result_v1" or result.get("status") not in {"frame_frozen", "insufficient_eligible_sources", "search_failed"}:
        errors.append("identity")
    for field in ("caption_metadata_access_count", "caption_content_access_count", "media_playback_count", "model_call_count", "outcome_access_count", "retry_count", "fallback_count"):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("provider_search_process_invocation_count") != 1 or result.get("raw_search_stdout_or_stderr_persisted") is not False:
        errors.append("execution")
    if result.get("status") == "frame_frozen":
        sources = result.get("selected_sources") or []
        slots = result.get("sampling_slots") or []
        if len(sources) != 3 or len(slots) != 18 or slots != build_slots(sources, contract):
            errors.append("frame")
        if any(source["video_id"] in contract["discovery"]["excluded_video_ids"] for source in sources):
            errors.append("excluded_source")
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
        raise B75Error("contract:" + ";".join(validation["errors"]))
    state_root = ROOT / contract["execution"]["state_root"]
    if state_root.exists():
        raise B75Error("B75 already consumed")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    b55_v1._exclusive_json(state_root / contract["execution"]["intent_filename"], _intent(contract))
    result: dict[str, Any] = {
        "schema": "uruha_p3_b75_real_episode_sampling_frame_result_v1",
        "version": "1.0.0",
        "provider_search_process_invocation_count": 1,
        "caption_metadata_access_count": 0,
        "caption_content_access_count": 0,
        "media_playback_count": 0,
        "model_call_count": 0,
        "outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "raw_search_stdout_or_stderr_persisted": False,
        "controlled_context_flip_lane_separate": True,
        "claim_boundary": contract["claim_boundary"],
    }
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B75Error("yt-dlp unavailable before invocation")
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
            sources = select_sources(document, contract)
        except (UnicodeDecodeError, json.JSONDecodeError, B75Error):
            result["status"] = "search_failed"
        else:
            result["eligible_source_count_found"] = len(sources)
            result["selected_sources"] = sources
            if len(sources) != contract["discovery"]["selected_source_count_exact"]:
                result["status"] = "insufficient_eligible_sources"
            else:
                result["status"] = "frame_frozen"
                result["sampling_slots"] = build_slots(sources, contract)
    stdout = stderr = b""
    completed = None
    _finalize(result)
    result_validation = validate_result(result, contract)
    if not result_validation["valid"]:
        raise B75Error("result:" + ";".join(result_validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["execution"]["result_filename"], result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    if not args.execute_once:
        parser.error("B75 supports only --execute-once")
    print(json.dumps(execute_once(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
