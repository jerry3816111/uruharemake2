#!/usr/bin/env python3
"""Independently analyze consolidation-admission cascade V1."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from consolidation_admission_cascade_v1_core import analyze_cascade
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_harness_lock.json"
)
MODEL_SCREEN_RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_raw.json"
)
JSON_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_analysis.json"
)
MD_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_analysis.md"
)
MODEL_KEYS = (
    "stage1_write_gate",
    "direct_control_and_stage2_classifier",
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
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "model_screen_result_lock_sha256": sha256(
            MODEL_SCREEN_RESULT_LOCK_PATH
        ),
    }.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw provenance drift: {key}")
    if raw.get("experiment_id") != config["experiment_id"]:
        raise ValueError("raw experiment identity drift")
    if not raw.get("completed_at"):
        raise ValueError("cascade collection is incomplete")
    if raw.get("gold_fields_passed_to_model"):
        raise ValueError("gold fields were exposed to a model")
    if raw.get("runtime_memory_write_performed"):
        raise ValueError("runtime memory write occurred")
    if raw.get("inflight") is not None:
        raise ValueError("raw result contains an unresolved in-flight request")

    snapshots = raw.get("model_snapshots") or {}
    if set(snapshots) != set(MODEL_KEYS):
        raise ValueError("raw model snapshot key drift")
    for model_key in MODEL_KEYS:
        snapshot = snapshots[model_key]
        frozen = config["models"][model_key]
        if snapshot.get("ollama_tag") != frozen["ollama_tag"]:
            raise ValueError(f"raw model name drift: {model_key}")
        if snapshot.get("digest") != frozen["digest"]:
            raise ValueError(f"raw model digest drift: {model_key}")

    control_rows = raw.get("control_rows") or []
    stage1_rows = raw.get("stage1_rows") or []
    stage2_rows = raw.get("stage2_rows") or []
    actual_calls = len(control_rows) + len(stage1_rows) + len(stage2_rows)
    stage1_writes = sum(
        row.get("admission_decision") == "write" for row in stage1_rows
    )
    invariants = config["run_invariants"]
    if len(control_rows) != invariants["control_calls_exact"]:
        raise ValueError("control call count drift")
    if len(stage1_rows) != invariants["stage1_calls_exact"]:
        raise ValueError("stage1 call count drift")
    if len(stage2_rows) != stage1_writes:
        raise ValueError("stage2 call count differs from compiled writes")
    if raw.get("model_calls") != actual_calls:
        raise ValueError("model call count does not match result rows")
    if actual_calls > invariants["total_model_calls_max"]:
        raise ValueError("model call count exceeds preregistered maximum")
    if raw.get("transport_attempts_made") != actual_calls:
        raise ValueError("transport attempts differ from model calls")

    result = analyze_cascade(
        dataset["cases"],
        control_rows,
        stage1_rows,
        stage2_rows,
        success_gates=config["success_gates"],
        run_invariants=invariants,
        model_calls=raw["model_calls"],
        transport_attempts=raw["transport_attempts_made"],
    )
    if result != raw.get("gate_snapshot"):
        raise ValueError("independent analysis differs from runner snapshot")
    passed = result["all_gates_pass"]
    return {
        "schema": "uruha_consolidation_admission_cascade_analysis_v1",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "evidence_status": (
            "development_cascade_no_runtime_or_generalization_claim"
        ),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "raw_result_sha256": sha256(raw_path),
        "models": config["models"],
        "cascade_result": result,
        "decision": result["decision"],
        "same_dataset_retest_authorized": False,
        "runtime_adapter_development_authorized": passed,
        "fresh_shadow_pilot_preregistration_authorized": passed,
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
    result = analysis["cascade_result"]
    control = result["control"]
    candidate = result["candidate"]
    stage1 = result["stage1"]
    stage2 = result["stage2"]
    paired = result["paired_vs_control"]
    lines = [
        "# Consolidation Admission Cascade V1",
        "",
        "| Condition | Correct | W / P / N | False / missed | Median | Warm p95 |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| Direct Qwen3.5 9B | {control['correct_count']}/12 "
            f"({control['accuracy']:.2%}) | "
            f"{control['class_metrics']['wisdom']['correct_count']} / "
            f"{control['class_metrics']['procedural']['correct_count']} / "
            f"{control['class_metrics']['none']['correct_count']} | "
            f"{control['false_long_term_write_count']} / "
            f"{control['missed_long_term_write_count']} | "
            f"{control['median_wall_seconds']:.3f}s | "
            f"{control['warm_p95_wall_seconds']:.3f}s |"
        ),
        (
            f"| Conditional 4B to 9B | {candidate['correct_count']}/12 "
            f"({candidate['accuracy']:.2%}) | "
            f"{candidate['class_metrics']['wisdom']['correct_count']} / "
            f"{candidate['class_metrics']['procedural']['correct_count']} / "
            f"{candidate['class_metrics']['none']['correct_count']} | "
            f"{candidate['false_long_term_write_count']} / "
            f"{candidate['missed_long_term_write_count']} | "
            f"{candidate['median_wall_seconds']:.3f}s | "
            f"{candidate['warm_p95_wall_seconds']:.3f}s |"
        ),
        "",
        "## Conditional computation",
        "",
        f"- Stage 1 writes: {stage1['write_count']}/12",
        f"- Stage 2 calls: {stage2['call_count']}/12",
        (
            f"- Newly correct / regressions / net: "
            f"{paired['newly_correct_count']} / "
            f"{paired['regression_count']} / "
            f"{paired['net_correct_gain_vs_control']:+d}"
        ),
        f"- Total model calls: {result['model_call_count']}",
        f"- All preregistered gates pass: {result['all_gates_pass']}",
        f"- Decision: `{analysis['decision']}`",
        "",
        (
            "This is a Codex-labeled development pilot on one frozen "
            "memory-admission contract. It does not test runtime memory "
            "writes, retrieval, dialogue quality, or broad human likeness."
        ),
        "",
    ]
    return "\n".join(lines)


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
