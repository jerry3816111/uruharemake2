#!/usr/bin/env python3
"""Analyze the one-change V54 development replay."""

import argparse
import json
from pathlib import Path

from analyze_selective_discourse_state_v53 import (
    analyze as analyze_v53,
    render_markdown as render_v53_markdown,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
DEFAULT_RAW = ROOT / "reports" / "metalinguistic_nonrequest_v54_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "metalinguistic_nonrequest_v54_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "metalinguistic_nonrequest_v54_development_analysis.md"
V53_RAW_PATH = ROOT / "reports" / "selective_discourse_state_v53_development_raw.json"
V53_ANALYSIS_PATH = ROOT / "reports" / "selective_discourse_state_v53_development_analysis.json"
HYBRID = "selective_state_machine_with_v51_fallback"


def _gold(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }


def analyze(raw, dataset, config, v53_raw, v53_analysis):
    report = analyze_v53(raw, dataset, config)
    report["schema"] = "uruha_metalinguistic_nonrequest_development_analysis_v54"
    report["v54_correction_count"] = raw["v54_correction_count"]
    gold = _gold(dataset)
    before = {
        (row["case_id"], row["target_id"]): row["condition_commitments"][HYBRID]
        for row in v53_raw["target_rows"]
    }
    after = {
        (row["case_id"], row["target_id"]): row["condition_commitments"][HYBRID]
        for row in raw["target_rows"]
    }
    changed = [key for key in sorted(before) if before[key] != after[key]]
    corrected = [key for key in changed if after[key] == gold[key]]
    target_regressions = [
        key
        for key in before
        if before[key] == gold[key] and after[key] != gold[key]
    ]
    v53_call_failures = {
        row["case_id"]
        for row in v53_analysis["conditions"][HYBRID]["compiled_call_failures"]
    }
    v54_call_failures = {
        row["case_id"]
        for row in report["conditions"][HYBRID]["compiled_call_failures"]
    }
    new_call_regressions = sorted(v54_call_failures - v53_call_failures)
    specific = config["v54_specific_gates"]
    specific_checks = {
        "correction_count": len(changed) == specific["correction_count"],
        "corrected_rule_accuracy": (
            round(len(corrected) / len(changed), 4) if changed else 0.0
        )
        == specific["corrected_rule_accuracy"],
        "v53_previously_correct_target_regression_count": len(target_regressions)
        == specific["v53_previously_correct_target_regression_count"],
        "v53_previously_correct_call_regression_count": len(new_call_regressions)
        == specific["v53_previously_correct_call_regression_count"],
    }
    inherited_gate = report["development_gate"]
    specific_gate = {
        "passed": all(specific_checks.values()),
        "checks": specific_checks,
        "failed_checks": [name for name, ok in specific_checks.items() if not ok],
    }
    passed = inherited_gate["passed"] and specific_gate["passed"]
    report["inherited_development_gate"] = inherited_gate
    report["v54_specific_comparison"] = {
        "changed_target_count": len(changed),
        "changed_targets": [
            {
                "case_id": key[0],
                "target_id": key[1],
                "v53": before[key],
                "v54": after[key],
                "gold": gold[key],
            }
            for key in changed
        ],
        "corrected_target_count": len(corrected),
        "previously_correct_target_regression_count": len(target_regressions),
        "previously_correct_target_regressions": [
            {"case_id": key[0], "target_id": key[1]} for key in target_regressions
        ],
        "previously_correct_call_regression_count": len(new_call_regressions),
        "previously_correct_call_regression_case_ids": new_call_regressions,
    }
    report["v54_specific_gate"] = specific_gate
    report["development_gate"] = {
        "passed": passed,
        "checks": {
            **inherited_gate["checks"],
            **{f"v54_{name}": ok for name, ok in specific_checks.items()},
        },
        "failed_checks": inherited_gate["failed_checks"]
        + [f"v54_{name}" for name in specific_gate["failed_checks"]],
    }
    if passed:
        report["decision"] = "authorize_independent_v54_holdout_construction"
        report["interpretation"] = (
            "Separating metalinguistic denial of request status from explicit action prohibition "
            "passed every locked development gate with no model calls. This authorizes only a new "
            "independent holdout, not runtime, shadow integration, or physical VRM execution."
        )
    else:
        report["decision"] = report["decision"].replace("v53", "v54")
        report["interpretation"] = (
            "The one-change V54 correction did not satisfy every locked development gate. Close "
            "this version and do not tune it under the same preregistration."
        )
    return report


def render_markdown(report):
    body = render_v53_markdown(report)
    body = body.replace(
        "# V53 selective discourse-state development result",
        "# V54 metalinguistic non-request development result",
    )
    return body.replace(
        "No model was called during V53 replay",
        "No model was called during V54 replay",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = analyze(
        load(args.raw),
        load(DATASET_PATH),
        load(CONFIG_PATH),
        load(V53_RAW_PATH),
        load(V53_ANALYSIS_PATH),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "development_gate_passed": report["development_gate"]["passed"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
