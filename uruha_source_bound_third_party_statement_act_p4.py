"""Product-only, source-bound statement-act repair for an M31 surface.

This overlay does not grant M31 authority.  It only replaces an already
authorized, single same-proposition question with a direct acknowledgement
when the exact current source is a simple third-party Japanese assertion.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy

import uruha_adaptive_person_model as uapm
import uruha_source_bound_preference_fallback_p4 as preference


LABEL = "source_bound_third_party_statement_act_p4"
SCHEMA = "uruha_source_bound_third_party_statement_act_p4_v1"
MAX_SOURCE_CHARS = 80
MAX_SUBJECT_CHARS = 24
MAX_OBJECT_CHARS = 32
_JA = r"[\u3041-\u3096\u30a1-\u30fa\u30fc\u3400-\u9fff\u3005\u3006\u30f5\u30f6]"
_DIRECT_LIKE = re.compile(
    rf"(?P<subject>{_JA}{{1,{MAX_SUBJECT_CHARS}}})"
    rf"は(?P<object>{_JA}{{1,{MAX_OBJECT_CHARS}}})が好き。"
)
_NON_THIRD_PARTY = frozenset({
    "私", "わたし", "あたし", "僕", "ぼく", "俺", "おれ", "うち", "自分",
    "あなた", "貴方", "君", "きみ", "お前", "おまえ", "ユーザー", "誰",
})
_CONDITIONAL_PREFIXES = ("もし", "もしも", "仮に", "例えば", "たとえば", "仮定")
_INDIRECT_MARKERS = (
    "らしい", "そう", "みたい", "だって", "という", "って聞", "と聞",
    "によると", "と言", "と話", "かもしれ", "はず", "ようだ",
)
_NEGATED_COMPONENT_MARKERS = ("じゃない", "ではない", "じゃなかった", "ではなかった")
_SOURCE_SELF_CHECK_KEYS = (
    "safe_response_semantics_faithful",
    "subject_preserved",
    "predicate_preserved",
    "time_quantity_relation_preserved",
    "polarity_preserved",
    "unsupported_addition_absent",
)

_INSTALLED = False
_ORIGINAL_M31 = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_direct_third_party_like_p4(source):
    """Parse only one complete direct ``XはYが好き。`` source sentence.

    The narrow grammar intentionally leaves embedded speech, clause scope,
    second-person address, and non-Japanese turns to their existing routes.
    It does not infer whether X or Y is a person from a model projection.
    """
    if not isinstance(source, str) or not 1 <= len(source) <= MAX_SOURCE_CHARS:
        return None
    match = _DIRECT_LIKE.fullmatch(source)
    if match is None:
        return None
    subject = match.group("subject")
    object_jp = match.group("object")
    if (
        subject in _NON_THIRD_PARTY
        or any(subject.startswith(prefix) for prefix in _CONDITIONAL_PREFIXES)
        or any(marker in subject or marker in object_jp for marker in _INDIRECT_MARKERS)
        or any(marker in subject or marker in object_jp for marker in _NEGATED_COMPONENT_MARKERS)
        or "は" in subject
    ):
        return None
    return {"subject_jp": subject, "object_jp": object_jp}


def _same_proposition_question(candidate: str, subject: str, object_jp: str) -> bool:
    """A sole question about the exact X/Y/好き proposition, not a follow-up.

    Requiring the entire candidate to be the question also protects a reply
    which first affirms X/Y and then asks a reasonable clarification.
    """
    compact = re.sub(r"[ \t\u3000]", "", candidate)
    if len(compact) > 120 or "\n" in compact or "\r" in compact:
        return False
    pattern = (
        rf"{re.escape(subject)}(?:は、?|、|って)"
        rf"{re.escape(object_jp)}(?:が)?好き(?:なの|なん|だ|か)?[?？]"
    )
    return re.fullmatch(pattern, compact) is not None


def repair_authorized_statement_act_p4(source, plan, contract):
    """Return an M31 plan/contract pair, changing only a proved bad surface.

    Original M31 self-check values are retained separately.  The replacement
    checks are *source-rule* checks, never represented as model judgments.
    """
    parsed = parse_direct_third_party_like_p4(source)
    if parsed is None or not isinstance(plan, dict) or not isinstance(contract, dict):
        return plan, contract
    source_hash = _sha256(source)
    digest = source_hash[:16]
    if not (
        contract.get("schema") == uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31
        and contract.get("status") == "semantically_authorized"
        and contract.get("surface_authority") is True
        and contract.get("model_call_completed") is True
        and contract.get("input_digest") == digest
        and plan.get("intent") == "semantically_authorized_literal_topic_m31"
    ):
        return plan, contract
    embedded_projection = plan.get("literal_topic_projection_m29")
    if isinstance(embedded_projection, dict) and embedded_projection.get("input_digest") != digest:
        return plan, contract
    original_candidate = contract.get("response_jp")
    if not isinstance(original_candidate, str) or plan.get("core_message_jp") != original_candidate:
        return plan, contract
    if not _same_proposition_question(
        original_candidate, parsed["subject_jp"], parsed["object_jp"]
    ):
        return plan, contract

    response = f"{parsed['subject_jp']}は{parsed['object_jp']}が好きなんだね。"
    old_checks = deepcopy(contract.get("surface_self_checks") or {})
    original_canonical_digest = _sha256(
        "\n".join(str(contract.get(key) or "") for key in (
            "subject_jp", "predicate_jp", "literal_summary_jp", "polarity"
        ))
    )
    updated_contract = deepcopy(contract)
    updated_plan = deepcopy(plan)
    audit = {
        "schema": SCHEMA,
        "status": "source_bounded_statement_repaired",
        "reason": "authorized_same_proposition_question_recast_direct_statement",
        "source_sha256": source_hash,
        "source_projection_digest": digest,
        "subject_sha256": _sha256(parsed["subject_jp"]),
        "object_sha256": _sha256(parsed["object_jp"]),
        "model_candidate_sha256": _sha256(original_candidate),
        "model_canonical_sha256": original_canonical_digest,
        "model_candidate_rejected": True,
        "repair_response_sha256": _sha256(response),
        "self_check_provenance": "deterministic_source_rule",
        "original_m31_self_check_provenance": "postparse_values_may_include_missing_nested_schema_defaults",
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "model_call_added": False,
        "route": "第三者の肯定文 → 同じ内容を質問にしない",
    }
    updated_contract.update({
        "subject_jp": parsed["subject_jp"],
        "predicate_jp": f"{parsed['object_jp']}が好き",
        "literal_summary_jp": source,
        "source_polarity": "affirmed",
        "polarity": "affirmed",
        "response_jp": response,
        "surface_anchors_jp": [parsed["subject_jp"], parsed["object_jp"], "好き"],
        "visible_anchor_count": 3,
        "original_m31_surface_self_checks": old_checks,
        "original_m31_surface_self_checks_provenance":
            "postparse_values_may_include_missing_nested_schema_defaults",
        "surface_self_checks": {key: True for key in _SOURCE_SELF_CHECK_KEYS},
        "surface_self_checks_provenance": "deterministic_source_rule",
        LABEL: audit,
    })
    updated_plan["core_message_jp"] = response
    updated_plan["jp_summary"] = source
    updated_plan["semantic_authorization_m31"] = deepcopy(updated_contract)
    return updated_plan, updated_contract


def authorize_literal_topic_with_source_act_p4(self, user_input, projection):
    """Product wrapper around M31, installed after preference fallback."""
    plan, contract = _ORIGINAL_M31(self, user_input, projection)
    if not isinstance(user_input, str) or not isinstance(projection, dict):
        return plan, contract
    # M31 accepts a source_anchor_exact_match flag as another source proof;
    # this narrower repair additionally requires the literal M29 digest.
    if projection.get("input_digest") != _sha256(user_input)[:16]:
        return plan, contract
    return repair_authorized_statement_act_p4(user_input, plan, contract)


authorize_literal_topic_with_source_act_p4._p4_source_act_wrapper = True


def _finish_source_act_trace_p4(self, result, source):
    """Keep the repaired selected plan and visible graph in one audit view."""
    if not isinstance(result, dict) or not isinstance(source, str):
        return result
    logic = result.get("logic") or {}
    authorization = logic.get("semantic_authorization_m31") or {}
    audit = authorization.get(LABEL) or {}
    if not (
        isinstance(audit, dict)
        and audit.get("schema") == SCHEMA
        and audit.get("source_sha256") == _sha256(source)
    ):
        return result
    trace = result.get("runtime_trace") or {}
    rows = trace.get("blackboard")
    selected = trace.get("selected_plan") or {}
    if not isinstance(rows, list):
        return result
    actual_selected = [
        row for row in rows if isinstance(row, dict) and row.get("label") == "selected_plan"
    ]
    actual_utterance = [
        row for row in rows if isinstance(row, dict) and row.get("label") == "utterance"
    ]
    expected = authorization.get("response_jp")
    matched = bool(
        authorization.get("surface_authority")
        and logic.get("intent") == "semantically_authorized_literal_topic_m31"
        and isinstance(expected, str)
        and logic.get("core_message_jp") == expected
        and selected.get("core_message_jp") == expected
        and len(actual_selected) == 1
        and (actual_selected[0].get("payload") or {}).get("core_message_jp") == expected
        and len(actual_utterance) == 1
        and (actual_utterance[0].get("payload") or {}).get("reply") == expected
        and result.get("reply") == expected
    )
    payload = deepcopy(audit)
    payload["status"] = (
        "source_bounded_statement_repaired" if matched else "selected_or_visible_mismatch"
    )
    payload["selected_visible_same_source_commit"] = matched
    without_prior = [
        row for row in rows
        if not (isinstance(row, dict) and row.get("label") == LABEL)
    ]
    insertion = next(
        (index + 1 for index, row in enumerate(without_prior)
         if isinstance(row, dict) and row.get("label") == "selected_plan"),
        len(without_prior),
    )
    without_prior.insert(insertion, {
        "stage": "verify", "label": LABEL, "payload": payload,
        "salience": 1.0 if not matched else 0.97,
    })
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(payload)
    logic[LABEL] = deepcopy(payload)
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        runtime.blackboard = deepcopy(without_prior)
        turn_traces = getattr(runtime, "turn_traces", None)
        if turn_traces and turn_traces[-1].get("cycle_index") == trace.get("cycle_index"):
            turn_traces[-1] = deepcopy(trace)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    sync_current_history_m41_1(result)
    return result


def run_turn_debug_with_source_act_p4(self, user_input, input_context=None):
    result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    return _finish_source_act_trace_p4(self, result, user_input)


def emit_response_if_ready_with_source_act_p4(self, event, tick_result):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _finish_source_act_trace_p4(self, result, (event or {}).get("user_input"))


def install_source_bound_third_party_statement_act_p4():
    """Idempotently install only after the source preference product chain."""
    global _INSTALLED, _ORIGINAL_M31, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    if not (
        preference._INSTALLED
        and LeftBrain._rule_based_plan
        is preference.rule_plan_with_source_bound_preference_fallback_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_preference_fallback_required")
    original = LeftBrain.authorize_literal_topic_m31
    if getattr(original, "_p4_source_act_wrapper", False):
        raise RuntimeError(f"{LABEL}:m31_already_wrapped")
    _ORIGINAL_M31 = original
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain.authorize_literal_topic_m31 = authorize_literal_topic_with_source_act_p4
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_source_act_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_source_act_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL",
    "parse_direct_third_party_like_p4",
    "repair_authorized_statement_act_p4",
    "authorize_literal_topic_with_source_act_p4",
    "install_source_bound_third_party_statement_act_p4",
]
