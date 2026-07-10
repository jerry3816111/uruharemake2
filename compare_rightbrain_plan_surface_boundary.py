#!/usr/bin/env python3
"""Paired comparison for the RightBrain Japanese response-plan boundary."""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_JSON_PATH,
    RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_MD_PATH,
    RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_JSON_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_BASELINE_REF = "87e54f7"
REPORT_REPO_PATH = "reports/rightbrain_selector_human_preference_v1_report.json"
METRICS = (
    "top_score_hit_rate",
    "selected_mean_human_score_1_5",
    "selected_mean_naturalness_1_5",
    "selected_mean_semantic_1_5",
    "chat_ready_yes_rate",
    "bottom_score_selection_rate",
)


def _load_git_json(ref, repo_path):
    process = subprocess.run(
        ["git", "show", f"{ref}:{repo_path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(process.stdout)


def _source_hashes(report):
    return {
        row["source_id"]: row.get("hashes") or {}
        for row in (report.get("data") or {}).get("source_summaries") or []
    }


def _strategy(report, name):
    return report["strict_no_exact_text_overlap"]["strategies"][name]


def _selection_map(report, name):
    return {row["task_id"]: row for row in _strategy(report, name)["selections"]}


def _validate_matched(baseline, candidate):
    mismatches = []
    for key in ("strict_task_count", "strict_candidate_count", "overlapping_task_ids"):
        before = (baseline.get("data") or {}).get(key)
        after = (candidate.get("data") or {}).get(key)
        if before != after:
            mismatches.append(f"data.{key}: {before!r} != {after!r}")
    if _source_hashes(baseline) != _source_hashes(candidate):
        mismatches.append("human-rating source hashes changed")
    for strategy in ("learned_selector_v1", "s0_full_system_candidate"):
        before = {
            task_id: row["selected_review_id"]
            for task_id, row in _selection_map(baseline, strategy).items()
        }
        after = {
            task_id: row["selected_review_id"]
            for task_id, row in _selection_map(candidate, strategy).items()
        }
        if before != after:
            mismatches.append(f"{strategy} selections changed")
    baseline_tasks = set(_selection_map(baseline, "current_runtime_heuristic_proxy"))
    candidate_tasks = set(_selection_map(candidate, "current_runtime_heuristic_proxy"))
    if baseline_tasks != candidate_tasks:
        mismatches.append("runtime heuristic task IDs changed")
    if mismatches:
        raise ValueError("Reports are not a matched single-variable comparison: " + "; ".join(mismatches))


def build_report(baseline, candidate, baseline_ref="baseline"):
    _validate_matched(baseline, candidate)
    before = _strategy(baseline, "current_runtime_heuristic_proxy")
    after = _strategy(candidate, "current_runtime_heuristic_proxy")
    deltas = {metric: round(after[metric] - before[metric], 6) for metric in METRICS}
    before_rows = _selection_map(baseline, "current_runtime_heuristic_proxy")
    after_rows = _selection_map(candidate, "current_runtime_heuristic_proxy")
    changed = []
    for task_id in sorted(before_rows):
        old = before_rows[task_id]
        new = after_rows[task_id]
        if old["selected_review_id"] == new["selected_review_id"]:
            continue
        changed.append(
            {
                "task_id": task_id,
                "before_review_id": old["selected_review_id"],
                "before_text": old["selected_output_text"],
                "before_human_score_1_5": old["human_mean_score_1_5"],
                "before_naturalness_1_5": old["human_naturalness_1_5"],
                "after_review_id": new["selected_review_id"],
                "after_text": new["selected_output_text"],
                "after_human_score_1_5": new["human_mean_score_1_5"],
                "after_naturalness_1_5": new["human_naturalness_1_5"],
            }
        )
    gate = {
        "matched_human_sources_and_task_set": True,
        "learned_and_s0_control_selections_unchanged": True,
        "top_score_hit_rate_improved": deltas["top_score_hit_rate"] > 0,
        "mean_naturalness_improved": deltas["selected_mean_naturalness_1_5"] > 0,
        "mean_semantic_score_noninferior": deltas["selected_mean_semantic_1_5"] >= 0,
        "chat_ready_yes_rate_noninferior": deltas["chat_ready_yes_rate"] >= 0,
        "bottom_score_selection_rate_noninferior": deltas["bottom_score_selection_rate"] <= 0,
    }
    promotion_recommended = all(gate.values())
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_plan_surface_boundary_paired_human_preference_compare",
        "baseline_ref": baseline_ref,
        "candidate_worktree": "current",
        "independent_variable": "F 右腦候選 gate 與評分器中的日文回覆計畫外洩邊界",
        "controlled_variables": {
            "human_rating_source_hashes": _source_hashes(candidate),
            "strict_task_count": candidate["data"]["strict_task_count"],
            "strict_candidate_count": candidate["data"]["strict_candidate_count"],
            "learned_selector_selections_unchanged": True,
            "s0_candidate_selections_unchanged": True,
        },
        "baseline": {metric: before[metric] for metric in METRICS},
        "candidate": {metric: after[metric] for metric in METRICS},
        "deltas": deltas,
        "changed_selection_count": len(changed),
        "changed_selections": changed,
        "gate": gate,
        "promotion_recommended": promotion_recommended,
        "decision_zh": (
            "建議採用：在相同人類盲評候選中，只加入日文回覆計畫邊界後，最高分命中、自然度與語意均提升，且控制組選擇不變。"
            if promotion_recommended
            else "不建議採用：配對人類偏好結果未同時改善自然度與最高分命中，或造成語意／可聊天性退步。"
        ),
        "research_boundary": (
            "這份配對比較沿用單一評分者的部分盲評資料，因此只能估計新邊界在固定候選集上的效果；"
            "不能據此主張開放世界的自然度或真實模型生成品質已全面改善。"
        ),
    }


def write_markdown(report, path):
    before = report["baseline"]
    after = report["candidate"]
    lines = [
        "# 右腦日文回覆計畫邊界：配對比較",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "## 唯一操作變因",
        "",
        report["independent_variable"],
        "",
        "人類評分來源、12 題、48 候選、learned selector 選擇與 S0 選擇全部固定。",
        "",
        "## 前後結果",
        "",
        "| 指標 | 修改前 | 修改後 | 差異 |",
        "|---|---:|---:|---:|",
        f"| 最高人類分數命中 | {before['top_score_hit_rate']:.1%} | {after['top_score_hit_rate']:.1%} | {report['deltas']['top_score_hit_rate'] * 100:+.1f} pp |",
        f"| 平均自然度 | {before['selected_mean_naturalness_1_5']:.3f}/5 | {after['selected_mean_naturalness_1_5']:.3f}/5 | {report['deltas']['selected_mean_naturalness_1_5']:+.3f} |",
        f"| 平均語意 | {before['selected_mean_semantic_1_5']:.3f}/5 | {after['selected_mean_semantic_1_5']:.3f}/5 | {report['deltas']['selected_mean_semantic_1_5']:+.3f} |",
        f"| 可直接聊天率 | {before['chat_ready_yes_rate']:.1%} | {after['chat_ready_yes_rate']:.1%} | {report['deltas']['chat_ready_yes_rate'] * 100:+.1f} pp |",
        "",
        "## 改變的選擇",
        "",
        "| task | 修改前 | 修改後 | 人類分數變化 |",
        "|---|---|---|---:|",
    ]
    for row in report["changed_selections"]:
        delta = row["after_human_score_1_5"] - row["before_human_score_1_5"]
        lines.append(
            f"| {row['task_id']} | {row['before_text']} | {row['after_text']} | {delta:+.2f} |"
        )
    lines.extend(["", "## 採用門檻", "", "| 條件 | 結果 |", "|---|---|"])
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", f"研究邊界：{report['research_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", default=DEFAULT_BASELINE_REF)
    parser.add_argument("--baseline-repo-path", default=REPORT_REPO_PATH)
    parser.add_argument("--candidate-report", default=RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_PLAN_SURFACE_BOUNDARY_COMPARE_REPORT_MD_PATH)
    args = parser.parse_args()

    baseline = _load_git_json(args.baseline_ref, args.baseline_repo_path)
    candidate = json.loads(Path(args.candidate_report).read_text(encoding="utf-8"))
    report = build_report(baseline, candidate, baseline_ref=args.baseline_ref)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({"deltas": report["deltas"], "gate": report["gate"], "promotion_recommended": report["promotion_recommended"]}, ensure_ascii=False, indent=2))
    return 0 if report["promotion_recommended"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
