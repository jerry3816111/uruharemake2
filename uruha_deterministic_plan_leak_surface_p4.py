"""Opt-in final speech-act repair for a deterministic short-confusion plan leak.

The existing model-candidate gate rejects plan/instruction wording, but a
selected deterministic surface can bypass that gate.  This adapter applies
that *same* rejection reason at the last visible boundary.  It does not
change the surprise route, the protected crisis/abuse intents, or memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib


LABEL = "deterministic_plan_leak_surface_p4"
SCHEMA = "uruha_deterministic_plan_leak_surface_p4_v1"
_INSTALLED = False
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_EMIT = None


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def realize_short_confusion_surface_p4(
    visible: str,
    logic: dict,
    rejection_reasons: list[str],
) -> tuple[str, dict]:
    """Turn a confirmed metaplan into the requested user-facing speech act.

    The source-frame bit only distinguishes a reported third-party statement
    from other surprise.  Neither branch asserts which report is true.
    """
    visible = str(visible or "")
    logic = logic if isinstance(logic, dict) else {}
    selection = logic.get("model_surface_selection") or {}
    reasons = list(dict.fromkeys(rejection_reasons or []))
    eligible = bool(
        logic.get("routing_path") == "low_road"
        and logic.get("intent") == "short_confusion"
        and logic.get("surface_act") == "plain_reply"
        and selection.get("selected_source") == "deterministic"
        and {"instruction_or_plan_leak", "japanese_response_plan_leak"}.intersection(reasons)
    )
    frame = ((logic.get("semantic_persona_surface_verifier_m39") or {}).get("source_frame") or {})
    third_party = frame.get("third_party_present") is True
    if eligible and third_party:
        final = "ん、そう聞いたのか。あんたはどう聞いてる？"
        act = "ask_user_view_without_adopting_third_party_claim"
    elif eligible:
        final = "ん、そこもうちょい聞かせて。"
        act = "low_pressure_open_clarification"
    else:
        final = visible
        act = "not_applicable"
    trace = {
        "schema": SCHEMA,
        "status": "performed" if eligible else "not_applicable",
        "eligibility": "low_road_short_confusion_selected_deterministic_plan_leak",
        "existing_rejection_reasons": reasons if eligible else [],
        "speech_act": act,
        "third_party_source_frame_observed": third_party if eligible else None,
        "before_sha256": _sha(visible),
        "final_sha256": _sha(final),
        "changed": final != visible,
        "model_calls_added": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "fact_memory_write_count": 0,
        "profile_write_count": 0,
        "claim_boundary": "bounded selected deterministic speech-act repair, not open-domain understanding or protected-route reclassification",
    }
    return final, trace


def _append_node(result: dict) -> dict:
    logic = (result or {}).get("logic") or {}
    payload = deepcopy(logic.get(LABEL) or {})
    if payload.get("status") != "performed":
        return result
    runtime_trace = result.get("runtime_trace") or {}
    rows = [row for row in list(runtime_trace.get("blackboard") or []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows))
    rows.insert(index, {"stage": "surface", "label": LABEL, "payload": payload, "salience": 1.0})
    runtime_trace["blackboard"] = rows
    runtime_trace[LABEL] = deepcopy(payload)
    result["runtime_trace"] = runtime_trace
    return result


def _sync_selected_short_history(right_brain, before: str, final: str, intent: str) -> str:
    """Keep the current short-term surface history aligned with actual speech.

    ``speak`` records its selected candidate before the final visible guard.
    Only the exact current assistant row may be changed; never rewrite older
    turns, user input, episodic facts, or an unrelated repair candidate.
    """
    history = getattr(right_brain, "history", None)
    if not isinstance(history, list) or not history:
        return "history_unavailable"
    row = history[-1]
    if not isinstance(row, dict) or row.get("role") != "assistant" or row.get("content") != before:
        return "current_assistant_mismatch"
    if str(row.get("intent") or "") != intent:
        return "current_intent_mismatch"
    counters = (
        ("reply_variant_counts", before, final),
        ("intent_variant_counts", (intent, before), (intent, final)),
        (
            "normalized_reply_counts",
            right_brain._normalize_reply_key(before),
            right_brain._normalize_reply_key(final),
        ),
        (
            "intent_normalized_counts",
            (intent, right_brain._normalize_reply_key(before)),
            (intent, right_brain._normalize_reply_key(final)),
        ),
    )
    for name, old_key, _ in counters:
        count = getattr(right_brain, name, None)
        if count is None or count.get(old_key, 0) < 1:
            return "counter_mismatch"
    row["content"] = final
    for name, old_key, new_key in counters:
        if old_key == new_key:
            continue
        count = getattr(right_brain, name)
        count[old_key] -= 1
        count[new_key] += 1
    return "current_assistant_synced"


def guard_selected_deterministic_surface_p4(
    right_brain, visible, logic_data, *, user_input="", memory_data=None
):
    """Run the existing candidate check on a selected deterministic surface."""
    if not isinstance(logic_data, dict):
        return visible
    selection = logic_data.get("model_surface_selection") or {}
    if (
        logic_data.get("routing_path") != "low_road"
        or logic_data.get("intent") != "short_confusion"
        or selection.get("selected_source") != "deterministic"
    ):
        return visible
    max_chars = int((logic_data.get("constraints") or {}).get("max_chars") or 48)
    reasons = right_brain._model_candidate_rejection_reasons(
        visible, logic_data, max_chars, user_input=user_input
    )
    final, trace = realize_short_confusion_surface_p4(visible, logic_data, reasons)
    if trace["status"] != "performed":
        return visible
    # The repair itself must clear the same plan-leak gate and the existing
    # language firewall; otherwise fail closed at this boundary.
    final_reasons = right_brain._model_candidate_rejection_reasons(
        final, logic_data, max_chars, user_input=user_input
    )
    language_reasons = right_brain._user_visible_language_rejection_reasons(
        final, user_input=user_input, logic_data=logic_data, memory_data=memory_data
    )
    if final_reasons or language_reasons:
        raise RuntimeError("deterministic_plan_leak_repair_not_visible_safe")
    guard = logic_data.get("visible_language_guard")
    if not isinstance(guard, dict) or guard.get("final_reply") != visible:
        raise RuntimeError("deterministic_plan_leak_guard_trace_mismatch")
    guard["final_reply"] = final
    guard["final_reply_sha256"] = _sha(final)
    guard["changed"] = True
    guard["repair_action"] = "post_guard_deterministic_speech_act_p4"
    guard["final_rejection_reasons"] = []
    selected_candidate = str(selection.get("selected_candidate") or "")
    trace["short_history_selected_sha256"] = _sha(selected_candidate)
    trace["short_history_sync_status"] = (
        _sync_selected_short_history(
            right_brain, selected_candidate, final,
            str(logic_data.get("intent") or ""),
        )
        if selected_candidate else "selected_candidate_unavailable"
    )
    logic_data[LABEL] = trace
    right_brain._bind_forbidden_projection_shadow_visible_reply(logic_data, final)
    return final


def install_deterministic_plan_leak_surface_p4() -> bool:
    """Install last in the opt-in product entry, preserving prior guards."""
    global _INSTALLED, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_EMIT
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    if _INSTALLED:
        return False
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready

    def guarded_with_plan_leak_surface(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD(
            self, reply, logic_data, user_input=user_input, memory_data=memory_data
        )
        return guard_selected_deterministic_surface_p4(
            self, visible, logic_data, user_input=user_input, memory_data=memory_data
        )

    def emit_with_plan_leak_trace(self, event, tick_result):
        result = _ORIGINAL_EMIT(self, event, tick_result)
        result = _append_node(result)
        trace = ((result or {}).get("runtime_trace") or {}).get(LABEL)
        if trace and getattr(self.runtime, "turn_traces", None):
            from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

            self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
            sync_current_history_m41_1(result)
            if self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"):
                self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_plan_leak_surface
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_plan_leak_trace
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "realize_short_confusion_surface_p4",
    "guard_selected_deterministic_surface_p4", "install_deterministic_plan_leak_surface_p4",
]
