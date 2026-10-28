"""Single-repair metadata transport for the frozen P3-B52 selection rule."""

from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import p3_b52_metadata_only_source_freeze as v1


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b52_metadata_only_source_selection_v2.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b52_metadata_only_source_selection_v2_implementation_freeze_2026-09-17.json"
)


def load_v2_config():
    return v1.load_json(CONFIG_PATH)


def _verify_file_binding(binding, binding_id):
    path = ROOT / str((binding or {}).get("path") or "")
    if not path.is_file():
        raise v1.B52ContractError(f"binding_missing:{binding_id}")
    if v1.sha256_bytes(path.read_bytes()) != str((binding or {}).get("sha256") or ""):
        raise v1.B52ContractError(f"binding_hash_mismatch:{binding_id}")
    return path


def build_effective_contract(config=None):
    config = deepcopy(config or load_v2_config())
    base_path = _verify_file_binding(config.get("base_contract"), "base_contract")
    _verify_file_binding(config.get("retained_failure"), "retained_failure")
    base = v1.load_json(base_path)
    before = deepcopy(base)
    override = config.get("retrieval_override") or {}
    base.update(
        {
            "schema": config["schema"],
            "version": config["version"],
            "status": config["status"],
            "single_changed_variable": config["single_changed_variable"],
            "retrieval_policy": deepcopy(override),
            "claim_boundary": config["claim_boundary"],
        }
    )
    for field in config.get("frozen_unchanged_fields") or []:
        if field.startswith("bindings."):
            key = field.split(".", 1)[1]
            if base["bindings"].get(key) != before["bindings"].get(key):
                raise v1.B52ContractError(f"frozen_field_changed:{field}")
        elif field == "claim_boundary":
            continue
        elif base.get(field) != before.get(field):
            raise v1.B52ContractError(f"frozen_field_changed:{field}")
    if int(override.get("maximum_playlist_entries_requested", -1)) != int(
        before["candidate_window"]["maximum_playlist_entries_requested"]
    ):
        raise v1.B52ContractError("maximum_playlist_entries_changed")
    return base


def validate_implementation_freeze():
    freeze = v1.load_json(FREEZE_PATH)
    errors = []
    if freeze.get("status") != "frozen_before_second_and_final_live_metadata_retrieval":
        errors.append("freeze_status_invalid")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = ROOT / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"frozen_artifact_missing:{artifact_id}")
            continue
        if v1.sha256_bytes(path.read_bytes()) != str((artifact or {}).get("sha256") or ""):
            errors.append(f"frozen_artifact_hash_mismatch:{artifact_id}")
    if errors:
        raise v1.B52ContractError(";".join(errors))
    return {
        "valid": True,
        "v1_failed_attempts_retained": freeze.get("v1_failed_attempts_retained"),
        "v2_live_retrieval_count_at_freeze": freeze.get(
            "v2_live_retrieval_count_at_freeze"
        ),
        "target_segment_access_count_at_freeze": freeze.get(
            "target_segment_access_count_at_freeze"
        ),
        "model_call_count_at_freeze": freeze.get("model_call_count_at_freeze"),
    }


def _parse_allowlisted_line(line, contract):
    fields = line.rstrip("\n").split("\t")
    if len(fields) != 6:
        raise v1.B52ContractError("allowlisted_metadata_column_count_invalid")
    video_id, channel_id, upload_date, duration, availability, live_status = fields
    raw = {
        "id": video_id,
        "channel_id": channel_id,
        "upload_date": upload_date,
        "duration": float(duration) if duration else None,
        "availability": availability,
        "live_status": live_status,
    }
    return v1.sanitize_ytdlp_entry(raw, contract)


def fetch_allowlisted_metadata(contract=None, *, executable=None):
    contract = deepcopy(contract or build_effective_contract())
    config = load_v2_config()
    retrieval = config["retrieval_override"]
    executable = executable or shutil.which("yt-dlp")
    if not executable:
        raise v1.B52ContractError("yt_dlp_unavailable")
    columns = retrieval["stdout_columns"]
    if columns != [
        "id",
        "channel_id",
        "upload_date",
        "duration",
        "availability",
        "live_status",
    ]:
        raise v1.B52ContractError("stdout_columns_changed")
    output_template = "\t".join(f"%({column})s" for column in columns)
    command = [
        executable,
        "--skip-download",
        "--ignore-errors",
        "--quiet",
        "--no-warnings",
        "--playlist-end",
        str(retrieval["maximum_playlist_entries_requested"]),
        "--output-na-placeholder",
        "",
        "--print",
        output_template,
        contract["target"]["official_streams_endpoint"],
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        raise v1.B52ContractError(
            f"metadata_retrieval_failed:{completed.returncode}"
        )
    rows = [
        _parse_allowlisted_line(line, contract)
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    if not rows:
        raise v1.B52ContractError("metadata_retrieval_returned_no_rows")
    return rows


if __name__ == "__main__":
    validate_implementation_freeze()
    effective = build_effective_contract()
    candidates = fetch_allowlisted_metadata(effective)
    print(
        json.dumps(
            v1.select_metadata_only_source(candidates, effective),
            ensure_ascii=False,
            indent=2,
        )
    )
