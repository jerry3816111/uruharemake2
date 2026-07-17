#!/usr/bin/env python3
"""Analyze the frozen exact-source pointer pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_source_pointer_v1_preregistration.json"
)
BASELINE_PATH = (
    ROOT / "reports" / "consolidation_source_pointer_v1_baseline.json"
)
TREATMENT_PATH = (
    ROOT / "reports" / "consolidation_source_pointer_v1_treatment.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "consolidation_source_pointer_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "consolidation_source_pointer_v1_analysis.md"
)
PREREGISTRATION_MERGE_COMMIT = (
    "c5b56665ef6deb218ddb595c9c2bdcb09a9e0753"
)
RUNTIME_PATHS = (
    "uruha_brain_mac.py",
    "uruha_memory_runtime.py",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_sha256(commit, path):
    content = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(content).hexdigest()


def _is_ancestor(ancestor, descendant):
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def _integrity_rejections_have_reasons(treatment):
    rows = [
        row
        for row in treatment["cases"]
        if row["split"] == "integrity"
    ]
    return bool(rows) and all(
        not row["pointer_activated"]
        and bool(row["source_pointer_rejection_reasons"])
        for row in rows
    )


def _evaluate_gates(config, baseline, treatment):
    expected = config["success_gates"]
    baseline_summary = baseline["summary"]
    treatment_summary = treatment["summary"]
    net_gain = (
        treatment_summary["positive_target_source_hits"]
        - baseline_summary["positive_target_source_hits"]
    )
    observations = {
        "control_positive_target_source_hits_exact": (
            baseline_summary["positive_target_source_hits"],
            "exact",
        ),
        "treatment_positive_target_source_hits_min": (
            treatment_summary["positive_target_source_hits"],
            "minimum",
        ),
        "paired_positive_net_gain_min": (net_gain, "minimum"),
        "treatment_positive_exact_user_text_hits_min": (
            treatment_summary["positive_exact_user_text_hits"],
            "minimum",
        ),
        "treatment_positive_summary_exact_user_text_hits_min": (
            treatment_summary[
                "positive_summary_exact_user_text_hits"
            ],
            "minimum",
        ),
        "treatment_wrong_source_injections_exact": (
            treatment_summary["wrong_source_injections"],
            "exact",
        ),
        "treatment_integrity_pointer_activations_exact": (
            treatment_summary["integrity_pointer_activations"],
            "exact",
        ),
        "treatment_unrelated_pointer_activations_exact": (
            treatment_summary["unrelated_pointer_activations"],
            "exact",
        ),
        "treatment_top_level_selection_unchanged_count_exact": (
            treatment_summary[
                "top_level_selection_unchanged_count"
            ],
            "exact",
        ),
        "treatment_maximum_source_evidence_count_max": (
            treatment_summary["maximum_source_evidence_count"],
            "maximum",
        ),
        "treatment_external_model_calls_exact": (
            treatment["external_model_calls"],
            "exact",
        ),
        "all_integrity_rejections_have_controller_reason": (
            _integrity_rejections_have_reasons(treatment),
            "exact",
        ),
    }
    gates = {}
    for key, (observed, comparison) in observations.items():
        required = expected[key]
        if comparison == "minimum":
            passed = observed >= required
        elif comparison == "maximum":
            passed = observed <= required
        else:
            passed = observed == required
        gates[key] = {
            "required": required,
            "observed": observed,
            "comparison": comparison,
            "passed": passed,
        }
    return gates


def analyze():
    config = _load(CONFIG_PATH)
    baseline = _load(BASELINE_PATH)
    treatment = _load(TREATMENT_PATH)
    dataset = _load(DATASET_PATH)
    frozen = config["frozen_baseline"]
    candidate_commit = treatment["runtime_commit"]

    artifact_checks = {
        "dataset_hash": (
            _sha256(DATASET_PATH) == frozen["dataset_sha256"]
            == treatment["dataset_sha256"]
        ),
        "measurement_hash": (
            _sha256(ROOT / frozen["measurement_path"])
            == frozen["measurement_sha256"]
        ),
        "baseline_report_hash": (
            _sha256(BASELINE_PATH) == frozen["report_sha256"]
        ),
        "baseline_runtime_hash": (
            _git_file_sha256(
                frozen["commit"],
                frozen["runtime_path"],
            )
            == frozen["runtime_sha256"]
            == baseline["runtime_sha256"]
        ),
        "candidate_runtime_hash": (
            _git_file_sha256(
                candidate_commit,
                frozen["runtime_path"],
            )
            == treatment["runtime_sha256"]
        ),
        "preregistration_precedes_candidate": _is_ancestor(
            PREREGISTRATION_MERGE_COMMIT,
            candidate_commit,
        ),
        "temporary_chroma_per_case": bool(
            treatment["temporary_chroma_per_case"]
        ),
        "no_external_model_calls": (
            treatment["external_model_calls"] == 0
        ),
        "no_gold_passed_to_runtime": not treatment[
            "gold_or_expected_answer_passed_to_runtime"
        ],
        "current_runtime_reverted": all(
            _sha256(ROOT / path)
            == _git_file_sha256(PREREGISTRATION_MERGE_COMMIT, path)
            for path in RUNTIME_PATHS
        ),
    }
    gates = _evaluate_gates(config, baseline, treatment)
    artifact_integrity_valid = all(artifact_checks.values())
    candidate_gates_passed = all(
        item["passed"] for item in gates.values()
    )
    if not artifact_integrity_valid:
        decision = "INVALID"
    elif candidate_gates_passed:
        decision = "KEEP"
    else:
        decision = "DROP"

    dataset_by_id = {
        case["case_id"]: case for case in dataset["cases"]
    }
    failed_positive_cases = []
    for row in treatment["cases"]:
        if row["split"] != "positive" or row["target_source_hit"]:
            continue
        case = dataset_by_id[row["case_id"]]
        failed_positive_cases.append(
            {
                "case_id": row["case_id"],
                "language": row["language"],
                "question": case["question"],
                "required_source": case["target_user_utterance"],
                "selected_source_id": (
                    row["source_evidence_ids"][0]
                    if row["source_evidence_ids"]
                    else None
                ),
                "selected_source_text": (
                    row["source_evidence_user_texts"][0]
                    if row["source_evidence_user_texts"]
                    else None
                ),
            }
        )
    return {
        "experiment_id": config["experiment_id"],
        "decision": decision,
        "artifact_integrity_valid": artifact_integrity_valid,
        "candidate_gates_passed": candidate_gates_passed,
        "artifact_checks": artifact_checks,
        "gates": gates,
        "baseline": baseline,
        "treatment": treatment,
        "failed_positive_cases": failed_positive_cases,
        "candidate_runtime_hashes": {
            path: _git_file_sha256(candidate_commit, path)
            for path in RUNTIME_PATHS
        },
        "current_runtime_hashes": {
            path: _sha256(ROOT / path) for path in RUNTIME_PATHS
        },
    }


def _render_markdown(result):
    baseline = result["baseline"]["summary"]
    treatment = result["treatment"]["summary"]
    lines = [
        "# 合併記憶來源指標實驗 V1",
        "",
        "**最終判定：DROP（候選未上線，正式 runtime 已還原）**",
        "",
        "## 測試問題",
        "",
        "濃縮記憶已保留原始對話 ID，但一般工作記憶不會沿著 ID "
        "找回被近期同主題訊息遮住的細節。本實驗只測試："
        "在濃縮記憶已被選中的前提下，是否能安全附上一條正確原始對話。",
        "",
        "模型、Prompt、top-5 記憶排序與回答生成皆未改變；"
        "每案使用臨時資料庫，沒有外部模型或付費 API。",
        "",
        "## 凍結結果",
        "",
        "| 指標 | 修改前 | 候選方法 | 成功門檻 | 判定 |",
        "|---|---:|---:|---:|---|",
        (
            "| 找到正確原始對話 | "
            f"{baseline['positive_target_source_hits']}/6 | "
            f"{treatment['positive_target_source_hits']}/6 | "
            "至少 5/6 | 失敗 |"
        ),
        (
            "| 原文進入工作記憶摘要 | "
            f"{baseline['positive_summary_exact_user_text_hits']}/6 | "
            f"{treatment['positive_summary_exact_user_text_hits']}/6 | "
            "至少 5/6 | 失敗 |"
        ),
        (
            "| 注入錯誤來源 | "
            f"{baseline['wrong_source_injections']} | "
            f"{treatment['wrong_source_injections']} | "
            "必須 0 | 失敗 |"
        ),
        (
            "| 無效指標被啟動 | "
            f"{baseline['integrity_pointer_activations']} | "
            f"{treatment['integrity_pointer_activations']} | "
            "必須 0 | 通過 |"
        ),
        (
            "| 無關記憶被啟動 | "
            f"{baseline['unrelated_pointer_activations']} | "
            f"{treatment['unrelated_pointer_activations']} | "
            "必須 0 | 通過 |"
        ),
        (
            "| top-5 排序保持不變 | "
            f"{baseline['top_level_selection_unchanged_count']}/12 | "
            f"{treatment['top_level_selection_unchanged_count']}/12 | "
            "12/12 | 通過 |"
        ),
        "",
        "## 失敗案例",
        "",
    ]
    for case in result["failed_positive_cases"]:
        lines.extend(
            [
                f"### `{case['case_id']}`",
                "",
                f"- 問題：{case['question']}",
                f"- 應找回：{case['required_source']}",
                f"- 實際選到：{case['selected_source_text']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 原因與決策",
            "",
            "兩個錯誤來源都與問題主題高度相似，也比真正來源更新，"
            "但內容明確表示「沒有提供數值」。這證明現有排序能衡量"
            "主題相關性，卻不能可靠衡量一段記憶是否真的包含回答所需證據。",
            "",
            "因此不加入針對時間、通勤或特定句型的補丁，也不降低門檻。"
            "候選程式已還原；後續若再研究，必須用全新資料預先測試"
            "通用的證據資訊量與確定性，而不是在本資料上追分。",
            "",
            "## 證據邊界",
            "",
            "本實驗只證明：來源 ID 完整性檢查有效，且簡單指標追溯"
            "能找回 4/6 個正確來源，但可靠度不足。它不證明回答品質、"
            "真實對話、長期記憶或人類相似度獲得改善。",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        _render_markdown(result),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "decision": result["decision"],
                "artifact_integrity_valid": result[
                    "artifact_integrity_valid"
                ],
                "failed_candidate_gates": [
                    key
                    for key, item in result["gates"].items()
                    if not item["passed"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(
        0 if result["artifact_integrity_valid"] else 1
    )


if __name__ == "__main__":
    main()
