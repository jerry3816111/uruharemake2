"""Audit frozen M49 Safari evidence without turning handoff into quality credit."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re


M49 = "route_qualified_task_handoff_m49"
M47 = "crosslingual_help_routing_m47"
M46 = "goal_progress_delivery_m46"
M45 = "actionable_help_delivery_m45"

EXPECTED = (
    ("レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。",
     "task_spans_added", "verified", True),
    ("机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。",
     "task_spans_added", "plan_rejected", False),
    ("把桌上的信件按日期分成兩堆，給我一個現在能做的步驟。",
     "no_new_task_span", "verified", True),
    ("To create three section headings, give me one practical step.",
     "no_new_task_span", "plan_rejected", False),
    ("Give me one practical step.", "no_new_task_span", "awaiting_task", False),
    ("方法はいらない。ただ聞いてほしい。", None, None, False),
)


def _load(path):
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _digest(text):
    return hashlib.sha256(str(text).encode()).hexdigest()[:16]


def _japanese_visible(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or ""))
                and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def _exact_additions(row, state):
    original = row.get("user_text") or ""
    results = []
    for item in state.get("added_sources") or []:
        origin = item.get("origin") or {}
        start = origin.get("span_start", -1)
        length = origin.get("span_length", -1)
        span = original[start:start + length] if start >= 0 and length >= 0 else ""
        results.append(bool(span and _digest(original) == origin.get("source_digest")
                            and _digest(span) == origin.get("span_digest")))
    return results


def audit(formal_path, postfix_path):
    rows = _load(formal_path)
    turns = []
    for index, (text, expected_m49, expected_m46, expected_delivery) in enumerate(EXPECTED):
        row = rows[index] if index < len(rows) else {}
        logic = row.get("logic") or {}
        state = logic.get(M49) or {}
        delivery = logic.get(M45) or {}
        m46 = logic.get(M46) or {}
        m47 = logic.get(M47) or {}
        exact = _exact_additions(row, state)
        turns.append({
            "turn_index": row.get("turn_index"),
            "input_matches_script": row.get("user_text") == text,
            "route_status": m47.get("status"),
            "m49_status": state.get("status") if state else None,
            "m49_status_pass": (state.get("status") if state else None) == expected_m49,
            "base_allowed_count": state.get("base_allowed_count") if state else None,
            "added_count": state.get("added_count") if state else None,
            "exact_origin_digest_pass": all(exact) if exact else None,
            "goal_selected_added_span": state.get("goal_selected_added_span") if state else None,
            "m46_status": m46.get("status") if m46 else None,
            "m46_status_pass": (m46.get("status") if m46 else None) == expected_m46,
            "delivered": delivery.get("delivered") is True,
            "delivery_pass": (delivery.get("delivered") is True) == expected_delivery,
            "visible_japanese_pass": _japanese_visible(row.get("assistant_reply")),
            "raw_dialogue_duplicated_in_m49": bool(state and text in json.dumps(state, ensure_ascii=False)),
            "long_term_memory_write": state.get("long_term_memory_write") if state else None,
        })

    postfix_rows = _load(postfix_path)
    postfix = postfix_rows[0] if postfix_rows else {}
    postfix_logic = postfix.get("logic") or {}
    postfix_state = postfix_logic.get(M49) or {}
    postfix_delivery = postfix_logic.get(M45) or {}
    correction_safety = {
        "input": postfix.get("user_text"),
        "visible_reply": postfix.get("assistant_reply"),
        "m49_added_count": postfix_state.get("added_count"),
        "delivery_status": postfix_delivery.get("status"),
        "model_calls_attempted": postfix_delivery.get("model_calls_attempted"),
        "visible_japanese_pass": _japanese_visible(postfix.get("assistant_reply")),
    }
    correction_safety["passed"] = (
        correction_safety["input"] == "You misunderstood; give me a method."
        and correction_safety["m49_added_count"] == 0
        and correction_safety["delivery_status"] == "awaiting_context"
        and correction_safety["model_calls_attempted"] == 0
        and correction_safety["visible_japanese_pass"]
    )

    structural = [
        turn["input_matches_script"] and turn["m49_status_pass"]
        and turn["m46_status_pass"] and turn["delivery_pass"]
        and turn["visible_japanese_pass"] and not turn["raw_dialogue_duplicated_in_m49"]
        and (turn["long_term_memory_write"] is False if turn["m49_status"] else True)
        for turn in turns
    ]
    added_turns = [turn for turn in turns if turn["m49_status"] == "task_spans_added"]
    positive_turns = turns[:4]
    return {
        "schema": "uruha_m49_isolated_web_audit",
        "source_logs": {"formal": str(formal_path), "postfix": str(postfix_path)},
        "session_ids": sorted({row.get("session_id") for row in rows + postfix_rows if row.get("session_id")}),
        "formal_turns": len(rows),
        "structural_trace_pass_count": sum(structural),
        "structural_trace_total": len(EXPECTED),
        "structural_trace_gate_passed": len(rows) == len(EXPECTED) and all(structural),
        "visible_japanese_count": sum(turn["visible_japanese_pass"] for turn in turns),
        "exact_route_qualified_handoff": f"{sum(turn['exact_origin_digest_pass'] is True for turn in added_turns)}/{len(added_turns)}",
        "added_span_goal_selection": f"{sum(turn['goal_selected_added_span'] is True for turn in added_turns)}/{len(added_turns)}",
        "positive_plan_and_delivery": f"{sum(turn['delivered'] for turn in positive_turns)}/{len(positive_turns)}",
        "pure_request_and_forbid_safety": f"{sum(not turn['delivered'] for turn in turns[4:])}/{len(turns[4:])}",
        "postfix_correction_safety": correction_safety,
        "m49_contract_gate_passed": (
            len(rows) == len(EXPECTED) and all(structural)
            and all(turn["exact_origin_digest_pass"] is True for turn in added_turns)
            and correction_safety["passed"]
        ),
        "source_aligned_practical_help_pipeline_passed": False,
        "turns": turns,
        "claim_boundary": (
            "M49 proves exact route-qualified current-turn task-span delivery and a correction safety guard. "
            "Only 2/4 positive Safari tasks produced actions; this is not a usefulness, holdout, human-preference, "
            "or human-understanding result."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("formal_log")
    parser.add_argument("--postfix", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.formal_log, args.postfix)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if result["m49_contract_gate_passed"] else 1)


if __name__ == "__main__":
    main()
