"""Audit frozen M48 Safari turns while separating surface repair from usefulness."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re


M48 = "crosslingual_action_realization_m48"
M46 = "goal_progress_delivery_m46"
M45 = "actionable_help_delivery_m45"

EXPECTED = (
    ("抽屜裡有信件和收據，現在混在一起。給我一個現在能做的步驟。", "repair_failed_closed", False),
    ("机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。", "blocked_by_nonrealization_violation", False),
    ("I have two piles labeled receipts and letters, and one receipt is in the letters pile. Give me one practical step.", "blocked_by_nonrealization_violation", False),
    ("The report is still blank. Give me one practical step.", "not_needed", True),
    ("My downloads folder contains PDFs and screenshots mixed together. Give me one practical step to start organizing it.", "blocked_by_nonrealization_violation", False),
    ("レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。", "repaired", True),
    ("方法はいらない。ただ聞いてほしい。", None, False),
)


def japanese_visible(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or ""))
                and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def state_for(logic):
    delivery = (logic or {}).get(M45) or {}
    m46 = delivery.get(M46) or {}
    state = ((logic or {}).get(M48) or m46.get(M48)
             or (m46.get("diagnostic") or {}).get(M48))
    return delivery, m46, state if isinstance(state, dict) else {}


def audit(path):
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    turns = []
    for index, (text, expected_status, expected_delivery) in enumerate(EXPECTED):
        row = rows[index] if index < len(rows) else {}
        logic = row.get("logic") or {}
        delivery, m46, state = state_for(logic)
        status = state.get("status") if state else None
        delivered = delivery.get("delivered") is True
        semantic_alignment_observation = None
        if index == 3:
            semantic_alignment_observation = "bounded author observation: one heading advances a blank report"
        elif index == 5:
            semantic_alignment_observation = (
                "bounded author failure: source asks for three headings, plan/output changes target to heading plus introduction"
            )
        turns.append({
            "turn_index": row.get("turn_index"),
            "input_matches_script": row.get("user_text") == text,
            "m48_status": status,
            "m48_status_pass": status == expected_status,
            "m48_changed": state.get("changed") if state else None,
            "semantic_fields_changed": state.get("semantic_fields_changed") if state else None,
            "object_visible": state.get("object_visible") if state else None,
            "operation_visible": state.get("operation_visible") if state else None,
            "stop_visible": state.get("stop_visible") if state else None,
            "m46_status": m46.get("status") or "not_applicable",
            "delivery_status": delivery.get("status") or "not_applicable",
            "delivered": delivered,
            "delivery_matches_observed_run": delivered == expected_delivery,
            "visible_japanese_pass": japanese_visible(row.get("assistant_reply")),
            "semantic_alignment_observation": semantic_alignment_observation,
            "raw_dialogue_duplicated_in_m48": bool(state and text in json.dumps(state, ensure_ascii=False)),
            "long_term_memory_write": state.get("long_term_memory_write") if state else None,
        })
    structural_pass = [
        turn["input_matches_script"] and turn["m48_status_pass"]
        and turn["delivery_matches_observed_run"] and turn["visible_japanese_pass"]
        and not turn["raw_dialogue_duplicated_in_m48"]
        and (turn["long_term_memory_write"] is False if turn["m48_status"] else True)
        for turn in turns
    ]
    repaired = [turn for turn in turns if turn["m48_status"] == "repaired"]
    return {
        "schema": "uruha_m48_isolated_web_audit",
        "source_log": str(source),
        "session_ids": sorted({row.get("session_id") for row in rows if row.get("session_id")}),
        "observed_turns": len(rows),
        "expected_turns": len(EXPECTED),
        "structural_trace_pass_count": sum(structural_pass),
        "structural_trace_total": len(EXPECTED),
        "structural_trace_gate_passed": len(rows) == len(EXPECTED) and all(structural_pass),
        "visible_japanese_count": sum(turn["visible_japanese_pass"] for turn in turns),
        "m48_repaired_count": len(repaired),
        "m48_repair_contract_pass_count": sum(
            turn["m48_changed"] is True
            and turn["semantic_fields_changed"] is False
            and turn["object_visible"] is True
            and turn["operation_visible"] is True
            and turn["stop_visible"] is True
            for turn in repaired
        ),
        "m48_not_needed_count": sum(turn["m48_status"] == "not_needed" for turn in turns),
        "m48_fail_closed_or_blocked_count": sum(
            turn["m48_status"] in {"repair_failed_closed", "blocked_by_nonrealization_violation"}
            for turn in turns
        ),
        "action_delivery_count": sum(turn["delivered"] for turn in turns[:-1]),
        "action_delivery_total": len(turns) - 1,
        "bounded_author_semantic_alignment": "1/2 delivered actions; not blind human evidence",
        "turns": turns,
        "claim_boundary": (
            "actual scripted Safari trace; one real M48 surface repair was observed, but its upstream plan "
            "was source-misaligned under bounded author inspection. No holdout or human preference claim."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.log)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if result["structural_trace_gate_passed"] else 1)


if __name__ == "__main__":
    main()
