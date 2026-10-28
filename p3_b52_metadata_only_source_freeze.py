"""Content-blind prospective source selection for P3-B52.

The selection contract accepts only identifiers, publication time, duration,
availability, and livestream status.  Titles, descriptions, transcripts, tags,
engagement counts, thumbnails, and all behavior content are outside authority.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b52_metadata_only_source_selection_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b52_metadata_only_source_selection_implementation_freeze_2026-09-17.json"
)


class B52ContractError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_contract():
    return load_json(CONFIG_PATH)


def validate_implementation_freeze(*, root=ROOT):
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_live_candidate_metadata_retrieval":
        errors.append("freeze_status_invalid")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"frozen_artifact_missing:{artifact_id}")
            continue
        observed = sha256_bytes(path.read_bytes())
        if observed != str((artifact or {}).get("sha256") or ""):
            errors.append(f"frozen_artifact_hash_mismatch:{artifact_id}")
    if errors:
        raise B52ContractError(";".join(errors))
    return {
        "valid": True,
        "frozen_artifact_count": len(freeze.get("frozen_artifacts") or {}),
        "live_metadata_retrieval_count_at_freeze": freeze.get(
            "live_metadata_retrieval_count_at_freeze"
        ),
        "target_segment_access_count_at_freeze": freeze.get(
            "target_segment_access_count_at_freeze"
        ),
        "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"),
    }


def _parse_date(value, field):
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise B52ContractError(f"invalid_date:{field}") from exc


def _validate_bindings(contract, root=ROOT):
    errors = []
    for binding_id, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{binding_id}")
            continue
        observed = sha256_bytes(path.read_bytes())
        if observed != str((binding or {}).get("sha256") or ""):
            errors.append(f"binding_hash_mismatch:{binding_id}")
    return errors


def validate_candidate(candidate, contract):
    candidate = deepcopy(candidate)
    schema = contract.get("candidate_schema") or {}
    required = set(schema.get("required_keys") or [])
    allowed = set(schema.get("allowed_keys") or [])
    forbidden = set(schema.get("forbidden_keys") or [])
    keys = set(candidate)
    errors = []
    missing = sorted(required - keys)
    unexpected = sorted(keys - allowed)
    explicit_forbidden = sorted(keys.intersection(forbidden))
    if missing:
        errors.append("missing_keys:" + ",".join(missing))
    if unexpected:
        errors.append("unexpected_keys:" + ",".join(unexpected))
    if explicit_forbidden:
        errors.append("forbidden_keys:" + ",".join(explicit_forbidden))
    if candidate.get("source_id") != f"youtube_{candidate.get('video_id', '')}":
        errors.append("source_id_not_derived_from_video_id")
    if not str(candidate.get("video_id") or "").strip():
        errors.append("video_id_missing")
    if isinstance(candidate.get("duration_seconds"), bool) or not isinstance(
        candidate.get("duration_seconds"), int
    ):
        errors.append("duration_seconds_not_integer")
    try:
        _parse_date(candidate.get("published_at"), "published_at")
    except B52ContractError as exc:
        errors.append(str(exc))
    return errors


def sanitize_ytdlp_entry(entry, contract):
    """Project a raw extractor row into the only authorized metadata fields."""
    target = contract["target"]
    timestamp = entry.get("timestamp")
    upload_date = str(entry.get("upload_date") or "")
    if timestamp is not None:
        published_at = dt.datetime.fromtimestamp(
            int(timestamp), tz=dt.timezone.utc
        ).date().isoformat()
    elif len(upload_date) == 8 and upload_date.isdigit():
        published_at = (
            f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        )
    else:
        published_at = ""
    video_id = str(entry.get("id") or "").strip()
    duration = entry.get("duration")
    if isinstance(duration, float) and duration.is_integer():
        duration = int(duration)
    return {
        "source_id": f"youtube_{video_id}",
        "platform": target["platform"],
        "video_id": video_id,
        "publisher_channel_id": str(
            entry.get("channel_id") or entry.get("uploader_id") or ""
        ).strip(),
        "published_at": published_at,
        "duration_seconds": duration,
        "availability": str(entry.get("availability") or "public").strip(),
        "live_status": str(entry.get("live_status") or "").strip(),
    }


def fetch_sanitized_official_stream_metadata(contract=None, *, executable=None):
    """Fetch public playlist metadata in memory and emit no raw extractor row."""
    contract = deepcopy(contract or load_contract())
    executable = executable or shutil.which("yt-dlp")
    if not executable:
        raise B52ContractError("yt_dlp_unavailable")
    target = contract["target"]
    maximum = int(contract["candidate_window"]["maximum_playlist_entries_requested"])
    command = [
        executable,
        "--flat-playlist",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        "--playlist-end",
        str(maximum),
        "--dump-json",
        target["official_streams_endpoint"],
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise B52ContractError(
            f"metadata_retrieval_failed:{completed.returncode}"
        )
    rows = []
    parse_failures = 0
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            parse_failures += 1
            continue
        rows.append(sanitize_ytdlp_entry(raw, contract))
    if parse_failures:
        raise B52ContractError(f"raw_metadata_parse_failure:{parse_failures}")
    return rows


def select_metadata_only_source(candidates, contract=None, exclusions=None):
    contract = deepcopy(contract or load_contract())
    binding_errors = _validate_bindings(contract)
    if binding_errors:
        raise B52ContractError(";".join(binding_errors))
    if exclusions is None:
        path = ROOT / contract["bindings"]["known_source_exclusions"]["path"]
        exclusions = load_json(path)
    if not isinstance(candidates, list) or not candidates:
        raise B52ContractError("empty_candidate_set")

    normalized = []
    seen = set()
    for index, candidate in enumerate(candidates):
        errors = validate_candidate(candidate, contract)
        if errors:
            raise B52ContractError(
                f"candidate[{index}]:" + ";".join(errors)
            )
        video_id = candidate["video_id"]
        if video_id in seen:
            raise B52ContractError(f"duplicate_video_id:{video_id}")
        seen.add(video_id)
        normalized.append(deepcopy(candidate))

    target = contract["target"]
    window = contract["candidate_window"]
    start = _parse_date(window["published_on_or_after"], "window_start")
    end = _parse_date(window["published_on_or_before"], "window_end")
    excluded_ids = set(exclusions.get("excluded_video_ids") or [])
    eligible = []
    rejected_counts = {
        "wrong_target": 0,
        "outside_date_window": 0,
        "outside_duration_window": 0,
        "not_public_completed_livestream": 0,
        "known_source": 0,
    }
    for row in normalized:
        if (
            row["platform"] != target["platform"]
            or row["publisher_channel_id"] != target["publisher_channel_id"]
        ):
            rejected_counts["wrong_target"] += 1
            continue
        published = _parse_date(row["published_at"], "published_at")
        if not start <= published <= end:
            rejected_counts["outside_date_window"] += 1
            continue
        if not (
            int(window["minimum_duration_seconds"])
            <= row["duration_seconds"]
            <= int(window["maximum_duration_seconds"])
        ):
            rejected_counts["outside_duration_window"] += 1
            continue
        if (
            row["availability"] != window["required_availability"]
            or row["live_status"] != window["required_live_status"]
        ):
            rejected_counts["not_public_completed_livestream"] += 1
            continue
        if row["video_id"] in excluded_ids:
            rejected_counts["known_source"] += 1
            continue
        eligible.append(row)
    if not eligible:
        raise B52ContractError("empty_eligible_set")

    seed = contract["selection"]["seed"]
    scored = []
    for row in eligible:
        score = sha256_bytes(
            f"{seed}|{row['video_id']}|{row['published_at']}".encode("utf-8")
        )
        scored.append((score, row))
    scored.sort(key=lambda item: (item[0], item[1]["video_id"]))
    winning_score, selected = scored[0]
    candidate_material = sorted(
        normalized,
        key=lambda row: (row["published_at"], row["video_id"]),
    )
    eligible_material = sorted(
        eligible,
        key=lambda row: (row["published_at"], row["video_id"]),
    )
    candidate_set_hash = sha256_bytes(
        canonical_json(candidate_material).encode("utf-8")
    )
    eligible_set_hash = sha256_bytes(
        canonical_json(eligible_material).encode("utf-8")
    )
    contract_hash = sha256_bytes(canonical_json(contract).encode("utf-8"))
    receipt_material = {
        "schema": "uruha_p3_b52_metadata_only_source_selection_receipt_v1",
        "contract_hash": contract_hash,
        "candidate_set_hash": candidate_set_hash,
        "eligible_set_hash": eligible_set_hash,
        "selection_seed": seed,
        "selected_source_id": selected["source_id"],
        "selected_video_id": selected["video_id"],
        "selected_published_at": selected["published_at"],
        "selected_duration_seconds": selected["duration_seconds"],
        "selection_score": winning_score,
    }
    receipt_hash = sha256_bytes(
        canonical_json(receipt_material).encode("utf-8")
    )
    return {
        **receipt_material,
        "receipt_hash": receipt_hash,
        "candidate_count": len(normalized),
        "eligible_count": len(eligible),
        "rejected_counts": rejected_counts,
        "stored_title_count": 0,
        "stored_description_count": 0,
        "stored_transcript_count": 0,
        "target_segment_access_count": 0,
        "future_response_access_count": 0,
        "gold_annotation_count": 0,
        "model_call_count": 0,
        "formal_m56_artifact_change_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    validate_implementation_freeze()
    contract = load_contract()
    candidates = fetch_sanitized_official_stream_metadata(contract)
    print(
        json.dumps(
            select_metadata_only_source(candidates, contract),
            ensure_ascii=False,
            indent=2,
        )
    )
