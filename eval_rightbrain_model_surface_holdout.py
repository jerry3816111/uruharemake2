#!/usr/bin/env python3
"""Evaluate model-blended RightBrain replies on the final-surface holdout."""

import argparse
import json
import os
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH,
    RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _selection_gap(selection):
    try:
        return round(float(selection["best_model_score"]) - float(selection["deterministic_score"]), 4)
    except (KeyError, TypeError, ValueError):
        return None


def _adapter_ref(adapter_path, base_only=False):
    if base_only:
        return "base_model_only"
    if adapter_path:
        return os.path.basename(os.path.abspath(adapter_path))
    return "configured_default"


def _set_model_env(adapter_path="", base_only=False, candidate_count=1, repair_enabled=False, repair_adapter_path=""):
    if base_only:
        os.environ["URUHA_RIGHT_BRAIN_ADAPTER_PATH"] = "base-only"
    elif adapter_path:
        os.environ["URUHA_RIGHT_BRAIN_ADAPTER_PATH"] = os.path.abspath(adapter_path)
    if repair_adapter_path:
        os.environ["URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH"] = os.path.abspath(repair_adapter_path)
    else:
        os.environ["URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH"] = ""
    os.environ["URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED"] = "1"
    os.environ["URUHA_RIGHT_BRAIN_MODEL_CANDIDATE_COUNT"] = str(max(1, int(candidate_count or 1)))
    os.environ["URUHA_RIGHT_BRAIN_MODEL_REPAIR_ENABLED"] = "1" if repair_enabled else "0"
    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"


def _case_inputs():
    from eval_rightbrain_audited_memory_surface import (
        MEMORY_BRIEF_CASES,
        MEMORY_CASE_INPUTS,
        SURFACE_HOLDOUT_CASES,
        _logic_for_memory_case,
    )

    cases = []
    for case in MEMORY_BRIEF_CASES:
        cases.append(
            {
                "id": case["id"],
                "category": "audited_memory",
                "user_input": MEMORY_CASE_INPUTS[case["id"]],
                "logic": _logic_for_memory_case(case),
                "memory_data": case.get("memory_data") or {},
                "psyche": case.get("psyche") or {"mood": 0, "trust": 50},
                "source_case": case,
            }
        )
    for case in SURFACE_HOLDOUT_CASES:
        logic = deepcopy(case["logic"])
        logic["required_marker_groups"] = deepcopy(case.get("required_marker_groups") or [])
        cases.append(
            {
                "id": case["id"],
                "category": case["category"],
                "user_input": case["user_input"],
                "logic": logic,
                "memory_data": {},
                "psyche": case.get("psyche") or {"mood": 0, "trust": 58},
                "source_case": case,
            }
        )
    return cases


def _evaluate_surface_quality(reply, case):
    from eval_rightbrain_audited_memory_surface import (
        _contains_anchor,
        _forbidden_hits,
        _generic_template_hits,
        _has_bad_language,
        _has_japanese,
        _normalized_reply,
        _required_group_hits,
    )
    from rightbrain_language_quality import has_awkward_surface, has_response_plan_leak

    source = case["source_case"]
    reply = str(reply or "")
    explicit_required = source.get("expected_policy") == "explicit_allowed"
    anchor_hit = _contains_anchor(reply, source) if case["category"] == "audited_memory" else False
    required_groups = source.get("required_marker_groups") or []
    required_hits = _required_group_hits(reply, required_groups)
    required_success = bool(required_hits and all(required_hits)) if required_groups else None
    background_private_safe = None
    if source.get("expected_policy") in {"background_only", "do_not_mention"}:
        background_private_safe = not _forbidden_hits(reply, source) and not anchor_hit
    forbidden_hits = _forbidden_hits(reply, source)
    template_hits = _generic_template_hits(reply)
    return {
        "reply": reply,
        "normalized_reply": _normalized_reply(reply),
        "explicit_anchor_required": explicit_required,
        "explicit_anchor_success": bool(anchor_hit) if explicit_required else None,
        "required_marker_groups": required_groups,
        "required_marker_hits": required_hits,
        "required_marker_success": required_success,
        "background_or_private_safe": background_private_safe,
        "forbidden_hits": forbidden_hits,
        "forbidden_surface_leak": bool(forbidden_hits),
        "generic_template_hits": template_hits,
        "generic_template_hit": bool(template_hits),
        "language_clean": _has_japanese(reply) and not _has_bad_language(reply),
        "awkward_surface_free": not has_awkward_surface(reply),
        "response_plan_leak_free": not has_response_plan_leak(reply),
        "unrelated_settings_template": "設定を調整" in reply,
    }


