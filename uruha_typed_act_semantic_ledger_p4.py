"""Bound two observable dialogue acts before their terminal realization.

This opt-in sidecar covers one narrow quote grammar and an independently
certified past-place answer. It does not infer intent, certify general semantic
equivalence, or write a psychological hypothesis into long-term memory.
Unsupported or inconsistent inputs must leave the existing route in charge.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
import re
import unicodedata

import uruha_current_turn_source_role_p4 as source_role
import uruha_mixed_act_lineage_p4 as lineage
import uruha_mixed_past_place_source_authority_p4 as past_place


LABEL = "typed_act_semantic_ledger_p4"
SCHEMA = "uruha_typed_act_semantic_ledger_p4_v1"
FLAG = "URUHA_P4_TYPED_ACT_SEMANTIC_LEDGER"

_EVENT_ID = re.compile(r"[0-9a-f]{32}\Z")
_QUOTE = re.compile(
    r"(?P<date>20\d{2}年(?:0?[1-9]|1[0-2])月(?:0?[1-9]|[12]\d|3[01])日)"
    r"の集合場所はまだ(?P<state>相談中|調整中|確認中)です\Z"
)
_DATE = re.compile(r"(20\d{2})年(\d{1,2})月(\d{1,2})日\Z")
_STYLE_COMMAND = re.compile(
    r"を友達(?:向けに|に(?:送る|話す|返す)感じで)"
    r"(?:もう少し|少し|もっと)?(?P<tone>柔らかく|やわらかく|カジュアルに|親しみやすく)"
    r"(?:言い換えて|書き換えて)[、,](?P<recall>.+)\Z"
)
_RECALL_SUFFIX = re.compile(
    rf"(?P<date>{past_place._DATE})に(?:私|僕|俺|うち)が"
    r"(?:選んだ|決めた)(?:集合)?場所も?(?:教えて|思い出して|覚えて)[。.!！]?\Z"
)
_CONTRADICTORY_STYLE = re.compile(
    r"堅い|硬い|固い|かたい|敬語|丁寧語|フォーマル|ビジネス|公式|"
    r"くだけない|砕けない|柔らかく(?:しない|ない)|やわらかく(?:しない|ない)|"
    r"カジュアル(?:にしない|じゃない)"
)
_CANONICAL_STYLE = {
    "柔らかく": "友達向けの柔らかい日本語",
    "やわらかく": "友達向けの柔らかい日本語",
    "カジュアルに": "友達向けのカジュアルな日本語",
    "親しみやすく": "友達向けの親しみやすい日本語",
}
_UNKNOWN_STATUSES = frozenset({
    "no_admitted_user_source", "source_retracted_or_ambiguous",
    "conflicting_user_sources", "current_turn_change_ambiguous",
    "source_transport_ambiguous", "source_value_outside_surface_budget",
})


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _binding_sha(binding: dict) -> str:
    return _sha(json.dumps(binding, sort_keys=True, ensure_ascii=False))


def _valid_absolute_date(value: str) -> bool:
    match = _DATE.fullmatch(value)
    if match is None:
        return False
    try:
        date(*(int(piece) for piece in match.groups()))
    except ValueError:
        return False
    return True


def _fail(reason: str) -> dict:
    return {"schema": SCHEMA, "eligible": False, "reason": reason}


def _bound_event(event: dict, admission: dict) -> tuple[dict, str] | tuple[None, str]:
    """Recheck immutable input and action spans, not a model's reply text."""
    raw = event.get("user_input")
    certificate = event.get(lineage.EVENT_KEY)
    if not isinstance(raw, str) or not raw or not isinstance(certificate, dict):
        return None, "missing_raw_or_lineage_event"
    event_id = certificate.get("event_id")
    cycle = certificate.get("cycle_index")
    raw_digest = _sha(raw)
    if (
        certificate.get("schema") != lineage.SCHEMA
        or not isinstance(event_id, str) or _EVENT_ID.fullmatch(event_id) is None
        or type(cycle) is not int or cycle < 0
        or certificate.get("raw_input_sha256") != raw_digest
        or certificate.get("source_role_act") != "mixed_request"
        or certificate.get("raw_dialogue_persisted") is not False
        or certificate.get("authority_transfer_permitted") is not False
        or certificate.get("model_calls_added") != 0
    ):
        return None, "event_identity_or_digest_mismatch"
    role = source_role.classify_current_turn_source_role_p4(raw, cycle_index=cycle)
    query = past_place.classify_mixed_past_place_query_p4(raw)
    actions = lineage._actions(raw, role, event_id)
    if (
        role.get("act") != "mixed_request"
        or role.get("quote_role") != "rewrite_object"
        or role.get("outer_role") != "current_user_context_or_instruction"
        or query.get("eligible") is not True
        or query.get("date_kind") != "absolute"
        or len(actions) != 2
        or [action.get("type") for action in actions]
        != ["quoted_rewrite", "past_user_place_recall"]
        or certificate.get("source_role_quote_sha256") != role.get("quote_raw_sha256")
        or certificate.get("actions") != actions
    ):
        return None, "unsupported_or_changed_action_structure"
    if (
        admission.get("schema") != "uruha_typed_mixed_atomic_delivery_p4_v1"
        or admission.get("eligible") is not True
        or admission.get("reason") != "current_two_action_direct_parent_verified"
        or admission.get("event_id") != event_id
        or admission.get("raw_input_sha256") != raw_digest
        or admission.get("cycle_index") != cycle
        or admission.get("actions") != actions
        or admission.get("source_role") != role
        or admission.get("query") != query
        or type(admission.get("prior_m31_surface_authority")) is not bool
        or admission.get("prior_m32_surface_authority") is not True
    ):
        return None, "admission_event_or_action_mismatch"
    m31_id = admission.get("m31_proposal_id")
    m32_id = admission.get("m32_proposal_id")
    if not (
        isinstance(m31_id, str) and m31_id.startswith(f"{event_id}:m31:")
        and _EVENT_ID.fullmatch(m31_id[len(f"{event_id}:m31:"):])
        and isinstance(m32_id, str) and m32_id.startswith(f"{event_id}:m32:")
        and _EVENT_ID.fullmatch(m32_id[len(f"{event_id}:m32:"):])
        and len({event_id, m31_id, m32_id, *(a["action_id"] for a in actions)}) == 5
    ):
        return None, "producer_or_action_id_mismatch"
    return {
        "raw": raw, "role": role, "query": query, "actions": actions,
        "event_id": event_id, "cycle_index": cycle, "raw_input_sha256": raw_digest,
    }, "verified"


