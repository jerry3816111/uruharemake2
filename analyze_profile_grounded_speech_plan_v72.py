#!/usr/bin/env python3
"""Analyze the frozen V72 typed profile grounding holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path

from run_profile_grounded_speech_plan_v72 import CONDITIONS
from uruha_profile_grounding import STRUCTURAL_SURFACES


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/profile_grounded_speech_plan_v72_preregistration.json"
DATASET = ROOT / "datasets/profile_grounded_speech_plan_v72.json"
LOCK = ROOT / "configs/profile_grounded_speech_plan_v72_harness_lock.json"
RAW = ROOT / "reports/profile_grounded_speech_plan_v72_raw.json"
ANALYSIS = ROOT / "reports/profile_grounded_speech_plan_v72_analysis.json"
MD = ROOT / "reports/profile_grounded_speech_plan_v72_analysis.md"
RESULT = ROOT / "configs/profile_grounded_speech_plan_v72_result_lock.json"

ABSTENTION_MARKERS = (
    "覚えてない",
    "聞いてない",
    "分からない",
    "知らない",
    "記憶にない",
    "記録にない",
    "思い出せない",
    "入ってない",
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def div(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.999999) - 1))]


def _polarity_error(reply, expected):
    relation = (expected["evidence_contract"] or {}).get("relation")
    value = str((expected["evidence_contract"] or {}).get("value") or "")
    if relation in {"likes", "favorite"}:
        return any(marker in reply for marker in ("苦手", "嫌い", "好きじゃない", "無理"))
    if relation == "dislikes":
        if "一番好き" in reply or "本命" in reply:
            return True
        if value:
            pattern = rf"{re.escape(value)}(?:が|は)好き(?!じゃない)"
            return bool(re.search(pattern, reply))
    return False


def score(row, case):
    expected = case["expected"]
    reply = str(row["reply"])
    value_markers = list(expected["required_value_markers"])
    relation_markers = list(expected["required_relation_markers"])
    forbidden_hits = [term for term in expected["forbidden_terms"] if term in reply]
    structural_hits = [term for term in STRUCTURAL_SURFACES if term in reply]
    relevant = bool(expected["memory_relevant"])
    abstention = bool(expected["abstention_required"])
    value_hit = bool(value_markers) and any(marker in reply for marker in value_markers)
    relation_hit = not relation_markers or any(marker in reply for marker in relation_markers)
    abstention_hit = any(marker in reply for marker in ABSTENTION_MARKERS)
    polarity_error = _polarity_error(reply, expected) or bool(forbidden_hits and relevant)
    if relevant:
        case_pass = value_hit and relation_hit and not polarity_error and not structural_hits
    elif abstention:
        case_pass = abstention_hit and not forbidden_hits and not structural_hits
    else:
        case_pass = not forbidden_hits and not structural_hits
    return {
        "case_id": case["id"],
        "family": case["scenario_family"],
        "condition": row["condition"],
        "memory_relevant": relevant,
        "abstention": abstention,
        "evidence_contract_exact": row["evidence_contract"] == expected["evidence_contract"],
        "value_hit": value_hit,
        "relation_scored": bool(relation_markers),
        "relation_hit": relation_hit,
        "abstention_hit": abstention_hit,
        "polarity_error": polarity_error,
        "forbidden_hits": forbidden_hits,
        "structural_hits": structural_hits,
        "case_pass": case_pass,
        "surface_pass": bool(row["surface_gate_pass"]),
        "selector_seconds": float(row["selection_contract"]["selector_seconds"]),
        "turn_seconds": float(row["turn_seconds"]),
        "leftbrain_model_calls": int(row["leftbrain_model_calls"]),
        "selection_status": row["selection_contract"]["status"],
        "reply": reply,
    }


def aggregate(rows):
    relevant = [row for row in rows if row["memory_relevant"]]
    irrelevant = [row for row in rows if not row["memory_relevant"]]
    abstention = [row for row in rows if row["abstention"]]
    relation_rows = [row for row in relevant if row["relation_scored"]]
    selector_times = [row["selector_seconds"] for row in rows if row["selector_seconds"] > 0]
    supported_times = [row["turn_seconds"] for row in relevant]
    return {
        "case_count": len(rows),
        "evidence_contract_exact_case_count": sum(row["evidence_contract_exact"] for row in rows),
        "overall_case_pass_count": sum(row["case_pass"] for row in rows),
        "relevant_case_pass_count": sum(row["case_pass"] for row in relevant),
        "value_slot_hit_count": sum(row["value_hit"] for row in relevant),
        "relation_slot_hit_count": sum(row["relation_hit"] for row in relation_rows),
        "relation_slot_case_count": len(relation_rows),
        "polarity_error_count": sum(row["polarity_error"] for row in rows),
        "structural_label_leak_count": sum(bool(row["structural_hits"]) for row in rows),
        "irrelevant_profile_intrusion_count": sum(bool(row["forbidden_hits"]) for row in irrelevant),
        "abstention_pass_count": sum(row["case_pass"] for row in abstention),
        "surface_gate_pass_count": sum(row["surface_pass"] for row in rows),
        "leftbrain_model_call_count": sum(row["leftbrain_model_calls"] for row in rows),
        "supported_memory_turn_median_seconds": statistics.median(supported_times),
        "supported_memory_turn_p95_seconds": p95(supported_times),
        "selector_median_seconds": statistics.median(selector_times),
        "selector_p95_seconds": p95(selector_times),
    }


def analyze(raw, dataset, prereg):
    cases = {case["id"]: case for case in dataset["cases"]}
    scores = [score(row, cases[row["case_id"]]) for row in raw["rows"]]
    metrics = {
        condition: aggregate([row for row in scores if row["condition"] == condition])
        for condition in CONDITIONS
    }
    maps = {
        condition: {row["case_id"]: row for row in scores if row["condition"] == condition}
        for condition in CONDITIONS
    }
    current = maps[CONDITIONS[0]]
    value_only = maps[CONDITIONS[1]]
    treatment = maps[CONDITIONS[2]]
    newly_value = sum(treatment[key]["case_pass"] and not value_only[key]["case_pass"] for key in treatment)
    regress_value = sum(value_only[key]["case_pass"] and not treatment[key]["case_pass"] for key in treatment)
    newly_current = sum(treatment[key]["case_pass"] and not current[key]["case_pass"] for key in treatment)
    treatment_metrics = metrics[CONDITIONS[2]]
    ability_gates = prereg["ability_success_gates"]
    cost_gates = prereg["local_cost_gates"]

    integrity = {
        "rows": raw["row_count"] == 72 and len(raw["rows"]) == 72,
        "pairs": len({(row["case_id"], row["condition"]) for row in raw["rows"]}) == 72,
        "conditions": raw["conditions"] == list(CONDITIONS),
        "locked_preflight": raw["locked_preflight"]["passed"] is True
        and raw["locked_preflight"]["observed_test_count"] == raw["locked_preflight"]["expected_test_count"],
        "gold_absent": raw["gold_in_raw"] is False,
        "temporary_databases": all(row["temporary_database"] for row in raw["rows"]),
        "rightbrain_model_off": raw["rightbrain_model_loading"] is False,
        "selector_calls": raw["selector_call_count"] == 24,
    }
    ability_checks = {
        "evidence_contract": treatment_metrics["evidence_contract_exact_case_count"] >= ability_gates["evidence_contract_exact_case_count_min"],
        "relevant": treatment_metrics["relevant_case_pass_count"] >= ability_gates["relevant_case_pass_count_min"],
        "overall": treatment_metrics["overall_case_pass_count"] >= ability_gates["overall_case_pass_count_min"],
        "value": treatment_metrics["value_slot_hit_count"] >= ability_gates["value_slot_hit_count_min"],
        "relation": treatment_metrics["relation_slot_hit_count"] >= ability_gates["relation_slot_hit_count_min"],
        "polarity": treatment_metrics["polarity_error_count"] <= ability_gates["polarity_error_count_max"],
        "structural_leak": treatment_metrics["structural_label_leak_count"] <= ability_gates["structural_label_leak_count_max"],
        "intrusion": treatment_metrics["irrelevant_profile_intrusion_count"] <= ability_gates["irrelevant_profile_intrusion_count_max"],
        "abstention": treatment_metrics["abstention_pass_count"] >= ability_gates["abstention_pass_count_min"],
        "new_vs_value": newly_value >= ability_gates["newly_passed_vs_value_only_min"],
        "regressions_vs_value": regress_value <= ability_gates["regressions_vs_value_only_max"],
        "new_vs_current": newly_current >= ability_gates["newly_passed_vs_current_pipeline_min"],
    }
    call_reduction = metrics[CONDITIONS[0]]["leftbrain_model_call_count"] - treatment_metrics["leftbrain_model_call_count"]
    cost_checks = {
        "leftbrain_calls": call_reduction >= cost_gates["leftbrain_model_calls_reduction_vs_current_min"],
        "turn_median": treatment_metrics["supported_memory_turn_median_seconds"] <= cost_gates["supported_memory_turn_median_seconds_max"],
        "turn_p95": treatment_metrics["supported_memory_turn_p95_seconds"] <= cost_gates["supported_memory_turn_p95_seconds_max"],
        "selector_median": treatment_metrics["selector_median_seconds"] <= cost_gates["selector_median_seconds_max"],
        "selector_p95": treatment_metrics["selector_p95_seconds"] <= cost_gates["selector_p95_seconds_max"],
        "transport": raw["transport_error_count"] <= cost_gates["transport_error_count_max"],
        "production": raw["production_database_access_count"] <= cost_gates["production_database_access_count_max"],
        "physical": raw["physical_action_count"] <= cost_gates["physical_action_count_max"],
    }
    integrity_passed = all(integrity.values())
    ability_passed = all(ability_checks.values())
    cost_passed = all(cost_checks.values())
    contracts_passed = ability_checks["evidence_contract"]
    if not integrity_passed:
        decision = "invalid_run"
    elif ability_passed and cost_passed:
        decision = "authorize_grounded_plan_answer_shadow_only"
    elif ability_passed:
        decision = "authorize_cost_optimization_research_only"
    elif contracts_passed:
        decision = "freeze_answer_use_and_move_to_rightbrain_or_self_monitor"
    else:
        decision = "stop_bridge_hypothesis_and_reassess_evidence_representation"

    return {
        "schema": "uruha_profile_grounded_speech_plan_analysis_v72",
        "decision": decision,
        "run_integrity": {"passed": integrity_passed, "checks": integrity},
        "ability_gates": {"passed": ability_passed, "checks": ability_checks},
        "cost_gates": {"passed": cost_passed, "checks": cost_checks},
        "metrics": metrics,
        "pairwise": {
            "newly_passed_vs_value_only": newly_value,
            "regressions_vs_value_only": regress_value,
            "newly_passed_vs_current_pipeline": newly_current,
        },
        "cost": {"leftbrain_model_calls_reduction_vs_current": call_reduction},
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
            "# V72 記憶證據到回答規劃接橋結果",
            "",
            f"**決策：** `{report['decision']}`",
            "",
            "| 條件 | 證據正確 | 全體通過 | 記憶題通過 | 值命中 | 關係命中 | 極性錯誤 | 左腦呼叫 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for condition in CONDITIONS:
            metric = report["metrics"][condition]
            lines.append(
                f"| {condition} | {metric['evidence_contract_exact_case_count']}/24 | "
                f"{metric['overall_case_pass_count']}/24 | {metric['relevant_case_pass_count']}/16 | "
                f"{metric['value_slot_hit_count']}/16 | {metric['relation_slot_hit_count']}/{metric['relation_slot_case_count']} | "
                f"{metric['polarity_error_count']} | {metric['leftbrain_model_call_count']} |"
            )
        lines.extend(
            [
                "",
                f"相對 value-only：新增通過 {report['pairwise']['newly_passed_vs_value_only']}，退步 {report['pairwise']['regressions_vs_value_only']}。",
                f"相對舊流程：新增通過 {report['pairwise']['newly_passed_vs_current_pipeline']}。",
                "",
                "只測臨時資料庫中的完整聊天 shadow；沒有啟用正式記憶回答。",
            ]
        )
        MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        RESULT.write_text(
            json.dumps(
                {
                    "schema": "uruha_profile_grounded_speech_plan_result_lock_v72",
                    "decision": report["decision"],
                    "run_integrity_passed": report["run_integrity"]["passed"],
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
                    "grounded_plan_shadow_authorized": report["decision"] == "authorize_grounded_plan_answer_shadow_only",
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
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
