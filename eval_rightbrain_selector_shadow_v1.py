#!/usr/bin/env python3
"""Replay real generated candidates through the runtime selector shadow path."""

import argparse
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH,
    RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_MD_PATH,
)
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _alignment_label(alignment):
    alignment = alignment or {}
    return "/".join(
        f"{float(alignment.get(key) or 0.0):.2f}"
        for key in (
            "grounding_term_hit_rate",
            "semantic_reference_bigram_dice",
            "user_input_unigram_dice",
        )
    )


def build_shadow_report(source_report):
    rightbrain = RightBrain(load_model=False)
    case_inputs = {case["id"]: case for case in _case_inputs()}
    cases = []
    learned_sources = Counter()
    active_count = 0
    current_valid_count = 0
    learned_valid_count = 0
    learned_gate_rejected_count = 0
    agreement_count = 0
    unchanged_output_count = 0
    candidate_count = 0
    input_rejected_candidate_count = 0

    for source_case in source_report.get("cases") or []:
        case_id = source_case.get("id")
        if case_id not in case_inputs:
            continue
        logic = deepcopy(case_inputs[case_id]["logic"])
        logic["user_input"] = source_case.get("user_input") or ""
        accepted_rows = deepcopy(source_case.get("model_accepted_candidates") or [])
        rejected_rows = deepcopy(source_case.get("model_initial_rejected_candidates") or [])
        logic["model_surface_candidate_trace"] = {
            "accepted": accepted_rows,
            "initial_rejected": rejected_rows,
            "repairs": [],
        }
        model_candidates = [
            str(candidate.get("candidate") or candidate.get("raw_candidate") or "")
            for candidate in accepted_rows
            if str(candidate.get("candidate") or candidate.get("raw_candidate") or "").strip()
        ]
        deterministic_reply = str(source_case.get("deterministic_reply") or "")
        current_reply = rightbrain._select_model_blended_reply(
            deterministic_reply,
            model_candidates,
            logic,
        )
        shadow = logic.get("model_surface_selector_shadow") or {}
        selection = logic.get("model_surface_selection") or {}
        active_count += int(shadow.get("status") == "active")
        current_valid_count += int(bool(shadow.get("current_selected_strict_valid")))
        learned_valid_count += int(bool(shadow.get("learned_selected_strict_valid")))
        learned_gate_rejected_count += int(bool(shadow.get("learned_selected_was_gate_rejected")))
        agreement_count += int(bool(shadow.get("agrees_with_current")))
        unchanged_output_count += int(current_reply == selection.get("selected_candidate"))
        candidate_count += int(shadow.get("candidate_count") or 0)
        input_rejected_candidate_count += len(rejected_rows)
        learned_sources[str(shadow.get("learned_selected_source") or "unknown")] += 1
        cases.append(
            {
                "id": case_id,
                "category": source_case.get("category"),
                "current_selected_source": selection.get("selected_source"),
                "current_reply": current_reply,
                "current_selected_semantic_alignment": shadow.get("current_selected_semantic_alignment"),
                "shadow_status": shadow.get("status"),
                "candidate_count": shadow.get("candidate_count"),
                "learned_selected_source": shadow.get("learned_selected_source"),
                "learned_selected_text": shadow.get("learned_selected_text"),
                "learned_selected_probability": shadow.get("learned_selected_probability"),
                "learned_selected_semantic_alignment": shadow.get("learned_selected_semantic_alignment"),
                "learned_selected_strict_valid": shadow.get("learned_selected_strict_valid"),
                "learned_selected_was_gate_rejected": shadow.get("learned_selected_was_gate_rejected"),
                "agrees_with_current": shadow.get("agrees_with_current"),
                "would_change_output": shadow.get("would_change_output"),
                "user_visible_reply_changed_by_shadow": current_reply != selection.get("selected_candidate"),
            }
        )

    case_count = len(cases)
    summary = {
        "case_count": case_count,
        "candidate_count": candidate_count,
        "input_rejected_candidate_count": input_rejected_candidate_count,
        "shadow_active_count": active_count,
        "shadow_active_rate": _safe_rate(active_count, case_count),
        "current_strict_valid_count": current_valid_count,
        "current_strict_valid_rate": _safe_rate(current_valid_count, case_count),
        "learned_strict_valid_count": learned_valid_count,
        "learned_strict_valid_rate": _safe_rate(learned_valid_count, case_count),
        "learned_gate_rejected_selection_count": learned_gate_rejected_count,
        "learned_gate_rejected_selection_rate": _safe_rate(learned_gate_rejected_count, case_count),
        "agreement_count": agreement_count,
        "agreement_rate": _safe_rate(agreement_count, case_count),
        "would_change_count": case_count - agreement_count,
        "would_change_rate": _safe_rate(case_count - agreement_count, case_count),
        "user_visible_output_unchanged_count": unchanged_output_count,
        "user_visible_output_unchanged_rate": _safe_rate(unchanged_output_count, case_count),
        "learned_selected_source_counts": dict(sorted(learned_sources.items())),
    }
    gate = {
        "all_cases_shadow_active": active_count == case_count and case_count > 0,
        "learned_selection_strict_valid_rate_is_100pct": learned_valid_count == case_count and case_count > 0,
        "learned_never_selects_gate_rejected_candidate": learned_gate_rejected_count == 0,
        "shadow_never_changes_user_visible_output": unchanged_output_count == case_count and case_count > 0,
        "contains_real_rejected_candidates": input_rejected_candidate_count > 0,
    }
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_selector_shadow_v1",
        "source_scope": source_report.get("scope"),
        "summary": summary,
        "gate": gate,
        "gate_passed": all(gate.values()),
        "cases": cases,
        "conclusion_zh": (
            "學習式 selector 已接入 F 右腦的 observe-only shadow path；它會評分真實候選並留下 trace，"
            "但不改變使用者收到的回答。"
        ),
        "research_boundary": (
            "This is an 11-case replay of previously generated runtime candidates. It validates wiring and safety, "
            "not superiority in naturalness. Future live logs and blinded preference evidence are still required before takeover."
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# RightBrain Selector Shadow v1",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## Runtime 重播結果",
        "",
        "| 指標 | 結果 | 意義 |",
        "|---|---:|---|",
        f"| cases | {summary['case_count']} | 先前真實模型生成案例 |",
        f"| candidates | {summary['candidate_count']} | deterministic、接受與拒絕候選總數 |",
        f"| real rejected candidates | {summary['input_rejected_candidate_count']} | strict gate 當時拒絕的真實輸出 |",
        f"| learned strict-valid | {_fmt_pct(summary['learned_strict_valid_rate'])} | learner 選到不違反合約候選的比例 |",
        f"| selected rejected candidate | {_fmt_pct(summary['learned_gate_rejected_selection_rate'])} | learner 誤選已拒絕候選；越低越好 |",
        f"| agreement with current | {_fmt_pct(summary['agreement_rate'])} | learner 與現行選擇相同的比例 |",
        f"| would change | {_fmt_pct(summary['would_change_rate'])} | 只記錄差異，不實際切換 |",
        f"| visible output unchanged | {_fmt_pct(summary['user_visible_output_unchanged_rate'])} | shadow 不得改變正式回答 |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 差異案例",
            "",
            "語意欄依序為 `grounding / leftbrain bigram / user-input unigram`，只作診斷，不是人工偏好分數。",
            "",
            "| case | current source | current semantic | learned source | learned semantic | valid | would change |",
            "|---|---|---:|---|---:|---|---|",
        ]
    )
    for case in report["cases"]:
        if not case.get("would_change_output"):
            continue
        lines.append(
            f"| {case['id']} | {case['current_selected_source']} | "
            f"{_alignment_label(case['current_selected_semantic_alignment'])} | "
            f"{case['learned_selected_source']} | "
            f"{_alignment_label(case['learned_selected_semantic_alignment'])} | "
            f"{case['learned_selected_strict_valid']} | {case['would_change_output']} |"
        )
    lines.extend(
        [
            "",
            "## 邊界",
            "",
            "- 本輪證明 runtime 接線與安全隔離，不證明 learner 比現行回答更自然。",
            "- 真實 web chat 的 `logic.model_surface_selector_shadow` 會自動寫入 JSONL 日誌。",
            "- 必須累積 live disagreement 並做偏好比較後，才可討論正式接管。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SELECTOR_SHADOW_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    source_report = json.loads(Path(args.source).read_text(encoding="utf-8"))
    report = build_shadow_report(source_report)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({"summary": report["summary"], "gate": report["gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
