#!/usr/bin/env python3
"""Decide whether an on-policy RightBrain adapter merits runtime holdout."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_preference_likelihood_gate_v21 import (
    MAX_PREFERRED_LIKELIHOOD_DECREASE_RATE,
    preferred_likelihood_diagnostic,
)
from project_paths import (
    RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_MD_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V22_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
RUNTIME_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"


def evaluate_candidate(label, training_report):
    initial = training_report["initial_eval_preference"]
    train = training_report["final_train_preference"]
    evaluation = training_report["final_eval_preference"]
    preferred = preferred_likelihood_diagnostic(training_report)
    expected_updates = math.ceil(
        training_report["target_pair_steps"] / training_report["grad_accum"]
    )
    evidence_complete = preferred["pair_count"] == training_report["eval_pair_count"]
    gates = {
        "train_eval_source_overlap_is_zero": training_report["source_overlap_count"] == 0,
        "all_optimizer_updates_completed": training_report["optimizer_updates"] == expected_updates,
        "nonfinite_training_events_are_zero": training_report["nonfinite_skips"] == 0,
        "train_chosen_preference_rate_at_least_75pct": train["chosen_preference_rate"] >= 0.75,
        "unseen_chosen_preference_rate_at_least_75pct": evaluation["chosen_preference_rate"] >= 0.75,
        "unseen_mean_margin_improved": (
            evaluation["mean_raw_preference_margin"] > initial["mean_raw_preference_margin"]
        ),
        "unseen_target_margin_rate_at_least_50pct": evaluation["target_margin_rate"] >= 0.5,
        "preferred_likelihood_evidence_is_complete": evidence_complete,
        "unseen_mean_preferred_log_prob_non_decreasing": (
            evidence_complete and preferred["mean_chosen_average_log_prob_delta"] >= 0
        ),
        "unseen_preferred_likelihood_decrease_rate_at_most_50pct": (
            evidence_complete
            and preferred["preferred_likelihood_decrease_rate"]
            <= MAX_PREFERRED_LIKELIHOOD_DECREASE_RATE
        ),
    }
    return {
        "label": label,
        "adapter_ref": training_report["output_adapter_ref"],
        "epochs": training_report["epochs"],
        "learning_rate": training_report["learning_rate"],
        "optimizer_updates": training_report["optimizer_updates"],
        "expected_optimizer_updates": expected_updates,
        "nonfinite_skips": training_report["nonfinite_skips"],
        "max_observed_gradient_norm": training_report["max_observed_gradient_norm"],
        "initial_eval_chosen_preference_rate": initial["chosen_preference_rate"],
        "final_train_chosen_preference_rate": train["chosen_preference_rate"],
        "final_eval_chosen_preference_rate": evaluation["chosen_preference_rate"],
        "initial_eval_target_margin_rate": initial["target_margin_rate"],
        "final_eval_target_margin_rate": evaluation["target_margin_rate"],
        "initial_eval_mean_raw_margin": initial["mean_raw_preference_margin"],
        "final_eval_mean_raw_margin": evaluation["mean_raw_preference_margin"],
        "eval_mean_raw_margin_delta": (
            evaluation["mean_raw_preference_margin"] - initial["mean_raw_preference_margin"]
        ),
        "preferred_likelihood": preferred,
        "gates": gates,
        "authorize_actual_model_holdout": all(gates.values()),
    }


def build_report(candidates):
    rows = [evaluate_candidate(label, report) for label, report in candidates]
    authorized = [row for row in rows if row["authorize_actual_model_holdout"]]
    if not authorized:
        decision_zh = "沒有候選通過未見偏好學習 gate；不執行昂貴 runtime holdout，正式右腦維持 V10。"
    elif len(authorized) == 1:
        decision_zh = "有一個候選通過所有前置 gate，可進入 V10 對照的雙 seed runtime holdout。"
    else:
        decision_zh = "多個候選通過前置 gate；必須先用預先定義的開發指標選出一個，不能同時偷看 promotion holdout。"
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_on_policy_preference_training_decision",
        "runtime_adapter_before": RUNTIME_ADAPTER,
        "runtime_adapter_after": RUNTIME_ADAPTER,
        "candidate_count": len(rows),
        "candidates": rows,
        "authorized_candidate_count": len(authorized),
        "selected_adapter": authorized[0]["adapter_ref"] if len(authorized) == 1 else None,
        "run_actual_model_holdout": len(authorized) == 1,
        "decision_zh": decision_zh,
        "diagnosis_zh": (
            "on-policy 資料確實揭露 V10 的自然錯誤，但目前 pair-level SimPO 沒有把未見偏好率推高；"
            "增加 epoch 只放大梯度，沒有改善正確排序。下一輪應平衡每個 source prompt 的總梯度，"
            "避免同一 prompt 因 rejected 候選較多而被重複加權。"
        ),
        "research_boundary": (
            "Automatic strict-contract labels measure semantic and surface contract realization, not broad human "
            "preference. Failing this gate blocks promotion; passing it would still require independent multi-seed "
            "generation and the untouched promotion holdout."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# RightBrain On-Policy Preference 訓練決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 候選 | epoch | updates | unseen preference | target margin | mean margin delta | preferred log-prob delta | gradient max | holdout |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["candidates"]:
        preferred = row["preferred_likelihood"]
        lines.append(
            f"| {row['label']} | {row['epochs']:.1f} | {row['optimizer_updates']} | "
            f"{row['initial_eval_chosen_preference_rate']:.0%} → {row['final_eval_chosen_preference_rate']:.0%} | "
            f"{row['final_eval_target_margin_rate']:.0%} | {row['eval_mean_raw_margin_delta']:+.6f} | "
            f"{preferred['mean_chosen_average_log_prob_delta']:+.6f} | "
            f"{row['max_observed_gradient_norm']:.3f} | "
            f"{'RUN' if row['authorize_actual_model_holdout'] else 'BLOCK'} |"
        )
    lines.extend(
        [
            "",
            "## 診斷",
            "",
            report["diagnosis_zh"],
            "",
            "## Gate 明細",
            "",
        ]
    )
    for row in report["candidates"]:
        lines.extend([f"### {row['label']}", "", "| 條件 | 結果 |", "|---|---|"])
        for name, passed in row["gates"].items():
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
        lines.append("")
    lines.extend(["研究邊界：" + report["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v21-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v22-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V22_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_MD_PATH)
    args = parser.parse_args()
    report = build_report(
        [
            ("V21 1-epoch", json.loads(Path(args.v21_report).read_text(encoding="utf-8"))),
            ("V22 3-epoch", json.loads(Path(args.v22_report).read_text(encoding="utf-8"))),
        ]
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "authorized_candidate_count": report["authorized_candidate_count"],
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
