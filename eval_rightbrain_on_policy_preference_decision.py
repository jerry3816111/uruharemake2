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
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V23_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V24_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V25_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
RUNTIME_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
FACTORIAL_CELLS = (
    "pairwise",
    "prompt_balanced",
    "pairwise_chosen_nll",
    "prompt_balanced_chosen_nll",
)
FACTORIAL_COMPARISONS = (
    ("prompt_balance_without_nll", "prompt balance", "pairwise", "prompt_balanced"),
    ("chosen_nll_without_balance", "chosen NLL", "pairwise", "pairwise_chosen_nll"),
    (
        "chosen_nll_with_balance",
        "chosen NLL",
        "prompt_balanced",
        "prompt_balanced_chosen_nll",
    ),
    (
        "prompt_balance_with_nll",
        "prompt balance",
        "pairwise_chosen_nll",
        "prompt_balanced_chosen_nll",
    ),
)


def _factor_cell(prompt_balance_enabled, chosen_nll_weight):
    if prompt_balance_enabled and chosen_nll_weight > 0:
        return "prompt_balanced_chosen_nll"
    if prompt_balance_enabled:
        return "prompt_balanced"
    if chosen_nll_weight > 0:
        return "pairwise_chosen_nll"
    return "pairwise"


def _training_controls(training_report):
    return {
        "base_model": training_report.get("base_model"),
        "dataset_sha256": training_report.get("dataset_sha256"),
        "init_adapter_ref": training_report.get("init_adapter_ref"),
        "epochs": training_report.get("epochs"),
        "learning_rate": training_report.get("learning_rate"),
        "beta": training_report.get("beta"),
        "gamma_beta_ratio": training_report.get("gamma_beta_ratio"),
        "grad_accum": training_report.get("grad_accum"),
        "seed": training_report.get("seed"),
        "train_source_ids": training_report.get("train_source_ids"),
        "eval_source_ids": training_report.get("eval_source_ids"),
    }


def evaluate_candidate(label, training_report):
    initial = training_report["initial_eval_preference"]
    train = training_report["final_train_preference"]
    evaluation = training_report["final_eval_preference"]
    preferred = preferred_likelihood_diagnostic(training_report)
    expected_updates = math.ceil(
        training_report["target_pair_steps"] / training_report["grad_accum"]
    )
    evidence_complete = preferred["pair_count"] == training_report["eval_pair_count"]
    prompt_balance_enabled = bool(
        (training_report.get("prompt_balance") or {}).get("enabled", False)
    )
    chosen_nll_weight = float(training_report.get("chosen_nll_weight") or 0.0)
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
        "method": training_report.get("method"),
        "prompt_balance_enabled": prompt_balance_enabled,
        "chosen_nll_weight": chosen_nll_weight,
        "factor_cell": _factor_cell(prompt_balance_enabled, chosen_nll_weight),
        "training_controls": _training_controls(training_report),
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
        "numerically_complete": (
            gates["all_optimizer_updates_completed"]
            and gates["nonfinite_training_events_are_zero"]
        ),
        "authorize_actual_model_holdout": all(gates.values()),
    }


