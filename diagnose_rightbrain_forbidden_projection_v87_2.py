#!/usr/bin/env python3
"""Diagnose the post-hoc V87.2 projection-scope mismatch."""

from __future__ import annotations

import json
from pathlib import Path

import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87


ROOT = Path(__file__).resolve().parent
ROWS_PATH = ROOT / "analysis/local_rightbrain_forbidden_projection_v87_2/paired_rows.jsonl"
CANDIDATES_PATH = ROOT / "analysis/local_planner_supervision_v76/candidates.jsonl"
FORMAL_REPORT_PATH = ROOT / "reports/rightbrain_forbidden_projection_v87_2.json"


def normalized_forbidden(values):
    return list(
        dict.fromkeys(
            str(value or "").strip()
            for value in values or []
            if str(value or "").strip()
        )
    )


def diagnose(rows, candidates, formal_report):
    candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
    mismatches = [row for row in rows if not row["projection_scope_matches"]]
    whitespace_only = 0
    unchanged_between_conditions = 0
    zero_projection = 0
    normalized_oracle_matches = 0
    whitespace_changed_marker_count = 0
    for row in mismatches:
        candidate = candidates_by_id[row["candidate_id"]]
        raw_forbidden = list(dict.fromkeys(candidate["target_plan"].get("must_avoid") or []))
        normalized = normalized_forbidden(raw_forbidden)
        changed = sum(
            str(value or "") != str(value or "").strip()
            for value in raw_forbidden
            if str(value or "").strip()
        )
        whitespace_changed_marker_count += changed
        whitespace_only += bool(changed) and len(raw_forbidden) == len(normalized)
        control = row["conditions"][v87.C0]
        treatment = row["conditions"][v87.T1]
        unchanged_between_conditions += (
            control["accepted"] == treatment["accepted"]
            and control["rejection_reasons"] == treatment["rejection_reasons"]
            and control["effective_forbidden_sha256"] == treatment["effective_forbidden_sha256"]
        )
        zero_projection += treatment["dropped_marker_count"] == 0
        normalized_oracle_matches += (
            treatment["effective_forbidden_sha256"] == v76.canonical_sha256(normalized)
        )
    false_positive_supported = bool(mismatches) and all(
        count == len(mismatches)
        for count in (
            whitespace_only,
            unchanged_between_conditions,
            zero_projection,
            normalized_oracle_matches,
        )
    )
    return {
        "schema": "uruha_rightbrain_forbidden_projection_diagnosis_v87_2",
        "diagnosis_type": "post_hoc_scope_oracle_audit_does_not_change_v87_2_decision",
        "formal_v87_2_decision": formal_report["decision"],
        "formal_scope_mismatch_count": formal_report["summary"]["projection_scope_mismatch_count"],
        "diagnosed_mismatch_count": len(mismatches),
        "mismatches_with_zero_projection": zero_projection,
        "mismatches_unchanged_between_conditions": unchanged_between_conditions,
        "mismatches_matching_normalized_oracle": normalized_oracle_matches,
        "whitespace_changed_marker_count": whitespace_changed_marker_count,
        "scope_mismatch_is_oracle_false_positive": false_positive_supported,
        "root_cause": (
            "The V87 scope oracle hashed raw must_avoid values, while the production gate strips surrounding "
            "whitespace in both control and treatment. One unchanged marker therefore produced a hash mismatch "
            "even though projection removed nothing and did not alter the decision."
        ),
        "next_falsifiable_step": (
            "Preregister V87.3 with an oracle that applies the production gate's existing whitespace "
            "normalization before comparing projected scope. Keep every runtime setting and outcome gate unchanged."
        ),
        "authorizations": {
            "v87_2_decision_override": False,
            "fresh_full_pipeline_holdout": False,
            "production_shadow": False,
            "production_default": False,
            "training_data": False,
        },
        "privacy": {
            "raw_marker_text_in_report": False,
            "candidate_or_session_ids_in_report": False,
        },
    }


def render_markdown(report):
    return "\n".join(
        [
            "# V87.2 Post-hoc Scope-Oracle Diagnosis",
            "",
            f"- Formal decision remains: `{report['formal_v87_2_decision']}`",
            f"- Formal scope mismatches: {report['formal_scope_mismatch_count']}",
            f"- Mismatches with zero projected markers: {report['mismatches_with_zero_projection']}",
            f"- Mismatches unchanged between conditions: {report['mismatches_unchanged_between_conditions']}",
            f"- Mismatches matching normalized oracle: {report['mismatches_matching_normalized_oracle']}",
            f"- Oracle false positive supported: **{'YES' if report['scope_mismatch_is_oracle_false_positive'] else 'NO'}**",
            "",
            "## Root Cause",
            "",
            report["root_cause"],
            "",
            "This diagnosis does not override V87.2 or authorize production use.",
            "",
        ]
    )


def main():
    rows = v76.load_jsonl(ROWS_PATH)
    candidates = v76.load_jsonl(CANDIDATES_PATH)
    formal_report = json.loads(FORMAL_REPORT_PATH.read_text(encoding="utf-8"))
    report = diagnose(rows, candidates, formal_report)
    json_path = ROOT / "reports/rightbrain_forbidden_projection_v87_2_diagnosis.json"
    md_path = ROOT / "reports/rightbrain_forbidden_projection_v87_2_diagnosis.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "oracle_false_positive": report["scope_mismatch_is_oracle_false_positive"],
                "formal_decision": report["formal_v87_2_decision"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
