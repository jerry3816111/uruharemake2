import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from compare_rightbrain_model_surface_holdouts import _validate_matched_runs
from project_paths import (
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH,
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH,
)
from rightbrain_language_quality import (
    has_awkward_surface,
    has_bad_language,
    has_japanese,
    has_response_plan_leak,
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _current_surface_issues(reply):
    reply = str(reply or "")
    issues = []
    if not has_japanese(reply) or has_bad_language(reply):
        issues.append("language_or_symbol_artifact")
    if has_awkward_surface(reply):
        issues.append("awkward_or_caregiver_surface")
    if has_response_plan_leak(reply):
        issues.append("japanese_response_plan_leak")
    return issues


def _initial_raw_candidates(case):
    values = []
    for row in case.get("model_initial_rejected_candidates") or []:
        values.append(str(row.get("raw_candidate") or ""))
    for row in case.get("model_accepted_candidates") or []:
        if row.get("source", "initial") == "initial":
            values.append(str(row.get("raw_candidate") or row.get("candidate") or ""))
    return Counter(values)


def _raw_candidate_control(baselines, promoted):
    mismatches = []
    compared_case_count = 0
    baseline_raw_candidate_count = 0
    candidate_raw_candidate_count = 0
    for baseline, candidate in zip(baselines, promoted):
        baseline_cases = _case_map(baseline)
        candidate_cases = _case_map(candidate)
        for case_id in sorted(set(baseline_cases) | set(candidate_cases)):
            compared_case_count += 1
            before = _initial_raw_candidates(baseline_cases.get(case_id, {}))
            after = _initial_raw_candidates(candidate_cases.get(case_id, {}))
            baseline_raw_candidate_count += sum(before.values())
            candidate_raw_candidate_count += sum(after.values())
            if before != after:
                mismatches.append({"seed": baseline.get("seed"), "case_id": case_id})
    expected_baseline_count = sum(
        int((report.get("summary") or {}).get("generated_candidate_count") or 0)
        for report in baselines
    )
    expected_candidate_count = sum(
        int((report.get("summary") or {}).get("generated_candidate_count") or 0)
        for report in promoted
    )
    fully_accounted = (
        baseline_raw_candidate_count == expected_baseline_count
        and candidate_raw_candidate_count == expected_candidate_count
    )
    return {
        "compared_case_count": compared_case_count,
        "identical_case_count": compared_case_count - len(mismatches),
        "baseline_raw_candidate_count": baseline_raw_candidate_count,
        "candidate_raw_candidate_count": candidate_raw_candidate_count,
        "expected_baseline_raw_candidate_count": expected_baseline_count,
        "expected_candidate_raw_candidate_count": expected_candidate_count,
        "fully_accounted": fully_accounted,
        "all_identical": not mismatches and compared_case_count > 0 and fully_accounted,
        "mismatches": mismatches,
    }


def _paired_surface_changes(baselines, promoted):
    rows = []
    for baseline, candidate in zip(baselines, promoted):
        baseline_cases = _case_map(baseline)
        candidate_cases = _case_map(candidate)
        for case_id in sorted(set(baseline_cases) & set(candidate_cases)):
            before_reply = str(baseline_cases[case_id].get("final_reply") or "")
            after_reply = str(candidate_cases[case_id].get("final_reply") or "")
            before_issues = _current_surface_issues(before_reply)
            after_issues = _current_surface_issues(after_reply)
            if before_issues == after_issues:
                continue
            rows.append(
                {
                    "seed": baseline.get("seed"),
                    "case_id": case_id,
                    "before_reply": before_reply,
                    "after_reply": after_reply,
                    "before_issues": before_issues,
                    "after_issues": after_issues,
                    "fixed": bool(before_issues and not after_issues),
                    "introduced": bool(after_issues and not before_issues),
                }
            )
    return rows


def _safe_case_surface_rate(cases):
    cases = list(cases or [])
    if not cases:
        return None
    passed = sum(not _current_surface_issues(row.get("final_reply")) for row in cases)
    return round(passed / len(cases), 4)


def _aggregate(reports):
    generated = sum(row["summary"]["generated_candidate_count"] for row in reports)
    accepted = sum(row["summary"]["accepted_candidate_count"] for row in reports)
    case_count = sum(row["summary"]["case_count"] for row in reports)
    selected = sum(row["summary"]["model_selected_case_count"] for row in reports)
    case_rows = [case for report in reports for case in report.get("cases") or []]
    current_surface_pass_count = sum(
        not _current_surface_issues(row.get("final_reply")) for row in case_rows
    )

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
        "rescored_final_surface_pass_rate": (
            round(current_surface_pass_count / len(case_rows), 4) if case_rows else None
        ),
        "rescored_final_surface_issue_count": len(case_rows) - current_surface_pass_count,
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


def _rejection_reason_deltas(baselines, promoted, *, family=False, runtime_checker_change=False):
    baseline_counts = _aggregate_rejection_reasons(baselines, family=family)
    promoted_counts = _aggregate_rejection_reasons(promoted, family=family)
    rows = []
    for reason in sorted(set(baseline_counts) | set(promoted_counts)):
        before = baseline_counts.get(reason, 0)
        after = promoted_counts.get(reason, 0)
        if before == after:
            continue
        if runtime_checker_change:
            direction = "new_detection" if after > before else "removed_detection"
        else:
            direction = "regressed" if after > before else "improved"
        rows.append(
            {
                "reason": reason,
                "baseline_count": before,
                "candidate_count": after,
                "delta": after - before,
                "direction": direction,
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
    if isinstance(curriculum, dict) and isinstance(curriculum.get("data_boundary"), dict):
        boundary = dict(curriculum["data_boundary"])
        diagnostic_only = bool(
            boundary.get("diagnostic_only")
            or boundary.get("holdout_case_overlap_count")
            or boundary.get("holdout_target_overlap_count")
        )
        boundary.setdefault("provided", True)
        boundary.setdefault("training_row_count", curriculum.get("curriculum_row_count", 0))
        boundary.setdefault("training_source_case_count", boundary.get("training_source_case_count", 0))
        boundary.setdefault("holdout_case_count", boundary.get("holdout_case_count", 0))
        boundary.setdefault("holdout_case_overlap_count", 0)
        boundary.setdefault("holdout_case_overlap_ids", [])
        boundary.setdefault("holdout_target_overlap_count", 0)
        boundary.setdefault("holdout_target_overlap_examples", [])
        boundary["diagnostic_only"] = diagnostic_only
        boundary.setdefault(
            "boundary_reason",
            (
                "Candidate training data overlaps the evaluated holdout case IDs or target replies. "
                "This comparison is useful for debugging but must not be used as promotion evidence."
            )
            if diagnostic_only
            else "No holdout case or target overlap was detected in the supplied curriculum report.",
        )
        return boundary

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
        seed_surface_changes = _paired_surface_changes([baseline], [candidate])
        seed_raw_control = _raw_candidate_control([baseline], [candidate])
        before_cases = baseline.get("cases") or []
        after_cases = candidate.get("cases") or []
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
                "baseline_rescored_final_surface_pass_rate": _safe_case_surface_rate(before_cases),
                "promoted_rescored_final_surface_pass_rate": _safe_case_surface_rate(after_cases),
                "fixed_final_surface_issue_count": sum(row["fixed"] for row in seed_surface_changes),
                "introduced_final_surface_issue_count": sum(
                    row["introduced"] for row in seed_surface_changes
                ),
                "raw_candidates_identical": seed_raw_control["all_identical"],
            }
        )

    baseline_aggregate = _aggregate(baselines)
    promoted_aggregate = _aggregate(promoted)
    raw_candidate_control = _raw_candidate_control(baselines, promoted)
    paired_surface_changes = _paired_surface_changes(baselines, promoted)
    fixed_surface_issue_count = sum(row["fixed"] for row in paired_surface_changes)
    introduced_surface_issue_count = sum(row["introduced"] for row in paired_surface_changes)
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
        and promoted_aggregate["rescored_final_surface_pass_rate"] == 1.0
    )
    runtime_shadow_safety_pass = (
        same_adapter_runtime_comparison
        and len(per_seed) >= 2
        and raw_candidate_control["all_identical"]
        and introduced_surface_issue_count == 0
        and quality_guard_pass
    )
    all_seed_noninferior = all(row["raw_candidate_acceptance_delta"] >= 0 for row in per_seed)
    all_seed_selection_noninferior = all(
        row["promoted_model_selected_case_count"] >= row["baseline_model_selected_case_count"]
        for row in per_seed
    )
    if same_adapter_runtime_comparison:
        metric_gate_pass = (
            len(per_seed) >= 2
            and raw_candidate_control["all_identical"]
            and fixed_surface_issue_count > 0
            and introduced_surface_issue_count == 0
            and quality_guard_pass
        )
    else:
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
                f"建議採用 runtime gate 改動：{len(per_seed)} 個 matched seeds 的 raw candidates 完全相同，"
                f"以同一版 checker 重評後，最終表面通過率由 "
                f"{baseline_aggregate['rescored_final_surface_pass_rate']:.1%} 提升至 "
                f"{promoted_aggregate['rescored_final_surface_pass_rate']:.1%}；"
                f"修正 {fixed_surface_issue_count} 個壞輸出且未新增壞輸出。"
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
    elif runtime_shadow_safety_pass and fixed_surface_issue_count == 0:
        decision_zh = (
            "本批 actual-model 樣本沒有命中待修正缺陷，因此不能單獨證明修復效果；"
            "但兩個 matched seeds 的 raw candidates 完全相同、未新增表面問題且最終品質維持 100%，"
            "可作為 runtime 安全非劣證據。"
        )
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
        "runtime_shadow_safety_pass": runtime_shadow_safety_pass,
        "quality_guard_pass": quality_guard_pass,
        "all_seed_noninferior": all_seed_noninferior,
        "all_seed_selection_noninferior": all_seed_selection_noninferior,
        "runtime_gate_evidence": {
            "raw_candidate_control": raw_candidate_control,
            "fixed_final_surface_issue_count": fixed_surface_issue_count,
            "introduced_final_surface_issue_count": introduced_surface_issue_count,
            "paired_surface_changes": paired_surface_changes,
        },
        "data_boundary": data_boundary,
        "aggregate": {
            "baseline": baseline_aggregate,
            "promoted": promoted_aggregate,
            "raw_candidate_acceptance_delta": acceptance_delta,
        },
        "per_seed": per_seed,
        "rejection_reason_deltas": {
            "exact": _rejection_reason_deltas(
                baselines,
                promoted,
                family=False,
                runtime_checker_change=same_adapter_runtime_comparison,
            ),
            "family": _rejection_reason_deltas(
                baselines,
                promoted,
                family=True,
                runtime_checker_change=same_adapter_runtime_comparison,
            ),
        },
        "case_diagnostics": _case_diagnostics(baselines, promoted),
        "decision_zh": decision_zh,
        "reason_delta_interpretation_zh": (
            "baseline 與 candidate 使用同一個 adapter，且本報告要求每題 raw candidates 完全相同。"
            "因此新增 rejection reason 代表 checker 新抓到的表面問題，不代表模型生成能力退步；"
            "是否採用改動由配對後的壞輸出修正數、零新增問題與最終品質防線共同決定。"
            if same_adapter_runtime_comparison
            else "baseline 與 candidate 使用不同 adapter，因此 rejection reason 增減主要反映候選模型輸出品質差異。"
        ),
        "research_boundary": (
            "此 gate 在相同 seed、相同候選數下進行配對比較；同 adapter 的 runtime checker 比較還要求"
            "每題 raw candidates 完全相同。它只證明已定義表面缺陷的攔截與受保護整合，"
            "不等同完整的人類自然度。若提供 curriculum report，會檢查 holdout overlap；有重疊時會阻止升版。"
        ),
    }


