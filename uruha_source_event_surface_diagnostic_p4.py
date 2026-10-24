"""Opt-in, same-turn source-event surface diagnostic.

The raw object/action slot is ephemeral. Only allowlisted digests and status
codes may enter logic, blackboard, episode metadata, or Web trace. This narrow
Japanese self-report grammar is a diagnostic, not general pragmatic or safety
understanding; its final verifier observes rather than blocking a bad reply.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re

from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4
from uruha_source_event_core_utility_p4 import (
    SCHEMA as CORE_SCHEMA,
    _NEGATION,
    _QUOTE,
    _REPORT,
    _SAFE_EVALUATION,
    _source_event,
    _valid_handoff,
)


SCHEMA = "uruha_source_event_surface_diagnostic_p4_v1"
ARM_ENV = "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"
_SENSITIVE_MEDICATION = re.compile(r"(?:薬|服用|投薬|処方|用量|ミリグラム|mg)", re.I)
_SENSITIVE_DOSE_ACTION = re.compile(r"(?:増や|減ら|やめ|止め|変え)")
# This opt-in auto-praise surface cannot rely on the normal planner's safety
# route: a harmful completed act may still reach full_planner. Prefer abstain
# on these recognizable harms; this finite veto is not a general safety model.
_UNSAFE_PRAISE_ACTION = re.compile(
    r"(?:盗|奪|騙|詐欺|殴|叩|刺|殺|傷つけ|虐待|いじめ|脅|放火|燃や|爆破|破壊|壊|侵入|毒|過量|飲みすぎ|自傷|自殺)"
)
_LATIN = re.compile(r"[A-Za-z]")
# For a harmful source, even a praise phrase followed by the usual persona
# tail is an endorsement. This is an audit signal, not a reply safety filter.
_PRAISE = re.compile(r"(?:やるじゃん|やるな|いいじゃん|いいね|すごい|頑張ったね|頑張ったな|えらいね|よかったね|おめでとう)")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceEventSlot:
    input_sha256: str
    event_sha256: str
    object_sha256: str
    action_sha256: str
    object_text: str
    action_text: str
    first_time: str
    requested_act: str


def _receipt(status: str, source: str, *, slot: SourceEventSlot | None = None,
             reason: str | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason or status,
        "input_sha256": _sha(source) if isinstance(source, str) else None,
        "event_sha256": slot.event_sha256 if slot else None,
        "object_sha256": slot.object_sha256 if slot else None,
        "action_sha256": slot.action_sha256 if slot else None,
        "first_time": slot.first_time if slot else None,
        "requested_act": slot.requested_act if slot else None,
        "raw_dialogue_persisted": False,
        "raw_dialogue_scope": "new_diagnostic_receipt_only",
        "existing_turn_episode_may_store_user_input": True,
        "private_state_truth_claimed": False,
        "model_call_added": False,
        "claim_boundary": "finite_current_user_japanese_self_report_audit_only",
    }


def _unsafe_praise_context(obj: str, action: str) -> str | None:
    if _SENSITIVE_MEDICATION.search(obj) and _SENSITIVE_DOSE_ACTION.search(action):
        return "medication_dose_safety_context"
    if _UNSAFE_PRAISE_ACTION.search(action):
        return "unsafe_completed_action_context"
    return None


def admit_source_event_slot_p4(source: str, handoff: object, logic: object) -> tuple[SourceEventSlot | None, dict]:
    """Revalidate original current-turn source and the actually completed route.

    `handoff` must come from this turn's transient cognitive_tick result, never
    from persisted logic or user-provided fields. The raw slot is not serializable
    into product traces by this module; callers must keep it local.
    """
    if not isinstance(source, str) or not isinstance(logic, dict):
        return None, _receipt("not_authorized", source, reason="invalid_input")
    if os.getenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT") == "1":
        return None, _receipt("not_authorized", source, reason="f8_prompt_must_be_off")
    expected = classify_direct_reply_act_p4(source)
    if not _valid_handoff(source, handoff, expected) or expected["requested_act"] != "brief_encouragement":
        return None, _receipt("not_authorized", source, reason="invalid_same_turn_handoff")
    m21 = logic.get("bounded_slow_path_m21") or {}
    if not (
        isinstance(m21, dict)
        and m21.get("route") == "full_planner"
        and m21.get("status") == "completed_within_budget"
        and m21.get("fallback_used") is False
        and m21.get("model_call_completed") is True
    ):
        return None, _receipt("not_authorized", source, reason="not_completed_full_m21")
    route = logic.get("direct_reply_act_planner_handoff_p4") or {}
    if not (
        isinstance(route, dict)
        and route.get("arm") == "control"
        and route.get("status") == "control_no_handoff"
        and route.get("actual_route") == "full_planner"
        and route.get("planner_prompt_injected") is False
        and route.get("input_sha256") == expected["input_sha256"]
        and route.get("cue_sha256") == expected["cue_sha256"]
        and route.get("requested_act") == "brief_encouragement"
        and route.get("m33_status") == "not_applicable"
    ):
        return None, _receipt("not_authorized", source, reason="route_receipt_mismatch")
    event = _source_event(source, expected["cue_span"][0])
    if event is None:
        return None, _receipt("not_authorized", source, reason="unsupported_source_event")
    sentence, obj, action = event
    coverage = logic.get("source_event_core_utility_p4") or {}
    if not (
        isinstance(coverage, dict)
        and coverage.get("schema") == CORE_SCHEMA
        and coverage.get("eligible") is True
        and coverage.get("status") == "no_grounded_candidate"
        and coverage.get("compact_completed") is True
        and coverage.get("compact_candidate_count") == 3
        and coverage.get("m21_fallback_used") is False
        and coverage.get("input_sha256") == _sha(source)
        and coverage.get("event_sha256") == _sha(sentence)
        and coverage.get("object_sha256") == _sha(obj)
        and coverage.get("action_sha256") == _sha(action)
        and coverage.get("final_core_matches_winner") is True
        and coverage.get("final_core_sha256") == _sha(str(logic.get("core_message_jp") or ""))
    ):
        return None, _receipt("not_authorized", source, reason="coverage_or_final_core_mismatch")
    if len(obj + "を" + action) > 20:
        return None, _receipt("not_authorized", source, reason="relation_over_20_codepoints")
    unsafe_reason = _unsafe_praise_context(obj, action)
    if unsafe_reason is not None:
        return None, _receipt("not_authorized", source, reason=unsafe_reason)
    slot = SourceEventSlot(
        input_sha256=_sha(source),
        event_sha256=_sha(sentence),
        object_sha256=_sha(obj),
        action_sha256=_sha(action),
        object_text=obj,
        action_text=action,
        first_time="observed" if source.startswith("初めて") else "not_stated",
        requested_act="brief_encouragement",
    )
    candidate = realize_source_event_p4(slot)
    if candidate is None:
        return None, _receipt("not_authorized", source, reason="cannot_realize_within_28_codepoints")
    return slot, _receipt("admitted", source, slot=slot)


def realize_source_event_p4(slot: SourceEventSlot) -> str | None:
    """Compose from the verified relation, not a question- or object-specific answer."""
    if not isinstance(slot, SourceEventSlot) or slot.requested_act != "brief_encouragement":
        return None
    first = "初めて" if slot.first_time == "observed" else ""
    if slot.first_time not in {"observed", "not_stated"}:
        return None
    reply = f"{slot.object_text}を{first}自分で{slot.action_text}んだ。やるじゃん。"
    return reply if len(reply) <= 28 else None


def audit_final_source_event_p4(source: str, slot: SourceEventSlot | None, reply: str) -> dict:
    """Pure final-visible verifier; never repairs, blocks, or asserts naturalness."""
    receipt = _receipt("not_authorized" if slot is None else "mismatch", source, slot=slot)
    receipt["reply_sha256"] = _sha(reply) if isinstance(reply, str) else None
    receipt["reply_codepoints"] = len(reply) if isinstance(reply, str) else None
    receipt["audit_stage"] = "after_last_guard_before_episode"
    if not isinstance(reply, str):
        receipt["reason"] = "invalid_reply"
        return receipt
    source_unsafe = isinstance(source, str) and (
        (_SENSITIVE_MEDICATION.search(source) and _SENSITIVE_DOSE_ACTION.search(source))
        or _UNSAFE_PRAISE_ACTION.search(source)
    )
    if source_unsafe and (_PRAISE.search(reply) or _SAFE_EVALUATION.search(reply)):
        receipt.update(status="unsafe_endorsement_observed", reason="unsafe_action_praised")
        return receipt
    if slot is None:
        return receipt
    if len(reply) > 28 or _LATIN.search(reply) or _QUOTE.search(reply) or _NEGATION.search(reply) or _REPORT.search(reply):
        receipt["reason"] = "length_language_or_scope_mismatch"
        return receipt
    first = "初めて" if slot.first_time == "observed" else ""
    if slot.first_time == "not_stated" and "初めて" in reply:
        receipt["reason"] = "invented_first_time"
        return receipt
    relation = slot.object_text + "を"
    prefixes = (
        f"{relation}{first}自分で{slot.action_text}",
        f"{first}自分で{relation}{slot.action_text}",
    )
    prefix = next((candidate for candidate in prefixes if reply.startswith(candidate)), None)
    if prefix is None:
        receipt["reason"] = "same_clause_actor_event_relation_unverified"
        return receipt
    tail = reply[len(prefix):]
    separator = "んだ。" if tail.startswith("んだ。") else "んだ、" if tail.startswith("んだ、") else None
    if separator is None or not _SAFE_EVALUATION.fullmatch(tail[len(separator):]):
        receipt["reason"] = "completed_event_or_brief_encouragement_unverified"
        return receipt
    receipt.update(status="matched", reason="same_clause_source_event_and_encouragement_verified")
    return receipt


__all__ = [
    "SCHEMA", "ARM_ENV", "SourceEventSlot", "admit_source_event_slot_p4",
    "realize_source_event_p4", "audit_final_source_event_p4",
]
