#!/usr/bin/env python3
"""Calibrate automatic right-brain labels against completed human blind ratings."""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from import_human_blind_evidence import (
    DEFAULT_SOURCE_SPECS,
    S0_SYSTEM_ID,
    _complete_rating,
    _read_csv,
    _read_jsonl,
    _sha256,
    load_blind_evidence,
)
from project_paths import (
    HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
    RIGHTBRAIN_HUMAN_PREFERENCE_CALIBRATION_V28_JSON_PATH,
    RIGHTBRAIN_HUMAN_PREFERENCE_CALIBRATION_V28_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
PROMOTION_HOLDOUT_REPORTS = (
    "reports/rightbrain_plan_surface_boundary_holdout_c3.json",
    "reports/rightbrain_plan_surface_boundary_holdout_c3_seed20260709.json",
)
METHOD_REFERENCES = (
    "https://arxiv.org/abs/2403.04132",
    "https://proceedings.mlr.press/v235/tajwar24a.html",
    "https://aclanthology.org/2024.acl-long.745/",
)


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _classification_metrics(rows, human_positive):
    counts = Counter()
    for row in rows:
        automatic = bool(row["programmatic_pass"])
        human = bool(human_positive(row))
        counts[(automatic, human)] += 1
    tp = counts[(True, True)]
    fp = counts[(True, False)]
    tn = counts[(False, False)]
    fn = counts[(False, True)]
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    specificity = _rate(tn, tn + fp)
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": (
            (recall + specificity) / 2
            if recall is not None and specificity is not None
            else None
        ),
        "matthews_correlation": (
            (tp * tn - fp * fn) / denominator if denominator else None
        ),
    }


def _mean(values):
    values = [float(value) for value in values]
    return sum(values) / len(values) if values else None


def _dimension_summary(rows):
    output = []
    by_source = defaultdict(list)
    for row in rows:
        by_source[row["source_id"]].append(row)
    for source_id, source_rows in sorted(by_source.items()):
        fields = sorted({field for row in source_rows for field in row["scores"]})
        systems = []
        for system_id in sorted({row["system_id"] for row in source_rows}):
            system_rows = [row for row in source_rows if row["system_id"] == system_id]
            systems.append(
                {
                    "system_id": system_id,
                    "candidate_count": len(system_rows),
                    "dimension_means": {
                        field: _mean(
                            row["scores"][field]
                            for row in system_rows
                            if row["scores"].get(field) is not None
                        )
                        for field in fields
                    },
                }
            )
        output.append(
            {
                "source_id": source_id,
                "score_fields": fields,
                "systems": systems,
            }
        )
    return output


def _duplicate_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["source_id"], row["task_id"], row["output_text"].strip())].append(row)
    duplicate_groups = [items for items in grouped.values() if len(items) > 1]
    disagreements = []
    decision_disagreements = []
    for items in duplicate_groups:
        signatures = {
            (
                item["decision"],
                tuple(sorted(item["scores"].items())),
            )
            for item in items
        }
        if len(signatures) > 1:
            evidence = {
                "source_id": items[0]["source_id"],
                "task_id": items[0]["task_id"],
                "output_text": items[0]["output_text"],
                "review_ids": [item["review_id"] for item in items],
                "decisions": [item["decision"] for item in items],
                "scores": [item["scores"] for item in items],
            }
            disagreements.append(evidence)
            if len({item["decision"] for item in items}) > 1:
                decision_disagreements.append(evidence)
    return {
        "exact_duplicate_text_group_count": len(duplicate_groups),
        "duplicate_rating_disagreement_group_count": len(disagreements),
        "duplicate_rating_disagreement_rate": _rate(
            len(disagreements), len(duplicate_groups)
        ),
        "duplicate_decision_disagreement_group_count": len(
            decision_disagreements
        ),
        "duplicate_decision_disagreement_rate": _rate(
            len(decision_disagreements), len(duplicate_groups)
        ),
        "disagreement_examples": disagreements[:5],
        "decision_disagreement_examples": decision_disagreements[:5],
    }


def _load_key_map(source_specs):
    key_map = {}
    for spec in source_specs:
        for row in _read_jsonl(spec["key_path"]):
            review_id = row["review_id"]
            key = (spec["source_id"], review_id)
            if key in key_map:
                raise ValueError(f"duplicate source/review key: {key}")
            key_map[key] = row
    return key_map


