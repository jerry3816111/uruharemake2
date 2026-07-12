#!/usr/bin/env python3
"""Analyze V29 same-policy human choices without promoting the runtime."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_ON_POLICY_V29_ANALYSIS_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_V29_ANALYSIS_MD_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH,
)
from serve_rightbrain_on_policy_blind_v29 import CHOICES, _package_sha256, load_package


TZ = ZoneInfo("Asia/Tokyo")
MIN_DECISIVE_PAIRS = 4
MIN_DECISIVE_SOURCE_FAMILIES = 4
EXPECTED_FORMAL_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
METHOD_REFERENCES = (
    "https://arxiv.org/abs/2403.04132",
    "https://proceedings.mlr.press/v235/tajwar24a.html",
    "https://arxiv.org/abs/2412.18407",
)


def _read_jsonl(path):
    rows = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
    return rows


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _candidate_summary(candidate):
    return {
        "candidate_id": candidate["candidate_id"],
        "text": candidate["text"],
        "seed": candidate["seed"],
        "source_report": candidate["source_report"],
        "current_strict_pass": candidate["current_strict_pass"],
        "human_reviewable_reasons": candidate["human_reviewable_reasons"],
        "hard_surface_pass": candidate["hard_surface_pass"],
    }


def _rating_outcome(choice, key_row):
    if choice == "left_better":
        return f"candidate:{key_row['left_candidate']['candidate_id']}"
    if choice == "right_better":
        return f"candidate:{key_row['right_candidate']['candidate_id']}"
    if choice == "tie":
        return "tie"
    if choice == "both_bad":
        return "both_bad"
    return "invalid"


def _integrity_evidence(package, key_rows, ratings_payload):
    package_rows = package.get("comparisons") or []
    package_id_list = [row.get("comparison_id") for row in package_rows]
    package_map = {row.get("comparison_id"): row for row in package_rows}
    key_id_list = [row.get("comparison_id") for row in key_rows]
    key_map = {row.get("comparison_id"): row for row in key_rows}
    rating_rows = ratings_payload.get("ratings") or []
    rating_ids = [row.get("comparison_id") for row in rating_rows]
    rating_map = {row.get("comparison_id"): row for row in rating_rows}
    package_ids = set(package_map)
    key_ids = set(key_map)

    key_package_text_matches = True
    all_candidates_hard_surface_pass = True
    pair_candidate_ids_are_distinct = True
    key_package_hash_matches = True
    adapter_refs = set()
    adapter_shas = set()
    for comparison_id, key in key_map.items():
        blind = package_map.get(comparison_id) or {}
        key_package_text_matches &= (
            blind.get("response_a") == key.get("left_candidate", {}).get("text")
            and blind.get("response_b") == key.get("right_candidate", {}).get("text")
            and blind.get("task_id") == key.get("task_id")
        )
        key_package_hash_matches &= key.get("package_sha256") == package.get(
            "package_sha256"
        )
        for side in ("left_candidate", "right_candidate"):
            candidate = key.get(side) or {}
            all_candidates_hard_surface_pass &= bool(
                candidate.get("hard_surface_pass")
            ) and not candidate.get("hard_rejection_reasons")
            if candidate.get("adapter_ref"):
                adapter_refs.add(candidate["adapter_ref"])
            if candidate.get("adapter_model_sha256"):
                adapter_shas.add(candidate["adapter_model_sha256"])
        pair_candidate_ids_are_distinct &= key.get("left_candidate", {}).get(
            "candidate_id"
        ) != key.get("right_candidate", {}).get("candidate_id")

    repeat_structure_matches = True
    repeat_rows = [row for row in key_rows if row.get("is_consistency_repeat")]
    for repeat in repeat_rows:
        base = key_map.get(repeat.get("repeat_of")) or {}
        repeat_structure_matches &= (
            bool(base)
            and not base.get("is_consistency_repeat")
            and repeat.get("task_id") == base.get("task_id")
            and repeat.get("source_case_id") == base.get("source_case_id")
            and repeat.get("left_candidate", {}).get("candidate_id")
            == base.get("right_candidate", {}).get("candidate_id")
            and repeat.get("right_candidate", {}).get("candidate_id")
            == base.get("left_candidate", {}).get("candidate_id")
        )

    unknown_choices = sorted(
        {
            str(row.get("choice"))
            for row in rating_rows
            if row.get("choice") not in CHOICES
        }
    )
    unknown_rating_ids = sorted(set(rating_ids) - package_ids)
    duplicate_rating_ids = sorted(
        comparison_id
        for comparison_id, count in Counter(rating_ids).items()
        if count > 1
    )
    declared_count = ratings_payload.get("rated_count")
    expected_completed = len(rating_map) == len(package_ids)
    completed_flag = bool(ratings_payload.get("completed"))

    gates = {
        "package_hash_matches_content": package.get("package_sha256")
        == _package_sha256(package),
        "package_comparison_ids_are_unique": len(package_id_list)
        == len(set(package_id_list)),
        "key_comparison_ids_are_unique": len(key_id_list) == len(set(key_id_list)),
        "key_ids_exactly_match_package_ids": key_ids == package_ids,
        "key_rows_match_blind_package_text": key_package_text_matches,
        "key_rows_bind_the_same_package_hash": key_package_hash_matches,
        "all_candidates_pass_hard_surface_gate": all_candidates_hard_surface_pass,
        "all_candidates_use_one_adapter_ref": len(adapter_refs) == 1,
        "adapter_ref_is_formal_v10": adapter_refs == {EXPECTED_FORMAL_ADAPTER},
        "all_candidates_use_one_adapter_sha": len(adapter_shas) == 1,
        "candidate_ids_are_distinct_within_each_pair": pair_candidate_ids_are_distinct,
        "consistency_repeat_structure_is_swapped": bool(repeat_rows)
        and repeat_structure_matches,
        "ratings_bind_the_same_package_hash": ratings_payload.get("package_sha256")
        == package.get("package_sha256"),
        "rating_ids_are_unique": not duplicate_rating_ids,
        "rating_ids_are_known": not unknown_rating_ids,
        "rating_choices_are_valid": not unknown_choices,
        "declared_rated_count_matches_rows": declared_count == len(rating_rows),
        "declared_comparison_count_matches_package": ratings_payload.get(
            "comparison_count"
        )
        == len(package_ids),
        "completed_flag_matches_actual_coverage": completed_flag
        == expected_completed,
    }
    return {
        "gates": gates,
        "package_map": package_map,
        "key_map": key_map,
        "rating_map": rating_map,
        "adapter_refs": sorted(adapter_refs),
        "adapter_shas": sorted(adapter_shas),
        "unknown_choices": unknown_choices,
        "unknown_rating_ids": unknown_rating_ids,
        "duplicate_rating_ids": duplicate_rating_ids,
        "repeat_rows": repeat_rows,
    }


def build_analysis_report(package, key_rows, ratings_payload):
    integrity = _integrity_evidence(package, key_rows, ratings_payload)
    key_map = integrity["key_map"]
    rating_map = integrity["rating_map"]
    integrity_passed = all(integrity["gates"].values())

    independent_rows = [
        row for row in key_rows if not row.get("is_consistency_repeat")
    ]
    decision_counts = Counter()
    decisive_pairs = []
    tie_rows = []
    both_bad_rows = []
    strict_soft_rows = []
    for key in independent_rows:
        rating = rating_map.get(key["comparison_id"])
        if rating is None:
            continue
        choice = rating["choice"]
        if choice not in CHOICES:
            continue
        decision_counts[choice] += 1
        common = {
            "comparison_id": key["comparison_id"],
            "source_case_id": key["source_case_id"],
            "source_family": key["source_family"],
            "category": key["category"],
            "choice": choice,
            "note": rating.get("note") or "",
        }
        if choice == "tie":
            tie_rows.append(
                {
                    **common,
                    "left_candidate": _candidate_summary(key["left_candidate"]),
                    "right_candidate": _candidate_summary(key["right_candidate"]),
                }
            )
            continue
        if choice == "both_bad":
            both_bad_rows.append(
                {
                    **common,
                    "left_candidate": _candidate_summary(key["left_candidate"]),
                    "right_candidate": _candidate_summary(key["right_candidate"]),
                }
            )
            continue
        chosen_side = "left_candidate" if choice == "left_better" else "right_candidate"
        rejected_side = (
            "right_candidate" if choice == "left_better" else "left_candidate"
        )
        chosen = key[chosen_side]
        rejected = key[rejected_side]
        pair = {
            **common,
            "chosen": _candidate_summary(chosen),
            "rejected": _candidate_summary(rejected),
        }
        decisive_pairs.append(pair)
        strict_values = {
            chosen["candidate_id"]: bool(chosen["current_strict_pass"]),
            rejected["candidate_id"]: bool(rejected["current_strict_pass"]),
        }
        if len(set(strict_values.values())) == 2:
            strict_soft_rows.append(
                {
                    "comparison_id": key["comparison_id"],
                    "human_preferred_strict": bool(chosen["current_strict_pass"]),
                    "chosen_candidate_id": chosen["candidate_id"],
                    "rejected_candidate_id": rejected["candidate_id"],
                }
            )

    consistency_details = []
    for repeat in integrity["repeat_rows"]:
        base_id = repeat["repeat_of"]
        base_rating = rating_map.get(base_id)
        repeat_rating = rating_map.get(repeat["comparison_id"])
        base_key = key_map.get(base_id)
        if base_rating is None or repeat_rating is None or base_key is None:
            consistency_details.append(
                {
                    "base_comparison_id": base_id,
                    "repeat_comparison_id": repeat["comparison_id"],
                    "completed": False,
                    "consistent": None,
                }
            )
            continue
        base_outcome = _rating_outcome(base_rating["choice"], base_key)
        repeat_outcome = _rating_outcome(repeat_rating["choice"], repeat)
        consistency_details.append(
            {
                "base_comparison_id": base_id,
                "repeat_comparison_id": repeat["comparison_id"],
                "completed": True,
                "base_choice": base_rating["choice"],
                "repeat_choice": repeat_rating["choice"],
                "base_outcome": base_outcome,
                "repeat_outcome": repeat_outcome,
                "consistent": base_outcome == repeat_outcome,
            }
        )

    completed_consistency = [row for row in consistency_details if row["completed"]]
    consistent_count = sum(row["consistent"] for row in completed_consistency)
    all_comparisons_rated = set(rating_map) == set(integrity["package_map"])
    decisive_source_families = {
        row["source_family"] for row in decisive_pairs
    }
    probe_gates = {
        "all_integrity_gates_pass": integrity_passed,
        "all_comparisons_are_rated": all_comparisons_rated,
        "all_consistency_controls_are_completed": len(completed_consistency)
        == len(consistency_details),
        "all_consistency_controls_agree_after_side_swap": bool(
            consistency_details
        )
        and consistent_count == len(consistency_details),
        "decisive_independent_pairs_at_least_minimum": len(decisive_pairs)
        >= MIN_DECISIVE_PAIRS,
        "decisive_source_families_at_least_minimum": len(
            decisive_source_families
        )
        >= MIN_DECISIVE_SOURCE_FAMILIES,
    }
    authorize_probe = all(probe_gates.values())
    strict_preferred_count = sum(
        row["human_preferred_strict"] for row in strict_soft_rows
    )

    if not integrity_passed:
        decision_zh = "評分證據的 SHA、key、choice 或計數完整性不一致；不得使用。"
    elif not all_comparisons_rated:
        decision_zh = (
            f"盲測尚未完成：{len(rating_map)}/{len(integrity['package_map'])}。"
            "目前只能確認已儲存進度，不能建立偏好資料。"
        )
    elif not probe_gates[
        "all_consistency_controls_agree_after_side_swap"
    ]:
        decision_zh = "隱藏重測判斷不一致；本批只能作錯誤診斷，不能建立偏好訓練資料。"
    elif not authorize_probe:
        decision_zh = "有效明確偏好或來源覆蓋不足；保留診斷結果，不進行偏好訓練。"
    else:
        decision_zh = (
            "同一正式 V10 的人類偏好資料通過完整性、左右交換一致性與來源覆蓋 gate，"
            "可建立小型凍結 V10 訓練 probe；仍未授權 runtime 升級。"
        )

    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_on_policy_v29_human_preference_analysis",
        "method_references": list(METHOD_REFERENCES),
        "method": {
            "comparison_design": "anonymous pairwise comparison within the same formal V10 policy",
            "tie_policy": "tie is retained as an outcome and never converted into chosen/rejected",
            "both_bad_policy": "both_bad is diagnostic and never converted into chosen/rejected",
            "consistency_policy": "hidden repeats swap left/right; consistency compares candidate identity, not button side",
            "training_boundary": "single-rater evidence can authorize only a small frozen-policy probe, never runtime promotion",
        },
        "summary": {
            "package_comparison_count": len(integrity["package_map"]),
            "rated_comparison_count": len(rating_map),
            "independent_comparison_count": len(independent_rows),
            "rated_independent_comparison_count": sum(
                key["comparison_id"] in rating_map for key in independent_rows
            ),
            "decisive_pair_count": len(decisive_pairs),
            "tie_count": len(tie_rows),
            "both_bad_count": len(both_bad_rows),
            "decisive_source_family_count": len(decisive_source_families),
            "decision_counts": dict(sorted(decision_counts.items())),
            "rater_count": 1,
        },
        "adapter_evidence": {
            "adapter_refs": integrity["adapter_refs"],
            "adapter_model_sha256": integrity["adapter_shas"],
        },
        "integrity_gates": integrity["gates"],
        "integrity_errors": {
            "unknown_choices": integrity["unknown_choices"],
            "unknown_rating_ids": integrity["unknown_rating_ids"],
            "duplicate_rating_ids": integrity["duplicate_rating_ids"],
        },
        "authorize_diagnostic_use": integrity_passed,
        "consistency_evidence": {
            "control_count": len(consistency_details),
            "completed_control_count": len(completed_consistency),
            "consistent_control_count": consistent_count,
            "consistency_rate": _rate(
                consistent_count,
                len(completed_consistency),
            ),
            "details": consistency_details,
        },
        "programmatic_strict_vs_human": {
            "one_strict_one_soft_decisive_pair_count": len(strict_soft_rows),
            "human_preferred_strict_count": strict_preferred_count,
            "human_preferred_strict_rate": _rate(
                strict_preferred_count,
                len(strict_soft_rows),
            ),
            "rows": strict_soft_rows,
            "causal_interpretation_allowed": False,
        },
        "decisive_preference_pairs": decisive_pairs,
        "tie_rows": tie_rows,
        "both_bad_rows": both_bad_rows,
        "preference_probe_gates": probe_gates,
        "authorize_preference_dataset_build": authorize_probe,
        "authorize_frozen_v10_training_probe": authorize_probe,
        "authorize_runtime_promotion": False,
        "authorize_population_human_preference_claim": False,
        "decision_zh": decision_zh,
        "research_boundary": (
            "This is a single-rater development calibration with two intra-rater repeats. "
            "It cannot estimate inter-rater reliability, rank models, or support a population-level claim."
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    consistency = report["consistency_evidence"]
    strict = report["programmatic_strict_vs_human"]
    lines = [
        "# RightBrain V29 同策略人類偏好分析",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 證據 | 結果 |",
        "|---|---:|",
        f"| 已評分 | {summary['rated_comparison_count']}/{summary['package_comparison_count']} |",
        f"| 獨立明確偏好 | {summary['decisive_pair_count']} |",
        f"| 平手 | {summary['tie_count']} |",
        f"| 兩邊都不好 | {summary['both_bad_count']} |",
        f"| 重測一致 | {consistency['consistent_control_count']}/{consistency['control_count']} |",
        f"| 可建立偏好資料 | {'YES' if report['authorize_preference_dataset_build'] else 'NO'} |",
        f"| 可升級 runtime | {'YES' if report['authorize_runtime_promotion'] else 'NO'} |",
        "",
        "## 自動規則與真人偏好",
        "",
        f"一邊 strict、一邊 soft 的明確比較共有 {strict['one_strict_one_soft_decisive_pair_count']} 組；"
        f"真人選 strict 為 {strict['human_preferred_strict_count']} 組。這只用來校準規則，不能作因果結論。",
        "",
        "## Probe gate",
        "",
        "| 條件 | 結果 |",
        "|---|---:|",
    ]
    for name, passed in report["preference_probe_gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "只有一位評分者與兩個重測，因此不能估計評分者間信度、不能做模型排名，也不能直接上線。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH)
    parser.add_argument("--key", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
    parser.add_argument("--ratings", default=RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_ON_POLICY_V29_ANALYSIS_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_ON_POLICY_V29_ANALYSIS_MD_PATH)
    args = parser.parse_args()
    if not Path(args.ratings).exists():
        print(
            json.dumps(
                {
                    "status": "waiting_for_human_ratings",
                    "ratings_path": args.ratings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    package = load_package(args.package)
    key_rows = _read_jsonl(args.key)
    ratings_payload = json.loads(Path(args.ratings).read_text(encoding="utf-8"))
    report = build_analysis_report(package, key_rows, ratings_payload)
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "rated_comparison_count": report["summary"]["rated_comparison_count"],
                "package_comparison_count": report["summary"]["package_comparison_count"],
                "consistency_rate": report["consistency_evidence"]["consistency_rate"],
                "decisive_pair_count": report["summary"]["decisive_pair_count"],
                "authorize_preference_dataset_build": report[
                    "authorize_preference_dataset_build"
                ],
                "authorize_runtime_promotion": report["authorize_runtime_promotion"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
