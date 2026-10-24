"""Product-only evidence boundary for compact-plan surface decoration.

The compact planner already returns a selected Japanese core.  On ordinary
direct-chat turns, legacy surface code used to append a fixed closing clause and
then prepend a hash-selected discourse marker.  This adapter keeps the existing
sanitizer, refinement and final visible-language firewall, but prevents those
two decorations when no plan evidence authorizes them.
"""
from contextvars import ContextVar
from copy import deepcopy
import hashlib


SCHEMA = "uruha_contextual_expression_commit_p2"
_TRACE = ContextVar("contextual_expression_commit_p2", default=None)
_INSTALLED = False
_ORIGINAL_FINALIZE = None
_ORIGINAL_SPEECH_VARIANTS = None
_ORIGINAL_REFINE = None

_PROTECTED_SCENES = {"support", "boundary", "refusal", "ooc_defense", "jealousy"}
_MEMORY_INTENTS = {
    "recall_name",
    "recall_preference",
    "recall_favorite",
    "recall_dislike",
    "memory_correction",
    "recall_recent",
    "memory_uncertain",
    "memory_unknown",
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def compact_call_completed(logic_data):
    audit = ((logic_data or {}).get("bounded_slow_path_m21") or {}).get(
        "compact_general_plan_p2"
    ) or {}
    return bool(
        audit.get("schema") == "uruha_compact_general_plan_p2"
        and audit.get("completed") is True
        and audit.get("candidate_count") == 3
    )


def expression_commit_scope(right_brain, logic_data, user_input):
    """Return a typed eligibility decision without inspecting phrase content."""
    logic_data = logic_data or {}
    if not compact_call_completed(logic_data):
        return False, "no_completed_compact_planner_call", ""
    if right_brain._structured_surface_required():
        return False, "structured_surface_provider_owns_realization", ""
    if logic_data.get("memory_use_expected") or logic_data.get("intent") in _MEMORY_INTENTS:
        return False, "memory_surface_contract", ""
    if logic_data.get("scene") in _PROTECTED_SCENES:
        return False, "protected_scene", ""
    dialogue_act = logic_data.get("dialogue_act") or right_brain._dialogue_act_from_plan(
        logic_data, user_input
    )
    if dialogue_act != "direct_chat_answer":
        return False, "non_direct_chat_act", str(dialogue_act or "")
    if logic_data.get("response_mode") not in {"direct_answer", "direct_answer_with_hedge"}:
        return False, "non_direct_response_mode", str(dialogue_act)
    return True, "completed_compact_direct_chat", str(dialogue_act)


def _new_trace(logic_data, dialogue_act):
    core = str((logic_data or {}).get("core_message_jp") or "").strip()
    return {
        "schema": SCHEMA,
        "status": "active",
        "activation_basis": "completed_compact_direct_chat",
        "dialogue_act": dialogue_act,
        "selected_core_message_jp": core,
        "selected_core_sha256": _digest(core),
        "selected_core_length": len(core),
        "fixed_direct_chat_suffix_authorized": False,
        "hash_selected_prefix_authorized": False,
        "suppressed_decorators": [],
        "legacy_fixed_surface_accessed_for_active_path": False,
        "model_call_added": False,
        "long_term_memory_write": False,
        "final_visible_surface_matched": None,
    }


def materialize_expression_commit_trace(result):
    """Put the actual expression decision in the existing runtime graph."""
    logic = result.get("logic") or {}
    payload = logic.get("contextual_expression_commit_p2")
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != "contextual_expression_commit_p2"]
    if isinstance(payload, dict) and payload.get("schema") == SCHEMA:
        guard = logic.get("visible_language_guard") or {}
        final_surface = str(
            guard.get("final_reply")
            or result.get("reply")
            or result.get("response")
            or payload.get("pre_language_guard_surface")
            or ""
        ).strip()
        payload = deepcopy(payload)
        payload["final_visible_surface_jp"] = final_surface
        payload["final_visible_surface_sha256"] = _digest(final_surface)
        payload["visible_language_guard_applied"] = bool(guard)
        payload["visible_language_guard_repair_action"] = guard.get("repair_action")
        payload["final_visible_surface_matched"] = bool(
            final_surface and final_surface == payload.get("pre_language_guard_surface")
        )
        logic["contextual_expression_commit_p2"] = payload
        index = next(
            (i + 1 for i, row in enumerate(rows) if row.get("label") == "compact_general_plan_p2"),
            next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(
            index,
            {
                "stage": "surface",
                "label": "contextual_expression_commit_p2",
                "payload": deepcopy(payload),
                "salience": 0.97,
            },
        )
    trace["blackboard"] = rows


def install_contextual_expression_commit_p2():
    global _INSTALLED, _ORIGINAL_FINALIZE, _ORIGINAL_SPEECH_VARIANTS, _ORIGINAL_REFINE
    if _INSTALLED:
        return False

    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    previous_speak = RightBrain.speak
    previous_finalize = RightBrain._finalize_surface_reply
    previous_speech_variants = RightBrain._speech_plan_variants
    previous_refine = RightBrain._refine_conversational_reply
    previous_emit = UruhaBrainV4_Mac.emit_response_if_ready
    previous_run = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_FINALIZE = previous_finalize
    _ORIGINAL_SPEECH_VARIANTS = previous_speech_variants
    _ORIGINAL_REFINE = previous_refine

    def speak(self, user_input, logic_data, memory_data, current_psyche):
        eligible, reason, dialogue_act = expression_commit_scope(self, logic_data, user_input)
        if not eligible:
            return previous_speak(self, user_input, logic_data, memory_data, current_psyche)
        audit = _new_trace(logic_data, dialogue_act)
        token = _TRACE.set(audit)
        try:
            reply = previous_speak(self, user_input, logic_data, memory_data, current_psyche)
            audit["pre_language_guard_surface"] = str(reply or "").strip()
            audit["pre_language_guard_surface_sha256"] = _digest(reply)
            audit["status"] = "surface_committed"
            logic_data["contextual_expression_commit_p2"] = deepcopy(audit)
            return reply
        finally:
            _TRACE.reset(token)

    def speech_variants(self, reply, logic_data, user_input, memory_data=None):
        audit = _TRACE.get()
        eligible, _, dialogue_act = expression_commit_scope(self, logic_data, user_input)
        if audit is None or not eligible or dialogue_act != "direct_chat_answer":
            return previous_speech_variants(
                self, reply, logic_data, user_input, memory_data=memory_data
            )
        core = str(logic_data.get("core_message_jp") or "").strip()
        max_chars = int((logic_data.get("constraints") or {}).get("max_chars") or 28)
        candidate = self._sanitize_reply(core, max_chars=max_chars) if core else ""
        if "fixed_direct_chat_suffix" not in audit["suppressed_decorators"]:
            audit["suppressed_decorators"].append("fixed_direct_chat_suffix")
        audit["direct_chat_variant_source"] = "selected_compact_core"
        audit["direct_chat_variant_jp"] = candidate
        audit["direct_chat_variant_sha256"] = _digest(candidate)
        return [candidate] if candidate else []

    def finalize(self, reply, logic_data, user_input, max_chars):
        audit = _TRACE.get()
        eligible, _, dialogue_act = expression_commit_scope(self, logic_data, user_input)
        if audit is None or not eligible or dialogue_act != "direct_chat_answer":
            return previous_finalize(self, reply, logic_data, user_input, max_chars)
        candidate = self._sanitize_reply(str(reply or ""), max_chars=max_chars)
        if candidate and "hash_selected_discourse_prefix" not in audit["suppressed_decorators"]:
            audit["suppressed_decorators"].append("hash_selected_discourse_prefix")
        audit["surface_before_prefix_gate_jp"] = candidate
        audit["surface_before_prefix_gate_sha256"] = _digest(candidate)
        return candidate

    def refine(self, reply, logic_data, user_input, memory_data=None):
        eligible, _, dialogue_act = expression_commit_scope(self, logic_data, user_input)
        core = str((logic_data or {}).get("core_message_jp") or "").strip()
        max_chars = int(((logic_data or {}).get("constraints") or {}).get("max_chars") or 28)
        candidate = self._sanitize_reply(str(reply or ""), max_chars=max_chars)
        selected_core = self._sanitize_reply(core, max_chars=max_chars) if core else ""
        if (
            eligible
            and dialogue_act == "direct_chat_answer"
            and candidate
            and selected_core
            and candidate == selected_core
        ):
            audit = _TRACE.get()
            if audit is not None:
                audit["short_complete_core_enrichment_authorized"] = False
                if "density_only_core_enrichment" not in audit["suppressed_decorators"]:
                    audit["suppressed_decorators"].append("density_only_core_enrichment")
            return candidate
        return previous_refine(
            self, reply, logic_data, user_input, memory_data=memory_data
        )

    RightBrain.speak = speak
    RightBrain._speech_plan_variants = speech_variants
    RightBrain._finalize_surface_reply = finalize
    RightBrain._refine_conversational_reply = refine

    def finish(self, result):
        materialize_expression_commit_trace(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if (
            self.runtime.turn_traces
            and self.runtime.turn_traces[-1].get("cycle_index")
            == result["runtime_trace"].get("cycle_index")
        ):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def emit(self, event, tick_result):
        return finish(self, previous_emit(self, event, tick_result))

    def run(self, user_input, input_context=None):
        return finish(self, previous_run(self, user_input, input_context=input_context))

    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True
