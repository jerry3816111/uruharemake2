#!/usr/bin/env python3
"""Independently analyze the frozen V6 reflection-admission pilot."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_admission_v6_core import analyze_admission_condition
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_evidence_gate_development_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "reflection_admission_v6_evidence_gate_harness_lock.json"
)
RAW_PATH = (
    ROOT / "reports" / "reflection_admission_v6_evidence_gate_development_raw.json"
)
JSON_OUTPUT = (
    ROOT
    / "reports"
    / "reflection_admission_v6_evidence_gate_development_analysis.json"
)
MD_OUTPUT = (
    ROOT
    / "reports"
    / "reflection_admission_v6_evidence_gate_development_analysis.md"
)
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def analyze(raw_path=RAW_PATH):
    config = _load(CONFIG_PATH)
    raw = _load(raw_path)
    dataset_path = ROOT / config["dataset"]["path"]
    closure_path = ROOT / config["construction_closure"]["path"]
    dataset = _load(dataset_path)
    expected_hashes = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "construction_closure_sha256": sha256(closure_path),
        "dataset_sha256": sha256(dataset_path),
    }
    for key, expected in expected_hashes.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw provenance drift: {key}")
    if not raw.get("completed_at"):
        raise ValueError("pilot collection is incomplete")
    if raw.get("gold_label_passed_to_model"):
        raise ValueError("gold label was exposed to the model")
    if raw.get("runtime_memory_write_performed"):
        raise ValueError("runtime memory write occurred")
    model_snapshot = raw.get("model_snapshot") or {}
    if model_snapshot.get("name") != config["model"]["name"]:
        raise ValueError("raw model name drift")
    if model_snapshot.get("digest") != config["model"]["digest"]:
        raise ValueError("raw model digest drift")
    rows = raw.get("candidate_rows") or []
    if raw.get("model_calls") != len(rows):
        raise ValueError("model call count does not match candidate rows")
    if len(rows) != config["success_gates"]["model_call_count_exact"]:
        raise ValueError("model call count differs from preregistration")

    result = analyze_admission_condition(
        dataset["cases"], rows, config["success_gates"]
    )
    if result != raw.get("gate_snapshot"):
        raise ValueError("independent analysis differs from runner snapshot")
    passed = result["all_gates_pass"]
    decision = (
        "authorize_separate_full_pipeline_development_integration_preregistration_only"
        if passed
        else "freeze_negative_result_and_abandon_exact_evidence_gate_contract"
    )
    return {
        "schema": "uruha_reflection_admission_evidence_gate_development_analysis_v6",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "evidence_status": "development_pilot_no_runtime_or_generalization_claim",
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "construction_closure_sha256": sha256(closure_path),
        "dataset_sha256": sha256(dataset_path),
        "raw_result_sha256": sha256(raw_path),
        "model": config["model"],
        "matched_result": result,
        "decision": decision,
        "full_pipeline_development_integration_preregistration_authorized": passed,
        "same_dataset_retest_authorized": False,
        "runtime_memory_write_authorized": False,
        "runtime_shadow_authorized": False,
        "fresh_holdout_authorized": False,
        "official_benchmark_claim_authorized": False,
        "cross_corpus_generalization_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
        "downstream_dialogue_improvement_claim_authorized": False,
    }


def _markdown(analysis):
    result = analysis["matched_result"]
    lines = [
        "# Reflection Admission Evidence-Gate Development Pilot V6",
        "",
        "| Condition | Correct | Accuracy |",
        "|---|---:|---:|",
        f"| Admit every proposed procedural reflection | {result['control_correct_count']}/32 | {result['control_accuracy']:.2%} |",
        f"| Qwen 3.5 4B evidence gate | {result['candidate_correct_count']}/32 | {result['candidate_accuracy']:.2%} |",
        "",
        f"- Accuracy delta: {result['accuracy_delta_vs_control'] * 100:+.2f} percentage points",
        f"- Net correct gain: {result['net_correct_gain_vs_control']:+d} cases",
        f"- Explicit instructions retained: {result['class_metrics']['admit']['correct']}/{result['class_metrics']['admit']['total']}",
        f"- Unsupported proposals rejected: {result['class_metrics']['reject']['correct']}/{result['class_metrics']['reject']['total']}",
        f"- False admits: {result['false_admit_count']}",
        f"- False rejects: {result['false_reject_count']}",
        f"- Tool parse success: {result['parse_success_rate']:.2%}",
        f"- Exact evidence contract success: {result['evidence_contract_success_rate']:.2%}",
        f"- Median wall time: {result['median_wall_seconds']:.3f}s",
        f"- Warm p95 wall time: {result['warm_p95_wall_seconds']:.3f}s",
        f"- All preregistered gates: **{'PASS' if result['all_gates_pass'] else 'FAIL'}**",
        f"- Decision: `{analysis['decision']}`",
        "",
        "This is one development-only test on a Codex-labeled Tatoeba sample. "
        "It does not authorize runtime memory writes, a fresh holdout, or a broad "
        "claim about human-like dialogue.",
        "",
    ]
    if result["false_admit_case_ids"]:
        lines.append(
            "- False-admit case IDs: "
            + ", ".join(result["false_admit_case_ids"])
        )
    if result["false_reject_case_ids"]:
        lines.append(
            "- False-reject case IDs: "
            + ", ".join(result["false_reject_case_ids"])
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--json-output", type=Path, default=JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=MD_OUTPUT)
    args = parser.parse_args()
    analysis = analyze(args.raw)
    _atomic_write(
        args.json_output,
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write(args.md_output, _markdown(analysis))
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
