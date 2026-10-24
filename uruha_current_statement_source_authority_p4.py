"""Product-only source authority for a narrow current preference assertion.

The certificate attests to what the user *said this turn*, not the truth of a
third party's preference.  It is deliberately separate from M31 model
authorization and from the profile writer.  The same certificate gates the
early rule seed and M29 priority; only the actually selected and visible plan
is recorded as a successful graph commit.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy

import uruha_adaptive_person_model as uapm
import uruha_source_bound_preference_fallback_p4 as preference
import uruha_source_bound_third_party_statement_act_p4 as statement_act
import uruha_source_semantic_atoms_m33 as source_atoms


LABEL = "current_statement_source_authority_p4"
SCHEMA = "uruha_current_statement_source_authority_p4_v1"
PRIORITY_SCHEMA = "uruha_current_statement_source_priority_p4_v1"

# A relation word is an observable grammatical subject, not a named person's
# identity.  Unknown names, pronouns, possessives, and inferred relationships
# stay on the inherited route.
_THIRD_PARTY_ROLES = frozenset({
    "友達", "友人", "母", "父", "兄", "姉", "弟", "妹", "祖母", "祖父",
    "先生", "先輩", "後輩", "同僚",
})
_OBJECT_HEAD_SUFFIXES = preference._OBJECT_HEAD_SUFFIXES + (
    "プリン", "ゼリー", "ラテ", "歌",
)
_PROTECTED_CUE = re.compile(
    r"死|殺|自殺|自傷|傷つけ|消えたい|首吊|性的|性行為|セックス|"
    r"レイプ|痴漢|裸|虐待|暴力|殴|戦争|銃|ナイフ|爆弾|薬物|ドラッグ"
)

_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_M29 = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_object(value: str) -> bool:
    """Require an observable object head rather than guess at a person name."""
    return bool(
        value
        and "は" not in value
        and value not in preference._PERSON_REFERENTS
        and not preference._PERSON_SUFFIX.search(value)
        and not preference._PERSON_SCOPE.search(value)
        and not preference._MEMORY_ACT.search(value)
        and (
            value.endswith(_OBJECT_HEAD_SUFFIXES)
            or value.startswith(preference._OBJECT_HEAD_PREFIXES)
        )
    )


def source_statement_certificate_p4(source):
    """Return a raw-free proof of one direct, affirmative source act or None.

    Self claims reuse the existing postposed-aware owner admission.  Third
    party claims are only user-reported source statements and never establish
    a factual profile write authority.
    """
    if not isinstance(source, str) or not 1 <= len(source) <= statement_act.MAX_SOURCE_CHARS:
        return None
    if _PROTECTED_CUE.search(source):
        return None

    self_plan = preference.source_bound_preference_plan_p4(source)
    if isinstance(self_plan, dict):
        prior = self_plan.get(preference.LABEL) or {}
        parsed = preference._SIMPLE_SELF_LIKE.fullmatch(source)
        if not (
            parsed
            and self_plan.get("planner_path") == preference.LABEL
            and prior.get("schema") == preference.SCHEMA
            and prior.get("status") == "source_admitted_current_self_like"
            and prior.get("input_sha256") == _sha256(source)
            and prior.get("value_sha256") == _sha256(parsed.group("value"))
        ):
            return None
        return {
            "schema": SCHEMA,
            "status": "source_statement_admitted",
            "owner": "user",
            "statement_act": "assertion",
            "polarity": "affirmed",
            "source_type": "current_user_self_assertion",
            "source_sha256": prior["input_sha256"],
            "source_span_sha256": prior["source_span_sha256"],
            "subject_sha256": _sha256(parsed.group("speaker")[:-1]),
            "value_sha256": prior["value_sha256"],
            "admission_reason": "postposed_owner_admitted_exact_self_like",
            "profile_write_authority": "existing_owner_admission_only",
            "profile_write_claimed": False,
            "model_authority_claimed": False,
            "raw_dialogue_persisted": False,
        }

    parsed = statement_act.parse_direct_third_party_like_p4(source)
    if not isinstance(parsed, dict):
        return None
    subject = parsed["subject_jp"]
    value = parsed["object_jp"]
    if subject not in _THIRD_PARTY_ROLES or not _bounded_object(value):
        return None
    return {
        "schema": SCHEMA,
        "status": "source_statement_admitted",
        "owner": "third_party",
        "statement_act": "assertion",
        "polarity": "affirmed",
        "source_type": "current_user_third_party_assertion",
        "source_sha256": _sha256(source),
        "source_span_sha256": _sha256(source[:-1]),
        "subject_sha256": _sha256(subject),
        "value_sha256": _sha256(value),
        "admission_reason": "bounded_relation_subject_and_object_head",
        "profile_write_authority": "none",
        "profile_write_claimed": False,
        "model_authority_claimed": False,
        "raw_dialogue_persisted": False,
    }


def source_statement_plan_p4(source):
    """Construct a source-faithful reply seed without claiming remembered fact."""
    certificate = source_statement_certificate_p4(source)
    if certificate is None:
        return None
    if certificate["owner"] == "user":
        plan = preference.source_bound_preference_plan_p4(source)
        if not isinstance(plan, dict):
            return None
        plan = deepcopy(plan)
        plan["planner_path"] = LABEL
        plan[LABEL] = deepcopy(certificate)
        return plan

    parsed = statement_act.parse_direct_third_party_like_p4(source)
    if not isinstance(parsed, dict):
        return None
    subject, value = parsed["subject_jp"], parsed["object_jp"]
    if (
        _sha256(subject) != certificate["subject_sha256"]
        or _sha256(value) != certificate["value_sha256"]
    ):
        return None
    return {
        "intent": "chat",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "第三者の好みについて話している",
        "reply_goal": "当輪の陳述だけを軽く受け止める",
        "jp_summary": f"ユーザーは{subject}が{value}を好きだと話している。",
        "core_message_jp": f"{subject}は{value}が好きなんだね。",
        "stance": {
            "warmth": 0.36, "tease": 0.08, "blunt": 0.12,
            "jealousy": 0.0, "distance": 0.08,
        },
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.08,
        "premise_check": "accept",
        "self_check": False,
        "subjective_note_jp": "当輪の第三者に関する申告だけを受け止める",
        "hidden_intent": "plain_request",
        "surface_act": "plain_reply",
        "grounding": {"preference_source": "current_user_third_party_assertion_only"},
        "payload_level": "medium",
        "planner_path": LABEL,
        LABEL: deepcopy(certificate),
        "constraints": {
            "first_person": "うち",
            "sentence_count": 1,
            "max_chars": 56,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": [
            "知ってた", "前から知ってる", "覚えてる", "覚えた", "メモした",
            "うちも好き", "私も好き",
        ],
    }


def rule_plan_with_current_statement_source_authority_p4(
    self, user_input, current_psyche, memory_data=None
):
    """Preserve the old route except a proved statement misread as an offer."""
    original = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    certificate = source_statement_certificate_p4(user_input)
    if certificate is None:
        return original
    if original is not None:
        if not isinstance(original, dict):
            return original
        is_legacy_food_offer = (
            original.get("intent") in {"food_offer_generic", "food_offer_sweet"}
            and original.get("scene") == "casual"
        )
        is_prior_source_seed = (
            certificate["owner"] == "user"
            and original.get("planner_path") == preference.LABEL
            and original.get("core_message_jp")
            == (preference.source_bound_preference_plan_p4(user_input) or {}).get("core_message_jp")
        )
        if not (is_legacy_food_offer or is_prior_source_seed):
            return original
    return source_statement_plan_p4(user_input) or original


def literal_topic_projection_with_current_statement_authority_p4(
    user_input,
    adaptive_feedback,
    pragmatic_understanding,
    feedback_topic_transition_m28=None,
):
    """Defer M31 only where the same current source proof is exact and safe."""
    candidate = _ORIGINAL_M29(
        user_input,
        adaptive_feedback,
        pragmatic_understanding,
        feedback_topic_transition_m28,
    )
    certificate = source_statement_certificate_p4(user_input)
    if not isinstance(candidate, dict) or certificate is None:
        return candidate
    if not (
        candidate.get("schema") == uapm.LITERAL_TOPIC_PROJECTION_SCHEMA_M29
        and candidate.get("surface_authority") is False
        and not (feedback_topic_transition_m28 or {}).get("surface_authority")
        and candidate.get("input_digest") == certificate["source_sha256"][:16]
    ):
        return candidate

    if candidate.get("projection_required") is True:
        original_atoms = source_atoms.extract_source_semantic_atoms_m33(user_input, candidate)
        if not (
            isinstance(original_atoms, dict)
            and original_atoms.get("status") == "source_pattern_unavailable"
        ):
            return candidate
        previous_m33_status = original_atoms["status"]
    elif (
        certificate["owner"] == "user"
        and candidate.get("projection_required") is False
        and (candidate.get("source_bound_preference_priority_p4") or {}).get("input_sha256")
        == certificate["source_sha256"]
    ):
        # The already installed self-preference overlay performed the M33
        # check; preserve it rather than infer availability a second way.
        previous_m33_status = "source_pattern_unavailable"
    else:
        return candidate

    updated = dict(candidate)
    updated.update({
        "status": "source_statement_rule_candidate_p4",
        "reason": "exact_current_statement_source_rule_available_before_m31",
        "projection_required": False,
        "source_statement_priority_p4": {
            "schema": PRIORITY_SCHEMA,
            "status": "source_rule_candidate",
            "source_sha256": certificate["source_sha256"],
            "source_span_sha256": certificate["source_span_sha256"],
            "subject_sha256": certificate["subject_sha256"],
            "value_sha256": certificate["value_sha256"],
            "owner": certificate["owner"],
            "statement_act": "assertion",
            "polarity": "affirmed",
            "original_m29_status": candidate.get("status"),
            "original_projection_required": candidate.get("projection_required"),
            "original_m33_status": previous_m33_status,
            "surface_authority_claimed": False,
            "raw_dialogue_persisted": False,
        },
    })
    return updated


def materialize_current_statement_source_authority_p4(result, source):
    """Audit a *selected* rule against the exact visible utterance."""
    if not isinstance(result, dict) or not isinstance(source, str):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    certificate = source_statement_certificate_p4(source)
    # The deterministic multi-tick planner keeps `planner_path` but may drop
    # nonstandard seed keys.  Recreate the same source proof instead of
    # mistaking its absent certificate field for a non-selection.
    actual = logic.get(LABEL)
    route = logic.get("bounded_slow_path_m21") or {}
    if not (
        isinstance(certificate, dict)
        and logic.get("planner_path") == LABEL
        and route.get("route") == "deterministic_rule_plan"
        and route.get("model_call_attempted") is False
    ):
        return result
    carried_certificate_matches = bool(
        actual is None
        or (
            isinstance(actual, dict)
            and all(
                actual.get(key) == certificate[key]
                for key in (
                    "source_sha256", "source_span_sha256",
                    "subject_sha256", "value_sha256",
                )
            )
        )
    )
    rows = trace.get("blackboard")
    selected = trace.get("selected_plan")
    if not isinstance(rows, list) or not isinstance(selected, dict):
        return result
    selected_rows = [
        row for row in rows if isinstance(row, dict) and row.get("label") == "selected_plan"
    ]
    utterance_rows = [
        row for row in rows if isinstance(row, dict) and row.get("label") == "utterance"
    ]
    if not (len(selected_rows) == 1 and len(utterance_rows) == 1):
        return result
    selected_row = selected_rows[0].get("payload") or {}
    utterance = utterance_rows[0].get("payload") or {}
    if not isinstance(selected_row, dict) or not isinstance(utterance, dict):
        return result
    expected_plan = source_statement_plan_p4(source)
    if not isinstance(expected_plan, dict):
        return result
    expected = expected_plan["core_message_jp"]
    selected_matches_logic = bool(
        selected.get("intent") == logic.get("intent")
        and selected.get("scene") == logic.get("scene")
        and selected.get("core_message_jp") == logic.get("core_message_jp")
        and selected_row.get("intent") == logic.get("intent")
        and selected_row.get("scene") == logic.get("scene")
        and selected_row.get("core_message_jp") == logic.get("core_message_jp")
    )
    visible_matches = bool(
        carried_certificate_matches
        and selected_matches_logic
        and logic.get("core_message_jp") == expected
        and utterance.get("reply") == expected
        and result.get("reply") == expected
    )
    payload = {
        "schema": SCHEMA,
        "status": (
            "selected_visible_same_source_commit"
            if visible_matches else "selected_or_visible_mismatch"
        ),
        "route": "当輪の肯定文 → 同じ主語と物品を承ける",
        "selected_visible_same_source_commit": visible_matches,
        "selected_plan_matches_logic": selected_matches_logic,
        "carried_certificate_matches": carried_certificate_matches,
        "owner": certificate["owner"],
        "source_type": certificate["source_type"],
        "statement_act": "assertion",
        "polarity": "affirmed",
        "source_sha256": certificate["source_sha256"],
        "source_span_sha256": certificate["source_span_sha256"],
        "subject_sha256": certificate["subject_sha256"],
        "value_sha256": certificate["value_sha256"],
        "m21_route": "deterministic_rule_plan",
        "m31_model_authority_claimed": False,
        "general_planner_model_call_attempted": False,
        "memory_write_claimed": False,
        "raw_dialogue_persisted": False,
    }
    if selected_matches_logic:
        selected["planner_path"] = LABEL
        selected_row["planner_path"] = LABEL
    without_prior = [
        row for row in rows
        if not (isinstance(row, dict) and row.get("label") == LABEL)
    ]
    insertion = next(
        (
            index + 1 for index, row in enumerate(without_prior)
            if isinstance(row, dict) and row.get("label") == "selected_plan"
        ),
        len(without_prior),
    )
    without_prior.insert(insertion, {
        "stage": "verify",
        "label": LABEL,
        "payload": payload,
        "salience": 0.97 if visible_matches else 1.0,
    })
    trace["blackboard"] = without_prior
    trace[LABEL] = deepcopy(payload)
    logic[LABEL] = deepcopy(payload)
    return result


def _finish_current_statement_source_authority_p4(self, result, source):
    materialize_current_statement_source_authority_p4(result, source)
    if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
        return result
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    current = result["runtime_trace"]
    self.runtime.last_selected_plan = deepcopy(current["selected_plan"])
    self.runtime.blackboard = deepcopy(current["blackboard"])
    snapshot = result.get("runtime_state")
    if isinstance(snapshot, dict):
        snapshot["last_selected_plan"] = deepcopy(current["selected_plan"])
    sync_current_history_m41_1(result)
    if (
        self.runtime.turn_traces
        and self.runtime.turn_traces[-1].get("cycle_index") == current.get("cycle_index")
    ):
        self.runtime.turn_traces[-1] = deepcopy(current)
    return result


def run_turn_debug_with_current_statement_source_authority_p4(
    self, user_input, input_context=None
):
    result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    return _finish_current_statement_source_authority_p4(self, result, user_input)


def emit_response_if_ready_with_current_statement_source_authority_p4(
    self, event, tick_result
):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _finish_current_statement_source_authority_p4(
        self, result, (event or {}).get("user_input")
    )


def install_current_statement_source_authority_p4():
    """Install after the existing P4 preference and statement-act overlays."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_M29, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    if not (
        preference._INSTALLED
        and statement_act._INSTALLED
        and LeftBrain._rule_based_plan
        is preference.rule_plan_with_source_bound_preference_fallback_p4
        and uapm.build_literal_topic_projection_candidate_m29
        is preference.literal_topic_projection_with_source_bound_rule_p4
        and UruhaBrainV4_Mac.run_turn_debug
        is statement_act.run_turn_debug_with_source_act_p4
        and UruhaBrainV4_Mac.emit_response_if_ready
        is statement_act.emit_response_if_ready_with_source_act_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_M29 = uapm.build_literal_topic_projection_candidate_m29
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_current_statement_source_authority_p4
    uapm.build_literal_topic_projection_candidate_m29 = (
        literal_topic_projection_with_current_statement_authority_p4
    )
    UruhaBrainV4_Mac.run_turn_debug = (
        run_turn_debug_with_current_statement_source_authority_p4
    )
    UruhaBrainV4_Mac.emit_response_if_ready = (
        emit_response_if_ready_with_current_statement_source_authority_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "LABEL",
    "SCHEMA",
    "PRIORITY_SCHEMA",
    "source_statement_certificate_p4",
    "source_statement_plan_p4",
    "materialize_current_statement_source_authority_p4",
    "install_current_statement_source_authority_p4",
]
