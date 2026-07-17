#!/usr/bin/env python3
"""Independently analyze the frozen V4 reflection holdout output."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_hybrid_classifier_v2_core import analyze_condition
from reflection_hybrid_classifier_v4_core import scorer_gates
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_preregistration.json"
)
AMENDMENT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_protocol_amendment.json"
)
CONSTRUCTION_CLOSURE_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_closure.json"
)
CARRIER_CONTRACT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
)
V3_RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_result_lock.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_harness_lock.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "reflection_hybrid_classifier_v4_independent_holdout.json"
)
RAW_PATH = (
    ROOT / "reports" / "reflection_hybrid_classifier_v4_independent_holdout_raw.json"
)
DEFAULT_JSON = (
    ROOT
    / "reports"
    / "reflection_hybrid_classifier_v4_independent_holdout_analysis.json"
)
DEFAULT_MD = (
    ROOT
    / "reports"
    / "reflection_hybrid_classifier_v4_independent_holdout_analysis.md"
)
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(report):
    result = report["matched_result"]
    classes = "\n".join(
        f"| {label} | {row['correct']}/{row['total']} | {row['accuracy']:.2%} |"
        for label, row in result["class_metrics"].items()
    )
    return f"""# Reflection Hybrid Classifier V4 Independent Holdout

| Condition | Correct | Accuracy |
|---|---:|---:|
| Frozen rules control | {result['rules_correct_count']}/32 | {result['rules_accuracy']:.2%} |
| Rules + frozen qwen3.5:4b tool fallback | {result['hybrid_correct_count']}/32 | {result['hybrid_accuracy']:.2%} |

| Candidate class | Correct | Accuracy |
|---|---:|---:|
{classes}

- Delta: {result['accuracy_delta']:+.2%}
- Newly correct: {result['newly_correct_count']}
- Regressions: {result['regression_count']}
- Critical false positives: {result['critical_false_positive_count']}
- Tool parse success: {result['parse_success_rate']:.2%}
- Median fallback latency: {result['median_fallback_wall_seconds']:.3f}s
- Warm p95 fallback latency: {result['warm_p95_fallback_wall_seconds']:.3f}s
- All frozen gates: **{'PASS' if result['all_gates_pass'] else 'FAIL'}**
- Decision: `{report['decision']}`

This is an ID-disjoint, same-corpus engineering holdout. Tatoeba provides source text, not reflection labels. It does not authorize memory writes or broad human-likeness claims.
"""


def analyze(raw_path=RAW_PATH, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite independent holdout analysis")
    preregistration = _load(PREREG_PATH)
    amendment = _load(AMENDMENT_PATH)
    contract = _load(CARRIER_CONTRACT_PATH)
    lock = _load(LOCK_PATH)
    dataset = _load(DATASET_PATH)
    raw = _load(raw_path)
    expected_hashes = {
        "preregistration_sha256": sha256(PREREG_PATH),
        "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
        "construction_closure_sha256": sha256(CONSTRUCTION_CLOSURE_PATH),
        "carrier_contract_sha256": sha256(CARRIER_CONTRACT_PATH),
        "v3_result_lock_sha256": sha256(V3_RESULT_LOCK_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
    }
    for key, expected in expected_hashes.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw result provenance drift: {key}")
    if raw["runner_branch"] != lock["required_run_branch"]:
        raise ValueError("raw result did not run from required branch")
    if raw["ollama_version"] != contract["local_runtime"]["ollama_version"]:
        raise ValueError("raw Ollama version drift")
    if raw["gold_label_passed_to_model"]:
        raise ValueError("gold label was exposed to model")
    if raw["runtime_memory_write_performed"]:
        raise ValueError("holdout run performed a runtime memory write")
    model = preregistration["frozen_system_conditions"]["selected_model"]
    digest = preregistration["frozen_system_conditions"]["selected_model_digest"]
    if raw["model"] != model or raw["model_snapshot"]["digest"] != digest:
        raise ValueError("frozen model identity drift")
    if raw["model_calls"] != len(raw["fallback_rows"]):
        raise ValueError("model-call accounting drift")
    if raw["model_calls"] != amendment["protocol_change"]["corrected_value"]:
        raise ValueError("holdout did not cover every required fallback")

    matched = analyze_condition(
        dataset["cases"],
        raw["rules_predictions"],
        raw["fallback_rows"],
        scorer_gates(preregistration, amendment),
    )
    if matched != raw["gate_snapshot"]:
        raise ValueError("runner gate snapshot drift")
    passed = matched["all_gates_pass"]
    decision = (
        preregistration["decision_rule"]["all_gates_pass"]
        if passed
        else preregistration["decision_rule"]["any_gate_fails"]
    )
    parse_error_counts = dict(
        sorted(
            Counter(
                row["parse_error"]
                for row in raw["fallback_rows"]
                if row["parse_error"] is not None
            ).items()
        )
    )
    report = {
        "schema": "uruha_reflection_hybrid_classifier_independent_holdout_analysis_v4",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_result_sha256": sha256(raw_path),
        **expected_hashes,
        "model": model,
        "model_calls": raw["model_calls"],
        "matched_result": matched,
        "parse_error_counts": parse_error_counts,
        "decision": decision,
        "shadow_integration_preregistration_authorized": passed,
        "runtime_memory_write_authorized": False,
        "official_benchmark_claim_authorized": False,
        "cross_corpus_generalization_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    analyze(args.raw, args.json, args.markdown)


if __name__ == "__main__":
    main()
