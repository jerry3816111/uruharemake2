"""Exact-record memory interventions for the V1 causal mechanism experiment."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import uruha_memory_runtime as umr


C0 = "c0_intact_target_and_irrelevant"
T1 = "t1_remove_exact_target"
T2 = "t2_replace_exact_target"
N1 = "n1_remove_exact_irrelevant"
CONDITIONS = (C0, T1, T2, N1)
AUDIT_ONLY_PROVENANCE_KEYS = ("retrieved_candidates", "candidate_pool")


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if len(cases) != 8 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("memory intervention cases must contain eight unique rows")
    return cases


def target_memory_id(case):
    return f"mici-v1-{case['id']}-target"


def irrelevant_memory_id(case):
    return f"mici-v1-{case['id']}-irrelevant"


def replacement_memory_id(case):
    return f"mici-v1-{case['id']}-replacement"


def stored_trace_id(memory_id):
    return f"stored:episode:{memory_id}"


def target_trace_id(case):
    return stored_trace_id(target_memory_id(case))


def irrelevant_trace_id(case):
    return stored_trace_id(irrelevant_memory_id(case))


def replacement_trace_id(case):
    return stored_trace_id(replacement_memory_id(case))


def fixture_rows(case):
    metadata = {
        "source": "memory_item_causal_intervention_v1_fixture",
        "status": "active",
        "speakability": "explicit_ok",
        "last_accessed_at": "2026-08-05 00:00:00",
        "decay_flag": False,
        "decay_multiplier": 1.0,
        "self_relevance": True,
    }
    return [
        {
            "id": target_memory_id(case),
            "text": case["target_text"],
            "metadata": {**metadata, "fixture_role": "target"},
        },
        {
            "id": irrelevant_memory_id(case),
            "text": case["irrelevant_text"],
            "metadata": {**metadata, "fixture_role": "irrelevant"},
        },
    ]


def seed_case(memory, case):
    rows = fixture_rows(case)
    memory.episode_col.add(
        ids=[row["id"] for row in rows],
        documents=[row["text"] for row in rows],
        metadatas=[row["metadata"] for row in rows],
    )


def _trace_ids(rows):
    return [str(row.get("trace_id") or "") for row in rows or []]


def capture_retrieval_audit(memory_data, case):
    provenance = copy.deepcopy(memory_data.get("memory_provenance") or {})
    selected = set(provenance.get("selected_working_memory_trace_ids") or [])
    passed = set(provenance.get("passed_to_leftbrain_trace_ids") or [])
    target_id = target_trace_id(case)
    irrelevant_id = irrelevant_trace_id(case)
    return {
        "schema": provenance.get("schema"),
        "retrieved_candidate_count": provenance.get("retrieved_candidate_count", 0),
        "candidate_count": provenance.get("candidate_count", 0),
        "selected_trace_ids": sorted(selected),
        "passed_trace_ids": sorted(passed),
        "target_selected": target_id in selected,
        "target_passed": target_id in passed,
        "irrelevant_selected": irrelevant_id in selected,
        "irrelevant_passed": irrelevant_id in passed,
        "retrieval_audit_sha256": canonical_sha256(provenance),
    }


def strip_audit_only_provenance(memory_data):
    provenance = memory_data.get("memory_provenance") or {}
    for key in AUDIT_ONLY_PROVENANCE_KEYS:
        provenance.pop(key, None)


def _split_summary(value):
    return [part.strip() for part in str(value or "").split("||") if part.strip()]


def _rewrite_episode_summary(memory_data, old_text, new_text=None):
    parts = _split_summary(memory_data.get("episodes"))
    rewritten = []
    for part in parts:
        if part == old_text:
            if new_text:
                rewritten.append(new_text)
            continue
        rewritten.append(part)
    memory_data["episodes"] = " || ".join(rewritten) if rewritten else "無相關經歷"


def _replace_row(row, case):
    replaced = copy.deepcopy(row)
    replaced.update(
        {
            "trace_id": replacement_trace_id(case),
            "memory_id": replacement_memory_id(case),
            "text": case["replacement_text"],
            "intervention_origin_trace_id": target_trace_id(case),
        }
    )
    return replaced


def _rewrite_rows(rows, remove_id, case=None):
    rewritten = []
    for row in rows or []:
        if row.get("trace_id") != remove_id:
            rewritten.append(copy.deepcopy(row))
        elif case is not None:
            rewritten.append(_replace_row(row, case))
    return rewritten


def _refresh_runtime_memory(bot, memory_data):
    bot.runtime.working_memory = list(memory_data.get("working_memory_items") or [])
    bot.runtime.last_attention_frame = bot._build_attention_frame(
        bot.runtime.last_user_input,
        memory_data,
    )
    for node in bot.runtime.blackboard:
        if node.get("label") == "working_memory":
            node["payload"] = bot._trace_payload(
                {
                    "summary": memory_data.get("working_memory_summary"),
                    "items": copy.deepcopy(bot.runtime.working_memory),
                    "attention_frame": copy.deepcopy(bot.runtime.last_attention_frame),
                }
            )
        elif node.get("label") == "attention_frame":
            node["payload"] = bot._trace_payload(bot.runtime.last_attention_frame)


def apply_condition(bot, event, case, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown memory intervention condition: {condition}")
    memory_data = event["memory_data"]
    strip_audit_only_provenance(memory_data)
    remove_id = None
    replacement_case = None
    if condition == T1:
        remove_id = target_trace_id(case)
    elif condition == T2:
        remove_id = target_trace_id(case)
        replacement_case = case
    elif condition == N1:
        remove_id = irrelevant_trace_id(case)

    if remove_id:
        memory_data["working_memory_items"] = _rewrite_rows(
            memory_data.get("working_memory_items"),
            remove_id,
            replacement_case,
        )
        provenance = memory_data.get("memory_provenance") or {}
        provenance["passed_to_leftbrain"] = _rewrite_rows(
            provenance.get("passed_to_leftbrain"),
            remove_id,
            replacement_case,
        )
        provenance["passed_to_leftbrain_trace_ids"] = list(
            dict.fromkeys(_trace_ids(provenance["passed_to_leftbrain"]))
        )
        old_text = (
            case["target_text"]
            if remove_id == target_trace_id(case)
            else case["irrelevant_text"]
        )
        _rewrite_episode_summary(
            memory_data,
            old_text,
            case["replacement_text"] if replacement_case else None,
        )

    memory_data["working_memory_summary"] = umr.working_memory_summary(
        memory_data.get("working_memory_items") or []
    )
    post_ids = _trace_ids(memory_data.get("working_memory_items"))
    intervention = {
        "condition": condition,
        "stage": "after_retrieval_before_leftbrain",
        "removed_trace_id": remove_id,
        "replacement_trace_id": replacement_trace_id(case) if replacement_case else None,
        "post_intervention_working_memory_trace_ids": post_ids,
        "post_intervention_passed_trace_ids": list(
            (memory_data.get("memory_provenance") or {}).get("passed_to_leftbrain_trace_ids")
            or []
        ),
    }
    memory_data.setdefault("memory_provenance", {})["intervention"] = intervention
    _refresh_runtime_memory(bot, memory_data)
    return intervention


def decision_view(memory_data):
    return {
        "working_memory_items": copy.deepcopy(memory_data.get("working_memory_items") or []),
        "working_memory_summary": memory_data.get("working_memory_summary"),
        "episodes": memory_data.get("episodes"),
        "wisdom": memory_data.get("wisdom"),
        "procedural": memory_data.get("procedural"),
        "procedural_summary": memory_data.get("procedural_summary"),
        "profile": memory_data.get("profile"),
        "profile_structured": copy.deepcopy(memory_data.get("profile_structured") or {}),
        "recent_dialogue": memory_data.get("recent_dialogue"),
        "recent_turns": copy.deepcopy(memory_data.get("recent_turns") or []),
        "short_term_summary": memory_data.get("short_term_summary"),
        "passed_to_leftbrain": copy.deepcopy(
            (memory_data.get("memory_provenance") or {}).get("passed_to_leftbrain") or []
        ),
    }


def contains_any(value, markers):
    text = json.dumps(value, ensure_ascii=False).lower()
    return any(str(marker).lower() in text for marker in markers or [])


def plan_projection(logic):
    anchor = logic.get("memory_anchor") or {}
    speech = logic.get("human_speech_plan") or {}
    return {
        "intent": logic.get("intent"),
        "scene": logic.get("scene"),
        "response_mode": logic.get("response_mode"),
        "surface_act": logic.get("surface_act"),
        "reply_goal": logic.get("reply_goal"),
        "core_message_jp": logic.get("core_message_jp"),
        "memory_anchor": {
            key: anchor.get(key)
            for key in ("kind", "value", "jp_anchor", "source_text", "source")
        },
        "speech_plan": {
            key: copy.deepcopy(speech.get(key))
            for key in ("content_units", "speech_moves", "grounding_terms")
        },
    }


def score_outcome(case, condition, retrieval_audit, event, logic, reply, elapsed, call_rows):
    memory_data = event["memory_data"]
    view = decision_view(memory_data)
    projection = plan_projection(logic)
    anchor = logic.get("memory_anchor") or {}
    target_id = target_trace_id(case)
    replacement_id = replacement_trace_id(case)
    forbidden_target_in_view = condition in {T1, T2} and contains_any(
        view,
        [case["target_text"], target_id, *case["target_markers"]],
    )
    forbidden_irrelevant_in_view = condition == N1 and contains_any(
        view,
        [case["irrelevant_text"], irrelevant_trace_id(case)],
    )
    return {
        "condition": condition,
        "retrieval_audit": retrieval_audit,
        "intervention": copy.deepcopy(
            (memory_data.get("memory_provenance") or {}).get("intervention") or {}
        ),
        "decision_view_sha256": canonical_sha256(view),
        "decision_view_target_absent_when_required": not forbidden_target_in_view,
        "decision_view_irrelevant_absent_when_required": not forbidden_irrelevant_in_view,
        "memory_anchor_trace_id": anchor.get("trace_id"),
        "memory_anchor_kind": anchor.get("kind"),
        "target_anchor": anchor.get("trace_id") == target_id,
        "replacement_anchor": anchor.get("trace_id") == replacement_id,
        "target_marker_in_plan": contains_any(projection, case["target_markers"]),
        "replacement_marker_in_plan": contains_any(projection, case["replacement_markers"]),
        "target_marker_in_reply": contains_any(reply, case["target_markers"]),
        "replacement_marker_in_reply": contains_any(reply, case["replacement_markers"]),
        "plan_projection": projection,
        "plan_sha256": canonical_sha256(projection),
        "reply": str(reply or ""),
        "elapsed_seconds": round(float(elapsed), 6),
        "leftbrain_call_count": len(call_rows),
        "leftbrain_calls": copy.deepcopy(call_rows),
        "transport_error_count": sum(
            row.get("status") != "returned" for row in call_rows
        ),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


def expected_sequence(cases):
    ranked = sorted(cases, key=lambda case: canonical_sha256(case["id"]))
    sequence = []
    for index, case in enumerate(ranked):
        order = CONDITIONS[index % len(CONDITIONS) :] + CONDITIONS[: index % len(CONDITIONS)]
        sequence.extend((case, condition) for condition in order)
    return sequence
