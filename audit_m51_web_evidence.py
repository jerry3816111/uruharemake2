"""Audit frozen M51 Safari candidate evidence separately from delivery quality."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re


M51 = "state_changing_candidates_m51"
M46 = "goal_progress_delivery_m46"
M45 = "actionable_help_delivery_m45"
EXPECTED = (
    ("机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。", "valid_candidate_selected", "verified"),
    ("レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。", "valid_candidate_selected", "rejected"),
    ("To create three section headings, give me one practical step.", "no_structurally_valid_candidate", "plan_rejected"),
    ("Give me one practical step.", "not_invoked", "awaiting_task"),
    ("方法はいらない。ただ聞いてほしい。", "not_invoked", None),
)


def _load(path):
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _japanese(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or "")) and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def audit(path):
    rows = _load(path)
    turns = []
    for index, (text, expected_m51, expected_m46) in enumerate(EXPECTED):
        row = rows[index] if index < len(rows) else {}
        logic = row.get("logic") or {}
        state = logic.get(M51) or {}
        m46 = logic.get(M46) or {}
        delivery = logic.get(M45) or {}
        candidate_count = state.get("candidate_count")
        unique_count = state.get("unique_candidate_count")
        positive = index < 3
        turns.append({
            "turn_index": row.get("turn_index"),
            "input_matches_script": row.get("user_text") == text,
            "m51_status": state.get("status"),
            "m51_status_pass": state.get("status") == expected_m51,
            "candidate_count": candidate_count,
            "unique_candidate_count": unique_count,
            "two_distinct_candidates_pass": candidate_count == 2 and unique_count == 2 if positive else candidate_count == 0,
            "structurally_valid_count": state.get("structurally_valid_count"),
            "m46_status": m46.get("status") if m46 else None,
            "m46_status_pass": (m46.get("status") if m46 else None) == expected_m46,
            "content_passed": m46.get("content_passed") if m46 else None,
            "surface_passed": m46.get("surface_passed") if m46 else None,
            "delivered": delivery.get("delivered") is True,
            "visible_japanese_pass": _japanese(row.get("assistant_reply")),
            "raw_dialogue_duplicated_in_m51": text in json.dumps(state, ensure_ascii=False),
            "long_term_memory_write": state.get("long_term_memory_write"),
        })
    structural = [
        turn["input_matches_script"] and turn["m51_status_pass"] and turn["m46_status_pass"]
        and turn["two_distinct_candidates_pass"] and turn["visible_japanese_pass"]
        and not turn["raw_dialogue_duplicated_in_m51"] and turn["long_term_memory_write"] is False
        for turn in turns
    ]
    return {
        "schema": "uruha_m51_isolated_web_audit",
        "source_log": str(path),
        "session_ids": sorted({row.get("session_id") for row in rows if row.get("session_id")}),
        "observed_turns": len(rows),
        "structural_trace_pass_count": sum(structural),
        "structural_trace_total": len(EXPECTED),
        "structural_trace_gate_passed": len(rows) == len(EXPECTED) and all(structural),
        "visible_japanese_count": sum(turn["visible_japanese_pass"] for turn in turns),
        "positive_two_distinct_candidates": f"{sum(turn['two_distinct_candidates_pass'] for turn in turns[:3])}/3",
        "positive_structurally_valid_selection": f"{sum((turn['structurally_valid_count'] or 0) > 0 for turn in turns[:3])}/3",
        "positive_plan_and_delivery": f"{sum(turn['delivered'] for turn in turns[:3])}/3",
        "missing_task_and_no_method_safety": f"{sum(not turn['delivered'] and turn['candidate_count'] == 0 for turn in turns[3:])}/2",
        "m51_contract_gate_passed": len(rows) == len(EXPECTED) and all(structural),
        "source_aligned_practical_help_pipeline_passed": False,
        "turns": turns,
        "claim_boundary": (
            "M51 proves two distinct source-bound candidate records were generated for three positive Safari cases, "
            "with M46 still authoritative. Only one was delivered; this is not broad practical-help, naturalness, "
            "human preference, felt-understanding, or human-equation evidence."
        ),
    }


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("log"); parser.add_argument("--output")
    args = parser.parse_args(); result = audit(args.log)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if result["m51_contract_gate_passed"] else 1)


if __name__ == "__main__":
    main()
