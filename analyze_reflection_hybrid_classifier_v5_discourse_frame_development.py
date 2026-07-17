#!/usr/bin/env python3
"""Independently analyze the frozen V5 discourse-frame development pilot."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_hybrid_classifier_v5_core import analyze_discourse_frame_condition
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_development_preregistration.json"
AMENDMENT_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_protocol_amendment.json"
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_harness_lock.json"
RAW_PATH = ROOT / "reports" / "reflection_hybrid_classifier_v5_discourse_frame_development_raw.json"
JSON_OUTPUT = ROOT / "reports" / "reflection_hybrid_classifier_v5_discourse_frame_development_analysis.json"
MD_OUTPUT = ROOT / "reports" / "reflection_hybrid_classifier_v5_discourse_frame_development_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _control_rows(config):
    analysis = _load(ROOT / config["frozen_control"]["analysis_path"])
    return analysis["analyses"][config["model"]["name"]]["rows"]


def analyze(raw_path=RAW_PATH):
    config = _load(CONFIG_PATH)
    amendment = _load(AMENDMENT_PATH)
    raw = _load(raw_path)
    dataset_path = ROOT / config["dataset"]["path"]
    dataset = _load(dataset_path)
    expected_hashes = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(dataset_path),
        "frozen_control_result_lock_sha256": sha256(
            ROOT / config["frozen_control"]["result_lock_path"]
        ),
        "frozen_control_analysis_sha256": sha256(
            ROOT / config["frozen_control"]["analysis_path"]
        ),
    }
    for key, expected in expected_hashes.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw provenance drift: {key}")
    if not raw.get("completed_at"):
        raise ValueError("pilot collection is incomplete")
    if raw.get("gold_label_passed_to_model"):
        raise ValueError("gold label was exposed to the model")
    if raw.get("fresh_v4_holdout_loaded"):
        raise ValueError("forbidden V4 holdout was loaded")
    if raw.get("runtime_memory_write_performed"):
        raise ValueError("runtime memory write occurred")
    model_snapshot = raw.get("model_snapshot") or {}
    if model_snapshot.get("name") != config["model"]["name"]:
        raise ValueError("raw model name drift")
    if model_snapshot.get("digest") != config["model"]["digest"]:
        raise ValueError("raw model digest drift")
    expected_calls = len(raw.get("live_control_fallback_rows") or []) + len(
        raw.get("candidate_fallback_rows") or []
    )
    if raw.get("model_calls") != expected_calls:
        raise ValueError("model call count does not match fallback rows")

    result = analyze_discourse_frame_condition(
        dataset["cases"],
        raw["rules_predictions"],
        _control_rows(config),
        raw["live_control_fallback_rows"],
        raw["candidate_fallback_rows"],
        amendment["unchanged_candidate_capability_gates"],
        amendment["live_control_reproduction_gates"],
        amendment["correction"]["total_model_call_count_exact"],
    )
    if result != raw["gate_snapshot"]:
        raise ValueError("independent analysis differs from runner snapshot")
    decision = (
        "authorize_new_cross_corpus_holdout_preregistration_only"
        if result["all_gates_pass"]
        else "freeze_negative_result_and_abandon_exact_discourse_frame_contract"
    )
    frame_rows = [
        {
            "id": row["id"],
            "observed_type": row["observed_type"],
            "parse_success": row["parse_success"],
            "discourse_frame": row["discourse_frame"],
        }
        for row in raw["candidate_fallback_rows"]
    ]
    return {
        "schema": "uruha_reflection_hybrid_classifier_discourse_frame_development_analysis_v5",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "raw_result_sha256": sha256(raw_path),
        "model": config["model"],
        "matched_result": result,
        "fallback_frames": frame_rows,
        "decision": decision,
        "fresh_holdout_preregistration_authorized": result["all_gates_pass"],
        "runtime_memory_write_authorized": False,
        "runtime_shadow_authorized": False,
        "official_benchmark_claim_authorized": False,
        "cross_corpus_generalization_claim_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _markdown(analysis):
    result = analysis["matched_result"]
    lines = [
        "# Reflection Discourse-Frame Development Pilot V5",
        "",
        "| Condition | Correct | Accuracy |",
        "|---|---:|---:|",
        f"| Historical frozen V3 direct carrier | {result['frozen_control_correct_count']}/32 | {result['frozen_control_accuracy']:.2%} |",
        f"| Live matched direct carrier | {result['live_control_correct_count']}/32 | {result['live_control_accuracy']:.2%} |",
        f"| V5 structured discourse frame | {result['candidate_correct_count']}/32 | {result['candidate_accuracy']:.2%} |",
        "",
        "| Candidate class | Correct | Accuracy |",
        "|---|---:|---:|",
    ]
    for label in ("semantic", "procedural", "interpretive", "none"):
        metric = result["class_metrics"][label]
        lines.append(
            f"| {label} | {metric['correct']}/{metric['total']} | {metric['accuracy']:.2%} |"
        )
    lines.extend(
        [
            "",
            f"- Delta vs live matched direct carrier: {result['accuracy_delta_vs_live_control']:+.2%}",
            f"- Live control prediction drift vs frozen V3: {result['live_control_prediction_drift_count']}",
            f"- Newly correct: {result['newly_correct_count']}",
            f"- Regressions: {result['regression_count']}",
            f"- Critical false positives: {result['critical_false_positive_count']}",
            f"- Structured tool parse success: {result['candidate_parse_success_rate']:.2%}",
            f"- Median fallback latency: {result['median_fallback_wall_seconds']:.3f}s",
            f"- Warm p95 fallback latency: {result['warm_p95_fallback_wall_seconds']:.3f}s",
            f"- All preregistered gates: **{'PASS' if result['all_gates_pass'] else 'FAIL'}**",
            f"- Decision: `{analysis['decision']}`",
            "",
            "This is development evidence on a retired, Codex-labeled dataset. It cannot authorize runtime memory writes or broad human-likeness claims.",
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
