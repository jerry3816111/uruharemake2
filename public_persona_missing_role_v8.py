"""Detect and project only dialogue roles missing from the existing semantic plan."""

from __future__ import annotations

from copy import deepcopy

import public_persona_contract_v3 as v3


SCHEMA = "uruha_public_persona_missing_role_v8"


ROLE_SCHEMAS = {
    "informal_public_self_introduction": [
        {"role": "public_activity_identity", "evidence_markers": ["ゲーム", "配信", "雑談", "遊"]},
        {"role": "audience_affiliation", "evidence_markers": ["みんな", "一緒", "リスナー", "気楽", "ゆる"]},
    ],
    "minor_delay_then_positive_promotion": [
        {"role": "brief_acknowledgement", "evidence_markers": ["遅", "今さら", "忘れ", "待たせ"]},
        {"role": "shared_positive_focus", "evidence_markers": ["楽し", "見て", "聴いて", "一緒"]},
    ],
    "fatigue_update_with_near_term_plan": [
        {"role": "current_state", "evidence_markers": ["眠", "疲", "へとへと", "へろへろ"]},
        {"role": "one_supported_next_action", "evidence_markers": ["食べ", "ご飯", "休", "戻", "寝", "ゲーム", "終", "遊"]},
    ],
    "minor_health_uncertainty_affecting_schedule": [
        {"role": "supported_current_state", "evidence_markers": ["喉", "頭", "痛", "胃", "調子"]},
        {"role": "explicit_uncertainty", "evidence_markers": ["様子", "まだ", "分から", "待"]},
        {"role": "preserve_decision_space", "evidence_markers": ["配信", "予定", "参加", "決め", "判断", "後で"]},
    ],
    "functional_stream_start_notification": [
        {"role": "start_signal", "evidence_markers": ["始", "開始", "開"]},
        {"role": "content_name", "evidence_markers": ["ゲーム", "配信", "ルーム", "部屋", "イベント", "対戦"]},
        {"role": "entry_point", "evidence_markers": ["見", "入", "参加", "今"]},
    ],
}


def _role_has_evidence(groups, role_markers):
    semantic_markers = [str(marker or "") for group in groups for marker in group]
    return any(
        role_marker in semantic_marker or semantic_marker in role_marker
        for semantic_marker in semantic_markers
        for role_marker in role_markers
        if semantic_marker and role_marker
    )


def compile_missing_role_contract(logic_data):
    """Return role coverage derived only from the existing semantic contract."""
    contract = v3.compile_persona_contract(logic_data)
    if contract["status"] != "active_development_hypothesis":
        return {
            "schema": SCHEMA,
            "status": "inactive_no_supported_context",
            "context": contract["context"],
            "covered_roles": [],
            "missing_roles": [],
            "contains_fixed_reply": False,
            "runtime_authorized": False,
            "training_authorized": False,
        }
    groups = (logic_data or {}).get("required_marker_groups") or []
    role_schema = ROLE_SCHEMAS[contract["context"]]
    covered = [
        item["role"]
        for item in role_schema
        if _role_has_evidence(groups, item["evidence_markers"])
    ]
    missing = [item["role"] for item in role_schema if item["role"] not in covered]
    return {
        "schema": SCHEMA,
        "status": "active_development_hypothesis",
        "context": contract["context"],
        "covered_roles": covered,
        "missing_roles": missing,
        "contains_fixed_reply": False,
        "runtime_authorized": False,
        "training_authorized": False,
    }


def project_missing_roles(payload_data, contract):
    """Add one compact field only when the semantic plan lacks a required role."""
    payload = deepcopy(payload_data) if isinstance(payload_data, dict) else {}
    missing = list(contract.get("missing_roles") or [])
    if not missing:
        return payload
    leftbrain_plan = deepcopy(payload.get("leftbrain_plan") or {})
    leftbrain_plan["missing_dialogue_roles"] = missing
    payload["leftbrain_plan"] = leftbrain_plan
    return payload
