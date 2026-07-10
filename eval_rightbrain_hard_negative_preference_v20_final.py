#!/usr/bin/env python3
"""Combine V20 synthetic and actual-model evidence into the final decision."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_FINAL_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_FINAL_DECISION_REPORT_MD_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_MULTISEED_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_ADAPTER_PRIORITY


TZ = ZoneInfo("Asia/Tokyo")


def _rate_delta(before, after):
    return round(float(after) - float(before), 4)


def build_report(
    dataset_report,
    training_report,
    pre_holdout_report,
    runtime_report,
    baseline_adapter_ref,
):
    initial_eval = training_report["initial_eval_preference"]
    final_eval = training_report["final_eval_preference"]
    baseline = runtime_report["aggregate"]["baseline"]
    candidate = runtime_report["aggregate"]["promoted"]
    family_deltas = runtime_report.get("rejection_reason_deltas", {}).get("family") or []
    regressions = [row for row in family_deltas if row.get("delta", 0) > 0]
    improvements = [row for row in family_deltas if row.get("delta", 0) < 0]
    synthetic_gate_passed = bool(pre_holdout_report["authorize_actual_model_holdout"])
    runtime_gate_passed = bool(runtime_report["promotion_recommended"])
    promote_adapter = synthetic_gate_passed and runtime_gate_passed
    transfer_gap = synthetic_gate_passed and not runtime_gate_passed

    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_hard_negative_preference_v20_final_decision",
        "baseline_adapter": baseline_adapter_ref,
        "candidate_adapter": training_report["output_adapter_ref"],
        "dataset_evidence": {
            "pair_count": dataset_report["pair_count"],
            "family_count": dataset_report["family_spec_count"],
            "single_slot_omission": dataset_report["all_pairs_single_slot_omission"],
            "length_matched": dataset_report["all_pairs_length_matched"],
            "holdout_case_overlap_count": dataset_report["data_boundary"][
                "holdout_case_overlap_count"
            ],
            "holdout_target_overlap_count": dataset_report["data_boundary"][
                "holdout_target_overlap_count"
            ],
        },
        "training_evidence": {
            "epochs": training_report["epochs"],
            "optimizer_updates": training_report["optimizer_updates"],
            "nonfinite_skips": training_report["nonfinite_skips"],
            "initial_unseen_chosen_preference_rate": initial_eval["chosen_preference_rate"],
            "final_unseen_chosen_preference_rate": final_eval["chosen_preference_rate"],
            "initial_unseen_mean_margin": initial_eval["mean_raw_preference_margin"],
            "final_unseen_mean_margin": final_eval["mean_raw_preference_margin"],
            "unseen_mean_margin_delta": _rate_delta(
                initial_eval["mean_raw_preference_margin"],
                final_eval["mean_raw_preference_margin"],
            ),
        },
        "runtime_evidence": {
            "seeds": runtime_report["seeds"],
            "case_count": candidate["case_count"],
            "generated_candidate_count": candidate["generated_candidate_count"],
            "baseline_accepted_candidate_count": baseline["accepted_candidate_count"],
            "candidate_accepted_candidate_count": candidate["accepted_candidate_count"],
            "baseline_raw_candidate_acceptance_rate": baseline[
                "raw_candidate_acceptance_rate"
            ],
            "candidate_raw_candidate_acceptance_rate": candidate[
                "raw_candidate_acceptance_rate"
            ],
            "raw_candidate_acceptance_delta": runtime_report["aggregate"][
                "raw_candidate_acceptance_delta"
            ],
            "baseline_model_selected_case_count": baseline["model_selected_case_count"],
            "candidate_model_selected_case_count": candidate["model_selected_case_count"],
            "baseline_final_quality_pass_rate": baseline["final_quality_pass_rate"],
            "candidate_final_quality_pass_rate": candidate["final_quality_pass_rate"],
            "quality_guard_pass": runtime_report["quality_guard_pass"],
            "all_seed_noninferior": runtime_report["all_seed_noninferior"],
            "all_seed_selection_noninferior": runtime_report[
                "all_seed_selection_noninferior"
            ],
            "regressed_failure_families": regressions,
            "improved_failure_families": improvements,
        },
        "gates": {
            "synthetic_pre_holdout_gate_passed": synthetic_gate_passed,
            "actual_model_runtime_gate_passed": runtime_gate_passed,
            "promote_adapter": promote_adapter,
        },
        "diagnosis": {
            "synthetic_to_runtime_transfer_gap": transfer_gap,
            "interpretation_zh": (
                "V20 的未見 synthetic pair 在訓練前已達 100% 偏好正確率，訓練後只有極小 margin 增益；"
                "這個訊號沒有轉移到真實生成，反而使語意缺漏與語言污染增加。"
                if transfer_gap
                else "synthetic gate 與真實生成 gate 的方向一致。"
            ),
            "next_experiment_zh": (
                "下一輪應改用與正式 holdout 分離的開發情境，收集 V10 真實生成的自然錯誤候選作為 on-policy "
                "preference data；訓練前還要先確認未見 pair 不是 100% 飽和。"
            ),
        },
        "decision_zh": (
            "V20 通過 synthetic 前置檢查，但真實模型雙 seed 退步，因此不升級；正式右腦維持 V10。"
            if not promote_adapter
            else "V20 同時通過 synthetic 與真實模型 gate，可以進入 runtime 升級程序。"
        ),
        "research_boundary": (
            "這份決策證明 V20 這組資料與訓練方法未改善指定的 11-case actual-model holdout；"
            "它不代表所有 preference learning 都無效，也不代表完整人類自然度已被測量。"
        ),
    }


def write_markdown(report, path):
    training = report["training_evidence"]
    runtime = report["runtime_evidence"]
    lines = [
        "# RightBrain V20 最終決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "## Synthetic 前置證據",
        "",
        "| 指標 | 訓練前 | 訓練後 |",
        "|---|---:|---:|",
        f"| 未見 pair 偏好正確率 | {training['initial_unseen_chosen_preference_rate']:.1%} | {training['final_unseen_chosen_preference_rate']:.1%} |",
        f"| 未見平均 margin | {training['initial_unseen_mean_margin']:+.6f} | {training['final_unseen_mean_margin']:+.6f} |",
        "",
        "## 真實模型雙 Seed",
        "",
        "| 指標 | V10 | V20 | 差異 |",
        "|---|---:|---:|---:|",
        f"| raw 候選接受率 | {runtime['baseline_raw_candidate_acceptance_rate']:.1%} | {runtime['candidate_raw_candidate_acceptance_rate']:.1%} | {runtime['raw_candidate_acceptance_delta'] * 100:+.1f} pp |",
        f"| 模型接管 | {runtime['baseline_model_selected_case_count']}/{runtime['case_count']} | {runtime['candidate_model_selected_case_count']}/{runtime['case_count']} | {runtime['candidate_model_selected_case_count'] - runtime['baseline_model_selected_case_count']:+d} |",
        f"| 最終品質 | {runtime['baseline_final_quality_pass_rate']:.1%} | {runtime['candidate_final_quality_pass_rate']:.1%} | {(runtime['candidate_final_quality_pass_rate'] - runtime['baseline_final_quality_pass_rate']) * 100:+.1f} pp |",
        "",
        "## 為什麼拒絕升級",
        "",
        report["diagnosis"]["interpretation_zh"],
        "",
        "| 退步錯誤族群 | V10 | V20 | 增加 |",
        "|---|---:|---:|---:|",
    ]
    for row in runtime["regressed_failure_families"]:
        lines.append(
            f"| {row['reason']} | {row['baseline_count']} | {row['candidate_count']} | {row['delta']:+d} |"
        )
    lines.extend(
        [
            "",
            "## 下一個有意義的實驗",
            "",
            report["diagnosis"]["next_experiment_zh"],
            "",
            f"研究邊界：{report['research_boundary']}",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH)
    parser.add_argument("--training-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--pre-holdout-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--runtime-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_MULTISEED_REPORT_JSON_PATH)
    parser.add_argument("--baseline-adapter-ref", default=RIGHT_BRAIN_ADAPTER_PRIORITY[0])
    parser.add_argument("--output-json", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_FINAL_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_FINAL_DECISION_REPORT_MD_PATH)
    args = parser.parse_args()
    report = build_report(
        json.loads(Path(args.dataset_report).read_text(encoding="utf-8")),
        json.loads(Path(args.training_report).read_text(encoding="utf-8")),
        json.loads(Path(args.pre_holdout_report).read_text(encoding="utf-8")),
        json.loads(Path(args.runtime_report).read_text(encoding="utf-8")),
        args.baseline_adapter_ref,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({"gates": report["gates"], "decision_zh": report["decision_zh"]}, ensure_ascii=False, indent=2))
    return 0 if report["gates"]["promote_adapter"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
