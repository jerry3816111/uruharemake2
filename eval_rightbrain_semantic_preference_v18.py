#!/usr/bin/env python3
"""Gate the v18 DPO training run before expensive actual-model holdouts."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DECISION_REPORT_MD_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_JSON_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def build_report(dataset_report, training_report):
    train = training_report["final_train_preference"]
    evaluation = training_report["final_eval_preference"]
    gates = {
        "dataset_holdout_overlap_is_zero": not dataset_report["data_boundary"]["diagnostic_only"],
        "train_eval_source_overlap_is_zero": training_report["source_overlap_count"] == 0,
        "all_optimizer_updates_completed": training_report["optimizer_updates"]
        == training_report["target_pair_steps"] // training_report["grad_accum"],
        "nonfinite_training_events_are_zero": training_report["nonfinite_skips"] == 0,
        "train_mean_reward_margin_is_positive": train["mean_reward_margin"] > 0,
        "unseen_eval_positive_margin_rate_at_least_75pct": (
            evaluation["positive_reward_margin_rate"] >= 0.75
        ),
        "unseen_eval_mean_reward_margin_is_positive": evaluation["mean_reward_margin"] > 0,
    }
    authorize_holdout = all(gates.values())
    length_profile = dataset_report["length_profile_chars"]
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_semantic_preference_v18_pre_holdout_gate",
        "adapter_ref": training_report["output_adapter_ref"],
        "gates": gates,
        "authorize_actual_model_holdout": authorize_holdout,
        "training_result": {
            "optimizer_updates": training_report["optimizer_updates"],
            "expected_optimizer_updates": training_report["target_pair_steps"]
            // training_report["grad_accum"],
            "nonfinite_skips": training_report["nonfinite_skips"],
            "max_observed_gradient_norm": training_report["max_observed_gradient_norm"],
            "train_positive_margin_rate": train["positive_reward_margin_rate"],
            "train_mean_reward_margin": train["mean_reward_margin"],
            "eval_positive_margin_rate": evaluation["positive_reward_margin_rate"],
            "eval_mean_reward_margin": evaluation["mean_reward_margin"],
        },
        "length_confound": {
            **length_profile,
            "interpretation": (
                "Rejected responses are constructed by deleting a semantic clause, so chosen responses are "
                "systematically longer. Summed sequence log-prob DPO therefore entangles completeness with length."
            ),
        },
        "decision_zh": (
            "允許進入真實模型 holdout。"
            if authorize_holdout
            else "不允許進入真實模型 holdout：V18 DPO 未在未見語意家族上形成穩定正偏好，且訓練出現非有限梯度。"
        ),
        "next_method": {
            "name": "length-normalized preference optimization (SimPO-style)",
            "reason": "使用 completion 平均 log-prob，分離語意完整度與回答長度，並移除 reference 重算成本。",
            "paper": "https://arxiv.org/abs/2405.14734",
        },
        "research_boundary": (
            "這個 gate 只檢查最佳化穩定性與未見偏好家族；訓練證據不足時會阻止昂貴的生成評測。"
            "即使通過，也仍須完成真實模型 holdout 才能升版。"
        ),
    }


def write_markdown(report, path):
    result = report["training_result"]
    length = report["length_confound"]
    lines = [
        "# RightBrain V18 DPO 訓練決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| optimizer updates | {result['optimizer_updates']}/{result['expected_optimizer_updates']} |",
        f"| non-finite skips | {result['nonfinite_skips']} |",
        f"| max gradient norm | {result['max_observed_gradient_norm']:.1f} |",
        f"| train positive margin | {result['train_positive_margin_rate']:.1%} |",
        f"| train mean margin | {result['train_mean_reward_margin']:+.6f} |",
        f"| unseen eval positive margin | {result['eval_positive_margin_rate']:.1%} |",
        f"| unseen eval mean margin | {result['eval_mean_reward_margin']:+.6f} |",
        "",
        "## 為什麼不繼續跑 holdout",
        "",
        f"chosen 平均 {length['chosen_mean']:.1f} 字，rejected 平均 {length['rejected_mean']:.1f} 字，差 {length['mean_delta']:.1f} 字。",
        "rejected 是刪掉一個語意子句產生，因此 summed-log-prob DPO 把回答長度與品質混在一起；本輪梯度不穩且未見家族只有一半朝正確方向。",
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
            "## 下一方法",
            "",
            f"{report['next_method']['name']}：{report['next_method']['reason']}",
            "",
            f"論文：{report['next_method']['paper']}",
            "",
            "## 研究邊界",
            "",
            report["research_boundary"],
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-report", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_JSON_PATH)
    parser.add_argument("--training-report", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DECISION_REPORT_MD_PATH)
    args = parser.parse_args()
    report = build_report(
        json.loads(Path(args.dataset_report).read_text(encoding="utf-8")),
        json.loads(Path(args.training_report).read_text(encoding="utf-8")),
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "gates": report["gates"],
                "authorize_actual_model_holdout": report["authorize_actual_model_holdout"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["authorize_actual_model_holdout"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