def _certified_style(role: dict, requested_style: str, outer_date: str) -> bool:
    cues = role.get("evidence_ids")
    outside = role.get("_outside_nfkc")
    quote = role.get("_quote_nfkc")
    if (
        not isinstance(cues, list)
        or not {"rewrite_request", "style_goal", "other_action"}.issubset(cues)
        or not isinstance(outside, str) or not outside or "\n" in outside
        or not isinstance(quote, str) or not quote
        or _sha(outside) != role.get("outside_classifier_normalized_sha256")
        or _sha(quote) != role.get("quote_normalized_sha256")
        or _CONTRADICTORY_STYLE.search(outside)
    ):
        return False
    command = _STYLE_COMMAND.fullmatch(outside)
    if command is None or _RECALL_SUFFIX.fullmatch(command.group("recall")) is None:
        return False
    recall = _RECALL_SUFFIX.fullmatch(command.group("recall"))
    return (
        recall is not None and recall.group("date") == outer_date
        and _CANONICAL_STYLE[command.group("tone")] == requested_style
    )


def _bound_quote(raw: str, role: dict) -> tuple[dict, str] | tuple[None, str]:
    span = role.get("quote_content_span_raw")
    if (
        not isinstance(span, list) or len(span) != 2
        or any(type(value) is not int for value in span)
        or not (0 <= span[0] < span[1] <= len(raw))
    ):
        return None, "quote_span_missing_or_invalid"
    quoted_raw = raw[span[0]:span[1]]
    if (
        _sha(quoted_raw) != role.get("quote_raw_sha256")
        or quoted_raw != unicodedata.normalize("NFKC", quoted_raw)
        or quoted_raw != role.get("_quote_nfkc")
    ):
        return None, "quote_raw_digest_or_canonical_form_mismatch"
    match = _QUOTE.fullmatch(quoted_raw)
    if match is None or not _valid_absolute_date(match.group("date")):
        return None, "unsupported_quote_date_or_pending_state"
    return {
        "raw": quoted_raw, "date": match.group("date"), "state": match.group("state"),
        "raw_sha256": _sha(quoted_raw),
    }, "verified"


