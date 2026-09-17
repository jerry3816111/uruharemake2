#!/usr/bin/env python3
"""Audit the one locked B46 case against the rubric frozen before generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from p3_product_comparison import canonical_sha256, write_new_json


DIMENSIONS = [
    "required_semantic_acts_present",
    "forbidden_semantic_acts_absent",
    "source_grounding_correct",
    "uncertainty_boundary_respected",
    "natural_japanese_surface",
]
CONDITION_ROWS = {
    "isolated_product": "product_turns",
    "full_history_direct": "direct_turns",
}


class AuditError(ValueError):
    pass


def _read(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reply(row: dict[str, Any], condition: str) -> tuple[str, str]:
    if condition == "isolated_product":
        return str(row["visible_reply"]), str(row["visible_reply_sha256"])
    final = row.get("final") or {}
    return str(final["content"]), str(final["content_sha256"])


def _validate_finding_map(
    findings: Any,
    expected_acts: list[str],
    reply: str,
    field: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(findings, dict) or set(findings) != set(expected_acts):
        raise AuditError(f"{field}_act_set_mismatch")
    clean: dict[str, dict[str, Any]] = {}
    for act in expected_acts:
        finding = findings[act]
        if not isinstance(finding, dict) or set(finding) != {"present", "evidence_quote", "rationale"}:
            raise AuditError(f"{field}_finding_shape_invalid")
        if not isinstance(finding["present"], bool) or not str(finding["rationale"]).strip():
            raise AuditError(f"{field}_finding_value_invalid")
        quote = str(finding["evidence_quote"])
        if quote and quote not in reply:
            raise AuditError(f"{field}_evidence_quote_not_in_reply")
        if finding["present"] and not quote:
            raise AuditError(f"{field}_present_without_quote")
        clean[act] = {
            "present": finding["present"],
            "evidence_quote": quote,
            "rationale": str(finding["rationale"]),
        }
    return clean


def build_audit(
    case_output_path: str | Path,
    source_path: str | Path,
    annotation_path: str | Path,
    adjudication_path: str | Path,
) -> dict[str, Any]:
    locked = _read(case_output_path)
    source = _read(source_path)
    annotations = _read(annotation_path)
    adjudication = _read(adjudication_path)

    bound = adjudication.get("bound_artifacts") or {}
    actual_hashes = {
        "case_output_sha256": _hash(case_output_path),
        "source_sha256": _hash(source_path),
        "annotation_sha256": _hash(annotation_path),
    }
    if bound != actual_hashes:
        raise AuditError("bound_artifact_hash_mismatch")
    if locked.get("schema") != "uruha_p3_b46_prospective_v3_case_output_lock_v1":
        raise AuditError("case_output_schema_invalid")
    if locked.get("status") != "case_output_lock_failed_retained":
        raise AuditError("case_output_status_invalid")
    if annotations.get("source_manifest_sha256") != actual_hashes["source_sha256"]:
        raise AuditError("annotation_source_binding_invalid")
    if adjudication.get("human_rater_evidence") is not False:
        raise AuditError("human_rater_boundary_invalid")
    if adjudication.get("generated_after_output_lock") is not True:
        raise AuditError("adjudication_timing_boundary_invalid")

    case_id = str(locked["case_id"])
    source_cases = {row["case_id"]: row for row in source.get("cases", [])}
    rubric_cases = {row["case_id"]: row for row in annotations.get("cases", [])}
    if case_id not in source_cases or case_id not in rubric_cases:
        raise AuditError("locked_case_missing_from_source_or_rubric")
    source_case = source_cases[case_id]
    rubric_case = rubric_cases[case_id]
    source_turns = {row["turn_id"]: row for row in source_case["turns"]}
    rubric_turns = {row["turn_id"]: row for row in rubric_case["turns"]}

    locked_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for condition, field in CONDITION_ROWS.items():
        rows = locked.get(field)
        if not isinstance(rows, list) or len(rows) != 4:
            raise AuditError("locked_condition_turn_shape_invalid")
        for row in rows:
            turn_id = str(row["turn_id"])
            reply, reply_sha256 = _reply(row, condition)
            if canonical_sha256(reply) != reply_sha256:
                raise AuditError("visible_reply_hash_invalid")
            if turn_id not in source_turns or turn_id not in rubric_turns:
                raise AuditError("locked_turn_missing_from_source_or_rubric")
            locked_rows[(condition, turn_id)] = {
                "reply": reply,
                "reply_sha256": reply_sha256,
                "surface_contract": row["surface_contract"],
            }

    rows = adjudication.get("rows")
    if not isinstance(rows, list) or len(rows) != 8:
        raise AuditError("adjudication_row_count_invalid")
    by_key = {(str(row.get("condition")), str(row.get("turn_id"))): row for row in rows}
    if len(by_key) != 8 or set(by_key) != set(locked_rows):
        raise AuditError("adjudication_key_set_invalid")

    critical_contract = set((annotations.get("scoring_contract") or {}).get("critical_failures", []))
    result_rows: list[dict[str, Any]] = []
    for condition in CONDITION_ROWS:
        for turn in source_case["turns"]:
            turn_id = turn["turn_id"]
            row = by_key[(condition, turn_id)]
            locked_row = locked_rows[(condition, turn_id)]
            if row.get("visible_reply_sha256") != locked_row["reply_sha256"]:
                raise AuditError("adjudication_reply_hash_mismatch")
            rubric = rubric_turns[turn_id]
            required = _validate_finding_map(
                row.get("required_act_findings"),
                rubric["required_semantic_acts"],
                locked_row["reply"],
                "required",
            )
            forbidden = _validate_finding_map(
                row.get("forbidden_act_findings"),
                rubric["forbidden_semantic_acts"],
                locked_row["reply"],
                "forbidden",
            )
            scores = row.get("scores")
            if not isinstance(scores, dict) or list(scores) != DIMENSIONS:
                raise AuditError("dimension_score_shape_invalid")
            if any(value not in (0, 1) or isinstance(value, bool) for value in scores.values()):
                raise AuditError("dimension_score_value_invalid")
            if scores[DIMENSIONS[0]] != int(all(item["present"] for item in required.values())):
                raise AuditError("required_dimension_inconsistent")
            if scores[DIMENSIONS[1]] != int(not any(item["present"] for item in forbidden.values())):
                raise AuditError("forbidden_dimension_inconsistent")
            evidence = row.get("dimension_evidence")
            if not isinstance(evidence, dict) or set(evidence) != set(DIMENSIONS[2:]):
                raise AuditError("dimension_evidence_shape_invalid")
            for dimension in DIMENSIONS[2:]:
                item = evidence[dimension]
                if not isinstance(item, dict) or set(item) != {"evidence_quote", "rationale"}:
                    raise AuditError("dimension_evidence_item_invalid")
                quote = str(item["evidence_quote"])
                if quote and quote not in locked_row["reply"]:
                    raise AuditError("dimension_evidence_quote_not_in_reply")
                if not str(item["rationale"]).strip():
                    raise AuditError("dimension_evidence_rationale_missing")
            critical = row.get("critical_failures")
            if not isinstance(critical, list) or len(set(critical)) != len(critical) or not set(critical).issubset(critical_contract):
                raise AuditError("critical_failure_invalid")
            if "non_japanese_visible_reply" in critical and scores["natural_japanese_surface"] != 0:
                raise AuditError("non_japanese_critical_failure_inconsistent")
            result_rows.append({
                "case_id": case_id,
                "condition": condition,
                "turn_id": turn_id,
                "source_content": turn["content"],
                "visible_reply": locked_row["reply"],
                "visible_reply_sha256": locked_row["reply_sha256"],
                "rubric": rubric,
                "required_act_findings": required,
                "forbidden_act_findings": forbidden,
                "dimension_evidence": evidence,
                "scores": scores,
                "turn_score": sum(scores.values()),
                "critical_failures": critical,
            })

    condition_summaries: dict[str, Any] = {}
    for condition in CONDITION_ROWS:
        condition_rows = [row for row in result_rows if row["condition"] == condition]
        primary = next(row for row in condition_rows if row["turn_id"].endswith("-u4"))
        critical = [
            {"turn_id": row["turn_id"], "code": code}
            for row in condition_rows
            for code in row["critical_failures"]
        ]
        totals = {dimension: sum(row["scores"][dimension] for row in condition_rows) for dimension in DIMENSIONS}
        condition_summaries[condition] = {
            "dimension_totals": totals,
            "total_score": sum(totals.values()),
            "maximum_score": 20,
            "u4_score": primary["turn_score"],
            "critical_failures": critical,
            "case_pass": primary["turn_score"] == 5 and not critical,
        }

    missing_cases = [
        {"case_id": row["case_id"], "status": "not_generated", "score": None}
        for row in source["cases"]
        if row["case_id"] != case_id
    ]
    return {
        "schema": "uruha_p3_b47_retained_case_rubric_audit_v1",
        "phase": "P3-B47",
        "status": "retained_case01_developer_proxy_audit_complete_no_batch_conclusion",
        "bound_artifacts": {**actual_hashes, "adjudication_sha256": _hash(adjudication_path)},
        "case_id": case_id,
        "human_rater_evidence": False,
        "formal_holdout_evidence": False,
        "rows": result_rows,
        "condition_summaries": condition_summaries,
        "unavailable_cases": missing_cases,
        "batch_comparison_available": False,
        "condition_winner": None,
        "model_calls": 0,
        "network_calls": 0,
        "claim_boundary": "Deterministic validation and aggregation of one post-lock developer-proxy adjudication against the rubric frozen before generation. It is not human preference evidence, a three-case comparison, formal holdout evidence, or a system advantage result.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-output", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--adjudication", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        payload = build_audit(args.case_output, args.source, args.annotations, args.adjudication)
    except (AuditError, KeyError, TypeError, json.JSONDecodeError) as exc:
        payload = {
            "schema": "uruha_p3_b47_retained_case_rubric_audit_refusal_v1",
            "phase": "P3-B47",
            "status": "audit_refused",
            "contract_code": str(exc),
            "model_calls": 0,
            "network_calls": 0,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "retained_case01_developer_proxy_audit_complete_no_batch_conclusion" else 1


if __name__ == "__main__":
    raise SystemExit(main())
