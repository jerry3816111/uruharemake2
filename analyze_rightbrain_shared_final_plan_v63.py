#!/usr/bin/env python3
"""Analyze the frozen V63 shared-final-plan payload ablation."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import analyze_rightbrain_speech_plan_payload_v62 as v62_analysis
from analyze_rightbrain_pipeline_shadow_v61 import (
    _bootstrap_delta,
    _paired_counts,
    _ratio,
)
from run_rightbrain_shared_final_plan_v63 import (
    ALLOWED_PLAN_SOURCES,
    C0,
    CONDITIONS,
    T1,
)


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_shared_final_plan_v63_preregistration.json"
DATASET_PATH = ROOT / "datasets/rightbrain_shared_final_plan_v63.json"
LOCK_PATH = ROOT / "configs/rightbrain_shared_final_plan_v63_harness_lock.json"
DEFAULT_RAW = ROOT / "reports/rightbrain_shared_final_plan_v63_raw.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_shared_final_plan_v63_analysis.json"
DEFAULT_MD = ROOT / "reports/rightbrain_shared_final_plan_v63_analysis.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(raw, condition, plan_source=None):
    return [
        row
        for row in raw["model_rows"]
        if row["condition"] == condition
        and (plan_source is None or row["plan_source"] == plan_source)
    ]


def _artifact_checks(raw, prereg, dataset, lock):
    case_ids = [case["id"] for case in dataset["cases"]]
    captures = raw["captures"]
    rows = raw["model_rows"]
    expected_pairs = {
        (case_id, condition)
        for case_id in case_ids
        for condition in CONDITIONS
    }
    observed_pairs = {(row["case_id"], row["condition"]) for row in rows}
    lock_hashes = {
        name: artifact["sha256"]
        for name, artifact in lock["frozen_artifacts"].items()
    }
    current_hashes = {
        name: _sha256(ROOT / artifact["path"])
        for name, artifact in lock["frozen_artifacts"].items()
    }
    capture_by_id = {capture["case_id"]: capture for capture in captures}
    source_counts = Counter(
        capture.get("plan_source") for capture in captures
    )
    model_high_road_count = source_counts["model_high_road"]
    return {
        "raw_schema_matches": raw.get("schema")
        == "uruha_rightbrain_shared_final_plan_raw_v63",
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
        "captured_final_logic_complete": all(
            capture.get("base_logic") for capture in captures
        ),
        "captured_runtime_plans_complete": all(
            capture.get("runtime_speech_plan", {}).get("content_units")
            and capture.get("runtime_speech_plan", {}).get("dialogue_act")
            for capture in captures
        ),
        "plan_sources_complete": all(
            capture.get("plan_source") in ALLOWED_PLAN_SOURCES
            for capture in captures
        ),
        "plan_source_distribution_matches": raw.get(
            "plan_source_distribution"
        )
        == dict(sorted(source_counts.items())),
        "leftbrain_calls_match_model_high_road": raw.get(
            "leftbrain_call_count"
        )
        == model_high_road_count
        and sum(
            capture.get("leftbrain_model_call_delta", 0)
            for capture in captures
        )
        == model_high_road_count,
        "fixture_retrieval_complete": all(
            set(capture["retrieved_fixture_ids"])
            == set(capture["expected_fixture_ids"])
            for capture in captures
        ),
        "gold_not_passed_to_model": raw.get(
            "gold_or_expected_outcome_passed_to_model"
        )
        is False,
        "preflight_passed": raw["preflight"]["passed"] is True,
        "production_database_not_opened": all(
            not capture["production_database_opened"]
            for capture in captures
        ),
    }


def _case_recall(rows):
    return [
        _ratio(
            row["raw_score"]["required_meaning_hit_count"],
            row["raw_score"]["required_meaning_count"],
        )
        for row in rows
    ]


def _source_summaries(raw):
    summaries = {}
    for source in sorted(ALLOWED_PLAN_SOURCES):
        c0_rows = _rows(raw, C0, source)
        t1_rows = _rows(raw, T1, source)
        if not c0_rows:
            summaries[source] = {"case_count": 0}
            continue
        c0 = v62_analysis._summary(c0_rows)
        t1 = v62_analysis._summary(t1_rows)
        summaries[source] = {
            "case_count": len(c0_rows),
            C0: c0,
            T1: t1,
            "required_meaning_recall_delta": round(
                t1["raw_required_meaning_recall"]
                - c0["raw_required_meaning_recall"],
                6,
            ),
        }
    return summaries


def analyze(raw, prereg, dataset, lock):
    checks = _artifact_checks(raw, prereg, dataset, lock)
    c0_rows = _rows(raw, C0)
    t1_rows = _rows(raw, T1)
    c0 = v62_analysis._summary(c0_rows)
    t1 = v62_analysis._summary(t1_rows)
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
                _case_recall(c0_rows),
                _case_recall(t1_rows),
                prereg["generation"]["seed"] + 1,
                lock["statistics"]["bootstrap_samples"],
            )
        },
    }

    capture_count = len(raw["captures"])
    final_plan_count = sum(
        bool(capture.get("base_logic")) for capture in raw["captures"]
    )
    speech_plan_count = sum(
        bool(capture.get("runtime_speech_plan", {}).get("content_units"))
        and bool(capture.get("runtime_speech_plan", {}).get("dialogue_act"))
        for capture in raw["captures"]
    )
    plan_source_count = sum(
        capture.get("plan_source") in ALLOWED_PLAN_SOURCES
        for capture in raw["captures"]
    )
    final_plan_rate = _ratio(final_plan_count, capture_count)
    speech_plan_rate = _ratio(speech_plan_count, capture_count)
    plan_source_rate = _ratio(plan_source_count, capture_count)

    gates = prereg["automatic_advance_gates"]
    peak_rss = t1["peak_ollama_rss_bytes"]
    gate_checks = {
        "all_hash_shape_freshness_and_isolation_checks_pass": all(
            checks.values()
        ),
        "shared_final_plan_capture_rate_at_least": final_plan_rate
        >= gates["shared_final_plan_capture_rate_at_least"],
        "runtime_speech_plan_capture_rate_at_least": speech_plan_rate
        >= gates["runtime_speech_plan_capture_rate_at_least"],
        "plan_source_record_rate_at_least": plan_source_rate
        >= gates["plan_source_record_rate_at_least"],
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
        "schema": "uruha_rightbrain_shared_final_plan_analysis_v63",
        "experiment_id": prereg["experiment_id"],
        "evidence_boundary": prereg["causal_boundary"],
        "artifact_checks": checks,
        "shared_final_plan_capture_count": final_plan_count,
        "shared_final_plan_capture_rate": final_plan_rate,
        "runtime_speech_plan_capture_count": speech_plan_count,
        "runtime_speech_plan_capture_rate": speech_plan_rate,
        "plan_source_record_rate": plan_source_rate,
        "plan_source_distribution": raw["plan_source_distribution"],
        "condition_summaries": {C0: c0, T1: t1},
        "plan_source_summaries": _source_summaries(raw),
        "paired_statistics": paired,
        "automatic_gates": {
            "passed": passed,
            "checks": gate_checks,
            "failed_checks": [
                name for name, value in gate_checks.items() if not value
            ],
        },
        "decision": (
            "authorize_new_data_runtime_integration_shadow_test"
            if passed
            else "freeze_negative_result_and_stop_full_speech_plan_payload_hypothesis"
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
    sources = report["plan_source_distribution"]
    return "\n".join(
        [
            "# V63 共享最終計畫傳遞實驗",
            "",
            f"- 自動門檻：**{'PASS' if report['automatic_gates']['passed'] else 'FAIL'}**",
            f"- 最終計畫捕捉：`{report['shared_final_plan_capture_count']}/14`",
            f"- 口語計畫捕捉：`{report['runtime_speech_plan_capture_count']}/14`",
            f"- 計畫來源：`{json.dumps(sources, ensure_ascii=False)}`",
            f"- 無口語計畫必要意思命中：`{_pct(c0['raw_required_meaning_recall'])}`",
            f"- 有口語計畫必要意思命中：`{_pct(t1['raw_required_meaning_recall'])}`",
            f"- 差值：`{100 * delta:+.1f} percentage points`",
            f"- 有口語計畫表面閘門：`{_pct(t1['raw_surface_gate_pass_rate'])}`",
            f"- 禁止意思違規：`{_pct(t1['raw_forbidden_meaning_violation_rate'])}`",
            f"- 私密記憶洩漏：`{t1['raw_private_memory_intrusion_count']}`",
            f"- 決策：`{report['decision']}`",
            "",
            "本 pilot 不修改正式 runtime，也不直接授權模型替換或上線。",
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
