#!/usr/bin/env python3
"""Collect multiple real V10 candidates for fresh V29 human-preference prompts."""

import argparse
import json
import os
from pathlib import Path

from eval_rightbrain_model_surface_holdout import build_report, write_markdown
from project_paths import (
    RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_MD_PATH,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases
from train_uruha_rightbrain_contract_v1 import _sha256


DEFAULT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_CANDIDATE_COUNT = 3
DEFAULT_SEED = 20260712


def finalize_candidate_report(report, adapter_path):
    from uruha_brain_mac import (
        RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES,
        RIGHT_BRAIN_SAMPLE_TEMPERATURES,
        RIGHT_BRAIN_SAMPLE_TOP_K,
        RIGHT_BRAIN_SAMPLE_TOP_P,
    )

    validation = validate_cases()
    requested_count = int(report["candidate_count_per_case"])
    runtime_setting_count = min(
        len(RIGHT_BRAIN_SAMPLE_TEMPERATURES),
        len(RIGHT_BRAIN_SAMPLE_TOP_P),
        len(RIGHT_BRAIN_SAMPLE_TOP_K),
        len(RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES),
    )
    effective_count = min(requested_count, runtime_setting_count)
    generated_counts = [
        int(row.get("generated_candidate_count") or 0)
        for row in report.get("cases") or []
    ]
    full_cases = {case["id"]: case for case in case_inputs()}
    collected_case_ids = [row.get("id") for row in report.get("cases") or []]
    collected_cases_valid = (
        bool(collected_case_ids)
        and len(collected_case_ids) == len(set(collected_case_ids))
        and all(case_id in full_cases for case_id in collected_case_ids)
    )
    expected = len(collected_case_ids) * effective_count
    adapter_file = Path(adapter_path) / "adapter_model.safetensors"
    report["adapter_model_sha256"] = _sha256(adapter_file)
    report["dev_case_validation"] = validation
    report["requested_candidate_count_per_case"] = requested_count
    report["runtime_sampling_setting_count"] = runtime_setting_count
    report["effective_candidate_count_per_case"] = effective_count
    report["collected_case_count"] = len(collected_case_ids)
    report["collected_case_ids"] = collected_case_ids
    report["conclusion_zh"] = (
        f"這份報告只收集正式 V10 在 {len(collected_case_ids)} 個指定全新情境中的多候選輸出。"
        "候選尚未取得人類偏好，不能直接訓練或作為 promotion 證據。"
    )
    report["candidate_collection_gates"] = {
        "real_model_loaded": report["load_model"] is True,
        "formal_v10_adapter_used": report["adapter_ref"]
        == "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1",
        "fresh_case_validation_passed": validation["valid"],
        "collected_cases_are_valid_fresh_cases": collected_cases_valid,
        "all_effective_runtime_candidates_generated": (
            len(generated_counts) == len(collected_case_ids)
            and all(count == effective_count for count in generated_counts)
            and report["summary"]["generated_candidate_count"] == expected
        ),
        "repair_was_disabled": report["repair_enabled"] is False,
    }
    report["authorize_blind_package_build"] = all(
        report["candidate_collection_gates"].values()
    )
    return report


def build_candidate_report(
    adapter_path,
    candidate_count,
    seed,
    load_model=True,
    case_ids=None,
):
    all_cases = case_inputs()
    validation = validate_cases(all_cases)
    if not validation["valid"]:
        raise ValueError(f"Invalid V29 development cases: {validation['errors']}")
    case_by_id = {case["id"]: case for case in all_cases}
    selected_ids = list(dict.fromkeys(case_ids or case_by_id))
    unknown = [case_id for case_id in selected_ids if case_id not in case_by_id]
    if unknown:
        raise ValueError(f"Unknown V29 case IDs: {unknown}")
    cases = [case_by_id[case_id] for case_id in selected_ids]
    report = build_report(
        load_model=load_model,
        adapter_path=adapter_path,
        candidate_count=candidate_count,
        seed=seed,
        repair_enabled=False,
        cases=cases,
        scope="rightbrain_on_policy_v29_candidate_collection",
        research_boundary=(
            "These fresh development prompts collect multiple candidates from the unchanged formal V10 policy. "
            "They do not overlap V21 training prompts, prior human-blind inputs, or the promotion holdout."
        ),
        conclusion_zh=(
            f"這份報告只收集正式 V10 在 {len(cases)} 個指定全新情境中的多候選輸出。候選尚未取得人類偏好，"
            "不能直接訓練或作為 promotion 證據。"
        ),
    )
    return finalize_candidate_report(report, adapter_path)


def write_candidate_markdown(report, path):
    write_markdown(report, path)
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## V29 採樣上限\n\n"
            f"- requested_candidate_count_per_case: {report['requested_candidate_count_per_case']}\n"
            f"- runtime_sampling_setting_count: {report['runtime_sampling_setting_count']}\n"
            f"- effective_candidate_count_per_case: {report['effective_candidate_count_per_case']}\n"
            "- 擴樣方法：保持每次正式 runtime 採樣設定不變，改用不同 seed 另存報告。\n"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-model", action="store_true")
    parser.add_argument(
        "--audit-existing",
        action="store_true",
        help="Recalculate collection gates without regenerating model text.",
    )
    parser.add_argument("--adapter-path", default=DEFAULT_ADAPTER)
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Collect only selected fresh cases; repeat for focused resampling.",
    )
    parser.add_argument(
        "--output-json",
        default=RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_JSON_PATH,
    )
    parser.add_argument(
        "--output-md",
        default=RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_MD_PATH,
    )
    args = parser.parse_args()
    if not args.load_model and not args.audit_existing:
        raise SystemExit("Use --load-model so V29 contains actual formal V10 candidates")
    if args.audit_existing:
        report = finalize_candidate_report(
            json.loads(Path(args.output_json).read_text(encoding="utf-8")),
            args.adapter_path,
        )
    else:
        report = build_candidate_report(
            args.adapter_path,
            args.candidate_count,
            args.seed,
            load_model=True,
            case_ids=args.case_id or None,
        )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_candidate_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "adapter_ref": report["adapter_ref"],
                "case_count": report["summary"]["case_count"],
                "generated_candidate_count": report["summary"][
                    "generated_candidate_count"
                ],
                "authorize_blind_package_build": report[
                    "authorize_blind_package_build"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["authorize_blind_package_build"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
