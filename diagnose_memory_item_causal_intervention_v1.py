#!/usr/bin/env python3
"""Diagnose the frozen V1 result without overriding its formal decision."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment
import run_memory_item_causal_intervention_v1 as runner


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/memory_item_causal_intervention_v1_diagnosis.json"
REPORT_MD = ROOT / "reports/memory_item_causal_intervention_v1_diagnosis.md"


def _percentile(values, fraction):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def _case_summary(rows):
    summaries = []
    for case_id in sorted({row["case_id"] for row in rows}):
        group = {row["condition"]: row for row in rows if row["case_id"] == case_id}
        summaries.append(
            {
                "case_id": case_id,
                "intact_target_anchor": bool(group[experiment.C0]["target_anchor"]),
                "intact_target_plan": bool(group[experiment.C0]["target_marker_in_plan"]),
                "removed_target_plan": bool(group[experiment.T1]["target_marker_in_plan"]),
                "replacement_anchor": bool(group[experiment.T2]["replacement_anchor"]),
                "replacement_plan": bool(group[experiment.T2]["replacement_marker_in_plan"]),
                "irrelevant_removed_target_plan": bool(group[experiment.N1]["target_marker_in_plan"]),
                "leftbrain_model_call_count": sum(row["leftbrain_call_count"] for row in group.values()),
                "maximum_elapsed_seconds": max(float(row["elapsed_seconds"]) for row in group.values()),
            }
        )
    return summaries


def build_diagnosis(rows, formal_report):
    failed_cleanliness = [
        row
        for row in rows
        if not row["decision_view_target_absent_when_required"]
        or not row["decision_view_irrelevant_absent_when_required"]
    ]
    model_rows = [row for row in rows if row["leftbrain_call_count"] > 0]
    rule_rows = [row for row in rows if row["leftbrain_call_count"] == 0]
    model_latencies = [float(row["elapsed_seconds"]) for row in model_rows]
    case_summaries = _case_summary(rows)
    uncovered = [row["case_id"] for row in case_summaries if not row["intact_target_anchor"]]
    return {
        "schema": "uruha_memory_item_causal_diagnosis_v1",
        "formal_decision_preserved": formal_report["decision"],
        "decision_override_authorized": False,
        "causal_behavior_observation": {
            "intact_target_plan_rate": formal_report["condition_summaries"][experiment.C0]["target_marker_in_plan_rate"],
            "removed_target_plan_rate": formal_report["condition_summaries"][experiment.T1]["target_marker_in_plan_rate"],
            "replacement_plan_rate": formal_report["condition_summaries"][experiment.T2]["replacement_marker_in_plan_rate"],
            "irrelevant_removed_target_plan_rate": formal_report["condition_summaries"][experiment.N1]["target_marker_in_plan_rate"],
            "paired_target_removal_delta": formal_report["paired_effects"]["target_removal_plan_marker"]["mean_delta"],
            "paired_bootstrap_95_ci": formal_report["paired_effects"]["target_removal_plan_marker"]["bootstrap_95_ci"],
        },
        "cleanliness_failure_diagnosis": {
            "failed_row_count": len(failed_cleanliness),
            "all_failed_rows_are_replacement_condition": len(failed_cleanliness) == 8
            and all(row["condition"] == experiment.T2 for row in failed_cleanliness),
            "target_semantic_marker_reappeared_in_plan_count": sum(row["target_marker_in_plan"] for row in failed_cleanliness),
            "target_semantic_marker_reappeared_in_reply_count": sum(row["target_marker_in_reply"] for row in failed_cleanliness),
            "replacement_marker_present_in_plan_count": sum(row["replacement_marker_in_plan"] for row in failed_cleanliness),
            "implementation_source": "replacement rows retain intervention_origin_trace_id for audit; the frozen cleanliness predicate also forbids that nonsemantic pointer",
            "classification": "audit_pointer_false_positive_requires_new_locked_harness",
        },
        "latency_diagnosis": {
            "model_path_row_count": len(model_rows),
            "rule_path_row_count": len(rule_rows),
            "model_path_median_seconds": statistics.median(model_latencies) if model_latencies else 0.0,
            "model_path_p95_seconds": _percentile(model_latencies, 0.95),
            "model_path_over_60_seconds_count": sum(value > 60.0 for value in model_latencies),
            "maximum_seconds": max(float(row["elapsed_seconds"]) for row in rows),
            "classification": "causal_signal_observed_but_current_local_planner_latency_gate_failed",
        },
        "coverage_diagnosis": {
            "covered_case_count": len(case_summaries) - len(uncovered),
            "total_case_count": len(case_summaries),
            "uncovered_case_ids": uncovered,
            "plant_name_observation": "The plant-name prompt entered the name-query path, but the current anchor extractor did not bind the non-person pattern 名前はミモザ/ルナ.",
        },
        "case_summaries": case_summaries,
        "next_evidence_requirement": "建立新的鎖定實驗，把審計用的原始指標移出決策視野，並將因果有效性與部署延遲分開判定；不得把 V1 重新解釋成正式通過。",
    }


def render_markdown(report):
    causal = report["causal_behavior_observation"]
    latency = report["latency_diagnosis"]
    coverage = report["coverage_diagnosis"]
    lines = [
        "# 逐筆記憶因果干預 V1 診斷",
        "",
        f"**正式判定維持：{report['formal_decision_preserved']}**",
        "",
        "本診斷不能覆蓋原判定，只說明為什麼失敗，以及哪些觀察仍可保留。",
        "",
        "## 能力觀察",
        "",
        f"- 完整記憶的目標計畫命中：{causal['intact_target_plan_rate']:.1%}",
        f"- 只移除目標後：{causal['removed_target_plan_rate']:.1%}",
        f"- 替換目標後的替換內容命中：{causal['replacement_plan_rate']:.1%}",
        f"- 只移除無關記憶後的目標命中：{causal['irrelevant_removed_target_plan_rate']:.1%}",
        f"- 配對差：{causal['paired_target_removal_delta']:+.1%}；95% CI [{causal['paired_bootstrap_95_ci'][0]:+.1%}, {causal['paired_bootstrap_95_ci'][1]:+.1%}]",
        "",
        "## 為什麼不能正式通過",
        "",
        "1. 替換記錄為了審計保留原始 trace_id 指標，舊檢查器把這個非語意欄位也當成洩漏。",
        f"2. 模型路徑中位數 {latency['model_path_median_seconds']:.1f} 秒、P95 {latency['model_path_p95_seconds']:.1f} 秒，超過 60 秒共 {latency['model_path_over_60_seconds_count']} 組。",
        "",
        "## 覆蓋缺口",
        "",
        f"- 成功建立目標錨點：{coverage['covered_case_count']}/{coverage['total_case_count']}。",
        f"- 未覆蓋案例：{', '.join(coverage['uncovered_case_ids']) or 'none'}。",
        "- 植物名稱被誤導入人物姓名抽取路徑，因此沒有綁定ミモザ/ルナ。",
        "",
        "## 下一個證據要求",
        "",
        report["next_evidence_requirement"],
        "",
    ]
    return "\n".join(lines)


def main():
    rows = runner.load_jsonl(runner.RAW_PATH)
    formal = json.loads(
        (ROOT / "reports/memory_item_causal_intervention_v1.json").read_text(encoding="utf-8")
    )
    report = build_diagnosis(rows, formal)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"formal_decision": report["formal_decision_preserved"], "coverage": report["coverage_diagnosis"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
