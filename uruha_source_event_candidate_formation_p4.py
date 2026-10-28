"""Narrow, source-bound prompt constraint for P4 compact candidate formation.

The current User's completed event is allowed into the model request only
after the existing M29/M33 handoff and f7 finite event grammar validate it.
This module does not generate an answer or turn a hypothesis into a memory.
"""

from __future__ import annotations

import hashlib

from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4
from uruha_source_event_core_utility_p4 import _source_event, _valid_handoff


SCHEMA = "uruha_source_event_candidate_formation_p4_v1"
MAX_RELATION_CODEPOINTS = 20


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_source_event_constraint_p4(source: str, handoff: object) -> tuple[str | None, dict]:
    """Return a temporary internal prompt segment and a raw-free receipt.

    ``prompt_injected`` remains false here: only the compact transport can
    truthfully mark it true after it changes the actual provider request.
    """
    receipt = {
        "schema": SCHEMA,
        "status": "abstained",
        "reason": "invalid_source",
        "input_sha256": _sha(source) if isinstance(source, str) else None,
        "event_sha256": None,
        "object_sha256": None,
        "action_sha256": None,
        "relation_codepoints": None,
        "first_time_observed": None,
        "constraint_available": False,
        "prompt_injected": False,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }
    if not isinstance(source, str):
        return None, receipt
    expected = classify_direct_reply_act_p4(source)
    if not _valid_handoff(source, handoff, expected):
        receipt["reason"] = "invalid_handoff"
        return None, receipt
    event = _source_event(source, expected["cue_span"][0])
    if event is None:
        receipt["reason"] = "unsupported_source_event"
        return None, receipt
    sentence, obj, action = event
    relation = f"{obj}を{action}"
    first_time = sentence.startswith("初めて")
    receipt.update(
        event_sha256=_sha(sentence),
        object_sha256=_sha(obj),
        action_sha256=_sha(action),
        relation_codepoints=len(relation),
        first_time_observed=first_time,
    )
    if len(relation) > MAX_RELATION_CODEPOINTS:
        receipt["reason"] = "relation_over_budget"
        return None, receipt
    observed_qualifier = (
        "The User explicitly said this was their first time; keep that fact if you acknowledge the event.\n"
        if first_time else
        "Do not add a first-time claim: none was stated.\n"
    )
    segment = (
        "\n[Current User completed event — P4 source-bound candidate formation]\n"
        f"The current User reported: {sentence[:-1]}\n"
        f"Observed completed object/action relation: {relation}\n"
        "For each of the three core_message_jp candidates, answer the User's requested act "
        "while keeping the User as actor and that exact completed object/action relation. "
        "Do not substitute a different action or object, or add unreported feelings or history.\n"
        f"{observed_qualifier}"
        "The earlier no-repeat rule forbids copying the whole request as a question; "
        "a natural short Japanese acknowledgement may reuse observed event words. "
        "Keep each core within 32 characters. This is an internal constraint, not text to quote.\n"
    )
    receipt.update(status="authorized", reason="source_event_verified", constraint_available=True)
    return segment, receipt


__all__ = ["SCHEMA", "MAX_RELATION_CODEPOINTS", "build_source_event_constraint_p4"]
