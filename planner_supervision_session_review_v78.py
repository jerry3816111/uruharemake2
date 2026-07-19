"""Build and review hash-bound session provenance units for planner supervision."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v78_session_review_contract.json"


def _candidate_binding(candidate):
    return {
        "id": candidate.get("id"),
        "source_sha256": (candidate.get("provenance") or {}).get("source_sha256"),
        "target_plan_sha256": candidate.get("target_plan_sha256"),
    }


def _preview_rows(candidates):
    indexes = sorted({0, len(candidates) // 2, len(candidates) - 1})
    return [
        {
            "turn_index": candidates[index].get("source_turn_index"),
            "user_utterance": (candidates[index].get("input") or {}).get("user_utterance"),
        }
        for index in indexes
    ]


def _session_summary(candidates):
    timestamps = [
        str((candidate.get("source_record") or {}).get("timestamp") or "")
        for candidate in candidates
    ]
    timestamps = [value for value in timestamps if value]
    turns = [candidate.get("source_turn_index") for candidate in candidates]
    turns = [value for value in turns if isinstance(value, int)]
    all_utterances = [
        {
            "turn_index": candidate.get("source_turn_index"),
            "user_utterance": (candidate.get("input") or {}).get("user_utterance"),
        }
        for candidate in candidates
    ]
    return {
        "candidate_count": len(candidates),
        "turn_index_range": [min(turns), max(turns)] if turns else None,
        "timestamp_range": [min(timestamps), max(timestamps)] if timestamps else None,
        "language_counts": dict(sorted(Counter(candidate["input"]["language"] for candidate in candidates).items())),
        "scenario_family_counts": dict(
            sorted(Counter(candidate["scenario_family"] for candidate in candidates).items())
        ),
        "utterance_preview": _preview_rows(candidates),
        "all_user_utterances": all_utterances,
    }


def build_session_review_units(candidates):
    grouped = defaultdict(list)
    for candidate in candidates:
        checks = candidate.get("collection_checks") or {}
        if checks.get("session_quarantine_applied") is not True:
            raise ValueError("candidate queue was not built with session quarantine")
        if checks.get("evaluation_contaminated_session") is not False:
            raise ValueError("candidate queue contains an evaluation-contaminated session")
        session_id = str(candidate.get("source_session_id") or "")
        if not session_id:
            raise ValueError("candidate is missing source_session_id")
        grouped[session_id].append(candidate)

    units = []
    for session_id, rows in sorted(grouped.items()):
        rows.sort(key=lambda candidate: (candidate.get("source_turn_index") is None, candidate.get("source_turn_index")))
        bindings = [_candidate_binding(candidate) for candidate in rows]
        candidate_set_sha256 = v76.canonical_sha256(bindings)
        summary = _session_summary(rows)
        summary_sha256 = v76.canonical_sha256(summary)
        units.append(
            {
                "schema": "uruha_planner_supervision_session_review_unit_v78",
                "id": "session_v78_" + v76.canonical_sha256(
                    {"session_id": session_id, "candidate_set_sha256": candidate_set_sha256}
                )[:20],
                "source_session_id": session_id,
                "candidate_ids": [candidate["id"] for candidate in rows],
                "candidate_bindings": bindings,
                "candidate_set_sha256": candidate_set_sha256,
                "session_summary": summary,
                "session_summary_sha256": summary_sha256,
                "status": "pending_human_session_provenance_review",
            }
        )
    return units


def write_session_review_outputs(units, queue_path, report_path):
    v76.write_jsonl(queue_path, units)
    report = {
        "schema": "uruha_planner_supervision_session_review_build_v78",
        "pending_candidate_count": sum(unit["session_summary"]["candidate_count"] for unit in units),
        "session_review_unit_count": len(units),
        "repeated_provenance_decisions_removed": sum(
            unit["session_summary"]["candidate_count"] for unit in units
        )
        - len(units),
        "training_rows_created": 0,
        "additional_model_calls": 0,
        "evidence_boundary": "Session review units are local pending data and do not certify a session or create training rows.",
    }
    v76.atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def _verify_review_unit(unit):
    if unit.get("session_summary_sha256") != v76.canonical_sha256(unit.get("session_summary")):
        raise ValueError("session summary hash mismatch")
    candidate_ids = unit.get("candidate_ids") or []
    candidate_bindings = unit.get("candidate_bindings") or []
    if unit.get("candidate_set_sha256") != v76.canonical_sha256(candidate_bindings):
        raise ValueError("session candidate set hash mismatch")
    if candidate_ids != [binding.get("id") for binding in candidate_bindings]:
        raise ValueError("session candidate identifiers do not match bindings")
    summary = unit.get("session_summary") or {}
    if len(candidate_ids) != summary.get("candidate_count"):
        raise ValueError("session candidate count mismatch")


def review_session(
    review_unit_id,
    decision,
    reviewer_id,
    *,
    consent_to_training=False,
    notes="",
    candidate_path,
    queue_path,
    manifest_path,
    reviewed_at=None,
):
    reviewer_id = str(reviewer_id or "").strip()
    if not reviewer_id:
        raise ValueError("reviewer_id is required")
    if decision not in {"certify_nonbenchmark", "quarantine"}:
        raise ValueError("invalid session review decision")
    if decision == "certify_nonbenchmark" and consent_to_training is not True:
        raise ValueError("certification requires explicit local training consent")
    if decision == "quarantine" and consent_to_training:
        raise ValueError("a quarantined session cannot consent to training")

    units = v76._latest_by_key(v76.load_jsonl(queue_path), "id")
    unit = units.get(str(review_unit_id))
    if not unit:
        raise ValueError("session review unit not found")
    _verify_review_unit(unit)
    canonical_units = v76._latest_by_key(build_session_review_units(v76.load_jsonl(candidate_path)), "id")
    if canonical_units.get(str(review_unit_id)) != unit:
        raise ValueError("session review unit does not match the current candidate queue")
    session_id = str(unit.get("source_session_id") or "")
    manifest_rows = v76.load_jsonl(manifest_path)
    if session_id in v76._latest_by_key(manifest_rows, "session_id"):
        raise ValueError("session already reviewed")

    reviewed_at = reviewed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    certified = decision == "certify_nonbenchmark"
    row = {
        "schema": "uruha_planner_supervision_session_review_v78",
        "review_unit_id": unit["id"],
        "session_id": session_id,
        "decision": decision,
        "benchmark_origin": "none" if certified else "benchmark_or_uncertain",
        "consent_to_training": bool(certified),
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "candidate_set_sha256": unit["candidate_set_sha256"],
        "session_summary_sha256": unit["session_summary_sha256"],
        "notes": str(notes or "").strip(),
    }
    v76.append_jsonl(manifest_path, row)
    return row


def session_review_status(units, manifest_rows):
    latest = v76._latest_by_key(manifest_rows, "session_id")
    certified = 0
    quarantined = 0
    pending = 0
    certified_candidate_count = 0
    for unit in units:
        row = latest.get(unit["source_session_id"])
        if not row:
            pending += 1
        elif v76._session_is_certified(unit["source_session_id"], manifest_rows):
            certified += 1
            certified_candidate_count += unit["session_summary"]["candidate_count"]
        else:
            quarantined += 1
    return {
        "session_review_unit_count": len(units),
        "certified_session_count": certified,
        "quarantined_session_count": quarantined,
        "pending_session_count": pending,
        "certified_candidate_count": certified_candidate_count,
        "training_rows_created": 0,
    }
