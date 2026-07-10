#!/usr/bin/env python3
"""Gate V19 SimPO before actual-model holdout generation."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_DECISION_REPORT_MD_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def build_report(training_report):
    initial = training_report["initial_eval_preference"]
    train = training_report["final_train_preference"]
    evaluation = training_report["final_eval_preference"]
    expected_updates = math.ceil(training_report["target_pair_steps"] / training_report["grad_accum"])
    gates = {
        "train_eval_source_overlap_is_zero": training_report["source_overlap_count"] == 0,
        "all_optimizer_updates_completed": training_report["optimizer_updates"] == expected_updates,
        "nonfinite_training_events_are_zero": training_report["nonfinite_skips"] == 0,
        "train_chosen_preference_rate_at_least_75pct": train["chosen_preference_rate"] >= 0.75,
        "unseen_eval_chosen_preference_rate_at_least_75pct": (
            evaluation["chosen_preference_rate"] >= 0.75
        ),
        "unseen_eval_mean_margin_improved": (
            evaluation["mean_raw_preference_margin"] > initial["mean_raw_preference_margin"]
        ),
        "unseen_eval_target_margin_rate_at_least_50pct": evaluation["target_margin_rate"] >= 0.5,
    }
    authorize_holdout = all(gates.values())
    margin_delta = (
        evaluation["mean_raw_preference_margin"] - initial["mean_raw_preference_margin"]
    )
    saturated_before_training = initial["chosen_preference_rate"] == 1.0
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_semantic_preference_v19_pre_holdout_gate",
        "adapter_ref": training_report["output_adapter_ref"],
        "gates": gates,
        "authorize_actual_model_holdout": authorize_holdout,
        "result": {
            "optimizer_updates": training_report["optimizer_updates"],
            "expected_optimizer_updates": expected_updates,
            "nonfinite_skips": training_report["nonfinite_skips"],
            "max_observed_gradient_norm": training_report["max_observed_gradient_norm"],
            "initial_eval_chosen_preference_rate": initial["chosen_preference_rate"],
            "final_eval_chosen_preference_rate": evaluation["chosen_preference_rate"],
            "initial_eval_mean_raw_margin": initial["mean_raw_preference_margin"],
            "final_eval_mean_raw_margin": evaluation["mean_raw_preference_margin"],
            "eval_mean_raw_margin_delta": margin_delta,
            "final_eval_target_margin_rate": evaluation["target_margin_rate"],
            "final_train_chosen_preference_rate": train["chosen_preference_rate"],
        },
        "decision_zh": (
            "允許 V19 進入 V10 對照的雙 seed 真實模型 holdout。"
            if authorize_holdout
            else "不允許 V19 進入真實模型 holdout：SimPO 未形成穩定的未見家族偏好改善。"
        ),
        "diagnosis": {
            "unseen_eval_saturated_before_training": saturated_before_training,
            "interpretation_zh": (
                "刪句 rejected 對 V10 已經太容易：訓練前 unseen chosen preference 就是 100%，"
                "訓練後平均 margin 還略降，因此不能把穩定訓練誤報成泛化提升。"
                if saturated_before_training
                else "unseen family 尚有辨識空間，但本輪 margin 未改善。"
            ),
            "next_dataset_change": (
                "建立長度相近、文法自然、只替換一個必要語意槽位的 hard negatives，"
                "避免用刪句產生可由長度直接識別的 rejected。"
            ),
        },
        "research_boundary": (
            "這是訓練穩定性與未見 synthetic preference family 的前置 gate；即使通過也不代表 adapter 可上線。"
        ),
    }


def write_markdown(report, path):
    result = report["result"]
    lines = [
        "# RightBrain V19 SimPO 訓練決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| optimizer updates | {result['optimizer_updates']}/{result['expected_optimizer_updates']} |",
        f"| non-finite skips | {result['nonfinite_skips']} |",
        f"| max gradient norm | {result['max_observed_gradient_norm']:.3f} |",
        f"| train chosen preference | {result['final_train_chosen_preference_rate']:.1%} |",
        f"| unseen eval chosen preference | {result['initial_eval_chosen_preference_rate']:.1%} -> {result['final_eval_chosen_preference_rate']:.1%} |",
        f"| unseen eval mean margin | {result['initial_eval_mean_raw_margin']:+.6f} -> {result['final_eval_mean_raw_margin']:+.6f} |",
        f"| unseen target margin rate | {result['final_eval_target_margin_rate']:.1%} |",
        "",
        "## 診斷",
        "",
        report["diagnosis"]["interpretation_zh"],
        "",
        f"下一資料改動：{report['diagnosis']['next_dataset_change']}",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", "## 研究邊界", "", report["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-report", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_DECISION_REPORT_MD_PATH)
    args = parser.parse_args()
    report = build_report(json.loads(Path(args.training_report).read_text(encoding="utf-8")))
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({"gates": report["gates"], "authorize_actual_model_holdout": report["authorize_actual_model_holdout"]}, ensure_ascii=False, indent=2))
    return 0 if report["authorize_actual_model_holdout"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
