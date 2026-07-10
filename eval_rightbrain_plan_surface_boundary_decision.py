#!/usr/bin/env python3
"""Combine human-preference, actual-model, and selector evidence for one release decision."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_JSON_PATH,
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_DECISION_REPORT_MD_PATH,
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_RUNTIME_COMPARE_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_JSON_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_report(human_report, runtime_report, selector_report):
    runtime_evidence = runtime_report["runtime_gate_evidence"]
    raw_control = runtime_evidence["raw_candidate_control"]
    selector_takeover = bool(
        (selector_report.get("gate") or {}).get("human_preference_takeover_recommended")
    )
    gates = {
        "paired_human_preference_effect_pass": bool(human_report.get("promotion_recommended")),
        "actual_model_shadow_safety_pass": bool(runtime_report.get("runtime_shadow_safety_pass")),
        "actual_model_raw_candidates_fully_matched": bool(raw_control.get("all_identical")),
        "actual_model_introduced_surface_issue_count_is_zero": (
            int(runtime_evidence.get("introduced_final_surface_issue_count") or 0) == 0
        ),
        "learned_selector_remains_observe_only": not selector_takeover,
    }
    adopt_boundary = all(gates.values())
    human_before = human_report["baseline"]
    human_after = human_report["candidate"]
    runtime_after = runtime_report["aggregate"]["promoted"]
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_plan_surface_boundary_release_decision",
        "independent_variable": human_report.get("independent_variable"),
        "gates": gates,
        "adopt_runtime_boundary": adopt_boundary,
        "replace_v10_adapter": False,
        "enable_learned_selector": False,
        "human_paired_evidence": {
            "strict_task_count": human_report["controlled_variables"]["strict_task_count"],
            "strict_candidate_count": human_report["controlled_variables"]["strict_candidate_count"],
            "top_score_hit_rate_before": human_before["top_score_hit_rate"],
            "top_score_hit_rate_after": human_after["top_score_hit_rate"],
            "mean_naturalness_before": human_before["selected_mean_naturalness_1_5"],
            "mean_naturalness_after": human_after["selected_mean_naturalness_1_5"],
            "mean_semantic_before": human_before["selected_mean_semantic_1_5"],
            "mean_semantic_after": human_after["selected_mean_semantic_1_5"],
            "chat_ready_before": human_before["chat_ready_yes_rate"],
            "chat_ready_after": human_after["chat_ready_yes_rate"],
        },
        "actual_model_shadow_evidence": {
            "seed_count": len(runtime_report.get("seeds") or []),
            "case_count": runtime_after["case_count"],
            "raw_candidate_count": raw_control["candidate_raw_candidate_count"],
            "raw_candidates_identical": raw_control["all_identical"],
            "fixed_final_surface_issue_count": runtime_evidence["fixed_final_surface_issue_count"],
            "introduced_final_surface_issue_count": runtime_evidence[
                "introduced_final_surface_issue_count"
            ],
            "final_quality_pass_rate": runtime_after["final_quality_pass_rate"],
            "runtime_standalone_promotion_recommended": runtime_report["promotion_recommended"],
            "runtime_shadow_safety_pass": runtime_report["runtime_shadow_safety_pass"],
        },
        "decision_zh": (
            "採用 F 右腦日文回覆計畫邊界；V10 adapter 不變，learned selector 繼續 observe-only。"
            if adopt_boundary
            else "不採用 F 右腦日文回覆計畫邊界：人類偏好改善、真實模型安全或部署邊界至少一項未通過。"
        ),
        "research_boundary": (
            "真人配對證據只有一位評分者與 12 題嚴格樣本；60 個真實模型候選沒有命中策略外洩，"
            "因此只能支持安全非劣，不能支持真實模型已有修復效果，也不能主張開放世界的人類自然度。"
        ),
    }


def write_markdown(report, path):
    human = report["human_paired_evidence"]
    runtime = report["actual_model_shadow_evidence"]
    lines = [
        "# F 右腦日文回覆計畫邊界：採用決策",
        "",
        "## 決策",
        "",
        report["decision_zh"],
        "",
        "這次修正的不是左腦推理能力，而是 F 右腦的輸出責任：內部可以保留回覆策略，最終只能對使用者直接說話。",
        "",
        "## 唯一操作變因",
        "",
        str(report.get("independent_variable") or ""),
        "",
        "模型、V10 adapter、候選文字、記憶、左腦計畫、seed 與人類評分都保持不變。",
        "",
        "## 證據一：固定真人盲評候選",
        "",
        "| 指標 | 修改前 | 修改後 | 差異 |",
        "|---|---:|---:|---:|",
        f"| 最高人類分數命中 | {human['top_score_hit_rate_before']:.1%} | {human['top_score_hit_rate_after']:.1%} | {(human['top_score_hit_rate_after'] - human['top_score_hit_rate_before']) * 100:+.1f} pp |",
        f"| 平均自然度 | {human['mean_naturalness_before']:.3f}/5 | {human['mean_naturalness_after']:.3f}/5 | {human['mean_naturalness_after'] - human['mean_naturalness_before']:+.3f} |",
        f"| 平均語意 | {human['mean_semantic_before']:.3f}/5 | {human['mean_semantic_after']:.3f}/5 | {human['mean_semantic_after'] - human['mean_semantic_before']:+.3f} |",
        f"| 可直接聊天 | {human['chat_ready_before']:.1%} | {human['chat_ready_after']:.1%} | {(human['chat_ready_after'] - human['chat_ready_before']) * 100:+.1f} pp |",
        "",
        f"控制條件為相同 {human['strict_task_count']} 題、{human['strict_candidate_count']} 個候選與相同人類評分。",
        "",
        "代表性改變：",
        "",
        "- 修改前：`返事がない不安を認め、自分で決めつけないように返す。`",
        "- 修改後：`既読で止まると不安になるよな。でも煩いって決めつけるな。`",
        "",
        "## 證據二：真實 V10 雙種子 shadow",
        "",
        "| 控制與結果 | 數值 |",
        "|---|---:|",
        f"| matched seeds | {runtime['seed_count']} |",
        f"| holdout cases | {runtime['case_count']} |",
        f"| raw candidates | {runtime['raw_candidate_count']} |",
        f"| 前後逐字相同 raw candidates | {'全部相同' if runtime['raw_candidates_identical'] else '不相同'} |",
        f"| 新增最終表面問題 | {runtime['introduced_final_surface_issue_count']} |",
        f"| 最終品質通過率 | {runtime['final_quality_pass_rate']:.1%} |",
        "",
        "這批真實 V10 候選沒有出現待修正策略句，因此不能單獨證明修復效果；它證明的是加入邊界後安全非劣。",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            report["research_boundary"],
            "",
            "learned selector 仍輸給真人偏好基準，因此繼續 observe-only，不能接管正式回答。",
            "",
            "V10 兩個 seed 的原始候選接受率合計仍只有 43.3%，下一個主要瓶頸仍是模型本體生成可靠度。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-report", default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_JSON_PATH)
    parser.add_argument(
        "--runtime-report",
        default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_RUNTIME_COMPARE_REPORT_JSON_PATH,
    )
    parser.add_argument("--selector-report", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_JSON_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_DECISION_REPORT_MD_PATH)
    args = parser.parse_args()

    report = build_report(
        _load_json(args.human_report),
        _load_json(args.runtime_report),
        _load_json(args.selector_report),
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({"gates": report["gates"], "adopt_runtime_boundary": report["adopt_runtime_boundary"]}, ensure_ascii=False, indent=2))
    return 0 if report["adopt_runtime_boundary"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
