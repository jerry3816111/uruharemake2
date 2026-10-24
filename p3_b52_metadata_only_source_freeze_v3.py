"""Reviewed Atom-first, no-replacement source freeze for P3-B52 V3."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import p3_b52_metadata_only_source_freeze as v1


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b52_metadata_only_source_selection_v3.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b52_metadata_only_source_selection_v3_implementation_freeze_2026-09-17.json"
)
ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/2015"
USER_AGENT = "UruhaBrain-P3-B52-Metadata-Only/3.0"


def load_config():
    return v1.load_json(CONFIG_PATH)


def _verify_binding(binding, binding_id):
    path = ROOT / str((binding or {}).get("path") or "")
    if not path.is_file():
        raise v1.B52ContractError(f"binding_missing:{binding_id}")
    if v1.sha256_bytes(path.read_bytes()) != str((binding or {}).get("sha256") or ""):
        raise v1.B52ContractError(f"binding_hash_mismatch:{binding_id}")
    return path


def validate_contract(config=None):
    config = deepcopy(config or load_config())
    errors = []
    if config.get("schema") != "uruha_p3_b52_metadata_only_source_selection_v3":
        errors.append("schema_mismatch")
    for binding_id, binding in (config.get("bindings") or {}).items():
        try:
            _verify_binding(binding, binding_id)
        except v1.B52ContractError as exc:
            errors.append(str(exc))
    base = v1.load_json(
        ROOT / config["bindings"]["v1_selection_contract"]["path"]
    )
    preselection = config.get("preselection") or {}
    postcheck = config.get("postselection_check") or {}
    unchanged = {
        "target_id": config.get("target", {}).get("target_id")
        == base.get("target", {}).get("target_id"),
        "platform": config.get("target", {}).get("platform")
        == base.get("target", {}).get("platform"),
        "publisher_channel": config.get("target", {}).get(
            "publisher_channel_id"
        )
        == base.get("target", {}).get("publisher_channel_id"),
        "date_start": preselection.get("published_on_or_after")
        == base.get("candidate_window", {}).get("published_on_or_after"),
        "date_end": preselection.get("published_on_or_before")
        == base.get("candidate_window", {}).get("published_on_or_before"),
        "seed": preselection.get("seed")
        == base.get("selection", {}).get("seed"),
        "score": preselection.get("score")
        == base.get("selection", {}).get("score"),
        "winner": preselection.get("winner")
        == base.get("selection", {}).get("winner"),
        "duration_min": postcheck.get("minimum_duration_seconds")
        == base.get("candidate_window", {}).get("minimum_duration_seconds"),
        "duration_max": postcheck.get("maximum_duration_seconds")
        == base.get("candidate_window", {}).get("maximum_duration_seconds"),
        "availability": postcheck.get("required_availability")
        == base.get("candidate_window", {}).get("required_availability"),
        "live_status": postcheck.get("required_live_status")
        == base.get("candidate_window", {}).get("required_live_status"),
    }
    if not all(unchanged.values()):
        errors.append("v1_selection_semantics_changed")
    if postcheck.get("automatic_replacement") is not False:
        errors.append("automatic_replacement_must_be_false")
    if postcheck.get("selected_video_id_must_not_change") is not True:
        errors.append("selected_id_binding_missing")
    boundary = config.get("execution_boundary") or {}
    if boundary.get("maximum_v3_atom_retrievals") != 1:
        errors.append("atom_retrieval_count_not_one")
    if boundary.get("maximum_selected_id_postchecks") != 1:
        errors.append("postcheck_count_not_one")
    if any(
        boundary.get(key) is not False
        for key in (
            "target_segment_access",
            "future_response_access",
            "gold_annotation",
            "model_generation",
            "formal_m56_artifact_change",
            "production_memory_write",
            "external_deployment",
        )
    ):
        errors.append("execution_boundary_open")
    return {
        "valid": not errors,
        "errors": errors,
        "unchanged_v1_checks": unchanged,
    }


def validate_implementation_freeze():
    freeze = v1.load_json(FREEZE_PATH)
    errors = []
    if freeze.get("status") != "frozen_before_v3_atom_or_postcheck_network_access":
        errors.append("freeze_status_invalid")
    for artifact_id, binding in (freeze.get("frozen_artifacts") or {}).items():
        try:
            _verify_binding(binding, artifact_id)
        except v1.B52ContractError as exc:
            errors.append(str(exc).replace("binding_", "frozen_artifact_", 1))
    if errors:
        raise v1.B52ContractError(";".join(errors))
    return {
        "valid": True,
        "reviewed_option": freeze.get("reviewed_option"),
        "atom_retrieval_count_at_freeze": freeze.get(
            "atom_retrieval_count_at_freeze"
        ),
        "selected_id_postcheck_count_at_freeze": freeze.get(
            "selected_id_postcheck_count_at_freeze"
        ),
        "target_segment_access_count_at_freeze": freeze.get(
            "target_segment_access_count_at_freeze"
        ),
    }


def parse_atom_metadata(payload, config=None):
    config = deepcopy(config or load_config())
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise v1.B52ContractError("atom_xml_invalid") from exc
    rows = []
    allowed_keys = set(config["preselection"]["allowed_keys"])
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        video_id = str(entry.findtext(f"{{{YT_NS}}}videoId") or "").strip()
        channel_id = str(entry.findtext(f"{{{YT_NS}}}channelId") or "").strip()
        published_text = str(
            entry.findtext(f"{{{ATOM_NS}}}published") or ""
        ).strip()
        try:
            published_at = dt.datetime.fromisoformat(
                published_text.replace("Z", "+00:00")
            ).date().isoformat()
        except ValueError as exc:
            raise v1.B52ContractError("atom_published_at_invalid") from exc
        row = {
            "source_id": f"youtube_{video_id}",
            "platform": config["target"]["platform"],
            "video_id": video_id,
            "publisher_channel_id": channel_id,
            "published_at": published_at,
        }
        if set(row) != allowed_keys:
            raise v1.B52ContractError("atom_projection_schema_mismatch")
        rows.append(row)
    if not rows:
        raise v1.B52ContractError("atom_feed_returned_no_entries")
    maximum = int(config["preselection"]["maximum_feed_entries"])
    if len(rows) > maximum:
        raise v1.B52ContractError("atom_feed_entry_count_exceeds_freeze")
    return rows


def fetch_atom_metadata(config=None):
    config = deepcopy(config or load_config())
    request = urllib.request.Request(
        config["target"]["official_atom_endpoint"],
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            status = int(response.status)
    except Exception as exc:
        raise v1.B52ContractError(
            f"atom_retrieval_failed:{type(exc).__name__}"
        ) from exc
    if status != 200:
        raise v1.B52ContractError(f"atom_http_status:{status}")
    return parse_atom_metadata(payload, config)


def _validate_preselection_candidate(row, config):
    preselection = config["preselection"]
    keys = set(row)
    required = set(preselection["required_keys"])
    allowed = set(preselection["allowed_keys"])
    forbidden = set(preselection["forbidden_keys"])
    errors = []
    if keys != required or not keys.issubset(allowed):
        errors.append("preselection_schema_mismatch")
    if keys.intersection(forbidden):
        errors.append("preselection_forbidden_field")
    if row.get("source_id") != f"youtube_{row.get('video_id', '')}":
        errors.append("source_id_not_derived")
    return errors


def select_atom_source(rows, config=None, exclusions=None):
    config = deepcopy(config or load_config())
    report = validate_contract(config)
    if not report["valid"]:
        raise v1.B52ContractError(";".join(report["errors"]))
    if exclusions is None:
        exclusions = v1.load_json(
            ROOT / config["bindings"]["known_source_exclusions"]["path"]
        )
    if not isinstance(rows, list) or not rows:
        raise v1.B52ContractError("empty_atom_candidate_set")
    known = set(exclusions.get("excluded_video_ids") or [])
    start = dt.date.fromisoformat(config["preselection"]["published_on_or_after"])
    end = dt.date.fromisoformat(config["preselection"]["published_on_or_before"])
    eligible = []
    seen = set()
    rejected = {"wrong_channel": 0, "outside_date_window": 0, "known_source": 0}
    for index, row in enumerate(rows):
        errors = _validate_preselection_candidate(row, config)
        if errors:
            raise v1.B52ContractError(
                f"candidate[{index}]:" + ";".join(errors)
            )
        if row["video_id"] in seen:
            raise v1.B52ContractError(f"duplicate_video_id:{row['video_id']}")
        seen.add(row["video_id"])
        if row["publisher_channel_id"] != config["target"]["publisher_channel_id"]:
            rejected["wrong_channel"] += 1
            continue
        published = dt.date.fromisoformat(row["published_at"])
        if not start <= published <= end:
            rejected["outside_date_window"] += 1
            continue
        if row["video_id"] in known:
            rejected["known_source"] += 1
            continue
        seed = config["preselection"]["seed"]
        score = v1.sha256_bytes(
            f"{seed}|{row['video_id']}|{row['published_at']}".encode("utf-8")
        )
        eligible.append((score, deepcopy(row)))
    if not eligible:
        raise v1.B52ContractError("empty_atom_eligible_set")
    eligible.sort(key=lambda item: (item[0], item[1]["video_id"]))
    winning_score, selected = eligible[0]
    candidate_hash = v1.sha256_bytes(
        v1.canonical_json(
            sorted(rows, key=lambda row: (row["published_at"], row["video_id"]))
        ).encode("utf-8")
    )
    selection_material = {
        "schema": "uruha_p3_b52_atom_preselection_receipt_v3",
        "candidate_set_hash": candidate_hash,
        "selection_seed": config["preselection"]["seed"],
        "selected_source_id": selected["source_id"],
        "selected_video_id": selected["video_id"],
        "selected_published_at": selected["published_at"],
        "selection_score": winning_score,
    }
    return {
        **selection_material,
        "preselection_receipt_hash": v1.sha256_bytes(
            v1.canonical_json(selection_material).encode("utf-8")
        ),
        "atom_candidate_count": len(rows),
        "preselection_eligible_count": len(eligible),
        "preselection_rejected_counts": rejected,
        "selected_id_locked_before_postcheck": True,
    }


def fetch_selected_metadata(preselection, config=None, *, executable=None):
    config = deepcopy(config or load_config())
    executable = executable or shutil.which("yt-dlp")
    if not executable:
        raise v1.B52ContractError("yt_dlp_unavailable")
    columns = config["postselection_check"]["stdout_columns"]
    output_template = "\t".join(f"%({column})s" for column in columns)
    video_id = preselection["selected_video_id"]
    command = [
        executable,
        "--skip-download",
        "--quiet",
        "--no-warnings",
        "--output-na-placeholder",
        "",
        "--print",
        output_template,
        f"https://www.youtube.com/watch?v={video_id}",
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
        raise v1.B52ContractError(
            f"selected_metadata_postcheck_failed:{completed.returncode}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise v1.B52ContractError("selected_metadata_row_count_not_one")
    fields = lines[0].split("\t")
    if len(fields) != 6:
        raise v1.B52ContractError("selected_metadata_column_count_invalid")
    raw = {
        "id": fields[0],
        "channel_id": fields[1],
        "upload_date": fields[2],
        "duration": float(fields[3]) if fields[3] else None,
        "availability": fields[4],
        "live_status": fields[5],
    }
    return v1.sanitize_ytdlp_entry(raw, v1.load_contract())


def finalize_no_replacement(preselection, selected_metadata, config=None):
    config = deepcopy(config or load_config())
    check = config["postselection_check"]
    expected_id = preselection["selected_video_id"]
    observed_id = str((selected_metadata or {}).get("video_id") or "")
    reasons = []
    if observed_id != expected_id:
        reasons.append("selected_video_id_changed")
    if selected_metadata.get("publisher_channel_id") != config["target"]["publisher_channel_id"]:
        reasons.append("publisher_channel_mismatch")
    if selected_metadata.get("published_at") != preselection["selected_published_at"]:
        reasons.append("published_date_mismatch")
    duration = selected_metadata.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, int):
        reasons.append("duration_unavailable")
    elif not check["minimum_duration_seconds"] <= duration <= check["maximum_duration_seconds"]:
        reasons.append("duration_outside_frozen_range")
    if selected_metadata.get("availability") != check["required_availability"]:
        reasons.append("not_public")
    if selected_metadata.get("live_status") != check["required_live_status"]:
        reasons.append("not_completed_livestream")
    accepted = not reasons
    result_material = {
        "schema": "uruha_p3_b52_metadata_only_source_freeze_result_v3",
        "status": (
            "source_reserved_postcheck_passed"
            if accepted
            else "selected_source_ineligible_no_replacement"
        ),
        "preselection_receipt_hash": preselection["preselection_receipt_hash"],
        "selected_source_id": preselection["selected_source_id"],
        "selected_video_id": expected_id,
        "selected_published_at": preselection["selected_published_at"],
        "selected_duration_seconds": duration,
        "postcheck_accepted": accepted,
        "postcheck_reasons": reasons,
        "automatic_replacement_performed": False,
    }
    return {
        **result_material,
        "result_hash": v1.sha256_bytes(
            v1.canonical_json(result_material).encode("utf-8")
        ),
        "atom_retrieval_count": 1,
        "selected_id_postcheck_count": 1,
        "stored_title_count": 0,
        "stored_description_count": 0,
        "stored_transcript_count": 0,
        "target_segment_access_count": 0,
        "future_response_access_count": 0,
        "gold_annotation_count": 0,
        "model_call_count": 0,
        "formal_m56_artifact_change_count": 0,
        "claim_boundary": config["claim_boundary"],
    }


def execute_v3():
    validate_implementation_freeze()
    config = load_config()
    contract = validate_contract(config)
    if not contract["valid"]:
        raise v1.B52ContractError(";".join(contract["errors"]))
    rows = fetch_atom_metadata(config)
    preselection = select_atom_source(rows, config)
    try:
        selected_metadata = fetch_selected_metadata(preselection, config)
    except v1.B52ContractError as exc:
        return {
            "schema": "uruha_p3_b52_metadata_only_source_freeze_result_v3",
            "status": "selected_source_postcheck_transport_failed_no_replacement",
            **preselection,
            "postcheck_accepted": False,
            "postcheck_reasons": [str(exc)],
            "automatic_replacement_performed": False,
            "atom_retrieval_count": 1,
            "selected_id_postcheck_count": 1,
            "stored_title_count": 0,
            "stored_description_count": 0,
            "stored_transcript_count": 0,
            "target_segment_access_count": 0,
            "future_response_access_count": 0,
            "gold_annotation_count": 0,
            "model_call_count": 0,
            "formal_m56_artifact_change_count": 0,
            "claim_boundary": config["claim_boundary"],
        }
    return {**preselection, **finalize_no_replacement(preselection, selected_metadata, config)}


if __name__ == "__main__":
    print(json.dumps(execute_v3(), ensure_ascii=False, indent=2))
