"""Audit frozen M50 Safari bundle evidence separately from action quality."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re


M50 = "current_task_source_bundle_m50"
M46 = "goal_progress_delivery_m46"
M45 = "actionable_help_delivery_m45"
EXPECTED = (
    ("レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。", "bundled", "plan_rejected"),
    ("机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。", "bundled", "plan_rejected"),
    ("To create three section headings, give me one practical step.", "not_bundled", "plan_rejected"),
    ("Give me one practical step.", "not_bundled", "awaiting_task"),
    ("方法はいらない。ただ聞いてほしい。", None, None),
)


def _load(path):
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _digest(text):
    return hashlib.sha256(str(text).encode()).hexdigest()[:16]


def _japanese(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or "")) and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def _bundle_exact(row, state):
    original = row.get("user_text") or ""
    checks = []
    for bundle in state.get("bundles") or []:
        origin = bundle.get("origin") or {}
        components = []
        valid = origin.get("source_digest") == _digest(original)
        for item in origin.get("components") or []:
            start, length = item.get("span_start", -1), item.get("span_length", -1)
            span = original[start:start + length] if start >= 0 and length > 0 else ""
            valid = valid and bool(span) and item.get("span_digest") == _digest(span)
            components.append(span)
        bundle_text = "\n".join(components)
        checks.append(valid and origin.get("bundle_digest") == _digest(bundle_text))
    return checks


def audit(path):
    rows = _load(path)
    turns = []
    for index, (text, expected_m50, expected_m46) in enumerate(EXPECTED):
        row = rows[index] if index < len(rows) else {}
        logic = row.get("logic") or {}
        state = logic.get(M50) or {}
        m46 = logic.get(M46) or {}
        delivery = logic.get(M45) or {}
        exact = _bundle_exact(row, state)
        turns.append({
            "turn_index": row.get("turn_index"),
            "input_matches_script": row.get("user_text") == text,
            "m50_status": state.get("status") if state else None,
            "m50_status_pass": (state.get("status") if state else None) == expected_m50,
            "bundle_count": state.get("bundle_count") if state else None,
            "final_source_count": state.get("final_source_count") if state else None,
            "bundle_exact_component_ledger_pass": all(exact) if exact else None,
            "semantic_compatibility_proven": state.get("semantic_compatibility_proven") if state else None,
            "m46_status": m46.get("status") if m46 else None,
            "m46_status_pass": (m46.get("status") if m46 else None) == expected_m46,
            "delivered": delivery.get("delivered") is True,
            "visible_japanese_pass": _japanese(row.get("assistant_reply")),
            "raw_dialogue_duplicated_in_m50": bool(state and text in json.dumps(state, ensure_ascii=False)),
            "long_term_memory_write": state.get("long_term_memory_write") if state else None,
        })
    structural = [
        turn["input_matches_script"] and turn["m50_status_pass"] and turn["m46_status_pass"]
        and turn["visible_japanese_pass"] and not turn["raw_dialogue_duplicated_in_m50"]
        and (turn["long_term_memory_write"] is False if turn["m50_status"] else True)
        for turn in turns
    ]
    bundled = [turn for turn in turns if turn["m50_status"] == "bundled"]
    return {
        "schema": "uruha_m50_isolated_web_audit",
        "source_log": str(path),
        "session_ids": sorted({row.get("session_id") for row in rows if row.get("session_id")}),
        "observed_turns": len(rows),
        "structural_trace_pass_count": sum(structural),
        "structural_trace_total": len(EXPECTED),
        "structural_trace_gate_passed": len(rows) == len(EXPECTED) and all(structural),
        "visible_japanese_count": sum(turn["visible_japanese_pass"] for turn in turns),
        "exact_bundle_component_ledgers": f"{sum(turn['bundle_exact_component_ledger_pass'] is True for turn in bundled)}/{len(bundled)}",
        "bundle_reduced_to_one_planner_source": f"{sum(turn['final_source_count'] == 1 for turn in bundled)}/{len(bundled)}",
        "positive_plan_and_delivery": f"{sum(turn['delivered'] for turn in turns[:3])}/3",
        "missing_task_and_no_method_safety": f"{sum(not turn['delivered'] for turn in turns[3:])}/2",
        "m50_contract_gate_passed": (
            len(rows) == len(EXPECTED) and all(structural)
            and all(turn["bundle_exact_component_ledger_pass"] is True for turn in bundled)
            and all(turn["final_source_count"] == 1 for turn in bundled)
        ),
        "source_aligned_practical_help_pipeline_passed": False,
        "turns": turns,
        "claim_boundary": (
            "M50 proves exact same-turn fragment composition into one planner source for two Safari cases. "
            "All three positive cases were rejected, so this is not action usefulness, human preference, "
            "felt-understanding, or human-equation evidence."
        ),
    }


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("log"); parser.add_argument("--output")
    args = parser.parse_args(); result = audit(args.log)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if result["m50_contract_gate_passed"] else 1)


if __name__ == "__main__":
    main()
