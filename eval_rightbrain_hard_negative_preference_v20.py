#!/usr/bin/env python3
"""Gate V20 hard-negative SimPO before actual-model generation."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_semantic_preference_v19 import build_report as build_training_gate
from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_MD_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def build_report(dataset_report, training_report):
    training_gate = build_training_gate(training_report)
    data_gates = {
        "dataset_pairs_are_single_slot_omissions": dataset_report["all_pairs_single_slot_omission"],
        "dataset_pairs_are_length_matched": dataset_report["all_pairs_length_matched"],
        "dataset_promotion_holdout_overlap_is_zero": not dataset_report["data_boundary"][
            "diagnostic_only"
        ],
    }
    gates = {**data_gates, **training_gate["gates"]}
    authorize_holdout = all(gates.values())
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_hard_negative_preference_v20_pre_holdout_gate",
        "adapter_ref": training_report["output_adapter_ref"],
        "gates": gates,
        "authorize_actual_model_holdout": authorize_holdout,
        "dataset_result": {
            "pair_count": dataset_report["pair_count"],
            **dataset_report["length_profile_chars"],
        },
        "training_result": training_gate["result"],
        "decision_zh": (
            "允許 V20 進入 V10 對照的雙 seed 真實模型 holdout。"
            if authorize_holdout
            else "不允許 V20 進入真實模型 holdout：hard-negative SimPO 未通過資料或未見家族 gate。"
        ),
        "research_boundary": (
            "V20 uses manually authored, length-matched synthetic hard negatives. Passing this gate only authorizes "
            "actual-model evaluation; it does not promote the adapter."
        ),
    }


def write_markdown(report, path):
    data = report["dataset_result"]
    training = report["training_result"]
    lines = [
        "# RightBrain V20 Hard-Negative SimPO 決策",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| hard-negative pairs | {data['pair_count']} |",
        f"| mean char delta | {data['mean_delta_rejected_minus_chosen']:+.2f} |",
        f"| max absolute char delta | {data['max_absolute_delta']} |",
        f"| optimizer updates | {training['optimizer_updates']}/{training['expected_optimizer_updates']} |",
        f"| non-finite skips | {training['nonfinite_skips']} |",
        f"| train chosen preference | {training['final_train_chosen_preference_rate']:.1%} |",
        f"| unseen chosen preference | {training['initial_eval_chosen_preference_rate']:.1%} -> {training['final_eval_chosen_preference_rate']:.1%} |",
        f"| unseen mean margin | {training['initial_eval_mean_raw_margin']:+.6f} -> {training['final_eval_mean_raw_margin']:+.6f} |",
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
    parser.add_argument("--dataset-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH)
    parser.add_argument("--training-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DECISION_REPORT_MD_PATH)
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
    print(json.dumps({"gates": report["gates"], "authorize_actual_model_holdout": report["authorize_actual_model_holdout"]}, ensure_ascii=False, indent=2))
    return 0 if report["authorize_actual_model_holdout"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