def _bound_source(event: dict, source_cert: dict, raw: str, outer_date: str) -> tuple[str, str]:
    """Return one certified answer; never promote friend/model text to User fact."""
    if not isinstance(source_cert, dict):
        return "", "missing_source_certificate"
    fresh = past_place.build_mixed_past_place_certificate_p4(raw, event.get("memory_data"))
    if (
        source_cert != fresh
        or source_cert.get("eligible") is not True
        or source_cert.get("date_kind") != "absolute"
        or source_cert.get("date_anchor") != outer_date
        or source_cert.get("input_sha256") != _sha(raw)
        or not isinstance(source_cert.get("binding_sha256"), str)
        or len(source_cert["binding_sha256"]) != 64
        or source_cert.get("authorized_reply_sha256")
        != _sha(str(source_cert.get("authorized_reply") or ""))
    ):
        return "", "source_certificate_binding_mismatch"
    status = source_cert.get("status")
    if status == "source_backed":
        value = source_cert.get("admitted_value")
        reply = source_cert.get("authorized_reply")
        if (
            not isinstance(value, str) or not value
            or not isinstance(reply, str)
            or reply != f"{outer_date}の集合場所は{value}にしたって言ってたな。"
            or source_cert.get("source_channel") not in {"direct_episode", "recent_turns"}
            or not isinstance(source_cert.get("source_trace_id"), str)
            or not source_cert["source_trace_id"]
        ):
            return "", "direct_user_source_or_answer_invalid"
        return reply, "verified"
    if status not in _UNKNOWN_STATUSES:
        return "", "unsupported_source_status"
    if (
        source_cert.get("admitted_value") is not None
        or source_cert.get("source_channel") is not None
        or source_cert.get("source_trace_id") is not None
    ):
        return "", "uncertain_source_contains_claim"
    return f"{outer_date}の集合場所は、今ある会話だけじゃ分からないな。", "verified"


