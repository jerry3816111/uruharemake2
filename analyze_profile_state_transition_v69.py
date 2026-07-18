#!/usr/bin/env python3
"""Analyze the frozen V69 cross-session profile-state shadow."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from run_profile_state_transition_v69 import CONDITIONS


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_state_transition_v69_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_state_transition_v69.json"
LOCK_PATH = ROOT / "configs/profile_state_transition_v69_harness_lock.json"
RAW_PATH = ROOT / "reports/profile_state_transition_v69_raw.json"
ANALYSIS_PATH = ROOT / "reports/profile_state_transition_v69_analysis.json"
MARKDOWN_PATH = ROOT / "reports/profile_state_transition_v69_analysis.md"
RESULT_LOCK_PATH = ROOT / "configs/profile_state_transition_v69_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _division(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def _score_row(row, case):
    expected = case["expected"]
    expected_written = set(expected["written_turn_ids"])
    expected_active = set(expected["active_turn_ids"])
    expected_historical = set(expected["historical_turn_ids"])
    persisted = set(row["persisted_ids"])
    active = set(row["active_ids"])
    historical = set(row["historical_ids"])
    inapplicable = set(row["inapplicable_ids"])
    unclassified = persisted - active - historical - inapplicable
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "language": case["language"],
        "condition": row["condition"],
        "exact_partition": (
            persisted == expected_written
            and active == expected_active
            and historical == expected_historical
            and not inapplicable
            and not unclassified
        ),
        "exact_active": active == expected_active,
        "active_true_positive": len(active & expected_active),
        "active_predicted": len(active),
        "active_gold": len(expected_active),
        "stale_active_count": len(active & expected_historical),
        "missed_active_count": len(expected_active - active),
        "preserved_write_count": len(persisted & expected_written),
        "expected_write_count": len(expected_written),
        "unexpected_write_count": len(persisted - expected_written),
        "state_seconds": float(row["state_seconds"]),
    }


def _aggregate(scores):
    times = [row["state_seconds"] for row in scores]
    return {
        "case_count": len(scores),
        "exact_partition_count": sum(row["exact_partition"] for row in scores),
        "exact_active_count": sum(row["exact_active"] for row in scores),
        "active_precision": _division(
            sum(row["active_true_positive"] for row in scores),
            sum(row["active_predicted"] for row in scores),
        ),
        "active_recall": _division(
            sum(row["active_true_positive"] for row in scores),
            sum(row["active_gold"] for row in scores),
        ),
        "stale_active_record_count": sum(row["stale_active_count"] for row in scores),
        "missed_active_record_count": sum(row["missed_active_count"] for row in scores),
        "history_preservation_rate": _division(
            sum(row["preserved_write_count"] for row in scores),
            sum(row["expected_write_count"] for row in scores),
        ),
        "unexpected_write_count": sum(row["unexpected_write_count"] for row in scores),
        "median_state_overhead_seconds": statistics.median(times),
        "p95_state_overhead_seconds": _percentile(times, 0.95),
    }


def analyze_raw(raw, dataset, prereg, lock):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = [_score_row(row, cases[row["case_id"]]) for row in raw["rows"]]
    by_condition = {
        condition: _aggregate([row for row in scores if row["condition"] == condition])
        for condition in CONDITIONS
    }
    matched = {row["case_id"]: row for row in scores if row["condition"] == CONDITIONS[1]}
    treatment = {row["case_id"]: row for row in scores if row["condition"] == CONDITIONS[2]}
    newly_exact = sum(
        treatment[case_id]["exact_partition"] and not matched[case_id]["exact_partition"]
        for case_id in cases
    )
    regressions = sum(
        matched[case_id]["exact_partition"] and not treatment[case_id]["exact_partition"]
        for case_id in cases
    )
    family_exact = {
        family: {
            "exact": sum(
                row["exact_partition"]
                for row in treatment.values()
                if row["scenario_family"] == family
            ),
            "count": sum(1 for row in treatment.values() if row["scenario_family"] == family),
        }
        for family in prereg["dataset"]["scenario_families"]
    }
    metric = by_condition[CONDITIONS[2]]
    gates = prereg["treatment_success_gates"]
    checks = {
        "exact_partition_count": metric["exact_partition_count"] >= gates["exact_partition_count_min"],
        "exact_active_count": metric["exact_active_count"] >= gates["exact_active_count_min"],
        "active_precision": metric["active_precision"] >= gates["active_precision_min"],
        "active_recall": metric["active_recall"] >= gates["active_recall_min"],
        "stale_active_record_count": metric["stale_active_record_count"] <= gates["stale_active_record_count_max"],
        "missed_active_record_count": metric["missed_active_record_count"] <= gates["missed_active_record_count_max"],
        "history_preservation_rate": metric["history_preservation_rate"] >= gates["history_preservation_rate_min"],
        "unexpected_write_count": metric["unexpected_write_count"] <= gates["unexpected_write_count_max"],
        "newly_exact_vs_matched_control": newly_exact >= gates["newly_exact_vs_matched_control_min"],
        "regressions_vs_matched_control": regressions <= gates["regressions_vs_matched_control_max"],
        "median_state_overhead_seconds": metric["median_state_overhead_seconds"] <= gates["median_state_overhead_seconds_max"],
        "p95_state_overhead_seconds": metric["p95_state_overhead_seconds"] <= gates["p95_state_overhead_seconds_max"],
    }
    integrity = {
        "row_count_exact": raw["row_count"] == 54 and len(raw["rows"]) == 54,
        "case_count_exact": raw["case_count"] == 18,
        "condition_rows_exact": all(by_condition[condition]["case_count"] == 18 for condition in CONDITIONS),
        "case_condition_pairs_unique": len(
            {(row["case_id"], row["condition"]) for row in raw["rows"]}
        ) == 54,
        "gold_absent": raw["gold_in_raw"] is False,
        "no_model_inference": raw["language_model_inference"] is False,
        "production_unchanged": (
            raw["production_runtime_changed"] is False
            and raw["production_database_access"] is False
        ),
        "temporary_chroma_only": (
            raw["temporary_chroma_access"] is True
            and all(row["temporary_chroma"] is True for row in raw["rows"])
        ),
        "timing_iterations_exact": (
            raw["warmup_iterations_per_case"]
            == lock["formal_run"]["timing"]["warmup_iterations_per_case"]
            and raw["scored_iterations_per_case"]
            == lock["formal_run"]["timing"]["scored_iterations_per_case"]
        ),
    }
    passed = all(checks.values()) and all(integrity.values())
    return {
        "schema": "uruha_profile_state_transition_analysis_v69",
        "experiment_id": prereg["experiment_id"],
        "decision": (
            "authorize_separate_production_shadow_integration"
            if passed
            else "freeze_result_and_leave_production_profile_persistence_unchanged"
        ),
        "run_integrity": {"passed": all(integrity.values()), "checks": integrity},
        "metrics": by_condition,
        "family_exact": family_exact,
        "pairwise": {
            "newly_exact_vs_matched_control": newly_exact,
            "regressions_vs_matched_control": regressions,
        },
        "success_gates": {"passed": all(checks.values()), "checks": checks},
        "case_scores": list(treatment.values()),
        "evidence_boundary": prereg["causal_boundary"],
        "production_runtime_changed": False,
    }


def _markdown(report):
    current = report["metrics"][CONDITIONS[0]]
    matched = report["metrics"][CONDITIONS[1]]
    treatment = report["metrics"][CONDITIONS[2]]
    failed = [name for name, passed in report["success_gates"]["checks"].items() if not passed]
    lines = [
        "# V69 跨 session 使用者資料狀態結果",
        "",
        f"**決策：** `{report['decision']}`",
        "",
        "| 條件 | 完整分流 | 現況完全正確 | 舊資料誤當現況 | 漏掉現況 | 歷史保留 | 中位狀態成本 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| 現行 session-only | {current['exact_partition_count']}/18 | {current['exact_active_count']}/18 | {current['stale_active_record_count']} | {current['missed_active_record_count']} | {current['history_preservation_rate']:.1%} | {current['median_state_overhead_seconds'] * 1000:.3f} ms |",
        f"| 同資料 append-only | {matched['exact_partition_count']}/18 | {matched['exact_active_count']}/18 | {matched['stale_active_record_count']} | {matched['missed_active_record_count']} | {matched['history_preservation_rate']:.1%} | {matched['median_state_overhead_seconds'] * 1000:.3f} ms |",
        f"| typed state + V67 | {treatment['exact_partition_count']}/18 | {treatment['exact_active_count']}/18 | {treatment['stale_active_record_count']} | {treatment['missed_active_record_count']} | {treatment['history_preservation_rate']:.1%} | {treatment['median_state_overhead_seconds'] * 1000:.3f} ms |",
        "",
        f"相對 matched control 新增完全正確 {report['pairwise']['newly_exact_vs_matched_control']} 題，退步 {report['pairwise']['regressions_vs_matched_control']} 題。",
        f"預註冊門檻：{'全部通過' if report['success_gates']['passed'] else '未通過'}。",
    ]
    if failed:
        lines.append("未通過：" + ", ".join(failed))
    lines.extend(
        [
            "",
            "本實驗只測已抽取 profile facts 的臨時資料庫寫入、讀回與現況／歷史分流；尚未修改正式資料庫，也未測最終回答、人格適應或廣義人類相似度。",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze_raw(_load(args.raw), _load(DATASET_PATH), _load(PREREG_PATH), _load(LOCK_PATH))
    if args.write:
        ANALYSIS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        MARKDOWN_PATH.write_text(_markdown(report), encoding="utf-8")
        authorized = report["success_gates"]["passed"] and report["run_integrity"]["passed"]
        result_lock = {
            "schema": "uruha_profile_state_transition_result_lock_v69",
            "decision": report["decision"],
            "run_integrity_passed": report["run_integrity"]["passed"],
            "success_gates_passed": report["success_gates"]["passed"],
            "frozen_artifacts": {
                "preregistration": {"path": str(PREREG_PATH.relative_to(ROOT)), "sha256": _sha256(PREREG_PATH)},
                "dataset": {"path": str(DATASET_PATH.relative_to(ROOT)), "sha256": _sha256(DATASET_PATH)},
                "harness_lock": {"path": str(LOCK_PATH.relative_to(ROOT)), "sha256": _sha256(LOCK_PATH)},
                "raw": {"path": str(args.raw.relative_to(ROOT)), "sha256": _sha256(args.raw)},
                "analysis": {"path": str(ANALYSIS_PATH.relative_to(ROOT)), "sha256": _sha256(ANALYSIS_PATH)},
                "markdown": {"path": str(MARKDOWN_PATH.relative_to(ROOT)), "sha256": _sha256(MARKDOWN_PATH)},
            },
            "production_shadow_integration_authorized": authorized,
            "production_database_migration_authorized": False,
            "runtime_activation_authorized": False,
            "post_run_case_editing_authorized": False,
            "post_run_threshold_change_authorized": False,
            "evidence_boundary": report["evidence_boundary"],
        }
        RESULT_LOCK_PATH.write_text(
            json.dumps(result_lock, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "run_integrity": report["run_integrity"],
                "metrics": report["metrics"],
                "pairwise": report["pairwise"],
                "success_gates": report["success_gates"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
