#!/usr/bin/env python3
"""Analyze the frozen V67 memory-validity pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from run_memory_validity_resolution_v67 import CONDITIONS


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/memory_validity_resolution_v67_preregistration.json"
DATASET_PATH = ROOT / "datasets/memory_validity_resolution_v67.json"
LOCK_PATH = ROOT / "configs/memory_validity_resolution_v67_harness_lock.json"
RAW_PATH = ROOT / "reports/memory_validity_resolution_v67_raw.json"
ANALYSIS_PATH = ROOT / "reports/memory_validity_resolution_v67_analysis.json"
MARKDOWN_PATH = ROOT / "reports/memory_validity_resolution_v67_analysis.md"
RESULT_LOCK_PATH = ROOT / "configs/memory_validity_resolution_v67_result_lock.json"


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
    predicted = {key: set(row[key]) for key in ("eligible_ids", "historical_ids", "inapplicable_ids", "working_memory_ids")}
    gold = {key: set(expected[key]) for key in predicted}
    noneligible = gold["historical_ids"] | gold["inapplicable_ids"]
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "condition": row["condition"],
        "exact_partition": all(predicted[key] == gold[key] for key in ("eligible_ids", "historical_ids", "inapplicable_ids")),
        "exact_working_memory": predicted["working_memory_ids"] == gold["working_memory_ids"],
        "eligible_true_positive": len(predicted["eligible_ids"] & gold["eligible_ids"]),
        "eligible_predicted": len(predicted["eligible_ids"]),
        "eligible_gold": len(gold["eligible_ids"]),
        "historical_true_positive": len(predicted["historical_ids"] & gold["historical_ids"]),
        "historical_gold": len(gold["historical_ids"]),
        "inapplicable_true_positive": len(predicted["inapplicable_ids"] & gold["inapplicable_ids"]),
        "inapplicable_gold": len(gold["inapplicable_ids"]),
        "stale_or_inapplicable_intrusions": len(predicted["working_memory_ids"] & noneligible),
        "over_suppressions": len(gold["eligible_ids"] - predicted["eligible_ids"]),
        "resolver_seconds": float(row["resolver_seconds"]),
    }


def _aggregate(scores):
    resolver_times = [row["resolver_seconds"] for row in scores]
    return {
        "case_count": len(scores),
        "exact_partition_count": sum(row["exact_partition"] for row in scores),
        "exact_working_memory_count": sum(row["exact_working_memory"] for row in scores),
        "eligible_precision": _division(sum(row["eligible_true_positive"] for row in scores), sum(row["eligible_predicted"] for row in scores)),
        "eligible_recall": _division(sum(row["eligible_true_positive"] for row in scores), sum(row["eligible_gold"] for row in scores)),
        "historical_recall": _division(sum(row["historical_true_positive"] for row in scores), sum(row["historical_gold"] for row in scores)),
        "inapplicable_recall": _division(sum(row["inapplicable_true_positive"] for row in scores), sum(row["inapplicable_gold"] for row in scores)),
        "stale_or_inapplicable_intrusion_count": sum(row["stale_or_inapplicable_intrusions"] for row in scores),
        "over_suppression_count": sum(row["over_suppressions"] for row in scores),
        "median_resolver_overhead_seconds": statistics.median(resolver_times),
        "p95_resolver_overhead_seconds": _percentile(resolver_times, 0.95),
    }


def analyze_raw(raw, dataset, prereg, lock):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = [_score_row(row, cases[row["case_id"]]) for row in raw["rows"]]
    by_condition = {
        condition: _aggregate([row for row in scores if row["condition"] == condition])
        for condition in CONDITIONS
    }
    treatment_scores = [row for row in scores if row["condition"] == CONDITIONS[1]]
    control_by_id = {row["case_id"]: row for row in scores if row["condition"] == CONDITIONS[0]}
    treatment_by_id = {row["case_id"]: row for row in treatment_scores}
    newly_exact = sum(
        treatment_by_id[case_id]["exact_working_memory"] and not control_by_id[case_id]["exact_working_memory"]
        for case_id in cases
    )
    regressions = sum(
        control_by_id[case_id]["exact_working_memory"] and not treatment_by_id[case_id]["exact_working_memory"]
        for case_id in cases
    )
    family_exact = {
        family: sum(row["exact_working_memory"] for row in treatment_scores if row["scenario_family"] == family)
        for family in prereg["dataset"]["scenario_families"]
    }

    metric = by_condition[CONDITIONS[1]]
    gates = prereg["treatment_success_gates"]
    checks = {
        "exact_partition_count": metric["exact_partition_count"] >= gates["exact_partition_count_min"],
        "exact_working_memory_count": metric["exact_working_memory_count"] >= gates["exact_working_memory_count_min"],
        "eligible_precision": metric["eligible_precision"] >= gates["eligible_precision_min"],
        "eligible_recall": metric["eligible_recall"] >= gates["eligible_recall_min"],
        "stale_or_inapplicable_intrusion_count": metric["stale_or_inapplicable_intrusion_count"] <= gates["stale_or_inapplicable_intrusion_count_max"],
        "over_suppression_count": metric["over_suppression_count"] <= gates["over_suppression_count_max"],
        "multi_value_exact_count": family_exact["multi_value_coexistence"] >= gates["multi_value_exact_count_min"],
        "legacy_exact_count": family_exact["legacy_metadata_compatibility"] >= gates["legacy_exact_count_min"],
        "newly_exact_working_memory_vs_control": newly_exact >= gates["newly_exact_working_memory_vs_control_min"],
        "regressions_vs_control": regressions <= gates["regressions_vs_control_max"],
        "median_resolver_overhead_seconds": metric["median_resolver_overhead_seconds"] <= gates["median_resolver_overhead_seconds_max"],
        "p95_resolver_overhead_seconds": metric["p95_resolver_overhead_seconds"] <= gates["p95_resolver_overhead_seconds_max"],
    }
    integrity_checks = {
        "row_count_exact": raw["row_count"] == 36 and len(raw["rows"]) == 36,
        "case_count_exact": raw["case_count"] == 18,
        "condition_rows_exact": all(by_condition[condition]["case_count"] == 18 for condition in CONDITIONS),
        "case_condition_pairs_unique": len({(row["case_id"], row["condition"]) for row in raw["rows"]}) == 36,
        "gold_absent": raw["gold_in_raw"] is False,
        "no_model_inference": raw["language_model_inference"] is False,
        "production_unchanged": raw["production_runtime_changed"] is False and raw["production_memory_read_or_write"] is False,
        "timing_iterations_exact": (
            raw["warmup_iterations_per_case"] == lock["formal_run"]["timing"]["warmup_iterations_per_case"]
            and raw["scored_iterations_per_case"] == lock["formal_run"]["timing"]["scored_iterations_per_case"]
        ),
    }
    passed = all(checks.values()) and all(integrity_checks.values())
    return {
        "schema": "uruha_memory_validity_resolution_analysis_v67",
        "experiment_id": prereg["experiment_id"],
        "decision": "authorize_fresh_production_compatible_shadow_integration" if passed else "freeze_result_and_do_not_modify_runtime",
        "run_integrity": {"passed": all(integrity_checks.values()), "checks": integrity_checks},
        "metrics": by_condition,
        "family_exact_working_memory": family_exact,
        "pairwise": {
            "newly_exact_working_memory_vs_control": newly_exact,
            "regressions_vs_control": regressions,
        },
        "success_gates": {"passed": all(checks.values()), "checks": checks},
        "case_scores": scores,
        "evidence_boundary": prereg["causal_boundary"],
        "production_runtime_changed": False,
    }


def _markdown(report):
    control = report["metrics"][CONDITIONS[0]]
    treatment = report["metrics"][CONDITIONS[1]]
    failed = [name for name, passed in report["success_gates"]["checks"].items() if not passed]
    lines = [
        "# V67 記憶有效性分流結果",
        "",
        f"**決策：** `{report['decision']}`",
        "",
        "| 條件 | 分流完全正確 | 工作記憶完全正確 | 舊/不適用記憶侵入 | 誤刪仍有效記憶 | 中位額外延遲 |",
        "|---|---:|---:|---:|---:|---:|",
        f"| 現行：全部候選可進入 | {control['exact_partition_count']}/18 | {control['exact_working_memory_count']}/18 | {control['stale_or_inapplicable_intrusion_count']} | {control['over_suppression_count']} | 0 ms |",
        f"| 通用有效性分流 | {treatment['exact_partition_count']}/18 | {treatment['exact_working_memory_count']}/18 | {treatment['stale_or_inapplicable_intrusion_count']} | {treatment['over_suppression_count']} | {treatment['median_resolver_overhead_seconds'] * 1000:.3f} ms |",
        "",
        f"新答對 {report['pairwise']['newly_exact_working_memory_vs_control']} 題，退步 {report['pairwise']['regressions_vs_control']} 題。",
        f"多值記憶保留 {report['family_exact_working_memory']['multi_value_coexistence']}/3；舊格式相容 {report['family_exact_working_memory']['legacy_metadata_compatibility']}/3。",
        f"預註冊門檻：{'全部通過' if report['success_gates']['passed'] else '未通過'}。",
    ]
    if failed:
        lines.append("未通過：" + ", ".join(failed))
    lines.extend([
        "",
        "本實驗只證明：記憶已具有通用狀態 metadata 時，分流器能否在顯著性排序前保留目前有效記憶並隔離舊資訊。",
        "它尚未證明自然語言能正確產生這些狀態，也未修改正式聊天或長期記憶資料庫。",
        "",
    ])
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
        result_lock = {
            "schema": "uruha_memory_validity_resolution_result_lock_v67",
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
            "runtime_change_authorized": False,
            "post_run_case_editing_authorized": False,
            "post_run_threshold_change_authorized": False,
            "evidence_boundary": report["evidence_boundary"],
        }
        RESULT_LOCK_PATH.write_text(json.dumps(result_lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "run_integrity": report["run_integrity"],
        "metrics": report["metrics"],
        "pairwise": report["pairwise"],
        "success_gates": report["success_gates"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
