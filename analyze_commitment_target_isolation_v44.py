#!/usr/bin/env python3
"""Analyze the four frozen V44 semantic isolation conditions."""

import argparse
import json
from pathlib import Path

from analyze_relational_commitment_context_v43 import evaluate_gate, summarize_condition


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
PREREG_PATH = ROOT / "configs" / "commitment_carrier_target_isolation_v44_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
AUDIT_PATH = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
V42_CONTROL_PATH = ROOT / "reports" / "grounded_commitment_classifier_v42_development_analysis.json"
V43_CONTROL_PATH = ROOT / "reports" / "relational_commitment_context_v43_development_analysis.json"
CARRIER_ANALYSIS_PATH = ROOT / "reports" / "commitment_carrier_v44_probe_analysis.json"
DEFAULT_RAW = ROOT / "reports" / "commitment_target_isolation_v44_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "commitment_target_isolation_v44_development_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "commitment_target_isolation_v44_development_analysis.md"


def _gold(dataset):
    return {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }


def _prediction_map(summary):
    return {
        (row["case_id"], row["target_id"]): row["commitment"]
        for row in summary["target_predictions"]
    }


def _transition(before_name, after_name, summaries, gold):
    before = _prediction_map(summaries[before_name])
    after = _prediction_map(summaries[after_name])
    fixed = []
    regressed = []
    for key, expected in gold.items():
        row = {"case_id": key[0], "target_id": key[1], "gold_commitment": expected}
        if before.get(key) != expected and after.get(key) == expected:
            fixed.append({**row, "before": before.get(key), "after": after.get(key)})
        if before.get(key) == expected and after.get(key) != expected:
            regressed.append({**row, "before": before.get(key), "after": after.get(key)})
    return {"fixed": fixed, "regressed": regressed}


def analyze(raw, dataset, audit, lock, prereg, v42, v43, carrier):
    summaries = {
        condition: summarize_condition(raw, dataset, audit, condition)
        for condition in lock["conditions"]
    }
    transitions = {}
    for before, after in zip(lock["conditions"], lock["conditions"][1:]):
        transitions[f"{before}_to_{after}"] = _transition(
            before, after, summaries, _gold(dataset)
        )
    candidate = lock["only_candidate_allowed_to_advance"]
    gate = evaluate_gate(summaries[candidate], prereg["development_gates"])
    return {
        "schema": "uruha_commitment_target_isolation_development_analysis_v44",
        "evidence_status": raw["evidence_status"],
        "selected_carrier": raw["selected_carrier"],
        "carrier_probe": carrier,
        "historical_controls": {
            "v42_two_field_with_evidence_index": v42["conditions"]["commitment_qwen3_5_4b"],
            "v43_one_field_relational": v43["conditions"]["relational_context_candidate"],
        },
        "conditions": summaries,
        "causal_transitions": transitions,
        "candidate_gate": gate,
        "development_gate_passed": gate["passed"],
        "fresh_holdout_authorized": gate["passed"],
        "runtime_change_authorized": False,
        "shadow_integration_authorized": False,
        "physical_vrm_execution_enabled": False,
        "decision": (
            "authorize_fresh_v44_holdout_freeze"
            if gate["passed"]
            else "stop_v44_before_holdout_and_runtime"
        ),
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def render_markdown(analysis):
    lines = [
        "# V44 carrier and target-isolation development result",
        "",
        f"Selected non-semantic carrier: `{analysis['selected_carrier']}`",
        "",
        "| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, row in analysis["conditions"].items():
        lines.append(
            f"| {condition} | {_pct(row['classifier_parse_success_rate'])} | "
            f"{_pct(row['commitment_accuracy'])} | {_pct(row['requested_commitment_precision'])} / "
            f"{_pct(row['requested_commitment_recall'])} | {_pct(row['supported_frame_case_exact_rate'])} | "
            f"{_pct(row['compiled_call_exact_accuracy'])} | {_pct(row['selected_evidence_support_rate'])} | "
            f"{row['p95_case_latency_seconds']:.2f}s |"
        )
    lines.extend(["", "## Causal transitions", ""])
    for name, row in analysis["causal_transitions"].items():
        lines.append(f"- `{name}`: fixed {len(row['fixed'])}, regressed {len(row['regressed'])}")
    lines.extend(
        [
            "",
            f"- Candidate passed: `{analysis['candidate_gate']['passed']}`",
            f"- Failed checks: `{analysis['candidate_gate']['failed_checks']}`",
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
        loads(args.raw),
        loads(DATASET_PATH),
        loads(AUDIT_PATH),
        loads(LOCK_PATH),
        loads(PREREG_PATH),
        loads(V42_CONTROL_PATH),
        loads(V43_CONTROL_PATH),
        loads(CARRIER_ANALYSIS_PATH),
    )
    args.json_output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({"development_gate_passed": analysis["development_gate_passed"], "decision": analysis["decision"]}, indent=2))


if __name__ == "__main__":
    main()
