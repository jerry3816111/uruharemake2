#!/usr/bin/env python3
"""Analyze V57 compiler development replay against frozen V48 calls."""

import argparse
import json
from pathlib import Path

from action_selective_deliberation_v37 import score_action_calls
from run_relation_authorized_action_compiler_v57 import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _pct(value):
    return f"{100 * value:.2f}%"


def _summarize(dataset, raw, compilation_key):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = []
    failures = []
    accepted = 0
    grounded = 0
    authorized = 0
    ungrounded = 0
    unresolved_execution = 0
    commitment_mutations = 0
    for row in raw["case_rows"]:
        case = cases[row["case_id"]]
        compilation = row[compilation_key]
        score = score_action_calls(case, compilation["accepted_calls"])
        scores.append(score)
        if not score["exact_match"]:
            failures.append(
                {
                    "case_id": case["id"],
                    "family": case["family"],
                    "user_input": case["user_input"],
                    "expected_calls": case["expected_calls"],
                    "actual_calls": score["actual_calls"],
                }
            )
        frames = compilation.get("accepted_frames") or []
        plan = compilation.get("execution_plan") or []
        accepted += len(frames)
        grounded += sum(bool(frame.get("matched_anchor")) for frame in frames)
        authorized += sum(bool(step.get("authorization")) for step in plan)
        ungrounded += compilation.get("ungrounded_execution_count", 0)
        unresolved_execution += compilation.get(
            "unresolved_model_only_execution_count", 0
        )
        commitment_mutations += compilation.get("commitment_mutation_count", 0)
    no_action = [score for score in scores if score["expected_call_count"] == 0]
    action_tp = sum(score["required_action_true_positive"] for score in scores)
    action_fn = sum(score["required_action_false_negative"] for score in scores)
    return {
        "case_count": len(scores),
        "exact_call_count": sum(score["exact_match"] for score in scores),
        "exact_call_accuracy": _rate(
            sum(score["exact_match"] for score in scores), len(scores)
        ),
        "call_failure_count": len(failures),
        "call_failures": failures,
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _rate(action_tp, action_tp + action_fn),
        "false_action_count": sum(score["false_action"] for score in scores),
        "negation_violation_count": sum(
            score["negation_violation"] for score in scores
        ),
        "accepted_call_anchor_coverage": _rate(grounded, accepted)
        if accepted
        else 1.0,
        "authorization_provenance_coverage": _rate(authorized, accepted)
        if accepted
        else 1.0,
        "ungrounded_execution_count": ungrounded,
        "unresolved_model_only_execution_count": unresolved_execution,
        "commitment_mutation_count": commitment_mutations,
    }


def analyze(raw, dataset, config):
    if raw["model_calls"] != 0 or raw["paid_api_used"]:
        raise ValueError("V57 development model accounting mismatch")
    if len(raw["case_rows"]) != config["frozen_inputs"]["case_count"]:
        raise ValueError("V57 development report is incomplete")
    control = _summarize(dataset, raw, "control_compilation")
    candidate = _summarize(dataset, raw, "candidate_compilation")
    control_failures = {row["case_id"] for row in control["call_failures"]}
    candidate_failures = {row["case_id"] for row in candidate["call_failures"]}
    comparison = {
        "exact_call_count_delta": candidate["exact_call_count"]
        - control["exact_call_count"],
        "false_action_count_delta": candidate["false_action_count"]
        - control["false_action_count"],
        "fixed_call_case_ids": sorted(control_failures - candidate_failures),
        "fixed_call_count": len(control_failures - candidate_failures),
        "call_regression_case_ids": sorted(candidate_failures - control_failures),
        "call_regression_count": len(candidate_failures - control_failures),
    }
    targeted = {
        row["case_id"] for row in config["prespecified_failure_repairs"]
    }
    targeted_fixed = sorted(targeted & (control_failures - candidate_failures))
    gates = config["development_gates"]
    checks = {
        "frozen_commitment_correct_count": config["frozen_inputs"][
            "frozen_v56_commitment_correct_count"
        ]
        == gates["frozen_commitment_correct_count"],
        "frozen_commitment_mutation_count": candidate["commitment_mutation_count"]
        == gates["frozen_commitment_mutation_count"],
        "candidate_exact_call_count": candidate["exact_call_count"]
        == gates["candidate_exact_call_count"],
        "candidate_exact_call_accuracy": candidate["exact_call_accuracy"]
        == gates["candidate_exact_call_accuracy"],
        "candidate_no_action_specificity": candidate["no_action_specificity"]
        == gates["candidate_no_action_specificity"],
        "candidate_required_action_recall": candidate["required_action_recall"]
        == gates["candidate_required_action_recall"],
        "candidate_false_action_count": candidate["false_action_count"]
        == gates["candidate_false_action_count"],
        "candidate_negation_violation_count": candidate["negation_violation_count"]
        == gates["candidate_negation_violation_count"],
        "candidate_accepted_call_anchor_coverage": candidate[
            "accepted_call_anchor_coverage"
        ]
        == gates["candidate_accepted_call_anchor_coverage"],
        "candidate_authorization_provenance_coverage": candidate[
            "authorization_provenance_coverage"
        ]
        == gates["candidate_authorization_provenance_coverage"],
        "candidate_ungrounded_execution_count": candidate[
            "ungrounded_execution_count"
        ]
        == gates["candidate_ungrounded_execution_count"],
        "targeted_fixed_call_count": len(targeted_fixed)
        == gates["targeted_fixed_call_count"],
        "call_regression_count": comparison["call_regression_count"]
        == gates["call_regression_count"],
        "unresolved_model_only_execution_count": candidate[
            "unresolved_model_only_execution_count"
        ]
        == gates["unresolved_model_only_execution_count"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_relation_authorized_action_compiler_development_analysis_v57",
        "evidence_status": raw["evidence_status"],
        "conditions": {CONTROL: control, CANDIDATE: candidate},
        "comparison": comparison,
        "targeted_fixed_call_case_ids": targeted_fixed,
        "gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "decision": (
            "authorize_independent_v57_compiler_holdout"
            if passed
            else "reject_v57_compiler_development_candidate"
        ),
        "fresh_holdout_claim_authorized": False,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "broad_human_likeness_claim_authorized": False,
    }


def render_markdown(report):
    control = report["conditions"][CONTROL]
    candidate = report["conditions"][CANDIDATE]
    return "\n".join(
        [
            "# V57 relation-authorized compiler development result",
            "",
            "This is consumed development evidence, not a fresh holdout.",
            "",
            "| condition | exact calls | false actions | required recall |",
            "|---|---:|---:|---:|",
            f"| frozen V48 | {control['exact_call_count']}/64 "
            f"({_pct(control['exact_call_accuracy'])}) | "
            f"{control['false_action_count']} | "
            f"{_pct(control['required_action_recall'])} |",
            f"| V57 candidate | {candidate['exact_call_count']}/64 "
            f"({_pct(candidate['exact_call_accuracy'])}) | "
            f"{candidate['false_action_count']} | "
            f"{_pct(candidate['required_action_recall'])} |",
            "",
            f"- Fixed calls / regressions: "
            f"`{report['comparison']['fixed_call_count']}` / "
            f"`{report['comparison']['call_regression_count']}`.",
            f"- Gate passed: `{report['gate']['passed']}`.",
            f"- Decision: `{report['decision']}`.",
            "- No runtime, shadow, or physical execution is authorized.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(load(args.raw), load(DATASET_PATH), load(CONFIG_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "gate_passed": report["gate"]["passed"],
                "decision": report["decision"],
                "failed_checks": report["gate"]["failed_checks"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