def _attach_automatic_labels(rows, key_map):
    output = []
    missing = []
    for row in rows:
        lookup_key = (row["source_id"], row["review_id"])
        key = key_map.get(lookup_key)
        if key is None:
            missing.append({"source_id": row["source_id"], "review_id": row["review_id"]})
            continue
        item = dict(row)
        item.update(
            {
                "programmatic_pass": bool(key.get("programmatic_pass")),
                "programmatic_semantic_completeness_score": key.get(
                    "semantic_completeness_score"
                ),
                "programmatic_user_facing_violation": bool(
                    key.get("user_facing_violation")
                ),
            }
        )
        output.append(item)
    return output, missing


def _load_explicit_pairs(source_specs, processed_rows):
    row_map = {
        (row["source_id"], row["review_id"]): row for row in processed_rows
    }
    pairs = []
    errors = []
    for spec in source_specs:
        ratings = _read_csv(spec["ratings_path"])
        complete = [row for row in ratings if _complete_rating(row, spec)]
        if not complete or "task_best_review_id" not in complete[0]:
            continue
        by_task = defaultdict(list)
        for row in complete:
            by_task[row["task_id"]].append(row)
        for task_id, task_rows in sorted(by_task.items()):
            best_ids = {row.get("task_best_review_id", "").strip() for row in task_rows}
            worst_ids = {row.get("task_worst_review_id", "").strip() for row in task_rows}
            best_ids.discard("")
            worst_ids.discard("")
            if len(best_ids) != 1 or len(worst_ids) != 1:
                errors.append(
                    {
                        "source_id": spec["source_id"],
                        "task_id": task_id,
                        "best_ids": sorted(best_ids),
                        "worst_ids": sorted(worst_ids),
                    }
                )
                continue
            best_id = next(iter(best_ids))
            worst_id = next(iter(worst_ids))
            best = row_map.get((spec["source_id"], best_id))
            worst = row_map.get((spec["source_id"], worst_id))
            if best is None or worst is None or best["output_text"] == worst["output_text"]:
                errors.append(
                    {
                        "source_id": spec["source_id"],
                        "task_id": task_id,
                        "best_ids": [best_id],
                        "worst_ids": [worst_id],
                        "reason": "missing_or_same_text",
                    }
                )
                continue
            pairs.append(
                {
                    "source_id": spec["source_id"],
                    "task_id": task_id,
                    "input": best["input"],
                    "best_review_id": best_id,
                    "best_system_id": best["system_id"],
                    "best_output_text": best["output_text"],
                    "best_scores": best["scores"],
                    "best_decision": best["decision"],
                    "worst_review_id": worst_id,
                    "worst_system_id": worst["system_id"],
                    "worst_output_text": worst["output_text"],
                    "worst_scores": worst["scores"],
                    "worst_decision": worst["decision"],
                }
            )
    return pairs, errors


def _holdout_inventory(paths):
    inputs = set()
    outputs = set()
    reports = []
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        reports.append({"ref": Path(path).name, "sha256": _sha256(path)})
        for case in payload.get("cases") or []:
            user_input = str(case.get("user_input") or "").strip()
            if user_input:
                inputs.add(user_input)
            for key in ("deterministic_reply", "final_reply"):
                text = str(case.get(key) or "").strip()
                if text:
                    outputs.add(text)
            for list_key in (
                "model_accepted_candidates",
                "model_rejected_candidates",
                "model_initial_rejected_candidates",
            ):
                for candidate in case.get(list_key) or []:
                    for key in ("candidate", "raw_candidate"):
                        text = str(candidate.get(key) or "").strip()
                        if text:
                            outputs.add(text)
    return {"inputs": inputs, "outputs": outputs, "reports": reports}


def _source_hashes_match(source_summaries, existing_report):
    expected = {
        row["source_id"]: row["hashes"] for row in existing_report.get("sources") or []
    }
    actual = {row["source_id"]: row["hashes"] for row in source_summaries}
    return actual == expected


