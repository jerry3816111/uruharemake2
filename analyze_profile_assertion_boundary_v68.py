#!/usr/bin/env python3
"""Analyze the frozen V68 profile assertion-boundary pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from run_profile_assertion_boundary_v68 import CONDITIONS


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_assertion_boundary_v68_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_assertion_boundary_v68.json"
LOCK_PATH = ROOT / "configs/profile_assertion_boundary_v68_harness_lock.json"
RAW_PATH = ROOT / "reports/profile_assertion_boundary_v68_raw.json"
ANALYSIS_PATH = ROOT / "reports/profile_assertion_boundary_v68_analysis.json"
MARKDOWN_PATH = ROOT / "reports/profile_assertion_boundary_v68_analysis.md"
RESULT_LOCK_PATH = ROOT / "configs/profile_assertion_boundary_v68_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _facts(rows):
    return {(str(row["fact_type"]), str(row["value"]).casefold()) for row in rows}


def _division(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def _score_row(row, case):
    observed = _facts(row["observed_facts"])
    expected = _facts(case["expected_facts"])
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "language": case["language"],
        "condition": row["condition"],
        "is_direct_assertion": bool(expected),
        "exact": observed == expected,
        "true_positive": len(observed & expected),
        "predicted": len(observed),
        "gold": len(expected),
        "false_write": not expected and bool(observed),
        "guard_seconds": float(row["guard_seconds"]),
    }


def _aggregate(scores):
    times = [row["guard_seconds"] for row in scores]
    return {
        "case_count": len(scores),
        "exact_case_count": sum(row["exact"] for row in scores),
        "fact_precision": _division(sum(row["true_positive"] for row in scores), sum(row["predicted"] for row in scores)),
        "fact_recall": _division(sum(row["true_positive"] for row in scores), sum(row["gold"] for row in scores)),
        "non_assertion_false_write_count": sum(row["false_write"] for row in scores),
        "direct_assertion_exact_count": sum(row["exact"] for row in scores if row["is_direct_assertion"]),
        "median_guard_overhead_seconds": statistics.median(times),
        "p95_guard_overhead_seconds": _percentile(times, 0.95),
    }


def analyze_raw(raw, dataset, prereg, lock):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = [_score_row(row, cases[row["case_id"]]) for row in raw["rows"]]
    by_condition = {condition: _aggregate([row for row in scores if row["condition"] == condition]) for condition in CONDITIONS}
    control = {row["case_id"]: row for row in scores if row["condition"] == CONDITIONS[0]}
    treatment = {row["case_id"]: row for row in scores if row["condition"] == CONDITIONS[1]}
    newly_exact = sum(treatment[case_id]["exact"] and not control[case_id]["exact"] for case_id in cases)
    regressions = sum(control[case_id]["exact"] and not treatment[case_id]["exact"] for case_id in cases)
    family_exact = {
        family: sum(row["exact"] for row in treatment.values() if row["scenario_family"] == family)
        for family in prereg["dataset"]["scenario_families"]
    }
    language_exact = {
        language: {
            "exact": sum(row["exact"] for row in treatment.values() if row["language"] == language),
            "count": sum(1 for row in treatment.values() if row["language"] == language),
        }
        for language in prereg["dataset"]["languages"]
    }
    metric = by_condition[CONDITIONS[1]]
    gates = prereg["treatment_success_gates"]
    checks = {
        "exact_case_count": metric["exact_case_count"] >= gates["exact_case_count_min"],
        "fact_precision": metric["fact_precision"] >= gates["fact_precision_min"],
        "fact_recall": metric["fact_recall"] >= gates["fact_recall_min"],
        "non_assertion_false_write_count": metric["non_assertion_false_write_count"] <= gates["non_assertion_false_write_count_max"],
        "direct_assertion_exact_count": metric["direct_assertion_exact_count"] >= gates["direct_assertion_exact_count_min"],
        "newly_exact_vs_control": newly_exact >= gates["newly_exact_vs_control_min"],
        "regressions_vs_control": regressions <= gates["regressions_vs_control_max"],
        "median_guard_overhead_seconds": metric["median_guard_overhead_seconds"] <= gates["median_guard_overhead_seconds_max"],
        "p95_guard_overhead_seconds": metric["p95_guard_overhead_seconds"] <= gates["p95_guard_overhead_seconds_max"],
    }
    integrity = {
        "row_count_exact": raw["row_count"] == 48 and len(raw["rows"]) == 48,
        "case_count_exact": raw["case_count"] == 24,
        "condition_rows_exact": all(by_condition[condition]["case_count"] == 24 for condition in CONDITIONS),
        "case_condition_pairs_unique": len({(row["case_id"], row["condition"]) for row in raw["rows"]}) == 48,
        "gold_absent": raw["gold_in_raw"] is False,
        "no_model_inference": raw["language_model_inference"] is False,
        "production_unchanged": raw["production_runtime_changed"] is False and raw["persistent_memory_read_or_write"] is False,
        "timing_iterations_exact": (
            raw["warmup_iterations_per_case"] == lock["formal_run"]["timing"]["warmup_iterations_per_case"]
            and raw["scored_iterations_per_case"] == lock["formal_run"]["timing"]["scored_iterations_per_case"]
        ),
    }
    passed = all(checks.values()) and all(integrity.values())
    return {
        "schema": "uruha_profile_assertion_boundary_analysis_v68",
        "experiment_id": prereg["experiment_id"],
        "decision": "authorize_production_guard_integration" if passed else "freeze_result_and_do_not_integrate_guard",
        "run_integrity": {"passed": all(integrity.values()), "checks": integrity},
        "metrics": by_condition,
        "family_exact": family_exact,
        "language_exact": language_exact,
        "pairwise": {"newly_exact_vs_control": newly_exact, "regressions_vs_control": regressions},
        "success_gates": {"passed": all(checks.values()), "checks": checks},
        "case_scores": list(treatment.values()),
        "evidence_boundary": prereg["causal_boundary"],
        "production_runtime_changed": False,
    }


def _markdown(report):
    control = report["metrics"][CONDITIONS[0]]
    treatment = report["metrics"][CONDITIONS[1]]
    failed = [name for name, passed in report["success_gates"]["checks"].items() if not passed]
    lines = [
        "# V68 使用者資料直接陳述邊界結果",
        "",
        f"**決策：** `{report['decision']}`",
        "",
        "| 條件 | 完全正確 | 非陳述誤寫 | 直接陳述保留 | Fact precision | Fact recall | 中位額外延遲 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| 現行無 guard | {control['exact_case_count']}/24 | {control['non_assertion_false_write_count']} | {control['direct_assertion_exact_count']}/12 | {control['fact_precision']:.1%} | {control['fact_recall']:.1%} | 0 ms |",
        f"| assertion scope guard | {treatment['exact_case_count']}/24 | {treatment['non_assertion_false_write_count']} | {treatment['direct_assertion_exact_count']}/12 | {treatment['fact_precision']:.1%} | {treatment['fact_recall']:.1%} | {treatment['median_guard_overhead_seconds'] * 1000:.3f} ms |",
        "",
        f"新答對 {report['pairwise']['newly_exact_vs_control']} 題，退步 {report['pairwise']['regressions_vs_control']} 題。",
        f"預註冊門檻：{'全部通過' if report['success_gates']['passed'] else '未通過'}。",
    ]
    if failed:
        lines.append("未通過：" + ", ".join(failed))
    lines.extend([
        "",
        "本實驗只測 profile facts 是否來自使用者直接自我陳述；尚未測持久化、狀態更新、檢索或最後回答。",
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
            "schema": "uruha_profile_assertion_boundary_result_lock_v68",
            "decision": report["decision"],
            "run_integrity_passed": report["run_integrity"]["passed"],
            "success_gates_passed": report["success_gates"]["passed"],
            "frozen_artifacts": {
                "preregistration": {"path": str(PREREG_PATH.relative_to(ROOT)), "sha256": _sha256(PREREG_PATH)},
                "dataset": {"path": str(DATASET_PATH.relative_to(ROOT)), "sha256": _sha256(DATASET_PATH)},
                "harness_lock": {"path": str(LOCK_PATH.relative_to(ROOT)), "sha256": _sha256(LOCK_PATH)},
                "raw": {"path": str(args.raw.relative_to(ROOT)), "sha256": _sha256(args.raw)},
                "analysis": {"path": str(ANALYSIS_PATH.relative_to(ROOT)), "sha256": _sha256(ANALYSIS_PATH)},
                "markdown": {"path": str(MARKDOWN_PATH.relative_to(ROOT)), "sha256": _sha256(MARKDOWN_PATH)}
            },
            "runtime_change_authorized": report["success_gates"]["passed"] and report["run_integrity"]["passed"],
            "stateful_writer_authorized": False,
            "post_run_case_editing_authorized": False,
            "post_run_threshold_change_authorized": False,
            "evidence_boundary": report["evidence_boundary"]
        }
        RESULT_LOCK_PATH.write_text(json.dumps(result_lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "run_integrity": report["run_integrity"], "metrics": report["metrics"], "pairwise": report["pairwise"], "success_gates": report["success_gates"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
