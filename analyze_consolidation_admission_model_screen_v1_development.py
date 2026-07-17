#!/usr/bin/env python3
"""Independently analyze the consolidation-admission model screen V1."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from consolidation_admission_model_screen_v1_core import (
    CONDITIONS,
    analyze_model_screen,
)
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_harness_lock.json"
)
V3_RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_raw.json"
)
JSON_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_analysis.json"
)
MD_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_analysis.md"
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
        "v3_result_lock_sha256": sha256(V3_RESULT_LOCK_PATH),
    }.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw provenance drift: {key}")
    if raw.get("experiment_id") != config["experiment_id"]:
        raise ValueError("raw experiment identity drift")
    if not raw.get("completed_at"):
        raise ValueError("model-screen collection is incomplete")
    if raw.get("gold_fields_passed_to_model"):
        raise ValueError("gold fields were exposed to a model")
    if raw.get("runtime_memory_write_performed"):
        raise ValueError("runtime memory write occurred")
    if raw.get("inflight") is not None:
        raise ValueError("raw result contains an unresolved in-flight request")

    snapshots = raw.get("model_snapshots") or {}
    if set(snapshots) != set(CONDITIONS):
        raise ValueError("raw model snapshot condition drift")
    for condition in CONDITIONS:
        snapshot = snapshots[condition]
        frozen = config["models"][condition]
        if snapshot.get("ollama_tag") != frozen["ollama_tag"]:
            raise ValueError(f"raw model name drift: {condition}")
        if snapshot.get("digest") != frozen["digest"]:
            raise ValueError(f"raw model digest drift: {condition}")

    rows_by_condition = raw.get("rows_by_condition") or {}
    expected_calls = config["run_invariants"]["model_call_count_exact"]
    actual_rows = sum(len(rows) for rows in rows_by_condition.values())
    if raw.get("model_calls") != actual_rows:
        raise ValueError("model call count does not match result rows")
    if raw.get("model_calls") != expected_calls:
        raise ValueError("model call count differs from preregistration")
    if (
        raw.get("transport_attempts_made")
        != config["run_invariants"]["transport_attempt_count_exact"]
    ):
        raise ValueError("transport attempt count differs from preregistration")
    for condition in CONDITIONS:
        if (
            len(rows_by_condition.get(condition) or [])
            != config["run_invariants"]["calls_per_model_exact"]
        ):
            raise ValueError(f"condition call count drift: {condition}")

    result = analyze_model_screen(
        dataset["cases"],
        rows_by_condition,
        models=config["models"],
        eligibility_gates=config["eligibility_gates"],
        latency_gates=config["latency_gates"],
        run_invariants=config["run_invariants"],
        model_calls=raw["model_calls"],
        transport_attempts=raw["transport_attempts_made"],
    )
    if result != raw.get("gate_snapshot"):
        raise ValueError("independent analysis differs from runner snapshot")
    selected = result["selected_model_condition"]
    return {
        "schema": "uruha_consolidation_admission_model_screen_analysis_v1",
        "experiment_id": config["experiment_id"],
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "evidence_status": "development_model_screen_no_runtime_or_generalization_claim",
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "raw_result_sha256": sha256(raw_path),
        "models": config["models"],
        "model_screen_result": result,
        "decision": result["decision"],
        "selected_model_condition": selected,
        "selected_model": (
            config["models"][selected] if selected is not None else None
        ),
        "same_dataset_retest_authorized": False,
        "fresh_integration_pilot_authorized": selected is not None,
        "two_stage_architecture_development_authorized": selected is None,
        "single_call_model_replacement_continuation_authorized": (
            selected is not None
        ),
        "runtime_memory_write_authorized": False,
        "runtime_shadow_authorized": False,
        "fresh_holdout_authorized": False,
        "official_benchmark_claim_authorized": False,
        "cross_corpus_generalization_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
        "biological_equivalence_claim_authorized": False,
        "downstream_dialogue_improvement_claim_authorized": False,
        "general_model_superiority_claim_authorized": False,
    }


def _markdown(analysis):
    result = analysis["model_screen_result"]
    rows = [
        (
            "Qwen2.5 7B control",
            result["control"],
            None,
        )
    ]
    labels = {
        "qwen35_4b_candidate": "Qwen3.5 4B",
        "qwen35_9b_candidate": "Qwen3.5 9B",
    }
    for condition, label in labels.items():
        candidate = result["candidates"][condition]
        rows.append((label, candidate["summary"], candidate))
    lines = [
        "# Consolidation Admission Model Screen V1",
        "",
        "| Model | Correct | W / P / N | Frame | Evidence | Parse / index | False / missed | Median / warm p95 | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, summary, candidate in rows:
        classes = summary["class_metrics"]
        eligible = "-" if candidate is None else str(candidate["eligible"])
        lines.append(
            f"| {label} | {summary['correct_count']}/12 "
            f"({summary['accuracy']:.2%}) | "
            f"{classes['wisdom']['correct_count']} / "
            f"{classes['procedural']['correct_count']} / "
            f"{classes['none']['correct_count']} | "
            f"{summary['semantic_frame_exact_count']}/12 | "
            f"{summary['evidence_grounded_count']}/12 | "
            f"{summary['parse_success_count']}/12 / "
            f"{summary['index_contract_success_count']}/12 | "
            f"{summary['false_long_term_write_count']} / "
            f"{summary['missed_long_term_write_count']} | "
            f"{summary['median_wall_seconds']:.3f}s / "
            f"{summary['warm_p95_wall_seconds']:.3f}s | {eligible} |"
        )
    lines.extend(
        [
            "",
            "## Paired changes versus Qwen2.5 7B",
            "",
            "| Candidate | Newly correct | Regressions | Net gain |",
            "|---|---:|---:|---:|",
        ]
    )
    for condition, label in labels.items():
        paired = result["candidates"][condition]["paired_vs_control"]
        lines.append(
            f"| {label} | {paired['newly_correct_count']} | "
            f"{paired['regression_count']} | "
            f"{paired['net_correct_gain_vs_control']:+d} |"
        )
    lines.extend(
        [
            "",
            f"- Exact model calls: {result['model_call_count']}",
            f"- Exact transport attempts: {result['transport_attempt_count']}",
            f"- Selected condition: `{result['selected_model_condition']}`",
            f"- Decision: `{analysis['decision']}`",
            "",
            "This is a Codex-labeled development model screen on one frozen "
            "memory-admission contract. It is not an official benchmark, "
            "runtime-memory test, or evidence of broad human-like memory.",
            "",
        ]
    )
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
