#!/usr/bin/env python3
"""Evaluate V48 scope perception with gold semantics fixed."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_selective_deliberation_v37 import score_action_calls
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import compile_v39
from relational_commitment_context_v43 import assemble_commitment_only_case
from target_relative_scope_v48 import (
    compile_target_relative_v48,
    perceive_target_relative_scope,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_relative_scope_v48_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_JSON = ROOT / "reports" / "target_relative_scope_v48_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "target_relative_scope_v48_development_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _validate_inputs(config):
    for key, expected in config["frozen_inputs"].items():
        if key.endswith("_sha256"):
            path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
            if _sha256(path) != expected:
                raise ValueError(f"V48 frozen input hash mismatch: {path.name}")


def _gold_by_target(case):
    return {
        f"{frame['domain']}.{frame['value']}": frame
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _target_scope_summary(scope):
    return {
        row["target_id"]: {
            "anchor_count": len(row["anchors"]),
            "safe_anchor_count": sum(not anchor["blocked"] for anchor in row["anchors"]),
            "blocked_anchor_count": sum(anchor["blocked"] for anchor in row["anchors"]),
            "reason_types": sorted(
                {
                    reason["marker_type"]
                    for anchor in row["anchors"]
                    for reason in anchor["scope_reasons"]
                }
            ),
            "anchors": row["anchors"],
        }
        for row in scope["targets"]
    }


def audit_scope(dataset, ontology):
    requested_total = 0
    requested_safe = 0
    negated_total = 0
    negated_blocked = 0
    cancelled_total = 0
    cancelled_blocked = 0
    failures = []
    rows = []
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        scope = perceive_target_relative_scope(case["user_input"], candidates)
        target_scope = _target_scope_summary(scope)
        gold = _gold_by_target(case)
        for target_id, frame in gold.items():
            observed = target_scope[target_id]
            commitment = frame["commitment"]
            correct = True
            if commitment == "requested":
                requested_total += 1
                correct = observed["safe_anchor_count"] >= 1
                requested_safe += int(correct)
            elif commitment == "negated":
                negated_total += 1
                correct = (
                    observed["safe_anchor_count"] == 0
                    and "target_local_negation" in observed["reason_types"]
                )
                negated_blocked += int(correct)
            elif commitment == "cancelled":
                cancelled_total += 1
                correct = (
                    observed["safe_anchor_count"] == 0
                    and bool(
                        {"target_local_cessation", "referential_cancellation"}
                        & set(observed["reason_types"])
                    )
                )
                cancelled_blocked += int(correct)
            if not correct:
                failures.append(
                    {
                        "case_id": case["id"],
                        "target_id": target_id,
                        "commitment": commitment,
                        "observed": observed,
                    }
                )
        rows.append(
            {
                "case_id": case["id"],
                "user_input": case["user_input"],
                "targets": target_scope,
                "assigned_markers": scope["assigned_markers"],
            }
        )
    rate = lambda numerator, denominator: round(numerator / denominator, 4)
    return {
        "requested_target_count": requested_total,
        "requested_target_safe_anchor_count": requested_safe,
        "requested_target_safe_anchor_recall": rate(requested_safe, requested_total),
        "negated_target_count": negated_total,
        "negated_target_blocked_all_count": negated_blocked,
        "negated_target_blocked_all_recall": rate(negated_blocked, negated_total),
        "cancelled_target_count": cancelled_total,
        "cancelled_target_blocked_all_count": cancelled_blocked,
        "cancelled_target_blocked_all_recall": rate(cancelled_blocked, cancelled_total),
        "failure_count": len(failures),
        "failures": failures,
        "rows": rows,
    }


def audit_probes(config, ontology):
    results = []
    for probe in config["metamorphic_probes"]:
        candidates = ground_supported_targets(probe["text"], ontology)
        scope = perceive_target_relative_scope(probe["text"], candidates)
        targets = _target_scope_summary(scope)
        failures = []
        for target_id in probe.get("blocked_all_targets", []):
            target = targets.get(target_id)
            if not target or target["safe_anchor_count"] != 0:
                failures.append(f"not_blocked_all:{target_id}")
        for target_id in probe.get("cessation_all_targets", []):
            target = targets.get(target_id)
            if (
                not target
                or target["safe_anchor_count"] != 0
                or "target_local_cessation" not in target["reason_types"]
            ):
                failures.append(f"not_cessation_all:{target_id}")
        for target_id, minimum in probe.get("blocked_anchor_minimums", {}).items():
            target = targets.get(target_id)
            if not target or target["blocked_anchor_count"] < minimum:
                failures.append(f"blocked_minimum:{target_id}")
        for target_id, minimum in probe.get("safe_target_minimums", {}).items():
            target = targets.get(target_id)
            if not target or target["safe_anchor_count"] < minimum:
                failures.append(f"safe_minimum:{target_id}")
        results.append(
            {
                "id": probe["id"],
                "text": probe["text"],
                "passed": not failures,
                "failures": failures,
                "targets": targets,
                "assigned_markers": scope["assigned_markers"],
            }
        )
    return {
        "probe_count": len(results),
        "passed_count": sum(row["passed"] for row in results),
        "pass_rate": round(sum(row["passed"] for row in results) / len(results), 4),
        "results": results,
    }


def _perfect_judgments(case, candidates):
    gold = _gold_by_target(case)
    return {
        candidate["target_id"]: {
            "parse_success": True,
            "errors": [],
            "commitment": gold[candidate["target_id"]]["commitment"],
        }
        for candidate in candidates
    }


def audit_perfect_semantic_compilation(dataset, ontology):
    old_scores = []
    new_scores = []
    old_failures = []
    new_failures = []
    transitions = []
    accepted = 0
    anchored = 0
    ungrounded = 0
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        assembled = assemble_commitment_only_case(
            case["user_input"], candidates, _perfect_judgments(case, candidates)
        )
        old_compilation = compile_v39(case["user_input"], assembled, ontology)
        new_compilation = compile_target_relative_v48(
            case["user_input"], assembled, ontology
        )
        old_score = score_action_calls(case, old_compilation["accepted_calls"])
        new_score = score_action_calls(case, new_compilation["accepted_calls"])
        old_scores.append(old_score)
        new_scores.append(new_score)
        if not old_score["exact_match"]:
            old_failures.append(
                {
                    "case_id": case["id"],
                    "expected_calls": case["expected_calls"],
                    "actual_calls": old_score["actual_calls"],
                }
            )
        if not new_score["exact_match"]:
            new_failures.append(
                {
                    "case_id": case["id"],
                    "expected_calls": case["expected_calls"],
                    "actual_calls": new_score["actual_calls"],
                }
            )
        if old_score["exact_match"] != new_score["exact_match"]:
            transitions.append(
                {
                    "case_id": case["id"],
                    "old_exact": old_score["exact_match"],
                    "new_exact": new_score["exact_match"],
                    "old_calls": old_score["actual_calls"],
                    "new_calls": new_score["actual_calls"],
                }
            )
        accepted_frames = new_compilation.get("accepted_frames") or []
        accepted += len(accepted_frames)
        anchored += sum(bool(frame.get("matched_anchor")) for frame in accepted_frames)
        ungrounded += new_compilation["ungrounded_execution_count"]
    no_action = [score for score in new_scores if score["expected_call_count"] == 0]
    case_count = len(dataset["cases"])
    return {
        "case_count": case_count,
        "old_exact_count": sum(score["exact_match"] for score in old_scores),
        "old_exact_accuracy": round(
            sum(score["exact_match"] for score in old_scores) / case_count, 4
        ),
        "old_failures": old_failures,
        "new_exact_count": sum(score["exact_match"] for score in new_scores),
        "perfect_semantic_compiled_call_exact_accuracy": round(
            sum(score["exact_match"] for score in new_scores) / case_count, 4
        ),
        "new_failures": new_failures,
        "improved_case_count": sum(
            not old["exact_match"] and new["exact_match"]
            for old, new in zip(old_scores, new_scores)
        ),
        "regressed_case_count": sum(
            old["exact_match"] and not new["exact_match"]
            for old, new in zip(old_scores, new_scores)
        ),
        "transitions": transitions,
        "perfect_semantic_no_action_specificity": round(
            sum(score["no_action_correct"] for score in no_action) / len(no_action), 4
        ),
        "perfect_semantic_false_action_rate": round(
            sum(score["false_action"] for score in new_scores) / case_count, 4
        ),
        "perfect_semantic_negation_violation_count": sum(
            score["negation_violation"] for score in new_scores
        ),
        "accepted_call_anchor_coverage": round(anchored / accepted, 4)
        if accepted
        else 1.0,
        "ungrounded_execution_count": ungrounded,
    }


def evaluate(config, dataset):
    _validate_inputs(config)
    ontology = load_v47_anchor_ontology()
    scope = audit_scope(dataset, ontology)
    probes = audit_probes(config, ontology)
    compilation = audit_perfect_semantic_compilation(dataset, ontology)
    metrics = {
        "requested_target_safe_anchor_recall": scope[
            "requested_target_safe_anchor_recall"
        ],
        "negated_target_blocked_all_recall": scope[
            "negated_target_blocked_all_recall"
        ],
        "cancelled_target_blocked_all_recall": scope[
            "cancelled_target_blocked_all_recall"
        ],
        "metamorphic_probe_pass_rate": probes["pass_rate"],
        "perfect_semantic_compiled_call_exact_accuracy": compilation[
            "perfect_semantic_compiled_call_exact_accuracy"
        ],
        "perfect_semantic_no_action_specificity": compilation[
            "perfect_semantic_no_action_specificity"
        ],
        "perfect_semantic_false_action_rate": compilation[
            "perfect_semantic_false_action_rate"
        ],
        "perfect_semantic_negation_violation_count": compilation[
            "perfect_semantic_negation_violation_count"
        ],
        "accepted_call_anchor_coverage": compilation[
            "accepted_call_anchor_coverage"
        ],
        "ungrounded_execution_count": compilation["ungrounded_execution_count"],
    }
    checks = {
        name: metrics[name] == expected
        for name, expected in config["development_gates"].items()
    }
    baseline_matches = (
        compilation["old_exact_count"]
        == config["expected_baseline"]["perfect_semantic_compiled_call_exact_count"]
    )
    passed = all(checks.values()) and baseline_matches and not compilation[
        "regressed_case_count"
    ]
    return {
        "schema": "uruha_target_relative_scope_development_analysis_v48",
        "evidence_status": "deterministic_gold_semantic_scope_and_compiler_diagnostic",
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "scope_audit": scope,
        "metamorphic_probes": probes,
        "perfect_semantic_compilation": compilation,
        "metrics": metrics,
        "baseline_reproduced": baseline_matches,
        "gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "v49_selective_router_development_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "decision": (
            "authorize_v49_selective_router_development"
            if passed
            else "reject_v48_target_relative_scope"
        ),
    }


def render_markdown(analysis):
    scope = analysis["scope_audit"]
    compilation = analysis["perfect_semantic_compilation"]
    return "\n".join(
        [
            "# V48 target-relative scope result",
            "",
            "| metric | result |",
            "|---|---:|",
            f"| Requested targets with a safe anchor | {scope['requested_target_safe_anchor_count']}/{scope['requested_target_count']} |",
            f"| Negated targets fully blocked | {scope['negated_target_blocked_all_count']}/{scope['negated_target_count']} |",
            f"| Cancelled targets fully blocked | {scope['cancelled_target_blocked_all_count']}/{scope['cancelled_target_count']} |",
            f"| Metamorphic probes | {analysis['metamorphic_probes']['passed_count']}/{analysis['metamorphic_probes']['probe_count']} |",
            f"| Old perfect-semantic call exact | {compilation['old_exact_count']}/{compilation['case_count']} |",
            f"| V48 perfect-semantic call exact | {compilation['new_exact_count']}/{compilation['case_count']} |",
            f"| Improved / regressed cases | {compilation['improved_case_count']} / {compilation['regressed_case_count']} |",
            "",
            f"- Gate passed: `{analysis['gate']['passed']}`",
            f"- Decision: `{analysis['decision']}`",
            "- Gold commitments were fixed; this isolates scope/compilation and does not claim better LLM reasoning.",
            "- Runtime and physical VRM execution remain unchanged.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    analysis = evaluate(load(CONFIG_PATH), load(DATASET_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {"gate_passed": analysis["gate"]["passed"], "decision": analysis["decision"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