def build_typed_act_semantic_ledger_p4(
    event: dict, admission: dict, source_cert: dict, requested_style: str,
) -> dict:
    """Produce a raw-free, digest-bound two-act receipt or fail closed.

    The caller must still perform the ordinary protected-route check and
    rederive this ledger at the final visible guard. This pure function adds
    no model calls or persistent facts; its result is not a safety waiver.
    """
    if not isinstance(event, dict) or not isinstance(admission, dict):
        return _fail("missing_event_or_admission")
    bound, reason = _bound_event(event, admission)
    if bound is None:
        return _fail(reason)
    query = bound["query"]
    outer_date = query.get("date_anchor")
    if not isinstance(outer_date, str) or not _valid_absolute_date(outer_date):
        return _fail("outer_date_unavailable_or_invalid")
    if not isinstance(requested_style, str) or not _certified_style(
        bound["role"], requested_style, outer_date
    ):
        return _fail("style_or_outer_recall_not_certified")
    quote, reason = _bound_quote(bound["raw"], bound["role"])
    if quote is None:
        return _fail(reason)
    recall_phrase, reason = _bound_source(
        event, source_cert, bound["raw"], outer_date
    )
    if reason != "verified":
        return _fail(reason)

    # The only supported rewrite preserves every source character preceding
    # the final copula, including year and pending-state token.
    rewrite_phrase = f"{quote['raw'][:-2]}なんだ"
    if rewrite_phrase != f"{quote['date']}の集合場所はまだ{quote['state']}なんだ":
        return _fail("rewrite_surface_slot_mismatch")
    if source_cert["status"] == "source_backed":
        recall_verified = recall_phrase == source_cert["authorized_reply"]
    else:
        recall_verified = recall_phrase == (
            f"{outer_date}の集合場所は、今ある会話だけじゃ分からないな。"
        )
    if not recall_verified:
        return _fail("recall_surface_slot_mismatch")
    candidate = f"「{rewrite_phrase}」って感じかな。{recall_phrase}"
    action_ids = [action["action_id"] for action in bound["actions"]]
    quote_binding = {
        "kind": "current_user_quoted_object_not_fact",
        "event_id": bound["event_id"],
        "raw_input_sha256": bound["raw_input_sha256"],
        "quote_raw_sha256": quote["raw_sha256"],
    }
    recall_binding = {
        "kind": "direct_user_certificate_or_honest_unknown",
        "event_id": bound["event_id"],
        "raw_input_sha256": bound["raw_input_sha256"],
        "source_certificate_binding_sha256": source_cert["binding_sha256"],
        "source_status": source_cert["status"],
        "source_channel": source_cert.get("source_channel"),
        "source_trace_id": source_cert.get("source_trace_id"),
    }
    acts = [
        {
            "action_id": action_ids[0],
            "type": "quoted_rewrite",
            "event_id": bound["event_id"],
            "cycle_index": bound["cycle_index"],
            "raw_input_sha256": bound["raw_input_sha256"],
            "source_binding": quote_binding,
            "source_binding_sha256": _binding_sha(quote_binding),
            "obligation_slot_digests": {
                "quote_raw_sha256": quote["raw_sha256"],
                "quote_date_sha256": _sha(quote["date"]),
                "quote_state_sha256": _sha(quote["state"]),
                "requested_style_sha256": _sha(requested_style),
            },
            "quote_state_class": "pending",
            "realized_surface_sha256": _sha(rewrite_phrase),
            "status": "bounded_slot_fidelity_verified",
            "semantic_equivalence_certified": False,
        },
        {
            "action_id": action_ids[1],
            "type": "past_user_place_recall",
            "event_id": bound["event_id"],
            "cycle_index": bound["cycle_index"],
            "raw_input_sha256": bound["raw_input_sha256"],
            "source_binding": recall_binding,
            "source_binding_sha256": _binding_sha(recall_binding),
            "obligation_slot_digests": {
                "recall_date_sha256": _sha(outer_date),
                "source_reply_sha256": source_cert["authorized_reply_sha256"],
            },
            "recall_actor": "user",
            "realized_surface_sha256": _sha(recall_phrase),
            "status": "bounded_slot_fidelity_verified",
            "semantic_equivalence_certified": False,
        },
    ]
    receipt = {
        "schema": SCHEMA,
        "status": "bounded_slot_fidelity_verified",
        "event_id": bound["event_id"],
        "cycle_index": bound["cycle_index"],
        "raw_input_sha256": bound["raw_input_sha256"],
        "action_ids": action_ids,
        "acts": acts,
        "quote_sha256": quote["raw_sha256"],
        "quote_raw_sha256": quote["raw_sha256"],
        "quote_role": "rewrite_object_not_fact",
        "quote_date_sha256": _sha(quote["date"]),
        "quote_state_sha256": _sha(quote["state"]),
        "quote_state_class": "pending",
        "recall_date_sha256": _sha(outer_date),
        "recall_actor": "user",
        "dates_distinct": quote["date"] != outer_date,
        "source_binding_sha256": source_cert["binding_sha256"],
        "source_reply_sha256": source_cert["authorized_reply_sha256"],
        "source_status": source_cert["status"],
        "source_channel": source_cert.get("source_channel"),
        "source_trace_id": source_cert.get("source_trace_id"),
        "rewrite_phrase_sha256": _sha(rewrite_phrase),
        "recall_phrase_sha256": _sha(recall_phrase),
        "candidate_sha256": _sha(candidate),
        "committed_visible_candidate_sha256": _sha(candidate),
        "model_call": {
            "status": "not_called_constrained_realization",
            "attempted_calls": 0, "completed_calls": 0, "completion_tokens": 0,
        },
        "model_calls_added": 0,
        "completion_tokens_added": 0,
        "bounded_slot_fidelity_verified": True,
        "semantic_equivalence_certified": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "bounded quote/date/state and direct-User source fidelity only; general meaning, style quality, and visible delivery require separate verification",
    }
    return {
        "schema": SCHEMA, "eligible": True, "reason": "two_acts_semantically_bound",
        "candidate": candidate, "rewrite_phrase": rewrite_phrase,
        "recall_phrase": recall_phrase, "receipt": receipt,
    }


__all__ = [
    "LABEL", "SCHEMA", "FLAG", "build_typed_act_semantic_ledger_p4",
]
