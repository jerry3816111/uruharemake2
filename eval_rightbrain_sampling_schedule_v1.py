#!/usr/bin/env python3
"""Compare RightBrain sampling schedules with one loaded model and matched seeds."""

import argparse
import json
import os
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import (
    _adapter_ref,
    _case_inputs,
    _evaluate_surface_quality,
    _quality_pass,
    _set_model_env,
)
from project_paths import (
    RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
REPORT_PATH = RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH
DEFAULT_SEED = 20260707
DEFAULT_CANDIDATE_COUNT = 3
MIN_ACCEPTANCE_GAIN = 0.10
MAX_DUPLICATE_RATE_INCREASE = 0.05

SCHEDULES = {
    "runtime_baseline": {
        "temperatures": [0.82, 0.96, 1.08],
        "top_p": [0.92, 0.95, 0.98],
        "top_k": [64, 96, 128],
        "repetition_penalties": [1.20, 1.26, 1.32],
    },
    "balanced": {
        "temperatures": [0.68, 0.78, 0.88],
        "top_p": [0.88, 0.91, 0.94],
        "top_k": [40, 56, 72],
        "repetition_penalties": [1.14, 1.18, 1.22],
    },
    "conservative": {
        "temperatures": [0.50, 0.62, 0.74],
        "top_p": [0.80, 0.85, 0.90],
        "top_k": [24, 32, 48],
        "repetition_penalties": [1.10, 1.14, 1.18],
    },
}

LANGUAGE_REASONS = {
    "cjk_language_leak",
    "nonstandard_cjk_surface",
    "unicode_replacement_character",
    "unexpected_ascii_leak",
}


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def validate_schedules(schedules, candidate_count=DEFAULT_CANDIDATE_COUNT):
    required = ("temperatures", "top_p", "top_k", "repetition_penalties")
    for name, schedule in schedules.items():
        for key in required:
            values = schedule.get(key)
            if not isinstance(values, list) or len(values) < candidate_count:
                raise ValueError(f"{name}.{key} must contain at least {candidate_count} values")
        if any(value <= 0 for value in schedule["temperatures"][:candidate_count]):
            raise ValueError(f"{name}.temperatures must be positive")
        if any(not 0 < value <= 1 for value in schedule["top_p"][:candidate_count]):
            raise ValueError(f"{name}.top_p must be in (0, 1]")
        if any(value <= 0 for value in schedule["top_k"][:candidate_count]):
            raise ValueError(f"{name}.top_k must be positive")
    return schedules


def _apply_schedule(runtime_module, schedule):
    runtime_module.RIGHT_BRAIN_SAMPLE_TEMPERATURES = list(schedule["temperatures"])
    runtime_module.RIGHT_BRAIN_SAMPLE_TOP_P = list(schedule["top_p"])
    runtime_module.RIGHT_BRAIN_SAMPLE_TOP_K = list(schedule["top_k"])
    runtime_module.RIGHT_BRAIN_SAMPLE_REPETITION_PENALTIES = list(schedule["repetition_penalties"])


def _reset_seed(torch_module, seed):
    torch_module.manual_seed(seed)
    if torch_module.backends.mps.is_available():
        torch_module.mps.manual_seed(seed)


def summarize_schedule(cases):
    generated = sum(case["generated_candidate_count"] for case in cases)
    accepted = sum(case["accepted_candidate_count"] for case in cases)
    covered = sum(case["accepted_candidate_count"] > 0 for case in cases)
    selected = sum(case["selected_source"] == "model" for case in cases)
    final_pass = sum(case["final_quality_pass"] for case in cases)
    language_clean = sum(case["final_quality"]["language_clean"] for case in cases)
    accepted_normalized = [
        candidate["normalized_reply"]
        for case in cases
        for candidate in case["accepted_candidates"]
        if candidate["normalized_reply"]
    ]
    duplicate_count = len(accepted_normalized) - len(set(accepted_normalized))
    rejected_candidates = [
        candidate
        for case in cases
        for candidate in case["rejected_candidates"]
    ]
    language_rejected = sum(
        bool(LANGUAGE_REASONS & set(candidate["rejection_reasons"]))
        for candidate in rejected_candidates
    )
    semantic_rejected = sum(
        any(reason.startswith("semantic_slots_missing:") for reason in candidate["rejection_reasons"])
        for candidate in rejected_candidates
    )
    return {
        "case_count": len(cases),
        "generated_candidate_count": generated,
        "accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": _safe_rate(accepted, generated),
        "candidate_case_coverage_count": covered,
        "candidate_case_coverage_rate": _safe_rate(covered, len(cases)),
        "model_selected_case_count": selected,
        "model_selected_case_rate": _safe_rate(selected, len(cases)),
        "final_quality_pass_rate": _safe_rate(final_pass, len(cases)),
        "final_language_clean_rate": _safe_rate(language_clean, len(cases)),
        "accepted_unique_reply_count": len(set(accepted_normalized)),
        "accepted_duplicate_count": duplicate_count,
        "accepted_duplicate_rate": _safe_rate(duplicate_count, len(accepted_normalized)),
        "language_rejected_candidate_count": language_rejected,
        "semantic_rejected_candidate_count": semantic_rejected,
        "rejection_reason_counts": dict(
            sorted(Counter(
                reason
                for candidate in rejected_candidates
                for reason in candidate["rejection_reasons"]
            ).items())
        ),
    }


def select_schedule(schedule_results, baseline_name="runtime_baseline"):
    baseline = schedule_results[baseline_name]["summary"]
    candidates = []
    comparisons = {}
    for name, result in schedule_results.items():
        summary = result["summary"]
        acceptance_gain = round(
            (summary["raw_candidate_acceptance_rate"] or 0.0)
            - (baseline["raw_candidate_acceptance_rate"] or 0.0),
            6,
        )
        duplicate_increase = round(
            (summary["accepted_duplicate_rate"] or 0.0)
            - (baseline["accepted_duplicate_rate"] or 0.0),
            6,
        )
        eligible = name != baseline_name and all(
            (
                acceptance_gain >= MIN_ACCEPTANCE_GAIN,
                summary["candidate_case_coverage_count"] >= baseline["candidate_case_coverage_count"],
                summary["model_selected_case_count"] >= baseline["model_selected_case_count"],
                summary["final_quality_pass_rate"] == 1.0,
                summary["final_language_clean_rate"] == 1.0,
                duplicate_increase <= MAX_DUPLICATE_RATE_INCREASE,
            )
        )
        comparisons[name] = {
            "acceptance_gain": acceptance_gain,
            "candidate_case_coverage_delta": (
                summary["candidate_case_coverage_count"] - baseline["candidate_case_coverage_count"]
            ),
            "model_selected_case_delta": (
                summary["model_selected_case_count"] - baseline["model_selected_case_count"]
            ),
            "accepted_duplicate_rate_increase": duplicate_increase,
            "eligible_for_runtime_validation": eligible,
        }
        if eligible:
            candidates.append((
                summary["candidate_case_coverage_count"],
                summary["accepted_candidate_count"],
                summary["model_selected_case_count"],
                -summary["semantic_rejected_candidate_count"],
                name,
            ))
    winner = max(candidates)[-1] if candidates else baseline_name
    return {
        "baseline": baseline_name,
        "recommended_schedule": winner,
        "independent_validation_recommended": winner != baseline_name,
        "comparisons": comparisons,
        "decision_rule": {
            "minimum_raw_acceptance_gain": MIN_ACCEPTANCE_GAIN,
            "minimum_case_coverage_delta": 0,
            "minimum_model_selected_case_delta": 0,
            "required_final_quality_pass_rate": 1.0,
            "required_final_language_clean_rate": 1.0,
            "maximum_duplicate_rate_increase": MAX_DUPLICATE_RATE_INCREASE,
        },
    }


def run_schedule(runtime_module, torch_module, model_right, deterministic_right, cases, name, schedule, seed):
    _apply_schedule(runtime_module, schedule)
    _reset_seed(torch_module, seed)
    started = time.time()
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
        accepted = []
        for candidate in trace.get("accepted") or []:
            text = str(candidate.get("candidate") or candidate.get("raw_candidate") or "")
            quality = _evaluate_surface_quality(text, case)
            accepted.append({
                "raw_candidate": candidate.get("raw_candidate") or "",
                "candidate": text,
                "normalized_reply": quality["normalized_reply"],
                "quality_pass": _quality_pass(quality),
            })
        rejected = [
            {
                "raw_candidate": candidate.get("raw_candidate") or "",
                "rejection_reasons": list(candidate.get("rejection_reasons") or []),
            }
            for candidate in trace.get("initial_rejected") or []
        ]
        final_quality = _evaluate_surface_quality(final_reply, case)
        rows.append({
            "id": case["id"],
            "category": case["category"],
            "user_input": case["user_input"],
            "deterministic_reply": deterministic_reply,
            "final_reply": final_reply,
            "selected_source": selection.get("selected_source") or "deterministic",
            "model_disabled_reason": trace.get("disabled_reason") or "",
            "generated_candidate_count": int(trace.get("initial_generated_count") or 0),
            "accepted_candidate_count": len(accepted),
            "accepted_candidates": accepted,
            "rejected_candidates": rejected,
            "final_quality": final_quality,
            "final_quality_pass": _quality_pass(final_quality),
        })
    return {
        "name": name,
        "schedule": schedule,
        "duration_seconds": round(time.time() - started, 3),
        "summary": summarize_schedule(rows),
        "cases": rows,
    }


def build_report(adapter_path, candidate_count=DEFAULT_CANDIDATE_COUNT, seed=DEFAULT_SEED):
    validate_schedules(SCHEDULES, candidate_count=candidate_count)
    _set_model_env(
        adapter_path=adapter_path,
        candidate_count=candidate_count,
        repair_enabled=False,
    )
    import torch
    import uruha_brain_mac as runtime_module

    model_started = time.time()
    deterministic_right = runtime_module.RightBrain(load_model=False)
    deterministic_right.model_blend_enabled = False
    model_right = runtime_module.RightBrain(load_model=True)
    model_right.model_blend_enabled = True
    model_right.model_candidate_count = candidate_count
    model_right.model_repair_enabled = False
    model_load_seconds = round(time.time() - model_started, 3)
    cases = _case_inputs()
    schedule_results = {}
    for name, schedule in SCHEDULES.items():
        schedule_results[name] = run_schedule(
            runtime_module,
            torch,
            model_right,
            deterministic_right,
            cases,
            name,
            schedule,
            seed,
        )
    decision = select_schedule(schedule_results)
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_sampling_schedule_ablation_v1",
        "base_model": os.getenv("URUHA_RIGHT_BRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        "adapter_ref": _adapter_ref(adapter_path),
        "seed": seed,
        "candidate_count_per_case": candidate_count,
        "case_count": len(cases),
        "model_load_seconds": model_load_seconds,
        "schedule_results": schedule_results,
        "decision": decision,
        "research_boundary": (
            "All schedules use one loaded model, the same cases, candidate count, and reset seed. "
            "This repeatedly used 11-case set is development evidence, not an untouched final holdout. "
            "A recommended schedule must still pass a separate runtime validation before becoming the default."
        ),
    }


def recompute_report(report):
    output = dict(report)
    output["decision"] = select_schedule(output["schedule_results"])
    output["decision_recomputed_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    return output


def write_markdown(report, path):
    lines = [
        "# RightBrain Sampling Schedule Ablation v1",
        "",
        "## 結論",
        "",
        (
            f"下一個獨立驗證候選是 `{report['decision']['recommended_schedule']}`；"
            f"是否值得進入獨立驗證：`{report['decision']['independent_validation_recommended']}`。"
        ),
        "",
        "## 固定條件",
        "",
        f"- model: `{report['base_model']}` + `{report['adapter_ref']}`",
        f"- seed: `{report['seed']}`",
        f"- cases: `{report['case_count']}`",
        f"- candidates per eligible case: `{report['candidate_count_per_case']}`",
        "- 每組 schedule 開始前重設相同 seed；模型只載入一次。",
        "",
        "## 結果",
        "",
        "| schedule | raw pass | covered cases | model selected | duplicate | language rejected | semantic rejected | final pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in report["schedule_results"].items():
        summary = result["summary"]
        lines.append(
            f"| {name} | {_fmt_pct(summary['raw_candidate_acceptance_rate'])} | "
            f"{summary['candidate_case_coverage_count']}/{summary['case_count']} | "
            f"{summary['model_selected_case_count']} | {_fmt_pct(summary['accepted_duplicate_rate'])} | "
            f"{summary['language_rejected_candidate_count']} | {summary['semantic_rejected_candidate_count']} | "
            f"{_fmt_pct(summary['final_quality_pass_rate'])} |"
        )
    lines.extend([
        "",
        "## 預先決策門檻",
        "",
        "| schedule | raw gain | coverage delta | selected delta | duplicate increase | eligible |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for name, comparison in report["decision"]["comparisons"].items():
        lines.append(
            f"| {name} | {_fmt_pct(comparison['acceptance_gain'])} | "
            f"{comparison['candidate_case_coverage_delta']} | {comparison['model_selected_case_delta']} | "
            f"{_fmt_pct(comparison['accepted_duplicate_rate_increase'])} | "
            f"{comparison['eligible_for_runtime_validation']} |"
        )
    lines.extend([
        "",
        "## 邊界",
        "",
        "- 這是生成策略消融，不改左腦答案、不加入題庫答案、不新增固定救援句。",
        "- 11 案已被多次使用，因此只能選出下一個待驗證設定，不能直接當最終泛化證明。",
        "- 若沒有設定通過預先門檻，runtime 維持原設定。",
        "- 自動候選另見 `rightbrain_sampling_schedule_naturalness_audit_v1.md`；自然度審查可否決部署。",
        "",
    ])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--adapter-path")
    source_group.add_argument("--recompute-from-report")
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_MD_PATH)
    args = parser.parse_args()
    if args.recompute_from_report:
        source_report = json.loads(Path(args.recompute_from_report).read_text(encoding="utf-8"))
        report = recompute_report(source_report)
    else:
        report = build_report(args.adapter_path, candidate_count=args.candidate_count, seed=args.seed)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({
        "summaries": {name: result["summary"] for name, result in report["schedule_results"].items()},
        "decision": report["decision"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
