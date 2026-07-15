#!/usr/bin/env python3
"""Analyze the preregistered zero-model V59/V60 matched replay."""

import json
import math
from collections import Counter
from pathlib import Path

from analyze_event_role_governor_v59_holdout import (
    BLOCKING_RELATIONS,
    DIRECT_FAMILY,
    RELATION_BY_FAMILY,
    summarize_compiler,
    summarize_state,
)
from run_predicate_morphology_v60_development import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_preregistration.json"
LOCK_PATH = ROOT / "configs" / "predicate_morphology_v60_replay_harness_lock.json"
ROLE_CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "predicate_morphology_v60_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "predicate_morphology_v60_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "predicate_morphology_v60_development_analysis.md"


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def summarize_v60_event_roles(raw, dataset, role_config):
    cases = {case["id"]: case for case in dataset["cases"]}
    contracts = role_config["expected_event_roles_by_family"]
    expected_relations = []
    direct_false_positives = []
    direct_rows = []
    slot_rows = []
    family_relation_counts = Counter()
    family_relation_passes = Counter()

    for row in raw["target_rows"]:
        case = cases[row["case_id"]]
        contract = contracts.get(case["family"])
        if contract is None:
            continue
        graph = row["candidate_state"].get("v60_event_role_graph") or {}
        relation_types = set(graph.get("relation_types") or [])
        expected_relation = contract["relation_type"]
        if expected_relation is not None:
            passed = expected_relation in relation_types
            expected_relations.append(
                {
                    "case_id": row["case_id"],
                    "target_id": row["target_id"],
                    "family": case["family"],
                    "expected_relation": expected_relation,
                    "observed_relations": sorted(relation_types),
                    "passed": passed,
                }
            )
            family_relation_counts[case["family"]] += 1
            family_relation_passes[case["family"]] += passed
        if case["family"] == DIRECT_FAMILY:
            direct = bool(graph.get("direct_focus_request"))
            direct_rows.append(
                {
                    "case_id": row["case_id"],
                    "target_id": row["target_id"],
                    "direct_focus_request": direct,
                }
            )
            blocking = sorted(relation_types & BLOCKING_RELATIONS)
            if blocking:
                direct_false_positives.append(
                    {
                        "case_id": row["case_id"],
                        "target_id": row["target_id"],
                        "blocking_relations": blocking,
                    }
                )

        slot_checks = {
            "relation": (
                relation_types == {expected_relation}
                if expected_relation is not None
                else not relation_types
            ),
            "event_owner": graph.get("event_owner")
            in set(contract["event_owner_allowed"]),
            "directive_governor": graph.get("directive_governor")
            == contract["directive_governor"],
            "event_time": graph.get("event_time")
            in set(contract["event_time_allowed"]),
            "direct_focus_request": bool(graph.get("direct_focus_request"))
            == contract["direct_focus_request"],
        }
        slot_rows.append(
            {
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "family": case["family"],
                "checks": slot_checks,
                "passed_slot_count": sum(slot_checks.values()),
                "slot_count": len(slot_checks),
            }
        )

    detected = sum(row["passed"] for row in expected_relations)
    slot_passes = sum(row["passed_slot_count"] for row in slot_rows)
    slot_count = sum(row["slot_count"] for row in slot_rows)
    return {
        "expected_relation_target_count": len(expected_relations),
        "expected_relation_detected_count": detected,
        "expected_relation_coverage": _ratio(detected, len(expected_relations)),
        "relation_family_groups": {
            family: {
                "detected_count": family_relation_passes[family],
                "target_count": family_relation_counts[family],
                "coverage": _ratio(
                    family_relation_passes[family], family_relation_counts[family]
                ),
            }
            for family in RELATION_BY_FAMILY
        },
        "relation_failure_rows": [row for row in expected_relations if not row["passed"]],
        "contrast_blocking_relation_target_count": len(direct_false_positives),
        "contrast_blocking_relation_targets": direct_false_positives,
        "direct_focus_request_detected_count": sum(
            row["direct_focus_request"] for row in direct_rows
        ),
        "direct_focus_request_target_count": len(direct_rows),
        "direct_focus_request_recall": _ratio(
            sum(row["direct_focus_request"] for row in direct_rows), len(direct_rows)
        ),
        "role_slot_correct_count": slot_passes,
        "role_slot_count": slot_count,
        "role_slot_accuracy": _ratio(slot_passes, slot_count),
        "role_slot_failure_rows": [
            row for row in slot_rows if row["passed_slot_count"] != row["slot_count"]
        ],
    }


