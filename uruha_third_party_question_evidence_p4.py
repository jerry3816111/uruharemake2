"""Product-only unknown-evidence authority for narrow third-party questions.

The current question is not evidence that its proposed preference is true.
This rule only uses recognizable user-origin context already passed to the
planner, and never claims to have searched the entire memory database.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy

import uruha_current_statement_source_authority_p4 as statement_authority
import uruha_source_bound_third_party_statement_act_p4 as statement_act


LABEL = "third_party_question_evidence_p4"
SCHEMA = "uruha_third_party_question_evidence_p4_v1"
_DIRECT_QUESTION = re.compile(
    rf"(?P<subject>{statement_act._JA}{{1,{statement_act.MAX_SUBJECT_CHARS}}})"
    rf"は(?P<object>{statement_act._JA}{{1,{statement_act.MAX_OBJECT_CHARS}}})が好き[？?]"
)
_EPISODE_USER = re.compile(
    r"(?:^|\|\s*)User:\s*(.*?)\s*\|\s*Summary:.*?\|\s*Uruha:",
    re.S,
)
_RECENT_USER = re.compile(r"User:\s*(.*?)\s*->\s*Uruha:.*", re.S)
# These are bounded, non-propositional decorations already observed from the
# existing persona surface.  The verifier must not accept arbitrary appended
# text merely because the selected unknown core is still present.
_BENIGN_DISCOURSE_PREFIXES = ("", "普通に、", "いや、", "てか、")
_BENIGN_DISCOURSE_SUFFIXES = ("", "そのくらいでいいだろ。")

_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unknown_core(subject: str, value: str) -> str:
    return f"{subject}が{value}を好きかどうかは、今の話だけじゃ分からないな。"


def _parse_direct_question(source):
    if (
        not isinstance(source, str)
        or not 1 <= len(source) <= statement_act.MAX_SOURCE_CHARS
        or statement_authority._PROTECTED_CUE.search(source)
    ):
        return None
    match = _DIRECT_QUESTION.fullmatch(source)
    if match is None:
        return None
    subject, value = match.group("subject"), match.group("object")
    if (
        subject not in statement_authority._THIRD_PARTY_ROLES
        or not statement_authority._bounded_object(value)
        or "が" in value
        or "好き" in value
        or any(subject.startswith(prefix) for prefix in statement_act._CONDITIONAL_PREFIXES)
        or any(
            marker in subject or marker in value
            for marker in statement_act._INDIRECT_MARKERS
            + statement_act._NEGATED_COMPONENT_MARKERS
        )
        # The existing deterministic candidate normalizer truncates core at
        # 40 characters.  Never admit a source whose full unknown core would
        # lose the owner, value, or uncertainty at the actual selected plan.
        or len(_unknown_core(subject, value)) > 40
    ):
        return None
    return subject, value


def _episode_user(text):
    if not isinstance(text, str):
        return None
    # Stored episodes concatenate raw user text with unescaped field labels.
    # A user can therefore include `| Summary:` or `| Uruha:` themselves.
    # Reject every ambiguous shape instead of truncating the user span and
    # incorrectly certifying that a prior X/Y proposition was absent.
    labels = [
        match.group(1)
        for match in re.finditer(r"(?:^|\|\s*)(User|Summary|Uruha):", text)
    ]
    if labels != ["User", "Summary", "Uruha"]:
        return None
    match = _EPISODE_USER.search(text)
    return match.group(1).strip() if match else None


def _recent_user(text):
    if not isinstance(text, str):
        return None
    if text.count("User:") != 1 or text.count("-> Uruha:") != 1:
        return None
    match = _RECENT_USER.fullmatch(text)
    return match.group(1).strip() if match else None


def _available_user_sources(memory_data):
    """Return recognized user utterances, or None for an unknown source shape."""
    if not isinstance(memory_data, dict):
        return None
    recent = memory_data.get("recent_turns")
    working = memory_data.get("working_memory_items")
    provenance = memory_data.get("memory_provenance")
    if not (
        isinstance(recent, list)
        and isinstance(working, list)
        and isinstance(provenance, dict)
        and isinstance(provenance.get("passed_to_leftbrain"), list)
    ):
        return None

    users = []
    for row in recent:
        if not isinstance(row, dict) or not isinstance(row.get("user"), str):
            return None
        if row["user"].strip():
            users.append(row["user"].strip())

    for row in working:
        if not isinstance(row, dict) or not isinstance(row.get("source"), str):
            return None
        if row["source"] != "episode" or row.get("selected") is False:
            continue
        user = _episode_user(row.get("text"))
        if user is None:
            return None
        if user:
            users.append(user)

    for row in provenance["passed_to_leftbrain"]:
        if not isinstance(row, dict) or not isinstance(row.get("channel"), str):
            return None
        channel = row["channel"]
        if channel == "direct_episode":
            if row.get("source") != "episode":
                return None
            user = _episode_user(row.get("text"))
        elif channel == "recent_turns":
            if row.get("source") != "recent_turn":
                return None
            user = _recent_user(row.get("text"))
        else:
            continue
        if user is None:
            return None
        if user:
            users.append(user)
    return users


def _same_pair_nonquestion_source(user, subject, value):
    """Only the exact same prior direct question lacks evidential weight."""
    if subject not in user or value not in user:
        return False
    if _parse_direct_question(user.strip()) == (subject, value):
        return False
    return True


def question_evidence_candidate_p4(source, memory_data):
    """Certify only that no same X/Y appears in recognized available sources."""
    parsed = _parse_direct_question(source)
    if parsed is None:
        return None
    users = _available_user_sources(memory_data)
    if users is None:
        return None
    subject, value = parsed
    if any(_same_pair_nonquestion_source(user, subject, value) for user in users):
        return None
    return {
        "schema": SCHEMA,
        "status": "question_unknown_rule_candidate",
        "owner": "third_party",
        "source_type": "current_user_third_party_question",
        "statement_act": "question",
        "polarity": "unresolved",
        "evidence_status": "not_found_in_available_context",
        "source_sha256": _sha256(source),
        "source_span_sha256": _sha256(source[:-1]),
        "subject_sha256": _sha256(subject),
        "value_sha256": _sha256(value),
        "recognized_user_source_count": len(users),
        "rule_authority": "unknown_only",
        "m31_model_authority_claimed": False,
        "memory_write_claimed": False,
        "raw_dialogue_persisted": False,
    }


def question_unknown_plan_p4(source, memory_data):
    """Construct an uncertainty-preserving plan without a factual claim."""
    certificate = question_evidence_candidate_p4(source, memory_data)
    parsed = _parse_direct_question(source)
    if certificate is None or parsed is None:
        return None
    subject, value = parsed
    if (
        certificate["subject_sha256"] != _sha256(subject)
        or certificate["value_sha256"] != _sha256(value)
    ):
        return None
    return {
        "intent": "chat",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "第三者の好みについて確かめている",
        "reply_goal": "現在使える証拠だけでは分からないと短く答える",
        "jp_summary": f"ユーザーは{subject}が{value}を好きか尋ねている。",
        "core_message_jp": _unknown_core(subject, value),
        "stance": {
            "warmth": 0.34, "tease": 0.02, "blunt": 0.1,
            "jealousy": 0.0, "distance": 0.06,
        },
        "cognitive_mode": "direct",
        "response_mode": "direct_answer_with_hedge",
        "uncertainty": 0.72,
        "premise_check": "accept",
        "self_check": True,
        "subjective_note_jp": "当輪の質問や関連するだけの記憶を事実に変えない",
        "hidden_intent": "plain_request",
        "surface_act": "plain_reply",
        "grounding": {"preference_source": "available_context_unknown"},
        "payload_level": "medium",
        "planner_path": LABEL,
        LABEL: deepcopy(certificate),
        "constraints": {
            "first_person": "うち",
            "sentence_count": 1,
            "max_chars": 44,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": [
            "知ってた", "前から知ってる", "覚えてる", "メモした",
            "好きなんだね", "うちも好き",
        ],
    }


def rule_plan_with_third_party_question_evidence_p4(
    self, user_input, current_psyche, memory_data=None
):
    original = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    if original is not None:
        return original
    return question_unknown_plan_p4(user_input, memory_data)


def _visible_unknown_preserved(reply, expected_core):
    """Accept only the selected core with finite known style decorations."""
    if not isinstance(reply, str) or not isinstance(expected_core, str):
        return False
    if not reply or not expected_core:
        return False
    return any(
        reply == f"{prefix}{expected_core}{suffix}"
        for prefix in _BENIGN_DISCOURSE_PREFIXES
        for suffix in _BENIGN_DISCOURSE_SUFFIXES
    )


def materialize_third_party_question_evidence_p4(result, source):
    """Record only an actually selected plan and its observed final surface."""
    if not isinstance(result, dict) or not isinstance(source, str):
        return result
    logic = result.get("logic")
    trace = result.get("runtime_trace")
    memory_data = result.get("memory_data")
    if not isinstance(logic, dict) or not isinstance(trace, dict):
        return result
    certificate = question_evidence_candidate_p4(source, memory_data)
    route = logic.get("bounded_slow_path_m21") or {}
    if not (
        isinstance(certificate, dict)
        and logic.get("planner_path") == LABEL
        and route.get("route") == "deterministic_rule_plan"
        and route.get("model_call_attempted") is False
    ):
        return result
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
    if len(selected_rows) != 1 or len(utterance_rows) != 1:
        return result
    selected_row = selected_rows[0].get("payload")
    utterance = utterance_rows[0].get("payload")
    expected_plan = question_unknown_plan_p4(source, memory_data)
    parsed = _parse_direct_question(source)
    if not (
        isinstance(selected_row, dict)
        and isinstance(utterance, dict)
        and isinstance(expected_plan, dict)
        and parsed is not None
    ):
        return result
    selected_matches_logic = bool(
        selected.get("intent") == logic.get("intent") == "chat"
        and selected.get("scene") == logic.get("scene") == "casual"
        and selected.get("core_message_jp") == logic.get("core_message_jp")
        and selected_row.get("intent") == logic.get("intent")
        and selected_row.get("scene") == logic.get("scene")
        and selected_row.get("core_message_jp") == logic.get("core_message_jp")
        and logic.get("core_message_jp") == expected_plan["core_message_jp"]
    )
    carried = logic.get(LABEL)
    carried_certificate_matches = bool(
        carried is None
        or (
            isinstance(carried, dict)
            and all(
                carried.get(key) == certificate[key]
                for key in (
                    "source_sha256", "source_span_sha256",
                    "subject_sha256", "value_sha256",
                )
            )
        )
    )
    reply = result.get("reply")
    visible_matches = bool(
        carried_certificate_matches
        and selected_matches_logic
        and utterance.get("reply") == reply
        and _visible_unknown_preserved(reply, expected_plan["core_message_jp"])
    )
    payload = {
        "schema": SCHEMA,
        "status": "visible_unknown_preserved" if visible_matches else "selected_or_visible_mismatch",
        "visible_unknown_preserved": visible_matches,
        "selected_plan_matches_logic": selected_matches_logic,
        "carried_certificate_matches": carried_certificate_matches,
        "owner": "third_party",
        "statement_act": "question",
        "evidence_status": "not_found_in_available_context",
        "source_sha256": certificate["source_sha256"],
        "source_span_sha256": certificate["source_span_sha256"],
        "subject_sha256": certificate["subject_sha256"],
        "value_sha256": certificate["value_sha256"],
        "m21_route": "deterministic_rule_plan",
        "m31_model_authority_claimed": False,
        "memory_write_claimed": False,
        "raw_dialogue_persisted": False,
    }
    if selected_matches_logic:
        selected["planner_path"] = LABEL
        selected_row["planner_path"] = LABEL
    without_prior = [
        row for row in rows if not (isinstance(row, dict) and row.get("label") == LABEL)
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


def _finish_third_party_question_evidence_p4(self, result, source):
    materialize_third_party_question_evidence_p4(result, source)
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


def run_turn_debug_with_third_party_question_evidence_p4(
    self, user_input, input_context=None
):
    result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    return _finish_third_party_question_evidence_p4(self, result, user_input)


def emit_response_if_ready_with_third_party_question_evidence_p4(
    self, event, tick_result
):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    return _finish_third_party_question_evidence_p4(
        self, result, (event or {}).get("user_input")
    )


def install_third_party_question_evidence_p4():
    """Install only after the current-statement product authority layer."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    if not (
        statement_authority._INSTALLED
        and LeftBrain._rule_based_plan
        is statement_authority.rule_plan_with_current_statement_source_authority_p4
        and UruhaBrainV4_Mac.run_turn_debug
        is statement_authority.run_turn_debug_with_current_statement_source_authority_p4
        and UruhaBrainV4_Mac.emit_response_if_ready
        is statement_authority.emit_response_if_ready_with_current_statement_source_authority_p4
    ):
        raise RuntimeError(f"{LABEL}:prior_product_chain_changed")
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    LeftBrain._rule_based_plan = rule_plan_with_third_party_question_evidence_p4
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_third_party_question_evidence_p4
    UruhaBrainV4_Mac.emit_response_if_ready = (
        emit_response_if_ready_with_third_party_question_evidence_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "LABEL",
    "SCHEMA",
    "question_evidence_candidate_p4",
    "question_unknown_plan_p4",
    "materialize_third_party_question_evidence_p4",
    "install_third_party_question_evidence_p4",
]
