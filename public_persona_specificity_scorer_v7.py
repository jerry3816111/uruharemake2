"""Evaluation-only check for concrete details unsupported by one case."""

from __future__ import annotations


SCHEMA = "uruha_public_persona_specificity_scorer_v7"


CONCRETE_SLOT_FAMILIES = {
    "minor_delay_then_positive_promotion": ["動画", "イベント", "作品", "曲"],
    "fatigue_update_with_near_term_plan": [
        "眠",
        "疲",
        "へとへと",
        "へろへろ",
        "食べ",
        "ご飯",
        "休",
        "戻",
        "寝",
        "ゲーム",
    ],
    "minor_health_uncertainty_affecting_schedule": ["喉", "頭", "胃"],
    "functional_stream_start_notification": [
        "ゲーム",
        "配信",
        "ルーム",
        "部屋",
        "イベント",
        "対戦",
    ],
}


def _case_evidence_text(case):
    logic = case.get("logic") or {}
    plan = logic.get("human_speech_plan") or {}
    groups = logic.get("required_marker_groups") or []
    values = [
        logic.get("jp_summary"),
        logic.get("core_message_jp"),
        *(plan.get("content_units") or []),
        *(marker for group in groups for marker in group),
    ]
    return " ".join(str(value or "") for value in values)


def score_specificity(reply, case):
    """Flag only sibling concrete slots absent from the frozen case evidence."""
    context = str(case.get("context") or "")
    vocabulary = CONCRETE_SLOT_FAMILIES.get(context, [])
    evidence = _case_evidence_text(case)
    text = str(reply or "")
    unsupported = [
        marker for marker in vocabulary if marker in text and marker not in evidence
    ]
    return {
        "schema": SCHEMA,
        "scored": bool(vocabulary),
        "passed": not unsupported,
        "unsupported_concrete_markers": unsupported,
    }
