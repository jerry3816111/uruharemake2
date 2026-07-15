#!/usr/bin/env python3
"""Analyze the preregistered matched V59/V60 independent holdout."""

import json
import math
from collections import Counter
from pathlib import Path

from analyze_event_role_governor_v59_holdout import summarize_compiler, summarize_state
from run_predicate_morphology_v60_independent_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "predicate_morphology_v60_independent_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_analysis.md"


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _target_id(frame):
    return f"{frame['domain']}.{frame['value']}"


def _two_sided_exact_mcnemar(case_fixes, case_regressions):
    discordant = case_fixes + case_regressions
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, value)
        for value in range(min(case_fixes, case_regressions) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def summarize_morphology(raw, dataset, config):
    cases = {case["id"]: case for case in dataset["cases"]}
    contracts = config["expected_morphology_by_family"]
    slot_rows = []
    family_slots = Counter()
    family_passes = Counter()
    completed_relation_rows = []
    polite_relation_rows = []
    embedded_relation_rows = []
    omitted_direct_rows = []
    full_direct_rows = []
    negative_relation_false_positives = []
    nonbenefactive_relation_false_positives = []

    for row in raw["target_rows"]:
        case = cases[row["case_id"]]
        contract = contracts.get(case["family"])
        if contract is None:
            continue
        graph = row["candidate_state"].get("v60_event_role_graph") or {}
        morphology = graph.get("v60_predicate_morphology") or {}
        relation_types = sorted(set(graph.get("relation_types") or []))
        checks = {
            "predicate_force": morphology.get("predicate_force")
            == contract["predicate_force"],
            "event_aspect": morphology.get("event_aspect")
            == contract["event_aspect"],
            "event_owner": graph.get("event_owner") == contract["event_owner"],
            "request_governor": graph.get("directive_governor")
            == contract["request_governor"],
            "direct_focus_request": bool(graph.get("direct_focus_request"))
            == contract["direct_focus_request"],
            "relation_types": relation_types == sorted(contract["relation_types"]),
        }
        slot_rows.append(
            {
                "case_id": row["case_id"],
                "target_id": row["target_id"],
                "family": case["family"],
                "checks": checks,
                "passed_slot_count": sum(checks.values()),
                "slot_count": len(checks),
                "observed": {
                    "predicate_force": morphology.get("predicate_force"),
                    "event_aspect": morphology.get("event_aspect"),
                    "event_owner": graph.get("event_owner"),
                    "request_governor": graph.get("directive_governor"),
                    "direct_focus_request": bool(graph.get("direct_focus_request")),
                    "relation_types": relation_types,
                },
            }
        )
        family_slots[case["family"]] += len(checks)
        family_passes[case["family"]] += sum(checks.values())

        relation_row = {
            "case_id": row["case_id"],
            "target_id": row["target_id"],
            "relation_types": relation_types,
        }
        if case["family"] == "controlled_completed_benefactive_without_time_adverb":
            completed_relation_rows.append(
                {
                    **relation_row,
                    "passed": "third_party_completed_benefactive_description"
                    in relation_types,
                }
            )
        elif case["family"] == "controlled_explicit_third_party_polite_benefactive":
            polite_relation_rows.append(
                {
                    **relation_row,
                    "passed": "third_party_polite_benefactive_description"
                    in relation_types,
                }
            )
        elif case["family"] == "controlled_embedded_speech_request":
            embedded_relation_rows.append(
                {
                    **relation_row,
                    "passed": "embedded_speech_content" in relation_types,
                }
            )
        elif case["family"] == "controlled_omitted_subject_current_request":
            omitted_direct_rows.append(
                {**relation_row, "passed": bool(graph.get("direct_focus_request"))}
            )
        elif case["family"] == "controlled_full_predicate_direct_request":
            full_direct_rows.append(
                {**relation_row, "passed": bool(graph.get("direct_focus_request"))}
            )
        elif case["family"] == "controlled_negative_benefactive_or_focus_event":
            if relation_types:
                negative_relation_false_positives.append(relation_row)
        elif case["family"] == "controlled_nonbenefactive_third_party_declarative":
            if relation_types:
                nonbenefactive_relation_false_positives.append(relation_row)

    slot_correct = sum(row["passed_slot_count"] for row in slot_rows)
    slot_count = sum(row["slot_count"] for row in slot_rows)

    def recall(rows):
        passed = sum(row["passed"] for row in rows)
        return {
            "correct_count": passed,
            "target_count": len(rows),
            "recall": _ratio(passed, len(rows)),
            "failure_rows": [row for row in rows if not row["passed"]],
        }

    return {
        "controlled_target_count": len(slot_rows),
        "controlled_slot_correct_count": slot_correct,
        "controlled_slot_count": slot_count,
        "controlled_slot_accuracy": _ratio(slot_correct, slot_count),
        "family_slot_groups": {
            family: {
                "correct_count": family_passes[family],
                "slot_count": family_slots[family],
                "accuracy": _ratio(family_passes[family], family_slots[family]),
            }
            for family in contracts
        },
        "completed_relation": recall(completed_relation_rows),
        "polite_description_relation": recall(polite_relation_rows),
        "embedded_speech_relation": recall(embedded_relation_rows),
        "omitted_subject_direct_request": recall(omitted_direct_rows),
        "full_predicate_direct_request": recall(full_direct_rows),
        "negative_positive_relation_false_positive_count": len(
            negative_relation_false_positives
        ),
        "negative_positive_relation_false_positives": negative_relation_false_positives,
        "nonbenefactive_relation_false_positive_count": len(
            nonbenefactive_relation_false_positives
        ),
        "nonbenefactive_relation_false_positives": nonbenefactive_relation_false_positives,
        "slot_failure_rows": [
            row for row in slot_rows if row["passed_slot_count"] != row["slot_count"]
        ],
    }


def analyze(raw, dataset, config):
    frozen = config["frozen_inputs"]
    if len(raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V60 holdout target inference incomplete")
    if len(raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V60 holdout case compilation incomplete")
    if raw.get("model_calls_made") != config["model_call_budget"]:
        raise ValueError("V60 holdout model-call accounting mismatch")
    transport_attempts = sum(
        row["fresh_v51_result"]["transport_attempts"] for row in raw["target_rows"]
    )
    if raw.get("transport_attempts_made") != transport_attempts:
        raise ValueError("V60 holdout transport-attempt accounting mismatch")
    if raw["paid_api_used"] or raw["physical_vrm_actions_executed"] != 0:
        raise ValueError("V60 holdout violated local no-actuation policy")
    if tuple(raw["conditions"]) != tuple(config["conditions"]):
        raise ValueError("V60 holdout condition order drift")
    if not raw["construction_audit"]["passed"]:
        raise ValueError("V60 holdout construction audit was not passed")

    control_state = summarize_state(raw, dataset, "control")
    candidate_state = summarize_state(raw, dataset, "candidate")
    control_compiler = summarize_compiler(raw, dataset, "control")
    candidate_compiler = summarize_compiler(raw, dataset, "candidate")
    morphology = summarize_morphology(raw, dataset, config)
    control_targets = {tuple(row) for row in control_state["correct_target_keys"]}
    candidate_targets = {tuple(row) for row in candidate_state["correct_target_keys"]}
    control_cases = set(control_compiler["correct_case_ids"])
    candidate_cases = set(candidate_compiler["correct_case_ids"])
    case_fixes = candidate_cases - control_cases
    case_regressions = control_cases - candidate_cases
    case_lookup = {case["id"]: case for case in dataset["cases"]}
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
        "case_fix_count": len(case_fixes),
        "case_fix_ids": sorted(case_fixes),
        "case_fix_family_counts": dict(
            sorted(Counter(case_lookup[case_id]["family"] for case_id in case_fixes).items())
        ),
        "case_regression_count": len(case_regressions),
        "case_regression_ids": sorted(case_regressions),
        "false_action_case_count_delta": candidate_compiler["false_action_case_count"]
        - control_compiler["false_action_case_count"],
        "required_call_recall_delta": candidate_compiler["required_call_recall"]
        - control_compiler["required_call_recall"],
        "mcnemar_discordant_case_count": len(case_fixes) + len(case_regressions),
        "two_sided_exact_mcnemar_p": _two_sided_exact_mcnemar(
            len(case_fixes), len(case_regressions)
        ),
    }

    expected_by_case = {
        case["id"]: {
            _target_id(frame): frame["commitment"] for frame in case["expected_frames"]
        }
        for case in dataset["cases"]
    }
    candidate_commitments_by_case = {
        row["case_id"]: row["candidate_commitments"] for row in raw["case_rows"]
    }
    compiler_only_failures = [
        case_id
        for case_id in candidate_compiler["failure_case_ids"]
        if candidate_commitments_by_case[case_id] == expected_by_case[case_id]
    ]
    residual_attribution = {
        "candidate_state_failure_count": len(candidate_state["failure_rows"]),
        "candidate_state_failure_selection_source_counts": candidate_state[
            "failure_selection_source_counts"
        ],
        "morphology_slot_failure_target_count": len(morphology["slot_failure_rows"]),
        "compiler_only_failure_case_count": len(compiler_only_failures),
        "compiler_only_failure_case_ids": sorted(compiler_only_failures),
    }

    state_gates = config["candidate_state_gates"]
    compiler_gates = config["candidate_compiler_gates"]
    morphology_gates = config["morphology_generalization_gates"]
    matched_gates = config["matched_comparison_gates"]
    checks = {
        "state_correct_count": candidate_state["correct_count"]
        >= state_gates["correct_commitment_count_at_least"],
        "state_commitment_accuracy": candidate_state["commitment_accuracy"]
        >= state_gates["commitment_accuracy_at_least"],
        "state_requested_precision": candidate_state["requested_precision"]
        == state_gates["requested_precision"],
        "state_requested_recall": candidate_state["requested_recall"]
        >= state_gates["requested_recall_at_least"],
        "state_external_accuracy": candidate_state["source_groups"]["external_exact"][
            "accuracy"
        ]
        >= state_gates["external_target_accuracy_at_least"],
        "state_controlled_accuracy": candidate_state["source_groups"][
            "controlled_researcher_authored"
        ]["accuracy"]
        >= state_gates["controlled_target_accuracy_at_least"],
        "compiler_ordered_exact_count": candidate_compiler["ordered_exact_count"]
        >= compiler_gates["ordered_exact_count_at_least"],
        "compiler_ordered_exact_accuracy": candidate_compiler["ordered_exact_accuracy"]
        >= compiler_gates["ordered_exact_accuracy_at_least"],
        "compiler_action_exact_accuracy": candidate_compiler[
            "action_ordered_exact_accuracy"
        ]
        >= compiler_gates["action_ordered_exact_accuracy_at_least"],
        "compiler_required_call_recall": candidate_compiler["required_call_recall"]
        >= compiler_gates["required_call_recall_at_least"],
        "compiler_no_action_specificity": candidate_compiler["no_action_specificity"]
        == compiler_gates["no_action_specificity"],
        "compiler_false_actions": candidate_compiler["false_action_case_count"]
        == compiler_gates["false_action_case_count"],
        "compiler_external_accuracy": candidate_compiler["source_groups"][
            "external_exact"
        ]["accuracy"]
        >= compiler_gates["external_exact_accuracy_at_least"],
        "compiler_controlled_accuracy": candidate_compiler["source_groups"][
            "controlled_researcher_authored"
        ]["accuracy"]
        >= compiler_gates["controlled_exact_accuracy_at_least"],
        "compiler_authorization_provenance": candidate_compiler[
            "authorization_provenance_coverage"
        ]
        == compiler_gates["authorization_provenance_coverage"],
        "compiler_ungrounded_execution": candidate_compiler["ungrounded_execution_count"]
        == compiler_gates["ungrounded_execution_count"],
        "compiler_commitment_mutation": candidate_compiler["commitment_mutation_count"]
        == compiler_gates["commitment_mutation_count"],
        "morphology_controlled_slots": morphology["controlled_slot_accuracy"]
        >= morphology_gates["controlled_slot_accuracy_at_least"],
        "morphology_each_family_slots": all(
            row["accuracy"]
            >= morphology_gates["each_controlled_family_slot_accuracy_at_least"]
            for row in morphology["family_slot_groups"].values()
        ),
        "morphology_completed_relation": morphology["completed_relation"]["recall"]
        >= morphology_gates["completed_relation_recall_at_least"],
        "morphology_polite_relation": morphology["polite_description_relation"][
            "recall"
        ]
        >= morphology_gates["polite_description_relation_recall_at_least"],
        "morphology_omitted_direct": morphology["omitted_subject_direct_request"][
            "recall"
        ]
        >= morphology_gates["omitted_subject_direct_request_recall_at_least"],
        "morphology_full_direct": morphology["full_predicate_direct_request"]["recall"]
        >= morphology_gates["full_predicate_direct_request_recall_at_least"],
        "morphology_embedded_relation": morphology["embedded_speech_relation"]["recall"]
        >= morphology_gates["embedded_speech_relation_recall_at_least"],
        "morphology_negative_false_positive": morphology[
            "negative_positive_relation_false_positive_count"
        ]
        == morphology_gates["negative_positive_relation_false_positive_count"],
        "morphology_nonbenefactive_false_positive": morphology[
            "nonbenefactive_relation_false_positive_count"
        ]
        == morphology_gates["nonbenefactive_relation_false_positive_count"],
        "matched_state_gain": comparison["state_correct_count_delta"]
        >= matched_gates["state_correct_count_delta_at_least"],
        "matched_case_gain": comparison["ordered_exact_count_delta"]
        >= matched_gates["ordered_exact_count_delta_at_least"],
        "matched_case_fixes": comparison["case_fix_count"]
        >= matched_gates["case_fix_count_at_least"],
        "matched_state_regressions": comparison["state_regression_count"]
        <= matched_gates["state_regression_count_at_most"],
        "matched_case_regressions": comparison["case_regression_count"]
        <= matched_gates["case_regression_count_at_most"],
        "matched_false_action_delta": comparison["false_action_case_count_delta"]
        <= matched_gates["false_action_case_count_delta_at_most"],
        "matched_required_call_recall_delta": comparison["required_call_recall_delta"]
        >= matched_gates["required_call_recall_delta_at_least"],
        "matched_exact_mcnemar": comparison["two_sided_exact_mcnemar_p"]
        <= matched_gates["two_sided_exact_mcnemar_p_at_most"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_predicate_morphology_independent_holdout_analysis_v60",
        "evidence_status": raw["evidence_status"],
        "model_calls_made": raw["model_calls_made"],
        "transport_attempts_made": transport_attempts,
        "control_condition": CONTROL,
        "candidate_condition": CANDIDATE,
        "control_state": control_state,
        "candidate_state": candidate_state,
        "control_compiler": control_compiler,
        "candidate_compiler": candidate_compiler,
        "morphology_generalization": morphology,
        "matched_comparison": comparison,
        "residual_attribution": residual_attribution,
        "gates": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": (
            "seal_v60_predicate_morphology_for_bounded_action_authorization"
            if passed
            else "reject_v60_independent_advancement_and_attribute_failure"
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
    morphology = report["morphology_generalization"]
    comparison = report["matched_comparison"]
    return "\n".join(
        [
            "# V60 predicate-morphology independent holdout",
            "",
            "Both conditions used one shared fresh local-model fallback per target and the same V57 compiler.",
            "",
            "| Metric | V59 control | V60 candidate |",
            "|---|---:|---:|",
            f"| State commitments | {control_state['correct_count']}/120 ({_pct(control_state['commitment_accuracy'])}) | {candidate_state['correct_count']}/120 ({_pct(candidate_state['commitment_accuracy'])}) |",
            f"| Ordered exact cases | {control['ordered_exact_count']}/117 ({_pct(control['ordered_exact_accuracy'])}) | {candidate['ordered_exact_count']}/117 ({_pct(candidate['ordered_exact_accuracy'])}) |",
            f"| False-action cases | {control['false_action_case_count']} | {candidate['false_action_case_count']} |",
            f"| Required-call recall | {_pct(control['required_call_recall'])} | {_pct(candidate['required_call_recall'])} |",
            f"| External exact cases | {control['source_groups']['external_exact']['correct_count']}/19 | {candidate['source_groups']['external_exact']['correct_count']}/19 |",
            "",
            f"- V60 controlled morphology slots: {morphology['controlled_slot_correct_count']}/{morphology['controlled_slot_count']} ({_pct(morphology['controlled_slot_accuracy'])})",
            f"- State fixes / regressions: {comparison['state_fix_count']} / {comparison['state_regression_count']}",
            f"- Case fixes / regressions: {comparison['case_fix_count']} / {comparison['case_regression_count']}",
            f"- Exact McNemar p: {comparison['two_sided_exact_mcnemar_p']:.6f}",
            f"- Gate: {'PASS' if report['gates']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            "",
            "A pass supports only this bounded Japanese action-authorization slice. Runtime and physical execution remain unauthorized.",
            "",
        ]
    )


def main():
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(load(DEFAULT_RAW), load(DATASET_PATH), load(CONFIG_PATH))
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
                "mcnemar_p": report["matched_comparison"][
                    "two_sided_exact_mcnemar_p"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
