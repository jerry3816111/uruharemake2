#!/usr/bin/env python3
"""Analyze the corrected frozen V87.2 candidate-gate regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v87 as v87_analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_2 as v872
import run_rightbrain_forbidden_projection_v87 as v87_runner
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_2_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize(rows, metadata):
    summary = v87_analyzer.summarize(rows, metadata)
    summary.update(
        {
            "control_gate_accept_count": sum(row["conditions"][v87.C0]["accepted"] for row in rows),
            "treatment_gate_accept_count": sum(row["conditions"][v87.T1]["accepted"] for row in rows),
            "required_contract_match_count": sum(row["required_contract_matches"] for row in rows),
            "fixed_runtime_settings_match_count": sum(row["fixed_runtime_settings_match"] for row in rows),
        }
    )
    return summary


def decision(contract, integrity, summary):
    if not integrity:
        return "inconclusive_integrity_failure", {}
    gates = contract["advance_gates"]
    checks = {
        "required_contracts": summary["required_contract_match_count"] == gates["required_contract_match_count_exact"],
        "control_accepts": summary["control_gate_accept_count"] == gates["control_gate_accept_count_exact"],
        "treatment_accepts": summary["treatment_gate_accept_count"] == gates["treatment_gate_accept_count_exact"],
        "recovered_conflicts": summary["recovered_conflict_only_rejection_count"] == gates["recovered_conflict_only_rejection_count_exact"],
        "no_new_rejections": summary["new_rejection_count"] <= gates["new_rejection_count_max"],
        "nonconflict_identity": summary["nonconflict_decision_identity_rate"] >= gates["nonconflict_decision_identity_rate_min"],
        "projected_marker_count": summary["projected_marker_count"] == gates["projected_marker_count_exact"],
        "projection_scope": summary["projection_scope_mismatch_count"] <= gates["projection_scope_mismatch_count_max"],
        "reply_hashes": summary["reply_hash_mismatch_count"] <= gates["reply_hash_mismatch_count_max"],
        "hard_markers": summary["hard_marker_regression_count"] <= gates["hard_marker_regression_count_max"],
    }
    if all(checks.values()):
        return contract["authorizations"]["on_pass"], checks
    if summary["new_rejection_count"] > 0 or summary["treatment_gate_accept_count"] < summary["control_gate_accept_count"]:
        return "stop_forbidden_conflict_projection_hypothesis", checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(contract, stored_rows, metadata, expected_rows, source_checks):
    fixed = contract["fixed_runtime_settings"]
    integrity_checks = {
        "sources": all(source_checks.values()),
        "preflight": metadata.get("preflight", {}).get("passed") is True,
        "case_count": len(stored_rows) == len(expected_rows) == int(contract["scope"]["case_count"]),
        "evaluation_count": int(metadata.get("evaluation_count", -1)) == int(contract["scope"]["expected_evaluation_count"]),
        "deterministic_recalculation": stored_rows == expected_rows,
        "fixed_settings_recorded": metadata.get("fixed_runtime_settings") == fixed,
        "fixed_settings_applied": all(row.get("fixed_runtime_settings_match") is True for row in stored_rows),
        "runtime_flags_restored": metadata.get("runtime_flags_restored") is True,
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
        "schema": "uruha_rightbrain_forbidden_projection_analysis_v87_2",
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
            "# V87.2 Corrected Forbidden-Conflict Projection Regression",
            "",
            f"- Decision: `{report['decision']}`",
            f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
            f"- Model calls: {summary['model_call_count']}",
            "",
            "| Metric | Result |",
            "|---|---:|",
            f"| Required contract match | {summary['required_contract_match_count']}/12 |",
            f"| Control gate accept | {summary['control_gate_accept_count']}/12 |",
            f"| Treatment gate accept | {summary['treatment_gate_accept_count']}/12 |",
            f"| Recovered conflict-only rejections | {summary['recovered_conflict_only_rejection_count']} |",
            f"| New rejections | {summary['new_rejection_count']} |",
            f"| Nonconflict decision identity | {summary['nonconflict_decision_identity_rate']:.1%} |",
            f"| Projected stale markers | {summary['projected_marker_count']} |",
            f"| Projection scope mismatches | {summary['projection_scope_mismatch_count']} |",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87_2.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87_2.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    stored_rows = v76.load_jsonl(local["paired_rows"])
    metadata = load_json(local["run_metadata"])
    source_checks = v87.verify_sources(contract, ROOT)
    packets, raw_rows, candidates = v87_runner.load_sources(contract)
    expected_rows = v872.evaluate_all(RightBrain(load_model=False), packets, raw_rows, candidates, contract)
    report = analyze(contract, stored_rows, metadata, expected_rows, source_checks)
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
