#!/usr/bin/env python3
"""Run the frozen P4-P lifecycle in two fresh Python processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import chromadb

import p4_p_cross_language_correction_lifecycle_gate as gate
import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l
import uruha_persisted_reference_time_p4 as p4o
import uruha_source_bound_japanese_value_surface_p4 as p4n


COLLECTION = "p4_p_correction_lifecycle"


class _Memory:
    def __init__(self, collection):
        self.profile_col = collection
        self.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        self._last_profile_state_shadow = {
            "status": "not_refreshed",
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }

    def _refresh_profile_state_shadow(self, *, reference_time=None):
        self._last_profile_state_shadow = {
            "status": "refreshed",
            "reference_time": reference_time,
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }


def _install_canonical_writer():
    base_extract = p4i.extract_explicit_current_preference_p4
    base_typed_record = p4i._typed_record
    p4l._ORIGINAL_EXTRACT = base_extract
    p4l._ORIGINAL_TYPED_RECORD = base_typed_record
    p4i.extract_explicit_current_preference_p4 = p4l.extract_with_preference_scope_canonicalization_p4
    p4i._typed_record = p4l.typed_record_with_preference_scope_canonicalization_p4


def _canonical_hash(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _snapshot(collection):
    payload = collection.get(include=["metadatas"])
    rows = [
        {"memory_id": memory_id, "metadata": metadata}
        for memory_id, metadata in zip(payload.get("ids") or [], payload.get("metadatas") or [])
    ]
    rows.sort(key=lambda row: row["memory_id"])
    return rows


def _record_hashes(rows):
    return {row["memory_id"]: _canonical_hash(row) for row in rows}


def _lineage(collection, reference_time):
    resolved = p4i._current_preference_rows(collection, reference_time=reference_time)
    payload = _snapshot(collection)
    negative = [
        row
        for row in payload
        if row["metadata"].get("preference_semantics") == "explicitly_negated_preference"
    ]
    return {
        "active_ids": sorted(str(row["memory_id"]) for row in resolved["active"]),
        "historical_ids": sorted(str(row["memory_id"]) for row in resolved["historical"]),
        "negative_ids": sorted(str(row["memory_id"]) for row in negative),
        "rows": payload,
    }


def _write_phase(db_path, contract):
    _install_canonical_writer()
    collection = chromadb.PersistentClient(path=db_path).get_or_create_collection(COLLECTION)
    memory = _Memory(collection)
    first = contract["process_1"]
    write = p4i.remember_explicit_current_preference_p4(
        memory, first["write_input"], timestamp=first["write_timestamp"]
    )
    correction = p4i.remember_explicit_current_preference_p4(
        memory, first["correction_input"], timestamp=first["correction_timestamp"]
    )
    lineage = _lineage(collection, first["correction_timestamp"])
    by_id = {row["memory_id"]: row["metadata"] for row in lineage["rows"]}
    negative_metadata = by_id.get(correction.get("negative_old_memory_id"), {})
    result = {
        "pid": os.getpid(),
        "session_id": str(uuid.uuid4()),
        "write_status": write.get("status"),
        "write_language": write.get("language"),
        "write_scope": write.get("scope"),
        "write_scope_source": write.get("scope_source"),
        "write_alias_id": (write.get(p4l.LABEL) or {}).get("alias_id"),
        "write_value": write.get("current_value"),
        "write_memory_id": write.get("current_memory_id"),
        "correction_status": correction.get("status"),
        "correction_language": correction.get("language"),
        "correction_scope": correction.get("scope"),
        "correction_scope_source": correction.get("scope_source"),
        "correction_alias_id": (correction.get(p4l.LABEL) or {}).get("alias_id"),
        "correction_previous_value": correction.get("previous_value"),
        "correction_current_value": correction.get("current_value"),
        "correction_memory_id": correction.get("current_memory_id"),
        "previous_current_memory_id": correction.get("previous_current_memory_id"),
        "negative_memory_id": correction.get("negative_old_memory_id"),
        "negative_correction_current_memory_id": negative_metadata.get(
            "correction_current_memory_id"
        ),
        "active_current_ids": lineage["active_ids"],
        "historical_current_ids": lineage["historical_ids"],
        "active_current_count": len(lineage["active_ids"]),
        "historical_current_count": len(lineage["historical_ids"]),
        "explicit_negative_count": len(lineage["negative_ids"]),
        "profile_record_count": len(lineage["rows"]),
        "history_preserved": correction.get("history_preserved"),
        "old_records_deleted_or_rewritten": correction.get("old_records_deleted_or_rewritten"),
        "record_hashes_after": _record_hashes(lineage["rows"]),
        "raw_dialogue_persisted": False,
    }
    return result


def _recall_phase(db_path, contract):
    collection = chromadb.PersistentClient(path=db_path).get_or_create_collection(COLLECTION)
    second = contract["process_2"]
    before = _snapshot(collection)
    lineage = _lineage(collection, "2026-09-22T08:02:00+08:00")
    recall = p4o.build_with_persisted_reference_time_p4(
        second["recall_input"], collection
    )
    after = _snapshot(collection)
    source_bound = recall.get(p4n.LABEL) or {}
    result = {
        "pid": os.getpid(),
        "session_id": str(uuid.uuid4()),
        "recall_status": recall.get("status"),
        "answer_use_authorized": recall.get("answer_use_authorized"),
        "query_language": recall.get("query_language"),
        "scope": recall.get("scope"),
        "localized_value_jp": recall.get("localized_value_jp"),
        "visible_surface": recall.get("selected_core_jp"),
        "value_surface_strategy": recall.get("value_surface_strategy"),
        "source_bound_status": source_bound.get("status"),
        "active_memory_id": recall.get("active_memory_id"),
        "answer_memory_ids": [recall.get("active_memory_id")] if recall.get("active_memory_id") else [],
        "process_start_active_ids": lineage["active_ids"],
        "process_start_historical_ids": lineage["historical_ids"],
        "process_start_negative_ids": lineage["negative_ids"],
        "profile_record_count_before": len(before),
        "profile_record_count_after": len(after),
        "profile_write_count": recall.get("profile_write_count"),
        "historical_answer_use_count": recall.get("historical_answer_use_count"),
        "explicit_negative_answer_use_count": recall.get("explicit_negative_answer_use_count"),
        "profile_snapshot_unchanged": before == after,
        "record_hashes_before": _record_hashes(before),
        "record_hashes_after": _record_hashes(after),
        "raw_dialogue_persisted": False,
    }
    return result


def _run_worker(phase, db_path):
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", phase, "--db", db_path]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return {
            "status": "worker_failed",
            "phase": phase,
            "returncode": completed.returncode,
            "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        }
    return json.loads(completed.stdout)


def run_frozen_probe():
    contract = gate.load_contract()
    with tempfile.TemporaryDirectory(prefix="uruha_p4_p_lifecycle_") as tempdir:
        db_path = str(Path(tempdir) / "memory_db")
        first = _run_worker("write", db_path)
        if first.get("status") == "worker_failed":
            evidence = {"process_1": first}
        else:
            second = _run_worker("recall", db_path)
            evidence = {
                "schema": "uruha_p4_p_cross_language_correction_lifecycle_evidence_v1",
                "process_1": first,
                "process_2": second,
                "restart": {
                    "old_process_exit_observed": True,
                    "old_pid": first.get("pid"),
                    "new_pid": second.get("pid"),
                    "old_session_id": first.get("session_id"),
                    "new_session_id": second.get("session_id"),
                    "same_persistent_db": True,
                },
                "accounting": {
                    "process_starts": 2,
                    "true_process_restart_count": 1,
                    "retry_count": 0,
                    "fallback_count": 0,
                    "model_call_count": 0,
                    "paid_api_call_count": 0,
                    "external_deployment_count": 0,
                    "production_memory_access_count": 0,
                },
            }
        evidence["gate_evaluation"] = gate.evaluate_evidence(contract, evidence)
        evidence["claim_boundary"] = contract["claim_boundary"]
        return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("write", "recall"))
    parser.add_argument("--db")
    args = parser.parse_args()
    contract = gate.load_contract()
    if args.worker:
        if not args.db:
            raise SystemExit("--db is required for a worker")
        result = (
            _write_phase(args.db, contract)
            if args.worker == "write"
            else _recall_phase(args.db, contract)
        )
    else:
        result = run_frozen_probe()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