def build_calibration_report(
    rows,
    source_summaries,
    *,
    source_hashes_match,
    missing_key_review_ids,
    holdout_input_overlaps,
    holdout_output_overlaps,
    holdout_reports,
    explicit_pairs,
    explicit_pair_errors,
    rater_count=1,
    inter_rater_reliability_available=False,
    population_sampling_design_available=False,
):
    tasks = defaultdict(list)
    for row in rows:
        tasks[(row["source_id"], row["task_id"])].append(row)
    system_counts = Counter(row["system_id"] for row in rows)
    decision_counts = Counter(row["decision"] for row in rows)
    category_counts = Counter(row["category"] for row in rows)
    programmatic_pass_systems = sorted(
        {row["system_id"] for row in rows if row["programmatic_pass"]}
    )
    programmatic_fail_systems = sorted(
        {row["system_id"] for row in rows if not row["programmatic_pass"]}
    )
    pass_identical_to_s0_identity = all(
        row["programmatic_pass"] == (row["system_id"] == S0_SYSTEM_ID)
        for row in rows
    )
    policy_rows = [row for row in rows if row["system_id"] == S0_SYSTEM_ID]
    policy_label_values = sorted({row["programmatic_pass"] for row in policy_rows})
    within_policy_pair_count = 0
    within_policy_multi_candidate_task_count = 0
    for task_rows in tasks.values():
        policy_texts = {
            row["output_text"]
            for row in task_rows
            if row["system_id"] == S0_SYSTEM_ID
        }
        if len(policy_texts) >= 2:
            within_policy_multi_candidate_task_count += 1
            within_policy_pair_count += len(policy_texts) * (len(policy_texts) - 1) // 2

    strict_yes = _classification_metrics(rows, lambda row: row["decision"] == "yes")
    acceptable = _classification_metrics(rows, lambda row: row["decision"] != "no")
    duplicate_summary = _duplicate_summary(rows)
    unique_candidate_text_count = sum(
        len({row["output_text"] for row in task_rows}) for task_rows in tasks.values()
    )
    integrity_gates = {
        "source_hashes_match_existing_evidence_report": source_hashes_match,
        "all_completed_rows_have_key_labels": not missing_key_review_ids,
        "all_source_joins_are_complete": all(
            row.get("missing_join_count") == 0 for row in source_summaries
        ),
        "every_completed_task_has_four_candidate_ratings": all(
            len(task_rows) == 4 for task_rows in tasks.values()
        ),
        "promotion_holdout_input_overlap_is_zero": not holdout_input_overlaps,
        "promotion_holdout_output_overlap_is_zero": not holdout_output_overlaps,
        "explicit_best_worst_pairs_have_no_errors": not explicit_pair_errors,
    }
    training_gates = {
        **integrity_gates,
        "within_policy_pair_count_is_positive": within_policy_pair_count > 0,
        "within_policy_programmatic_label_has_both_values": policy_label_values
        == [False, True],
        "programmatic_pass_is_not_identical_to_system_identity": not (
            pass_identical_to_s0_identity
        ),
        "exact_duplicate_human_decisions_are_consistent": duplicate_summary[
            "duplicate_decision_disagreement_group_count"
        ]
        == 0,
    }
    authorize_training = all(training_gates.values())
    population_claim_gates = {
        "training_data_gate_passed": authorize_training,
        "at_least_two_independent_raters_available": rater_count >= 2,
        "inter_rater_reliability_is_available": inter_rater_reliability_available,
        "population_sampling_design_is_available": population_sampling_design_available,
    }
    authorize_population_claim = all(population_claim_gates.values())
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_human_preference_calibration_v28",
        "method_references": list(METHOD_REFERENCES),
        "method": {
            "primary_label": "blinded human final decision",
            "cross_package_score_policy": (
                "V15 four-dimensional scores and V16 two-dimensional scores are summarized separately; "
                "they are never collapsed into one shared scalar."
            ),
            "automatic_comparison_policy": (
                "Programmatic pass versus human decisions is descriptive because candidate system identity "
                "is a measured confound."
            ),
            "training_policy": (
                "Preference training requires at least two distinct candidates from the same current policy "
                "for one prompt, within-policy label variation, source integrity, and zero promotion-holdout overlap."
            ),
        },
        "summary": {
            "source_count": len(source_summaries),
            "completed_task_count": len(tasks),
            "candidate_rating_count": len(rows),
            "unique_candidate_text_count_within_task": unique_candidate_text_count,
            "category_count": len(category_counts),
            "category_counts": dict(sorted(category_counts.items())),
            "system_counts": dict(sorted(system_counts.items())),
            "human_decision_counts": dict(sorted(decision_counts.items())),
            "programmatic_pass_count": sum(row["programmatic_pass"] for row in rows),
            "programmatic_fail_count": sum(not row["programmatic_pass"] for row in rows),
            "rater_count": rater_count,
        },
        "source_summaries": source_summaries,
        "holdout_evidence": {
            "reports": holdout_reports,
            "input_overlap_count": len(holdout_input_overlaps),
            "input_overlaps": sorted(holdout_input_overlaps),
            "output_overlap_count": len(holdout_output_overlaps),
            "output_overlaps": sorted(holdout_output_overlaps),
        },
        "cross_system_programmatic_calibration": {
            "strict_human_yes": strict_yes,
            "human_acceptable_yes_or_borderline": acceptable,
            "causal_interpretation_allowed": False,
        },
        "system_identity_confound": {
            "programmatic_pass_systems": programmatic_pass_systems,
            "programmatic_fail_systems": programmatic_fail_systems,
            "programmatic_pass_identical_to_s0_identity": pass_identical_to_s0_identity,
            "within_s0_programmatic_label_values": policy_label_values,
            "within_s0_human_decision_counts": dict(
                sorted(Counter(row["decision"] for row in policy_rows).items())
            ),
        },
        "within_policy_preference_evidence": {
            "policy_system_id": S0_SYSTEM_ID,
            "candidate_count": len(policy_rows),
            "task_count": len(
                {(row["source_id"], row["task_id"]) for row in policy_rows}
            ),
            "multi_candidate_task_count": within_policy_multi_candidate_task_count,
            "pair_count": within_policy_pair_count,
        },
        "duplicate_candidate_evidence": duplicate_summary,
        "package_specific_dimension_summaries": _dimension_summary(rows),
        "explicit_blind_preference_pairs": {
            "pair_count": len(explicit_pairs),
            "error_count": len(explicit_pair_errors),
            "errors": explicit_pair_errors,
            "pairs": explicit_pairs,
        },
        "integrity_gates": integrity_gates,
        "preference_training_gates": training_gates,
        "authorize_preference_training": authorize_training,
        "population_human_preference_claim_gates": population_claim_gates,
        "authorize_population_human_preference_claim": authorize_population_claim,
        "decision_zh": (
            "現有盲評足以證明自動 contract pass 不等於人類偏好，但不能直接拿來訓練 V28："
            "同一題只有一個 S0 右腦候選，within-policy 偏好對為 0，而且 programmatic pass "
            "與 S0 系統身分完全重合。正式右腦維持 V10。"
            if not authorize_training
            else "人類偏好資料通過同 policy、來源完整性與 holdout 隔離 gate，可進入凍結 V10 probe；尚未授權訓練或上線。"
        ),
        "next_evidence_step_zh": (
            "先在全新 development prompts 上由 V10 每題產生多個匿名候選，再收集同 policy 的成對偏好；"
            "promotion holdout 保持未觸碰。建立至少兩位獨立評分者後，才可主張一般人類偏好而非單一使用者偏好。"
        ),
        "research_boundary": (
            "This is a partial single-rater pilot. Cross-system confusion metrics are descriptive and confounded "
            "by candidate-system construction. The report authorizes neither preference training nor a population-level "
            "claim about human likeness."
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    confound = report["system_identity_confound"]
    strict = report["cross_system_programmatic_calibration"]["strict_human_yes"]
    acceptable = report["cross_system_programmatic_calibration"][
        "human_acceptable_yes_or_borderline"
    ]
    lines = [
        "# RightBrain V28 人類偏好校準",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "| 證據 | 結果 |",
        "|---|---:|",
        f"| 完成題目 | {summary['completed_task_count']} |",
        f"| 真人候選評分 | {summary['candidate_rating_count']} |",
        f"| 題內不重複回答 | {summary['unique_candidate_text_count_within_task']} |",
        f"| S0 同 policy 偏好對 | {report['within_policy_preference_evidence']['pair_count']} |",
        f"| 相同文字評分不一致 | {report['duplicate_candidate_evidence']['duplicate_rating_disagreement_group_count']}/{report['duplicate_candidate_evidence']['exact_duplicate_text_group_count']} |",
        f"| 相同文字最終判定矛盾 | {report['duplicate_candidate_evidence']['duplicate_decision_disagreement_group_count']}/{report['duplicate_candidate_evidence']['exact_duplicate_text_group_count']} |",
        f"| 可直接用於偏好訓練 | {'YES' if report['authorize_preference_training'] else 'NO'} |",
        "",
        "## 最重要的混淆變因",
        "",
        f"- programmatic pass 的系統：`{', '.join(confound['programmatic_pass_systems'])}`",
        f"- pass 是否完全等同 S0 身分：`{confound['programmatic_pass_identical_to_s0_identity']}`",
        f"- S0 內部自動標籤值：`{confound['within_s0_programmatic_label_values']}`",
        f"- S0 的真人最終判定：`{confound['within_s0_human_decision_counts']}`",
        "",
        "因此下表只能描述現有四種候選的關係，不能證明自動 gate 能預測任意右腦回答的人類偏好。",
        "",
        "| 人類標準 | TP | FP | TN | FN | precision | recall | balanced accuracy | MCC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| 嚴格 YES | {strict['true_positive']} | {strict['false_positive']} | {strict['true_negative']} | {strict['false_negative']} | {strict['precision']:.3f} | {strict['recall']:.3f} | {strict['balanced_accuracy']:.3f} | {strict['matthews_correlation']:.3f} |",
        f"| 可接受（YES+borderline） | {acceptable['true_positive']} | {acceptable['false_positive']} | {acceptable['true_negative']} | {acceptable['false_negative']} | {acceptable['precision']:.3f} | {acceptable['recall']:.3f} | {acceptable['balanced_accuracy']:.3f} | {acceptable['matthews_correlation']:.3f} |",
        "",
        "## 分批多維結果",
        "",
        "v15 與 v16 使用不同問題與量表，所以分開列出，不做跨量表總分。",
        "",
    ]
    for package in report["package_specific_dimension_summaries"]:
        fields = package["score_fields"]
        lines.extend(
            [
                f"### {package['source_id']}",
                "",
                "| system | n | " + " | ".join(fields) + " |",
                "|---|---:|" + "---:|" * len(fields),
            ]
        )
        for system in package["systems"]:
            values = [system["dimension_means"][field] for field in fields]
            lines.append(
                f"| {system['system_id']} | {system['candidate_count']} | "
                + " | ".join(f"{value:.3f}" for value in values)
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## 明示成對偏好",
            "",
            f"v16 共留下 `{report['explicit_blind_preference_pairs']['pair_count']}` 組明示 best/worst；這些是跨系統評價證據，不是同 policy 訓練對。",
            "",
            "| task | best system | worst system |",
            "|---|---|---|",
        ]
    )
    for pair in report["explicit_blind_preference_pairs"]["pairs"]:
        lines.append(
            f"| {pair['task_id']} | {pair['best_system_id']} | {pair['worst_system_id']} |"
        )
    lines.extend(["", "## Training gate", "", "| 條件 | 結果 |", "|---|---|"])
    for name, passed in report["preference_training_gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            report["next_evidence_step_zh"],
            "",
            "研究邊界：" + report["research_boundary"],
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--existing-evidence-report",
        default=HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
    )
    parser.add_argument(
        "--output-json",
        default=RIGHTBRAIN_HUMAN_PREFERENCE_CALIBRATION_V28_JSON_PATH,
    )
    parser.add_argument(
        "--output-md",
        default=RIGHTBRAIN_HUMAN_PREFERENCE_CALIBRATION_V28_MD_PATH,
    )
    args = parser.parse_args()
    rows, _, source_summaries = load_blind_evidence()
    key_map = _load_key_map(DEFAULT_SOURCE_SPECS)
    rows, missing_key_review_ids = _attach_automatic_labels(rows, key_map)
    explicit_pairs, explicit_pair_errors = _load_explicit_pairs(
        DEFAULT_SOURCE_SPECS, rows
    )
    existing_report = json.loads(
        Path(args.existing_evidence_report).read_text(encoding="utf-8")
    )
    holdout = _holdout_inventory(PROMOTION_HOLDOUT_REPORTS)
    blind_inputs = {row["input"].strip() for row in rows}
    blind_outputs = {row["output_text"].strip() for row in rows}
    report = build_calibration_report(
        rows,
        source_summaries,
        source_hashes_match=_source_hashes_match(source_summaries, existing_report),
        missing_key_review_ids=missing_key_review_ids,
        holdout_input_overlaps=blind_inputs & holdout["inputs"],
        holdout_output_overlaps=blind_outputs & holdout["outputs"],
        holdout_reports=holdout["reports"],
        explicit_pairs=explicit_pairs,
        explicit_pair_errors=explicit_pair_errors,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "completed_task_count": report["summary"]["completed_task_count"],
                "candidate_rating_count": report["summary"]["candidate_rating_count"],
                "within_policy_pair_count": report[
                    "within_policy_preference_evidence"
                ]["pair_count"],
                "system_identity_confound": report["system_identity_confound"][
                    "programmatic_pass_identical_to_s0_identity"
                ],
                "authorize_preference_training": report[
                    "authorize_preference_training"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
