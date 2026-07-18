#!/usr/bin/env python3
"""Analyze the frozen V71 profile relevance and speakability holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from run_profile_relevance_speakability_v71 import CONDITIONS


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/profile_relevance_speakability_v71_preregistration.json"
DATASET = ROOT / "datasets/profile_relevance_speakability_v71.json"
LOCK = ROOT / "configs/profile_relevance_speakability_v71_harness_lock.json"
RAW = ROOT / "reports/profile_relevance_speakability_v71_raw.json"
ANALYSIS = ROOT / "reports/profile_relevance_speakability_v71_analysis.json"
MD = ROOT / "reports/profile_relevance_speakability_v71_analysis.md"
RESULT = ROOT / "configs/profile_relevance_speakability_v71_result_lock.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def div(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.999999) - 1))]


def score(row, case):
    expected = case["expected"]
    expected_ids = list(expected["selected_memory_ids"])
    selected_ids = list(row["selected_memory_ids"])
    reply = str(row["reply"])
    groups = expected["required_marker_groups"]
    hits = [any(str(marker) in reply for marker in group) for group in groups]
    forbidden = [term for term in expected["forbidden_terms"] if term in reply]
    return {
        "case_id": case["id"],
        "family": case["scenario_family"],
        "condition": row["condition"],
        "memory_relevant": expected["memory_relevant"],
        "abstention": expected["abstention_required"],
        "expected_memory_ids": expected_ids,
        "selected_memory_ids": selected_ids,
        "selector_exact": selected_ids == expected_ids,
        "selector_false_positive": not expected_ids and bool(selected_ids),
        "selector_false_negative": bool(expected_ids) and selected_ids != expected_ids,
        "required_hits": sum(hits),
        "required_count": len(hits),
        "forbidden_hits": forbidden,
        "case_pass": all(hits) and not forbidden,
        "surface_pass": row["surface_gate_pass"],
        "selector_seconds": row["selection_contract"]["selector_seconds"],
        "turn_seconds": row["turn_seconds"],
        "selection_status": row["selection_contract"]["status"],
        "reply": reply,
    }


def aggregate(rows):
    relevant = [row for row in rows if row["memory_relevant"]]
    irrelevant = [row for row in rows if not row["memory_relevant"]]
    abstention = [row for row in rows if row["abstention"]]
    selector_times = [row["selector_seconds"] for row in rows if row["selector_seconds"] > 0]
    return {
        "case_count": len(rows),
        "selector_exact_case_count": sum(row["selector_exact"] for row in rows),
        "selector_false_positive_count": sum(row["selector_false_positive"] for row in rows),
        "selector_false_negative_count": sum(row["selector_false_negative"] for row in rows),
        "overall_pass_count": sum(row["case_pass"] for row in rows),
        "relevant_pass_count": sum(row["case_pass"] for row in relevant),
        "required_marker_group_recall": div(
            sum(row["required_hits"] for row in rows),
            sum(row["required_count"] for row in rows),
        ),
        "irrelevant_profile_intrusion_count": sum(bool(row["forbidden_hits"]) for row in irrelevant),
        "abstention_pass_count": sum(row["case_pass"] for row in abstention),
        "surface_gate_pass_count": sum(row["surface_pass"] for row in rows),
        "median_selector_seconds": statistics.median(selector_times) if selector_times else 0.0,
        "p95_selector_seconds": p95(selector_times) if selector_times else 0.0,
        "median_full_turn_seconds": statistics.median(row["turn_seconds"] for row in rows),
        "p95_full_turn_seconds": p95([row["turn_seconds"] for row in rows]),
    }


def analyze(raw, dataset, prereg):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = [score(row, cases[row["case_id"]]) for row in raw["rows"]]
    metrics = {
        condition: aggregate([row for row in scores if row["condition"] == condition])
        for condition in CONDITIONS
    }
    maps = {
        condition: {
            row["case_id"]: row for row in scores if row["condition"] == condition
        }
        for condition in CONDITIONS
    }
    full = maps[CONDITIONS[0]]
    bare = maps[CONDITIONS[1]]
    treatment = maps[CONDITIONS[2]]
    newly_bare = sum(treatment[key]["case_pass"] and not bare[key]["case_pass"] for key in treatment)
    regress_bare = sum(bare[key]["case_pass"] and not treatment[key]["case_pass"] for key in treatment)
    newly_full = sum(treatment[key]["case_pass"] and not full[key]["case_pass"] for key in treatment)
    treatment_metrics = metrics[CONDITIONS[2]]
    ability_gates = prereg["ability_success_gates"]
    cost_gates = prereg["local_cost_gates"]

    selector_checks = {
        "selector_exact": treatment_metrics["selector_exact_case_count"] >= ability_gates["selector_exact_case_count_min"],
        "selector_false_positive": treatment_metrics["selector_false_positive_count"] <= ability_gates["selector_false_positive_count_max"],
        "selector_false_negative": treatment_metrics["selector_false_negative_count"] <= ability_gates["selector_false_negative_count_max"],
    }
    ability_checks = {
        **selector_checks,
        "relevant": treatment_metrics["relevant_pass_count"] >= ability_gates["relevant_case_pass_count_min"],
        "overall": treatment_metrics["overall_pass_count"] >= ability_gates["overall_case_pass_count_min"],
        "marker_recall": treatment_metrics["required_marker_group_recall"] >= ability_gates["required_marker_group_recall_min"],
        "intrusion": treatment_metrics["irrelevant_profile_intrusion_count"] <= ability_gates["irrelevant_profile_intrusion_count_max"],
        "abstention": treatment_metrics["abstention_pass_count"] >= ability_gates["abstention_pass_count_min"],
        "new_vs_bare": newly_bare >= ability_gates["newly_passed_vs_bare_key_min"],
        "regressions_vs_bare": regress_bare <= ability_gates["regressions_vs_bare_key_max"],
        "new_vs_full": newly_full >= ability_gates["newly_passed_vs_full_projection_min"],
        "surface": treatment_metrics["surface_gate_pass_count"] + ability_gates["surface_gate_regression_vs_full_projection_max"] >= metrics[CONDITIONS[0]]["surface_gate_pass_count"],
    }
    cost_checks = {
        "encoder_load": raw["encoder_load_seconds"] <= cost_gates["encoder_load_seconds_max"],
        "encoder_rss": raw["encoder_peak_rss_delta_bytes"] <= cost_gates["encoder_peak_rss_delta_bytes_max"],
        "selector_median": treatment_metrics["median_selector_seconds"] <= cost_gates["median_selector_seconds_max"],
        "selector_p95": treatment_metrics["p95_selector_seconds"] <= cost_gates["p95_selector_seconds_max"],
        "turn_median": treatment_metrics["median_full_turn_seconds"] <= cost_gates["median_full_turn_seconds_max"],
        "turn_p95": treatment_metrics["p95_full_turn_seconds"] <= cost_gates["p95_full_turn_seconds_max"],
        "transport": raw["transport_error_count"] <= cost_gates["transport_error_count_max"],
        "production": raw["production_database_access_count"] <= cost_gates["production_database_access_count_max"],
        "physical": raw["physical_action_count"] <= cost_gates["physical_action_count_max"],
    }
    integrity = {
        "rows": raw["row_count"] == 72 and len(raw["rows"]) == 72,
        "pairs": len({(row["case_id"], row["condition"]) for row in raw["rows"]}) == 72,
        "conditions": raw["conditions"] == list(CONDITIONS),
        "locked_preflight": raw["locked_preflight"]["passed"] is True
        and raw["locked_preflight"]["observed_test_count"] == raw["locked_preflight"]["expected_test_count"],
        "gold_absent": raw["gold_in_raw"] is False,
        "temporary_databases": all(row["temporary_database"] for row in raw["rows"]),
        "rightbrain_model_off": raw["rightbrain_model_loading"] is False,
        "selector_calls": raw["selector_call_count"] == 48,
    }
    integrity_passed = all(integrity.values())
    selector_passed = all(selector_checks.values())
    ability_passed = all(ability_checks.values())
    cost_passed = all(cost_checks.values())
    if not integrity_passed:
        decision = "invalid_run"
    elif ability_passed and cost_passed:
        decision = "authorize_answer_path_shadow_only"
    elif ability_passed:
        decision = "authorize_cost_optimization_research_only"
    elif selector_passed:
        decision = "freeze_answer_use_and_move_downstream"
    else:
        decision = "stop_selector_hypothesis_and_reassess_representation"

    return {
        "schema": "uruha_profile_relevance_speakability_analysis_v71",
        "decision": decision,
        "run_integrity": {"passed": integrity_passed, "checks": integrity},
        "selector_gates": {"passed": selector_passed, "checks": selector_checks},
        "ability_gates": {"passed": ability_passed, "checks": ability_checks},
        "cost_gates": {"passed": cost_passed, "checks": cost_checks},
        "metrics": metrics,
        "cost": {
            "encoder_load_seconds": raw["encoder_load_seconds"],
            "encoder_peak_rss_delta_bytes": raw["encoder_peak_rss_delta_bytes"],
        },
        "pairwise": {
            "newly_passed_vs_bare_key": newly_bare,
            "regressions_vs_bare_key": regress_bare,
            "newly_passed_vs_full_projection": newly_full,
        },
        "treatment_case_scores": list(treatment.values()),
        "evidence_boundary": prereg["causal_boundary"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze(load(RAW), load(DATASET), load(PREREG))
    if args.write:
        ANALYSIS.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = [
            "# V71 使用者資料相關性與可說性結果",
            "",
            f"**決策：** `{report['decision']}`",
            "",
            "| 條件 | 選對記憶 | 全體通過 | 記憶題通過 | 無關侵入 | 不知道時拒答 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for condition in CONDITIONS:
            metric = report["metrics"][condition]
            lines.append(
                f"| {condition} | {metric['selector_exact_case_count']}/24 | "
                f"{metric['overall_pass_count']}/24 | {metric['relevant_pass_count']}/16 | "
                f"{metric['irrelevant_profile_intrusion_count']} | {metric['abstention_pass_count']}/4 |"
            )
        lines.extend(
            [
                "",
                f"相對 bare key：新增通過 {report['pairwise']['newly_passed_vs_bare_key']}，退步 {report['pairwise']['regressions_vs_bare_key']}。",
                f"相對整份 profile：新增通過 {report['pairwise']['newly_passed_vs_full_projection']}。",
                "",
                "只測臨時資料庫中的完整聊天 shadow；沒有啟用正式記憶回答。",
            ]
        )
        MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        RESULT.write_text(
            json.dumps(
                {
                    "schema": "uruha_profile_relevance_speakability_result_lock_v71",
                    "decision": report["decision"],
                    "run_integrity_passed": report["run_integrity"]["passed"],
                    "selector_gates_passed": report["selector_gates"]["passed"],
                    "ability_gates_passed": report["ability_gates"]["passed"],
                    "cost_gates_passed": report["cost_gates"]["passed"],
                    "frozen_artifacts": {
                        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha(PREREG)},
                        "dataset": {"path": str(DATASET.relative_to(ROOT)), "sha256": sha(DATASET)},
                        "harness_lock": {"path": str(LOCK.relative_to(ROOT)), "sha256": sha(LOCK)},
                        "raw": {"path": str(RAW.relative_to(ROOT)), "sha256": sha(RAW)},
                        "analysis": {"path": str(ANALYSIS.relative_to(ROOT)), "sha256": sha(ANALYSIS)},
                        "markdown": {"path": str(MD.relative_to(ROOT)), "sha256": sha(MD)},
                    },
                    "answer_path_shadow_authorized": report["decision"] == "authorize_answer_path_shadow_only",
                    "runtime_activation_authorized": False,
                    "post_run_case_editing_authorized": False,
                    "post_run_threshold_change_authorized": False,
                    "evidence_boundary": report["evidence_boundary"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "integrity": report["run_integrity"],
                "selector": report["selector_gates"],
                "ability": report["ability_gates"],
                "cost": report["cost_gates"],
                "metrics": report["metrics"],
                "pairwise": report["pairwise"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
