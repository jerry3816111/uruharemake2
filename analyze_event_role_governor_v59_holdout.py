#!/usr/bin/env python3
"""Analyze the preregistered matched V58/V59 independent holdout."""

import json
import math
from collections import Counter
from pathlib import Path

from run_event_role_governor_v59_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "event_role_governor_v59_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "event_role_governor_v59_holdout_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "event_role_governor_v59_holdout_analysis.md"
RELATION_BY_FAMILY = {
    "controlled_embedded_speech_content": "embedded_speech_content",
    "controlled_third_party_habitual_description": "third_party_habitual_description",
    "controlled_past_experiential_description": "past_experiential_description",
}
DIRECT_FAMILY = "controlled_direct_focus_request_contrast"
BLOCKING_RELATIONS = set(RELATION_BY_FAMILY.values())


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _canonical(call):
    return json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _counter(calls):
    return Counter(_canonical(call) for call in calls)


def _target_id(frame):
    return f"{frame['domain']}.{frame['value']}"


def _expected_targets(dataset):
    return {
        (case["id"], _target_id(frame)): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def _group_summary(correct_keys, cases, target_rows):
    groups = {}
    for source_type in ("external_exact", "controlled_researcher_authored"):
        keys = {
            (row["case_id"], row["target_id"])
            for row in target_rows
            if cases[row["case_id"]]["source_type"] == source_type
        }
        groups[source_type] = {
            "correct_count": len(keys & correct_keys),
            "target_count": len(keys),
            "accuracy": _ratio(len(keys & correct_keys), len(keys)),
        }
    return groups


def summarize_state(raw, dataset, prefix):
    expected = _expected_targets(dataset)
    cases = {case["id"]: case for case in dataset["cases"]}
    rows = [
        row
        for row in raw["target_rows"]
        if (row["case_id"], row["target_id"]) in expected
    ]
    field = f"{prefix}_commitment"
    correct = {
        (row["case_id"], row["target_id"])
        for row in rows
        if row[field] == expected[(row["case_id"], row["target_id"])]
    }
    predicted_requested = sum(row[field] == "requested" for row in rows)
    gold_requested = sum(value == "requested" for value in expected.values())
    true_requested = sum(
        row[field] == "requested"
        and expected[(row["case_id"], row["target_id"])] == "requested"
        for row in rows
    )
    family = {}
    for name in sorted({case["family"] for case in cases.values()}):
        keys = {
            (row["case_id"], row["target_id"])
            for row in rows
            if cases[row["case_id"]]["family"] == name
        }
        family[name] = {
            "correct_count": len(keys & correct),
            "target_count": len(keys),
            "accuracy": _ratio(len(keys & correct), len(keys)),
        }
    failures = [
        {
            "case_id": row["case_id"],
            "family": cases[row["case_id"]]["family"],
            "source_type": cases[row["case_id"]]["source_type"],
            "target_id": row["target_id"],
            "expected": expected[(row["case_id"], row["target_id"])],
            "actual": row[field],
            "selection_source": row[f"{prefix}_selection_source"],
            "shared_fallback_commitment": row["shared_fallback_commitment"],
        }
        for row in rows
        if (row["case_id"], row["target_id"]) not in correct
    ]
    return {
        "target_count": len(rows),
        "correct_count": len(correct),
        "commitment_accuracy": _ratio(len(correct), len(rows)),
        "requested_precision": _ratio(true_requested, predicted_requested),
        "requested_recall": _ratio(true_requested, gold_requested),
        "predicted_requested_count": predicted_requested,
        "gold_requested_count": gold_requested,
        "true_requested_count": true_requested,
        "selection_source_counts": dict(
            sorted(Counter(row[f"{prefix}_selection_source"] for row in rows).items())
        ),
        "failure_selection_source_counts": dict(
            sorted(Counter(row["selection_source"] for row in failures).items())
        ),
        "source_groups": _group_summary(correct, cases, rows),
        "family_groups": family,
        "correct_target_keys": sorted([list(key) for key in correct]),
        "failure_rows": failures,
    }


def summarize_compiler(raw, dataset, prefix):
    cases = {case["id"]: case for case in dataset["cases"]}
    key = f"{prefix}_compilation"
    rows = []
    expected_call_count = 0
    matched_call_count = 0
    accepted_call_count = 0
    authorization_sum = 0.0
    for raw_row in raw["case_rows"]:
        case = cases[raw_row["case_id"]]
        compilation = raw_row[key]
        expected = case["expected_calls"]
        actual = compilation.get("accepted_calls") or []
        expected_counter = _counter(expected)
        actual_counter = _counter(actual)
        matched = expected_counter & actual_counter
        unexpected = actual_counter - expected_counter
        ordered_exact = list(map(_canonical, expected)) == list(map(_canonical, actual))
        rows.append(
            {
                "case_id": case["id"],
                "family": case["family"],
                "source_type": case["source_type"],
                "ordered_exact": ordered_exact,
                "expected_action": bool(expected),
                "false_action": bool(unexpected),
                "correct_restraint": not expected and not actual,
                "expected_calls": expected,
                "actual_calls": actual,
            }
        )
        expected_call_count += sum(expected_counter.values())
        matched_call_count += sum(matched.values())
        accepted_call_count += len(actual)
        authorization_sum += (
            compilation.get("authorization_provenance_coverage", 0.0) * len(actual)
        )
    action_rows = [row for row in rows if row["expected_action"]]
    no_action_rows = [row for row in rows if not row["expected_action"]]

    def grouped(field):
        output = {}
        for value in sorted({row[field] for row in rows}):
            group = [row for row in rows if row[field] == value]
            output[value] = {
                "correct_count": sum(row["ordered_exact"] for row in group),
                "case_count": len(group),
                "accuracy": _ratio(sum(row["ordered_exact"] for row in group), len(group)),
            }
        return output

    return {
        "case_count": len(rows),
        "ordered_exact_count": sum(row["ordered_exact"] for row in rows),
        "ordered_exact_accuracy": _ratio(sum(row["ordered_exact"] for row in rows), len(rows)),
        "action_ordered_exact_count": sum(row["ordered_exact"] for row in action_rows),
        "action_case_count": len(action_rows),
        "action_ordered_exact_accuracy": _ratio(
            sum(row["ordered_exact"] for row in action_rows), len(action_rows)
        ),
        "false_action_case_count": sum(row["false_action"] for row in rows),
        "no_action_specificity": _ratio(
            sum(row["correct_restraint"] for row in no_action_rows), len(no_action_rows)
        ),
        "required_call_precision": _ratio(matched_call_count, accepted_call_count),
        "required_call_recall": _ratio(matched_call_count, expected_call_count),
        "matched_required_call_count": matched_call_count,
        "expected_call_count": expected_call_count,
        "accepted_call_count": accepted_call_count,
        "authorization_provenance_coverage": _ratio(
            authorization_sum, accepted_call_count
        ),
        "ungrounded_execution_count": sum(
            raw_row[key].get("ungrounded_execution_count", 0)
            for raw_row in raw["case_rows"]
        ),
        "commitment_mutation_count": sum(
            raw_row[key].get("commitment_mutation_count", 0)
            for raw_row in raw["case_rows"]
        ),
        "source_groups": grouped("source_type"),
        "family_groups": grouped("family"),
        "correct_case_ids": sorted(row["case_id"] for row in rows if row["ordered_exact"]),
        "failure_case_ids": sorted(row["case_id"] for row in rows if not row["ordered_exact"]),
        "false_action_case_ids": sorted(row["case_id"] for row in rows if row["false_action"]),
        "failure_rows": [row for row in rows if not row["ordered_exact"]],
    }


def summarize_event_roles(raw, dataset, config):
    cases = {case["id"]: case for case in dataset["cases"]}
    contracts = config["expected_event_roles_by_family"]
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
        graph = row["candidate_state"].get("v59_event_role_graph") or {}
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


def _two_sided_exact_mcnemar(case_fixes, case_regressions):
    discordant = case_fixes + case_regressions
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, value)
        for value in range(min(case_fixes, case_regressions) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def analyze(raw, dataset, config):
    frozen = config["frozen_inputs"]
    if len(raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V59 holdout target inference incomplete")
    if len(raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V59 holdout case compilation incomplete")
    if raw.get("model_calls_made") != config["model_call_budget"]:
        raise ValueError("V59 holdout model-call accounting mismatch")
    if raw["paid_api_used"] or raw["physical_vrm_actions_executed"] != 0:
        raise ValueError("V59 holdout violated local no-actuation policy")
    if tuple(raw["conditions"]) != tuple(config["conditions"]):
        raise ValueError("V59 holdout condition order drift")
    if not raw["construction_audit"]["passed"]:
        raise ValueError("V59 holdout construction audit was not passed")

    control_state = summarize_state(raw, dataset, "control")
    candidate_state = summarize_state(raw, dataset, "candidate")
    control_compiler = summarize_compiler(raw, dataset, "control")
    candidate_compiler = summarize_compiler(raw, dataset, "candidate")
    event_roles = summarize_event_roles(raw, dataset, config)
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
        "state_fix_target_keys": sorted([list(key) for key in candidate_targets - control_targets]),
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
        case["id"]: {_target_id(frame): frame["commitment"] for frame in case["expected_frames"]}
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
        "event_role_relation_failure_count": len(event_roles["relation_failure_rows"]),
        "event_role_slot_failure_target_count": len(event_roles["role_slot_failure_rows"]),
        "compiler_only_failure_case_count": len(compiler_only_failures),
        "compiler_only_failure_case_ids": sorted(compiler_only_failures),
    }

    state_gates = config["candidate_state_gates"]
    compiler_gates = config["candidate_compiler_gates"]
    role_gates = config["event_role_generalization_gates"]
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
        == compiler_gates["external_exact_accuracy"],
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
        "event_role_expected_relation_count": event_roles[
            "expected_relation_detected_count"
        ]
        >= role_gates["expected_relation_count_at_least"],
        "event_role_expected_relation_coverage": event_roles["expected_relation_coverage"]
        >= role_gates["expected_relation_coverage_at_least"],
        "event_role_each_relation_family": all(
            event_roles["relation_family_groups"][family]["coverage"]
            >= role_gates["each_relation_family_coverage_at_least"]
            for family in RELATION_BY_FAMILY
        ),
        "event_role_contrast_false_positives": event_roles[
            "contrast_blocking_relation_target_count"
        ]
        == role_gates["contrast_blocking_relation_target_count"],
        "event_role_direct_focus_recall": event_roles["direct_focus_request_recall"]
        >= role_gates["direct_focus_request_recall_at_least"],
        "event_role_slot_accuracy": event_roles["role_slot_accuracy"]
        >= role_gates["role_slot_accuracy_at_least"],
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
        "schema": "uruha_event_role_governor_independent_holdout_analysis_v59",
        "evidence_status": raw["evidence_status"],
        "control_condition": CONTROL,
        "candidate_condition": CANDIDATE,
        "control_state": control_state,
        "candidate_state": candidate_state,
        "control_compiler": control_compiler,
        "candidate_compiler": candidate_compiler,
        "event_role_generalization": event_roles,
        "matched_comparison": comparison,
        "residual_attribution": residual_attribution,
        "gates": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": (
            "seal_v59_event_role_candidate_and_authorize_separate_compiler_coverage"
            if passed
            else "reject_v59_independent_advancement_and_attribute_failure"
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
    comparison = report["matched_comparison"]
    roles = report["event_role_generalization"]
    return "\n".join(
        [
            "# V59 event-role independent holdout",
            "",
            "Both conditions used one shared fresh local-model fallback per target and the same V57 compiler.",
            "",
            "| Metric | V58 control | V59 candidate |",
            "|---|---:|---:|",
            f"| State commitments | {control_state['correct_count']}/73 ({_pct(control_state['commitment_accuracy'])}) | {candidate_state['correct_count']}/73 ({_pct(candidate_state['commitment_accuracy'])}) |",
            f"| Ordered exact cases | {control['ordered_exact_count']}/72 ({_pct(control['ordered_exact_accuracy'])}) | {candidate['ordered_exact_count']}/72 ({_pct(candidate['ordered_exact_accuracy'])}) |",
            f"| False-action cases | {control['false_action_case_count']} | {candidate['false_action_case_count']} |",
            f"| Required-call recall | {_pct(control['required_call_recall'])} | {_pct(candidate['required_call_recall'])} |",
            "",
            f"- Event-role relation coverage: {roles['expected_relation_detected_count']}/{roles['expected_relation_target_count']} ({_pct(roles['expected_relation_coverage'])})",
            f"- Role-slot accuracy: {roles['role_slot_correct_count']}/{roles['role_slot_count']} ({_pct(roles['role_slot_accuracy'])})",
            f"- Direct-request recall: {_pct(roles['direct_focus_request_recall'])}",
            f"- Case fixes / regressions: {comparison['case_fix_count']} / {comparison['case_regression_count']}",
            f"- Exact McNemar p: {comparison['two_sided_exact_mcnemar_p']:.6f}",
            f"- Gate: {'PASS' if report['gates']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            "",
            "A pass supports only this project-fresh Japanese event-role slice. Runtime and physical execution remain unauthorized.",
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
                "false_actions": report["candidate_compiler"]["false_action_case_count"],
                "mcnemar_p": report["matched_comparison"]["two_sided_exact_mcnemar_p"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
