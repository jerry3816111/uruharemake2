"""Audit frozen M52 Safari realization evidence without scoring human usefulness."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re


M52 = "candidate_realization_m52"
M51 = "state_changing_candidates_m51"
M46 = "goal_progress_delivery_m46"
M45 = "actionable_help_delivery_m45"
EXPECTED = (
    ("机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。", "realized", "verified"),
    ("レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。", "realized", "verified"),
    ("To create three section headings, give me one practical step.", "realized", "rejected"),
    ("Give me one practical step.", None, "awaiting_task"),
    ("方法はいらない。ただ聞いてほしい。", None, None),
)


def _load(path):
    source = Path(path); opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _japanese(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or "")) and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def audit(path):
    rows = _load(path); turns = []
    for index, (text, expected_m52, expected_m46) in enumerate(EXPECTED):
        row = rows[index] if index < len(rows) else {}; logic = row.get("logic") or {}
        state = logic.get(M52); m51 = logic.get(M51) or {}; m46 = logic.get(M46) or {}; delivery = logic.get(M45) or {}
        positive = index < 3
        turns.append({
            "turn_index": row.get("turn_index"), "input_matches_script": row.get("user_text") == text,
            "m52_status": state.get("status") if isinstance(state, dict) else None,
            "m52_status_pass": (state.get("status") if isinstance(state, dict) else None) == expected_m52,
            "semantic_fields_unchanged": state.get("semantic_fields_unchanged") if isinstance(state, dict) else None,
            "added_model_calls": state.get("added_model_calls") if isinstance(state, dict) else None,
            "raw_candidate_text_persisted": state.get("raw_candidate_text_persisted") if isinstance(state, dict) else None,
            "long_term_memory_write": state.get("long_term_memory_write") if isinstance(state, dict) else None,
            "m51_candidate_count": m51.get("candidate_count"),
            "m46_status": m46.get("status") if m46 else None,
            "m46_status_pass": (m46.get("status") if m46 else None) == expected_m46,
            "delivered": delivery.get("delivered") is True,
            "visible_japanese_pass": _japanese(row.get("assistant_reply")),
            "raw_dialogue_duplicated_in_m52": bool(state and text in json.dumps(state, ensure_ascii=False)),
            "positive_contract_pass": (
                isinstance(state, dict) and state.get("semantic_fields_unchanged") is True
                and state.get("added_model_calls") == 0 and m51.get("candidate_count") == 2
            ) if positive else state is None,
        })
    structural = [
        turn["input_matches_script"] and turn["m52_status_pass"] and turn["m46_status_pass"]
        and turn["visible_japanese_pass"] and turn["positive_contract_pass"]
        and not turn["raw_dialogue_duplicated_in_m52"]
        and (turn["raw_candidate_text_persisted"] is False if index < 3 else True)
        and (turn["long_term_memory_write"] is False if index < 3 else True)
        for index, turn in enumerate(turns)
    ]
    return {
        "schema": "uruha_m52_isolated_web_audit", "source_log": str(path),
        "session_ids": sorted({row.get("session_id") for row in rows if row.get("session_id")}),
        "observed_turns": len(rows), "structural_trace_pass_count": sum(structural),
        "structural_trace_total": len(EXPECTED),
        "m52_contract_gate_passed": len(rows) == len(EXPECTED) and all(structural),
        "visible_japanese_count": sum(turn["visible_japanese_pass"] for turn in turns),
        "positive_realization_contract": f"{sum(turn['positive_contract_pass'] for turn in turns[:3])}/3",
        "positive_plan_and_delivery": f"{sum(turn['delivered'] for turn in turns[:3])}/3",
        "missing_task_and_no_method_safety": f"{sum(not turn['delivered'] and turn['m52_status'] is None for turn in turns[3:])}/2",
        "source_aligned_practical_help_pipeline_passed": False,
        "turns": turns,
        "claim_boundary": (
            "M52 proves deterministic candidate field/surface realization for three Safari cases without changing "
            "goal/effect/stop or adding model calls. One delivered report invented category labels and English surface "
            "was rejected; this is not source-aligned usefulness, naturalness human rating, or understanding evidence."
        ),
    }


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("log"); parser.add_argument("--output")
    args = parser.parse_args(); result = audit(args.log); payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output: Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end=""); raise SystemExit(0 if result["m52_contract_gate_passed"] else 1)


if __name__ == "__main__": main()
