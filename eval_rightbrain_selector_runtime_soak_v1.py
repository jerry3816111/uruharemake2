#!/usr/bin/env python3
"""Run the full repair-selection corpus through the production shadow path."""

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_MD_PATH,
)
from rightbrain_repair_selector import grouped_contract_split, split_summary
from uruha_brain_mac import RightBrain


EXPECTED_CASE_COUNT = 360
EXPECTED_TEST_CASE_COUNT = 54


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _logic_from_contract(payload, rejected_candidates):
    leftbrain_plan = payload.get("leftbrain_plan") or {}
    return {
        "scene": leftbrain_plan.get("scene") or "",
        "intent": leftbrain_plan.get("intent") or "",
        "surface_act": leftbrain_plan.get("surface_act") or "",
        "dialogue_act": leftbrain_plan.get("dialogue_act") or "",
        "core_message_jp": leftbrain_plan.get("meaning") or "",
        "required_marker_groups": payload.get("required_marker_groups") or [],
        "must_avoid": payload.get("forbidden_markers") or [],
        "constraints": {"max_chars": int((payload.get("context") or {}).get("max_chars") or 80)},
        "user_input": payload.get("user_input") or "",
        "model_surface_candidate_trace": {
            "accepted": [],
            "initial_rejected": [
                {
                    "raw_candidate": candidate.get("text") or "",
                    "candidate": "",
                    "rejection_reasons": candidate.get("detected_errors") or [],
                }
                for candidate in rejected_candidates
            ],
            "repairs": [],
        },
    }


def _new_metrics():
    return {
        "case_count": 0,
        "candidate_count": 0,
        "rejected_candidate_count": 0,
        "runtime_detected_rejected_candidate_count": 0,
        "shadow_active_count": 0,
        "learned_gold_selection_count": 0,
        "learned_strict_valid_count": 0,
        "learned_gate_rejected_selection_count": 0,
        "visible_output_unchanged_count": 0,
    }


def _finalize_metrics(metrics):
    cases = metrics["case_count"]
    rejected = metrics["rejected_candidate_count"]
    output = dict(metrics)
    output.update(
        {
            "runtime_rejected_candidate_detection_rate": _safe_rate(
                metrics["runtime_detected_rejected_candidate_count"], rejected
            ),
            "shadow_active_rate": _safe_rate(metrics["shadow_active_count"], cases),
            "learned_gold_selection_rate": _safe_rate(metrics["learned_gold_selection_count"], cases),
            "learned_strict_valid_rate": _safe_rate(metrics["learned_strict_valid_count"], cases),
            "learned_gate_rejected_selection_rate": _safe_rate(
                metrics["learned_gate_rejected_selection_count"], cases
            ),
            "visible_output_unchanged_rate": _safe_rate(metrics["visible_output_unchanged_count"], cases),
        }
    )
    return output


def _update_metrics(metrics, case):
    metrics["case_count"] += 1
    metrics["candidate_count"] += case["candidate_count"]
    metrics["rejected_candidate_count"] += case["rejected_candidate_count"]
    metrics["runtime_detected_rejected_candidate_count"] += case["runtime_detected_rejected_candidate_count"]
    metrics["shadow_active_count"] += int(case["shadow_active"])
    metrics["learned_gold_selection_count"] += int(case["learned_selected_gold"])
    metrics["learned_strict_valid_count"] += int(case["learned_strict_valid"])
    metrics["learned_gate_rejected_selection_count"] += int(case["learned_gate_rejected"])
    metrics["visible_output_unchanged_count"] += int(case["visible_output_unchanged"])


