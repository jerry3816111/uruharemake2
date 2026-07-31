"""Separate planner coverage from reply realization for public-persona evaluation."""

from __future__ import annotations

from copy import deepcopy

import public_persona_missing_role_v8 as v8


SCHEMA = "uruha_public_persona_realization_audit_v9"


# These vocabularies are evaluation-only concept probes. They are never model input.
PLAN_ROLE_MARKERS = {
    "informal_public_self_introduction": {
        "public_activity_identity": ["配信者", "ゲーム", "配信", "雑談", "活動"],
        "audience_affiliation": ["視聴者", "みんな", "一緒", "参加者", "交流", "共同体", "気楽"],
    },
    "minor_delay_then_positive_promotion": {
        "brief_acknowledgement": ["遅れ", "遅れた", "忘れ", "待たせ", "今さら"],
        "shared_positive_focus": ["楽し", "勧め", "聴いて", "見て", "紹介", "作品へ注意"],
    },
    "fatigue_update_with_near_term_plan": {
        "current_state": ["眠", "疲", "疲労", "へとへと", "へろへろ"],
        "one_supported_next_action": ["食事", "食べ", "ゲーム", "休", "戻", "寝", "終え", "切り上げ"],
    },
    "minor_health_uncertainty_affecting_schedule": {
        "supported_current_state": ["喉", "頭", "胃", "体調", "不調", "調子"],
        "explicit_uncertainty": ["未確定", "不確か", "不安定", "まだ分から", "様子", "後で", "確約しな"],
        "preserve_decision_space": ["配信するか", "参加するか", "予定", "後で決", "待って決", "判断", "確約せず", "確約しな"],
    },
    "functional_stream_start_notification": {
        "start_signal": ["開始", "始め", "開いた", "始ま"],
        "content_name": ["ゲーム配信", "ルーム", "イベント", "対戦"],
        "entry_point": ["案内", "入口", "入って", "参加を促", "見られる", "視聴者"],
    },
}


REPLY_ROLE_MARKERS = deepcopy(PLAN_ROLE_MARKERS)
REPLY_ROLE_MARKERS["fatigue_update_with_near_term_plan"]["one_supported_next_action"].extend(
    ["終わ", "明日"]
)
REPLY_ROLE_MARKERS["minor_health_uncertainty_affecting_schedule"]["explicit_uncertainty"].extend(
    ["かも", "分から"]
)


SCORER_ROLE_MAP = {
    "public_activity": "public_activity_identity",
    "audience_affiliation": "audience_affiliation",
    "brief_acknowledgement": "brief_acknowledgement",
    "positive_focus": "shared_positive_focus",
    "current_state": "current_state",
    "next_action": "one_supported_next_action",
    "supported_state": "supported_current_state",
    "uncertainty": "explicit_uncertainty",
    "deferred_decision": "preserve_decision_space",
    "start_signal": "start_signal",
    "content_name": "content_name",
    "entry_point": "entry_point",
}


def _clean(value):
    return str(value or "").strip()


def planning_evidence(logic_data):
    """Return only preregistered planning fields, excluding evaluation markers."""
    logic = logic_data if isinstance(logic_data, dict) else {}
    speech_plan = logic.get("human_speech_plan") or {}
    fields = {
        "jp_summary": _clean(logic.get("jp_summary")),
        "core_message_jp": _clean(logic.get("core_message_jp")),
        "intent": _clean(logic.get("intent")),
        "dialogue_act": _clean(logic.get("dialogue_act")),
        "speech_plan_dialogue_act": _clean(speech_plan.get("dialogue_act")),
        "content_units": [_clean(item) for item in speech_plan.get("content_units") or []],
        "speech_moves": [_clean(item) for item in speech_plan.get("speech_moves") or []],
    }
    return fields


def _joined_evidence(evidence):
    values = []
    for value in evidence.values():
        values.extend(value if isinstance(value, list) else [value])
    return "\n".join(item for item in values if item)


def _marker_hits(text, markers):
    return [marker for marker in markers if marker and marker in text]


def compile_plan_coverage(logic_data):
    """Classify expected persona roles using plan fields, never scorer markers."""
    v8_contract = v8.compile_missing_role_contract(logic_data)
    if v8_contract["status"] != "active_development_hypothesis":
        return {
            "schema": SCHEMA,
            "status": "inactive_no_supported_context",
            "context": v8_contract["context"],
            "roles": [],
            "covered_roles": [],
            "missing_roles": [],
            "contains_fixed_reply": False,
            "runtime_authorized": False,
            "training_authorized": False,
        }
    context = v8_contract["context"]
    evidence = planning_evidence(logic_data)
    text = _joined_evidence(evidence)
    roles = []
    for role, markers in PLAN_ROLE_MARKERS[context].items():
        hits = _marker_hits(text, markers)
        roles.append({"role": role, "planned": bool(hits), "plan_marker_hits": hits})
    return {
        "schema": SCHEMA,
        "status": "active_development_hypothesis",
        "context": context,
        "roles": roles,
        "covered_roles": [item["role"] for item in roles if item["planned"]],
        "missing_roles": [item["role"] for item in roles if not item["planned"]],
        "contains_fixed_reply": False,
        "runtime_authorized": False,
        "training_authorized": False,
    }


def missing_required_roles(reasons):
    roles = []
    for reason in reasons or []:
        prefix = "missing_required:"
        if not str(reason).startswith(prefix):
            continue
        scorer_id = str(reason)[len(prefix) :]
        role = SCORER_ROLE_MAP.get(scorer_id)
        if role:
            roles.append(role)
    return roles


def classify_missing_role(logic_data, reply, role):
    coverage = compile_plan_coverage(logic_data)
    planned = role in coverage["covered_roles"]
    context = coverage["context"]
    reply_hits = _marker_hits(str(reply or ""), REPLY_ROLE_MARKERS[context][role])
    if not planned:
        classification = "planner_role_missing"
    elif reply_hits:
        classification = "lexical_scorer_gap"
    else:
        classification = "planned_but_unrealized"
    return {
        "role": role,
        "planned": planned,
        "plan_marker_hits": next(
            item["plan_marker_hits"] for item in coverage["roles"] if item["role"] == role
        ),
        "reply_concept_hits": reply_hits,
        "classification": classification,
    }
