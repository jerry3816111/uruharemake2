#!/usr/bin/env python3
"""Build a compact same-policy human blind package from real V10 candidates."""

import argparse
import csv
import hashlib
import itertools
import json
import random
import re
import unicodedata
from copy import deepcopy
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    HUMAN_BLIND_DATA_DIR,
    REPORTS_DIR,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_V29_PACKAGE_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_V29_PACKAGE_REPORT_MD_PATH,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs


TZ = ZoneInfo("Asia/Tokyo")
FORMAL_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_SEED = 20260712
DEFAULT_INDEPENDENT_COMPARISONS = 10
DEFAULT_CONSISTENCY_REPEATS = 2
MIN_PAIR_DIVERSITY = 0.08
HUMAN_REVIEWABLE_REASON_NAMES = {
    "polite_tone_drift",
    "awkward_or_caregiver_surface",
    "formal_register_drift",
    "risk_overreaction",
    "benign_action_overreaction",
}


def _json_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text_key(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def _pair_diversity(left, right):
    return 1.0 - SequenceMatcher(None, _text_key(left), _text_key(right)).ratio()


def _candidate_id(case_id, seed, text):
    digest = hashlib.sha256(
        f"{case_id}\n{seed}\n{text}".encode("utf-8")
    ).hexdigest()[:16]
    return f"v29cand_{digest}"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _prior_human_output_texts():
    outputs = set()
    for path in Path(HUMAN_BLIND_DATA_DIR).glob("*_rating_sheet.csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                text = str(row.get("output_text") or "").strip()
                if text:
                    outputs.add(_text_key(text))
    return outputs


def _promotion_output_texts():
    outputs = set()
    for path in Path(REPORTS_DIR).glob(
        "rightbrain_plan_surface_boundary_holdout_c3*.json"
    ):
        report = _read_json(path)
        for row in report.get("cases") or []:
            for field in ("deterministic_reply", "final_reply"):
                text = str(row.get(field) or "").strip()
                if text:
                    outputs.add(_text_key(text))
            for field in (
                "model_accepted_candidates",
                "model_initial_rejected_candidates",
            ):
                for candidate in row.get(field) or []:
                    text = str(
                        candidate.get("raw_candidate")
                        or candidate.get("candidate")
                        or ""
                    ).strip()
                    if text:
                        outputs.add(_text_key(text))
    return outputs


def _max_chars(case):
    return int(case.get("logic", {}).get("constraints", {}).get("max_chars") or 88)


def _current_rejection_reasons(rightbrain, text, case):
    reasons = rightbrain._model_candidate_rejection_reasons(
        text,
        deepcopy(case["logic"]),
        _max_chars(case),
        user_input=case["user_input"],
    )
    for marker in case.get("forbidden_substrings") or []:
        if marker and marker in text:
            reasons.append("case_forbidden_surface_violation")
            break
    return list(dict.fromkeys(reasons))


def _human_reviewable_reason(reason):
    return (
        reason in HUMAN_REVIEWABLE_REASON_NAMES
        or str(reason).startswith("semantic_slots_missing:")
    )


def _validate_report(report):
    gates = report.get("candidate_collection_gates") or {}
    errors = []
    if report.get("adapter_ref") != FORMAL_ADAPTER:
        errors.append("not_formal_v10_adapter")
    if report.get("load_model") is not True:
        errors.append("model_not_loaded")
    if report.get("repair_enabled") is not False:
        errors.append("repair_not_disabled")
    if not report.get("adapter_model_sha256"):
        errors.append("missing_adapter_sha256")
    if not report.get("authorize_blind_package_build"):
        errors.append("candidate_collection_not_authorized")
    if gates and not all(gates.values()):
        errors.append("candidate_collection_gate_failed")
    return errors


def collect_human_eligible_candidates(
    candidate_reports,
    prior_output_texts=None,
    promotion_output_texts=None,
):
    """Re-evaluate raw model text with the current runtime contract."""
    from uruha_brain_mac import RightBrain

    cases = {case["id"]: case for case in case_inputs()}
    prior_output_texts = (
        _prior_human_output_texts()
        if prior_output_texts is None
        else set(prior_output_texts)
    )
    promotion_output_texts = (
        _promotion_output_texts()
        if promotion_output_texts is None
        else set(promotion_output_texts)
    )
    rightbrain = RightBrain(load_model=False)
    by_case = {case_id: [] for case_id in cases}
    audit_rows = []
    adapter_shas = set()

    for source_ref, report in candidate_reports:
        errors = _validate_report(report)
        if errors:
            raise ValueError(f"Invalid candidate report {source_ref}: {errors}")
        adapter_sha = report["adapter_model_sha256"]
        adapter_shas.add(adapter_sha)
        seed = int(report["seed"])
        for row in report.get("cases") or []:
            case_id = row.get("id")
            if case_id not in cases:
                continue
            raw_items = []
            for origin_field in (
                "model_accepted_candidates",
                "model_initial_rejected_candidates",
            ):
                for item in row.get(origin_field) or []:
                    raw_text = str(item.get("raw_candidate") or "").strip()
                    if raw_text:
                        raw_items.append((origin_field, raw_text))

            seen_in_row = set()
            for origin_field, text in raw_items:
                normalized = _text_key(text)
                if not normalized or normalized in seen_in_row:
                    continue
                seen_in_row.add(normalized)
                reasons = _current_rejection_reasons(rightbrain, text, cases[case_id])
                reviewable_reasons = [
                    reason for reason in reasons if _human_reviewable_reason(reason)
                ]
                hard_reasons = [
                    reason for reason in reasons if not _human_reviewable_reason(reason)
                ]
                prior_overlap = normalized in prior_output_texts
                promotion_overlap = normalized in promotion_output_texts
                candidate = {
                    "candidate_id": _candidate_id(case_id, seed, text),
                    "case_id": case_id,
                    "source_family": cases[case_id]["source_family"],
                    "category": cases[case_id]["category"],
                    "text": text,
                    "normalized_text_sha256": hashlib.sha256(
                        normalized.encode("utf-8")
                    ).hexdigest(),
                    "seed": seed,
                    "source_report": str(source_ref),
                    "source_field": origin_field,
                    "adapter_ref": report["adapter_ref"],
                    "adapter_model_sha256": adapter_sha,
                    "current_rejection_reasons": reasons,
                    "current_strict_pass": not reasons,
                    "human_reviewable_reasons": reviewable_reasons,
                    "hard_rejection_reasons": hard_reasons,
                    "hard_surface_pass": not hard_reasons,
                    "prior_human_output_overlap": prior_overlap,
                    "promotion_output_overlap": promotion_overlap,
                }
                audit_rows.append(candidate)
                if not hard_reasons and not prior_overlap and not promotion_overlap:
                    by_case[case_id].append(candidate)

    if len(adapter_shas) != 1:
        raise ValueError(f"Candidate reports use different adapter SHAs: {adapter_shas}")

    for case_id, candidates in by_case.items():
        unique = {}
        for candidate in candidates:
            unique.setdefault(candidate["normalized_text_sha256"], candidate)
        by_case[case_id] = list(unique.values())
    return by_case, audit_rows, next(iter(adapter_shas))


def _best_pair(candidates):
    pairs = []
    for left, right in itertools.combinations(candidates, 2):
        diversity = _pair_diversity(left["text"], right["text"])
        if diversity < MIN_PAIR_DIVERSITY:
            continue
        length_balance = min(len(left["text"]), len(right["text"])) / max(
            len(left["text"]), len(right["text"])
        )
        pairs.append((diversity + 0.05 * length_balance, diversity, left, right))
    if not pairs:
        return None
    _, diversity, left, right = max(
        pairs,
        key=lambda item: (item[0], item[2]["candidate_id"], item[3]["candidate_id"]),
    )
    return {"left": left, "right": right, "diversity": round(diversity, 6)}


def _select_case_pairs(by_case, independent_count):
    cases = {case["id"]: case for case in case_inputs()}
    pairable = []
    for case_id, candidates in by_case.items():
        pair = _best_pair(candidates)
        if pair:
            pairable.append(
                {
                    "case": cases[case_id],
                    "pair": pair,
                }
            )
    pairable.sort(
        key=lambda item: (-item["pair"]["diversity"], item["case"]["id"])
    )

    selected = []
    seen_categories = set()
    for item in pairable:
        category = item["case"]["category"]
        if category not in seen_categories:
            selected.append(item)
            seen_categories.add(category)
        if len(selected) == independent_count:
            return selected, pairable
    for item in pairable:
        if item not in selected:
            selected.append(item)
        if len(selected) == independent_count:
            break
    return selected, pairable


def _blind_entry(base_id, task_id, category, user_input, left, right):
    return {
        "comparison_id": base_id,
        "task_id": task_id,
        "category": category,
        "user_input": user_input,
        "response_a": left["text"],
        "response_b": right["text"],
    }


def _shuffle_with_spaced_repeats(entries, repeat_links, rng):
    minimum_gap = max(4, len(entries) // 3)
    shuffled = list(entries)
    for _ in range(1000):
        rng.shuffle(shuffled)
        positions = {
            entry["comparison_id"]: index
            for index, entry in enumerate(shuffled)
        }
        if all(
            abs(positions[repeat_id] - positions[base_id]) >= minimum_gap
            for repeat_id, base_id in repeat_links.items()
        ):
            return shuffled, minimum_gap
    raise ValueError("Unable to space consistency repeats without changing package size")


def build_blind_package(
    candidate_reports,
    seed=DEFAULT_SEED,
    independent_count=DEFAULT_INDEPENDENT_COMPARISONS,
    repeat_count=DEFAULT_CONSISTENCY_REPEATS,
    prior_output_texts=None,
    promotion_output_texts=None,
):
    by_case, audit_rows, adapter_sha = collect_human_eligible_candidates(
        candidate_reports,
        prior_output_texts=prior_output_texts,
        promotion_output_texts=promotion_output_texts,
    )
    selected, pairable = _select_case_pairs(by_case, independent_count)
    if len(selected) < independent_count:
        raise ValueError(
            f"Only {len(selected)} prompts have two distinct hard-surface-pass candidates; "
            f"need {independent_count}. Generate another seed instead of weakening the gate."
        )
    if repeat_count > len(selected):
        raise ValueError("repeat_count cannot exceed independent comparison count")

    rng = random.Random(seed)
    blind_entries = []
    key_entries = []
    for index, item in enumerate(selected, start=1):
        case = item["case"]
        left = item["pair"]["left"]
        right = item["pair"]["right"]
        if rng.random() < 0.5:
            left, right = right, left
        comparison_id = f"v29_base_{index:02d}"
        task_id = f"v29_task_{index:02d}"
        blind_entries.append(
            _blind_entry(
                comparison_id,
                task_id,
                case["category"],
                case["user_input"],
                left,
                right,
            )
        )
        key_entries.append(
            {
                "comparison_id": comparison_id,
                "task_id": task_id,
                "source_case_id": case["id"],
                "source_family": case["source_family"],
                "category": case["category"],
                "is_consistency_repeat": False,
                "repeat_of": "",
                "left_candidate": left,
                "right_candidate": right,
                "pair_diversity": item["pair"]["diversity"],
            }
        )

    repeat_indices = [round(i * (len(selected) - 1) / max(1, repeat_count - 1)) for i in range(repeat_count)]
    base_by_id = {entry["comparison_id"]: entry for entry in blind_entries}
    key_by_id = {entry["comparison_id"]: entry for entry in key_entries}
    repeat_links = {}
    for repeat_index, base_index in enumerate(repeat_indices, start=1):
        base_id = f"v29_base_{base_index + 1:02d}"
        base = base_by_id[base_id]
        base_key = key_by_id[base_id]
        comparison_id = f"v29_repeat_{repeat_index:02d}"
        repeat_links[comparison_id] = base_id
        blind_entries.append(
            {
                "comparison_id": comparison_id,
                "task_id": base["task_id"],
                "category": base["category"],
                "user_input": base["user_input"],
                "response_a": base["response_b"],
                "response_b": base["response_a"],
            }
        )
        key_entries.append(
            {
                "comparison_id": comparison_id,
                "task_id": base["task_id"],
                "source_case_id": base_key["source_case_id"],
                "source_family": base_key["source_family"],
                "category": base_key["category"],
                "is_consistency_repeat": True,
                "repeat_of": base_id,
                "left_candidate": base_key["right_candidate"],
                "right_candidate": base_key["left_candidate"],
                "pair_diversity": base_key["pair_diversity"],
            }
        )

    blind_entries, minimum_repeat_gap = _shuffle_with_spaced_repeats(
        blind_entries,
        repeat_links,
        rng,
    )
    for display_order, entry in enumerate(blind_entries, start=1):
        entry["display_order"] = display_order
    order_by_id = {
        entry["comparison_id"]: entry["display_order"] for entry in blind_entries
    }
    for entry in key_entries:
        entry["display_order"] = order_by_id[entry["comparison_id"]]
    key_entries.sort(key=lambda entry: entry["display_order"])
    repeat_display_gaps = [
        abs(order_by_id[repeat_id] - order_by_id[base_id])
        for repeat_id, base_id in repeat_links.items()
    ]

    package = {
        "schema_version": 1,
        "package_id": "rightbrain_on_policy_blind_v29",
        "purpose_zh": "比較同一正式右腦對同一題產生的兩個硬性表面安全候選；只判斷自然度、語意完整度與人格感。",
        "instructions_zh": [
            "先看使用者發話，再比較左右兩個回答。",
            "選比較像自然聊天、沒有漏掉重點、人格語氣較合理的一邊。程式沒有替你預先決定這三項。",
            "若兩邊同樣好選平手；若兩邊都不適合直接對人說，選兩邊都不好。",
        ],
        "choices": ["left_better", "tie", "right_better", "both_bad"],
        "comparison_count": len(blind_entries),
        "comparisons": blind_entries,
    }
    package["package_sha256"] = _json_sha256(package)

    for entry in key_entries:
        entry["package_sha256"] = package["package_sha256"]
        entry["adapter_ref"] = FORMAL_ADAPTER
        entry["adapter_model_sha256"] = adapter_sha

    all_candidate_rows = [
        candidate
        for entry in key_entries
        for candidate in (entry["left_candidate"], entry["right_candidate"])
    ]
    blind_forbidden_fields = {
        "adapter_ref",
        "adapter_model_sha256",
        "candidate_id",
        "current_rejection_reasons",
        "current_strict_pass",
        "hard_rejection_reasons",
        "hard_surface_pass",
        "is_consistency_repeat",
        "repeat_of",
        "source_case_id",
        "source_family",
    }
    package_text = json.dumps(package, ensure_ascii=False, sort_keys=True)
    blind_field_leaks = sorted(
        field for field in blind_forbidden_fields if f'"{field}"' in package_text
    )
    independent_keys = [entry for entry in key_entries if not entry["is_consistency_repeat"]]
    gates = {
        "exactly_requested_independent_comparisons": len(independent_keys)
        == independent_count,
        "exactly_requested_consistency_repeats": len(key_entries) - len(independent_keys)
        == repeat_count,
        "all_candidates_same_formal_policy": all(
            candidate["adapter_ref"] == FORMAL_ADAPTER
            and candidate["adapter_model_sha256"] == adapter_sha
            for candidate in all_candidate_rows
        ),
        "all_candidates_hard_surface_pass": all(
            candidate["hard_surface_pass"]
            and not candidate["hard_rejection_reasons"]
            for candidate in all_candidate_rows
        ),
        "all_pairs_are_distinct": all(
            _text_key(entry["left_candidate"]["text"])
            != _text_key(entry["right_candidate"]["text"])
            for entry in key_entries
        ),
        "exact_prior_human_output_overlap_zero": not any(
            candidate["prior_human_output_overlap"] for candidate in all_candidate_rows
        ),
        "exact_promotion_output_overlap_zero": not any(
            candidate["promotion_output_overlap"] for candidate in all_candidate_rows
        ),
        "blind_package_has_no_key_fields": not blind_field_leaks,
        "consistency_repeats_are_spaced": all(
            gap >= minimum_repeat_gap for gap in repeat_display_gaps
        ),
        "package_hash_is_bound": package["package_sha256"] == _json_sha256(
            {key: value for key, value in package.items() if key != "package_sha256"}
        ),
    }
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_on_policy_v29_same_policy_human_blind_package",
        "research_question": (
            "When hard contract failures and model identity are controlled, which V10 surface realization "
            "does a human prefer for naturalness, semantic completeness, and personality fit?"
        ),
        "candidate_report_count": len(candidate_reports),
        "candidate_report_refs": [str(source_ref) for source_ref, _ in candidate_reports],
        "package_build_seed": seed,
        "minimum_pair_diversity": MIN_PAIR_DIVERSITY,
        "adapter_ref": FORMAL_ADAPTER,
        "adapter_model_sha256": adapter_sha,
        "raw_candidate_audit_count": len(audit_rows),
        "raw_unique_candidate_count": len(
            {
                (candidate["case_id"], candidate["normalized_text_sha256"])
                for candidate in audit_rows
            }
        ),
        "current_strict_pass_candidate_count": sum(
            candidate["current_strict_pass"] for candidate in audit_rows
        ),
        "hard_surface_pass_candidate_count": sum(
            candidate["hard_surface_pass"] for candidate in audit_rows
        ),
        "eligible_candidate_count": sum(len(items) for items in by_case.values()),
        "pairable_case_count": len(pairable),
        "selected_independent_comparison_count": len(independent_keys),
        "consistency_repeat_count": len(key_entries) - len(independent_keys),
        "selected_category_count": len({entry["category"] for entry in independent_keys}),
        "selected_source_family_count": len(
            {entry["source_family"] for entry in independent_keys}
        ),
        "selected_case_ids": [entry["source_case_id"] for entry in independent_keys],
        "minimum_consistency_repeat_gap": minimum_repeat_gap,
        "consistency_repeat_display_gaps": repeat_display_gaps,
        "blind_field_leaks": blind_field_leaks,
        "gates": gates,
        "authorize_human_rating": all(gates.values()),
        "authorize_preference_training": False,
        "authorize_runtime_promotion": False,
        "package_sha256": package["package_sha256"],
        "research_boundary": (
            "This package can collect one-rater within-policy preferences. It cannot by itself authorize "
            "training, claim inter-rater reliability, or promote a runtime adapter."
        ),
    }
    return package, key_entries, report


def write_outputs(package, key_entries, report, package_path, key_path, report_json, report_md):
    for path in (package_path, key_path, report_json, report_md):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(package_path).write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(key_path).write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in key_entries),
        encoding="utf-8",
    )
    Path(report_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gate_rows = "\n".join(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in report["gates"].items()
    )
    markdown = f"""# 右腦 V29 同策略人類盲測封裝

## 結論

{f"可以進行 {report['selected_independent_comparison_count'] + report['consistency_repeat_count']} 次一鍵人類比較。" if report['authorize_human_rating'] else '封裝未通過 gate，不可交給人類評分。'}

## 為什麼需要人類

程式先排除中文、亂碼、內部計畫外洩、禁用記憶與其他可確定的硬失敗。語意 marker 只是近似規則，不會替人類決定答案；留下的左右回答都來自同一個正式 V10，人類只判斷自然度、語意完整度與人格感。

## 數量

- 真實生成候選：{report['raw_candidate_audit_count']}
- 題內文字去重後：{report['raw_unique_candidate_count']}
- 現行嚴格契約通過：{report['current_strict_pass_candidate_count']}
- 硬性表面安全通過：{report['hard_surface_pass_candidate_count']}
- 排除舊盲測與 promotion 重疊後可用：{report['eligible_candidate_count']}
- 可配成兩個不同硬性表面安全候選的題目：{report['pairable_case_count']}
- 獨立比較：{report['selected_independent_comparison_count']}
- 隱藏一致性重測：{report['consistency_repeat_count']}
- 類別覆蓋：{report['selected_category_count']}
- package build seed：{report['package_build_seed']}
- 候選報告：{', '.join(report['candidate_report_refs'])}

## Gate

| Gate | 結果 |
|---|---:|
{gate_rows}

## 證據邊界

本封裝只能取得單一評分者的同策略偏好；不能單獨授權訓練、主張評分者間信度，或升級正式 runtime adapter。
"""
    Path(report_md).write_text(markdown, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate-report",
        action="append",
        default=[],
        help="Repeat for multiple real V10 seed reports.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--independent-count", type=int, default=DEFAULT_INDEPENDENT_COMPARISONS)
    parser.add_argument("--repeat-count", type=int, default=DEFAULT_CONSISTENCY_REPEATS)
    parser.add_argument("--output-package", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH)
    parser.add_argument("--output-key", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
    parser.add_argument("--output-report-json", default=RIGHTBRAIN_ON_POLICY_V29_PACKAGE_REPORT_JSON_PATH)
    parser.add_argument("--output-report-md", default=RIGHTBRAIN_ON_POLICY_V29_PACKAGE_REPORT_MD_PATH)
    args = parser.parse_args()
    report_paths = args.candidate_report or [RIGHTBRAIN_ON_POLICY_V29_CANDIDATE_REPORT_JSON_PATH]
    candidate_reports = [(str(path), _read_json(path)) for path in report_paths]
    package, key_entries, report = build_blind_package(
        candidate_reports,
        seed=args.seed,
        independent_count=args.independent_count,
        repeat_count=args.repeat_count,
    )
    write_outputs(
        package,
        key_entries,
        report,
        args.output_package,
        args.output_key,
        args.output_report_json,
        args.output_report_md,
    )
    print(
        json.dumps(
            {
                "comparison_count": package["comparison_count"],
                "pairable_case_count": report["pairable_case_count"],
                "authorize_human_rating": report["authorize_human_rating"],
                "package_sha256": report["package_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["authorize_human_rating"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