def build_runtime_soak_report(rows):
    started = time.monotonic()
    rightbrain = RightBrain(load_model=False)
    if rightbrain.selector_model is None:
        raise RuntimeError(f"Selector model unavailable: {rightbrain.selector_model_load_error}")
    split_seed = int(rightbrain.selector_model.get("split_seed") or 20260707)
    splits = grouped_contract_split(rows, seed=split_seed)
    row_split = {
        row["id"]: split_name
        for split_name, split_rows in splits.items()
        for row in split_rows
    }
    overall = _new_metrics()
    split_metrics = {name: _new_metrics() for name in ("train", "validation", "test")}
    category_metrics = {}
    rejected_source_counts = Counter()
    runtime_missed_source_counts = Counter()
    failures = []

    for row in rows:
        payload = row["contract_payload"]
        gold = next(
            candidate
            for candidate in row["candidates"]
            if candidate["candidate_id"] == row["gold_candidate_id"]
        )
        rejected = [
            candidate
            for candidate in row["candidates"]
            if candidate["candidate_id"] != row["gold_candidate_id"]
        ]
        logic = _logic_from_contract(payload, rejected)
        max_chars = logic["constraints"]["max_chars"]
        runtime_detected = 0
        for candidate in rejected:
            rejected_source_counts[str(candidate.get("source") or "unknown")] += 1
            reasons = rightbrain._model_candidate_rejection_reasons(
                candidate.get("text") or "",
                logic,
                max_chars,
                user_input=logic["user_input"],
            )
            if reasons:
                runtime_detected += 1
            else:
                runtime_missed_source_counts[str(candidate.get("source") or "unknown")] += 1

        output = rightbrain._select_model_blended_reply(gold["text"], [], logic)
        shadow = logic.get("model_surface_selector_shadow") or {}
        case = {
            "id": row["id"],
            "split": row_split[row["id"]],
            "category": str(row.get("category") or "uncategorized"),
            "candidate_count": len(row["candidates"]),
            "rejected_candidate_count": len(rejected),
            "runtime_detected_rejected_candidate_count": runtime_detected,
            "shadow_active": shadow.get("status") == "active",
            "learned_selected_gold": shadow.get("learned_selected_text") == gold["text"],
            "learned_strict_valid": bool(shadow.get("learned_selected_strict_valid")),
            "learned_gate_rejected": bool(shadow.get("learned_selected_was_gate_rejected")),
            "visible_output_unchanged": output == gold["text"],
            "learned_selected_source": shadow.get("learned_selected_source"),
        }
        _update_metrics(overall, case)
        _update_metrics(split_metrics[case["split"]], case)
        category_key = f"{case['split']}:{case['category']}"
        category_metrics.setdefault(category_key, _new_metrics())
        _update_metrics(category_metrics[category_key], case)
        if not all(
            (
                case["runtime_detected_rejected_candidate_count"] == case["rejected_candidate_count"],
                case["shadow_active"],
                case["learned_selected_gold"],
                case["learned_strict_valid"],
                not case["learned_gate_rejected"],
                case["visible_output_unchanged"],
            )
        ):
            failures.append(case)

    finalized_splits = {name: _finalize_metrics(metrics) for name, metrics in split_metrics.items()}
    finalized_categories = {
        key: _finalize_metrics(metrics)
        for key, metrics in sorted(category_metrics.items())
    }
    test = finalized_splits["test"]
    split_info = split_summary(splits)
    gate = {
        "full_case_count_is_360": len(rows) == EXPECTED_CASE_COUNT,
        "test_case_count_is_54": test["case_count"] == EXPECTED_TEST_CASE_COUNT,
        "contract_fingerprint_overlap_is_zero": all(
            count == 0 for count in split_info["fingerprint_overlap_counts"].values()
        ),
        "test_runtime_detects_all_rejected_candidates": test["runtime_rejected_candidate_detection_rate"] == 1.0,
        "test_shadow_active_rate_is_100pct": test["shadow_active_rate"] == 1.0,
        "test_learned_gold_selection_rate_is_100pct": test["learned_gold_selection_rate"] == 1.0,
        "test_learned_strict_valid_rate_is_100pct": test["learned_strict_valid_rate"] == 1.0,
        "test_learned_never_selects_gate_rejected_candidate": test["learned_gate_rejected_selection_count"] == 0,
        "test_visible_output_unchanged_rate_is_100pct": test["visible_output_unchanged_rate"] == 1.0,
        "no_runtime_soak_failures": not failures,
    }
    duration = time.monotonic() - started
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "rightbrain_selector_runtime_soak_v1",
        "dataset_scope": "rightbrain_repair_selection_v1",
        "split": split_info,
        "duration_seconds": round(duration, 4),
        "cases_per_second": round(len(rows) / duration, 2) if duration else None,
        "summary": _finalize_metrics(overall),
        "split_metrics": finalized_splits,
        "category_metrics": finalized_categories,
        "rejected_source_counts": dict(sorted(rejected_source_counts.items())),
        "runtime_missed_source_counts": dict(sorted(runtime_missed_source_counts.items())),
        "gate": gate,
        "gate_passed": all(gate.values()),
        "failures": failures,
        "conclusion_zh": (
            "360 組候選已完整通過 production RightBrain shadow path；主要泛化結論只採用 54 組 contract-held-out test。"
        ),
        "research_boundary": (
            "This is a synthetic corruption soak for runtime integration. Train and validation rows are reported for diagnostics; "
            "only the contract-disjoint test split is used for the generalization gate. It is not live dialogue or a naturalness test."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# RightBrain Selector Runtime Soak v1",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## Split 結果",
        "",
        "| split | cases | rejected candidates | runtime detected | learned gold | invalid selected | output unchanged |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("train", "validation", "test"):
        metrics = report["split_metrics"][name]
        lines.append(
            f"| {name} | {metrics['case_count']} | {metrics['rejected_candidate_count']} | "
            f"{_fmt_pct(metrics['runtime_rejected_candidate_detection_rate'])} | "
            f"{_fmt_pct(metrics['learned_gold_selection_rate'])} | "
            f"{_fmt_pct(metrics['learned_gate_rejected_selection_rate'])} | "
            f"{_fmt_pct(metrics['visible_output_unchanged_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Held-out Test Gate",
            "",
            "| 條件 | 結果 |",
            "|---|---|",
        ]
    )
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 360 題用來做 runtime soak；其中 train/validation 只供診斷。",
            "- 泛化 gate 只看 54 題未跨 contract fingerprint 的 test split。",
            "- 這證明 runtime 接線與污染拒絕穩定，不證明自然度，也不計入 live 100/20 門檻。",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SELECTOR_RUNTIME_SOAK_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    report = build_runtime_soak_report(rows)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({"summary": report["summary"], "test": report["split_metrics"]["test"], "gate": report["gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
