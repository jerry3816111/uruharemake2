#!/usr/bin/env python3
"""Aggregate observe-only RightBrain selector evidence from web conversation logs."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from project_paths import (
    RIGHTBRAIN_SELECTOR_LIVE_DISAGREEMENT_QUEUE_JSON_PATH,
    RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_JSON_PATH,
    RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_MD_PATH,
    WEB_CONVERSATION_LOG_JSONL_PATH,
)


DEFAULT_MIN_MULTI_CANDIDATE_CASES = 100
DEFAULT_MIN_DISAGREEMENTS = 20


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _normalize_text(text):
    return "".join(str(text or "").lower().split()).strip("。．.!！？?、,，")


def _turn_key(record, fallback_index):
    session_id = str(record.get("session_id") or "").strip()
    turn_index = record.get("turn_index")
    if session_id and turn_index is not None:
        return f"{session_id}:{turn_index}"
    return f"unkeyed:{fallback_index}"


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return [], {"exists": False, "invalid_line_count": 0, "nonempty_line_count": 0}
    rows = []
    invalid = 0
    nonempty = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        nonempty += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            invalid += 1
    return rows, {"exists": True, "invalid_line_count": invalid, "nonempty_line_count": nonempty}


def _score_margin(shadow):
    scores = sorted(
        [
            float(row.get("probability"))
            for row in shadow.get("candidate_scores") or []
            if isinstance(row.get("probability"), (int, float))
        ],
        reverse=True,
    )
    if len(scores) < 2:
        return None
    return round(scores[0] - scores[1], 6)


def extract_shadow_case(record, fallback_index=0):
    logic = record.get("logic") or {}
    shadow = logic.get("model_surface_selector_shadow") or {}
    if shadow.get("status") != "active":
        return None
    selection = logic.get("model_surface_selection") or {}
    assistant_reply = str(record.get("assistant_reply") or "").strip()
    current_text = str(shadow.get("current_selected_text") or selection.get("selected_candidate") or "").strip()
    visible_matches_current = _normalize_text(assistant_reply) == _normalize_text(current_text)
    candidate_count = int(shadow.get("candidate_count") or 0)
    learned_valid = bool(shadow.get("learned_selected_strict_valid"))
    current_valid = bool(shadow.get("current_selected_strict_valid"))
    selected_rejected = bool(shadow.get("learned_selected_was_gate_rejected"))
    would_change = bool(shadow.get("would_change_output"))
    trace_claims_no_change = shadow.get("changes_user_visible_reply") is False
    return {
        "case_id": _turn_key(record, fallback_index),
        "timestamp": record.get("timestamp"),
        "session_id": record.get("session_id"),
        "turn_index": record.get("turn_index"),
        "input_mode": record.get("input_mode"),
        "user_text": record.get("user_text"),
        "assistant_reply": assistant_reply,
        "scene": logic.get("scene") or (record.get("planner_debug") or {}).get("scene"),
        "intent": logic.get("intent") or (record.get("planner_debug") or {}).get("intent"),
        "candidate_count": candidate_count,
        "multi_candidate": candidate_count > 1,
        "current_selected_source": selection.get("selected_source"),
        "current_selected_text": current_text,
        "current_selected_strict_valid": current_valid,
        "learned_selected_source": shadow.get("learned_selected_source"),
        "learned_selected_text": shadow.get("learned_selected_text"),
        "learned_selected_probability": shadow.get("learned_selected_probability"),
        "learned_selected_strict_valid": learned_valid,
        "learned_selected_was_gate_rejected": selected_rejected,
        "agrees_with_current": bool(shadow.get("agrees_with_current")),
        "would_change_output": would_change,
        "score_margin": _score_margin(shadow),
        "trace_claims_no_visible_change": trace_claims_no_change,
        "visible_reply_matches_current": visible_matches_current,
        "safety_pass": (
            learned_valid
            and current_valid
            and not selected_rejected
            and trace_claims_no_change
            and visible_matches_current
        ),
        "candidate_scores": shadow.get("candidate_scores") or [],
    }


def _deduplicated_shadow_cases(records):
    by_turn = {}
    for index, record in enumerate(records):
        case = extract_shadow_case(record, fallback_index=index)
        if case:
            by_turn[case["case_id"]] = case
    return sorted(by_turn.values(), key=lambda row: (str(row.get("timestamp") or ""), row["case_id"]))


def build_report(
    records,
    source_path=WEB_CONVERSATION_LOG_JSONL_PATH,
    source_meta=None,
    min_multi_candidate_cases=DEFAULT_MIN_MULTI_CANDIDATE_CASES,
    min_disagreements=DEFAULT_MIN_DISAGREEMENTS,
):
    cases = _deduplicated_shadow_cases(records)
    multi_cases = [case for case in cases if case["multi_candidate"]]
    disagreements = [case for case in multi_cases if case["would_change_output"]]
    learned_invalid = [case for case in multi_cases if not case["learned_selected_strict_valid"]]
    current_invalid = [case for case in multi_cases if not case["current_selected_strict_valid"]]
    selected_rejected = [case for case in multi_cases if case["learned_selected_was_gate_rejected"]]
    visible_change_violations = [
        case
        for case in cases
        if not case["trace_claims_no_visible_change"] or not case["visible_reply_matches_current"]
    ]
    unsafe_cases = [case for case in cases if not case["safety_pass"]]
    source_counts = Counter(str(case.get("learned_selected_source") or "unknown") for case in multi_cases)
    scene_counts = Counter(str(case.get("scene") or "unknown") for case in disagreements)
    intent_counts = Counter(str(case.get("intent") or "unknown") for case in disagreements)

    summary = {
        "logged_record_count": len(records),
        "active_shadow_case_count": len(cases),
        "multi_candidate_case_count": len(multi_cases),
        "multi_candidate_coverage_rate": _safe_rate(len(multi_cases), len(cases)),
        "disagreement_count": len(disagreements),
        "disagreement_rate": _safe_rate(len(disagreements), len(multi_cases)),
        "agreement_count": len(multi_cases) - len(disagreements),
        "learned_invalid_count": len(learned_invalid),
        "learned_invalid_rate": _safe_rate(len(learned_invalid), len(multi_cases)),
        "current_invalid_count": len(current_invalid),
        "current_invalid_rate": _safe_rate(len(current_invalid), len(multi_cases)),
        "learned_gate_rejected_selection_count": len(selected_rejected),
        "visible_change_violation_count": len(visible_change_violations),
        "unsafe_case_count": len(unsafe_cases),
        "learned_selected_source_counts": dict(sorted(source_counts.items())),
        "disagreement_scene_counts": dict(sorted(scene_counts.items())),
        "disagreement_intent_counts": dict(sorted(intent_counts.items())),
    }
    gate = {
        "source_log_has_no_invalid_lines": int((source_meta or {}).get("invalid_line_count") or 0) == 0,
        "safety_has_multi_candidate_observations": len(multi_cases) > 0,
        "enough_multi_candidate_cases": len(multi_cases) >= min_multi_candidate_cases,
        "enough_disagreements_for_quality_comparison": len(disagreements) >= min_disagreements,
        "learned_invalid_count_is_zero": len(learned_invalid) == 0,
        "learned_never_selects_gate_rejected_candidate": len(selected_rejected) == 0,
        "shadow_never_changes_visible_output": len(visible_change_violations) == 0,
    }
    safety_gate_passed = all(
        gate[name]
        for name in (
            "learned_invalid_count_is_zero",
            "learned_never_selects_gate_rejected_candidate",
            "shadow_never_changes_visible_output",
            "source_log_has_no_invalid_lines",
            "safety_has_multi_candidate_observations",
        )
    )
    quality_comparison_ready = all(gate.values())
    if not gate["source_log_has_no_invalid_lines"]:
        status = "blocked_by_source_log_parse_errors"
    elif not cases:
        status = "waiting_for_live_shadow_data"
    elif not multi_cases:
        status = "waiting_for_live_multi_candidate_data"
    elif not safety_gate_passed:
        status = "blocked_by_shadow_safety_failure"
    elif len(multi_cases) < min_multi_candidate_cases:
        status = "insufficient_multi_candidate_cases"
    elif len(disagreements) < min_disagreements:
        status = "insufficient_disagreements"
    else:
        status = "ready_for_quality_comparison"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "rightbrain_selector_live_evidence",
        "source_path": str(source_path),
        "source_meta": source_meta or {},
        "thresholds": {
            "min_multi_candidate_cases": int(min_multi_candidate_cases),
            "min_disagreements": int(min_disagreements),
        },
        "status": status,
        "summary": summary,
        "gate": gate,
        "safety_gate_passed": safety_gate_passed,
        "quality_comparison_ready": quality_comparison_ready,
        "disagreements": disagreements,
        "unsafe_cases": unsafe_cases,
        "research_boundary": (
            "Only live web-log rows containing an active observe-only selector trace count as live evidence. "
            "Legacy rows and the 11-case replay are not counted toward readiness. Passing this gate permits "
            "quality comparison only; it does not permit runtime takeover."
        ),
    }


def build_disagreement_queue(report):
    return {
        "generated_at": report["generated_at"],
        "scope": "rightbrain_selector_live_disagreement_queue",
        "source_scope": report["scope"],
        "status": report["status"],
        "quality_comparison_ready": report["quality_comparison_ready"],
        "count": len(report.get("disagreements") or []),
        "items": report.get("disagreements") or [],
        "next_stage": (
            "automated_pairwise_quality_comparison"
            if report["quality_comparison_ready"]
            else "continue_observe_only_collection"
        ),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# RightBrain Selector Live Evidence",
        "",
        "## 一句話結論",
        "",
        (
            f"目前狀態：`{report['status']}`。這份報告只計入正式 web log 中實際存在的 active shadow trace，"
            "不把舊對話或 11 題重播冒充 live 證據。"
        ),
        "",
        "## 現況",
        "",
        "| 指標 | 數值 |",
        "|---|---:|",
        f"| logged records | {summary['logged_record_count']} |",
        f"| active shadow cases | {summary['active_shadow_case_count']} |",
        f"| multi-candidate cases | {summary['multi_candidate_case_count']} |",
        f"| multi-candidate coverage | {_fmt_pct(summary['multi_candidate_coverage_rate'])} |",
        f"| disagreements | {summary['disagreement_count']} |",
        f"| disagreement rate | {_fmt_pct(summary['disagreement_rate'])} |",
        f"| learned invalid | {summary['learned_invalid_count']} |",
        f"| selected gate-rejected | {summary['learned_gate_rejected_selection_count']} |",
        f"| visible-output violations | {summary['visible_change_violation_count']} |",
        "",
        "## 進入品質比較的門檻",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'WAIT/FAIL'} |")
    lines.extend(
        [
            "",
            f"quality comparison ready: `{report['quality_comparison_ready']}`",
            "",
            "## 解讀",
            "",
            "- `0` 筆 live shadow 代表尚未收集，不代表 selector 成功或失敗。",
            "- 至少需要 100 筆真實多候選案例與 20 筆分歧，才值得比較哪個回答更自然。",
            "- 任一污染誤選或 shadow 改動可見輸出，都會阻止進入下一階段。",
            "- 下一階段先做自動 pairwise quality comparison；不會立刻要求人工逐題盲測。",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-log", default=WEB_CONVERSATION_LOG_JSONL_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SELECTOR_LIVE_EVIDENCE_REPORT_MD_PATH)
    parser.add_argument("--queue-json", default=RIGHTBRAIN_SELECTOR_LIVE_DISAGREEMENT_QUEUE_JSON_PATH)
    parser.add_argument("--min-multi-candidate-cases", type=int, default=DEFAULT_MIN_MULTI_CANDIDATE_CASES)
    parser.add_argument("--min-disagreements", type=int, default=DEFAULT_MIN_DISAGREEMENTS)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    records, source_meta = load_jsonl(args.web_log)
    report = build_report(
        records,
        source_path=args.web_log,
        source_meta=source_meta,
        min_multi_candidate_cases=args.min_multi_candidate_cases,
        min_disagreements=args.min_disagreements,
    )
    queue = build_disagreement_queue(report)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.output_md).write_text(build_markdown(report) + "\n", encoding="utf-8")
    Path(args.queue_json).write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "summary": report["summary"], "gate": report["gate"]}, ensure_ascii=False, indent=2))
    return 1 if args.require_ready and not report["quality_comparison_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
