#!/usr/bin/env python3
"""Independently analyze indexed consolidation-admission V2 results."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from consolidation_admission_v2_indexed_core import (
    analyze_indexed_conditions,
)
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_development_preregistration.json"
)
CORRECTION_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_protocol_correction.json"
)
LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_harness_lock.json"
)
V1_CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
V1_RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_raw.json"
)
JSON_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_analysis.json"
)
MD_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_analysis.md"
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
    dataset = _load(dataset_path)
    for key, expected in {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_correction_sha256": sha256(CORRECTION_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "v1_preregistration_sha256": sha256(V1_CONFIG_PATH),
        "v1_core_sha256": sha256(
            ROOT / "consolidation_admission_v1_core.py"
        ),
        "v1_result_lock_sha256": sha256(V1_RESULT_LOCK_PATH),
    }.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw provenance drift: {key}")
    if raw.get("experiment_id") != config["experiment_id"]:
        raise ValueError("raw experiment identity drift")
    if not raw.get("completed_at"):
        raise ValueError("pilot collection is incomplete")
    if raw.get("gold_fields_passed_to_model"):
        raise ValueError("gold fields were exposed to the model")
    if raw.get("runtime_memory_write_performed"):
        raise ValueError("runtime memory write occurred")
    model_snapshot = raw.get("model_snapshot") or {}
    if model_snapshot.get("name") != config["model"]["name"]:
        raise ValueError("raw model name drift")
    if model_snapshot.get("digest") != config["model"]["digest"]:
        raise ValueError("raw model digest drift")

    control_rows = raw.get("control_rows") or []
    candidate_rows = raw.get("candidate_rows") or []
    expected_calls = config["success_gates"]["model_call_count_exact"]
    if raw.get("model_calls") != len(control_rows) + len(candidate_rows):
        raise ValueError("model call count does not match result rows")
    if raw.get("model_calls") != expected_calls:
        raise ValueError("model call count differs from preregistration")
    if raw.get("transport_attempts_made", 0) < raw["model_calls"]:
        raise ValueError("transport attempt count is impossible")

    result = analyze_indexed_conditions(
        dataset["cases"],
        control_rows,
        candidate_rows,
        config["success_gates"],
    )
    if result != raw.get("gate_snapshot"):
        raise ValueError("independent analysis differs from runner snapshot")
    passed = result["all_gates_pass"]
    return {
        "schema": "uruha_consolidation_admission_indexed_analysis_v2",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "evidence_status": "development_pilot_no_runtime_or_generalization_claim",
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_correction_sha256": sha256(CORRECTION_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "raw_result_sha256": sha256(raw_path),
        "model": config["model"],
        "matched_result": result,
        "transport_attempts_made": raw["transport_attempts_made"],
        "decision": (
            "authorize_separately_preregistered_new_session_japanese_rule_generation_pilot"
            if passed
            else "freeze_negative_result_and_leave_enabled_consolidation_unchanged"
        ),
        "same_dataset_retest_authorized": False,
        "post_admission_generation_pilot_authorized": passed,
        "runtime_memory_write_authorized": False,
        "runtime_shadow_authorized": False,
        "fresh_holdout_authorized": False,
        "official_benchmark_claim_authorized": False,
        "cross_corpus_generalization_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
        "biological_equivalence_claim_authorized": False,
        "downstream_dialogue_improvement_claim_authorized": False,
    }


def _markdown(analysis):
    result = analysis["matched_result"]
    control = result["control"]
    candidate = result["candidate"]
    lines = [
        "# Consolidation Admission Indexed Development Pilot V2",
        "",
        "| Condition | Correct | Accuracy | Median | Warm p95 |",
        "|---|---:|---:|---:|---:|",
        f"| Frozen V1 source-bound JSON | {control['correct_count']}/18 | {control['accuracy']:.2%} | {control['median_wall_seconds']:.3f}s | {control['warm_p95_wall_seconds']:.3f}s |",
        f"| V2 indexed tool frame | {candidate['correct_count']}/18 | {candidate['accuracy']:.2%} | {candidate['median_wall_seconds']:.3f}s | {candidate['warm_p95_wall_seconds']:.3f}s |",
        "",
        f"- Accuracy delta: {result['accuracy_delta_vs_control'] * 100:+.2f} percentage points",
        f"- Net correct gain: {result['net_correct_gain_vs_control']:+d} cases",
        f"- Wisdom: {result['class_metrics']['wisdom']['candidate_correct']}/6",
        f"- Procedural: {result['class_metrics']['procedural']['candidate_correct']}/6",
        f"- Episodic-only none: {result['class_metrics']['none']['candidate_correct']}/6",
        f"- Exact frame: {candidate['frame_exact_count']}/18",
        f"- Grounded evidence: {candidate['evidence_grounded_count']}/18",
        f"- Positive grounded evidence: {candidate['positive_evidence_grounded_count']}/12",
        f"- False long-term writes: {result['candidate_false_long_term_write_count']}",
        f"- Missed long-term writes: {result['candidate_missed_long_term_write_count']}",
        f"- Tool parse success: {candidate['parse_success_rate']:.2%}",
        f"- Index contract success: {candidate['index_contract_success_rate']:.2%}",
        f"- Successful model calls: {result['model_call_count']}",
        f"- Transport attempts: {analysis['transport_attempts_made']}",
        f"- All preregistered gates: **{'PASS' if result['all_gates_pass'] else 'FAIL'}**",
        f"- Decision: `{analysis['decision']}`",
        "",
        "This is a Codex-labeled development pilot, not an official benchmark "
        "or a runtime-memory test. It cannot establish broad human-like memory.",
        "",
    ]
    if result["newly_correct_case_ids"]:
        lines.append(
            "- Newly correct case IDs: "
            + ", ".join(result["newly_correct_case_ids"])
        )
    if result["regression_case_ids"]:
        lines.append(
            "- Regression case IDs: "
            + ", ".join(result["regression_case_ids"])
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
