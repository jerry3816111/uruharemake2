#!/usr/bin/env python3
"""Build holdout-separated DPO pairs for RightBrain semantic realization."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_candidate_gate_contrast_curriculum_v16 import FAMILY_SPECS
from build_rightbrain_candidate_gate_curriculum_v15 import _holdout_boundary, _load_reports
from build_rightbrain_compact_slot_curriculum_v17 import _payload, _target_errors
from project_paths import (
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_JSON_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_MD_PATH,
)
from rightbrain_language_quality import has_bad_language, has_japanese, has_response_plan_leak
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


TZ = ZoneInfo("Asia/Tokyo")
CLAUSE_RE = re.compile(r"[^。！？!?、,]+[。！？!?、,]?")
DANGLING_CLAUSE_END_RE = re.compile(r"(?:決めつけず|分からないし|だし|けど|けれど|なら|から)[。]$")
DEFAULT_SOURCE_REPORTS = [
    "reports/rightbrain_plan_surface_boundary_holdout_c3.json",
    "reports/rightbrain_plan_surface_boundary_holdout_c3_seed20260709.json",
]


def _group_hits(text, groups):
    text = str(text or "")
    return [any(str(marker) in text for marker in group) for group in groups]


def _clean_join(parts):
    text = "".join(parts).strip(" 、,。")
    text = re.sub(r"^[でもけどがはをに、,]+", "", text).strip()
    text = re.sub(r"[、,]{2,}", "、", text)
    text = re.sub(r"。{2,}", "。", text)
    if text and text[-1] not in "。！？!?":
        text += "。"
    return text


def _omission_candidates(chosen, groups):
    parts = [match.group(0) for match in CLAUSE_RE.finditer(str(chosen or ""))]
    chosen_hits = _group_hits(chosen, groups)
    if not all(chosen_hits):
        return []
    candidates = []
    for index in range(len(parts)):
        rejected = _clean_join(parts[:index] + parts[index + 1 :])
        if not rejected or rejected == chosen or len(rejected) < 6:
            continue
        if DANGLING_CLAUSE_END_RE.search(rejected):
            continue
        rejected_hits = _group_hits(rejected, groups)
        if sum(rejected_hits) >= len(groups):
            continue
        if not has_japanese(rejected) or has_bad_language(rejected):
            continue
        if has_response_plan_leak(rejected):
            continue
        candidates.append(
            {
                "rejected": rejected,
                "removed_clause": parts[index],
                "chosen_hit_count": sum(chosen_hits),
                "rejected_hit_count": sum(rejected_hits),
                "omitted_group_indexes": [
                    group_index
                    for group_index, hit in enumerate(rejected_hits)
                    if not hit
                ],
            }
        )
    return candidates


def _pick_hard_omission(chosen, groups, variant_index):
    candidates = _omission_candidates(chosen, groups)
    if not candidates:
        raise ValueError(f"Could not produce a semantic omission for: {chosen}")
    hardest = max(row["rejected_hit_count"] for row in candidates)
    candidates = [row for row in candidates if row["rejected_hit_count"] == hardest]
    return candidates[(variant_index - 1) % len(candidates)]


def build_preference_pairs(specs=None, source_reports=None):
    specs = list(specs or FAMILY_SPECS)
    source_reports = list(source_reports or _load_reports(DEFAULT_SOURCE_REPORTS))
    rows = []
    category_counts = Counter()
    omitted_group_count_distribution = Counter()
    rejected_coverage_distribution = Counter()

    for spec in specs:
        payload = _payload(spec)
        prompt_messages = [
            {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
        ]
        for variant_index, chosen in enumerate(spec["targets"], start=1):
            errors = _target_errors(chosen, payload)
            if errors:
                raise ValueError(f"Invalid chosen target {spec['id']}#{variant_index}: {errors}")
            omission = _pick_hard_omission(
                chosen,
                payload["required_marker_groups"],
                variant_index,
            )
            source_case_id = spec["id"].replace("v16_", "v18_", 1)
            row = {
                "id": f"rb_semantic_preference_v18_{len(rows) + 1:04d}",
                "source_case_id": source_case_id,
                "category": spec["category"],
                "training_role": "rightbrain_semantic_completeness_dpo_v18",
                "preference_rule": "complete_required_marker_groups_over_natural_semantic_omission",
                "prompt_messages": prompt_messages,
                "chosen": chosen,
                "rejected": omission["rejected"],
                "pair_diagnostics": {
                    "required_group_count": len(payload["required_marker_groups"]),
                    **omission,
                },
                # Keep canonical messages so the existing holdout-overlap audit can inspect targets.
                "messages": [*prompt_messages, {"role": "assistant", "content": chosen}],
            }
            rows.append(row)
            category_counts[spec["category"]] += 1
            omitted_group_count_distribution[len(omission["omitted_group_indexes"])] += 1
            rejected_coverage_distribution[
                f"{omission['rejected_hit_count']}/{omission['chosen_hit_count']}"
            ] += 1

    boundary = _holdout_boundary(rows, source_reports)
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_semantic_preference_v18_dataset",
        "method": "offline DPO pair construction with V10 as the future reference policy",
        "pair_count": len(rows),
        "family_spec_count": len(specs),
        "category_counts": dict(sorted(category_counts.items())),
        "omitted_group_count_distribution": {
            str(key): value for key, value in sorted(omitted_group_count_distribution.items())
        },
        "rejected_coverage_distribution": dict(sorted(rejected_coverage_distribution.items())),
        "all_chosen_cover_every_required_group": all(
            row["pair_diagnostics"]["chosen_hit_count"]
            == row["pair_diagnostics"]["required_group_count"]
            for row in rows
        ),
        "all_rejected_omit_required_group": all(
            row["pair_diagnostics"]["rejected_hit_count"]
            < row["pair_diagnostics"]["required_group_count"]
            for row in rows
        ),
        "all_rejected_keep_clean_direct_surface": all(
            has_japanese(row["rejected"])
            and not has_bad_language(row["rejected"])
            and not has_response_plan_leak(row["rejected"])
            and not DANGLING_CLAUSE_END_RE.search(row["rejected"])
            for row in rows
        ),
        "length_profile_chars": {
            "chosen_mean": round(sum(len(row["chosen"]) for row in rows) / len(rows), 3),
            "rejected_mean": round(sum(len(row["rejected"]) for row in rows) / len(rows), 3),
            "mean_delta": round(
                sum(len(row["chosen"]) - len(row["rejected"]) for row in rows) / len(rows),
                3,
            ),
            "chosen_longer_pair_count": sum(
                len(row["chosen"]) > len(row["rejected"]) for row in rows
            ),
        },
        "source_reports": [Path(report["_source_path"]).name for report in source_reports],
        "data_boundary": boundary,
        "research_boundary": (
            "Pairs are deterministically constructed from holdout-separated synthetic contract families. "
            "They encode semantic completeness, not broad human preference, and cannot be evaluated on their source targets."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain v18 語意完整度偏好資料",
        "",
        "## 結論",
        "",
        "這份資料不再只示範正確答案，而是對同一份左腦契約建立「完整回答 > 自然但漏掉必要語意的回答」配對。",
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| preference pairs | {summary['pair_count']} |",
        f"| family specs | {summary['family_spec_count']} |",
        f"| chosen 全部完整 | {summary['all_chosen_cover_every_required_group']} |",
        f"| rejected 全部漏槽位 | {summary['all_rejected_omit_required_group']} |",
        f"| rejected 保持乾淨直接日文 | {summary['all_rejected_keep_clean_direct_surface']} |",
        f"| chosen 平均比 rejected 長 | {summary['length_profile_chars']['mean_delta']:.1f} chars |",
        f"| holdout case overlap | {summary['data_boundary']['holdout_case_overlap_count']} |",
        f"| holdout target overlap | {summary['data_boundary']['holdout_target_overlap_count']} |",
        "",
        "## Pair 範例",
        "",
        "| family | chosen | rejected | omitted groups |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['source_case_id']} | {row['chosen']} | {row['rejected']} | "
            f"{row['pair_diagnostics']['omitted_group_indexes']} |"
        )
    lines.extend(["", "## 研究邊界", "", summary["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH)
    parser.add_argument("--report-json", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_JSON_PATH)
    parser.add_argument("--report-md", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_REPORT_MD_PATH)
    args = parser.parse_args()

    rows, summary = build_preference_pairs()
    if not rows:
        raise RuntimeError("No v18 preference pairs were generated.")
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("v18 preference pairs overlap promotion holdout; refusing to write.")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, rows, args.report_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
