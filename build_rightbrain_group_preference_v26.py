#!/usr/bin/env python3
"""Build prompt-level positive/negative response groups from V10 traces."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_on_policy_preference_v21 import (
    DEFAULT_SOURCE_REPORTS,
    EXPECTED_CANDIDATES_PER_REPORT,
    EXPECTED_REPORT_COUNT,
    EXPECTED_SOURCE_ADAPTER,
    _load_json,
    _promotion_holdout_outputs,
    _prompt_messages,
    _strict_candidate_pool,
)
from project_paths import (
    RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_JSON_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_MD_PATH,
)
from rightbrain_on_policy_dev_cases_v21 import case_inputs, validate_cases
from train_uruha_rightbrain_contract_v1 import _sha256


TZ = ZoneInfo("Asia/Tokyo")
MIN_GROUP_COUNT = 10
MIN_CANDIDATE_COUNT = 60
MIN_SOURCE_FAMILY_COUNT = 6
MIN_GROUP_SIZE = 4


def _merge_candidate(candidate_map, record, label, seed, conflicts):
    text = str(record.get("text") or "").strip()
    if not text:
        return
    existing = candidate_map.get(text)
    if existing is None:
        existing = {
            "text": text,
            "label": label,
            "source_seeds": set(),
            "origins": set(),
            "failure_reasons": set(),
        }
        candidate_map[text] = existing
    elif existing["label"] != label:
        conflicts.add(text)
        return
    existing["source_seeds"].add(seed)
    existing["origins"].add(record["candidate_origin"])
    existing["failure_reasons"].update(record.get("rejection_reasons") or [])


def _serialize_candidates(case_id, candidates, label):
    rows = []
    prefix = "p" if label == "positive" else "n"
    for index, row in enumerate(
        sorted(
            (item for item in candidates.values() if item["label"] == label),
            key=lambda item: item["text"],
        ),
        start=1,
    ):
        output = {
            "id": f"{case_id}_{prefix}{index:02d}",
            "text": row["text"],
            "source_seeds": sorted(row["source_seeds"]),
            "origins": sorted(row["origins"]),
        }
        if label == "negative":
            output["failure_reasons"] = sorted(row["failure_reasons"])
        rows.append(output)
    return rows


def build_groups(raw_reports=None, cases=None, promotion_holdout_outputs=None):
    raw_reports = list(raw_reports or (_load_json(path) for path in DEFAULT_SOURCE_REPORTS))
    cases = list(cases or case_inputs())
    validation = validate_cases(cases)
    if not validation["valid"]:
        raise ValueError(f"Invalid V21 cases: {validation['errors']}")
    case_map = {case["id"]: case for case in cases}
    holdout_outputs = set(
        promotion_holdout_outputs
        if promotion_holdout_outputs is not None
        else _promotion_holdout_outputs()
    )
    adapters = {report.get("adapter_ref") for report in raw_reports}
    seeds = [report.get("seed") for report in raw_reports]
    if len(adapters) != 1 or None in adapters:
        raise ValueError(f"Raw reports must use one explicit adapter: {adapters}")
    if len(seeds) != len(set(seeds)):
        raise ValueError(f"Raw report seeds must be unique: {seeds}")

    expected_case_ids = set(case_map)
    source_evidence = []
    raw_case_maps = []
    for report in raw_reports:
        rows = report.get("cases") or []
        case_rows = {row.get("id"): row for row in rows}
        raw_case_maps.append((report, case_rows))
        source_evidence.append(
            {
                "seed": report.get("seed"),
                "case_count": len(rows),
                "case_ids_complete": set(case_rows) == expected_case_ids,
                "model_loaded": report.get("load_model") is True,
                "generated_candidate_count": (report.get("summary") or {}).get(
                    "generated_candidate_count"
                ),
            }
        )

    groups = []
    skipped = Counter()
    source_family_counts = Counter()
    label_conflicts = set()
    holdout_candidate_overlaps = set()
    raw_unique_candidate_count = 0
    raw_positive_count = raw_negative_count = 0

    for case in cases:
        candidates = {}
        for report, raw_case_map in raw_case_maps:
            raw_case = raw_case_map.get(case["id"])
            if raw_case is None:
                continue
            accepted, rejected = _strict_candidate_pool(raw_case, case)
            for row in accepted:
                _merge_candidate(
                    candidates,
                    row,
                    "positive",
                    report["seed"],
                    label_conflicts,
                )
            for row in rejected:
                _merge_candidate(
                    candidates,
                    row,
                    "negative",
                    report["seed"],
                    label_conflicts,
                )

        raw_unique_candidate_count += len(candidates)
        raw_positive_count += sum(row["label"] == "positive" for row in candidates.values())
        raw_negative_count += sum(row["label"] == "negative" for row in candidates.values())
        for text in set(candidates) & holdout_outputs:
            holdout_candidate_overlaps.add(text)
            del candidates[text]

        positives = _serialize_candidates(case["id"], candidates, "positive")
        negatives = _serialize_candidates(case["id"], candidates, "negative")
        if not positives:
            skipped["group_without_positive"] += 1
            skipped["candidate_without_contrast"] += len(negatives)
            continue
        if not negatives:
            skipped["group_without_negative"] += 1
            skipped["candidate_without_contrast"] += len(positives)
            continue

        source_family = case["source_family"]
        source_family_counts[source_family] += 1
        groups.append(
            {
                "id": f"rb_group_preference_v26_{len(groups) + 1:04d}",
                "source_case_id": f"v21_{source_family}",
                "source_prompt_id": case["id"],
                "category": case["category"],
                "training_role": "rightbrain_v10_on_policy_group_preference_v26",
                "group_rule": "unordered_strict_contract_positive_vs_negative",
                "on_policy_adapter_ref": next(iter(adapters)),
                "prompt_messages": _prompt_messages(case),
                "positives": positives,
                "negatives": negatives,
            }
        )

    positive_count = sum(len(group["positives"]) for group in groups)
    negative_count = sum(len(group["negatives"]) for group in groups)
    group_sizes = [len(group["positives"]) + len(group["negatives"]) for group in groups]
    final_texts = {
        row["text"]
        for group in groups
        for row in [*group["positives"], *group["negatives"]]
    }
    gates = {
        "source_adapter_is_current_v10": adapters == {EXPECTED_SOURCE_ADAPTER},
        "source_report_count_is_two": len(raw_reports) == EXPECTED_REPORT_COUNT,
        "source_seeds_are_unique": len(seeds) == len(set(seeds)),
        "every_source_report_covers_all_cases": all(
            row["case_ids_complete"] for row in source_evidence
        ),
        "every_source_report_loaded_real_model": all(
            row["model_loaded"] for row in source_evidence
        ),
        "every_source_report_has_48_candidates": all(
            row["generated_candidate_count"] == EXPECTED_CANDIDATES_PER_REPORT
            for row in source_evidence
        ),
        "development_case_contract_valid": validation["valid"],
        "promotion_holdout_case_overlap_is_zero": validation[
            "promotion_holdout_case_overlap_count"
        ]
        == 0,
        "promotion_holdout_input_overlap_is_zero": validation[
            "promotion_holdout_input_overlap_count"
        ]
        == 0,
        "promotion_holdout_candidate_text_overlap_is_zero": not (
            final_texts & holdout_outputs
        ),
        "candidate_label_conflict_count_is_zero": not label_conflicts,
        "group_count_at_least_10": len(groups) >= MIN_GROUP_COUNT,
        "candidate_count_at_least_60": positive_count + negative_count
        >= MIN_CANDIDATE_COUNT,
        "source_family_count_at_least_6": len(source_family_counts)
        >= MIN_SOURCE_FAMILY_COUNT,
        "every_group_has_positive_and_negative": all(
            group["positives"] and group["negatives"] for group in groups
        ),
        "minimum_group_size_at_least_4": min(group_sizes, default=0)
        >= MIN_GROUP_SIZE,
        "all_candidates_are_v10_on_policy": all(
            origin.startswith("v10_")
            for group in groups
            for candidate in [*group["positives"], *group["negatives"]]
            for origin in candidate["origins"]
        ),
    }
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_group_preference_v26_dataset",
        "method": "cross_seed_unordered_positive_negative_response_groups",
        "method_references": [
            "https://proceedings.mlr.press/v267/gupta25c.html",
            "https://arxiv.org/abs/2604.15602",
        ],
        "source_adapter_ref": next(iter(adapters)),
        "source_seeds": sorted(seeds),
        "source_report_evidence": source_evidence,
        "development_case_count": len(cases),
        "raw_unique_candidate_count": raw_unique_candidate_count,
        "raw_positive_count": raw_positive_count,
        "raw_negative_count": raw_negative_count,
        "group_count": len(groups),
        "positive_candidate_count": positive_count,
        "negative_candidate_count": negative_count,
        "training_candidate_count": positive_count + negative_count,
        "group_size_min": min(group_sizes, default=0),
        "group_size_max": max(group_sizes, default=0),
        "group_size_mean": (
            sum(group_sizes) / len(group_sizes) if group_sizes else 0.0
        ),
        "source_family_count": len(source_family_counts),
        "source_family_counts": dict(sorted(source_family_counts.items())),
        "skipped_counts": dict(skipped),
        "label_conflict_count": len(label_conflicts),
        "label_conflict_examples": sorted(label_conflicts)[:5],
        "excluded_promotion_holdout_candidate_count": len(
            holdout_candidate_overlaps
        ),
        "excluded_promotion_holdout_candidate_examples": sorted(
            holdout_candidate_overlaps
        )[:5],
        "gates": gates,
        "authorize_group_probe": all(gates.values()),
        "decision_zh": (
            "V10 真實候選已形成來源隔離的多回答群組，可進入凍結 V10 的訓練前群組 probe。"
            if all(gates.values())
            else "群組資料未通過來源或多樣性 gate，禁止載入模型與訓練。"
        ),
        "research_boundary": (
            "Responses are grouped by automatic strict-contract pass/fail labels from the current V10 policy. "
            "Multiple positives are intentionally unordered so training does not force one canonical reply. "
            "These labels measure contract realization, not broad human preference."
        ),
    }
    return groups, summary


def write_markdown(summary, path):
    lines = [
        "# RightBrain V26 多回答群組資料",
        "",
        "## 結論",
        "",
        summary["decision_zh"],
        "",
        "| 指標 | 數量 |",
        "|---|---:|",
        f"| 原始不重複回答 | {summary['raw_unique_candidate_count']} |",
        f"| 可訓練情境群組 | {summary['group_count']} |",
        f"| 合格回答 | {summary['positive_candidate_count']} |",
        f"| 失敗回答 | {summary['negative_candidate_count']} |",
        f"| 可訓練回答總數 | {summary['training_candidate_count']} |",
        f"| 每組回答數 | {summary['group_size_min']}–{summary['group_size_max']} |",
        f"| 來源能力家族 | {summary['source_family_count']} |",
        "",
        "同一情境可以有多個合格說法；正集合與負集合內部都不指定唯一排名。",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in summary["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", "研究邊界：" + summary["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", action="append", dest="source_reports")
    parser.add_argument("--output-dataset", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_MD_PATH)
    args = parser.parse_args()
    source_paths = args.source_reports or list(DEFAULT_SOURCE_REPORTS)
    groups, summary = build_groups([_load_json(path) for path in source_paths])
    Path(args.output_dataset).write_text(
        json.dumps(groups, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary["dataset_ref"] = Path(args.output_dataset).name
    summary["dataset_sha256"] = _sha256(args.output_dataset)
    summary["source_reports"] = [
        {"ref": Path(path).name, "sha256": _sha256(path)} for path in source_paths
    ]
    Path(args.output_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, args.output_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["authorize_group_probe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
