#!/usr/bin/env python3
"""Analyze the frozen deterministic V87 candidate-gate regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import run_rightbrain_forbidden_projection_v87 as runner
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize(rows, metadata):
    count = len(rows)
    nonconflict = [row for row in rows if row["diagnosed_conflict_count"] == 0]
    return {
        "case_count": count,
        "evaluation_count": count * len(v87.CONDITIONS),
        "model_call_count": int(metadata.get("model_call_count") or 0),
        "control_gate_accept_rate": sum(row["conditions"][v87.C0]["accepted"] for row in rows) / max(1, count),
        "treatment_gate_accept_rate": sum(row["conditions"][v87.T1]["accepted"] for row in rows) / max(1, count),
        "recovered_conflict_only_rejection_count": sum(row["conflict_only_recovered"] for row in rows),
        "new_rejection_count": sum(bool(row["added_reasons"]) for row in rows),
        "nonconflict_decision_identity_rate": sum(row["nonconflict_decision_identical"] for row in nonconflict) / max(1, len(nonconflict)),
        "projected_marker_count": sum(row["conditions"][v87.T1]["dropped_marker_count"] for row in rows),
        "projection_scope_mismatch_count": sum(not row["projection_scope_matches"] for row in rows),
        "reply_hash_mismatch_count": sum(not row["reply_hash_matches"] for row in rows),
        "hard_marker_regression_count": int(metadata.get("hard_marker_regression_count") or 0),
    }


def decision(contract, integrity, summary):
    if not integrity:
        return "inconclusive_integrity_failure", {}
    gates = contract["advance_gates"]
    checks = {
        "treatment_gate_accept_rate": summary["treatment_gate_accept_rate"] >= gates["treatment_gate_accept_rate_min"],
        "recovered_conflicts": summary["recovered_conflict_only_rejection_count"] >= gates["recovered_conflict_only_rejection_count_min"],
        "no_new_rejections": summary["new_rejection_count"] <= gates["new_rejection_count_max"],
        "nonconflict_identity": summary["nonconflict_decision_identity_rate"] >= gates["nonconflict_decision_identity_rate_min"],
        "projected_marker_count": summary["projected_marker_count"] == gates["projected_marker_count_exact"],
        "projection_scope": summary["projection_scope_mismatch_count"] <= gates["projection_scope_mismatch_count_max"],
        "reply_hashes": summary["reply_hash_mismatch_count"] <= gates["reply_hash_mismatch_count_max"],
        "hard_markers": summary["hard_marker_regression_count"] <= gates["hard_marker_regression_count_max"],
    }
    if all(checks.values()):
        return contract["authorizations"]["on_pass"], checks
    failure = contract["failure_rule"]
    if (
        summary["recovered_conflict_only_rejection_count"] <= failure["recovered_conflict_only_rejection_count_max"]
        or summary["new_rejection_count"] >= failure["new_rejection_count_min"]
    ):
        return failure["decision"], checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(contract, stored_rows, metadata, expected_rows, source_checks):
    integrity_checks = {
        "sources": all(source_checks.values()),
        "preflight": metadata.get("preflight", {}).get("passed") is True,
        "case_count": len(stored_rows) == len(expected_rows) == int(contract["scope"]["case_count"]),
        "evaluation_count": int(metadata.get("evaluation_count") or 0) == int(contract["scope"]["expected_evaluation_count"]),
        "deterministic_recalculation": stored_rows == expected_rows,
        "zero_model_calls": int(metadata.get("model_call_count", -1)) == 0,
        "no_side_effects": (
            metadata.get("production_database_opened") is False
            and int(metadata.get("production_memory_write_count", -1)) == 0
            and int(metadata.get("physical_vrm_action_count", -1)) == 0
            and all(row.get("production_memory_write_count") == 0 and row.get("physical_vrm_action_count") == 0 for row in stored_rows)
        ),
    }
    integrity = all(integrity_checks.values())
    summary = summarize(stored_rows, metadata)
    final_decision, gate_checks = decision(contract, integrity, summary)
    return {
        "schema": "uruha_rightbrain_forbidden_projection_analysis_v87",
        "experiment_id": contract["experiment_id"],
        "decision": final_decision,
        "integrity_passed": integrity,
        "integrity_checks": integrity_checks,
        "summary": summary,
        "advance_gate_checks": gate_checks,
        "production_shadow_authorized": False,
        "production_default_enable_authorized": False,
        "training_data_authorized": False,
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# V87 Forbidden-Conflict Projection Regression",
            "",
            f"- Decision: `{report['decision']}`",
            f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
            f"- Model calls: {summary['model_call_count']}",
            "",
            "| Metric | Result |",
            "|---|---:|",
            f"| Control gate accept | {summary['control_gate_accept_rate']:.1%} |",
            f"| Treatment gate accept | {summary['treatment_gate_accept_rate']:.1%} |",
            f"| Recovered conflict-only rejections | {summary['recovered_conflict_only_rejection_count']} |",
            f"| New rejections | {summary['new_rejection_count']} |",
            f"| Nonconflict decision identity | {summary['nonconflict_decision_identity_rate']:.1%} |",
            f"| Projected stale markers | {summary['projected_marker_count']} |",
            f"| Reply hash mismatches | {summary['reply_hash_mismatch_count']} |",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    stored_rows = v76.load_jsonl(local["paired_rows"])
    metadata = load_json(local["run_metadata"])
    source_checks = v87.verify_sources(contract, ROOT)
    packets, raw_rows, candidates = runner.load_sources(contract)
    expected_rows = v87.evaluate_all(RightBrain(load_model=False), packets, raw_rows, candidates, contract)
    report = analyze(contract, stored_rows, metadata, expected_rows, source_checks)
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
