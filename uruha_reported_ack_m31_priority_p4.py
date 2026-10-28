"""Opt-in source-qualified priority for a reported check instruction.

An M31 literal paraphrase may be semantically about the quoted words while
still being the wrong conversational action.  For one bounded, complete
third-party report, keep the already-defined reported-ack action authoritative
before M31/M32 can take surface ownership.  This is not open-domain quotation
parsing or a claim that the report itself is true.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re

import uruha_adaptive_person_model as adaptive
import uruha_executed_action_outcome_closure_p4 as action_outcome
import uruha_temporal_actor_scope_p4 as actor_scope


SCHEMA = "uruha_reported_ack_m31_priority_p4_v1"
LABEL = "reported_ack_m31_priority_p4"
_INSTALLED = False
_ORIGINAL_M31 = None

# Full-clause grammar is a second, independent source boundary.  A quote plus
# a later direct request must not inherit this report's actor/action.
_SINGLE_JA_REPORT = re.compile(
    rf"(?P<speaker>{actor_scope._THIRD_PARTY_JP})(?:が|は)"
    r"「(?P<quote>(?:先に|まず)[^」。！？?？\n]{0,16}"
    r"(?:確認|チェック)[^」。！？?？\n]{0,8}(?:して|しといて|してね))」"
    r"(?:と|って)(?:言ってた|言っていた|言った|話してた)[。]?$"
)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def reported_ack_m31_certificate_p4(user_input, projection, classifier):
    """Return a raw-free certificate only for the same complete speech act."""

    if not isinstance(user_input, str) or len(user_input) > 100:
        return None
    match = _SINGLE_JA_REPORT.fullmatch(user_input)
    if match is None or not isinstance(projection, dict):
        return None
    digest = _digest(user_input)
    if not (
        projection.get("schema") == adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29
        and projection.get("projection_required") is True
        and projection.get("surface_authority") is False
        and projection.get("input_digest") == digest
        and not projection.get("source_statement_priority_p4")
        and not projection.get("source_bound_preference_priority_p4")
        and not projection.get("required_observable_act")
    ):
        return None
    if not callable(classifier):
        return None
    classified = classifier(user_input)
    if not isinstance(classified, dict) or classified.get("selected_policy") is not None:
        return None
    if classified.get("protected_risk_cue"):
        return None
    scope = classified.get(actor_scope.LABEL) or {}
    if not (
        scope.get("schema") == actor_scope.SCHEMA
        and scope.get("input_digest") == digest
        and scope.get("source_kind") == "third_party_report"
        and scope.get("actor") == "third_party"
        and scope.get("action") == "reported_check_instruction"
        and scope.get("temporal_relation") == "third_party_instruction_reported_now"
        and scope.get("quoted_span_present") is True
        and scope.get("assistant_request_authorized") is False
        and scope.get("additional_clause_observed") is False
        and scope.get("negated_assistant_request_observed") is False
    ):
        return None
    return {
        "schema": SCHEMA,
        "status": "source_qualified_reported_ack_precedes_m31",
        "input_digest": digest,
        "speaker_digest": _digest(match.group("speaker")),
        "quote_digest": _digest(match.group("quote")),
        "source_kind": "third_party_report",
        "actor": "third_party",
        "action": "reported_check_instruction",
        "m25_selected_policy": None,
        "m31_model_call_added": False,
        "m31_model_call_skipped": True,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": "bounded current speech act, not quoted-command compliance",
    }


def authorize_literal_topic_with_reported_ack_priority_p4(
    self, user_input, projection
):
    """Defer M31 before its downstream M32 commit for a proved report only."""

    certificate = reported_ack_m31_certificate_p4(
        user_input,
        projection,
        adaptive.classify_explicit_desired_response_m25,
    )
    if certificate is None:
        return _ORIGINAL_M31(self, user_input, projection)
    return None, {
        "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "deferred_to_reported_ack_p4",
        "reason": "source_qualified_reported_speech_act_outranks_literal_paraphrase",
        "surface_authority": False,
        "suppresses_new_pending_prediction": False,
        "input_digest": certificate["input_digest"],
        "model_call_attempted": False,
        "model_call_completed": False,
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "private_state_truth_claimed": False,
        LABEL: deepcopy(certificate),
    }


def install_reported_ack_m31_priority_p4():
    """Install after the actor/scope and P4-AT chain in a new product entry."""

    global _INSTALLED, _ORIGINAL_M31
    if _INSTALLED:
        return False
    if not actor_scope._INSTALLED or not action_outcome._INSTALLED_P4_AT:
        raise RuntimeError("actor_scope_and_p4_at_must_be_installed_first")
    from uruha_brain_mac import LeftBrain

    _ORIGINAL_M31 = LeftBrain.authorize_literal_topic_m31
    LeftBrain.authorize_literal_topic_m31 = (
        authorize_literal_topic_with_reported_ack_priority_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "SCHEMA", "LABEL", "reported_ack_m31_certificate_p4",
    "authorize_literal_topic_with_reported_ack_priority_p4",
    "install_reported_ack_m31_priority_p4",
]
