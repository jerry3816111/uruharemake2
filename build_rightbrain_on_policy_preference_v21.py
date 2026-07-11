#!/usr/bin/env python3
"""Build source-separated preference pairs from actual V10 candidate traces."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _evaluate_surface_quality, _quality_pass
from project_paths import (
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED2_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_MD_PATH,
)
from rightbrain_on_policy_dev_cases_v21 import case_inputs, validate_cases
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SOURCE_REPORTS = (
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED1_REPORT_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_DEV_V21_SEED2_REPORT_JSON_PATH,
)
PROMOTION_HOLDOUT_REPORTS = (
    "reports/rightbrain_plan_surface_boundary_holdout_c3.json",
    "reports/rightbrain_plan_surface_boundary_holdout_c3_seed20260709.json",
)
MIN_PAIR_COUNT = 24
MIN_SOURCE_FAMILY_COUNT = 6
MIN_STRICT_CHOSEN_CASE_COUNT = 8
MIN_FAILURE_FAMILY_COUNT = 4
EXPECTED_SOURCE_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
EXPECTED_REPORT_COUNT = 2
EXPECTED_CANDIDATES_PER_REPORT = 48


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _strict_quality_reasons(quality):
    reasons = []
    if not quality["language_clean"]:
        reasons.append("strict_language_clean_failed")
    if not quality["awkward_surface_free"]:
        reasons.append("strict_awkward_surface_failed")
    if not quality["response_plan_leak_free"]:
        reasons.append("strict_response_plan_leak")
    if quality["forbidden_surface_leak"]:
        reasons.append("strict_forbidden_surface_leak")
    if quality["generic_template_hit"]:
        reasons.append("strict_generic_template")
    if quality["required_marker_success"] is False:
        hit_count = sum(quality["required_marker_hits"])
        reasons.append(
            f"strict_semantic_slots_missing:{hit_count}/{len(quality['required_marker_hits'])}"
        )
    if quality["explicit_anchor_required"] and not quality["explicit_anchor_success"]:
        reasons.append("strict_explicit_anchor_missing")
    if quality["background_or_private_safe"] is False:
        reasons.append("strict_private_memory_leak")
    if quality["unrelated_settings_template"]:
        reasons.append("strict_unrelated_settings_template")
    return reasons


def _failure_family(reason):
    reason = str(reason or "")
    if ":" in reason:
        reason = reason.split(":", 1)[0]
    if reason.startswith("strict_"):
        reason = reason[len("strict_") :]
    aliases = {
        "ascii_symbol_artifact": "ascii_leak",
        "unexpected_ascii_leak": "ascii_leak",
        "cjk_language_leak": "language_pollution",
        "foreign_script_leak": "language_pollution",
        "language_clean_failed": "language_pollution",
        "missing_japanese_surface": "language_pollution",
        "nonstandard_cjk_surface": "language_pollution",
    }
    return aliases.get(reason, reason)


def _candidate_text(row):
    return str(row.get("candidate") or row.get("raw_candidate") or "").strip()


def _strict_candidate_pool(raw_case, case, include_audited_residue=True):
    strict_accepted = []
    strict_rejected = []
    for row in raw_case.get("model_accepted_candidates") or []:
        if row.get("source", "initial") != "initial":
            continue
        text = _candidate_text(row)
        if not text:
            continue
        quality = _evaluate_surface_quality(
            text,
            case,
            include_audited_residue=include_audited_residue,
        )
        reasons = _strict_quality_reasons(quality)
        record = {
            "text": text,
            "score": float(row.get("score") or 0.0),
            "quality": quality,
            "rejection_reasons": reasons,
            "candidate_origin": "v10_gate_accepted",
        }
        if _quality_pass(quality):
            strict_accepted.append(record)
        else:
            strict_rejected.append(record)
    for row in raw_case.get("model_initial_rejected_candidates") or []:
        text = str(row.get("raw_candidate") or "").strip()
        if not text:
            continue
        quality = _evaluate_surface_quality(
            text,
            case,
            include_audited_residue=include_audited_residue,
        )
        reasons = list(row.get("rejection_reasons") or [])
        reasons.extend(_strict_quality_reasons(quality))
        strict_rejected.append(
            {
                "text": text,
                "score": None,
                "quality": quality,
                "rejection_reasons": list(dict.fromkeys(reasons)),
                "candidate_origin": "v10_gate_rejected",
            }
        )
    return (
        sorted(strict_accepted, key=lambda row: (-row["score"], row["text"])),
        strict_rejected,
    )


def _prompt_messages(case):
    rightbrain = RightBrain(load_model=False)
    logic = json.loads(json.dumps(case["logic"], ensure_ascii=False))
    max_chars = logic.get("constraints", {}).get("max_chars", 88)
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


def _promotion_holdout_outputs(paths=PROMOTION_HOLDOUT_REPORTS):
    outputs = set()
    for path in paths:
        report = _load_json(path)
        for case in report.get("cases") or []:
            for key in ("deterministic_reply", "final_reply"):
                text = str(case.get(key) or "").strip()
                if text:
                    outputs.add(text)
    return outputs


def build_pairs(raw_reports, cases=None, promotion_holdout_outputs=None):
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
    report_case_coverage = [
        {
            "seed": report.get("seed"),
            "case_count": len(report.get("cases") or []),
            "case_ids_complete": {
                row.get("id") for row in report.get("cases") or []
            }
            == expected_case_ids,
            "model_loaded": report.get("load_model") is True,
            "generated_candidate_count": (report.get("summary") or {}).get(
                "generated_candidate_count"
            ),
        }
        for report in raw_reports
    ]
    rows = []
    seen_pairs = set()
    reason_counts = Counter()
    failure_family_counts = Counter()
    source_family_counts = Counter()
    strict_chosen_case_ids = set()
    skipped = Counter()
    holdout_chosen_overlap = set()

    for report in raw_reports:
        for raw_case in report.get("cases") or []:
            case = case_map.get(raw_case.get("id"))
            if case is None:
                raise ValueError(f"Unexpected V21 case in raw report: {raw_case.get('id')}")
            accepted, rejected = _strict_candidate_pool(
                raw_case,
                case,
                include_audited_residue=False,
            )
            if not accepted:
                skipped["case_without_strict_on_policy_chosen"] += 1
                continue
            chosen = accepted[0]
            strict_chosen_case_ids.add(case["id"])
            if chosen["text"] in holdout_outputs:
                holdout_chosen_overlap.add(chosen["text"])
                skipped["promotion_holdout_chosen_text_overlap"] += len(rejected)
                continue
            prompt_messages = _prompt_messages(case)
            for rejected_row in rejected:
                rejected_text = rejected_row["text"]
                pair_key = (json.dumps(prompt_messages, ensure_ascii=False, sort_keys=True), chosen["text"], rejected_text)
                if not rejected_text or rejected_text == chosen["text"] or pair_key in seen_pairs:
                    skipped["duplicate_or_empty_pair"] += 1
                    continue
                reasons = list(dict.fromkeys(rejected_row["rejection_reasons"]))
                if not reasons:
                    skipped["rejected_without_failure_reason"] += 1
                    continue
                seen_pairs.add(pair_key)
                chosen_quality = chosen["quality"]
                rejected_quality = rejected_row["quality"]
                source_family = case["source_family"]
                row = {
                    "id": f"rb_on_policy_preference_v21_{len(rows) + 1:04d}",
                    "source_case_id": f"v21_{source_family}",
                    "source_prompt_id": case["id"],
                    "source_seed": report["seed"],
                    "category": case["category"],
                    "training_role": "rightbrain_v10_on_policy_preference_v21",
                    "preference_rule": "strict_contract_pass_over_same_policy_failed_candidate",
                    "on_policy_adapter_ref": report["adapter_ref"],
                    "chosen_origin": "v10_strict_quality_accepted",
                    "rejected_origin": rejected_row["candidate_origin"],
                    "preference_failure_reasons": reasons,
                    "prompt_messages": prompt_messages,
                    "chosen": chosen["text"],
                    "rejected": rejected_text,
                    "pair_diagnostics": {
                        "required_group_count": len(chosen_quality["required_marker_hits"]),
                        "chosen_hit_count": sum(chosen_quality["required_marker_hits"]),
                        "rejected_hit_count": sum(rejected_quality["required_marker_hits"]),
                        "chosen_strict_quality_pass": True,
                        "rejected_strict_quality_pass": False,
                        "rejected_surface_failure_reasons": reasons,
                        "chosen_chars": len(chosen["text"]),
                        "rejected_chars": len(rejected_text),
                    },
                    "messages": [
                        *prompt_messages,
                        {"role": "assistant", "content": chosen["text"]},
                    ],
                }
                rows.append(row)
                reason_counts.update(reasons)
                failure_family_counts.update(_failure_family(reason) for reason in reasons)
                source_family_counts[source_family] += 1

    gates = {
        "source_adapter_is_current_v10": adapters == {EXPECTED_SOURCE_ADAPTER},
        "source_report_count_is_two": len(raw_reports) == EXPECTED_REPORT_COUNT,
        "every_source_report_covers_all_cases": all(
            row["case_ids_complete"] for row in report_case_coverage
        ),
        "every_source_report_loaded_real_model": all(
            row["model_loaded"] for row in report_case_coverage
        ),
        "every_source_report_has_48_candidates": all(
            row["generated_candidate_count"] == EXPECTED_CANDIDATES_PER_REPORT
            for row in report_case_coverage
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
        "promotion_holdout_chosen_text_overlap_is_zero": not holdout_chosen_overlap,
        "pair_count_at_least_24": len(rows) >= MIN_PAIR_COUNT,
        "source_family_count_at_least_6": len(source_family_counts) >= MIN_SOURCE_FAMILY_COUNT,
        "strict_chosen_case_count_at_least_8": (
            len(strict_chosen_case_ids) >= MIN_STRICT_CHOSEN_CASE_COUNT
        ),
        "failure_family_count_at_least_4": (
            len(failure_family_counts) >= MIN_FAILURE_FAMILY_COUNT
        ),
        "all_chosen_are_v10_on_policy": all(
            row["chosen_origin"] == "v10_strict_quality_accepted" for row in rows
        ),
        "all_rejected_are_v10_on_policy": all(
            row["rejected_origin"].startswith("v10_") for row in rows
        ),
    }
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_on_policy_preference_v21_dataset",
        "source_adapter_ref": next(iter(adapters)),
        "source_seeds": sorted(seeds),
        "raw_report_count": len(raw_reports),
        "source_report_evidence": report_case_coverage,
        "development_case_count": len(cases),
        "strict_chosen_case_count": len(strict_chosen_case_ids),
        "strict_chosen_case_ids": sorted(strict_chosen_case_ids),
        "pair_count": len(rows),
        "source_family_count": len(source_family_counts),
        "source_family_counts": dict(sorted(source_family_counts.items())),
        "failure_reason_counts": dict(reason_counts.most_common()),
        "failure_family_counts": dict(failure_family_counts.most_common()),
        "skipped_counts": dict(skipped),
        "promotion_holdout_chosen_text_overlap_count": len(holdout_chosen_overlap),
        "promotion_holdout_chosen_text_overlap_examples": sorted(holdout_chosen_overlap)[:5],
        "gates": gates,
        "authorize_preference_probe": all(gates.values()),
        "decision_zh": (
            "V21 on-policy 資料通過來源、多樣性與 holdout 邊界 gate，可進入訓練前偏好難度 probe。"
            if all(gates.values())
            else "V21 on-policy 資料尚未通過 gate，不得訓練。"
        ),
        "research_boundary": (
            "Both chosen and rejected completions are sampled from the current V10 policy. Chosen labels are "
            "automatic strict-contract labels, not human preference ratings. This authorizes only a pre-training "
            "preference probe, never adapter promotion."
        ),
    }
    return rows, summary


def write_markdown(summary, path):
    lines = [
        "# RightBrain V21 On-Policy Preference Dataset",
        "",
        "## 結論",
        "",
        summary["decision_zh"],
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| source adapter | {summary['source_adapter_ref']} |",
        f"| seeds | {summary['source_seeds']} |",
        f"| development cases | {summary['development_case_count']} |",
        f"| cases with strict chosen | {summary['strict_chosen_case_count']} |",
        f"| preference pairs | {summary['pair_count']} |",
        f"| source families | {summary['source_family_count']} |",
        f"| holdout chosen overlap | {summary['promotion_holdout_chosen_text_overlap_count']} |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in summary["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Failure Families",
            "",
            "| family | count |",
            "|---|---:|",
        ]
    )
    for name, count in summary["failure_family_counts"].items():
        lines.append(f"| {name} | {count} |")
    lines.extend(["", f"研究邊界：{summary['research_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", action="append")
    parser.add_argument("--output", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH)
    parser.add_argument("--report-json", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_JSON_PATH)
    parser.add_argument("--report-md", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_MD_PATH)
    args = parser.parse_args()
    source_paths = args.source_report or list(DEFAULT_SOURCE_REPORTS)
    rows, summary = build_pairs([_load_json(path) for path in source_paths])
    Path(args.output).write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, args.report_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["authorize_preference_probe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
