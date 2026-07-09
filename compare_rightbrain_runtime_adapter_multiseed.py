import argparse
import json
from datetime import datetime
from pathlib import Path

from compare_rightbrain_model_surface_holdouts import _validate_matched_runs
from project_paths import (
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH,
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH,
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _aggregate(reports):
    generated = sum(row["summary"]["generated_candidate_count"] for row in reports)
    accepted = sum(row["summary"]["accepted_candidate_count"] for row in reports)
    case_count = sum(row["summary"]["case_count"] for row in reports)
    selected = sum(row["summary"]["model_selected_case_count"] for row in reports)

    def weighted_rate(metric):
        numerator = sum(row["summary"][metric] * row["summary"]["case_count"] for row in reports)
        return round(numerator / case_count, 4) if case_count else None

    return {
        "run_count": len(reports),
        "case_count": case_count,
        "generated_candidate_count": generated,
        "accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": round(accepted / generated, 4) if generated else None,
        "model_selected_case_count": selected,
        "model_selected_case_rate": round(selected / case_count, 4) if case_count else None,
        "final_quality_pass_rate": weighted_rate("final_quality_pass_rate"),
        "final_language_clean_rate": weighted_rate("final_language_clean_rate"),
        "final_forbidden_surface_leak_rate": weighted_rate("final_forbidden_surface_leak_rate"),
        "final_generic_template_hit_rate": weighted_rate("final_generic_template_hit_rate"),
        "case_eval_duration_seconds": round(sum(row.get("case_eval_duration_seconds", 0.0) for row in reports), 3),
    }


def _case_map(report):
    return {row["id"]: row for row in report.get("cases") or []}


def _count_reasons(rows):
    counts = {}
    for row in rows:
        for reason in row.get("model_rejection_reasons") or []:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def _reason_family(reason):
    reason = str(reason or "")
    if reason.startswith("semantic_slots_missing:"):
        return "semantic_slots_missing"
    return reason


def _aggregate_rejection_reasons(reports, *, family=False):
    counts = {}
    for report in reports:
        reason_counts = (report.get("summary") or {}).get("rejection_reason_counts") or {}
        if not reason_counts:
            reason_counts = {}
            for row in report.get("cases") or []:
                for reason in row.get("model_rejection_reasons") or []:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for reason, count in reason_counts.items():
            key = _reason_family(reason) if family else str(reason)
            counts[key] = counts.get(key, 0) + int(count or 0)
    return counts


def _rejection_reason_deltas(baselines, promoted, *, family=False):
    baseline_counts = _aggregate_rejection_reasons(baselines, family=family)
    promoted_counts = _aggregate_rejection_reasons(promoted, family=family)
    rows = []
    for reason in sorted(set(baseline_counts) | set(promoted_counts)):
        before = baseline_counts.get(reason, 0)
        after = promoted_counts.get(reason, 0)
        if before == after:
            continue
        rows.append(
            {
                "reason": reason,
                "baseline_count": before,
                "candidate_count": after,
                "delta": after - before,
                "direction": "regressed" if after > before else "improved",
            }
        )
    return sorted(rows, key=lambda row: (-abs(row["delta"]), row["reason"]))


def _case_diagnostics(baselines, promoted):
    baseline_by_case = {}
    promoted_by_case = {}
    for report in baselines:
        for case_id, row in _case_map(report).items():
            baseline_by_case.setdefault(case_id, []).append(row)
    for report in promoted:
        for case_id, row in _case_map(report).items():
            promoted_by_case.setdefault(case_id, []).append(row)

    rows = []
    for case_id in sorted(set(baseline_by_case) | set(promoted_by_case)):
        baseline_rows = baseline_by_case.get(case_id, [])
        promoted_rows = promoted_by_case.get(case_id, [])
        baseline_accepted = sum(row.get("accepted_candidate_count", 0) for row in baseline_rows)
        promoted_accepted = sum(row.get("accepted_candidate_count", 0) for row in promoted_rows)
        baseline_selected = sum(1 for row in baseline_rows if row.get("selected_source") == "model")
        promoted_selected = sum(1 for row in promoted_rows if row.get("selected_source") == "model")
        baseline_reasons = _count_reasons(baseline_rows)
        promoted_reasons = _count_reasons(promoted_rows)
        if (
            baseline_accepted == promoted_accepted
            and baseline_selected == promoted_selected
            and baseline_reasons == promoted_reasons
        ):
            continue
        rows.append(
            {
                "id": case_id,
                "category": (promoted_rows or baseline_rows)[0].get("category", ""),
                "baseline_accepted_candidate_count": baseline_accepted,
                "candidate_accepted_candidate_count": promoted_accepted,
                "accepted_candidate_delta": promoted_accepted - baseline_accepted,
                "baseline_model_selected_seed_count": baseline_selected,
                "candidate_model_selected_seed_count": promoted_selected,
                "model_selected_seed_delta": promoted_selected - baseline_selected,
                "baseline_rejection_reason_counts": baseline_reasons,
                "candidate_rejection_reason_counts": promoted_reasons,
                "new_rejection_reasons": sorted(set(promoted_reasons) - set(baseline_reasons)),
                "resolved_rejection_reasons": sorted(set(baseline_reasons) - set(promoted_reasons)),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["accepted_candidate_delta"],
            row["model_selected_seed_delta"],
            row["id"],
        ),
    )


def _curriculum_rows(curriculum):
    if not curriculum:
        return []
    if isinstance(curriculum, list):
        return curriculum
    if isinstance(curriculum, dict):
        rows = curriculum.get("rows")
        return rows if isinstance(rows, list) else []
    return []


def _curriculum_boundary(curriculum, reports):
    rows = _curriculum_rows(curriculum)
    if not rows:
        return {
            "provided": bool(curriculum),
            "training_row_count": 0,
            "diagnostic_only": False,
            "holdout_case_overlap_count": 0,
            "holdout_target_overlap_count": 0,
        }

    holdout_cases = {}
    holdout_targets = set()
    for report in reports:
        for row in report.get("cases") or []:
            case_id = str(row.get("id") or "")
            if not case_id:
                continue
            holdout_cases[case_id] = row
            for key in ("deterministic_reply", "final_reply"):
                text = str(row.get(key) or "").strip()
                if text:
                    holdout_targets.add((case_id, text))

    training_case_ids = {str(row.get("source_case_id") or "") for row in rows if row.get("source_case_id")}
    training_targets = set()
    for row in rows:
        case_id = str(row.get("source_case_id") or "")
        messages = row.get("messages") or []
        if case_id and messages:
            target = str((messages[-1] or {}).get("content") or "").strip()
            if target:
                training_targets.add((case_id, target))

    case_overlap = sorted(training_case_ids & set(holdout_cases))
    target_overlap = sorted(training_targets & holdout_targets)
    return {
        "provided": True,
        "training_row_count": len(rows),
        "training_source_case_count": len(training_case_ids),
        "holdout_case_count": len(holdout_cases),
        "holdout_case_overlap_count": len(case_overlap),
        "holdout_case_overlap_ids": case_overlap,
        "holdout_target_overlap_count": len(target_overlap),
        "holdout_target_overlap_examples": [
            {"case_id": case_id, "target": target} for case_id, target in target_overlap[:8]
        ],
        "diagnostic_only": bool(case_overlap or target_overlap),
        "boundary_reason": (
            "Candidate training data overlaps the evaluated holdout case IDs or target replies. "
            "This comparison is useful for debugging but must not be used as promotion evidence."
        )
        if case_overlap or target_overlap
        else "No holdout case or target overlap was detected in the supplied curriculum.",
    }


def build_report(baselines, promoted, curriculum=None):
    if not baselines or len(baselines) != len(promoted):
        raise ValueError("baseline and promoted reports must have the same non-zero count")

    baseline_adapter = baselines[0].get("adapter_ref")
    promoted_adapter = promoted[0].get("adapter_ref")
    same_adapter_runtime_comparison = baseline_adapter == promoted_adapter
    candidate_count = baselines[0].get("candidate_count_per_case")
    seen_seeds = set()
    per_seed = []
    for baseline, candidate in zip(baselines, promoted):
        _validate_matched_runs(baseline, candidate)
        if baseline.get("adapter_ref") != baseline_adapter:
            raise ValueError("baseline adapter changed across seeds")
        if candidate.get("adapter_ref") != promoted_adapter:
            raise ValueError("promoted adapter changed across seeds")
        if baseline.get("candidate_count_per_case") != candidate_count:
            raise ValueError("candidate count changed across seeds")
        seed = baseline.get("seed")
        if seed in seen_seeds:
            raise ValueError(f"duplicate seed: {seed}")
        seen_seeds.add(seed)
        before = baseline["summary"]
        after = candidate["summary"]
        per_seed.append(
            {
                "seed": seed,
                "baseline_raw_candidate_acceptance_rate": before["raw_candidate_acceptance_rate"],
                "promoted_raw_candidate_acceptance_rate": after["raw_candidate_acceptance_rate"],
                "raw_candidate_acceptance_delta": round(
                    after["raw_candidate_acceptance_rate"] - before["raw_candidate_acceptance_rate"],
                    4,
                ),
                "baseline_model_selected_case_count": before["model_selected_case_count"],
                "promoted_model_selected_case_count": after["model_selected_case_count"],
                "baseline_final_quality_pass_rate": before["final_quality_pass_rate"],
                "promoted_final_quality_pass_rate": after["final_quality_pass_rate"],
            }
        )

    baseline_aggregate = _aggregate(baselines)
    promoted_aggregate = _aggregate(promoted)
    acceptance_delta = round(
        promoted_aggregate["raw_candidate_acceptance_rate"]
        - baseline_aggregate["raw_candidate_acceptance_rate"],
        4,
    )
    quality_guard_pass = (
        promoted_aggregate["final_quality_pass_rate"] == 1.0
        and promoted_aggregate["final_language_clean_rate"] == 1.0
        and promoted_aggregate["final_forbidden_surface_leak_rate"] == 0.0
        and promoted_aggregate["final_generic_template_hit_rate"] == 0.0
    )
    all_seed_noninferior = all(row["raw_candidate_acceptance_delta"] >= 0 for row in per_seed)
    metric_gate_pass = (
        len(per_seed) >= 2
        and acceptance_delta > 0
        and all_seed_noninferior
        and promoted_aggregate["model_selected_case_count"] >= baseline_aggregate["model_selected_case_count"]
        and quality_guard_pass
    )
    data_boundary = _curriculum_boundary(curriculum, baselines + promoted)
    promotion_recommended = metric_gate_pass and not data_boundary["diagnostic_only"]
    if promotion_recommended:
        selected_before = baseline_aggregate["model_selected_case_count"]
        selected_after = promoted_aggregate["model_selected_case_count"]
        selected_phrase = (
            f"由 {selected_before} 增至 {selected_after}"
            if selected_after > selected_before
            else f"維持 {selected_after}"
        )
        if same_adapter_runtime_comparison:
            decision_zh = (
                f"建議採用 runtime gate 改動：{len(per_seed)} 個 matched seeds 合計 raw 接受率由 "
                f"{baseline_aggregate['raw_candidate_acceptance_rate']:.1%} 提升至 "
                f"{promoted_aggregate['raw_candidate_acceptance_rate']:.1%}，模型接管數{selected_phrase}，"
                "且最終品質防線維持 100%。"
            )
        else:
            decision_zh = (
                f"建議升版：{len(per_seed)} 個 matched seeds 合計 raw 接受率由 "
                f"{baseline_aggregate['raw_candidate_acceptance_rate']:.1%} 提升至 "
                f"{promoted_aggregate['raw_candidate_acceptance_rate']:.1%}，模型接管數{selected_phrase}，"
                "且最終品質防線維持 100%。"
            )
    elif data_boundary["diagnostic_only"]:
        decision_zh = (
            "不建議升版：這次比較含有訓練資料與 holdout case/target 重疊，只能作為 diagnostic/dev 證據；"
            "即使分數上升也不能當成可上線 promotion evidence。"
        )
        if not metric_gate_pass:
            decision_zh += "此外，多 seed 數字本身也未同時通過候選可靠度、接管數與最終品質門檻。"
    else:
        decision_zh = "不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。"

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "rightbrain_runtime_adapter_multiseed_promotion_gate",
        "comparison_mode": (
            "same_adapter_runtime_gate_check"
            if same_adapter_runtime_comparison
            else "adapter_promotion_gate"
        ),
        "baseline_adapter": baseline_adapter,
        "promoted_adapter": promoted_adapter,
        "candidate_count_per_case": candidate_count,
        "seeds": sorted(seen_seeds),
        "promotion_recommended": promotion_recommended,
        "metric_gate_pass": metric_gate_pass,
        "quality_guard_pass": quality_guard_pass,
        "all_seed_noninferior": all_seed_noninferior,
        "data_boundary": data_boundary,
        "aggregate": {
            "baseline": baseline_aggregate,
            "promoted": promoted_aggregate,
            "raw_candidate_acceptance_delta": acceptance_delta,
        },
        "per_seed": per_seed,
        "rejection_reason_deltas": {
            "exact": _rejection_reason_deltas(baselines, promoted, family=False),
            "family": _rejection_reason_deltas(baselines, promoted, family=True),
        },
        "case_diagnostics": _case_diagnostics(baselines, promoted),
        "decision_zh": decision_zh,
        "reason_delta_interpretation_zh": (
            "baseline 與 candidate 使用同一個 adapter，因此 rejection reason 的增加可能代表 runtime checker "
            "更嚴格抓出原本漏標的污染，而不是模型本身退步；升版仍必須看候選接受率、接管數與最終品質。"
            if same_adapter_runtime_comparison
            else "baseline 與 candidate 使用不同 adapter，因此 rejection reason 增減主要反映候選模型輸出品質差異。"
        ),
        "research_boundary": (
            "This gate compares adapters under matched seeds and runtime candidate count. "
            "It measures model candidate reliability and guarded integration, not human naturalness. "
            "When a curriculum is supplied, holdout overlap is reported and blocks promotion."
        ),
    }


