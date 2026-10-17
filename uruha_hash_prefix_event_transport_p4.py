"""Opt-in, per-speak transport for the frozen P4 hash-prefix event.

RightBrain.speak shallow-copies its input logic.  A fresh list shared by that
copy carries finalizer events back to the caller; only events for the reply
actually returned by speak are published.  The frozen final graph audit still
checks that the delivered reply and utterance match before counting them.
"""

from __future__ import annotations

import hashlib

import uruha_hash_prefix_provenance_gate_p4 as gate
import uruha_selected_offer_action_surface_fidelity_p4 as offer_surface


LABEL = "hash_prefix_event_transport_p4"
_EVENT_KEY = gate._EVENT_KEY
_EVENT_FIELD_ORDER = (
    "schema", "action", "prefix", "selected_candidate_sha256",
    "legacy_candidate_sha256", "returned_candidate_sha256",
)
_EVENT_FIELDS = frozenset(_EVENT_FIELD_ORDER)
_MAX_EVENTS = 16
_INSTALLED = False
_ORIGINAL_SPEAK = None


def _sha(reply: str) -> str:
    return hashlib.sha256(reply.encode("utf-8")).hexdigest()


def _returned_event(event, reply, reply_sha):
    """Copy only the frozen hash-only record for this exact speak reply."""
    if (
        type(event) is not dict
        or frozenset(event) != _EVENT_FIELDS
        or any(type(event[key]) is not str for key in _EVENT_FIELD_ORDER)
    ):
        return None
    prefix = event.get("prefix")
    if not (
        event.get("schema") == gate.SCHEMA
        and event.get("action") == "removed_unlicensed_hash_addition"
        and prefix in gate._FIXED_PREFIXES
        and event.get("selected_candidate_sha256") == reply_sha
        and event.get("returned_candidate_sha256") == reply_sha
        and event.get("legacy_candidate_sha256") == _sha(prefix + reply)
    ):
        return None
    return {key: event[key] for key in _EVENT_FIELD_ORDER}


def speak_with_hash_prefix_event_transport_p4(
    self, user_input, logic_data, memory_data, current_psyche,
):
    """Share a new bounded list through speak's copy, then publish only its reply's events."""
    if not isinstance(logic_data, dict):
        return _ORIGINAL_SPEAK(self, user_input, logic_data, memory_data, current_psyche)

    # Replacing, rather than extending, an unexpected prior value means stale
    # or caller-supplied events cannot be mistaken for this speak's operations.
    events = []
    logic_data[_EVENT_KEY] = events
    try:
        reply = _ORIGINAL_SPEAK(self, user_input, logic_data, memory_data, current_psyche)
    except BaseException:
        logic_data.pop(_EVENT_KEY, None)
        raise

    if not (
        isinstance(reply, str)
        and reply
        and logic_data.get(_EVENT_KEY) is events
        and len(events) <= _MAX_EVENTS
    ):
        logic_data.pop(_EVENT_KEY, None)
        return reply
    reply_sha = _sha(reply)
    try:
        related = []
        seen = set()
        for event in events:
            copy = _returned_event(event, reply, reply_sha)
            if copy is None:
                continue
            identity = tuple(copy[key] for key in _EVENT_FIELD_ORDER)
            if identity not in seen:
                seen.add(identity)
                related.append(copy)
    except Exception:
        # A malformed event must not turn a successful speech into an error.
        logic_data.pop(_EVENT_KEY, None)
        return reply
    if related:
        logic_data[_EVENT_KEY] = related
    else:
        logic_data.pop(_EVENT_KEY, None)
    return reply


def install_hash_prefix_event_transport_p4():
    """Install once, strictly after the frozen hash-prefix product chain."""
    global _INSTALLED, _ORIGINAL_SPEAK
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    if not (
        gate._INSTALLED
        and RightBrain._finalize_surface_reply is gate.finalize_with_hash_prefix_provenance_p4
        and RightBrain.speak is offer_surface.speak_with_selected_offer_action_p4
        and UruhaBrainV4_Mac.run_turn_debug is gate.run_turn_debug_with_hash_prefix_provenance_p4
        and UruhaBrainV4_Mac.emit_response_if_ready is gate.emit_response_if_ready_with_hash_prefix_provenance_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_SPEAK = RightBrain.speak
    RightBrain.speak = speak_with_hash_prefix_event_transport_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "speak_with_hash_prefix_event_transport_p4",
    "install_hash_prefix_event_transport_p4",
]
