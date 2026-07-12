#!/usr/bin/env python3
"""Build V30 preference pairs only from authorized V29 human choices."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from analyze_rightbrain_on_policy_blind_v29 import _read_jsonl, build_analysis_report
from project_paths import (
    RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_DATASET_PATH,
    RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_JSON_PATH,
    RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_MD_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases
from serve_rightbrain_on_policy_blind_v29 import load_package
from uruha_brain_mac import (
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
    RightBrain,
)
from train_uruha_rightbrain_dpo_v18 import load_preference_rows


TZ = ZoneInfo("Asia/Tokyo")
EXPECTED_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
MIN_PAIR_COUNT = 4
MIN_SOURCE_FAMILY_COUNT = 4
PROMOTION_HOLDOUT_REPORTS = (
    "reports/rightbrain_plan_surface_boundary_holdout_c3.json",
    "reports/rightbrain_plan_surface_boundary_holdout_c3_seed20260709.json",
)


def _canonical_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _analysis_evidence_sha256(analysis):
    stable = {
        key: value for key, value in analysis.items() if key != "generated_at"
    }
    return _canonical_sha256(stable)


def _prompt_messages(case):
    rightbrain = RightBrain(load_model=False)
    logic = json.loads(json.dumps(case["logic"], ensure_ascii=False))
    max_chars = int(logic.get("constraints", {}).get("max_chars") or 88)
    payload = rightbrain._build_model_surface_payload(
        logic,
        case.get("psyche") or {},
        max_chars,
        memory_data=case.get("memory_data") or {},
    )
    return [
        {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
        {"role": "user", "content": payload},
    ]


def _promotion_holdout_inventory(paths=PROMOTION_HOLDOUT_REPORTS):
    inputs = set()
    outputs = set()
    for path in paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        for case in report.get("cases") or []:
            user_input = str(case.get("user_input") or "").strip()
            if user_input:
                inputs.add(user_input)
            for field in ("deterministic_reply", "final_reply"):
                text = str(case.get(field) or "").strip()
                if text:
                    outputs.add(text)
            for field in (
                "model_accepted_candidates",
                "model_initial_rejected_candidates",
            ):
                for candidate in case.get(field) or []:
                    text = str(
                        candidate.get("raw_candidate")
                        or candidate.get("candidate")
                        or ""
                    ).strip()
                    if text:
                        outputs.add(text)
    return {"inputs": inputs, "outputs": outputs}


def build_dataset(
    package,
    key_rows,
    ratings_payload,
    *,
    promotion_holdout_inputs=None,
    promotion_holdout_outputs=None,
):
    analysis = build_analysis_report(package, key_rows, ratings_payload)
    cases = case_inputs()
    validation = validate_cases(cases)
    case_map = {case["id"]: case for case in cases}
    if promotion_holdout_inputs is None or promotion_holdout_outputs is None:
        holdout = _promotion_holdout_inventory()
        promotion_holdout_inputs = holdout["inputs"]
        promotion_holdout_outputs = holdout["outputs"]
    promotion_holdout_inputs = set(promotion_holdout_inputs)
    promotion_holdout_outputs = set(promotion_holdout_outputs)

    rows = []
    skipped = Counter()
    seen_pair_keys = set()
    source_family_counts = Counter()
    unknown_source_case_ids = set()
    chosen_holdout_overlaps = set()
    rejected_holdout_overlaps = set()
    input_holdout_overlaps = set()

    for preference in analysis["decisive_preference_pairs"]:
        source_case_id = preference["source_case_id"]
        case = case_map.get(source_case_id)
        if case is None:
            unknown_source_case_ids.add(source_case_id)
            skipped["unknown_source_case"] += 1
            continue
        chosen = preference["chosen"]
        rejected = preference["rejected"]
        chosen_text = str(chosen.get("text") or "").strip()
        rejected_text = str(rejected.get("text") or "").strip()
        pair_key = (source_case_id, chosen_text, rejected_text)
        if not chosen_text or not rejected_text or chosen_text == rejected_text:
            skipped["empty_or_same_text"] += 1
            continue
        if pair_key in seen_pair_keys:
            skipped["duplicate_pair"] += 1
            continue
        seen_pair_keys.add(pair_key)
        if case["user_input"] in promotion_holdout_inputs:
            input_holdout_overlaps.add(case["user_input"])
        if chosen_text in promotion_holdout_outputs:
            chosen_holdout_overlaps.add(chosen_text)
        if rejected_text in promotion_holdout_outputs:
            rejected_holdout_overlaps.add(rejected_text)
        prompt_messages = _prompt_messages(case)
        source_family = preference["source_family"]
        row = {
            "id": f"rb_human_on_policy_preference_v30_{len(rows) + 1:04d}",
            "source_case_id": source_case_id,
            "source_prompt_id": source_case_id,
            "source_family": source_family,
            "category": preference["category"],
            "training_role": "rightbrain_v10_human_on_policy_preference_v30",
            "preference_rule": "single_rater_blinded_same_policy_decisive_choice",
            "on_policy_adapter_ref": analysis["adapter_evidence"]["adapter_refs"][0]
            if analysis["adapter_evidence"]["adapter_refs"]
            else "",
            "on_policy_adapter_sha256": analysis["adapter_evidence"][
                "adapter_model_sha256"
            ][0]
            if analysis["adapter_evidence"]["adapter_model_sha256"]
            else "",
            "prompt_messages": prompt_messages,
            "chosen": chosen_text,
            "rejected": rejected_text,
            "human_preference_evidence": {
                "comparison_id": preference["comparison_id"],
                "human_choice": preference["choice"],
                "note": preference["note"],
                "chosen_candidate_id": chosen["candidate_id"],
                "rejected_candidate_id": rejected["candidate_id"],
                "package_sha256": package["package_sha256"],
                "single_rater": True,
            },
            "pair_diagnostics": {
                "chosen_current_strict_pass": chosen["current_strict_pass"],
                "rejected_current_strict_pass": rejected["current_strict_pass"],
                "chosen_human_reviewable_reasons": chosen[
                    "human_reviewable_reasons"
                ],
                "rejected_human_reviewable_reasons": rejected[
                    "human_reviewable_reasons"
                ],
                "chosen_hard_surface_pass": chosen["hard_surface_pass"],
                "rejected_hard_surface_pass": rejected["hard_surface_pass"],
                "chosen_seed": chosen["seed"],
                "rejected_seed": rejected["seed"],
            },
            "messages": [
                *prompt_messages,
                {"role": "assistant", "content": chosen_text},
            ],
        }
        rows.append(row)
        source_family_counts[source_family] += 1

    adapter_refs = {row["on_policy_adapter_ref"] for row in rows}
    adapter_shas = {row["on_policy_adapter_sha256"] for row in rows}
    gates = {
        "human_analysis_authorized_dataset_build": analysis[
            "authorize_preference_dataset_build"
        ],
        "v29_development_cases_are_valid": validation["valid"],
        "all_decisive_pairs_were_materialized": len(rows)
        == analysis["summary"]["decisive_pair_count"],
        "pair_count_at_least_minimum": len(rows) >= MIN_PAIR_COUNT,
        "source_family_count_at_least_minimum": len(source_family_counts)
        >= MIN_SOURCE_FAMILY_COUNT,
        "source_prompt_ids_are_unique": len(
            {row["source_prompt_id"] for row in rows}
        )
        == len(rows),
        "all_source_families_are_named": all(
            str(row["source_family"]).strip() for row in rows
        ),
        "all_categories_are_named": all(str(row["category"]).strip() for row in rows),
        "unknown_source_case_count_is_zero": not unknown_source_case_ids,
        "all_pairs_have_distinct_text": all(
            row["chosen"] != row["rejected"] for row in rows
        ),
        "all_candidates_pass_hard_surface_gate": all(
            row["pair_diagnostics"]["chosen_hard_surface_pass"]
            and row["pair_diagnostics"]["rejected_hard_surface_pass"]
            for row in rows
        ),
        "all_pairs_use_formal_v10_adapter": adapter_refs == {EXPECTED_ADAPTER},
        "all_pairs_use_one_adapter_sha": len(adapter_shas) == 1
        and "" not in adapter_shas,
        "promotion_holdout_input_overlap_is_zero": not input_holdout_overlaps,
        "promotion_holdout_chosen_overlap_is_zero": not chosen_holdout_overlaps,
        "promotion_holdout_rejected_overlap_is_zero": not rejected_holdout_overlaps,
        "tie_rows_are_not_materialized": all(
            row["human_preference_evidence"]["human_choice"]
            in {"left_better", "right_better"}
            for row in rows
        ),
    }
    authorize_probe = all(gates.values())
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_human_on_policy_preference_v30_dataset",
        "source_evidence": {
            "package_sha256": package["package_sha256"],
            "key_canonical_sha256": _canonical_sha256(key_rows),
            "ratings_canonical_sha256": _canonical_sha256(ratings_payload),
            "analysis_canonical_sha256": _analysis_evidence_sha256(analysis),
            "adapter_refs": analysis["adapter_evidence"]["adapter_refs"],
            "adapter_model_sha256": analysis["adapter_evidence"][
                "adapter_model_sha256"
            ],
        },
        "analysis_summary": analysis["summary"],
        "analysis_consistency_evidence": analysis["consistency_evidence"],
        "pair_count": len(rows),
        "source_family_count": len(source_family_counts),
        "source_family_counts": dict(sorted(source_family_counts.items())),
        "unknown_source_case_ids": sorted(unknown_source_case_ids),
        "skipped_counts": dict(sorted(skipped.items())),
        "promotion_holdout_overlap": {
            "input_count": len(input_holdout_overlaps),
            "chosen_count": len(chosen_holdout_overlaps),
            "rejected_count": len(rejected_holdout_overlaps),
        },
        "dataset_canonical_sha256": _canonical_sha256(rows),
        "gates": gates,
        "authorize_preference_probe": authorize_probe,
        "authorize_training": False,
        "authorize_runtime_promotion": False,
        "decision_zh": (
            "真人同策略明確偏好已轉為來源隔離資料，可進入凍結 V10 likelihood probe；尚未授權訓練。"
            if authorize_probe
            else "人類評分、來源、數量或 holdout gate 未通過；不寫出可訓練資料。"
        ),
        "research_boundary": (
            "This single-rater dataset may be used only for a frozen-policy likelihood probe. "
            "A separate probe, training run, and matched-seed generation holdout are required before promotion."
        ),
    }
    return rows, report


def write_outputs(rows, report, dataset_path, report_json_path, report_md_path):
    dataset_path = Path(dataset_path)
    report_json_path = Path(report_json_path)
    report_md_path = Path(report_md_path)
    for path in (dataset_path, report_json_path, report_md_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    if report["authorize_preference_probe"]:
        dataset_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report["dataset_file_sha256"] = _file_sha256(dataset_path)
    else:
        dataset_path.unlink(missing_ok=True)
        report["dataset_file_sha256"] = ""
    report_json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# RightBrain V30 真人同策略偏好資料",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 證據 | 結果 |",
        "|---|---:|",
        f"| 明確偏好 pair | {report['pair_count']} |",
        f"| 來源族 | {report['source_family_count']} |",
        f"| hidden repeat 一致 | {report['analysis_consistency_evidence']['consistent_control_count']}/{report['analysis_consistency_evidence']['control_count']} |",
        f"| 可進 likelihood probe | {'YES' if report['authorize_preference_probe'] else 'NO'} |",
        f"| 已授權訓練 | {'YES' if report['authorize_training'] else 'NO'} |",
        f"| 已授權 runtime | {'YES' if report['authorize_runtime_promotion'] else 'NO'} |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---:|",
    ]
    for name, passed in report["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "這是單一評分者的 development 資料。必須先確認正式 V10 在未見來源上仍會排錯，才值得訓練。",
            "",
        ]
    )
    report_md_path.write_text("\n".join(lines), encoding="utf-8")


def bind_source_file_hashes(report, package_path, key_path, ratings_path):
    report["source_evidence"].update(
        {
            "package_file_sha256": _file_sha256(package_path),
            "key_file_sha256": _file_sha256(key_path),
            "ratings_file_sha256": _file_sha256(ratings_path),
        }
    )
    return report


def load_authorized_probe_rows(
    dataset_path,
    report_path,
    *,
    package_path=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    key_path=RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    ratings_path=RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH,
):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if not report.get("authorize_preference_probe"):
        raise ValueError("V30 dataset report did not authorize the likelihood probe")
    if report.get("authorize_training") or report.get("authorize_runtime_promotion"):
        raise ValueError("V30 dataset report exceeds the allowed probe boundary")
    if not report.get("gates") or not all(report["gates"].values()):
        raise ValueError("V30 dataset report contains a failed source gate")
    source = report.get("source_evidence") or {}
    expected_file_hashes = {
        "package_file_sha256": _file_sha256(package_path),
        "key_file_sha256": _file_sha256(key_path),
        "ratings_file_sha256": _file_sha256(ratings_path),
    }
    for field, actual in expected_file_hashes.items():
        if source.get(field) != actual:
            raise ValueError(f"V30 source evidence changed after report: {field}")
    package = load_package(package_path)
    key_rows = _read_jsonl(key_path)
    ratings_payload = json.loads(Path(ratings_path).read_text(encoding="utf-8"))
    analysis = build_analysis_report(package, key_rows, ratings_payload)
    if not analysis.get("authorize_preference_dataset_build"):
        raise ValueError("Current V29 human analysis no longer authorizes dataset use")
    if source.get("package_sha256") != package.get("package_sha256"):
        raise ValueError("V30 package content hash does not match its evidence report")
    if source.get("key_canonical_sha256") != _canonical_sha256(key_rows):
        raise ValueError("V30 key canonical hash does not match its evidence report")
    if source.get("ratings_canonical_sha256") != _canonical_sha256(ratings_payload):
        raise ValueError("V30 ratings canonical hash does not match its evidence report")
    if source.get("analysis_canonical_sha256") != _analysis_evidence_sha256(analysis):
        raise ValueError("V30 analysis changed after its evidence report")
    rebuilt_rows, rebuilt_report = build_dataset(package, key_rows, ratings_payload)
    if not rebuilt_report.get("authorize_preference_probe"):
        raise ValueError("Current source evidence no longer rebuilds an authorized probe")
    if report.get("dataset_canonical_sha256") != rebuilt_report.get(
        "dataset_canonical_sha256"
    ):
        raise ValueError("V30 report does not match rebuilt human preference pairs")
    if report.get("dataset_file_sha256") != _file_sha256(dataset_path):
        raise ValueError("V30 preference dataset changed after its evidence report")
    rows = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if report.get("dataset_canonical_sha256") != _canonical_sha256(rows):
        raise ValueError("V30 canonical dataset hash does not match its evidence report")
    if report.get("pair_count") != len(rows):
        raise ValueError("V30 dataset row count does not match its evidence report")
    if _canonical_sha256(rows) != _canonical_sha256(rebuilt_rows):
        raise ValueError("V30 dataset does not match rebuilt human preference pairs")
    return load_preference_rows(dataset_path, allow_human_preference=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH)
    parser.add_argument("--key", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
    parser.add_argument("--ratings", default=RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH)
    parser.add_argument("--output-dataset", default=RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_DATASET_PATH)
    parser.add_argument("--output-report-json", default=RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_JSON_PATH)
    parser.add_argument("--output-report-md", default=RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_MD_PATH)
    args = parser.parse_args()
    if not Path(args.ratings).exists():
        print(
            json.dumps(
                {"status": "waiting_for_human_ratings", "ratings_path": args.ratings},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    package = load_package(args.package)
    key_rows = _read_jsonl(args.key)
    ratings_payload = json.loads(Path(args.ratings).read_text(encoding="utf-8"))
    rows, report = build_dataset(package, key_rows, ratings_payload)
    bind_source_file_hashes(
        report,
        args.package,
        args.key,
        args.ratings,
    )
    write_outputs(
        rows,
        report,
        args.output_dataset,
        args.output_report_json,
        args.output_report_md,
    )
    print(
        json.dumps(
            {
                "pair_count": report["pair_count"],
                "source_family_count": report["source_family_count"],
                "authorize_preference_probe": report["authorize_preference_probe"],
                "authorize_training": report["authorize_training"],
                "authorize_runtime_promotion": report["authorize_runtime_promotion"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["authorize_preference_probe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