def write_markdown(report, output_path):
    before = report["aggregate"]["baseline"]
    after = report["aggregate"]["promoted"]
    same_adapter_runtime_gate = report.get("comparison_mode") == "same_adapter_runtime_gate_check"

    def display_direction(row):
        if (
            same_adapter_runtime_gate
            and row.get("reason") == "nonstandard_cjk_surface"
            and int(row.get("delta") or 0) > 0
        ):
            return "stricter_detection"
        return row["direction"]

    lines = [
        "# RightBrain Runtime Adapter Multi-seed Promotion Gate",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "## 控制變因",
        "",
        f"- baseline adapter: `{report['baseline_adapter']}`",
        f"- candidate adapter: `{report['promoted_adapter']}`",
        f"- comparison mode: `{report.get('comparison_mode', 'adapter_promotion_gate')}`",
        f"- seeds: `{report['seeds']}`",
        f"- candidates per case: `{report['candidate_count_per_case']}`",
        f"- all seeds non-inferior: `{report['all_seed_noninferior']}`",
        f"- metric gate pass: `{report['metric_gate_pass']}`",
        f"- final quality guard: `{report['quality_guard_pass']}`",
        f"- diagnostic only: `{report['data_boundary']['diagnostic_only']}`",
        "",
        "## 合計結果",
        "",
        "| 指標 | baseline adapter | candidate adapter |",
        "|---|---:|---:|",
        f"| raw 候選接受 | {before['accepted_candidate_count']}/{before['generated_candidate_count']} ({before['raw_candidate_acceptance_rate']:.1%}) | {after['accepted_candidate_count']}/{after['generated_candidate_count']} ({after['raw_candidate_acceptance_rate']:.1%}) |",
        f"| 模型實際接管 | {before['model_selected_case_count']}/{before['case_count']} | {after['model_selected_case_count']}/{after['case_count']} |",
        f"| 最終品質通過率 | {before['final_quality_pass_rate']:.1%} | {after['final_quality_pass_rate']:.1%} |",
        "",
        "## Rejection Reason 解讀",
        "",
        report["reason_delta_interpretation_zh"],
        "",
        "## 各 Seed",
        "",
        "| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["per_seed"]:
        lines.append(
            f"| {row['seed']} | {row['baseline_raw_candidate_acceptance_rate']:.1%} | "
            f"{row['promoted_raw_candidate_acceptance_rate']:.1%} | "
            f"{row['raw_candidate_acceptance_delta']:+.1%} | "
            f"{row['baseline_model_selected_case_count']} | "
            f"{row['promoted_model_selected_case_count']} |"
        )
    data_boundary = report["data_boundary"]
    if data_boundary.get("provided"):
        lines.extend(
            [
                "",
                "## 資料邊界",
                "",
                "| 指標 | 值 |",
                "|---|---:|",
                f"| training rows | {data_boundary['training_row_count']} |",
                f"| holdout case overlap | {data_boundary['holdout_case_overlap_count']} |",
                f"| holdout target overlap | {data_boundary['holdout_target_overlap_count']} |",
                "",
                data_boundary["boundary_reason"],
            ]
        )
    family_deltas = report.get("rejection_reason_deltas", {}).get("family") or []
    if family_deltas:
        lines.extend(
            [
                "",
                "## Rejection Reason Family Delta",
                "",
                "| family | baseline count | candidate count | delta | direction |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for row in family_deltas:
            lines.append(
                f"| {row['reason']} | {row['baseline_count']} | {row['candidate_count']} | "
                f"{row['delta']:+d} | {display_direction(row)} |"
            )
    exact_deltas = report.get("rejection_reason_deltas", {}).get("exact") or []
    if exact_deltas:
        lines.extend(
            [
                "",
                "## Rejection Reason Exact Delta",
                "",
                "| reason | baseline count | candidate count | delta | direction |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for row in exact_deltas[:16]:
            lines.append(
                f"| {row['reason']} | {row['baseline_count']} | {row['candidate_count']} | "
                f"{row['delta']:+d} | {display_direction(row)} |"
            )
    diagnostics = report.get("case_diagnostics") or []
    if diagnostics:
        lines.extend(
            [
                "",
                "## Case-level Regression Diagnostics",
                "",
                "| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |",
                "|---|---|---:|---:|---|---|",
            ]
        )
        for row in diagnostics[:12]:
            lines.append(
                f"| {row['id']} | {row['category']} | {row['accepted_candidate_delta']:+d} | "
                f"{row['model_selected_seed_delta']:+d} | {', '.join(row['new_rejection_reasons']) or '-'} | "
                f"{', '.join(row['resolved_rejection_reasons']) or '-'} |"
            )
    lines.extend(["", f"研究邊界：{report['research_boundary']}", ""])
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-json", action="append", required=True)
    parser.add_argument("--promoted-json", action="append", required=True)
    parser.add_argument("--curriculum-json", default="")
    parser.add_argument("--output-json", default=RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH)
    args = parser.parse_args()

    curriculum = _load_json(args.curriculum_json) if args.curriculum_json else None
    report = build_report(
        [_load_json(path) for path in args.baseline_json],
        [_load_json(path) for path in args.promoted_json],
        curriculum=curriculum,
    )
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["promotion_recommended"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