def write_markdown(report, output_path):
    before = report["aggregate"]["baseline"]
    after = report["aggregate"]["promoted"]
    same_adapter_runtime_gate = report.get("comparison_mode") == "same_adapter_runtime_gate_check"

    def display_direction(row):
        return row["direction"]

    mode_control_lines = (
        [
            f"- raw candidates identical: `{report['runtime_gate_evidence']['raw_candidate_control']['all_identical']}`",
            f"- raw candidates fully accounted: `{report['runtime_gate_evidence']['raw_candidate_control']['fully_accounted']}`",
        ]
        if same_adapter_runtime_gate
        else [f"- all seeds raw-acceptance non-inferior: `{report['all_seed_noninferior']}`"]
    )

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
        *mode_control_lines,
        f"- metric gate pass: `{report['metric_gate_pass']}`",
        f"- runtime shadow safety pass: `{report['runtime_shadow_safety_pass']}`",
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
        f"| 同版 checker 重評的表面通過率 | {before['rescored_final_surface_pass_rate']:.1%} | {after['rescored_final_surface_pass_rate']:.1%} |",
        "",
        "## Rejection Reason 解讀",
        "",
        report["reason_delta_interpretation_zh"],
        "",
        "## 各 Seed",
        "",
    ]
    if same_adapter_runtime_gate:
        lines.extend(
            [
                "| seed | raw 相同 | baseline surface | candidate surface | 修正 | 新增問題 |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for row in report["per_seed"]:
            lines.append(
                f"| {row['seed']} | {'yes' if row['raw_candidates_identical'] else 'no'} | "
                f"{row['baseline_rescored_final_surface_pass_rate']:.1%} | "
                f"{row['promoted_rescored_final_surface_pass_rate']:.1%} | "
                f"{row['fixed_final_surface_issue_count']} | "
                f"{row['introduced_final_surface_issue_count']} |"
            )
    else:
        lines.extend(
            [
                "| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in report["per_seed"]:
            lines.append(
                f"| {row['seed']} | {row['baseline_raw_candidate_acceptance_rate']:.1%} | "
                f"{row['promoted_raw_candidate_acceptance_rate']:.1%} | "
                f"{row['raw_candidate_acceptance_delta']:+.1%} | "
                f"{row['baseline_model_selected_case_count']} | "
                f"{row['promoted_model_selected_case_count']} |"
            )
    surface_changes = report["runtime_gate_evidence"]["paired_surface_changes"]
    if surface_changes:
        lines.extend(
            [
                "",
                "## 配對後的最終輸出變化",
                "",
                "| seed | case | before issues | after issues | before | after |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for row in surface_changes:
            lines.append(
                f"| {row['seed']} | {row['case_id']} | {', '.join(row['before_issues']) or '-'} | "
                f"{', '.join(row['after_issues']) or '-'} | {row['before_reply']} | {row['after_reply']} |"
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
