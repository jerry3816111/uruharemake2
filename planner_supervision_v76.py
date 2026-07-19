"""Local-only collection and strict review helpers for planner supervision."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import audit_planner_supervision_v75 as v75


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v76_collection_contract.json"
V75_CONTRACT_PATH = ROOT / "configs/planner_supervision_v75_readiness_contract.json"
WEB_LOG_PATH = ROOT / "web_logs/uruha_web_conversation_log.jsonl"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path, rows):
    atomic_write(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def detect_language(text):
    text = str(text or "")
    if re.search(r"[ぁ-んァ-ヶ]", text):
        return "ja"
    if re.search(r"[一-龠]", text):
        return "zh"
    return "en"


def infer_scenario_family(plan):
    plan = plan or {}
    joined = " ".join(
        str(plan.get(field) or "").casefold()
        for field in ("intent", "scene", "response_mode", "surface_act", "hidden_intent")
    )
    if plan.get("self_correction_applied") or any(marker in joined for marker in ("repair", "correction")):
        return "reflection_repair"
    if any(marker in joined for marker in ("function", "tool", "action", "vrm", "call")):
        return "action_function_call"
    if plan.get("memory_use_expected") or any(marker in joined for marker in ("memory", "recall", "remember")):
        return "memory_recall_update"
    if any(marker in joined for marker in ("false_belief", "theory_of_mind", "belief_reasoning")):
        return "false_belief_tom"
    if any(marker in joined for marker in ("crisis", "boundary", "refusal", "protective_brake", "safety")):
        return "boundary_safety"
    if any(marker in joined for marker in ("clarify", "ambiguous", "premise_challenge", "reference_probe")):
        return "ambiguity_clarification"
    if any(marker in joined for marker in ("support", "comfort", "anxiety", "empath")):
        return "emotional_support"
    if any(marker in joined for marker in ("relationship", "trust", "jealous", "attachment")):
        return "relationship_personality"
    if str(plan.get("hidden_intent") or "") not in {"", "plain_request", "plain_statement"}:
        return "pragmatic_implicature"
    return "ordinary_direct"


def protected_inputs_from_v75(v75_contract=None):
    v75_contract = v75_contract or load_json(V75_CONTRACT_PATH)
    protected = set()
    for spec in v75_contract["source_registry"]:
        if not spec.get("protected_evaluation"):
            continue
        loaded = v75._load_source(spec, v75_contract)
        for user_utterance in loaded["protected_utterances"]:
            normalized = v75._normalize(user_utterance)
            if normalized:
                protected.add(normalized)
    return protected


def input_context_from_log(record):
    trace = record.get("cognition_trace") or {}
    memory = record.get("memory_snapshot") or {}
    psyche = trace.get("psyche_before") or {}
    return {
        "user_utterance": str(record.get("user_text") or "").strip(),
        "language": detect_language(record.get("user_text")),
        "recent_dialogue": memory.get("recent_turns") or [],
        "working_memory": memory.get("working_memory_items") or [],
        "psyche_state": psyche,
        "relationship_state": {
            "trust": psyche.get("trust"),
            "trust_lock_turns": psyche.get("trust_lock_turns", 0),
        },
    }


def input_fingerprint(input_context):
    payload = {
        "user_utterance": v75._normalize(input_context.get("user_utterance")),
        "language": input_context.get("language"),
        "recent_dialogue": input_context.get("recent_dialogue") or [],
        "working_memory": input_context.get("working_memory") or [],
        "psyche_state": input_context.get("psyche_state") or {},
        "relationship_state": input_context.get("relationship_state") or {},
    }
    return canonical_sha256(payload)


def _input_is_complete(input_context, v75_contract):
    if not v75._complete_input_context(input_context, v75_contract):
        return False
    psyche = input_context.get("psyche_state") or {}
    relationship = input_context.get("relationship_state") or {}
    return psyche.get("mood") is not None and psyche.get("trust") is not None and relationship.get("trust") is not None


def _overlap_reason(user_utterance, protected_inputs, threshold):
    normalized = v75._normalize(user_utterance)
    if not normalized:
        return "missing_user_utterance"
    if normalized in protected_inputs:
        return "exact_evaluation_overlap"
    if any(SequenceMatcher(None, normalized, old).ratio() >= threshold for old in protected_inputs):
        return "near_evaluation_overlap"
    return ""


def evaluation_contaminated_sessions(records, protected_inputs, threshold):
    contaminated = set()
    overlap_reasons = []
    for record in records:
        reason = _overlap_reason(record.get("user_text"), protected_inputs, threshold)
        overlap_reasons.append(reason)
        if reason in {"exact_evaluation_overlap", "near_evaluation_overlap"}:
            contaminated.add(str(record.get("session_id") or ""))
    return contaminated, overlap_reasons


def build_candidates(
    records,
    protected_inputs=None,
    contract=None,
    v75_contract=None,
    *,
    quarantine_contaminated_sessions=True,
):
    contract = contract or load_json(CONTRACT_PATH)
    v75_contract = v75_contract or load_json(V75_CONTRACT_PATH)
    protected_inputs = protected_inputs if protected_inputs is not None else protected_inputs_from_v75(v75_contract)
    accepted_modes = set(contract["accepted_input_modes"])
    threshold = float(contract["near_evaluation_overlap_threshold"])
    records = list(records)
    contaminated_sessions, overlap_reasons = evaluation_contaminated_sessions(records, protected_inputs, threshold)
    candidates = []
    reason_counts = Counter()
    seen_fingerprints = set()
    otherwise_valid_records_quarantined = 0

    for record, overlap_reason in zip(records, overlap_reasons):
        reasons = []
        session_is_contaminated = str(record.get("session_id") or "") in contaminated_sessions
        if record.get("input_mode") not in accepted_modes:
            reasons.append("unsupported_input_mode")
        input_context = input_context_from_log(record)
        target_plan = record.get("logic") or {}
        if not _input_is_complete(input_context, v75_contract):
            reasons.append("incomplete_input_context")
        if not v75._complete_plan(target_plan, v75_contract):
            reasons.append("incomplete_target_plan")
        if overlap_reason:
            reasons.append(overlap_reason)
        fingerprint = input_fingerprint(input_context)
        if fingerprint in seen_fingerprints:
            reasons.append("duplicate_input_context")
        if quarantine_contaminated_sessions and session_is_contaminated:
            if not reasons:
                otherwise_valid_records_quarantined += 1
            reasons.append("evaluation_contaminated_session")

        if reasons:
            reason_counts.update(set(reasons))
            continue
        seen_fingerprints.add(fingerprint)
        source_id = f"web_log:{record.get('session_id')}:{record.get('turn_index')}"
        source_sha256 = canonical_sha256(record)
        target_sha256 = canonical_sha256(target_plan)
        candidate_id = "plan_v76_" + canonical_sha256(
            {"source_id": source_id, "source_sha256": source_sha256, "target_plan_sha256": target_sha256}
        )[:20]
        candidates.append(
            {
                "schema": "uruha_planner_supervision_candidate_v76",
                "id": candidate_id,
                "scenario_family": infer_scenario_family(target_plan),
                "split": "candidate",
                "status": "pending_human_plan_review_and_session_certification",
                "input": input_context,
                "target_plan": target_plan,
                "target_plan_sha256": target_sha256,
                "source_session_id": str(record.get("session_id") or ""),
                "source_turn_index": record.get("turn_index"),
                "source_record": record,
                "provenance": {
                    "source_kind": "live_dialogue_pending_review",
                    "source_id": source_id,
                    "source_sha256": source_sha256,
                    "benchmark_origin": "unknown",
                },
                "collection_checks": {
                    "complete_input_context": True,
                    "complete_target_plan": True,
                    "evaluation_overlap": False,
                    "duplicate_input_context": False,
                    "session_quarantine_applied": quarantine_contaminated_sessions,
                    "evaluation_contaminated_session": session_is_contaminated,
                    "additional_model_calls": 0,
                },
            }
        )

    return {
        "schema": "uruha_planner_supervision_candidate_build_v76",
        "summary": {
            "source_record_count": len(records),
            "candidate_count": len(candidates),
            "excluded_count": len(records) - len(candidates),
            "protected_input_count": len(protected_inputs),
            "session_quarantine_enabled": quarantine_contaminated_sessions,
            "evaluation_contaminated_session_count": len(contaminated_sessions),
            "otherwise_valid_records_quarantined": otherwise_valid_records_quarantined,
            "additional_model_calls": 0,
            "training_rows_created": 0,
        },
        "exclusion_reason_counts": dict(sorted(reason_counts.items())),
        "evaluation_contaminated_session_sha256s": sorted(
            canonical_sha256({"session_id": session_id}) for session_id in contaminated_sessions
        ),
        "candidates": candidates,
        "evidence_boundary": "Candidates are quarantined pending data. They are not human-approved targets and cannot enter training.",
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# V76 Planner Supervision Candidate Build",
        "",
        f"- source_record_count: {summary['source_record_count']}",
        f"- pending_candidate_count: {summary['candidate_count']}",
        f"- excluded_count: {summary['excluded_count']}",
        f"- protected_input_count: {summary['protected_input_count']}",
        f"- additional_model_calls: {summary['additional_model_calls']}",
        f"- training_rows_created: {summary['training_rows_created']}",
        "",
        "## Exclusions",
        "",
    ]
    for reason, count in report["exclusion_reason_counts"].items():
        lines.append(f"- {reason}: {count}")
    if not report["exclusion_reason_counts"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Pending candidates remain local and cannot be used for training until strict review and session certification succeed.",
            "",
        ]
    )
    return "\n".join(lines)


def write_candidate_outputs(report, candidate_path, report_path, markdown_path=None):
    write_jsonl(candidate_path, report["candidates"])
    atomic_write(report_path, json.dumps({key: value for key, value in report.items() if key != "candidates"}, ensure_ascii=False, indent=2) + "\n")
    if markdown_path:
        atomic_write(markdown_path, build_markdown(report))


def _latest_by_key(rows, key):
    output = {}
    for row in rows:
        value = str(row.get(key) or "")
        if value:
            output[value] = row
    return output


def _session_is_certified(session_id, manifest_rows):
    row = _latest_by_key(manifest_rows, "session_id").get(str(session_id)) or {}
    return row.get("benchmark_origin") == "none" and row.get("consent_to_training") is True


def review_candidate(
    candidate_id,
    decision,
    reviewer_id,
    scenario_family,
    notes="",
    certify_non_benchmark=False,
    consent_to_training=False,
    candidate_path=None,
    manifest_path=None,
    review_path=None,
    strict_annotation_path=None,
    reviewed_at=None,
    contract=None,
    v75_contract=None,
    protected_inputs=None,
):
    contract = contract or load_json(CONTRACT_PATH)
    v75_contract = v75_contract or load_json(V75_CONTRACT_PATH)
    paths = contract["local_paths"]
    candidate_path = Path(candidate_path or ROOT / paths["candidate_queue"])
    manifest_path = Path(manifest_path or ROOT / paths["session_manifest"])
    review_path = Path(review_path or ROOT / paths["review_log"])
    strict_annotation_path = Path(strict_annotation_path or ROOT / paths["strict_annotations"])
    reviewed_at = reviewed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    reviewer_id = str(reviewer_id or "").strip()
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be accept or reject")
    if not reviewer_id:
        raise ValueError("reviewer_id is required")
    if scenario_family not in contract["scenario_families"]:
        raise ValueError("scenario_family is invalid")

    candidates = _latest_by_key(load_jsonl(candidate_path), "id")
    candidate = candidates.get(str(candidate_id))
    if not candidate:
        raise ValueError("candidate not found")
    if str(candidate_id) in _latest_by_key(load_jsonl(review_path), "candidate_id"):
        raise ValueError("candidate already reviewed")
    if str(candidate_id) in _latest_by_key(load_jsonl(strict_annotation_path), "id"):
        raise ValueError("candidate already accepted")
    collection_checks = candidate.get("collection_checks") or {}
    if collection_checks.get("session_quarantine_applied") is not True:
        raise ValueError("candidate was not built with session quarantine")
    if collection_checks.get("evaluation_contaminated_session") is not False:
        raise ValueError("candidate belongs to an evaluation-contaminated session")
    source_record = candidate.get("source_record")
    source_sha256 = (candidate.get("provenance") or {}).get("source_sha256")
    if not isinstance(source_record, dict) or source_sha256 != canonical_sha256(source_record):
        raise ValueError("candidate source hash mismatch")
    if canonical_sha256(input_context_from_log(source_record)) != canonical_sha256(candidate.get("input")):
        raise ValueError("candidate input does not match source record")
    if canonical_sha256(source_record.get("logic") or {}) != canonical_sha256(candidate.get("target_plan")):
        raise ValueError("candidate target does not match source record")
    if candidate.get("target_plan_sha256") != canonical_sha256(candidate.get("target_plan")):
        raise ValueError("candidate target hash mismatch")

    session_id = str(candidate.get("source_session_id") or "")
    manifest_rows = load_jsonl(manifest_path)
    pending_certification = None
    if certify_non_benchmark or consent_to_training:
        if not (certify_non_benchmark and consent_to_training):
            raise ValueError("non-benchmark certification and training consent must both be true")
        existing = _latest_by_key(manifest_rows, "session_id").get(session_id)
        if existing and not _session_is_certified(session_id, manifest_rows):
            raise ValueError("session has a conflicting certification")
        if not existing:
            pending_certification = {
                "schema": "uruha_planner_supervision_session_certification_v76",
                "session_id": session_id,
                "benchmark_origin": "none",
                "consent_to_training": True,
                "certified_by": reviewer_id,
                "certified_at": reviewed_at,
            }
            manifest_rows.append(pending_certification)

    accepted_row = None
    if decision == "accept":
        if not _session_is_certified(session_id, manifest_rows):
            raise ValueError("accepted plan requires a certified non-benchmark training session")
        protected_inputs = protected_inputs if protected_inputs is not None else protected_inputs_from_v75(v75_contract)
        overlap = _overlap_reason(candidate["input"]["user_utterance"], protected_inputs, contract["near_evaluation_overlap_threshold"])
        if overlap:
            raise ValueError(f"candidate overlaps protected evaluation data: {overlap}")
        accepted_row = {
            "schema": "uruha_planner_supervision_annotation_v75",
            "id": candidate["id"],
            "scenario_family": scenario_family,
            "split": "train",
            "input": candidate["input"],
            "target_plan": candidate["target_plan"],
            "human_review": {
                "decision": "accept",
                "reviewer_id": reviewer_id,
                "reviewed_at": reviewed_at,
                "target_plan_sha256": candidate["target_plan_sha256"],
                "notes": str(notes or "").strip(),
            },
            "provenance": {
                "source_kind": "live_dialogue_strict_review",
                "source_id": candidate["provenance"]["source_id"],
                "source_sha256": candidate["provenance"]["source_sha256"],
                "benchmark_origin": "none",
            },
        }
        unit = v75._strict_units([accepted_row], v75_contract)[0]
        failures = v75._unit_rejection_reasons(unit, v75_contract, False, protected_inputs)
        if failures:
            raise ValueError("accepted row failed V75 gates: " + ",".join(failures))
        if pending_certification:
            append_jsonl(manifest_path, pending_certification)
        append_jsonl(strict_annotation_path, accepted_row)

    review_record = {
        "schema": "uruha_planner_supervision_review_v76",
        "candidate_id": candidate["id"],
        "decision": decision,
        "scenario_family": scenario_family,
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "target_plan_sha256": candidate["target_plan_sha256"],
        "source_id": candidate["provenance"]["source_id"],
        "notes": str(notes or "").strip(),
        "strict_annotation_written": accepted_row is not None,
    }
    append_jsonl(review_path, review_record)
    return {"review": review_record, "accepted_row": accepted_row}
