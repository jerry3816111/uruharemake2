#!/usr/bin/env python3
"""Compare the V26 and V27 single-variable Group-MPO experiments."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_GROUP_MPO_V26_DECISION_JSON_PATH,
    RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_COMPARISON_JSON_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_COMPARISON_MD_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_DECISION_JSON_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
CONTROLLED_FIELDS = (
    "method",
    "base_model",
    "init_adapter_ref",
    "init_adapter_model_sha256",
    "dataset_ref",
    "dataset_sha256",
    "probe_ref",
    "probe_sha256",
    "max_length",
    "epochs",
    "beta",
    "positive_nll_weight",
    "weight_decay",
    "optimizer_eps",
    "max_gradient_norm",
    "seed",
    "train_source_ids",
    "eval_source_ids",
    "source_overlap_count",
)


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _summary(training, decision):
    metrics = decision["metrics"]
    initial_absolute = metrics["initial_eval_absolute_policy_ranking"]
    final_absolute = metrics["final_eval_absolute_policy_ranking"]
    likelihood = metrics["positive_likelihood"]
    return {
        "learning_rate": training["learning_rate"],
        "epochs": training["epochs"],
        "optimizer_updates": training["optimizer_updates"],
        "nonfinite_skips": training["nonfinite_skips"],
        "max_observed_gradient_norm": training["max_observed_gradient_norm"],
        "final_train_relative_pairwise_preference": metrics[
            "final_train_pairwise_preference"
        ],
        "final_eval_relative_pairwise_preference": metrics[
            "final_eval_pairwise_preference"
        ],
        "initial_eval_absolute_pairwise_preference": initial_absolute[
            "pairwise_positive_preference_rate"
        ],
        "final_eval_absolute_pairwise_preference": final_absolute[
            "pairwise_positive_preference_rate"
        ],
        "eval_absolute_pairwise_delta": final_absolute[
            "pairwise_positive_preference_rate"
        ]
        - initial_absolute["pairwise_positive_preference_rate"],
        "eval_absolute_mean_margin_delta": final_absolute[
            "mean_positive_negative_margin"
        ]
        - initial_absolute["mean_positive_negative_margin"],
        "eval_positive_mass_gain": metrics["eval_positive_mass_gain"],
        "eval_mean_positive_log_prob_delta": likelihood[
            "mean_positive_average_log_prob_delta"
        ],
        "passed_gate_count": sum(decision["gates"].values()),
        "gate_count": len(decision["gates"]),
        "authorized_runtime_holdout": decision["run_actual_model_holdout"],
    }


def build_comparison(v26_training, v26_decision, v27_training, v27_decision):
    mismatches = {
        field: {"v26": v26_training.get(field), "v27": v27_training.get(field)}
        for field in CONTROLLED_FIELDS
        if v26_training.get(field) != v27_training.get(field)
    }
    v26 = _summary(v26_training, v26_decision)
    v27 = _summary(v27_training, v27_decision)
    only_learning_rate_changed = (
        not mismatches
        and v26["learning_rate"] == 1e-7
        and v27["learning_rate"] == 3e-7
    )
    v27_better_absolute = (
        v27["final_eval_absolute_pairwise_preference"]
        > v26["final_eval_absolute_pairwise_preference"]
    )
    reject = (
        only_learning_rate_changed
        and not v27_better_absolute
        and not v27["authorized_runtime_holdout"]
    )
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_group_mpo_v27_single_variable_comparison",
        "independent_variable": "learning_rate",
        "v26": v26,
        "v27": v27,
        "controlled_fields": list(CONTROLLED_FIELDS),
        "controlled_field_mismatches": mismatches,
        "only_learning_rate_changed": only_learning_rate_changed,
        "decision": "reject_learning_rate_increase" if reject else "inconclusive",
        "runtime_adapter_before": v27_decision["runtime_adapter_before"],
        "runtime_adapter_after": v27_decision["runtime_adapter_after"],
        "run_actual_model_holdout": False,
        "conclusion_zh": (
            "在資料、V10 起點、MPO、NLL、seed 與 epoch 全部固定時，"
            "learning rate 由 1e-7 提高到 3e-7 沒有提高未見回答的絕對排序，"
            "因此拒絕 V27，正式右腦維持 V10。"
            if reject
            else "單一變因條件或結果不完整，無法做出學習率結論。"
        ),
        "next_evidence_step_zh": (
            "停止只增加學習率或 epoch。下一步先把現有人類盲評轉成可追溯的"
            "多維偏好診斷，檢查現行自動 contract 標籤是否真的對應自然、完整、"
            "有人格的人類回答；資料 gate 通過前不再訓練。"
        ),
        "research_boundary": (
            "This paired run rejects this V27 candidate under one fixed seed and frozen dataset. "
            "It does not prove that every larger learning rate is universally harmful. The current labels "
            "measure strict contract realization rather than broad human preference."
        ),
    }


def write_markdown(report, path):
    v26 = report["v26"]
    v27 = report["v27"]
    lines = [
        "# RightBrain V27 單一變因比較",
        "",
        "## 結論",
        "",
        report["conclusion_zh"],
        "",
        "| 指標 | V26 (1e-7) | V27 (3e-7) |",
        "|---|---:|---:|",
        f"| 訓練更新 / 非有限跳過 | {v26['optimizer_updates']} / {v26['nonfinite_skips']} | {v27['optimizer_updates']} / {v27['nonfinite_skips']} |",
        f"| 未見相對偏好 | {v26['final_eval_relative_pairwise_preference']:.2%} | {v27['final_eval_relative_pairwise_preference']:.2%} |",
        f"| 未見絕對偏好 | {v26['final_eval_absolute_pairwise_preference']:.2%} | {v27['final_eval_absolute_pairwise_preference']:.2%} |",
        f"| 絕對偏好變化 | {v26['eval_absolute_pairwise_delta']:+.2%} | {v27['eval_absolute_pairwise_delta']:+.2%} |",
        f"| 正回答集合機率增加 | {v26['eval_positive_mass_gain']:+.2%} | {v27['eval_positive_mass_gain']:+.2%} |",
        f"| 通過 gate | {v26['passed_gate_count']}/{v26['gate_count']} | {v27['passed_gate_count']}/{v27['gate_count']} |",
        "",
        f"控制變因一致：{'PASS' if report['only_learning_rate_changed'] else 'FAIL'}",
        "",
        "## 下一個有意義的證據步驟",
        "",
        report["next_evidence_step_zh"],
        "",
        "研究邊界：" + report["research_boundary"],
        "",
    ]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v26-training", default=RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v26-decision", default=RIGHTBRAIN_GROUP_MPO_V26_DECISION_JSON_PATH)
    parser.add_argument("--v27-training", default=RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v27-decision", default=RIGHTBRAIN_GROUP_MPO_V27_DECISION_JSON_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_GROUP_MPO_V27_COMPARISON_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_GROUP_MPO_V27_COMPARISON_MD_PATH)
    args = parser.parse_args()
    report = build_comparison(
        _load(args.v26_training),
        _load(args.v26_decision),
        _load(args.v27_training),
        _load(args.v27_decision),
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({
        "decision": report["decision"],
        "only_learning_rate_changed": report["only_learning_rate_changed"],
        "run_actual_model_holdout": report["run_actual_model_holdout"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["decision"] == "reject_learning_rate_increase" else 1


if __name__ == "__main__":
    raise SystemExit(main())
