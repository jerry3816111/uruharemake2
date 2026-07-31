#!/usr/bin/env python3
"""Aggregate privacy-bounded observe-only forbidden-projection evidence from web logs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from project_paths import (
    RIGHTBRAIN_FORBIDDEN_PROJECTION_LIVE_EVIDENCE_REPORT_JSON_PATH,
    RIGHTBRAIN_FORBIDDEN_PROJECTION_LIVE_EVIDENCE_REPORT_MD_PATH,
    WEB_CONVERSATION_LOG_JSONL_PATH,
)


DEFAULT_MIN_ACTIVE_CONFLICT_TURNS = 20
DEFAULT_MIN_ACTIVE_SESSIONS = 5
DEFAULT_MIN_RECOVERED_TURNS = 5
DEFAULT_MAX_SHADOW_ELAPSED_MILLISECONDS = 25.0
RAW_BEARING_KEYS = {
    "candidate",
    "raw_candidate",
    "text",
    "marker",
    "markers",
    "original_markers",
    "effective_markers",
    "visible_reply",
}


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return [], {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "size_bytes": 0,
            "invalid_line_count": 0,
            "nonempty_line_count": 0,
        }
    raw_bytes = path.read_bytes()
    rows = []
    invalid = 0
    nonempty = 0
    for line in raw_bytes.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        nonempty += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            invalid += 1
    return rows, {
        "path": str(path),
        "exists": True,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "size_bytes": len(raw_bytes),
        "invalid_line_count": invalid,
        "nonempty_line_count": nonempty,
    }


def _contains_raw_bearing_key(value):
    if isinstance(value, dict):
        return any(
            str(key).lower() in RAW_BEARING_KEYS or _contains_raw_bearing_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_raw_bearing_key(child) for child in value)
    return False


def extract_observation(record):
    logic = record.get("logic") or {}
    shadow = logic.get("model_surface_forbidden_projection_shadow") or {}
    if shadow.get("schema") != "uruha_rightbrain_forbidden_projection_shadow_v89":
        return None
    assistant_reply = str(record.get("assistant_reply") or "").strip()
    visible_hash = hashlib.sha256(assistant_reply.encode("utf-8")).hexdigest()
    comparisons = shadow.get("candidate_comparisons") or []
    return {
        "session_id": str(record.get("session_id") or ""),
        "turn_index": record.get("turn_index"),
        "status": str(shadow.get("status") or "unknown"),
        "enabled": bool(shadow.get("enabled")),
        "production_projection_enabled": bool(shadow.get("production_projection_enabled")),
        "candidate_count": int(shadow.get("candidate_count") or 0),
        "projected_marker_count": int(shadow.get("projected_marker_count") or 0),
        "recovered_candidate_count": int(shadow.get("recovered_candidate_count") or 0),
        "new_rejection_count": int(shadow.get("new_rejection_count") or 0),
        "changes_user_visible_reply": shadow.get("changes_user_visible_reply"),
        "extra_model_call_count": int(shadow.get("extra_model_call_count") or 0),
        "projection_scope_matches": shadow.get("projection_scope_matches"),
        "visible_reply_hash_matches": shadow.get("visible_reply_sha256") == visible_hash,
        "candidate_comparison_count": len(comparisons),
        "privacy_payload_clean": not _contains_raw_bearing_key(shadow),
        "elapsed_milliseconds": shadow.get("elapsed_milliseconds"),
    }


def build_report(
    records,
    *,
    source_meta=None,
    min_active_conflict_turns=DEFAULT_MIN_ACTIVE_CONFLICT_TURNS,
    min_active_sessions=DEFAULT_MIN_ACTIVE_SESSIONS,
    min_recovered_turns=DEFAULT_MIN_RECOVERED_TURNS,
    max_shadow_elapsed_milliseconds=DEFAULT_MAX_SHADOW_ELAPSED_MILLISECONDS,
):
    raw_observations = [
        observation
        for record in records
        if (observation := extract_observation(record)) is not None
    ]
    keyed_observations = {}
    unkeyed_observations = []
    duplicate_shadow_traces = 0
    for observation in raw_observations:
        session_id = observation["session_id"]
        turn_index = observation["turn_index"]
        if not session_id or turn_index is None:
            unkeyed_observations.append(observation)
            continue
        key = (session_id, str(turn_index))
        if key in keyed_observations:
            duplicate_shadow_traces += 1
        keyed_observations[key] = observation
    observations = [*keyed_observations.values(), *unkeyed_observations]
    active = [row for row in observations if row["status"] == "active"]
    active_sessions = {row["session_id"] for row in active if row["session_id"]}
    recovered_turns = sum(row["recovered_candidate_count"] > 0 for row in active)
    privacy_violations = sum(not row["privacy_payload_clean"] for row in observations)
    visible_violations = sum(
        row["changes_user_visible_reply"] is not False or not row["visible_reply_hash_matches"]
        for row in observations
    )
    extra_calls = sum(row["extra_model_call_count"] for row in observations)
    new_rejections = sum(row["new_rejection_count"] for row in active)
    scope_mismatches = sum(row["projection_scope_matches"] is not True for row in active)
    production_projection_enabled = sum(
        row["production_projection_enabled"] for row in observations
    )
    elapsed = [
        float(row["elapsed_milliseconds"])
        for row in observations
        if isinstance(row.get("elapsed_milliseconds"), (int, float))
    ]
    maximum_elapsed = max(elapsed, default=None)
    summary = {
        "logged_record_count": len(records),
        "raw_shadow_trace_count": len(raw_observations),
        "shadow_trace_count": len(observations),
        "duplicate_shadow_trace_count": duplicate_shadow_traces,
        "status_counts": dict(sorted(Counter(row["status"] for row in observations).items())),
        "active_conflict_turn_count": len(active),
        "active_session_count": len(active_sessions),
        "candidate_comparison_count": sum(row["candidate_comparison_count"] for row in active),
        "recovered_turn_count": recovered_turns,
        "recovered_candidate_count": sum(row["recovered_candidate_count"] for row in active),
        "recovered_turn_rate": _safe_rate(recovered_turns, len(active)),
        "new_rejection_count": new_rejections,
        "visible_output_violation_count": visible_violations,
        "extra_model_call_count": extra_calls,
        "scope_mismatch_count": scope_mismatches,
        "production_projection_enabled_count": production_projection_enabled,
        "privacy_violation_count": privacy_violations,
        "maximum_shadow_elapsed_milliseconds": maximum_elapsed,
    }
    safety_gate = {
        "shadow_never_changes_visible_output": visible_violations == 0,
        "zero_extra_model_calls": extra_calls == 0,
        "zero_new_rejections": new_rejections == 0,
        "projection_scope_matches": scope_mismatches == 0,
        "production_projection_never_enabled": production_projection_enabled == 0,
        "privacy_payload_clean": privacy_violations == 0,
        "shadow_overhead_within_budget": (
            maximum_elapsed is None
            or maximum_elapsed <= float(max_shadow_elapsed_milliseconds)
        ),
        "valid_jsonl": int((source_meta or {}).get("invalid_line_count") or 0) == 0,
    }
    evidence_gate = {
        "enough_active_conflict_turns": len(active) >= int(min_active_conflict_turns),
        "enough_active_sessions": len(active_sessions) >= int(min_active_sessions),
        "enough_recovered_turns": recovered_turns >= int(min_recovered_turns),
    }
    safety_passed = all(safety_gate.values())
    review_ready = safety_passed and all(evidence_gate.values())
    if not safety_passed:
        status = "blocked_by_shadow_safety_failure"
    elif review_ready:
        status = "ready_for_limited_activation_review"
    elif observations:
        status = "collecting_live_shadow_evidence"
    else:
        status = "waiting_for_live_shadow_data"
    return {
        "schema": "uruha_rightbrain_forbidden_projection_live_evidence_v89",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "observe_only_web_conversation_shadow",
        "source_meta": source_meta or {},
        "thresholds": {
            "min_active_conflict_turns": int(min_active_conflict_turns),
            "min_active_sessions": int(min_active_sessions),
            "min_recovered_turns": int(min_recovered_turns),
            "max_shadow_elapsed_milliseconds": float(max_shadow_elapsed_milliseconds),
        },
        "status": status,
        "summary": summary,
        "safety_gate": safety_gate,
        "evidence_gate": evidence_gate,
        "safety_gate_passed": safety_passed,
        "limited_activation_review_ready": review_ready,
        "production_default_enable_authorized": False,
        "persona_fidelity_claim_authorized": False,
        "research_boundary": (
            "Only V89 observe-only traces from real web conversation logs count. Readiness permits a separate "
            "limited activation review only; it never enables the projection, changes visible replies, or supports "
            "public-persona fidelity claims by itself."
        ),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# RightBrain Forbidden Projection Live Evidence",
        "",
        f"- Status: `{report['status']}`",
        f"- Limited activation review ready: `{report['limited_activation_review_ready']}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Logged records | {summary['logged_record_count']} |",
        f"| V89 shadow traces | {summary['shadow_trace_count']} |",
        f"| Duplicate shadow traces ignored | {summary['duplicate_shadow_trace_count']} |",
        f"| Active conflict turns | {summary['active_conflict_turn_count']} |",
        f"| Active sessions | {summary['active_session_count']} |",
        f"| Recovered turns | {summary['recovered_turn_count']} |",
        f"| Recovery rate | {_fmt_pct(summary['recovered_turn_rate'])} |",
        f"| New rejections | {summary['new_rejection_count']} |",
        f"| Visible-output violations | {summary['visible_output_violation_count']} |",
        f"| Extra model calls | {summary['extra_model_call_count']} |",
        f"| Production projection enabled | {summary['production_projection_enabled_count']} |",
        f"| Privacy violations | {summary['privacy_violation_count']} |",
        "",
        report["research_boundary"],
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-log", default=WEB_CONVERSATION_LOG_JSONL_PATH)
    parser.add_argument(
        "--output-json",
        default=RIGHTBRAIN_FORBIDDEN_PROJECTION_LIVE_EVIDENCE_REPORT_JSON_PATH,
    )
    parser.add_argument(
        "--output-md",
        default=RIGHTBRAIN_FORBIDDEN_PROJECTION_LIVE_EVIDENCE_REPORT_MD_PATH,
    )
    parser.add_argument("--min-active-conflict-turns", type=int, default=DEFAULT_MIN_ACTIVE_CONFLICT_TURNS)
    parser.add_argument("--min-active-sessions", type=int, default=DEFAULT_MIN_ACTIVE_SESSIONS)
    parser.add_argument("--min-recovered-turns", type=int, default=DEFAULT_MIN_RECOVERED_TURNS)
    parser.add_argument(
        "--max-shadow-elapsed-milliseconds",
        type=float,
        default=DEFAULT_MAX_SHADOW_ELAPSED_MILLISECONDS,
    )
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    records, source_meta = load_jsonl(args.web_log)
    report = build_report(
        records,
        source_meta=source_meta,
        min_active_conflict_turns=args.min_active_conflict_turns,
        min_active_sessions=args.min_active_sessions,
        min_recovered_turns=args.min_recovered_turns,
        max_shadow_elapsed_milliseconds=args.max_shadow_elapsed_milliseconds,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_md).write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "summary": report["summary"],
                "safety_gate": report["safety_gate"],
                "evidence_gate": report["evidence_gate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if args.require_ready and not report["limited_activation_review_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
