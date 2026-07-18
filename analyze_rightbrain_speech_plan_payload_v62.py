#!/usr/bin/env python3
"""Analyze the frozen V62 matched speech-plan payload ablation."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from analyze_rightbrain_pipeline_shadow_v61 import (
    _bootstrap_delta,
    _duplicate_rate,
    _p95,
    _paired_counts,
    _ratio,
)
from run_rightbrain_speech_plan_payload_v62 import C0, CONDITIONS, T1


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT / "configs/rightbrain_speech_plan_payload_v62_preregistration.json"
)
DATASET_PATH = ROOT / "datasets/rightbrain_speech_plan_payload_v62.json"
LOCK_PATH = ROOT / "configs/rightbrain_speech_plan_payload_v62_harness_lock.json"
DEFAULT_RAW = ROOT / "reports/rightbrain_speech_plan_payload_v62_raw.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_speech_plan_payload_v62_analysis.json"
DEFAULT_MD = ROOT / "reports/rightbrain_speech_plan_payload_v62_analysis.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(raw, condition):
    return [row for row in raw["model_rows"] if row["condition"] == condition]


def _summary(rows):
    scores = [row["raw_score"] for row in rows]
    required_hits = sum(score["required_meaning_hit_count"] for score in scores)
    required_total = sum(score["required_meaning_count"] for score in scores)
    forbidden_hits = sum(score["forbidden_meaning_hit_count"] for score in scores)
    forbidden_total = sum(
        len(score["forbidden_meaning_propositions"]) for score in scores
    )
    latencies = [row["generation_metrics"]["wall_seconds"] for row in rows]
    rss = [
        row["peak_ollama_rss_bytes"]
        for row in rows
        if row["peak_ollama_rss_bytes"] is not None
    ]
    return {
        "case_count": len(rows),
        "payload_plan_presence_count": sum(
            row["payload_plan_present"] for row in rows
        ),
        "payload_plan_presence_rate": _ratio(
            sum(row["payload_plan_present"] for row in rows),
            len(rows),
        ),
        "raw_required_meaning_hit_count": required_hits,
        "raw_required_meaning_total": required_total,
        "raw_required_meaning_recall": _ratio(required_hits, required_total),
        "raw_case_complete_count": sum(
            score["required_meaning_pass"] for score in scores
        ),
        "raw_case_complete_rate": _ratio(
            sum(score["required_meaning_pass"] for score in scores),
            len(rows),
        ),
        "raw_forbidden_meaning_hit_count": forbidden_hits,
        "raw_forbidden_meaning_total": forbidden_total,
        "raw_forbidden_meaning_violation_rate": _ratio(
            forbidden_hits,
            forbidden_total,
        ),
        "raw_private_memory_intrusion_count": sum(
            score["private_memory_intrusion"] for score in scores
        ),
        "raw_surface_gate_pass_count": sum(
            score["current_gate_pass"] for score in scores
        ),
        "raw_surface_gate_pass_rate": _ratio(
            sum(score["current_gate_pass"] for score in scores),
            len(rows),
        ),
        "normalized_duplicate_reply_rate": _duplicate_rate(
            [score["normalized_reply"] for score in scores]
        ),
        "model_latency_median_seconds": round(
            statistics.median(latencies),
            6,
        ),
        "model_latency_p95_seconds": _p95(latencies),
        "peak_ollama_rss_bytes": max(rss) if rss else None,
        "transport_error_count": sum(
            bool(row["transport_error"]) for row in rows
        ),
        "surface_rejection_reason_counts": dict(
            sorted(
                Counter(
                    reason
                    for score in scores
                    for reason in score["current_gate_rejection_reasons"]
                ).items()
            )
        ),
    }


def _artifact_checks(raw, prereg, dataset, lock):
    case_ids = [case["id"] for case in dataset["cases"]]
    captures = raw["captures"]
    rows = raw["model_rows"]
    observed_pairs = {(row["case_id"], row["condition"]) for row in rows}
    expected_pairs = {
        (case_id, condition)
        for case_id in case_ids
        for condition in CONDITIONS
    }
    lock_hashes = {
        name: artifact["sha256"]
        for name, artifact in lock["frozen_artifacts"].items()
    }
    current_hashes = {
        name: _sha256(ROOT / artifact["path"])
        for name, artifact in lock["frozen_artifacts"].items()
    }
    capture_by_id = {capture["case_id"]: capture for capture in captures}
    return {
        "raw_schema_matches": raw.get("schema")
        == "uruha_rightbrain_speech_plan_payload_raw_v62",
        "experiment_id_matches": raw.get("experiment_id")
        == prereg["experiment_id"],
        "lock_hash_matches_raw": raw.get("harness_lock_sha256")
        == _sha256(LOCK_PATH),
        "frozen_artifact_hashes_match": raw.get("frozen_artifact_hashes")
        == lock_hashes,
        "current_frozen_artifacts_match": current_hashes == lock_hashes,
        "condition_order_matches": tuple(raw.get("conditions") or ())
        == CONDITIONS,
        "case_order_and_capture_count_match": [
            capture["case_id"] for capture in captures
        ]
        == case_ids,
        "paired_rows_complete": observed_pairs == expected_pairs
        and len(rows) == len(expected_pairs),
        "shared_plan_hash_reused": all(
            row["shared_plan_sha256"]
            == capture_by_id[row["case_id"]]["shared_plan_sha256"]
            for row in rows
        ),
        "control_payloads_exclude_plan": all(
            not row["payload_plan_present"] for row in _rows(raw, C0)
        ),
        "treatment_payloads_include_plan": all(
            row["payload_plan_present"] for row in _rows(raw, T1)
        ),
        "captured_runtime_plans_complete": all(
            capture["runtime_speech_plan"].get("content_units")
            and capture["runtime_speech_plan"].get("dialogue_act")
            for capture in captures
        ),
        "gold_not_passed_to_model": raw.get(
            "gold_or_expected_outcome_passed_to_model"
        )
        is False,
        "preflight_passed": raw["preflight"]["passed"] is True,
        "production_database_not_opened": all(
            not capture["production_database_opened"] for capture in captures
        ),
    }


def analyze(raw, prereg, dataset, lock):
    checks = _artifact_checks(raw, prereg, dataset, lock)
    c0_rows = _rows(raw, C0)
    t1_rows = _rows(raw, T1)
    c0 = _summary(c0_rows)
    t1 = _summary(t1_rows)

    c0_case_recall = [
        _ratio(
            row["raw_score"]["required_meaning_hit_count"],
            row["raw_score"]["required_meaning_count"],
        )
        for row in c0_rows
    ]
    t1_case_recall = [
        _ratio(
            row["raw_score"]["required_meaning_hit_count"],
            row["raw_score"]["required_meaning_count"],
        )
        for row in t1_rows
    ]
    c0_complete = [
        row["raw_score"]["required_meaning_pass"] for row in c0_rows
    ]
    t1_complete = [
        row["raw_score"]["required_meaning_pass"] for row in t1_rows
    ]
    paired = {
        "case_complete": {
            "paired_counts": _paired_counts(c0_complete, t1_complete),
            "bootstrap": _bootstrap_delta(
                c0_complete,
                t1_complete,
                prereg["generation"]["seed"],
                lock["statistics"]["bootstrap_samples"],
            ),
        },
        "case_meaning_recall": {
            "bootstrap": _bootstrap_delta(
                c0_case_recall,
                t1_case_recall,
                prereg["generation"]["seed"] + 1,
                lock["statistics"]["bootstrap_samples"],
            )
        },
    }

    gates = prereg["automatic_advance_gates"]
    speech_plan_count = sum(
        bool(capture["runtime_speech_plan"].get("content_units"))
        and bool(capture["runtime_speech_plan"].get("dialogue_act"))
        for capture in raw["captures"]
    )
    speech_plan_rate = _ratio(speech_plan_count, len(raw["captures"]))
    peak_rss = t1["peak_ollama_rss_bytes"]
    gate_checks = {
        "all_hash_shape_freshness_and_isolation_checks_pass": all(
            checks.values()
        ),
        "t1_speech_plan_capture_rate_at_least": speech_plan_rate
        >= gates["t1_speech_plan_capture_rate_at_least"],
        "t1_payload_plan_presence_rate_at_least": t1[
            "payload_plan_presence_rate"
        ]
        >= gates["t1_payload_plan_presence_rate_at_least"],
        "t1_raw_required_meaning_recall_at_least": t1[
            "raw_required_meaning_recall"
        ]
        >= gates["t1_raw_required_meaning_recall_at_least"],
        "t1_raw_required_meaning_recall_delta_vs_c0_at_least": (
            t1["raw_required_meaning_recall"]
            - c0["raw_required_meaning_recall"]
        )
        >= gates["t1_raw_required_meaning_recall_delta_vs_c0_at_least"],
        "t1_raw_forbidden_meaning_violation_rate_at_most": t1[
            "raw_forbidden_meaning_violation_rate"
        ]
        <= gates["t1_raw_forbidden_meaning_violation_rate_at_most"],
        "t1_raw_private_memory_intrusion_count": t1[
            "raw_private_memory_intrusion_count"
        ]
        == gates["t1_raw_private_memory_intrusion_count"],
        "t1_raw_surface_gate_pass_rate_at_least": t1[
            "raw_surface_gate_pass_rate"
        ]
        >= gates["t1_raw_surface_gate_pass_rate_at_least"],
        "t1_duplicate_rate_not_higher_than_c0": t1[
            "normalized_duplicate_reply_rate"
        ]
        <= c0["normalized_duplicate_reply_rate"],
        "t1_model_latency_median_seconds_at_most": t1[
            "model_latency_median_seconds"
        ]
        <= gates["t1_model_latency_median_seconds_at_most"],
        "t1_model_latency_p95_seconds_at_most": t1[
            "model_latency_p95_seconds"
        ]
        <= gates["t1_model_latency_p95_seconds_at_most"],
        "t1_peak_ollama_rss_bytes_at_most": peak_rss is not None
        and peak_rss <= gates["t1_peak_ollama_rss_bytes_at_most"],
        "leftbrain_call_count_exact": raw["leftbrain_call_count"]
        == gates["leftbrain_call_count_exact"],
        "rightbrain_model_call_count_exact": raw["logical_model_call_count"]
        == gates["rightbrain_model_call_count_exact"],
        "transport_error_count_exact": raw["transport_error_count"]
        == gates["transport_error_count_exact"],
        "production_memory_write_count_exact": raw[
            "production_memory_write_count"
        ]
        == gates["production_memory_write_count_exact"],
        "physical_vrm_action_count_exact": raw["physical_vrm_action_count"]
        == gates["physical_vrm_action_count_exact"],
    }
    passed = all(gate_checks.values())
    return {
        "schema": "uruha_rightbrain_speech_plan_payload_analysis_v62",
        "experiment_id": prereg["experiment_id"],
        "evidence_boundary": prereg["causal_boundary"],
        "artifact_checks": checks,
        "speech_plan_capture_count": speech_plan_count,
        "speech_plan_capture_rate": speech_plan_rate,
        "condition_summaries": {C0: c0, T1: t1},
        "paired_statistics": paired,
        "automatic_gates": {
            "passed": passed,
            "checks": gate_checks,
            "failed_checks": [
                name for name, value in gate_checks.items() if not value
            ],
        },
        "decision": (
            "authorize_new_data_semantic_contract_projector_development"
            if passed
            else "freeze_negative_result_and_stop_full_speech_plan_hypothesis"
        ),
        "human_blind_review_authorized": False,
        "runtime_change_authorized": False,
        "production_rightbrain_replacement_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{100 * value:.1f}%"


def _markdown(report):
    c0 = report["condition_summaries"][C0]
    t1 = report["condition_summaries"][T1]
    delta = t1["raw_required_meaning_recall"] - c0[
        "raw_required_meaning_recall"
    ]
    return "\n".join(
        [
            "# V62 speech-plan payload ablation",
            "",
            f"- Automatic gate: **{'PASS' if report['automatic_gates']['passed'] else 'FAIL'}**",
            f"- Speech-plan capture: `{report['speech_plan_capture_count']}/14`",
            f"- Control required-meaning recall: `{_pct(c0['raw_required_meaning_recall'])}`",
            f"- Treatment required-meaning recall: `{_pct(t1['raw_required_meaning_recall'])}`",
            f"- Treatment delta: `{100 * delta:+.1f} percentage points`",
            f"- Treatment surface pass: `{_pct(t1['raw_surface_gate_pass_rate'])}`",
            f"- Treatment forbidden violation: `{_pct(t1['raw_forbidden_meaning_violation_rate'])}`",
            f"- Treatment private-memory intrusions: `{t1['raw_private_memory_intrusion_count']}`",
            f"- Decision: `{report['decision']}`",
            "",
            "This pilot changes no production runtime and authorizes no model replacement.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = analyze(
        _load(args.raw),
        _load(PREREG_PATH),
        _load(DATASET_PATH),
        _load(LOCK_PATH),
    )
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "automatic_gate_passed": report["automatic_gates"]["passed"],
                "failed_checks": report["automatic_gates"]["failed_checks"],
                "json_output": str(args.json_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
