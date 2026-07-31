"""Typed evaluation contract for public-persona behavior calibration."""

from __future__ import annotations

from copy import deepcopy

import public_persona_contract_v3 as v3


SCHEMA = "uruha_public_persona_scorer_contract_v4"


SCORER_POLICIES = {
    "informal_public_self_introduction": {
        "required_groups": [
            {"id": "public_activity", "markers": ["ゲーム", "配信", "雑談"]},
            {"id": "audience_affiliation", "markers": ["みんな", "一緒", "リスナー"]},
        ],
        "optional_groups": [
            {"id": "mild_self_tease", "markers": ["だら", "ぐだ", "適当", "寝"]},
        ],
        "forbidden_groups": [
            {"id": "private_identity_claim", "markers": ["中の人", "本名", "私生活では"]},
            {"id": "perfect_idol_claim", "markers": ["完璧なアイドル", "理想のアイドル"]},
        ],
        "ordered_pairs": [["public_activity", "audience_affiliation"]],
        "maximum_characters": 72,
    },
    "minor_delay_then_positive_promotion": {
        "required_groups": [
            {"id": "brief_acknowledgement", "markers": ["遅", "今さら", "忘れ", "待たせ"]},
            {"id": "positive_focus", "markers": ["楽し", "見て", "聴いて", "一緒"]},
        ],
        "optional_groups": [],
        "forbidden_groups": [
            {"id": "extended_apology", "markers": ["何度でも謝", "心よりお詫び", "深くお詫び"]},
            {"id": "self_punishment", "markers": ["全部うちが悪", "取り返しのつかない"]},
        ],
        "ordered_pairs": [["brief_acknowledgement", "positive_focus"]],
        "maximum_characters": 72,
    },
    "fatigue_update_with_near_term_plan": {
        "required_groups": [
            {"id": "current_state", "markers": ["眠", "疲", "へとへと"]},
            {"id": "next_action", "markers": ["食べ", "ご飯", "休", "戻", "寝", "ゲーム"]},
        ],
        "optional_groups": [],
        "forbidden_groups": [
            {"id": "crisis_dramatization", "markers": ["人生が終わ", "深刻な状態", "永遠に休"]},
            {"id": "caregiver_demand", "markers": ["看病して"]},
        ],
        "ordered_pairs": [["current_state", "next_action"]],
        "maximum_characters": 68,
    },
    "minor_health_uncertainty_affecting_schedule": {
        "required_groups": [
            {"id": "supported_state", "markers": ["喉", "頭", "胃", "調子"]},
            {"id": "uncertainty", "markers": ["様子", "まだ", "分から", "かも"]},
            {"id": "deferred_decision", "markers": ["後で", "決め", "待って"]},
        ],
        "optional_groups": [],
        "forbidden_groups": [
            {"id": "diagnosis", "markers": ["診断", "病名", "に違いない"]},
            {"id": "false_certainty", "markers": ["絶対配信", "絶対参加", "必ず治"]},
        ],
        "ordered_pairs": [["supported_state", "deferred_decision"]],
        "maximum_characters": 72,
    },
    "functional_stream_start_notification": {
        "required_groups": [
            {"id": "start_signal", "markers": ["始め", "開始", "開いた", "始ま"]},
            {"id": "content_name", "markers": ["ゲーム", "配信", "ルーム", "イベント", "対戦"]},
            {"id": "entry_point", "markers": ["見て", "入って", "参加", "今から"]},
        ],
        "optional_groups": [],
        "forbidden_groups": [
            {"id": "emotional_preface", "markers": ["そういえば", "まず説明すると"]},
            {"id": "background_story", "markers": ["長い背景", "思い出話", "人生について"]},
        ],
        "ordered_pairs": [],
        "maximum_characters": 44,
    },
}


def compile_scorer_contract(context):
    """Return an evaluation-only contract derived from one V3 development policy."""
    context_name = str(context or "").strip()
    policy = SCORER_POLICIES.get(context_name)
    if policy is None:
        return {
            "schema": SCHEMA,
            "status": "inactive_unsupported_context",
            "context": context_name or None,
            "source_observation_ids": [],
            "required_groups": [],
            "optional_groups": [],
            "forbidden_groups": [],
            "ordered_pairs": [],
            "maximum_characters": None,
            "runtime_authorized": False,
            "training_authorized": False,
        }
    return {
        "schema": SCHEMA,
        "status": "active_evaluation_only",
        "context": context_name,
        "source_observation_ids": list(v3.POLICIES[context_name]["source_observation_ids"]),
        **deepcopy(policy),
        "runtime_authorized": False,
        "training_authorized": False,
    }


def _group_map(contract):
    groups = {}
    for field in ("required_groups", "optional_groups", "forbidden_groups"):
        for group in contract[field]:
            groups[group["id"]] = group
    return groups


def _first_marker_index(text, markers):
    indices = [text.find(marker) for marker in markers if marker and text.find(marker) >= 0]
    return min(indices) if indices else -1


def score_reply(reply, contract):
    """Score required, optional, forbidden, order, and length without model calls."""
    text = str(reply or "").strip()
    if contract.get("status") != "active_evaluation_only":
        return {
            "scored": False,
            "passed": None,
            "reasons": ["unsupported_context"],
            "required_hits": {},
            "optional_hits": {},
            "forbidden_hits": {},
            "ordering_checks": [],
            "length_pass": None,
        }

    required_hits = {
        group["id"]: _first_marker_index(text, group["markers"]) >= 0
        for group in contract["required_groups"]
    }
    optional_hits = {
        group["id"]: _first_marker_index(text, group["markers"]) >= 0
        for group in contract["optional_groups"]
    }
    forbidden_hits = {
        group["id"]: [marker for marker in group["markers"] if marker and marker in text]
        for group in contract["forbidden_groups"]
    }
    groups = _group_map(contract)
    ordering_checks = []
    for first_id, second_id in contract["ordered_pairs"]:
        first_index = _first_marker_index(text, groups[first_id]["markers"])
        second_index = _first_marker_index(text, groups[second_id]["markers"])
        ordering_checks.append(
            {
                "first_group": first_id,
                "second_group": second_id,
                "first_index": first_index,
                "second_index": second_index,
                "passed": first_index >= 0 and second_index >= 0 and first_index < second_index,
            }
        )
    length_pass = len(text) <= int(contract["maximum_characters"])
    reasons = []
    reasons.extend(f"missing_required:{name}" for name, hit in required_hits.items() if not hit)
    reasons.extend(f"forbidden:{name}" for name, hits in forbidden_hits.items() if hits)
    reasons.extend(
        f"wrong_order:{item['first_group']}->{item['second_group']}"
        for item in ordering_checks
        if not item["passed"]
    )
    if not length_pass:
        reasons.append("too_long")
    return {
        "scored": True,
        "passed": not reasons,
        "reasons": reasons,
        "required_hits": required_hits,
        "optional_hits": optional_hits,
        "forbidden_hits": forbidden_hits,
        "ordering_checks": ordering_checks,
        "length_pass": length_pass,
    }
