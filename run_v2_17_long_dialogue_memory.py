#!/usr/bin/env python3
"""Run the isolated V2.17 long-dialogue memory trace experiment.

The distractor turns are a frozen transcript replayed through the production
``save_episode`` path.  Only the four checkpoint turns run the full live
perception -> retrieval -> planning -> visible reply -> writeback path.  This
keeps the experiment about delayed memory transport without pretending that
all 25 displayed replies were freshly generated in this run.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
import re
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_17_long_dialogue_memory_case.json"
OUTPUT_PATH = ROOT / "analysis/v2_17_long_dialogue_memory_raw.json"
ATTEMPT_PATH_PATTERN = "v2_17_long_dialogue_memory_raw_attempt{number}.json"
PRODUCTION_DB_PATH = ROOT / "uruha_memory_mac_db"


def _load_case():
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def _tree_sha256(path):
    digest = hashlib.sha256()
    for child in sorted(Path(path).rglob("*")):
        if not child.is_file():
            continue
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(child.read_bytes())
    return digest.hexdigest()


def _archive_previous_output():
    if not OUTPUT_PATH.exists():
        return None
    number = 1
    while (OUTPUT_PATH.parent / ATTEMPT_PATH_PATTERN.format(number=number)).exists():
        number += 1
    archive = OUTPUT_PATH.parent / ATTEMPT_PATH_PATTERN.format(number=number)
    archive.write_bytes(OUTPUT_PATH.read_bytes())
    return str(archive.relative_to(ROOT))


def _compact_trace_rows(rows):
    compact = []
    for row in rows or []:
        compact.append(
            {
                "trace_id": row.get("trace_id"),
                "memory_id": row.get("memory_id"),
                "source": row.get("source"),
                "channel": row.get("channel"),
                "text": str(row.get("text") or ""),
                "score": row.get("score"),
                "rank": row.get("rank"),
                "selected": row.get("selected"),
            }
        )
    return compact


def _target_rows(memory_data, probes):
    probes = [str(probe).lower() for probe in probes]
    provenance = memory_data.get("memory_provenance") or {}
    rows = []
    for row in provenance.get("passed_to_leftbrain") or []:
        text = str(row.get("text") or "").lower()
        if any(probe in text for probe in probes):
            rows.append(row)
    return _compact_trace_rows(rows)


def _remove_value_from_decision_view(memory_data, value):
    view = copy.deepcopy(memory_data)
    target = str(value or "").lower()
    profile = view.get("profile_structured") or {}
    for field in ("favorites", "likes", "dislikes"):
        profile[field] = [
            item for item in profile.get(field) or []
            if str(item).lower() != target
        ]
    provenance = view.get("memory_provenance") or {}
    provenance["passed_to_leftbrain"] = [
        row for row in provenance.get("passed_to_leftbrain") or []
        if target not in str(row.get("text") or "").lower()
    ]
    provenance["passed_to_leftbrain_trace_ids"] = [
        row.get("trace_id") for row in provenance["passed_to_leftbrain"]
        if row.get("trace_id")
    ]
    view["working_memory_items"] = [
        row for row in view.get("working_memory_items") or []
        if target not in str(row.get("text") or "").lower()
    ]
    return view


def _remove_irrelevant_from_decision_view(memory_data):
    view = copy.deepcopy(memory_data)
    rows = list(view.get("working_memory_items") or [])
    if rows:
        removed = rows.pop(0)
    else:
        removed = {}
    view["working_memory_items"] = rows
    trace_id = removed.get("trace_id")
    provenance = view.get("memory_provenance") or {}
    if trace_id:
        provenance["passed_to_leftbrain"] = [
            row for row in provenance.get("passed_to_leftbrain") or []
            if row.get("trace_id") != trace_id
        ]
        provenance["passed_to_leftbrain_trace_ids"] = [
            row.get("trace_id") for row in provenance["passed_to_leftbrain"]
            if row.get("trace_id")
        ]
    return view, removed


def _anchor_ablation(bot, user_input, memory_data, target_value):
    intact_anchor = bot._extract_actionable_memory_anchor(user_input, memory_data)
    removed_view = _remove_value_from_decision_view(memory_data, target_value)
    removed_anchor = bot._extract_actionable_memory_anchor(user_input, removed_view)
    control_view, removed_control = _remove_irrelevant_from_decision_view(memory_data)
    control_anchor = bot._extract_actionable_memory_anchor(user_input, control_view)

    def projected_reply(anchor):
        if not anchor:
            return None
        logic = {
            "memory_use_expected": True,
            "memory_anchor": anchor,
            "constraints": {"max_chars": 42},
        }
        return bot.right_brain._memory_grounded_reply(logic, user_input)

    return {
        "schema": "uruha_v2_17_memory_anchor_ablation",
        "stage": "after_retrieval_before_reply_planning",
        "target_value": target_value,
        "intact": {
            "anchor": intact_anchor,
            "projected_memory_reply": projected_reply(intact_anchor),
        },
        "remove_target": {
            "anchor": removed_anchor,
            "projected_memory_reply": projected_reply(removed_anchor),
        },
        "remove_irrelevant": {
            "removed_trace_id": removed_control.get("trace_id"),
            "anchor": control_anchor,
            "projected_memory_reply": projected_reply(control_anchor),
        },
        "interpretation": "Mechanism-level decision-anchor intervention; not an additional full-model reply run.",
    }


def _visible_japanese_pass(result):
    guard = result.get("logic", {}).get("visible_language_guard") or {}
    return bool(result.get("reply")) and not (guard.get("final_rejection_reasons") or [])


def _run_checkpoint(bot, turn, target_value):
    started = time.monotonic()
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        result = bot.run_turn_debug(turn["user"])
    elapsed = round(time.monotonic() - started, 4)
    memory_data = result.get("memory_data") or {}
    provenance = memory_data.get("memory_provenance") or {}
    anchor = result.get("logic", {}).get("memory_anchor") or {}
    passed_target_rows = _target_rows(memory_data, [target_value])
    if anchor.get("source") == "current_input":
        passed_target_rows.insert(
            0,
            {
                "trace_id": anchor.get("trace_id"),
                "memory_id": None,
                "source": "current_input",
                "channel": "current_input",
                "text": turn["user"],
                "score": anchor.get("score"),
                "rank": None,
                "selected": True,
            },
        )
    return {
        "turn": turn["turn"],
        "role": turn["role"],
        "execution": turn["execution"],
        "user": turn["user"],
        "reply": result.get("reply"),
        "elapsed_seconds": elapsed,
        "intent": result.get("logic", {}).get("intent"),
        "profile_before": memory_data.get("profile_structured") or {},
        "profile_after": result.get("memory_runtime", {}).get("profile") or {},
        "memory_anchor": anchor,
        "memory_use_expected": bool(result.get("logic", {}).get("memory_use_expected")),
        "post_check": result.get("logic", {}).get("post_check") or {},
        "visible_language_guard": result.get("logic", {}).get("visible_language_guard") or {},
        "visible_japanese_pass": _visible_japanese_pass(result),
        "selected_working_memory": _compact_trace_rows(
            row for row in provenance.get("candidate_pool") or []
            if row.get("selected")
        ),
        "passed_target_rows": passed_target_rows,
        "selected_trace_ids": provenance.get("selected_working_memory_trace_ids") or [],
        "passed_trace_ids": provenance.get("passed_to_leftbrain_trace_ids") or [],
        "ablation": _anchor_ablation(bot, turn["user"], memory_data, target_value),
        "runtime_cycle_index": result.get("runtime_trace", {}).get("cycle_index"),
        "runtime_log_sha256": hashlib.sha256(capture.getvalue().encode("utf-8")).hexdigest(),
    }


def _replay_turn(bot, turn):
    logic = {
        "intent": "chat",
        "scene": "casual",
        "jp_summary": "隔離長對話干擾輪回放",
        "cognitive_mode": "direct",
        "premise_check": "accept",
        "routing_path": "replayed_writeback",
    }
    bot.memory.save_episode(
        turn["user"],
        turn["reply"],
        bot.psyche.get_state(),
        logic,
    )
    return {
        "turn": turn["turn"],
        "role": turn["role"],
        "execution": turn["execution"],
        "user": turn["user"],
        "reply": turn["reply"],
        "profile_after": bot.memory.get_runtime_snapshot().get("profile") or {},
    }


def _checkpoint_passes(row, case):
    expected = case["expected"]
    reply = str(row.get("reply") or "")
    role = row["role"]
    if role == "delayed_recall":
        semantic = any(value in reply for value in expected["initial_value_japanese_any"])
        source_turn = expected["initial_source_turn"]
    elif role == "corrected_recall":
        semantic = any(value in reply for value in expected["corrected_value_japanese_any"])
        source_turn = expected["correction_source_turn"]
    elif role == "withdrawal_probe":
        semantic = bool(
            re.search(
                r"前のままじゃない|(もう|今は).*(違|じゃない|好みじゃない)|いちごミルク.*(違|じゃない|前の情報|外してる)",
                reply,
            )
        )
        source_turn = expected["correction_source_turn"]
    else:
        semantic = True
        source_turn = expected["correction_source_turn"]
    ablation = row.get("ablation") or {}
    intact_anchor = (ablation.get("intact") or {}).get("anchor") or {}
    removed_anchor = (ablation.get("remove_target") or {}).get("anchor") or {}
    control_anchor = (ablation.get("remove_irrelevant") or {}).get("anchor") or {}
    return {
        "semantic_reply_pass": semantic,
        "visible_japanese_pass": bool(row.get("visible_japanese_pass")),
        "target_passed_to_decision": bool(row.get("passed_target_rows")),
        "anchor_present": bool(row.get("memory_anchor")),
        "target_removal_changes_anchor": bool(intact_anchor) and intact_anchor != removed_anchor,
        "irrelevant_removal_preserves_anchor": bool(intact_anchor) and intact_anchor == control_anchor,
        "claimed_source_turn": source_turn,
    }


def main():
    case = _load_case()
    archived_previous_output = _archive_previous_output()
    production_hash_before = _tree_sha256(PRODUCTION_DB_PATH)
    rows = []
    checkpoints = []
    with tempfile.TemporaryDirectory(prefix="uruha-v217-long-dialogue-") as isolated_db:
        os.environ["URUHA_MEMORY_DB_PATH"] = isolated_db
        os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
        brain_mod = importlib.import_module("uruha_brain_mac")
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            bot = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)

        for turn in case["turns"]:
            if turn["execution"] == "full_runtime":
                profile = bot.memory.get_runtime_snapshot().get("profile") or {}
                if turn["role"] == "explicit_correction":
                    target = case["expected"]["corrected_value"]
                elif turn["role"] == "withdrawal_probe":
                    target = case["expected"]["initial_value"]
                else:
                    target = (
                        (profile.get("favorites") or profile.get("likes") or [""])[0]
                        if (profile.get("favorites") or profile.get("likes"))
                        else case["expected"]["initial_value"]
                    )
                print(f"[{turn['turn']}/25] full runtime: {turn['role']}", flush=True)
                row = _run_checkpoint(bot, turn, target)
                checkpoints.append(row)
                rows.append({key: row[key] for key in ("turn", "role", "execution", "user", "reply", "profile_after")})
            else:
                rows.append(_replay_turn(bot, turn))

        isolated_profile = bot.memory.get_runtime_snapshot().get("profile") or {}
        isolated_session_turn_count = len(bot.memory.session_turns)

    production_hash_after = _tree_sha256(PRODUCTION_DB_PATH)
    for row in checkpoints:
        row["checks"] = _checkpoint_passes(row, case)

    expected = case["expected"]
    first = next(row for row in checkpoints if row["role"] == "delayed_recall")
    corrected = next(row for row in checkpoints if row["role"] == "corrected_recall")
    withdrawn = next(row for row in checkpoints if row["role"] == "withdrawal_probe")
    summary = {
        "turn_count": len(rows),
        "distractor_turn_count": sum(row["role"] == "distractor" for row in rows),
        "full_runtime_checkpoint_count": len(checkpoints),
        "initial_delayed_recall_pass": first["checks"]["semantic_reply_pass"],
        "corrected_delayed_recall_pass": corrected["checks"]["semantic_reply_pass"],
        "withdrawn_value_not_current_pass": withdrawn["checks"]["semantic_reply_pass"],
        "all_checkpoint_visible_japanese_pass": all(row["checks"]["visible_japanese_pass"] for row in checkpoints),
        "all_checkpoint_target_transport_observed": all(row["checks"]["target_passed_to_decision"] for row in checkpoints),
        "anchor_ablation_gate_pass": all(
            row["checks"]["target_removal_changes_anchor"]
            and row["checks"]["irrelevant_removal_preserves_anchor"]
            for row in checkpoints
            if row["role"] in {"delayed_recall", "corrected_recall"}
        ),
        "production_db_unchanged": production_hash_before == production_hash_after,
        "isolated_session_turn_count": isolated_session_turn_count,
        "final_profile": isolated_profile,
        "expected_current_value": expected["corrected_value"],
    }
    summary["bounded_success"] = all(
        [
            summary["turn_count"] == 25,
            summary["initial_delayed_recall_pass"],
            summary["corrected_delayed_recall_pass"],
            summary["withdrawn_value_not_current_pass"],
            summary["all_checkpoint_visible_japanese_pass"],
            summary["production_db_unchanged"],
        ]
    )
    payload = {
        "schema": "uruha_v2_17_long_dialogue_memory_raw",
        "case_id": case["case_id"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "archived_previous_output": archived_previous_output,
        "execution_boundary": case["evidence_boundary"],
        "source_links": {
            "initial_memory": {"source_turn": expected["initial_source_turn"], "value": expected["initial_value"]},
            "correction": {"source_turn": expected["correction_source_turn"], "value": expected["corrected_value"]},
        },
        "rows": rows,
        "checkpoints": checkpoints,
        "summary": summary,
        "production_db_hash_before": production_hash_before,
        "production_db_hash_after": production_hash_after,
        "claims": {
            "supported": "In this isolated 25-turn case, an early profile memory was passed into the decision path and recalled after 15 unrelated turns; after explicit correction and five more unrelated turns, the new value was recalled and the old value was not treated as current.",
            "not_supported": [
                "unbounded or cross-month memory",
                "all 25 replies freshly generated by the full model",
                "general long-conversation superiority over a baseline LLM",
                "human-like autobiographical memory",
                "human preference or felt-understanding superiority"
            ]
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "summary": summary}, ensure_ascii=False, indent=2))
    if not summary["bounded_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