def _same(actual, expected):
    if isinstance(expected, float):
        return math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
    return actual == expected


def analyze(raw, dataset, config, lock, role_config):
    frozen = config["frozen_inputs"]
    if len(raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V60 target replay incomplete")
    if len(raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V60 case replay incomplete")
    if raw["model_calls"] != 0 or raw["paid_api_used"]:
        raise ValueError("V60 replay violated zero-model policy")
    if raw["physical_vrm_actions_executed"] != 0:
        raise ValueError("V60 replay executed a physical VRM action")
    if tuple(raw["conditions"]) != (CONTROL, CANDIDATE):
        raise ValueError("V60 replay condition order drift")
    if tuple(lock["conditions"]) != (CONTROL, CANDIDATE):
        raise ValueError("V60 replay lock condition order drift")

    control_state = summarize_state(raw, dataset, "control")
    candidate_state = summarize_state(raw, dataset, "candidate")
    control_compiler = summarize_compiler(raw, dataset, "control")
    candidate_compiler = summarize_compiler(raw, dataset, "candidate")
    event_roles = summarize_v60_event_roles(raw, dataset, role_config)
    control_targets = {tuple(row) for row in control_state["correct_target_keys"]}
    candidate_targets = {tuple(row) for row in candidate_state["correct_target_keys"]}
    control_cases = set(control_compiler["correct_case_ids"])
    candidate_cases = set(candidate_compiler["correct_case_ids"])
    comparison = {
        "state_correct_count_delta": candidate_state["correct_count"]
        - control_state["correct_count"],
        "state_fix_count": len(candidate_targets - control_targets),
        "state_fix_target_keys": sorted(
            [list(key) for key in candidate_targets - control_targets]
        ),
        "state_regression_count": len(control_targets - candidate_targets),
        "state_regression_target_keys": sorted(
            [list(key) for key in control_targets - candidate_targets]
        ),
        "ordered_exact_count_delta": candidate_compiler["ordered_exact_count"]
        - control_compiler["ordered_exact_count"],
        "case_fix_count": len(candidate_cases - control_cases),
        "case_fix_ids": sorted(candidate_cases - control_cases),
        "case_regression_count": len(control_cases - candidate_cases),
        "case_regression_ids": sorted(control_cases - candidate_cases),
    }

    expected = config["expected_replay_effect"]
    checks = {
        "control_state_correct_count": control_state["correct_count"]
        == frozen["v59_correct_commitment_count"],
        "control_ordered_exact_count": control_compiler["ordered_exact_count"]
        == frozen["v59_ordered_exact_count"],
        "control_false_action_count": control_compiler["false_action_case_count"]
        == frozen["v59_false_action_case_count"],
        "state_correct_count": candidate_state["correct_count"]
        == expected["correct_commitment_count"],
        "state_commitment_accuracy": _same(
            candidate_state["commitment_accuracy"], expected["commitment_accuracy"]
        ),
        "state_requested_precision": _same(
            candidate_state["requested_precision"], expected["requested_precision"]
        ),
        "state_requested_recall": _same(
            candidate_state["requested_recall"], expected["requested_recall"]
        ),
        "compiler_ordered_exact_count": candidate_compiler["ordered_exact_count"]
        == expected["ordered_exact_count"],
        "compiler_ordered_exact_accuracy": _same(
            candidate_compiler["ordered_exact_accuracy"],
            expected["ordered_exact_accuracy"],
        ),
        "compiler_false_actions": candidate_compiler["false_action_case_count"]
        == expected["false_action_case_count"],
        "compiler_no_action_specificity": _same(
            candidate_compiler["no_action_specificity"],
            expected["no_action_specificity"],
        ),
        "compiler_required_call_recall": _same(
            candidate_compiler["required_call_recall"],
            expected["required_call_recall"],
        ),
        "event_role_expected_relations": event_roles[
            "expected_relation_detected_count"
        ]
        == expected["expected_relation_detected_count"],
        "event_role_relation_targets": event_roles["expected_relation_target_count"]
        == expected["expected_relation_target_count"],
        "event_role_direct_focus_count": event_roles[
            "direct_focus_request_detected_count"
        ]
        == expected["direct_focus_request_detected_count"],
        "event_role_direct_focus_targets": event_roles[
            "direct_focus_request_target_count"
        ]
        == expected["direct_focus_request_target_count"],
        "event_role_slot_correct_count": event_roles["role_slot_correct_count"]
        == expected["role_slot_correct_count"],
        "event_role_slot_count": event_roles["role_slot_count"]
        == expected["role_slot_count"],
        "matched_state_fixes": comparison["state_fix_count"]
        == expected["state_fix_count"],
        "matched_state_regressions": comparison["state_regression_count"]
        == expected["state_regression_count"],
        "matched_case_fixes": comparison["case_fix_count"]
        == expected["case_fix_count"],
        "matched_case_regressions": comparison["case_regression_count"]
        == expected["case_regression_count"],
        "compiler_ungrounded_execution": candidate_compiler[
            "ungrounded_execution_count"
        ]
        == 0,
        "compiler_commitment_mutation": candidate_compiler[
            "commitment_mutation_count"
        ]
        == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_predicate_morphology_development_analysis_v60",
        "evidence_status": raw["evidence_status"],
        "control_condition": CONTROL,
        "candidate_condition": CANDIDATE,
        "control_state": control_state,
        "candidate_state": candidate_state,
        "control_compiler": control_compiler,
        "candidate_compiler": candidate_compiler,
        "event_role_replay": event_roles,
        "matched_comparison": comparison,
        "residual_state_failures": candidate_state["failure_rows"],
        "gates": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": (
            "authorize_second_fresh_v60_independent_holdout"
            if passed
            else "reject_v60_replay_and_diagnose_predicate_morphology"
        ),
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "complete_rightbrain_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{value:.2%}"


def render_markdown(report):
    control_state = report["control_state"]
    candidate_state = report["candidate_state"]
    control = report["control_compiler"]
    candidate = report["candidate_compiler"]
    roles = report["event_role_replay"]
    comparison = report["matched_comparison"]
    return "\n".join(
        [
            "# V60 predicate-morphology development replay",
            "",
            "This matched replay reused the frozen V59 model fallback and made zero model calls.",
            "",
            "| Metric | V59 control | V60 candidate |",
            "|---|---:|---:|",
            f"| State commitments | {control_state['correct_count']}/73 ({_pct(control_state['commitment_accuracy'])}) | {candidate_state['correct_count']}/73 ({_pct(candidate_state['commitment_accuracy'])}) |",
            f"| Ordered exact cases | {control['ordered_exact_count']}/72 ({_pct(control['ordered_exact_accuracy'])}) | {candidate['ordered_exact_count']}/72 ({_pct(candidate['ordered_exact_accuracy'])}) |",
            f"| False-action cases | {control['false_action_case_count']} | {candidate['false_action_case_count']} |",
            f"| V60 direct-request role recall | n/a | {roles['direct_focus_request_detected_count']}/{roles['direct_focus_request_target_count']} |",
            f"| V60 role-slot accuracy | n/a | {roles['role_slot_correct_count']}/{roles['role_slot_count']} ({_pct(roles['role_slot_accuracy'])}) |",
            "",
            f"- State fixes / regressions: {comparison['state_fix_count']} / {comparison['state_regression_count']}",
            f"- Case fixes / regressions: {comparison['case_fix_count']} / {comparison['case_regression_count']}",
            f"- Gate: {'PASS' if report['gates']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            "",
            "This consumed-data replay can authorize only a second fresh holdout, not runtime deployment.",
            "",
        ]
    )


def main():
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(
        load(DEFAULT_RAW),
        load(DATASET_PATH),
        load(CONFIG_PATH),
        load(LOCK_PATH),
        load(ROLE_CONFIG_PATH),
    )
    DEFAULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DEFAULT_MARKDOWN.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "gate_passed": report["gates"]["passed"],
                "state_correct": report["candidate_state"]["correct_count"],
                "ordered_exact": report["candidate_compiler"]["ordered_exact_count"],
                "false_actions": report["candidate_compiler"][
                    "false_action_case_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