def _quality_pass(quality):
    checks = [
        quality["language_clean"],
        quality["awkward_surface_free"],
        quality["response_plan_leak_free"],
        not quality["forbidden_surface_leak"],
        not quality["generic_template_hit"],
        not quality["unrelated_settings_template"],
    ]
    if quality["explicit_anchor_required"]:
        checks.append(bool(quality["explicit_anchor_success"]))
    if quality["required_marker_success"] is not None:
        checks.append(bool(quality["required_marker_success"]))
    if quality["background_or_private_safe"] is not None:
        checks.append(bool(quality["background_or_private_safe"]))
    return all(checks)


def _summarize(rows, model_loaded):
    generated = sum(row["generated_candidate_count"] for row in rows)
    initial_accepted = sum(row["initial_accepted_candidate_count"] for row in rows)
    accepted = sum(row["accepted_candidate_count"] for row in rows)
    repair_attempts = sum(row["repair_attempt_count"] for row in rows)
    repair_accepted = sum(row["repair_accepted_count"] for row in rows)
    selected_rows = [row for row in rows if row["selected_source"] == "model"]
    fallback_rows = [row for row in rows if row["selected_source"] != "model"]
    available_not_selected = [
        row for row in rows if row["accepted_candidate_count"] > 0 and row["selected_source"] != "model"
    ]
    selection_gaps = [
        row["model_selection_score_gap"]
        for row in available_not_selected
        if row.get("model_selection_score_gap") is not None
    ]
    duplicate_count = len(rows) - len({row["final_quality"]["normalized_reply"] for row in rows})
    return {
        "case_count": len(rows),
        "model_loaded": bool(model_loaded),
        "generated_candidate_count": generated,
        "initial_accepted_candidate_count": initial_accepted,
        "accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": _safe_rate(initial_accepted, generated),
        "repair_attempt_count": repair_attempts,
        "repair_accepted_count": repair_accepted,
        "repair_success_rate": _safe_rate(repair_accepted, repair_attempts),
        "effective_candidate_acceptance_rate": _safe_rate(accepted, generated),
        "model_selected_case_count": len(selected_rows),
        "model_selected_case_rate": _safe_rate(len(selected_rows), len(rows)),
        "model_candidate_available_not_selected_count": len(available_not_selected),
        "model_candidate_available_not_selected_rate": _safe_rate(len(available_not_selected), len(rows)),
        "model_available_not_selected_avg_score_gap": (
            round(sum(selection_gaps) / len(selection_gaps), 4) if selection_gaps else None
        ),
        "deterministic_quality_pass_rate": _safe_rate(
            sum(row["deterministic_quality_pass"] for row in rows),
            len(rows),
        ),
        "final_quality_pass_rate": _safe_rate(sum(row["final_quality_pass"] for row in rows), len(rows)),
        "model_selected_quality_pass_rate": _safe_rate(
            sum(row["final_quality_pass"] for row in selected_rows),
            len(selected_rows),
        ),
        "fallback_quality_pass_rate": _safe_rate(
            sum(row["final_quality_pass"] for row in fallback_rows),
            len(fallback_rows),
        ),
        "final_language_clean_rate": _safe_rate(
            sum(row["final_quality"]["language_clean"] for row in rows),
            len(rows),
        ),
        "final_awkward_surface_free_rate": _safe_rate(
            sum(row["final_quality"]["awkward_surface_free"] for row in rows),
            len(rows),
        ),
        "final_response_plan_leak_free_rate": _safe_rate(
            sum(row["final_quality"]["response_plan_leak_free"] for row in rows),
            len(rows),
        ),
        "final_forbidden_surface_leak_rate": _safe_rate(
            sum(row["final_quality"]["forbidden_surface_leak"] for row in rows),
            len(rows),
        ),
        "final_generic_template_hit_rate": _safe_rate(
            sum(row["final_quality"]["generic_template_hit"] for row in rows),
            len(rows),
        ),
        "final_normalized_duplicate_reply_rate": _safe_rate(duplicate_count, len(rows)),
        "disabled_reason_counts": dict(Counter(row["model_disabled_reason"] for row in rows if row["model_disabled_reason"])),
        "rejection_reason_counts": dict(
            Counter(reason for row in rows for reason in row["model_rejection_reasons"])
        ),
    }