def build_factorial_analysis(rows):
    cohorts = {}
    for row in rows:
        signature = json.dumps(
            row["training_controls"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        cohorts.setdefault(signature, []).append(row)
    cohort_rows = max(
        cohorts.values(),
        key=lambda group: (len({row["factor_cell"] for row in group}), len(group)),
    )
    cells = {row["factor_cell"]: row for row in cohort_rows}
    missing_cells = [cell for cell in FACTORIAL_CELLS if cell not in cells]
    comparisons = []
    for comparison_id, factor, baseline_cell, treatment_cell in FACTORIAL_COMPARISONS:
        if baseline_cell not in cells or treatment_cell not in cells:
            continue
        baseline = cells[baseline_cell]
        treatment = cells[treatment_cell]
        execution_clean = baseline["numerically_complete"] and treatment["numerically_complete"]
        comparisons.append(
            {
                "id": comparison_id,
                "changed_factor": factor,
                "baseline": baseline["label"],
                "treatment": treatment["label"],
                "valid_single_factor_comparison": execution_clean,
                "exclusion_reason_zh": (
                    None
                    if execution_clean
                    else "至少一組發生非有限梯度或少做 optimizer update，不能當作乾淨因果比較。"
                ),
                "final_eval_preference_delta_pp": round(
                    100
                    * (
                        treatment["final_eval_chosen_preference_rate"]
                        - baseline["final_eval_chosen_preference_rate"]
                    ),
                    6,
                ),
                "final_eval_target_margin_delta_pp": round(
                    100
                    * (
                        treatment["final_eval_target_margin_rate"]
                        - baseline["final_eval_target_margin_rate"]
                    ),
                    6,
                ),
                "eval_mean_margin_gain_difference": (
                    treatment["eval_mean_raw_margin_delta"]
                    - baseline["eval_mean_raw_margin_delta"]
                ),
                "preferred_log_prob_gain_difference": (
                    treatment["preferred_likelihood"][
                        "mean_chosen_average_log_prob_delta"
                    ]
                    - baseline["preferred_likelihood"][
                        "mean_chosen_average_log_prob_delta"
                    ]
                ),
            }
        )
    return {
        "design": "2x2_prompt_balance_by_chosen_nll",
        "complete_four_cell_design": not missing_cells,
        "selected_control_signature": cohort_rows[0]["training_controls"],
        "cells": {
            cell: {
                "label": row["label"],
                "prompt_balance_enabled": row["prompt_balance_enabled"],
                "chosen_nll_weight": row["chosen_nll_weight"],
                "final_eval_chosen_preference_rate": row[
                    "final_eval_chosen_preference_rate"
                ],
                "final_eval_target_margin_rate": row["final_eval_target_margin_rate"],
                "eval_mean_raw_margin_delta": row["eval_mean_raw_margin_delta"],
                "mean_chosen_average_log_prob_delta": row["preferred_likelihood"][
                    "mean_chosen_average_log_prob_delta"
                ],
                "optimizer_updates": row["optimizer_updates"],
                "expected_optimizer_updates": row["expected_optimizer_updates"],
                "nonfinite_skips": row["nonfinite_skips"],
                "numerically_complete": row["numerically_complete"],
            }
            for cell, row in cells.items()
        },
        "missing_cells": missing_cells,
        "comparisons": comparisons,
        "research_boundary": (
            "This is a one-seed local 2x2 ablation. Only comparisons with complete optimizer updates and zero "
            "non-finite events support a single-factor interpretation; none establish broad human preference."
        ),
    }


def derive_diagnosis(factorial):
    comparisons = {row["id"]: row for row in factorial["comparisons"]}
    observations = []
    balance = comparisons.get("prompt_balance_without_nll")
    if balance and balance["valid_single_factor_comparison"]:
        observations.append(
            "單獨加入 prompt 平衡後，未見偏好率變化 "
            f"{balance['final_eval_preference_delta_pp']:+.1f} pp，沒有形成正向證據。"
        )
    nll = comparisons.get("chosen_nll_with_balance")
    if nll and nll["valid_single_factor_comparison"]:
        observations.append(
            "在 prompt 平衡固定開啟時，chosen NLL 使未見偏好率變化 "
            f"{nll['final_eval_preference_delta_pp']:+.1f} pp，但仍須通過絕對 gate 才能上線。"
        )
    invalid = [
        row for row in factorial["comparisons"] if not row["valid_single_factor_comparison"]
    ]
    if invalid:
        observations.append(
            "含數值異常候選的比較已排除因果解讀，不用不完整訓練替候選加分。"
        )
    observations.append(
        "目前證據只支持 chosen NLL 可降低退化風險，不支持這批 pairwise 資料已讓右腦學會穩定偏好排序；正式右腦維持 V10。"
    )
    return "".join(observations)


def build_report(candidates):
    rows = [evaluate_candidate(label, report) for label, report in candidates]
    factorial = build_factorial_analysis(rows)
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
        "factorial_analysis": factorial,
        "authorized_candidate_count": len(authorized),
        "selected_adapter": authorized[0]["adapter_ref"] if len(authorized) == 1 else None,
        "run_actual_model_holdout": len(authorized) == 1,
        "decision_zh": decision_zh,
        "diagnosis_zh": derive_diagnosis(factorial),
        "research_references": [
            "https://github.com/princeton-nlp/SimPO",
            "https://proceedings.mlr.press/v267/gupta25c.html",
            "https://arxiv.org/abs/2604.15602",
        ],
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
    factorial = report["factorial_analysis"]
    lines.extend(
        [
            "",
            "## 2×2 單一變因設計",
            "",
            "固定 V10 起點、資料、切分、seed、epoch、學習率、beta 與 batch 設定，只切換 prompt 平衡與 chosen NLL。",
            "",
            "| 實驗格 | prompt 平衡 | chosen NLL | unseen preference | target margin | margin delta | updates | 數值完整 |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for cell in FACTORIAL_CELLS:
        row = factorial["cells"].get(cell)
        if row is None:
            lines.append(f"| {cell} | - | - | - | - | - | - | MISSING |")
            continue
        lines.append(
            f"| {row['label']} | {'ON' if row['prompt_balance_enabled'] else 'OFF'} | "
            f"{row['chosen_nll_weight']:.1f} | {row['final_eval_chosen_preference_rate']:.0%} | "
            f"{row['final_eval_target_margin_rate']:.0%} | {row['eval_mean_raw_margin_delta']:+.6f} | "
            f"{row['optimizer_updates']}/{row['expected_optimizer_updates']} | "
            f"{'YES' if row['numerically_complete'] else 'NO'} |"
        )
    lines.extend(
        [
            "",
            "| 單一變因比較 | 對照 → 處理 | preference 差 | margin gain 差 | 可作因果解讀 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for comparison in factorial["comparisons"]:
        lines.append(
            f"| {comparison['changed_factor']} | {comparison['baseline']} → {comparison['treatment']} | "
            f"{comparison['final_eval_preference_delta_pp']:+.1f} pp | "
            f"{comparison['eval_mean_margin_gain_difference']:+.6f} | "
            f"{'YES' if comparison['valid_single_factor_comparison'] else 'NO'} |"
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
    lines.extend(
        [
            "研究邊界：" + report["research_boundary"],
            "",
            "2×2 邊界：" + factorial["research_boundary"],
            "",
            "參考：" + "、".join(report["research_references"]),
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v21-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v22-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V22_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v23-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V23_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v24-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V24_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--v25-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V25_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_DECISION_MD_PATH)
    args = parser.parse_args()
    report = build_report(
        [
            ("V21 1-epoch", json.loads(Path(args.v21_report).read_text(encoding="utf-8"))),
            ("V22 3-epoch", json.loads(Path(args.v22_report).read_text(encoding="utf-8"))),
            (
                "V23 prompt-balanced",
                json.loads(Path(args.v23_report).read_text(encoding="utf-8")),
            ),
            (
                "V24 balanced + chosen-NLL",
                json.loads(Path(args.v24_report).read_text(encoding="utf-8")),
            ),
            (
                "V25 pairwise + chosen-NLL",
                json.loads(Path(args.v25_report).read_text(encoding="utf-8")),
            ),
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
