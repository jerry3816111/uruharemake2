#!/usr/bin/env python3
"""Collect V10 candidates on source-separated V21 development cases."""

import argparse
import json
import os
from pathlib import Path

from eval_rightbrain_model_surface_holdout import build_report, write_markdown
from project_paths import (
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_MD_PATH,
)
from rightbrain_on_policy_dev_cases_v21 import case_inputs, validate_cases


DEFAULT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"


def build_dev_report(adapter_path, candidate_count, seed, load_model=True):
    cases = case_inputs()
    validation = validate_cases(cases)
    if not validation["valid"]:
        raise ValueError(f"Invalid V21 development cases: {validation['errors']}")
    report = build_report(
        load_model=load_model,
        adapter_path=adapter_path,
        candidate_count=candidate_count,
        seed=seed,
        repair_enabled=False,
        cases=cases,
        scope="rightbrain_on_policy_dev_v21_candidate_collection",
        research_boundary=(
            "These are source-separated development prompts used only to collect candidates from the current "
            "V10 policy. They do not overlap the promotion holdout and cannot be used as promotion evidence."
        ),
        conclusion_zh=(
            "這份報告只記錄 V10 在 16 個新開發情境中的真實候選分布；後續 preference dataset "
            "只會使用同一批 V10 產生、且通過完整品質檢查的 chosen，搭配同策略產生的 rejected。"
        ),
    )
    report["dev_case_validation"] = validation
    report["on_policy_evidence"] = {
        "adapter_ref": os.path.basename(os.path.abspath(adapter_path)),
        "chosen_and_rejected_must_come_from_same_adapter": True,
        "manual_chosen_allowed": False,
        "deterministic_fallback_allowed_as_chosen": False,
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-model", action="store_true")
    parser.add_argument("--adapter-path", default=DEFAULT_ADAPTER)
    parser.add_argument("--candidate-count", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--output-json", default=RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_MD_PATH)
    args = parser.parse_args()
    if not args.load_model:
        raise SystemExit("Use --load-model so this report contains actual V10 candidates")
    report = build_dev_report(
        args.adapter_path,
        args.candidate_count,
        args.seed,
        load_model=True,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    summary = report["summary"]
    expected_candidates = summary["case_count"] * report["candidate_count_per_case"]
    return 0 if summary["model_loaded"] and summary["generated_candidate_count"] == expected_candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
