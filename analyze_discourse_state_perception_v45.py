#!/usr/bin/env python3
"""Analyze V45 discourse-state perception and its no-regression rule."""

import argparse
import json
from pathlib import Path

from analyze_commitment_target_isolation_v44 import _transition
from analyze_relational_commitment_context_v43 import evaluate_gate, summarize_condition
from run_discourse_state_perception_v45 import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
AUDIT_PATH = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
V44_PATH = ROOT / "reports" / "commitment_target_isolation_v44_development_analysis.json"
DEFAULT_RAW = ROOT / "reports" / "discourse_state_perception_v45_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "discourse_state_perception_v45_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "discourse_state_perception_v45_development_analysis.md"
CANDIDATE = "taxonomy_plus_discourse_signals_candidate"


def _gold(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def evaluate_development_decision(metric_gate, v44_to_v45):
    no_regression = not v44_to_v45["regressed"]
    return {
        "passed": bool(metric_gate["passed"] and no_regression),
        "no_semantic_regression_vs_v44": no_regression,
    }


def analyze(raw, dataset, audit, config, v44):
    summaries = {
        condition: summarize_condition(raw, dataset, audit, condition)
        for condition in CONDITIONS
    }
    definition_to_signal = _transition(
        CONDITIONS[0], CONDITIONS[1], summaries, _gold(dataset)
    )
    comparison = {
        "v44": v44["conditions"]["isolated_scope_signals_candidate"],
        "v45": summaries[CANDIDATE],
    }
    v44_to_v45 = _transition("v44", "v45", comparison, _gold(dataset))
    metric_gate = evaluate_gate(summaries[CANDIDATE], config["development_gates"])
    decision_gate = evaluate_development_decision(metric_gate, v44_to_v45)
    passed = decision_gate["passed"]
    return {
        "schema": "uruha_discourse_state_perception_development_analysis_v45",
        "evidence_status": raw["evidence_status"],
        "v44_control": comparison["v44"],
        "conditions": summaries,
        "definition_to_signal_attribution": definition_to_signal,
        "v44_to_v45_attribution": v44_to_v45,
        "metric_gate": metric_gate,
        "no_semantic_regression_vs_v44": decision_gate[
            "no_semantic_regression_vs_v44"
        ],
        "development_gate_passed": passed,
        "fresh_holdout_authorized": passed,
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "decision": (
            "authorize_fresh_v45_holdout_freeze"
            if passed
            else "stop_v45_before_holdout_and_runtime"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V45 discourse-state perception development result",
        "",
        "| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows = {"v44_final_control": analysis["v44_control"], **analysis["conditions"]}
    for name, row in rows.items():
        lines.append(
            f"| {name} | {_pct(row['classifier_parse_success_rate'])} | {_pct(row['commitment_accuracy'])} | "
            f"{_pct(row['requested_commitment_precision'])} / {_pct(row['requested_commitment_recall'])} | "
            f"{_pct(row['supported_frame_case_exact_rate'])} | {_pct(row['compiled_call_exact_accuracy'])} | "
            f"{_pct(row['selected_evidence_support_rate'])} | {row['p95_case_latency_seconds']:.2f}s |"
        )
    lines.extend(
        [
            "",
            f"- Definition -> signals: fixed {len(analysis['definition_to_signal_attribution']['fixed'])}, regressed {len(analysis['definition_to_signal_attribution']['regressed'])}",
            f"- V44 -> V45: fixed {len(analysis['v44_to_v45_attribution']['fixed'])}, regressed {len(analysis['v44_to_v45_attribution']['regressed'])}",
            f"- Metric gate passed: `{analysis['metric_gate']['passed']}`",
            f"- No semantic regression: `{analysis['no_semantic_regression_vs_v44']}`",
            f"- Decision: `{analysis['decision']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    loads = lambda path: json.loads(path.read_text(encoding="utf-8"))
    analysis = analyze(
        loads(args.raw), loads(DATASET_PATH), loads(AUDIT_PATH), loads(CONFIG_PATH), loads(V44_PATH)
    )
    args.json_output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({"development_gate_passed": analysis["development_gate_passed"], "decision": analysis["decision"]}, indent=2))


if __name__ == "__main__":
    main()
