#!/usr/bin/env python3
"""Evaluate V47 candidate grounding without invoking an LLM."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_candidate_perception_v47_preregistration.json"
V37_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
V45_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_JSON = ROOT / "reports" / "action_candidate_perception_v47_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "action_candidate_perception_v47_development_analysis.md"
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
                raise ValueError(f"V47 frozen input hash mismatch: {path.name}")


def _gold_targets(case):
    return {
        (frame["domain"], frame["value"])
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _candidate_targets(user_input, ontology):
    return {
        (row["domain"], row["value"])
        for row in ground_supported_targets(user_input, ontology)
    }


def audit_dataset(dataset, ontology):
    true_positive = 0
    gold_total = 0
    candidate_total = 0
    missing = []
    extra = []
    per_case = []
    for case in dataset["cases"]:
        gold = _gold_targets(case)
        candidates = _candidate_targets(case["user_input"], ontology)
        matched = gold & candidates
        gold_total += len(gold)
        candidate_total += len(candidates)
        true_positive += len(matched)
        for target in sorted(gold - candidates):
            missing.append({"case_id": case["id"], "target": list(target)})
        for target in sorted(candidates - gold):
            extra.append({"case_id": case["id"], "target": list(target)})
        per_case.append(
            {
                "case_id": case["id"],
                "gold": [list(target) for target in sorted(gold)],
                "candidates": [list(target) for target in sorted(candidates)],
            }
        )
    return {
        "case_count": len(dataset["cases"]),
        "gold_supported_target_count": gold_total,
        "candidate_target_count": candidate_total,
        "true_positive_target_count": true_positive,
        "supported_target_recall": round(true_positive / gold_total, 4) if gold_total else 1.0,
        "candidate_precision": round(true_positive / candidate_total, 4)
        if candidate_total
        else 1.0,
        "missing_target_count": len(missing),
        "missing_targets": missing,
        "extra_candidate_count": len(extra),
        "extra_candidates": extra,
        "per_case": per_case,
    }


def _probe_audit(probes, ontology):
    rows = []
    for text in probes:
        candidates = _candidate_targets(text, ontology)
        rows.append(
            {
                "text": text,
                "point_candidate": ("motion", "point") in candidates,
                "all_candidates": [list(target) for target in sorted(candidates)],
            }
        )
    return rows


def _nonpoint_change_count(datasets, baseline, candidate):
    changes = []
    for dataset_name, dataset in datasets.items():
        for case in dataset["cases"]:
            before = _candidate_targets(case["user_input"], baseline) - {
                ("motion", "point")
            }
            after = _candidate_targets(case["user_input"], candidate) - {
                ("motion", "point")
            }
            if before != after:
                changes.append(
                    {
                        "dataset": dataset_name,
                        "case_id": case["id"],
                        "before": [list(target) for target in sorted(before)],
                        "after": [list(target) for target in sorted(after)],
                    }
                )
    return changes


def evaluate(config, v37, v45):
    _validate_inputs(config)
    baseline = load_v39_anchor_ontology()
    candidate = load_v47_anchor_ontology()
    positive_baseline = _probe_audit(config["positive_pointing_probes"], baseline)
    positive_candidate = _probe_audit(config["positive_pointing_probes"], candidate)
    negative_baseline = _probe_audit(
        config["negative_instruction_and_finger_probes"], baseline
    )
    negative_candidate = _probe_audit(
        config["negative_instruction_and_finger_probes"], candidate
    )
    baseline_results = {
        "v37": audit_dataset(v37, baseline),
        "v45": audit_dataset(v45, baseline),
    }
    candidate_results = {
        "v37": audit_dataset(v37, candidate),
        "v45": audit_dataset(v45, candidate),
    }
    nonpoint_changes = _nonpoint_change_count(
        {"v37": v37, "v45": v45}, baseline, candidate
    )
    positive_hits = sum(row["point_candidate"] for row in positive_candidate)
    negative_false_positives = sum(
        row["point_candidate"] for row in negative_candidate
    )
    metrics = {
        "v37_supported_target_recall": candidate_results["v37"][
            "supported_target_recall"
        ],
        "v37_candidate_precision": candidate_results["v37"]["candidate_precision"],
        "v45_supported_target_recall": candidate_results["v45"][
            "supported_target_recall"
        ],
        "v45_candidate_precision": candidate_results["v45"]["candidate_precision"],
        "v45_extra_candidate_count": candidate_results["v45"][
            "extra_candidate_count"
        ],
        "positive_probe_recall": round(
            positive_hits / len(positive_candidate), 4
        ),
        "negative_probe_false_positive_count": negative_false_positives,
        "non_point_candidate_set_change_count": len(nonpoint_changes),
    }
    gates = config["development_gates"]
    checks = {name: metrics[name] == expected for name, expected in gates.items()}
    passed = all(checks.values())
    return {
        "schema": "uruha_action_candidate_perception_development_analysis_v47",
        "evidence_status": "internal_deterministic_regression_and_metamorphic_probe",
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "baseline": baseline_results,
        "candidate": candidate_results,
        "probes": {
            "positive_baseline": positive_baseline,
            "positive_candidate": positive_candidate,
            "negative_baseline": negative_baseline,
            "negative_candidate": negative_candidate,
        },
        "nonpoint_changes": nonpoint_changes,
        "metrics": metrics,
        "gate": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [name for name, ok in checks.items() if not ok],
        },
        "selective_router_development_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "decision": (
            "authorize_v47_overlay_for_selective_router_development"
            if passed
            else "reject_v47_point_anchor_overlay"
        ),
    }


def render_markdown(analysis):
    before = analysis["baseline"]
    after = analysis["candidate"]
    metrics = analysis["metrics"]
    return "\n".join(
        [
            "# V47 action-candidate perception result",
            "",
            "| dataset | old recall / precision / extras | V47 recall / precision / extras |",
            "|---|---:|---:|",
            f"| V37 development | {before['v37']['supported_target_recall']:.4f} / {before['v37']['candidate_precision']:.4f} / {before['v37']['extra_candidate_count']} | {after['v37']['supported_target_recall']:.4f} / {after['v37']['candidate_precision']:.4f} / {after['v37']['extra_candidate_count']} |",
            f"| retired V45 development | {before['v45']['supported_target_recall']:.4f} / {before['v45']['candidate_precision']:.4f} / {before['v45']['extra_candidate_count']} | {after['v45']['supported_target_recall']:.4f} / {after['v45']['candidate_precision']:.4f} / {after['v45']['extra_candidate_count']} |",
            "",
            f"- Positive pointing probes: {metrics['positive_probe_recall']:.1%}",
            f"- Negative instruction/finger false positives: {metrics['negative_probe_false_positive_count']}",
            f"- Non-point candidate changes: {metrics['non_point_candidate_set_change_count']}",
            f"- Gate passed: `{analysis['gate']['passed']}`",
            f"- Decision: `{analysis['decision']}`",
            "- Runtime remains unchanged; this overlay is only authorized for the next development experiment.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    analysis = evaluate(load(CONFIG_PATH), load(V37_PATH), load(V45_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "gate_passed": analysis["gate"]["passed"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