def build_report(
    load_model=False,
    adapter_path="",
    repair_adapter_path="",
    base_only=False,
    candidate_count=1,
    seed=20260624,
    repair_enabled=False,
):
    if load_model:
        _set_model_env(
            adapter_path=adapter_path,
            base_only=base_only,
            candidate_count=candidate_count,
            repair_enabled=repair_enabled,
            repair_adapter_path=repair_adapter_path,
        )
        import torch

        torch.manual_seed(seed)
        if torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)

    from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RightBrain

    started_at = time.time()
    cases = _case_inputs()
    deterministic_right = RightBrain(load_model=False)
    model_right = RightBrain(load_model=bool(load_model))
    model_right.model_blend_enabled = bool(load_model)
    model_right.model_candidate_count = max(1, int(candidate_count or 1))
    model_right.model_repair_enabled = bool(repair_enabled)
    model_ready_at = time.time()

    rows = []
    for case in cases:
        deterministic_right.history = []
        model_right.history = []
        deterministic_logic = deepcopy(case["logic"])
        model_logic = deepcopy(case["logic"])
        deterministic_reply = deterministic_right.speak(
            case["user_input"],
            deterministic_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        final_reply = model_right.speak(
            case["user_input"],
            model_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        trace = model_logic.get("model_surface_candidate_trace") or {}
        selection = model_logic.get("model_surface_selection") or {}
        model_rejection_reasons = [
            reason for item in trace.get("rejected") or [] for reason in item.get("rejection_reasons") or []
        ]
        deterministic_quality = _evaluate_surface_quality(deterministic_reply, case)
        final_quality = _evaluate_surface_quality(final_reply, case)
        selection_gap = _selection_gap(selection)
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "user_input": case["user_input"],
                "deterministic_reply": deterministic_reply,
                "final_reply": final_reply,
                "selected_source": selection.get("selected_source") or "deterministic",
                "model_surface_selection": selection,
                "model_selection_score_gap": selection_gap,
                "model_disabled_reason": trace.get("disabled_reason") or "",
                "generated_candidate_count": trace.get("initial_generated_count", 0),
                "initial_accepted_candidate_count": trace.get("initial_accepted_count", 0),
                "accepted_candidate_count": len(trace.get("accepted") or []),
                "repair_attempt_count": trace.get("repair_attempt_count", 0),
                "repair_accepted_count": trace.get("repair_accepted_count", 0),
                "model_accepted_candidates": trace.get("accepted") or [],
                "model_rejected_candidates": trace.get("rejected") or [],
                "model_initial_rejected_candidates": trace.get("initial_rejected") or [],
                "model_repair_attempts": trace.get("repairs") or [],
                "model_rejection_reasons": model_rejection_reasons,
                "deterministic_quality": deterministic_quality,
                "deterministic_quality_pass": _quality_pass(deterministic_quality),
                "final_quality": final_quality,
                "final_quality_pass": _quality_pass(final_quality),
            }
        )

    summary = _summarize(rows, model_loaded=load_model)
    completed_at = time.time()
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_model_blend_surface_holdout_eval",
        "research_boundary": (
            "This evaluates final-surface safety and quality for the same audited-memory/surface holdout. "
            "When load_model=false, it is a deterministic fallback baseline and does not claim raw model maturity. "
            "When load_model=true, raw candidates and optional one-pass contract repairs are measured separately "
            "through the same strict model candidate gate before selection."
        ),
        "adapter_ref": _adapter_ref(adapter_path, base_only=base_only),
        "repair_adapter_ref": _adapter_ref(repair_adapter_path) if repair_adapter_path else "",
        "load_model": bool(load_model),
        "seed": seed,
        "candidate_count_per_case": max(1, int(candidate_count or 1)),
        "repair_enabled": bool(repair_enabled),
        "runtime_contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "duration_seconds": round(completed_at - started_at, 3),
        "model_load_duration_seconds": round(model_ready_at - started_at, 3),
        "case_eval_duration_seconds": round(completed_at - model_ready_at, 3),
        "summary": summary,
        "cases": rows,
        "conclusion_zh": (
            "這份評測把 deterministic 右腦與 model-blend 右腦放在同一套 11 題 final-surface holdout 上。"
            "報告分開計算首次候選與一次修正後的有效候選，避免把 fallback 安全性或修正效果"
            "誤報成 raw model 成熟度。"
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# 右腦模型候選 Final-Surface Holdout",
        "",
        "這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 執行條件",
        "",
        f"- load_model: {report['load_model']}",
        f"- adapter_ref: {report['adapter_ref']}",
        f"- repair_adapter_ref: {report.get('repair_adapter_ref') or '(none)'}",
        f"- candidate_count_per_case: {report['candidate_count_per_case']}",
        f"- repair_enabled: {report['repair_enabled']}",
        f"- runtime_contract_version: {report['runtime_contract_version']}",
        f"- model_load_duration_seconds: {report['model_load_duration_seconds']}",
        f"- case_eval_duration_seconds: {report['case_eval_duration_seconds']}",
        "",
        "## 指標總表",
        "",
        "| 指標 | 結果 | 意義 |",
        "|---|---:|---|",
        f"| case_count | {summary['case_count']} | 同一套 final-surface holdout 題數 |",
        f"| raw_candidate_acceptance_rate | {_fmt_pct(summary['raw_candidate_acceptance_rate'])} | raw model 候選通過 gate 的比例 |",
        f"| repair_success_rate | {_fmt_pct(summary['repair_success_rate'])} | 首次失敗後，一次修正成功的比例 |",
        f"| effective_candidate_acceptance_rate | {_fmt_pct(summary['effective_candidate_acceptance_rate'])} | 加入一次修正後，候選最終可用比例 |",
        f"| model_selected_case_rate | {_fmt_pct(summary['model_selected_case_rate'])} | 模型候選實際接管最終回覆比例 |",
        f"| model_candidate_available_not_selected_rate | {_fmt_pct(summary['model_candidate_available_not_selected_rate'])} | 有可用模型候選但仍保留 deterministic 的比例 |",
        f"| model_available_not_selected_avg_score_gap | {summary['model_available_not_selected_avg_score_gap']} | 未接管時，最佳模型分數 - deterministic 分數；負數代表 deterministic 較強 |",
        f"| deterministic_quality_pass_rate | {_fmt_pct(summary['deterministic_quality_pass_rate'])} | deterministic baseline 品質通過率 |",
        f"| final_quality_pass_rate | {_fmt_pct(summary['final_quality_pass_rate'])} | 最終回覆品質通過率 |",
        f"| model_selected_quality_pass_rate | {_fmt_pct(summary['model_selected_quality_pass_rate'])} | 模型接管時的品質通過率 |",
        f"| final_language_clean_rate | {_fmt_pct(summary['final_language_clean_rate'])} | 最終回覆是否保持日文乾淨 |",
        f"| final_awkward_surface_free_rate | {_fmt_pct(summary['final_awkward_surface_free_rate'])} | 最終回覆是否沒有已稽核的不自然或照護者式句型 |",
        f"| final_response_plan_leak_free_rate | {_fmt_pct(summary['final_response_plan_leak_free_rate'])} | 最終回覆是否沒有把左腦回覆方針直接說給使用者 |",
        f"| final_generic_template_hit_rate | {_fmt_pct(summary['final_generic_template_hit_rate'])} | 最終回覆是否掉進固定模板；越低越好 |",
        f"| final_normalized_duplicate_reply_rate | {_fmt_pct(summary['final_normalized_duplicate_reply_rate'])} | 正規化後重複比例；越低越好 |",
        "",
        "## 個案表",
        "",
        "| case | 類型 | selected | initial/effective | score gap | repair accepted/attempted | final pass | final reply |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in report["cases"]:
        lines.append(
            "| {id} | {category} | {selected} | {initial}/{effective} | {gap} | {repair_acc}/{repair_try} | {passed} | {reply} |".format(
                id=row["id"],
                category=row["category"],
                selected=row["selected_source"],
                initial=row["initial_accepted_candidate_count"],
                effective=row["accepted_candidate_count"],
                gap=row.get("model_selection_score_gap"),
                repair_acc=row["repair_accepted_count"],
                repair_try=row["repair_attempt_count"],
                passed="yes" if row["final_quality_pass"] else "no",
                reply=row["final_reply"],
            )
        )
    if summary["disabled_reason_counts"]:
        lines.extend(["", "## Model Disabled Reasons", ""])
        for key, value in summary["disabled_reason_counts"].items():
            lines.append(f"- {key}: {value}")
    if summary["rejection_reason_counts"]:
        lines.extend(["", "## Model Rejection Reasons", ""])
        for key, value in summary["rejection_reason_counts"].items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-model", action="store_true")
    parser.add_argument("--adapter-path", default=os.getenv("URUHA_RIGHT_BRAIN_ADAPTER_PATH", ""))
    parser.add_argument("--repair-adapter-path", default=os.getenv("URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH", ""))
    parser.add_argument("--base-only", action="store_true")
    parser.add_argument("--candidate-count", type=int, default=1)
    parser.add_argument("--repair-enabled", action="store_true")
    parser.add_argument("--seed", type=int, default=20260624)
    parser.add_argument("--output-json", default=RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_MD_PATH)
    args = parser.parse_args()

    report = build_report(
        load_model=args.load_model,
        adapter_path=args.adapter_path,
        repair_adapter_path=args.repair_adapter_path,
        base_only=args.base_only,
        candidate_count=args.candidate_count,
        seed=args.seed,
        repair_enabled=args.repair_enabled,
    )
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success = (
        report["summary"]["deterministic_quality_pass_rate"] == 1.0
        and report["summary"]["final_quality_pass_rate"] == 1.0
        and report["summary"]["final_language_clean_rate"] == 1.0
        and report["summary"]["final_awkward_surface_free_rate"] == 1.0
        and report["summary"]["final_response_plan_leak_free_rate"] == 1.0
        and report["summary"]["final_forbidden_surface_leak_rate"] == 0.0
        and report["summary"]["final_generic_template_hit_rate"] == 0.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
