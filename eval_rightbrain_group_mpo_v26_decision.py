#!/usr/bin/env python3
"""Decide whether V26 group MPO merits an untouched runtime holdout."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_GROUP_MPO_V26_DECISION_JSON_PATH,
    RIGHTBRAIN_GROUP_MPO_V26_DECISION_MD_PATH,
    RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
RUNTIME_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
MAX_REFERENCE_IDENTITY_DELTA = 5e-4
MIN_TRAIN_PAIRWISE_PREFERENCE = 0.75
MIN_EVAL_PAIRWISE_PREFERENCE = 0.75
MIN_EVAL_STRICT_SEPARATION = 0.50
MIN_EVAL_POSITIVE_TOP1 = 0.75
MIN_EVAL_POSITIVE_MASS_GAIN = 0.05
MAX_POSITIVE_LIKELIHOOD_DECREASE_RATE = 0.50


def positive_likelihood_diagnostic(initial_metrics, final_metrics):
    initial = {
        response["id"]: response["policy_average_log_prob"]
        for group in initial_metrics["groups"]
        for response in group["responses"]
        if response["label"] == "positive"
    }
    final = {
        response["id"]: response["policy_average_log_prob"]
        for group in final_metrics["groups"]
        for response in group["responses"]
        if response["label"] == "positive"
    }
    shared = sorted(set(initial) & set(final))
    deltas = [final[row_id] - initial[row_id] for row_id in shared]
    decrease_count = sum(delta < 0 for delta in deltas)
    return {
        "initial_positive_count": len(initial),
        "final_positive_count": len(final),
        "matched_positive_count": len(shared),
        "evidence_complete": len(shared) == len(initial) == len(final),
        "mean_positive_average_log_prob_delta": sum(deltas) / len(deltas),
        "positive_likelihood_decrease_count": decrease_count,
        "positive_likelihood_decrease_rate": decrease_count / len(deltas),
        "rows": [
            {
                "id": row_id,
                "initial": initial[row_id],
                "final": final[row_id],
                "delta": final[row_id] - initial[row_id],
            }
            for row_id in shared
        ],
    }


def absolute_policy_ranking(metrics):
    pair_count = correct_pairs = tie_pairs = 0
    top_count = strict_count = 0
    margins = []
    for group in metrics["groups"]:
        positives = [
            response["policy_average_log_prob"]
            for response in group["responses"]
            if response["label"] == "positive"
        ]
        negatives = [
            response["policy_average_log_prob"]
            for response in group["responses"]
            if response["label"] == "negative"
        ]
        pair_count += len(positives) * len(negatives)
        correct_pairs += sum(p > n for p in positives for n in negatives)
        tie_pairs += sum(p == n for p in positives for n in negatives)
        top_count += int(max(positives) > max(negatives))
        strict_count += int(min(positives) > max(negatives))
        margins.append(
            sum(positives) / len(positives) - sum(negatives) / len(negatives)
        )
    group_count = len(metrics["groups"])
    return {
        "pair_count": pair_count,
        "pairwise_positive_preference_rate": correct_pairs / pair_count,
        "pairwise_tie_rate": tie_pairs / pair_count,
        "positive_top1_rate": top_count / group_count,
        "strict_positive_separation_rate": strict_count / group_count,
        "mean_positive_negative_margin": sum(margins) / group_count,
    }


def build_decision(training_report):
    initial_train = training_report["initial_train_group_metrics"]
    initial_eval = training_report["initial_eval_group_metrics"]
    final_train = training_report["final_train_group_metrics"]
    final_eval = training_report["final_eval_group_metrics"]
    likelihood = positive_likelihood_diagnostic(initial_eval, final_eval)
    initial_train_absolute = absolute_policy_ranking(initial_train)
    final_train_absolute = absolute_policy_ranking(final_train)
    initial_eval_absolute = absolute_policy_ranking(initial_eval)
    final_eval_absolute = absolute_policy_ranking(final_eval)
    positive_mass_gain = (
        final_eval["mean_positive_probability_mass"]
        - initial_eval["mean_positive_probability_mass"]
    )
    mean_margin_gain = (
        final_eval["mean_positive_negative_margin"]
        - initial_eval["mean_positive_negative_margin"]
    )
    reference_delta = max(
        initial_train["max_abs_policy_reference_log_prob_delta"],
        initial_eval["max_abs_policy_reference_log_prob_delta"],
    )
    gates = {
        "train_eval_source_overlap_is_zero": training_report["source_overlap_count"] == 0,
        "all_group_updates_completed": training_report["optimizer_updates"]
        == training_report["target_group_steps"],
        "nonfinite_training_events_are_zero": training_report["nonfinite_skips"] == 0,
        "frozen_reference_identity_delta_at_most_5e_4": reference_delta
        <= MAX_REFERENCE_IDENTITY_DELTA,
        "train_pairwise_positive_preference_at_least_75pct": final_train[
            "pairwise_positive_preference_rate"
        ]
        >= MIN_TRAIN_PAIRWISE_PREFERENCE,
        "unseen_pairwise_positive_preference_at_least_75pct": final_eval[
            "pairwise_positive_preference_rate"
        ]
        >= MIN_EVAL_PAIRWISE_PREFERENCE,
        "unseen_strict_group_separation_at_least_50pct": final_eval[
            "strict_positive_separation_rate"
        ]
        >= MIN_EVAL_STRICT_SEPARATION,
        "unseen_positive_top1_at_least_75pct": final_eval["positive_top1_rate"]
        >= MIN_EVAL_POSITIVE_TOP1,
        "unseen_positive_mass_gain_at_least_5pp": positive_mass_gain
        >= MIN_EVAL_POSITIVE_MASS_GAIN,
        "unseen_mean_group_margin_improved": mean_margin_gain > 0,
        "train_absolute_pairwise_preference_improved": final_train_absolute[
            "pairwise_positive_preference_rate"
        ]
        > initial_train_absolute["pairwise_positive_preference_rate"],
        "unseen_absolute_pairwise_preference_improved": final_eval_absolute[
            "pairwise_positive_preference_rate"
        ]
        > initial_eval_absolute["pairwise_positive_preference_rate"],
        "unseen_absolute_mean_margin_improved": final_eval_absolute[
            "mean_positive_negative_margin"
        ]
        > initial_eval_absolute["mean_positive_negative_margin"],
        "positive_likelihood_evidence_is_complete": likelihood["evidence_complete"],
        "unseen_mean_positive_log_prob_non_decreasing": likelihood[
            "mean_positive_average_log_prob_delta"
        ]
        >= 0,
        "unseen_positive_likelihood_decrease_rate_at_most_50pct": likelihood[
            "positive_likelihood_decrease_rate"
        ]
        <= MAX_POSITIVE_LIKELIHOOD_DECREASE_RATE,
    }
    authorized = all(gates.values())
    absolute_eval_delta = (
        final_eval_absolute["pairwise_positive_preference_rate"]
        - initial_eval_absolute["pairwise_positive_preference_rate"]
    )
    diagnosis_zh = (
        f"相對 reference 的未見排序達 {final_eval['pairwise_positive_preference_rate']:.1%}，"
        f"但模型絕對排序只由 {initial_eval_absolute['pairwise_positive_preference_rate']:.1%} "
        f"變為 {final_eval_absolute['pairwise_positive_preference_rate']:.1%} "
        f"({absolute_eval_delta:+.1%})，正集合機率僅增加 {positive_mass_gain:+.2%}。"
        "這證明更新方向多數正確，但幅度不足以翻轉原本錯排，不能把相對分數當成實際能力提升。"
    )
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_group_mpo_v26_training_decision",
        "runtime_adapter_before": RUNTIME_ADAPTER,
        "runtime_adapter_after": RUNTIME_ADAPTER,
        "candidate_adapter": training_report["output_adapter_ref"],
        "run_actual_model_holdout": authorized,
        "selected_candidate_for_holdout": (
            training_report["output_adapter_ref"] if authorized else None
        ),
        "gates": gates,
        "metrics": {
            "reference_identity_max_abs_delta": reference_delta,
            "frozen_v10_absolute_probe_pairwise_preference": training_report.get(
                "frozen_v10_absolute_eval_pairwise_preference_rate"
            ),
            "frozen_v10_absolute_probe_misranked_pair_count": training_report.get(
                "frozen_v10_absolute_eval_misranked_pair_count"
            ),
            "initial_train_pairwise_preference": initial_train[
                "pairwise_positive_preference_rate"
            ],
            "final_train_pairwise_preference": final_train[
                "pairwise_positive_preference_rate"
            ],
            "initial_eval_pairwise_preference": initial_eval[
                "pairwise_positive_preference_rate"
            ],
            "final_eval_pairwise_preference": final_eval[
                "pairwise_positive_preference_rate"
            ],
            "final_eval_strict_separation": final_eval[
                "strict_positive_separation_rate"
            ],
            "final_eval_positive_top1": final_eval["positive_top1_rate"],
            "initial_eval_positive_mass": initial_eval[
                "mean_positive_probability_mass"
            ],
            "final_eval_positive_mass": final_eval[
                "mean_positive_probability_mass"
            ],
            "eval_positive_mass_gain": positive_mass_gain,
            "eval_mean_margin_gain": mean_margin_gain,
            "initial_train_absolute_policy_ranking": initial_train_absolute,
            "final_train_absolute_policy_ranking": final_train_absolute,
            "initial_eval_absolute_policy_ranking": initial_eval_absolute,
            "final_eval_absolute_policy_ranking": final_eval_absolute,
            "positive_likelihood": likelihood,
        },
        "decision_zh": (
            "V26 通過群組排序、正回答機率與數值穩定 gate，可進入未觸碰的雙 seed runtime holdout；尚未授權上線。"
            if authorized
            else "V26 未通過群組訓練 gate，不執行 runtime holdout，正式右腦維持 V10。"
        ),
        "diagnosis_zh": diagnosis_zh,
        "next_experiment_zh": (
            "下一個可歸因實驗只把 learning rate 從 1e-7 提高到 3e-7；資料、MPO、NLL、seed、epoch "
            "與全部 gate 固定。V26 的 0 次非有限事件支持測試較大更新，但不保證 V27 會通過。"
        ),
        "research_boundary": (
            "Passing these likelihood gates would authorize only actual-generation comparison against V10. "
            "Relative policy/reference ranking is reported separately from absolute policy ranking. No matched "
            "all-pairs training control has been run yet, so this experiment cannot isolate the MPO objective as "
            "the cause of any gain. It does not by itself prove more human-like dialogue or authorize promotion."
        ),
    }


def write_markdown(report, path):
    metrics = report["metrics"]
    lines = [
        "# RightBrain V26 Group MPO 決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        report["diagnosis_zh"],
        "",
        "| 指標 | 訓練前 | 訓練後 |",
        "|---|---:|---:|",
        f"| train 相對 reference 排序 | {metrics['initial_train_pairwise_preference']:.1%} | {metrics['final_train_pairwise_preference']:.1%} |",
        f"| unseen 相對 reference 排序 | {metrics['initial_eval_pairwise_preference']:.1%} | {metrics['final_eval_pairwise_preference']:.1%} |",
        f"| train 模型絕對排序 | {metrics['initial_train_absolute_policy_ranking']['pairwise_positive_preference_rate']:.1%} | {metrics['final_train_absolute_policy_ranking']['pairwise_positive_preference_rate']:.1%} |",
        f"| unseen 模型絕對排序 | {metrics['initial_eval_absolute_policy_ranking']['pairwise_positive_preference_rate']:.1%} | {metrics['final_eval_absolute_policy_ranking']['pairwise_positive_preference_rate']:.1%} |",
        f"| unseen 正集合機率質量 | {metrics['initial_eval_positive_mass']:.1%} | {metrics['final_eval_positive_mass']:.1%} |",
        f"| unseen 全正回答高於全負回答 | - | {metrics['final_eval_strict_separation']:.1%} |",
        f"| unseen 組內最高為正回答 | - | {metrics['final_eval_positive_top1']:.1%} |",
        "",
        f"凍結 V10 的絕對機率 probe 勝率為 {metrics['frozen_v10_absolute_probe_pairwise_preference']:.1%}。"
        "相對分數衡量每個回答相對 V10 移動的方向；模型絕對排序才表示最後模型是否真的翻轉原本錯排。",
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
            "下一個單一變因：" + report["next_experiment_zh"],
            "",
            "研究邊界：" + report["research_boundary"],
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-report", default=RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_GROUP_MPO_V26_DECISION_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_GROUP_MPO_V26_DECISION_MD_PATH)
    args = parser.parse_args()
    training_report = json.loads(Path(args.training_report).read_text(encoding="utf-8"))
    report = build_decision(training_report)
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "run_actual_model_holdout": report["run_actual_model_holdout"],
                "decision_zh": report["decision_zh"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
