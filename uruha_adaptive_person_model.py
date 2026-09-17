"""M18 hierarchical adaptive desired-response model for the live runtime.

The persisted state is an operational interaction model, not factual memory and
not a claim about a user's private mind.  It stores only named parameters,
outcome counts, turn numbers, and hashes of evidence.  Raw dialogue is never
written to this store.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path

from uruha_reference_person_equation import POLICIES, REFERENCE_PERSON, score_candidates


MODEL_SCHEMA = "uruha_adaptive_person_model_m18"
M17_MODEL_SCHEMA = "uruha_adaptive_person_model_m17"
LEGACY_MODEL_SCHEMA = "uruha_adaptive_person_model_m16"
STATE_SCHEMA = "uruha_desired_response_state_m18"
DECISION_SCHEMA = "uruha_desired_response_decision_m18"
FEEDBACK_SCHEMA = "uruha_desired_response_feedback_update_m18"
SCOPE_SCHEMA = "uruha_adaptive_context_scope_m18"
HIERARCHY_SCHEMA = "uruha_adaptive_scope_hierarchy_m18"
DIMENSION_SCHEMA = "uruha_composable_response_dimensions_m18"
CORRECTION_SCHEMA = "uruha_correction_aware_surface_m20"
DESIRED_RESPONSE_MODE_SCHEMA = "uruha_desired_response_mode_m23"
EXPLICIT_DESIRED_RESPONSE_SCHEMA_M25 = "uruha_cross_lingual_explicit_desired_response_m25"
EXPLICIT_CONVERSATION_ACT_SCHEMA_P3_B50 = (
    "uruha_explicit_conversation_act_p3_b50"
)
IMPLICIT_RESPONSE_DISTRIBUTION_SCHEMA_M26 = (
    "uruha_outcome_calibrated_implicit_response_distribution_m26"
)
CAUSAL_OUTCOME_LEDGER_SCHEMA_M27 = "uruha_causal_outcome_calibration_ledger_m27"
CAUSAL_OUTCOME_SUMMARY_SCHEMA_M27 = "uruha_causal_outcome_calibration_summary_m27"
FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28 = "uruha_feedback_topic_transition_m28"
LITERAL_TOPIC_PROJECTION_SCHEMA_M29 = "uruha_generalized_literal_topic_projection_m29"
SEMANTIC_AUTHORIZATION_SCHEMA_M31 = "uruha_semantic_authorization_m31"
SEMANTIC_COMMIT_REPAIR_SCHEMA_M32 = "uruha_deterministic_semantic_commit_m32"
TRIGGER_RELATION_SCHEMA_M37 = "uruha_pragmatic_trigger_relation_m37"
TRIGGER_RELATION_UPDATE_SCHEMA_M37 = "uruha_pragmatic_trigger_relation_update_m37"
CURRENT_TURN_SEMANTIC_COMMIT_SCHEMA_M48 = "uruha_current_turn_semantic_commit_m48"
STORE_VERSION = 5
DEFAULT_SCOPE_TTL_REVISIONS = 24
M37_TRIGGER_RELATION_TTL_REVISIONS = 48
M27_MAX_LEDGER_ENTRIES = 120
M27_MIN_DECISIVE_EXECUTED_SAMPLES = 8

POLICY_TO_RESPONSE_MODE_M23 = {
    "care_physiology": "physiological_care",
    "solve_regulation": "practical_help",
    "listen_presence": "listening",
    "share_arousal": "companionship",
    "playful_tease": "playful_tease",
    "calibrate_need": "low_pressure_clarification",
}

MODE_EVIDENCE_ATOMS_M23 = {
    "physiological_care": ("sleep_debt", "physical_strain", "uncertainty"),
    "practical_help": ("solution_request", "uncertainty"),
    "listening": ("listening_request", "companionship_request", "uncertainty"),
    "companionship": ("companionship_request", "positive_arousal", "uncertainty"),
    "playful_tease": ("humor_invitation", "relationship_familiarity", "uncertainty"),
    "low_pressure_clarification": ("uncertainty",),
}

EXPLICIT_REQUEST_SURFACES_M25 = {
    "care_physiology": "体がしんどい方なら、まず水飲んで少し休も。",
    "solve_regulation": "今すぐできる一個だけ、一緒に決めよ。",
    "listen_presence": "うん。今は方法出さないから、そのまま話して。",
    "share_arousal": "うん。今は質問しないで、ちょっとここにいる。",
    "playful_tease": "朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。",
    "calibrate_need": "じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？",
}

RESPONSE_DIMENSIONS = (
    "care",
    "directness",
    "humor",
    "listening",
    "actionability",
    "distance",
)

# These are semantic strategy anchors, not final utterance templates.  The
# selected vector is subsequently adapted by current evidence and verified
# scoped preferences, then realized through one of several bounded Japanese
# surfaces.
POLICY_DIMENSION_PROFILES = {
    "care_physiology": {
        "care": 0.92,
        "directness": 0.64,
        "humor": 0.02,
        "listening": 0.58,
        "actionability": 0.48,
        "distance": 0.34,
    },
    "solve_regulation": {
        "care": 0.56,
        "directness": 0.90,
        "humor": 0.05,
        "listening": 0.28,
        "actionability": 0.96,
        "distance": 0.30,
    },
    "listen_presence": {
        "care": 0.78,
        "directness": 0.52,
        "humor": 0.03,
        "listening": 0.98,
        "actionability": 0.08,
        "distance": 0.24,
    },
    "share_arousal": {
        "care": 0.56,
        "directness": 0.72,
        "humor": 0.38,
        "listening": 0.56,
        "actionability": 0.10,
        "distance": 0.18,
    },
    "playful_tease": {
        "care": 0.34,
        "directness": 0.94,
        "humor": 0.98,
        "listening": 0.26,
        "actionability": 0.04,
        "distance": 0.08,
    },
    "calibrate_need": {
        "care": 0.60,
        "directness": 0.72,
        "humor": 0.08,
        "listening": 0.74,
        "actionability": 0.18,
        "distance": 0.30,
    },
}

SURFACE_VARIANTS = {
    "care_physiology": [
        "寝不足とか体のしんどさがあるなら、まず水飲んでちょっと休も。",
        "体がしんどい方なら、無理に頭止めようとしないで一回水飲も。",
        "寝てないなら、考える方より先に体を少し休ませよ。",
    ],
    "solve_regulation": [
        "今すぐなら、頭の中を一回メモに全部出して、五分だけ呼吸整えよ。",
        "まず五分だけ、気になってること全部メモに逃がそ。順番はそのあとでいい。",
        "最初の一個だけ決めよ。いま頭に浮かんでることをメモして、五分だけそこから離れればいい。",
    ],
    "listen_presence": [
        "今日はずっとそれに付き合わされてんのか。今は方法出さないから、そのまま話して。",
        "解決策より、まず何がずっと引っかかってるか聞かせて。",
        "そっか。今は直そうとしなくていいから、続きそのまま言って。",
    ],
    "share_arousal": [
        "そりゃ頭止まんねえわ。結果来るまでうちも一緒にそわそわしとく。",
        "それは落ち着けって方が無理だろ。来るまで一緒に待っとこ。",
        "あー、それ楽しみで回り続けてるやつじゃん。うちまで気になってきた。",
    ],
    "playful_tease": [
        "朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。",
        "お前の脳みそ、朝から勝手に延長戦入ってんじゃん。",
        "頭だけ先に三日分走ってるだろ。ちょっと帰ってこいって。",
        "また脳内会議だけ終電逃してんのかよ。",
    ],
    "calibrate_need": [
        "寝てないのか、考え事で止まんないのか、まずそこだけどっち？",
        "しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？",
        "今ほしいの、止め方と、ただ聞いてほしいのと、どっちに近い？",
    ],
}

ATOM_DEFAULTS = {
    "sleep_debt": (0.30, 0.12),
    "physical_strain": (0.40, 0.28),
    "solution_request": (0.38, 0.20),
    "listening_request": (0.38, 0.20),
    "positive_arousal": (0.44, 0.18),
    "humor_invitation": (0.28, 0.14),
    "relationship_familiarity": (0.50, 0.18),
    "companionship_request": (0.40, 0.18),
    "task_pressure": (0.30, 0.12),
    "uncertainty": (0.86, 0.86),
}

PERSISTABLE_ATOMS = {
    "solution_request",
    "listening_request",
    "positive_arousal",
    "humor_invitation",
    "relationship_familiarity",
    "companionship_request",
}

PROTECTED_INTENTS = {
    "abuse_pushback",
    "sexual_boundary",
    "crisis_support",
    "giving_up_support",
    "ooc_or_knowledge_refusal",
    "hallucination_safe",
}
PROTECTED_SCENES = {"boundary", "refusal", "ooc_defense", "crisis"}


def _clip(value):
    return max(0.0, min(1.0, float(value or 0.0)))


def _digest(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]


def _contains(text, markers):
    lowered = str(text or "").lower()
    return any(str(marker).lower() in lowered for marker in markers)


_M37_TRIGGER_PATTERN_FAMILIES = {
    "cognitive_overactivity": {
        "zh": {
            "heads": (
                r"(?:念頭|念头|想法|思緒|思绪|腦袋|脑袋|腦子|脑子|腦中|脑中|腦裡|脑里)",
            ),
            "predicates": (
                r"(?:停不下|停不住|打轉|打转|繞來繞去|绕来绕去|反覆|反复|亂跑|乱跑|一個接一個|一个接一个|轉個不停|转个不停)",
            ),
        },
        "en": {
            "heads": (r"\b(?:thoughts?|ideas?|mind|head)\b",),
            "predicates": (
                r"\b(?:rac(?:e|es|ed|ing)|bounc(?:e|es|ed|ing)|circl(?:e|es|ed|ing)|ricochet(?:s|ed|ing)?|spin(?:s|ning)?|loop(?:s|ed|ing)?|won't\s+stop|will\s+not\s+stop)\b",
            ),
        },
        "ja": {
            "heads": (r"(?:頭|考え|思考|思い|アイデア)",),
            "predicates": (
                r"(?:止まらない|止まってくれない|回りっぱなし|ぐるぐる|堂々巡り|考え続け|次々)",
            ),
        },
    },
    "task_stall": {
        "zh": {
            "heads": (r"(?:報告|报告|作業|作业|專案|项目|進度|进度|工作|題目|题目|草稿)",),
            "predicates": (r"(?:卡住|卡在|卡得|動不了|动不了|推不動|推不动|沒進展|没进展|停在原地)",),
        },
        "en": {
            "heads": (r"\b(?:report|assignment|project|work|draft|task)\b",),
            "predicates": (r"\b(?:stuck|stall(?:ed|ing)?|blocked|not\s+moving|can't\s+progress|cannot\s+progress)\b",),
        },
        "ja": {
            "heads": (r"(?:課題|レポート|作業|プロジェクト|原稿)",),
            "predicates": (r"(?:行き詰ま|詰まって|進まない|止まって|先へ進めない)",),
        },
    },
    "waiting_for_outcome": {
        "zh": {
            "heads": (r"(?:回覆|回复|回信|消息|結果|结果|通知)",),
            "predicates": (r"(?:還在等|还在等|一直等|還沒來|还没来|沒收到|没收到|一直看)",),
        },
        "en": {
            "heads": (r"\b(?:reply|response|result|message|decision|notification)\b",),
            "predicates": (r"\b(?:wait(?:ing|ed)?|hasn't\s+arrived|has\s+not\s+arrived|keep\s+checking|still\s+checking)\b",),
        },
        "ja": {
            "heads": (r"(?:返事|返信|結果|連絡|通知)",),
            "predicates": (r"(?:待って|来ない|届かない|確認し続け)",),
        },
    },
}


def extract_observable_trigger_predicates_m37(user_input):
    """Extract bounded visible trigger predicates without retaining source text."""
    text = str(user_input or "")
    lowered = text.lower()
    matches = []
    for predicate, language_groups in _M37_TRIGGER_PATTERN_FAMILIES.items():
        for language, patterns in language_groups.items():
            head_hits = [
                index
                for index, pattern in enumerate(patterns["heads"], start=1)
                if re.search(pattern, lowered, re.I)
            ]
            predicate_hits = [
                index
                for index, pattern in enumerate(patterns["predicates"], start=1)
                if re.search(pattern, lowered, re.I)
            ]
            if head_hits and predicate_hits:
                matches.append(
                    {
                        "predicate": predicate,
                        "language": language,
                        "cue_ids": [
                            f"{predicate}:{language}:head:{index}"
                            for index in head_hits
                        ]
                        + [
                            f"{predicate}:{language}:predicate:{index}"
                            for index in predicate_hits
                        ],
                    }
                )
    predicates = sorted({row["predicate"] for row in matches})
    return {
        "schema": TRIGGER_RELATION_SCHEMA_M37,
        "status": (
            "single_observable_trigger"
            if len(predicates) == 1
            else "multiple_observable_triggers"
            if len(predicates) > 1
            else "no_bounded_observable_trigger"
        ),
        "predicates": predicates,
        "matched_languages": sorted({row["language"] for row in matches}),
        "cue_ids": list(
            dict.fromkeys(
                cue_id for row in matches for cue_id in row["cue_ids"]
            )
        )[:16],
        "evidence_digest": _digest(text),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def _conditional_relation_cues_m37(user_input):
    text = str(user_input or "")
    patterns = {
        "zh": (
            r"(?:如果|若是|只要|每次|下次)",
            r"(?:當|当).{1,36}(?:時|时)",
            r"(?:時|时)[，,]",
        ),
        "en": (r"\b(?:when|whenever|if)\b",),
        "ja": (r"(?:時は|ときは|たら[、,]|なら[、,])",),
    }
    cues = []
    for language, language_patterns in patterns.items():
        for index, pattern in enumerate(language_patterns, start=1):
            if re.search(pattern, text, re.I):
                cues.append(f"conditional:{language}:{index}")
    return cues


def classify_trigger_relation_candidate_m37(user_input, explicit_request=None):
    """Separate a future observable trigger from its requested response policy."""
    trigger = extract_observable_trigger_predicates_m37(user_input)
    explicit = deepcopy(
        explicit_request
        if isinstance(explicit_request, dict)
        else classify_explicit_desired_response_m25(user_input)
    )
    conditional_cues = _conditional_relation_cues_m37(user_input)
    predicates = trigger.get("predicates") or []
    policy_id = str(explicit.get("selected_policy") or "")
    candidate_ready = bool(
        len(predicates) == 1
        and conditional_cues
        and explicit.get("detected")
        and explicit.get("authority") == "current_explicit_desired_response"
        and policy_id in POLICIES
        and not explicit.get("protected_risk_cue")
    )
    if candidate_ready:
        status = "candidate_ready"
        reason = "conditional_observable_trigger_and_explicit_response_policy_separated"
    elif explicit.get("protected_risk_cue"):
        status = "blocked_protected_route"
        reason = "protected_risk_route_outranks_preference_relation"
    elif not conditional_cues:
        status = "current_only_not_relation"
        reason = "no_future_or_recurring_conditional_marker"
    elif len(predicates) > 1:
        status = "ambiguous_multiple_triggers"
        reason = "multiple_observable_trigger_predicates_fail_closed"
    elif not predicates:
        status = "unrecognized_trigger"
        reason = "no_bounded_observable_trigger_predicate"
    else:
        status = "missing_explicit_response_policy"
        reason = "trigger_present_without_preexisting_explicit_response_policy"
    predicate = predicates[0] if len(predicates) == 1 else None
    source_digest = trigger.get("evidence_digest")
    return {
        "schema": TRIGGER_RELATION_SCHEMA_M37,
        "status": status,
        "reason": reason,
        "relation_id": (
            f"m37-{_digest(f'{predicate}|{policy_id}|{source_digest}')}"
            if candidate_ready
            else None
        ),
        "trigger_predicate": predicate,
        "response_policy": policy_id or None,
        "trigger_cue_ids": list(trigger.get("cue_ids") or []),
        "conditional_cue_ids": conditional_cues[:8],
        "matched_languages": list(trigger.get("matched_languages") or []),
        "source_digest": source_digest,
        "verification_required": candidate_ready,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def _normalise_trigger_relation_candidate_m37(payload):
    payload = payload if isinstance(payload, dict) else {}
    predicate = str(payload.get("trigger_predicate") or "")[:48]
    policy_id = str(payload.get("response_policy") or "")[:40]
    return {
        "schema": TRIGGER_RELATION_SCHEMA_M37,
        "status": str(payload.get("status") or "not_available")[:64],
        "reason": str(payload.get("reason") or "")[:120],
        "relation_id": str(payload.get("relation_id") or "")[:48] or None,
        "trigger_predicate": predicate or None,
        "response_policy": policy_id if policy_id in POLICIES else None,
        "trigger_cue_ids": [
            str(value)[:96] for value in (payload.get("trigger_cue_ids") or [])[:16]
        ],
        "conditional_cue_ids": [
            str(value)[:64]
            for value in (payload.get("conditional_cue_ids") or [])[:8]
        ],
        "matched_languages": [
            str(value)[:8] for value in (payload.get("matched_languages") or [])[:4]
        ],
        "source_digest": str(payload.get("source_digest") or "")[:32],
        "verification_required": bool(payload.get("verification_required")),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def _normalise_verified_trigger_relation_m37(payload):
    payload = payload if isinstance(payload, dict) else {}
    predicate = str(payload.get("trigger_predicate") or "")[:48]
    policy_id = str(payload.get("response_policy") or "")[:40]
    history = payload.get("verification_history") or {}
    return {
        "schema": TRIGGER_RELATION_SCHEMA_M37,
        "relation_id": str(payload.get("relation_id") or "")[:48],
        "trigger_predicate": predicate,
        "response_policy": policy_id,
        "status": str(payload.get("status") or "verified")[:32],
        "active": bool(payload.get("active", True)),
        "confidence": _clip(payload.get("confidence", 0.0)),
        "source_kind": str(
            payload.get("source_kind") or "verified_future_response_relation"
        )[:64],
        "source_digest": str(payload.get("source_digest") or "")[:32],
        "created_turn": max(0, int(payload.get("created_turn") or 0)),
        "updated_turn": max(0, int(payload.get("updated_turn") or 0)),
        "updated_revision": max(0, int(payload.get("updated_revision") or 0)),
        "ttl_revisions": max(
            1,
            min(
                500,
                int(
                    payload.get("ttl_revisions")
                    or M37_TRIGGER_RELATION_TTL_REVISIONS
                ),
            ),
        ),
        "verification_history": {
            "supported": max(0, int(history.get("supported") or 0)),
            "contradicted": max(0, int(history.get("contradicted") or 0)),
            "uncertain": max(0, int(history.get("uncertain") or 0)),
            "last_feedback_digest": str(
                history.get("last_feedback_digest") or ""
            )[:32],
        },
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def match_verified_trigger_relation_m37(model, user_input):
    """Match current observable semantics to one verified raw-free relation."""
    trigger = extract_observable_trigger_predicates_m37(user_input)
    predicates = trigger.get("predicates") or []
    if len(predicates) != 1:
        return {
            "schema": TRIGGER_RELATION_SCHEMA_M37,
            "status": (
                "ambiguous_multiple_triggers"
                if len(predicates) > 1
                else "no_current_trigger_match"
            ),
            "current_trigger": trigger,
            "raw_dialogue_persisted": False,
        }
    predicate = predicates[0]
    revision_count = max(0, int((model or {}).get("revision_count") or 0))
    eligible = []
    expired = []
    for incoming in (model or {}).get("trigger_policy_relations_m37") or []:
        relation = _normalise_verified_trigger_relation_m37(incoming)
        if (
            not relation.get("active")
            or relation.get("status") != "verified"
            or relation.get("trigger_predicate") != predicate
            or relation.get("response_policy") not in POLICIES
        ):
            continue
        age = max(0, revision_count - int(relation.get("updated_revision") or 0))
        if age > int(relation.get("ttl_revisions") or 0):
            expired.append(relation.get("relation_id"))
            continue
        relation["age_revisions"] = age
        eligible.append(relation)
    eligible.sort(
        key=lambda row: (
            -int(row.get("updated_revision") or 0),
            -float(row.get("confidence") or 0.0),
            str(row.get("relation_id") or ""),
        )
    )
    if not eligible:
        return {
            "schema": TRIGGER_RELATION_SCHEMA_M37,
            "status": "no_verified_relation",
            "trigger_predicate": predicate,
            "current_trigger": trigger,
            "expired_relation_ids": expired[:8],
            "raw_dialogue_persisted": False,
        }
    top_revision = int(eligible[0].get("updated_revision") or 0)
    top = [
        row for row in eligible if int(row.get("updated_revision") or 0) == top_revision
    ]
    if len({row.get("response_policy") for row in top}) > 1:
        return {
            "schema": TRIGGER_RELATION_SCHEMA_M37,
            "status": "ambiguous_verified_relations",
            "trigger_predicate": predicate,
            "current_trigger": trigger,
            "candidate_relation_ids": [row.get("relation_id") for row in top],
            "raw_dialogue_persisted": False,
        }
    selected = eligible[0]
    return {
        "schema": TRIGGER_RELATION_SCHEMA_M37,
        "status": "matched_verified_trigger_relation",
        "authority": "verified_observable_trigger_relation_m37",
        "trigger_predicate": predicate,
        "response_policy": selected.get("response_policy"),
        "relation_id": selected.get("relation_id"),
        "confidence": selected.get("confidence"),
        "age_revisions": selected.get("age_revisions"),
        "current_trigger_cue_ids": list(trigger.get("cue_ids") or []),
        "current_evidence_digest": trigger.get("evidence_digest"),
        "source_digest": selected.get("source_digest"),
        "match_kind": "typed_predicate_morphology_or_bounded_paraphrase",
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def _normalise_feedback_token_m28(text):
    """Collapse punctuation without translating or retaining the raw turn."""
    return re.sub(r"[\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def _pure_feedback_act_m28(user_input):
    token = _normalise_feedback_token_m28(user_input)
    support_tokens = {
        "對就是這樣",
        "对就是这样",
        "沒錯",
        "没错",
        "そうそう",
        "その通り",
        "exactly",
        "thatsright",
    }
    correction_tokens = {
        "不是這樣",
        "不是这样",
        "不對",
        "不对",
        "違う",
        "そうじゃない",
        "no",
        "thatswrong",
    }
    if token in support_tokens:
        return "support"
    if token in correction_tokens:
        return "correction"
    return None


def _literal_topic_surface_m28(user_input):
    """Return a bounded Japanese surface for a self-contained literal topic.

    These rows are typed grounding fallbacks for transition safety, not a claim
    that the complete pragmatic meaning of the turn has been decoded.  An
    ordinary surface model remains free to handle richer topics outside this
    narrow guard.
    """
    text = str(user_input or "").strip()
    lowered = text.lower()
    typed_surfaces = (
        (
            "weather_rain",
            ("下雨", "下著雨", "下着雨", "雨が降", "雨降", "raining", "rainy"),
            "雨なんだ。出るなら傘忘れんなよ。",
        ),
        (
            "weather_snow",
            ("下雪", "雪が降", "雪降", "snowing", "snowy"),
            "雪なんだ。出るなら足元気をつけろよ。",
        ),
        (
            "weather_cold",
            ("很冷", "好冷", "寒い", "冷え", "freezing", "cold outside"),
            "寒いんだ。ちゃんとあったかくしろよ。",
        ),
        (
            "weather_hot",
            ("很熱", "很热", "好熱", "好热", "暑い", "hot outside"),
            "暑いんだ。ちゃんと水飲めよ。",
        ),
    )
    for topic_kind, markers, surface in typed_surfaces:
        if any(marker in lowered for marker in markers):
            return topic_kind, surface
    # Do not let a generic acknowledgement suppress richer pragmatic or
    # learned-response plans.  M28 only takes surface authority when the
    # current literal topic has an explicit bounded grounding row.
    return None, None


def _self_contained_literal_turn_m28(user_input, pragmatic_understanding):
    text = str(user_input or "").strip()
    pragmatic = pragmatic_understanding or {}
    if pragmatic.get("pragmatic_label") != "literal_intent_unresolved":
        return False
    if pragmatic.get("text_visible_hesitation"):
        return False
    if not text or len(_normalise_feedback_token_m28(text)) < 3:
        return False
    if re.search(r"[?？]", text):
        return False
    if classify_explicit_desired_response_m25(text).get("detected"):
        return False
    if _contains(
        text,
        [
            "請",
            "请",
            "幫我",
            "帮我",
            "告訴我",
            "告诉我",
            "can you",
            "could you",
            "please",
            "してほしい",
            "てくれ",
            "じゃなく",
            "actually",
        ],
    ):
        return False
    # Short deictic fragments are not a topic rebase.  They still need the
    # ordinary clarification path because their referent is genuinely absent.
    token = _normalise_feedback_token_m28(text)
    if token in {"那個", "那个", "這個", "这个", "それ", "これ", "あれ", "that", "this", "it"}:
        return False
    return True


def build_feedback_topic_transition_m28(
    user_input,
    adaptive_feedback,
    pragmatic_understanding,
):
    """Separate feedback about the previous reply from current-turn content.

    M27 determines whether an outcome is causally usable for calibration. M28
    consumes that typed result only to keep the visible conversation coherent;
    it never changes the M27 ledger outcome.
    """
    feedback = deepcopy(adaptive_feedback or {})
    pure_act = _pure_feedback_act_m28(user_input)
    previous_prediction_id = feedback.get("previous_prediction_id")
    linked = bool(feedback.get("feedback_linked_to_previous_prediction"))
    contract = {
        "schema": FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28,
        "status": "not_applied",
        "reason": "current_turn_does_not_require_feedback_topic_transition",
        "current_turn_act": "ordinary_current_content",
        "surface_authority": False,
        "expected_surface_jp": None,
        "topic_kind": None,
        "suppresses_new_pending_prediction": False,
        "previous_outcome": {
            "prediction_id": previous_prediction_id,
            "status": feedback.get("status") or "not_available",
            "reason": feedback.get("reason") or "no_previous_outcome",
            "linked": linked,
            "m27_status": (
                (feedback.get("causal_outcome_calibration_m27") or {}).get("status")
                or "not_available"
            ),
        },
        "input_digest": _digest(user_input),
        "m27_outcome_preserved": True,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "typed feedback/current-topic continuity; not proof of private intent"
        ),
    }
    if pure_act == "support" and linked and feedback.get("status") == "supported":
        contract.update(
            {
                "status": "pure_feedback_acknowledgement",
                "reason": "current_turn_only_confirms_previous_response",
                "current_turn_act": "acknowledge_previous_response",
                "surface_authority": True,
                "expected_surface_jp": "ん、分かった。",
                "topic_kind": "previous_response_feedback",
                "suppresses_new_pending_prediction": True,
            }
        )
        return contract
    if (
        previous_prediction_id
        and not linked
        and feedback.get("status") == "uncertain"
        and _self_contained_literal_turn_m28(user_input, pragmatic_understanding)
    ):
        topic_kind, surface = _literal_topic_surface_m28(user_input)
        if topic_kind and surface:
            contract.update(
                {
                    "status": "current_topic_rebase",
                    "reason": "unlinked_self_contained_literal_content_rebases_surface",
                    "current_turn_act": "respond_to_current_literal_topic",
                    "surface_authority": True,
                    "expected_surface_jp": surface,
                    "topic_kind": topic_kind,
                    "suppresses_new_pending_prediction": True,
                }
            )
    return contract


def build_literal_topic_projection_candidate_m29(
    user_input,
    adaptive_feedback,
    pragmatic_understanding,
    feedback_topic_transition_m28=None,
):
    """Authorize a generalized projection attempt without authorizing output."""
    feedback = deepcopy(adaptive_feedback or {})
    m28 = deepcopy(feedback_topic_transition_m28 or {})
    candidate = {
        "schema": LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        "status": "not_candidate",
        "reason": "current_turn_does_not_require_generalized_literal_projection",
        "projection_required": False,
        "surface_authority": False,
        "input_digest": _digest(user_input),
        "previous_prediction_id": feedback.get("previous_prediction_id"),
        "previous_feedback_linked": bool(
            feedback.get("feedback_linked_to_previous_prediction")
        ),
        "m27_status": (
            (feedback.get("causal_outcome_calibration_m27") or {}).get("status")
            or "not_available"
        ),
        "m28_status": m28.get("status") or "not_applied",
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "candidate for literal anchor projection; not yet a valid translation or response"
        ),
    }
    if m28.get("surface_authority"):
        candidate.update(
            {
                "status": "covered_by_bounded_m28_grounding",
                "reason": "m28_already_has_typed_current_topic_surface",
            }
        )
        return candidate
    fresh_session = not feedback.get("previous_prediction_id")
    unlinked_uncertain_previous = bool(
        feedback.get("previous_prediction_id")
        and feedback.get("status") == "uncertain"
        and not feedback.get("feedback_linked_to_previous_prediction")
    )
    if (
        (fresh_session or unlinked_uncertain_previous)
        and _self_contained_literal_turn_m28(user_input, pragmatic_understanding)
    ):
        candidate.update(
            {
                "status": "projection_candidate",
                "reason": (
                    "fresh_self_contained_literal_topic_requires_grounded_projection"
                    if fresh_session
                    else "unlinked_self_contained_literal_topic_requires_grounded_projection"
                ),
                "projection_required": True,
                "candidate_context_m32": (
                    "fresh_session"
                    if fresh_session
                    else "previous_unlinked_unknown"
                ),
            }
        )
    return candidate


def _compositional_explicit_response_matches_m36(text, negated_policies):
    """Compose bounded response-form heads and complements across languages."""

    patterns = {
        "listen_presence": {
            "zh": [
                r"(?:先|只|就)?(?:聽|听)(?:我)?.{0,10}(?:說|说|講|讲|完)",
                r"(?:讓|让)我.{0,8}(?:說|说|講|讲).{0,4}完",
            ],
            "en": [
                r"\blet\s+me\s+(?:finish|talk|say\s+it)\b",
                r"\bhear\s+(?:me|this)\s+out\b",
            ],
            "ja": [r"(?:話|はなし).{0,12}(?:聞いて|きいて)"],
        },
        "share_arousal": {
            "zh": [r"陪我.{0,5}(?:待|一下|一會|一会)"],
            "en": [
                r"\bstay\s+(?:nearby|close|here|with\s+me)\b",
                r"\bkeep\s+me\s+company\b",
            ],
            "ja": [r"(?:そば|ここ|一緒).{0,6}(?:いて|居て)"],
        },
        "solve_regulation": {
            "zh": [
                r"(?:給|给)我.{0,12}(?:步驟|步骤|方法|動作|动作)",
                r"(?:告訴|告诉)我.{0,12}(?:怎麼做|怎么做|先做)",
            ],
            "en": [
                r"\bgive\s+me\s+(?:(?:one|a|the)\s+)?(?:[a-z-]+\s+){0,4}(?:step|method|thing\s+to\s+(?:do|try))\b",
                r"\btell\s+me\s+(?:what|how).{0,24}\bdo\b",
                r"\bwhat\s+should\s+i\s+do\s+first\b",
            ],
            "ja": [
                r"(?:一つ|ひとつ|一個).{0,12}(?:手順|方法|やること).{0,8}(?:教えて|決めて)",
                r"(?:どうすれば|まず何を).{0,12}(?:いい|教えて|すればいい)",
            ],
        },
        "playful_tease": {
            "zh": [r"(?:輕鬆|轻松)?.{0,4}吐槽我.{0,4}(?:一句|一下)?"],
            "en": [r"\bgive\s+me\s+(?:(?:a|one)\s+)?(?:small|light|gentle)?\s*roast\b"],
            "ja": [r"ツッコミ.{0,6}(?:入れて|して)"],
        },
        "calibrate_need": {
            "zh": [r"(?:先問|先问|先確認|先确认).{0,8}(?:我|要什麼|要什么)"],
            "en": [r"\b(?:ask|check|clarify).{0,12}\bfirst\b"],
            "ja": [r"先に.{0,8}(?:聞いて|確認して)"],
        },
    }
    lowered = str(text or "").lower()
    rows = []
    for policy_id, language_groups in patterns.items():
        if policy_id in negated_policies:
            continue
        for language, language_patterns in language_groups.items():
            for pattern_index, pattern in enumerate(language_patterns, start=1):
                for match in re.finditer(pattern, lowered, re.I):
                    rows.append(
                        {
                            "policy_id": policy_id,
                            "mode": POLICY_TO_RESPONSE_MODE_M23[policy_id],
                            "language": language,
                            "cue_id": f"{policy_id}:{language}:m36:{pattern_index}",
                            "position": match.start(),
                            "specificity": len(match.group(0)),
                        }
                    )
    return rows


def classify_explicit_conversation_act_p3_b50(user_input):
    """Detect an explicit request to complain *with* the user.

    A joint complaint is not equivalent to generic companionship and is also
    distinct from teasing the user.  Only an observable current-turn request
    grants authority.  Ordinary negative content and inferred frustration do
    not activate this contract.
    """
    text = str(user_input or "")
    lowered = text.lower()
    negative_patterns = {
        "zh": [
            r"(?:不要|不用|別|别)(?:再)?(?:陪我|跟我|和我|一起)(?:一起)?(?:來|来)?(?:吐槽|抱怨)",
            r"不是(?:要|叫)你(?:陪我|跟我|和我|一起)(?:一起)?(?:來|来)?(?:吐槽|抱怨)",
        ],
        "en": [
            r"\b(?:don['’]?t|do\s+not).{0,24}(?:complain|rant).{0,12}(?:with\s+me|together)\b",
            r"\bnot\s+asking\s+you\s+to.{0,16}(?:complain|rant)\b",
        ],
        "ja": [
            r"一緒に.{0,8}(?:愚痴|文句|ツッコ|ぼや).{0,8}(?:ないで|なくていい)",
            r"(?:愚痴|文句).{0,8}(?:付き合わなくていい|言わないで)",
        ],
    }
    positive_patterns = {
        "zh": [
            r"(?:陪我|跟我|和我)(?:一起)?(?:來|来)?(?:吐槽|抱怨)",
            r"(?:跟|和)我一起(?:來|来)?(?:吐槽|抱怨)",
            r"一起(?:來|来)?(?:吐槽|抱怨)(?:一下)?",
        ],
        "en": [
            r"\b(?:complain|rant)\s+with\s+me\b",
            r"\bjoin\s+me\s+in\s+(?:complaining|ranting)\b",
            r"\blet['’]?s\s+(?:complain|rant)\b",
        ],
        "ja": [
            r"一緒に.{0,8}(?:愚痴って|文句(?:言って|言おう)|ツッコんで|ぼやいて)",
            r"(?:愚痴|文句).{0,8}(?:付き合って|一緒に言って)",
        ],
    }
    negated_languages = {
        language
        for language, patterns in negative_patterns.items()
        if any(re.search(pattern, lowered, re.I) for pattern in patterns)
    }
    matches = []
    for language, patterns in positive_patterns.items():
        if language in negated_languages:
            continue
        for pattern_index, pattern in enumerate(patterns, start=1):
            for match in re.finditer(pattern, lowered, re.I):
                matches.append(
                    {
                        "language": language,
                        "cue_id": f"joint_complaint:{language}:b50:{pattern_index}",
                        "position": match.start(),
                        "specificity": len(match.group(0)),
                    }
                )
    matches.sort(
        key=lambda row: (row["position"], row["specificity"]),
        reverse=True,
    )
    selected = deepcopy(matches[0]) if matches else {}
    protected_risk_cue = _contains(
        lowered,
        [
            "想死", "不想活", "自殺", "自杀",
            "want to die", "kill myself", "end my life",
            "死にたい", "自殺したい", "消えたい",
        ],
    )
    authoritative = bool(selected and not protected_risk_cue)
    return {
        "schema": EXPLICIT_CONVERSATION_ACT_SCHEMA_P3_B50,
        "status": (
            "blocked_by_protected_risk_cue"
            if selected and protected_risk_cue
            else "explicit_joint_complaint_requested"
            if selected
            else "explicit_joint_complaint_negated"
            if negated_languages
            else "not_detected"
        ),
        "detected": bool(selected),
        "act": "joint_complaint" if selected else None,
        "selected_policy": "share_arousal" if selected else None,
        "authority": (
            "current_explicit_conversation_act"
            if authoritative
            else "protected_risk_route"
            if selected and protected_risk_cue
            else "not_applicable"
        ),
        "authoritative": authoritative,
        "negated": bool(negated_languages),
        "negated_languages": sorted(negated_languages),
        "matched_language": selected.get("language"),
        "cue_id": selected.get("cue_id"),
        "match_position": selected.get("position"),
        "surface_required": authoritative,
        "surface_status": "pending" if authoritative else "not_applicable",
        "evidence_digest": _digest(text),
        "claim_boundary": (
            "explicit request to perform a joint complaint only; ordinary "
            "negative content does not authorize the act"
        ),
        "raw_dialogue_persisted": False,
    }


def classify_explicit_desired_response_m25(user_input):
    """Detect an explicitly requested response form across Chinese/English/Japanese.

    This is current-turn communicative evidence, not a stored preference or a
    private-state claim.  The trace records typed cue IDs and a digest only.
    """
    text = str(user_input or "")
    lowered = text.lower()
    explicit_conversation_act_p3_b50 = (
        classify_explicit_conversation_act_p3_b50(text)
    )
    positive = {
        "listen_presence": {
            "zh": ["聽我說", "听我说", "聽我講", "听我讲", "先聽我", "先听我", "只要聽", "只要听"],
            "en": ["listen to me", "just listen", "hear me out", "let me talk"],
            "ja": ["聞いてほしい", "話を聞いて", "まず聞いて", "そのまま聞いて"],
        },
        "share_arousal": {
            "zh": ["陪我一下", "陪著我", "陪着我", "先陪我", "待在這裡陪我", "待在这里陪我"],
            "en": ["stay with me", "keep me company", "be here with me", "sit with me"],
            "ja": ["そばにいて", "一緒にいて", "ここにいて", "付き合ってて"],
        },
        "solve_regulation": {
            "zh": ["給我方法", "给我方法", "告訴我怎麼做", "告诉我怎么做", "現在能做的方法", "现在能做的方法"],
            "en": ["tell me what to do", "give me a method", "give me one step", "what can i do now"],
            "ja": ["方法を教えて", "今できること", "どうすればいいか教えて", "一個だけ決めて"],
        },
        "playful_tease": {
            "zh": ["吐槽我", "虧我一下", "亏我一下", "開我玩笑", "开我玩笑"],
            "en": ["tease me", "roast me", "make fun of me", "give me a joke"],
            "ja": ["ツッコんで", "いじって", "からかって", "軽く煽って"],
        },
        "calibrate_need": {
            "zh": ["先問我", "先问我", "先確認我要什麼", "先确认我要什么"],
            "en": ["ask me first", "clarify with me first", "check what i want first"],
            "ja": ["先に聞いて", "先に確認して", "何がほしいか聞いて"],
        },
    }
    negative = {
        "listen_presence": [
            "不要只聽", "不要只听", "不是只要你聽", "不是只要你听",
            "don't just listen", "do not just listen", "聞くだけじゃなく",
        ],
        "share_arousal": [
            "不用陪我", "不要陪我", "別陪我", "别陪我",
            "don't stay with me", "do not stay with me", "そばにいなくていい", "一緒にいなくていい",
        ],
        "solve_regulation": [
            "不要方法", "不用方法", "不是要方法", "不想要方法", "不要給建議", "不要给建议", "別給建議", "别给建议",
            "no advice", "not asking for a solution", "don't want advice", "do not want advice", "don't give me advice", "do not give me advice", "don't offer advice", "do not offer advice", "解決策はいらない", "方法はいらない", "方法はほしくない", "解決しようとせず",
        ],
        "playful_tease": [
            "不是要吐槽", "不要吐槽", "別吐槽", "别吐槽",
            "don't tease", "do not tease", "not asking for a joke", "ツッコミはいらない", "いじらなくていい",
        ],
        "calibrate_need": [
            "不要問", "不要再問", "别问", "別問", "不用確認", "不用确认",
            "don't ask", "no questions", "do not ask", "質問しないで", "確認しなくていい",
        ],
    }

    negated_policies = {
        policy_id
        for policy_id, markers in negative.items()
        if _contains(lowered, markers)
    }
    matches = []
    for policy_id, language_groups in positive.items():
        if policy_id in negated_policies:
            continue
        for language, markers in language_groups.items():
            for marker_index, marker in enumerate(markers):
                position = lowered.rfind(marker.lower())
                if position < 0:
                    continue
                matches.append(
                    {
                        "policy_id": policy_id,
                        "mode": POLICY_TO_RESPONSE_MODE_M23[policy_id],
                        "language": language,
                        "cue_id": f"{policy_id}:{language}:{marker_index + 1}",
                        "position": position,
                        "specificity": len(marker),
                    }
                )
    matches.extend(
        _compositional_explicit_response_matches_m36(
            lowered,
            negated_policies,
        )
    )
    if explicit_conversation_act_p3_b50.get("detected"):
        matches.append(
            {
                "policy_id": "share_arousal",
                "mode": POLICY_TO_RESPONSE_MODE_M23["share_arousal"],
                "language": explicit_conversation_act_p3_b50.get(
                    "matched_language"
                ),
                "cue_id": explicit_conversation_act_p3_b50.get("cue_id"),
                "position": int(
                    explicit_conversation_act_p3_b50.get("match_position")
                    or 0
                ),
                "specificity": 1000,
            }
        )
    matches.sort(
        key=lambda row: (row["position"], row["specificity"]),
        reverse=True,
    )
    selected = deepcopy(matches[0]) if matches else {}
    protected_risk_cue = _contains(
        lowered,
        [
            "想死", "不想活", "自殺", "自杀",
            "want to die", "kill myself", "end my life",
            "死にたい", "自殺したい", "消えたい",
        ],
    )
    alternatives = []
    seen_policies = set()
    for row in matches:
        policy_id = row["policy_id"]
        if policy_id in seen_policies:
            continue
        seen_policies.add(policy_id)
        alternatives.append(
            {
                "policy_id": policy_id,
                "mode": row["mode"],
                "cue_id": row["cue_id"],
                "language": row["language"],
            }
        )
    mixed = len(alternatives) > 1
    compositional_cue_ids_m36 = [
        row["cue_id"] for row in matches if ":m36:" in str(row.get("cue_id") or "")
    ]
    return {
        "schema": EXPLICIT_DESIRED_RESPONSE_SCHEMA_M25,
        "detected": bool(selected),
        "status": (
            "blocked_by_protected_risk_cue"
            if selected and protected_risk_cue
            else "selected"
            if selected
            else "not_detected"
        ),
        "selected_policy": selected.get("policy_id"),
        "selected_mode": selected.get("mode"),
        "authority": (
            "protected_risk_route"
            if selected and protected_risk_cue
            else "current_explicit_desired_response"
            if selected
            else "not_applicable"
        ),
        "confidence": 0.90 if mixed else 0.99 if selected else 0.0,
        "mixed_unnegated_cues": mixed,
        "alternatives": alternatives,
        "negated_policies": sorted(negated_policies),
        "matched_languages": sorted({row["language"] for row in matches}),
        "compositional_match_count_m36": len(compositional_cue_ids_m36),
        "compositional_cue_ids_m36": compositional_cue_ids_m36[:12],
        "protected_risk_cue": protected_risk_cue,
        "explicit_conversation_act_p3_b50": {
            **explicit_conversation_act_p3_b50,
            "authoritative": bool(
                explicit_conversation_act_p3_b50.get("authoritative")
                and not protected_risk_cue
            ),
            "authority": (
                "protected_risk_route"
                if protected_risk_cue
                and explicit_conversation_act_p3_b50.get("detected")
                else explicit_conversation_act_p3_b50.get("authority")
            ),
        },
        "evidence_digest": _digest(text),
        "claim_boundary": "explicit surface request only; not private-state inference",
        "raw_dialogue_persisted": False,
    }


def _explicit_correction_cues(user_input):
    """Return bounded correction evidence without retaining the utterance."""
    text = str(user_input or "")
    markers = {
        "explicit_misunderstanding": [
            "你誤會",
            "你误会",
            "你理解錯",
            "你理解错",
            "また誤解",
            "勘違いしてる",
            "you misunderstood",
            "you misread",
            "you got it wrong",
            "not what i meant",
        ],
        "exclusive_desired_response": [
            "我只想",
            "只是想",
            "只要你",
            "だけでいい",
            "してほしいだけ",
            "i only want",
            "i just want",
            "all i want",
        ],
        "explicit_rejection": [
            "不是這個意思",
            "不是这个意思",
            "不是要",
            "そうじゃない",
            "no, we are",
            "no, i mean",
        ],
    }
    cue_types = [name for name, values in markers.items() if _contains(text, values)]
    lowered = text.strip().lower()
    if lowered.startswith(("不是，", "不是,", "不是 ")):
        cue_types.append("explicit_rejection")
    cue_types = list(dict.fromkeys(cue_types))
    return {
        "detected": bool(cue_types),
        "cue_types": cue_types,
        "evidence_digest": _digest(text),
        "raw_dialogue_persisted": False,
    }


def _shared_wait_request(user_input):
    return bool(
        _contains(
            user_input,
            [
                "一起等結果",
                "一起等结果",
                "陪我等",
                "結果來之前陪",
                "结果来之前陪",
                "結果を一緒に待",
                "一緒に結果を待",
                "wait for the result with me",
                "waiting for the result with me",
                "stay with me while we wait",
            ],
        )
    )


def _normalise_m27_ledger_entry(payload):
    payload = payload if isinstance(payload, dict) else {}
    result_status = str(payload.get("result_status") or "pending")
    if result_status not in {
        "pending",
        "supported",
        "contradicted",
        "uncertain",
        "not_available",
    }:
        result_status = "uncertain"
    action = str(payload.get("action") or "not_applied")
    if action not in {
        "execute_implicit",
        "abstain_low_pressure_clarification",
        "explicit_authority_bypass",
        "not_applied",
    }:
        action = "not_applied"
    return {
        "schema": CAUSAL_OUTCOME_LEDGER_SCHEMA_M27,
        "prediction_id": str(payload.get("prediction_id") or "")[:80],
        "turn_index": max(0, int(payload.get("turn_index") or 0)),
        "input_digest": str(payload.get("input_digest") or "")[:32],
        "context_scope_id": str(payload.get("context_scope_id") or "")[:80],
        "implicit_top_policy": str(payload.get("implicit_top_policy") or "")[:40],
        "implicit_top_mode": str(payload.get("implicit_top_mode") or "")[:48],
        "performed_policy": str(payload.get("performed_policy") or "")[:40],
        "action": action,
        "top_probability": round(_clip(payload.get("top_probability")), 4),
        "probability_margin": round(_clip(payload.get("probability_margin")), 4),
        "evidence_quality": round(_clip(payload.get("evidence_quality")), 4),
        "result_status": result_status,
        "feedback_linked_to_prediction": bool(
            payload.get("feedback_linked_to_prediction")
        ),
        "feedback_linkage_reason": str(
            payload.get("feedback_linkage_reason") or "pending"
        )[:80],
        "explicit_target_policy": str(
            payload.get("explicit_target_policy") or ""
        )[:40],
        "resolved_turn": (
            max(0, int(payload.get("resolved_turn") or 0))
            if payload.get("resolved_turn") is not None
            else None
        ),
        "feedback_evidence_digest": str(
            payload.get("feedback_evidence_digest") or ""
        )[:32],
        "eligible_for_implicit_calibration": action
        in {"execute_implicit", "abstain_low_pressure_clarification"},
        "raw_dialogue_persisted": False,
    }


def build_causal_outcome_calibration_summary_m27(model):
    """Summarize only causally linked M26 outcomes.

    This is an online descriptive ledger. It never authorizes automatic
    threshold tuning and does not replace a fresh source-disjoint holdout.
    """
    ledger = [
        _normalise_m27_ledger_entry(row)
        for row in ((model or {}).get("outcome_calibration_ledger_m27") or [])[
            -M27_MAX_LEDGER_ENTRIES:
        ]
        if isinstance(row, dict)
    ]
    eligible = [row for row in ledger if row["eligible_for_implicit_calibration"]]
    executed = [row for row in eligible if row["action"] == "execute_implicit"]
    abstained = [
        row
        for row in eligible
        if row["action"] == "abstain_low_pressure_clarification"
    ]
    decisive_executed = [
        row
        for row in executed
        if row["feedback_linked_to_prediction"]
        and row["result_status"] in {"supported", "contradicted"}
    ]
    decisive_abstained = [
        row
        for row in abstained
        if row["feedback_linked_to_prediction"]
        and row["result_status"] in {"supported", "contradicted"}
    ]
    supported_executed = sum(
        row["result_status"] == "supported" for row in decisive_executed
    )
    contradicted_executed = sum(
        row["result_status"] == "contradicted" for row in decisive_executed
    )
    effective_count = len(decisive_executed)
    selective_accuracy = (
        round(supported_executed / effective_count, 4)
        if effective_count
        else None
    )
    selective_risk = (
        round(contradicted_executed / effective_count, 4)
        if effective_count
        else None
    )
    brier_score = None
    if decisive_executed:
        brier_score = round(
            sum(
                (
                    float(row["top_probability"])
                    - (1.0 if row["result_status"] == "supported" else 0.0)
                )
                ** 2
                for row in decisive_executed
            )
            / len(decisive_executed),
            4,
        )
    probability_bins = []
    for low, high in ((0.0, 0.5), (0.5, 0.7), (0.7, 1.0001)):
        rows = [
            row
            for row in decisive_executed
            if low <= float(row["top_probability"]) < high
        ]
        probability_bins.append(
            {
                "lower": low,
                "upper": 1.0 if high > 1.0 else high,
                "sample_count": len(rows),
                "mean_stated_probability": (
                    round(
                        sum(float(row["top_probability"]) for row in rows)
                        / len(rows),
                        4,
                    )
                    if rows
                    else None
                ),
                "observed_support_rate": (
                    round(
                        sum(row["result_status"] == "supported" for row in rows)
                        / len(rows),
                        4,
                    )
                    if rows
                    else None
                ),
            }
        )
    evidence_gate_met = effective_count >= M27_MIN_DECISIVE_EXECUTED_SAMPLES
    return {
        "schema": CAUSAL_OUTCOME_SUMMARY_SCHEMA_M27,
        "status": (
            "descriptive_online_evidence_only"
            if evidence_gate_met
            else "insufficient_evidence"
        ),
        "ledger_entry_count": len(ledger),
        "eligible_implicit_decision_count": len(eligible),
        "executed_implicit_count": len(executed),
        "abstained_count": len(abstained),
        "pending_count": sum(row["result_status"] == "pending" for row in ledger),
        "unknown_or_unlinked_count": sum(
            row["result_status"] in {"uncertain", "not_available"}
            or (
                row["result_status"] in {"supported", "contradicted"}
                and not row["feedback_linked_to_prediction"]
            )
            for row in eligible
        ),
        "effective_decisive_executed_samples": effective_count,
        "minimum_decisive_executed_samples": M27_MIN_DECISIVE_EXECUTED_SAMPLES,
        "supported_executed_count": supported_executed,
        "contradicted_executed_count": contradicted_executed,
        "decisive_abstention_count": len(decisive_abstained),
        "coverage": round(len(executed) / len(eligible), 4) if eligible else 0.0,
        "selective_accuracy": selective_accuracy,
        "selective_risk": selective_risk,
        "brier_score_descriptive": brier_score,
        "probability_bins": probability_bins,
        "minimum_evidence_gate_met": evidence_gate_met,
        "automatic_threshold_tuning_allowed": False,
        "threshold_tuning_status": (
            "eligible_for_offline_review_not_auto_tuning"
            if evidence_gate_met
            else "blocked_insufficient_decisive_evidence"
        ),
        "external_calibration_status": "not_established_without_fresh_holdout",
        "unknown_outcomes_counted_as_success": False,
        "claim_boundary": (
            "privacy-safe online outcome accounting; not external human "
            "calibration and not a probability of private mental state"
        ),
        "raw_dialogue_persisted": False,
    }


def _m27_entry_from_pending_prediction(pending):
    pending = deepcopy(pending or {})
    m26 = deepcopy(pending.get("implicit_response_m26") or {})
    return _normalise_m27_ledger_entry(
        {
            "prediction_id": pending.get("prediction_id"),
            "turn_index": pending.get("turn_index"),
            "input_digest": pending.get("input_digest"),
            "context_scope_id": (pending.get("context_scope") or {}).get("scope_id"),
            "implicit_top_policy": m26.get("implicit_top_policy"),
            "implicit_top_mode": m26.get("implicit_top_mode"),
            "performed_policy": pending.get("policy_id"),
            "action": m26.get("status"),
            "top_probability": m26.get("top_probability"),
            "probability_margin": m26.get("probability_margin"),
            "evidence_quality": m26.get("evidence_quality"),
            "result_status": "pending",
            "feedback_linkage_reason": "pending_next_turn_outcome",
            "raw_dialogue_persisted": False,
        }
    )


def _upsert_m27_pending_prediction(model, pending):
    state = model
    entry = _m27_entry_from_pending_prediction(pending)
    prediction_id = entry.get("prediction_id")
    if not prediction_id:
        state["outcome_calibration_summary_m27"] = (
            build_causal_outcome_calibration_summary_m27(state)
        )
        return state
    ledger = [
        _normalise_m27_ledger_entry(row)
        for row in (state.get("outcome_calibration_ledger_m27") or [])
        if isinstance(row, dict)
    ]
    replaced = False
    for index in range(len(ledger) - 1, -1, -1):
        if ledger[index].get("prediction_id") == prediction_id:
            ledger[index] = entry
            replaced = True
            break
    if not replaced:
        ledger.append(entry)
    state["outcome_calibration_ledger_m27"] = ledger[-M27_MAX_LEDGER_ENTRIES:]
    state["outcome_calibration_summary_m27"] = (
        build_causal_outcome_calibration_summary_m27(state)
    )
    return state


def _resolve_m27_outcome(model, pending, feedback, turn_index=0):
    state = model
    pending = deepcopy(pending or {})
    feedback = deepcopy(feedback or {})
    prediction_id = str(pending.get("prediction_id") or "")
    if not prediction_id:
        summary = build_causal_outcome_calibration_summary_m27(state)
        state["outcome_calibration_summary_m27"] = summary
        return state, {
            "schema": CAUSAL_OUTCOME_LEDGER_SCHEMA_M27,
            "status": "not_available",
            "reason": "no_pending_prediction_to_resolve",
            "summary": summary,
            "raw_dialogue_persisted": False,
        }
    ledger = [
        _normalise_m27_ledger_entry(row)
        for row in (state.get("outcome_calibration_ledger_m27") or [])
        if isinstance(row, dict)
    ]
    matching_index = next(
        (
            index
            for index in range(len(ledger) - 1, -1, -1)
            if ledger[index].get("prediction_id") == prediction_id
        ),
        None,
    )
    if matching_index is None:
        ledger.append(_m27_entry_from_pending_prediction(pending))
        matching_index = len(ledger) - 1
    row = deepcopy(ledger[matching_index])
    linked = bool(feedback.get("feedback_linked_to_previous_prediction"))
    feedback_status = str(feedback.get("status") or "uncertain")
    decisive = linked and feedback_status in {"supported", "contradicted"}
    row.update(
        {
            "result_status": feedback_status if decisive else "uncertain",
            "feedback_linked_to_prediction": linked,
            "feedback_linkage_reason": feedback.get("feedback_linkage_reason")
            or "unresolved",
            "explicit_target_policy": feedback.get("explicit_target_policy"),
            "resolved_turn": int(turn_index),
            "feedback_evidence_digest": (
                (feedback.get("evidence") or {}).get("digest") or ""
            ),
            "raw_dialogue_persisted": False,
        }
    )
    ledger[matching_index] = _normalise_m27_ledger_entry(row)
    state["outcome_calibration_ledger_m27"] = ledger[-M27_MAX_LEDGER_ENTRIES:]
    summary = build_causal_outcome_calibration_summary_m27(state)
    state["outcome_calibration_summary_m27"] = summary
    return state, {
        "schema": CAUSAL_OUTCOME_LEDGER_SCHEMA_M27,
        "status": "resolved_decisive" if decisive else "resolved_unknown_excluded",
        "reason": (
            "causally_linked_support_or_contradiction_counted"
            if decisive
            else "unknown_or_unlinked_outcome_excluded_from_success"
        ),
        "prediction_id": prediction_id,
        "action": row.get("action"),
        "result_status": row.get("result_status"),
        "feedback_linked_to_prediction": linked,
        "effective_decisive_executed_samples": summary.get(
            "effective_decisive_executed_samples"
        ),
        "minimum_evidence_gate_met": summary.get("minimum_evidence_gate_met"),
        "automatic_threshold_tuning_allowed": False,
        "summary": summary,
        "raw_dialogue_persisted": False,
    }


def empty_model():
    return {
        "schema": MODEL_SCHEMA,
        "version": STORE_VERSION,
        "claim_scope": "operational_desired_response_model_not_private_mind",
        "memory_boundary": "separate_from_factual_and_episodic_memory",
        "raw_dialogue_persisted": False,
        "policy_reliability": {
            policy_id: {
                "alpha": 1,
                "beta": 1,
                "supported": 0,
                "contradicted": 0,
                "uncertain": 0,
                "mean": 0.5,
            }
            for policy_id in POLICIES
        },
        "learned_atoms": {},
        "scoped_atoms": {},
        "scoped_policy_reliability": {},
        "trigger_policy_relations_m37": [],
        "legacy_unscoped_atom_count": 0,
        "pending_prediction": None,
        "outcome_calibration_ledger_m27": [],
        "outcome_calibration_summary_m27": {
            "schema": CAUSAL_OUTCOME_SUMMARY_SCHEMA_M27,
            "status": "insufficient_evidence",
            "effective_decisive_executed_samples": 0,
            "minimum_decisive_executed_samples": M27_MIN_DECISIVE_EXECUTED_SAMPLES,
            "automatic_threshold_tuning_allowed": False,
            "raw_dialogue_persisted": False,
        },
        "revision_history": [],
        "revision_count": 0,
        "last_turn": 0,
    }


def _normalise_model(payload):
    state = empty_model()
    if not isinstance(payload, dict) or payload.get("schema") not in {
        MODEL_SCHEMA,
        M17_MODEL_SCHEMA,
        LEGACY_MODEL_SCHEMA,
    }:
        return state
    state["revision_count"] = max(0, int(payload.get("revision_count") or 0))
    state["last_turn"] = max(0, int(payload.get("last_turn") or 0))
    pending = payload.get("pending_prediction")
    if isinstance(pending, dict):
        state["pending_prediction"] = {
            "prediction_id": str(pending.get("prediction_id") or "")[:80],
            "policy_id": str(pending.get("policy_id") or "")[:40],
            "expected_utility": _clip(pending.get("expected_utility")),
            "utility_margin": max(-1.0, min(1.0, float(pending.get("utility_margin") or 0.0))),
            "turn_index": max(0, int(pending.get("turn_index") or 0)),
            "input_digest": str(pending.get("input_digest") or "")[:32],
            "context_scope": _normalise_scope(pending.get("context_scope")),
            "causal_scope_ids": [
                str(scope_id)[:180]
                for scope_id in (pending.get("causal_scope_ids") or [])
                if str(scope_id).strip()
            ][:8],
            "response_dimensions": _strip_raw_fields(
                pending.get("response_dimensions") or {}
            ),
            "realization": _strip_raw_fields(pending.get("realization") or {}),
            "implicit_response_m26": {
                "status": str(
                    (pending.get("implicit_response_m26") or {}).get("status")
                    or "not_applied"
                )[:48],
                "implicit_top_policy": str(
                    (pending.get("implicit_response_m26") or {}).get(
                        "implicit_top_policy"
                    )
                    or ""
                )[:40],
                "implicit_top_mode": str(
                    (pending.get("implicit_response_m26") or {}).get(
                        "implicit_top_mode"
                    )
                    or ""
                )[:48],
                "top_probability": round(
                    _clip(
                        (pending.get("implicit_response_m26") or {}).get(
                            "top_probability"
                        )
                    ),
                    4,
                ),
                "probability_margin": round(
                    _clip(
                        (pending.get("implicit_response_m26") or {}).get(
                            "probability_margin"
                        )
                    ),
                    4,
                ),
                "evidence_quality": round(
                    _clip(
                        (pending.get("implicit_response_m26") or {}).get(
                            "evidence_quality"
                        )
                    ),
                    4,
                ),
                "raw_dialogue_persisted": False,
            },
            "trigger_relation_candidate_m37": (
                _normalise_trigger_relation_candidate_m37(
                    pending.get("trigger_relation_candidate_m37") or {}
                )
            ),
            "raw_dialogue_persisted": False,
        }
    else:
        state["pending_prediction"] = None
    state["outcome_calibration_ledger_m27"] = [
        _normalise_m27_ledger_entry(row)
        for row in (payload.get("outcome_calibration_ledger_m27") or [])[
            -M27_MAX_LEDGER_ENTRIES:
        ]
        if isinstance(row, dict)
    ]
    state["outcome_calibration_summary_m27"] = (
        build_causal_outcome_calibration_summary_m27(state)
    )
    for policy_id in POLICIES:
        incoming = ((payload.get("policy_reliability") or {}).get(policy_id) or {})
        row = state["policy_reliability"][policy_id]
        for key in ("supported", "contradicted", "uncertain"):
            row[key] = max(0, int(incoming.get(key) or 0))
        row["alpha"] = max(1, int(incoming.get("alpha") or (1 + row["supported"])))
        row["beta"] = max(1, int(incoming.get("beta") or (1 + row["contradicted"])))
        row["mean"] = round(row["alpha"] / (row["alpha"] + row["beta"]), 4)
    for atom, incoming in (payload.get("learned_atoms") or {}).items():
        if atom not in PERSISTABLE_ATOMS or not isinstance(incoming, dict):
            continue
        state["learned_atoms"][atom] = {
            "value": _clip(incoming.get("value")),
            "confidence": _clip(incoming.get("confidence")),
            "source_kind": str(incoming.get("source_kind") or "explicit_feedback"),
            "evidence_digest": str(incoming.get("evidence_digest") or "")[:32],
            "updated_turn": max(0, int(incoming.get("updated_turn") or 0)),
            "contradiction_count": max(0, int(incoming.get("contradiction_count") or 0)),
        }
    state["legacy_unscoped_atom_count"] = (
        len(state["learned_atoms"])
        if payload.get("schema") == LEGACY_MODEL_SCHEMA
        else max(0, int(payload.get("legacy_unscoped_atom_count") or 0))
    )
    for scope_id, incoming_scope in (payload.get("scoped_atoms") or {}).items():
        if not isinstance(incoming_scope, dict):
            continue
        scope = _normalise_scope(incoming_scope.get("scope"), scope_id=scope_id)
        atoms = {}
        for atom, incoming in (incoming_scope.get("atoms") or {}).items():
            if atom not in PERSISTABLE_ATOMS or not isinstance(incoming, dict):
                continue
            atoms[atom] = {
                "value": _clip(incoming.get("value")),
                "confidence": _clip(incoming.get("confidence")),
                "source_kind": str(incoming.get("source_kind") or "explicit_feedback")[:80],
                "evidence_digest": str(incoming.get("evidence_digest") or "")[:32],
                "updated_turn": max(0, int(incoming.get("updated_turn") or 0)),
                "updated_revision": max(0, int(incoming.get("updated_revision") or 0)),
                "contradiction_count": max(0, int(incoming.get("contradiction_count") or 0)),
            }
        dimensions = {}
        for dimension, incoming in (incoming_scope.get("dimensions") or {}).items():
            if dimension not in RESPONSE_DIMENSIONS or not isinstance(incoming, dict):
                continue
            dimensions[dimension] = {
                "value": _clip(incoming.get("value")),
                "confidence": _clip(incoming.get("confidence")),
                "source_kind": str(incoming.get("source_kind") or "explicit_feedback")[:80],
                "evidence_digest": str(incoming.get("evidence_digest") or "")[:32],
                "updated_turn": max(0, int(incoming.get("updated_turn") or 0)),
                "updated_revision": max(0, int(incoming.get("updated_revision") or 0)),
                "contradiction_count": max(0, int(incoming.get("contradiction_count") or 0)),
            }
        if atoms or dimensions:
            state["scoped_atoms"][scope["scope_id"]] = {
                "scope": scope,
                "atoms": atoms,
                "dimensions": dimensions,
                "last_updated_revision": max(
                    0, int(incoming_scope.get("last_updated_revision") or 0)
                ),
                "ttl_revisions": max(
                    1,
                    min(
                        500,
                        int(
                            incoming_scope.get("ttl_revisions")
                            or DEFAULT_SCOPE_TTL_REVISIONS
                        ),
                    ),
                ),
            }
    for scope_id, incoming_scope in (payload.get("scoped_policy_reliability") or {}).items():
        if not isinstance(incoming_scope, dict):
            continue
        normalized_scope = {}
        for policy_id in POLICIES:
            incoming = incoming_scope.get(policy_id) or {}
            if not isinstance(incoming, dict):
                incoming = {}
            supported = max(0, int(incoming.get("supported") or 0))
            contradicted = max(0, int(incoming.get("contradicted") or 0))
            alpha = max(1, int(incoming.get("alpha") or (1 + supported)))
            beta = max(1, int(incoming.get("beta") or (1 + contradicted)))
            normalized_scope[policy_id] = {
                "alpha": alpha,
                "beta": beta,
                "supported": supported,
                "contradicted": contradicted,
                "uncertain": max(0, int(incoming.get("uncertain") or 0)),
                "mean": round(alpha / (alpha + beta), 4),
            }
        state["scoped_policy_reliability"][str(scope_id)[:80]] = normalized_scope
    state["trigger_policy_relations_m37"] = [
        relation
        for relation in (
            _normalise_verified_trigger_relation_m37(row)
            for row in (payload.get("trigger_policy_relations_m37") or [])[-48:]
            if isinstance(row, dict)
        )
        if relation.get("relation_id")
        and relation.get("trigger_predicate") in _M37_TRIGGER_PATTERN_FAMILIES
        and relation.get("response_policy") in POLICIES
    ]
    state["revision_history"] = [
        _strip_raw_fields(row)
        for row in (payload.get("revision_history") or [])[-40:]
        if isinstance(row, dict)
    ]
    return state


def _scope_from_id(scope_id):
    parts = str(scope_id or "").split(":", 2)
    return _normalise_scope(
        {
            "domain": parts[0] if parts and parts[0] else "general_conversation",
            "interaction_kind": parts[1] if len(parts) > 1 else "ordinary_exchange",
            "relationship_band": parts[2] if len(parts) > 2 else "unspecified",
        },
        scope_id=scope_id,
    )


def _normalise_scope(payload, scope_id=None):
    payload = payload if isinstance(payload, dict) else {}
    domain = str(payload.get("domain") or "general_conversation")[:48]
    interaction_kind = str(payload.get("interaction_kind") or "ordinary_exchange")[:48]
    relationship_band = str(payload.get("relationship_band") or "unspecified")[:32]
    resolved_id = str(scope_id or payload.get("scope_id") or "")[:80]
    if not resolved_id:
        resolved_id = f"{domain}:{interaction_kind}:{relationship_band}"
    return {
        "schema": SCOPE_SCHEMA,
        "scope_id": resolved_id,
        "domain": domain,
        "interaction_kind": interaction_kind,
        "relationship_band": relationship_band,
        "confidence": _clip(payload.get("confidence", 0.5)),
        "evidence_tags": [
            str(item)[:48] for item in (payload.get("evidence_tags") or [])[:8]
        ],
        "raw_dialogue_persisted": False,
    }


def _has_compositional_arousal_cue_m36(user_input):
    text = str(user_input or "").lower()
    patterns = (
        r"(?:想法|思緒|思绪|腦中|脑中).{0,24}(?:停不住|停不下|亂跑|乱跑|一直在跑|一個接一個|一个接一个)",
        r"\b(?:thoughts?|ideas?|mind).{0,48}(?:racing|bouncing|circling|won't\s+stop|will\s+not\s+stop)\b",
        r"頭が.{0,16}(?:止ま(?:らない|んない|ってくれない)|回りっぱなし|休まらない)",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def infer_context_scope(user_input, pragmatic_understanding=None, hypothesis=None):
    """Map visible cues to a bounded categorical reuse scope, never raw text."""
    text = str(user_input or "")
    pragmatic_label = str((pragmatic_understanding or {}).get("pragmatic_label") or "")
    features = set((hypothesis or {}).get("semantic_features") or [])
    assignments = _explicit_atom_assignments(text)
    tags = []

    if assignments.get("sleep_debt") or assignments.get("physical_strain"):
        domain = "physical_wellbeing"
        interaction_kind = "state_disclosure"
        confidence = 0.94
        tags.append("explicit_body_or_sleep_cue_precedes_style_transfer")
    elif (
        pragmatic_label == "ambiguous_arousal"
        or _has_compositional_arousal_cue_m36(text)
        or _contains(
            text,
            [
                "坐不住",
                "停不下來",
                "停不下来",
                "轉個不停",
                "转个不停",
                "頭停ま",
                "頭が止ま",
                "mind won't stop",
                "thoughts keep racing",
                "racing thoughts",
                "can't sit still",
            ],
        )
    ):
        domain = "arousal_regulation"
        interaction_kind = "state_disclosure"
        confidence = 0.90
        tags.append("ambiguous_or_explicit_arousal")
    elif assignments.get("task_pressure") or _contains(
        text,
        ["進度", "进度", "專案", "项目", "project", "presentation", "作業", "報告", "deadline"],
    ):
        domain = "task_execution"
        interaction_kind = "problem_solving"
        confidence = 0.88
        tags.append("task_execution_cue")
    elif assignments.get("positive_arousal") or pragmatic_label == "explicit_positive_arousal":
        domain = "positive_anticipation"
        interaction_kind = "state_disclosure"
        confidence = 0.88
        tags.append("positive_arousal_cue")
    elif assignments.get("listening_request") or assignments.get("companionship_request") or pragmatic_label == "possible_indirect_support_request":
        domain = "emotional_support"
        interaction_kind = "emotional_bid"
        confidence = 0.82
        tags.append("support_or_presence_cue")
    elif assignments.get("humor_invitation"):
        domain = "relationship_play"
        interaction_kind = "play_invitation"
        confidence = 0.86
        tags.append("explicit_humor_invitation")
    else:
        domain = "general_conversation"
        interaction_kind = "ordinary_exchange"
        confidence = 0.48
        tags.append("no_specific_context_cue")

    # Interaction kind is deliberately separated from topic/domain.  This is
    # what lets M18 distinguish an arousal disclosure from a request for a
    # concrete step while still permitting an audited same-domain fallback.
    if assignments.get("humor_invitation"):
        interaction_kind = "play_invitation"
    elif assignments.get("solution_request"):
        interaction_kind = "problem_solving"
    elif assignments.get("listening_request") or assignments.get("companionship_request"):
        interaction_kind = "emotional_bid"

    familiar_cue = bool(
        assignments.get("humor_invitation")
        or _contains(
            text,
            [
                "平常",
                "平時",
                "平时",
                "像以前",
                "又來了",
                "又来了",
                "いつもみたい",
                "いつもの",
                "またか",
                "as usual",
                "like usual",
                "you know me",
                "we usually",
            ],
        )
    )
    distant_cue = _contains(
        text,
        ["第一次聊", "不太熟", "初めて話", "まだよく知らない", "first time talking"],
    )
    relationship_band = "familiar" if familiar_cue else "distant" if distant_cue else "unspecified"
    if "support_request" in features and domain == "general_conversation":
        domain = "emotional_support"
        interaction_kind = "emotional_bid"
        confidence = max(confidence, 0.66)
        tags.append("hypothesis_support_feature")
    return _normalise_scope(
        {
            "domain": domain,
            "interaction_kind": interaction_kind,
            "relationship_band": relationship_band,
            "confidence": confidence,
            "evidence_tags": tags,
        }
    )


def _empty_policy_reliability():
    return {
        policy_id: {
            "alpha": 1,
            "beta": 1,
            "supported": 0,
            "contradicted": 0,
            "uncertain": 0,
            "mean": 0.5,
        }
        for policy_id in POLICIES
    }


def _strip_raw_fields(payload):
    """Defence in depth: a persisted model may not contain dialogue strings."""
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            key_text = str(key)
            if key_text.lower() in {
                "text",
                "raw_text",
                "feedback",
                "user_input",
                "current_input",
                "observed",
                "literal_content",
            }:
                continue
            cleaned[key_text] = _strip_raw_fields(value)
        return cleaned
    if isinstance(payload, list):
        return [_strip_raw_fields(item) for item in payload]
    return deepcopy(payload)


def load_model(path):
    target = Path(path)
    if not target.exists():
        return empty_model(), {"status": "new", "path": str(target)}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return _normalise_model(payload), {"status": "loaded", "path": str(target)}
    except Exception as exc:
        return empty_model(), {
            "status": "invalid_store_reset_in_memory",
            "path": str(target),
            "error_type": type(exc).__name__,
        }


def save_model(path, model):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _normalise_model(model)
    fd, tmp_path = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return {"status": "saved", "path": str(target), "revision_count": payload["revision_count"]}


def _set_atom(atoms, key, value, confidence, status, evidence_kind):
    atoms[key] = {
        "value": _clip(value),
        "confidence": _clip(confidence),
        "status": status,
        "evidence": evidence_kind,
    }


def _explicit_atom_assignments(user_input):
    text = str(user_input or "")
    assignments = {}
    explicit_request_m25 = classify_explicit_desired_response_m25(text)
    if explicit_request_m25.get("protected_risk_cue"):
        return assignments

    negative_solution = _contains(
        text,
        ["不要方法", "不用方法", "不是要方法", "別給建議", "别给建议", "解決策はいらない", "no advice", "not asking for a solution"],
    )
    negative_humor = _contains(
        text,
        [
            "不是要吐槽",
            "不要吐槽",
            "別吐槽",
            "别吐槽",
            "いじらなくていい",
            "ツッコミはいらない",
            "don't tease",
            "do not tease",
            "not asking for a joke",
        ],
    )
    humor = _contains(
        text,
        ["吐槽", "開玩笑", "开玩笑", "いじって", "ツッコ", "tease me", "joke"],
    ) and not negative_humor
    listen = _contains(
        text,
        [
            "只想有人聽",
            "只想有人听",
            "聽我說",
            "听我说",
            "先聽我講",
            "先听我讲",
            "聞いてほしい",
            "listen to me",
            "just listen",
            "hear me out",
        ],
    )
    solution = _contains(
        text,
        [
            "有沒有辦法",
            "有没有办法",
            "怎麼辦",
            "怎么办",
            "怎麼停",
            "怎么停",
            "該先做什麼",
            "该先做什么",
            "方法",
            "どうすれば",
            "止め方",
            "what can i do",
            "what should i do first",
            "how do i stop",
        ],
    ) and not negative_solution
    positive = _contains(text, ["不是緊張", "不是紧张", "興奮", "兴奋", "期待", "楽しみ", "excited", "looking forward"])
    sleep = _contains(text, ["沒有睡", "没有睡", "沒睡", "没睡", "徹夜", "寝てない", "眠ってない", "didn't sleep", "no sleep"])
    physical = _contains(text, ["不舒服", "頭痛", "头痛", "胸悶", "胸闷", "しんど", "具合悪", "physically unwell", "headache"])
    companionship = _contains(text, ["陪我", "一起", "有人陪", "そばにいて", "一緒に", "stay with me", "with me"])
    shared_wait = _shared_wait_request(text)
    task = _contains(text, ["工作", "作業", "報告", "报告", "截止", "締切", "deadline", "finish this"])

    if humor:
        assignments.update(
            {
                "humor_invitation": (0.98, 0.99, "explicit_user_feedback"),
                "relationship_familiarity": (0.90, 0.90, "bounded_from_humor_invitation"),
                "solution_request": (0.04, 0.94, "explicit_user_feedback"),
                "uncertainty": (0.06, 0.96, "derived_after_explicit_feedback"),
            }
        )
    if negative_humor:
        assignments["humor_invitation"] = (0.03, 0.98, "explicit_user_feedback")
    if negative_solution:
        assignments["solution_request"] = (0.03, 0.98, "explicit_user_feedback")
    if listen:
        assignments.update(
            {
                "listening_request": (0.98, 0.99, "explicit_user_feedback"),
                "companionship_request": (0.86, 0.90, "bounded_from_listening_request"),
                "solution_request": (0.03, 0.98, "explicit_user_feedback"),
                "uncertainty": (0.05, 0.96, "derived_after_explicit_feedback"),
            }
        )
    if solution:
        assignments.update(
            {
                "solution_request": (0.98, 0.99, "explicit_user_request"),
                "uncertainty": (0.06, 0.95, "derived_after_explicit_request"),
            }
        )
    if positive:
        assignments.update(
            {
                "positive_arousal": (0.97, 0.98, "explicit_user_report"),
                "uncertainty": (0.08, 0.94, "derived_after_explicit_report"),
            }
        )
    if sleep:
        assignments["sleep_debt"] = (0.98, 0.99, "explicit_user_report")
    if physical:
        assignments["physical_strain"] = (0.92, 0.96, "explicit_user_report")
    if companionship:
        assignments.update(
            {
                "companionship_request": (0.94, 0.94, "explicit_user_request"),
                "uncertainty": (0.05, 0.96, "derived_after_explicit_request"),
            }
        )
    if shared_wait:
        assignments.update(
            {
                "companionship_request": (0.99, 0.99, "explicit_shared_wait_request"),
                "positive_arousal": (0.78, 0.86, "bounded_visible_anticipation"),
                "uncertainty": (0.05, 0.98, "explicit_desired_response_resolves_ambiguity"),
            }
        )
    if task:
        assignments["task_pressure"] = (0.88, 0.84, "visible_task_cue")
    m25_policy = (
        str(explicit_request_m25.get("selected_policy") or "")
        if explicit_request_m25.get("authority")
        == "current_explicit_desired_response"
        else ""
    )
    if m25_policy == "listen_presence":
        assignments.update(
            {
                "listening_request": (0.99, 0.99, "m25_current_explicit_request"),
                "solution_request": (0.03, 0.98, "m25_current_explicit_request"),
                "uncertainty": (0.04, 0.98, "m25_current_explicit_request"),
            }
        )
    elif m25_policy == "share_arousal":
        assignments.update(
            {
                "companionship_request": (0.99, 0.99, "m25_current_explicit_request"),
                "uncertainty": (0.04, 0.98, "m25_current_explicit_request"),
            }
        )
    elif m25_policy == "solve_regulation":
        assignments.update(
            {
                "solution_request": (0.99, 0.99, "m25_current_explicit_request"),
                "uncertainty": (0.04, 0.98, "m25_current_explicit_request"),
            }
        )
    elif m25_policy == "playful_tease":
        assignments.update(
            {
                "humor_invitation": (0.99, 0.99, "m25_current_explicit_request"),
                "relationship_familiarity": (0.90, 0.90, "m25_bounded_humor_context"),
                "uncertainty": (0.04, 0.98, "m25_current_explicit_request"),
            }
        )
    elif m25_policy == "calibrate_need":
        assignments["uncertainty"] = (0.90, 0.98, "m25_current_explicit_request")
    return assignments


def _explicit_target_policy(user_input):
    explicit_request_m25 = classify_explicit_desired_response_m25(user_input)
    if explicit_request_m25.get("protected_risk_cue"):
        return None
    if explicit_request_m25.get("authority") == "current_explicit_desired_response":
        return explicit_request_m25.get("selected_policy")
    assignments = _explicit_atom_assignments(user_input)
    if _shared_wait_request(user_input):
        return "share_arousal"
    if assignments.get("humor_invitation", (0,))[0] >= 0.9:
        return "playful_tease"
    if assignments.get("listening_request", (0,))[0] >= 0.9:
        return "listen_presence"
    if assignments.get("solution_request", (0,))[0] >= 0.9:
        return "solve_regulation"
    if assignments.get("positive_arousal", (0,))[0] >= 0.9:
        return "share_arousal"
    if assignments.get("sleep_debt", (0,))[0] >= 0.9 or assignments.get("physical_strain", (0,))[0] >= 0.9:
        return "care_physiology"
    if assignments.get("companionship_request", (0,))[0] >= 0.9:
        return "share_arousal"
    return None


def _dimension_targets_for_policy(policy_id):
    return {
        key: _clip(value)
        for key, value in (POLICY_DIMENSION_PROFILES.get(policy_id) or {}).items()
        if key in RESPONSE_DIMENSIONS
    }


def _feedback_dimension_targets(selected_policy, explicit_target, status):
    """Return only dimensions supported by linked response feedback.

    Generic support verifies the selected vector.  A correction verifies the
    explicitly requested vector instead.  Generic rejection without a target
    is intentionally not converted into a guessed replacement preference.
    """
    if explicit_target:
        return _dimension_targets_for_policy(explicit_target)
    if status == "supported" and selected_policy:
        return _dimension_targets_for_policy(selected_policy)
    return {}


def _supported_explicit_response_atom_assignments(pending, status):
    """Persist only the reversible response form that the user just verified.

    This does not infer a private emotion or need.  It turns an explicitly
    requested and subsequently supported interaction policy into the same
    typed, scoped preference atoms already used by M18/M26.
    """
    if status != "supported":
        return {}
    implicit = (pending or {}).get("implicit_response_m26") or {}
    if implicit.get("status") != "explicit_authority_bypass":
        return {}
    policy_id = str((pending or {}).get("policy_id") or "")
    if policy_id == "playful_tease":
        return {
            "humor_invitation": (0.96, 0.92, "supported_explicit_response_form"),
            "relationship_familiarity": (0.84, 0.78, "bounded_humor_interaction_context"),
        }
    if policy_id == "solve_regulation":
        return {
            "solution_request": (0.96, 0.92, "supported_explicit_response_form")
        }
    if policy_id == "listen_presence":
        return {
            "listening_request": (0.96, 0.92, "supported_explicit_response_form"),
            "solution_request": (0.04, 0.90, "supported_explicit_response_form"),
        }
    if policy_id == "share_arousal":
        return {
            "companionship_request": (0.96, 0.92, "supported_explicit_response_form")
        }
    return {}


def _update_verified_trigger_relation_m37(
    state,
    pending,
    status,
    feedback_digest,
    turn_index,
    revision_index,
):
    candidate = _normalise_trigger_relation_candidate_m37(
        (pending or {}).get("trigger_relation_candidate_m37") or {}
    )
    policy_id = str((pending or {}).get("policy_id") or "")
    base = {
        "schema": TRIGGER_RELATION_UPDATE_SCHEMA_M37,
        "status": "not_applicable",
        "reason": "no_ready_trigger_relation_candidate",
        "relation_id": candidate.get("relation_id"),
        "trigger_predicate": candidate.get("trigger_predicate"),
        "response_policy": candidate.get("response_policy"),
        "previous_outcome": status,
        "persisted_relation_count": len(
            state.get("trigger_policy_relations_m37") or []
        ),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }
    if candidate.get("status") != "candidate_ready":
        return state, base
    if candidate.get("response_policy") != policy_id:
        base.update(
            {
                "status": "rejected_policy_mismatch",
                "reason": "candidate_policy_differs_from_executed_prediction",
            }
        )
        return state, base
    if status != "supported":
        base.update(
            {
                "status": "candidate_not_verified",
                "reason": (
                    "seed_response_prediction_was_contradicted"
                    if status == "contradicted"
                    else "seed_response_prediction_not_decisively_supported"
                ),
            }
        )
        return state, base

    relation_id = str(candidate.get("relation_id") or "")
    predicate = str(candidate.get("trigger_predicate") or "")
    relations = [
        _normalise_verified_trigger_relation_m37(row)
        for row in (state.get("trigger_policy_relations_m37") or [])
        if isinstance(row, dict)
    ]
    superseded_ids = []
    existing = None
    for relation in relations:
        if relation.get("relation_id") == relation_id:
            existing = relation
        elif relation.get("active") and relation.get("trigger_predicate") == predicate:
            relation["active"] = False
            relation["status"] = "superseded"
            relation["updated_turn"] = int(turn_index)
            relation["updated_revision"] = int(revision_index)
            superseded_ids.append(relation.get("relation_id"))
    if existing is None:
        existing = _normalise_verified_trigger_relation_m37(
            {
                "relation_id": relation_id,
                "trigger_predicate": predicate,
                "response_policy": policy_id,
                "status": "verified",
                "active": True,
                "confidence": 0.90,
                "source_kind": "verified_future_response_relation",
                "source_digest": candidate.get("source_digest"),
                "created_turn": int((pending or {}).get("turn_index") or 0),
                "updated_turn": int(turn_index),
                "updated_revision": int(revision_index),
                "ttl_revisions": M37_TRIGGER_RELATION_TTL_REVISIONS,
                "verification_history": {},
            }
        )
        relations.append(existing)
    history = existing.setdefault("verification_history", {})
    history["supported"] = int(history.get("supported") or 0) + 1
    history["last_feedback_digest"] = str(feedback_digest or "")[:32]
    existing.update(
        {
            "status": "verified",
            "active": True,
            "confidence": round(
                min(0.99, 0.90 + 0.02 * int(history.get("supported") or 0)),
                4,
            ),
            "updated_turn": int(turn_index),
            "updated_revision": int(revision_index),
            "raw_dialogue_persisted": False,
            "private_state_truth_claimed": False,
        }
    )
    state["trigger_policy_relations_m37"] = relations[-48:]
    base.update(
        {
            "status": "verified_relation_persisted",
            "reason": "explicit_future_response_relation_supported_next_turn",
            "confidence": existing.get("confidence"),
            "superseded_relation_ids": superseded_ids,
            "persisted_relation_count": len(relations),
        }
    )
    return state, base


def observe_next_turn(model, user_input, turn_index=0):
    """Verify the pending response-policy prediction using only decisive cues."""
    state = _normalise_model(model)
    pending = deepcopy(state.get("pending_prediction") or {})
    if not pending:
        summary_m27 = build_causal_outcome_calibration_summary_m27(state)
        state["outcome_calibration_summary_m27"] = summary_m27
        return state, {
            "schema": FEEDBACK_SCHEMA,
            "status": "not_available",
            "reason": "no_previous_desired_response_prediction",
            "turn_index": int(turn_index),
            "changed_policy": None,
            "atom_changes": [],
            "trigger_relation_update_m37": {
                "schema": TRIGGER_RELATION_UPDATE_SCHEMA_M37,
                "status": "not_available",
                "reason": "no_pending_prediction_to_resolve",
                "raw_dialogue_persisted": False,
            },
            "causal_outcome_calibration_m27": {
                "schema": CAUSAL_OUTCOME_LEDGER_SCHEMA_M27,
                "status": "not_available",
                "reason": "no_pending_prediction_to_resolve",
                "summary": summary_m27,
                "automatic_threshold_tuning_allowed": False,
                "raw_dialogue_persisted": False,
            },
        }

    selected_policy = str(pending.get("policy_id") or "")
    pending_scope = _normalise_scope(pending.get("context_scope"))
    scope_id = pending_scope["scope_id"]
    causal_scope_ids = list(
        dict.fromkeys(
            [
                scope_id,
                *[
                    str(value)
                    for value in (pending.get("causal_scope_ids") or [])
                    if str(value).strip()
                ],
            ]
        )
    )
    explicit_target = _explicit_target_policy(user_input)
    generic_support = _contains(
        user_input,
        [
            "對就是這樣",
            "对就是这样",
            "對，就是這樣",
            "对，就是这样",
            "沒錯",
            "没错",
            "そうそう",
            "その通り",
            "exactly",
            "that's right",
        ],
    )
    correction_cues = _explicit_correction_cues(user_input)
    target_guarded_leading_rejection_m36 = bool(
        explicit_target
        and re.match(
            r"^\s*(?:no\b[\s,;:!\-—–]*|違う[\s、,;:！!\-—–]+)",
            str(user_input or ""),
            re.I,
        )
    )
    generic_correction = bool(
        correction_cues["detected"]
        or _contains(user_input, ["你搞錯", "你搞错"])
        or target_guarded_leading_rejection_m36
    )
    explicit_feedback_reference = _contains(
        user_input,
        [
            "不是要",
            "不要你",
            "我要的是",
            "我想要你",
            "剛剛",
            "刚刚",
            "さっき",
            "そうじゃなく",
            "欲しかったのは",
            "i didn't want",
            "i did not want",
            "i wanted you",
            "what i wanted",
            "you should have",
            "you misunderstood",
            "i only want",
            "i just want",
        ],
    )
    indirect_revision_cue = _contains(
        user_input,
        [
            "其實我只想",
            "其实我只想",
            "算了，先",
            "算了先",
            "先別",
            "先别",
            "反而想",
            "やっぱり",
            "むしろ",
            "とりあえず聞いて",
            "actually i just",
            "rather have you",
            "just let me",
        ],
    )
    feedback_linked = bool(
        generic_support
        or generic_correction
        or explicit_feedback_reference
        or target_guarded_leading_rejection_m36
        or (explicit_target and indirect_revision_cue)
        or (selected_policy == "calibrate_need" and explicit_target)
    )
    support_then_new_request = bool(
        generic_support
        and explicit_target
        and selected_policy != "calibrate_need"
        and not explicit_feedback_reference
        and not indirect_revision_cue
    )

    if support_then_new_request:
        # A turn such as "Exactly, that's right. Now I'm excited about ..."
        # verifies the previous response and starts a new request.  Do not bind
        # the new topic's desired policy or atoms to the previous context.
        status = "supported"
        reason = "generic_support_precedes_new_explicit_request"
    elif explicit_target and feedback_linked:
        status = "supported" if explicit_target == selected_policy else "contradicted"
        reason = "explicit_desired_response_matches_prediction" if status == "supported" else "explicit_desired_response_differs_from_prediction"
    elif generic_support:
        status = "supported"
        reason = "explicit_generic_support"
    elif generic_correction:
        status = "contradicted"
        reason = "explicit_generic_correction"
    elif explicit_target:
        status = "uncertain"
        reason = "new_explicit_request_not_evidence_about_previous_response"
    else:
        status = "uncertain"
        reason = "no_decisive_feedback_about_response_policy"

    reliability = state["policy_reliability"].setdefault(selected_policy, {})
    before_reliability = deepcopy(reliability)
    reliability[status] = int(reliability.get(status) or 0) + 1
    if status == "supported":
        reliability["alpha"] = int(reliability.get("alpha") or 1) + 1
    elif status == "contradicted":
        reliability["beta"] = int(reliability.get("beta") or 1) + 1
    reliability["mean"] = round(
        int(reliability.get("alpha") or 1)
        / (int(reliability.get("alpha") or 1) + int(reliability.get("beta") or 1)),
        4,
    )
    scoped_reliability = state["scoped_policy_reliability"].setdefault(
        scope_id,
        _empty_policy_reliability(),
    )[selected_policy]
    before_scoped_reliability = deepcopy(scoped_reliability)
    scoped_reliability[status] = int(scoped_reliability.get(status) or 0) + 1
    if status == "supported":
        scoped_reliability["alpha"] = int(scoped_reliability.get("alpha") or 1) + 1
    elif status == "contradicted":
        scoped_reliability["beta"] = int(scoped_reliability.get("beta") or 1) + 1
    scoped_reliability["mean"] = round(
        int(scoped_reliability.get("alpha") or 1)
        / (
            int(scoped_reliability.get("alpha") or 1)
            + int(scoped_reliability.get("beta") or 1)
        ),
        4,
    )

    atom_changes = []
    dimension_changes = []
    evidence_digest = _digest(user_input)
    next_revision = int(state.get("revision_count") or 0) + int(
        status in {"supported", "contradicted"}
    )
    scope_record = state["scoped_atoms"].setdefault(
        scope_id,
        {
            "scope": pending_scope,
            "atoms": {},
            "dimensions": {},
            "last_updated_revision": next_revision,
            "ttl_revisions": DEFAULT_SCOPE_TTL_REVISIONS,
        },
    )
    scope_record.setdefault("dimensions", {})
    feedback_assignments = (
        _explicit_atom_assignments(user_input)
        if feedback_linked and not support_then_new_request
        else {}
    )
    if feedback_linked and not support_then_new_request and not explicit_target:
        feedback_assignments.update(
            _supported_explicit_response_atom_assignments(pending, status)
        )
    for atom, (value, confidence, source_kind) in feedback_assignments.items():
        if atom not in PERSISTABLE_ATOMS:
            continue
        before = deepcopy(scope_record["atoms"].get(atom))
        after = {
            "value": _clip(value),
            "confidence": _clip(confidence),
            "source_kind": source_kind,
            "evidence_digest": evidence_digest,
            "updated_turn": int(turn_index),
            "updated_revision": next_revision,
            "contradiction_count": int((before or {}).get("contradiction_count") or 0),
        }
        if before and abs(float(before.get("value", 0.0)) - after["value"]) >= 0.45:
            after["contradiction_count"] += 1
        scope_record["atoms"][atom] = after
        # Retain this aggregate only for M16-compatible diagnostics. M17 reply
        # decisions never consume it without an exact categorical scope match.
        state["learned_atoms"][atom] = deepcopy(after)
        atom_changes.append(
            {
                "atom": atom,
                "scope_id": scope_id,
                "before": before,
                "after": deepcopy(after),
            }
        )
    if atom_changes:
        scope_record["scope"] = pending_scope
        scope_record["last_updated_revision"] = next_revision

    dimension_targets = _feedback_dimension_targets(
        selected_policy,
        None if support_then_new_request else explicit_target,
        status,
    ) if feedback_linked else {}
    for dimension, value in dimension_targets.items():
        before = deepcopy(scope_record["dimensions"].get(dimension))
        after = {
            "value": _clip(value),
            "confidence": 0.94 if explicit_target and not support_then_new_request else 0.84,
            "source_kind": (
                "explicit_desired_response_feedback"
                if explicit_target and not support_then_new_request
                else "explicit_support_of_selected_response"
            ),
            "evidence_digest": evidence_digest,
            "updated_turn": int(turn_index),
            "updated_revision": next_revision,
            "contradiction_count": int((before or {}).get("contradiction_count") or 0),
        }
        if before and abs(float(before.get("value", 0.0)) - after["value"]) >= 0.45:
            after["contradiction_count"] += 1
        scope_record["dimensions"][dimension] = after
        dimension_changes.append(
            {
                "dimension": dimension,
                "scope_id": scope_id,
                "before": before,
                "after": deepcopy(after),
            }
        )
    if dimension_changes:
        scope_record["scope"] = pending_scope
        scope_record["last_updated_revision"] = next_revision

    # A correction must repair every structured scope that causally supported
    # the response being rejected. Otherwise a stale preference can survive in
    # the original disclosure scope and revive on the next similar turn even
    # though the visible correction appeared successful.
    causal_scope_repairs = []
    if status == "contradicted" and explicit_target and feedback_linked:
        for causal_scope_id in causal_scope_ids:
            if causal_scope_id == scope_id:
                continue
            causal_record = state["scoped_atoms"].get(causal_scope_id)
            if not isinstance(causal_record, dict):
                continue
            repaired_atoms = []
            repaired_dimensions = []
            causal_record.setdefault("atoms", {})
            causal_record.setdefault("dimensions", {})
            for atom, (value, confidence, source_kind) in feedback_assignments.items():
                if atom not in PERSISTABLE_ATOMS:
                    continue
                before = deepcopy(causal_record["atoms"].get(atom))
                after = {
                    "value": _clip(value),
                    "confidence": _clip(confidence),
                    "source_kind": "explicit_correction_causal_scope_repair",
                    "evidence_digest": evidence_digest,
                    "updated_turn": int(turn_index),
                    "updated_revision": next_revision,
                    "contradiction_count": int((before or {}).get("contradiction_count") or 0),
                }
                if before and abs(float(before.get("value", 0.0)) - after["value"]) >= 0.45:
                    after["contradiction_count"] += 1
                causal_record["atoms"][atom] = after
                state["learned_atoms"][atom] = deepcopy(after)
                repaired_atoms.append(
                    {"atom": atom, "before": before, "after": deepcopy(after)}
                )
            for dimension, value in dimension_targets.items():
                before = deepcopy(causal_record["dimensions"].get(dimension))
                after = {
                    "value": _clip(value),
                    "confidence": 0.94,
                    "source_kind": "explicit_correction_causal_scope_repair",
                    "evidence_digest": evidence_digest,
                    "updated_turn": int(turn_index),
                    "updated_revision": next_revision,
                    "contradiction_count": int((before or {}).get("contradiction_count") or 0),
                }
                if before and abs(float(before.get("value", 0.0)) - after["value"]) >= 0.45:
                    after["contradiction_count"] += 1
                causal_record["dimensions"][dimension] = after
                repaired_dimensions.append(
                    {"dimension": dimension, "before": before, "after": deepcopy(after)}
                )
            causal_reliability = state["scoped_policy_reliability"].setdefault(
                causal_scope_id,
                _empty_policy_reliability(),
            )[selected_policy]
            causal_reliability["contradicted"] = int(
                causal_reliability.get("contradicted") or 0
            ) + 1
            causal_reliability["beta"] = int(causal_reliability.get("beta") or 1) + 1
            causal_reliability["mean"] = round(
                int(causal_reliability.get("alpha") or 1)
                / (
                    int(causal_reliability.get("alpha") or 1)
                    + int(causal_reliability.get("beta") or 1)
                ),
                4,
            )
            causal_record["last_updated_revision"] = next_revision
            causal_scope_repairs.append(
                {
                    "scope_id": causal_scope_id,
                    "repaired_atoms": repaired_atoms,
                    "repaired_dimensions": repaired_dimensions,
                    "revoked_policy": selected_policy,
                    "replacement_policy": explicit_target,
                    "policy_reliability_after": deepcopy(causal_reliability),
                }
            )

    state, trigger_relation_update_m37 = _update_verified_trigger_relation_m37(
        state,
        pending,
        status,
        evidence_digest,
        turn_index,
        next_revision,
    )

    trace = {
        "schema": FEEDBACK_SCHEMA,
        "status": status,
        "reason": reason,
        "turn_index": int(turn_index),
        "previous_prediction_id": pending.get("prediction_id"),
        "previous_policy_id": selected_policy,
        "explicit_target_policy": explicit_target,
        "correction_cues_m20": correction_cues,
        "current_request_separated_from_feedback": support_then_new_request,
        "feedback_linked_to_previous_prediction": feedback_linked,
        "target_guarded_leading_rejection_m36": target_guarded_leading_rejection_m36,
        "trigger_relation_update_m37": trigger_relation_update_m37,
        "feedback_linkage_reason": (
            "calibration_answer"
            if selected_policy == "calibrate_need" and explicit_target
            else "explicit_feedback_reference"
            if explicit_feedback_reference
            else "indirect_revision_cue"
            if indirect_revision_cue and explicit_target
            else "generic_feedback"
            if generic_support or generic_correction
            else "new_request_or_unresolved"
        ),
        "policy_reliability_before": before_reliability,
        "policy_reliability_after": deepcopy(reliability),
        "context_scope": pending_scope,
        "scoped_policy_reliability_before": before_scoped_reliability,
        "scoped_policy_reliability_after": deepcopy(scoped_reliability),
        "atom_changes": atom_changes,
        "dimension_changes": dimension_changes,
        "causal_scope_repairs_m23": causal_scope_repairs,
        "evidence": {
            "source": "next_user_turn",
            "digest": evidence_digest,
            "raw_text_persisted": False,
        },
    }
    state, m27_outcome_update = _resolve_m27_outcome(
        state,
        pending,
        trace,
        turn_index=turn_index,
    )
    trace["causal_outcome_calibration_m27"] = m27_outcome_update
    state["revision_count"] += int(
        status in {"supported", "contradicted"}
        or bool(atom_changes)
        or bool(dimension_changes)
    )
    state["last_turn"] = int(turn_index)
    state["pending_prediction"] = None
    state["revision_history"] = [*state.get("revision_history", []), deepcopy(trace)][-40:]
    return state, trace


HIERARCHY_LEVEL_WEIGHTS = {
    "exact": 1.0,
    "domain": 0.62,
    "relationship": 0.36,
}


def _hierarchy_level(source_scope, target_scope):
    if source_scope.get("scope_id") == target_scope.get("scope_id"):
        return "exact"
    if source_scope.get("domain") == target_scope.get("domain"):
        return "domain"
    source_relationship = source_scope.get("relationship_band")
    if (
        source_relationship
        and source_relationship != "unspecified"
        and source_relationship == target_scope.get("relationship_band")
    ):
        return "relationship"
    return None


def _hierarchy_records(model, target_scope):
    rows = []
    scope_ids = set((model.get("scoped_atoms") or {}).keys())
    scope_ids.update((model.get("scoped_policy_reliability") or {}).keys())
    for scope_id in scope_ids:
        record = (model.get("scoped_atoms") or {}).get(scope_id) or {}
        source_scope = _normalise_scope(record.get("scope"), scope_id=scope_id)
        if not record.get("scope"):
            source_scope = _scope_from_id(scope_id)
        level = _hierarchy_level(source_scope, target_scope)
        if not level:
            continue
        rows.append(
            {
                "level": level,
                "weight": HIERARCHY_LEVEL_WEIGHTS[level],
                "scope": source_scope,
                "record": record,
                "last_updated_revision": int(record.get("last_updated_revision") or 0),
            }
        )
    level_order = {"exact": 0, "domain": 1, "relationship": 2}
    rows.sort(
        key=lambda row: (
            level_order[row["level"]],
            -row["last_updated_revision"],
            row["scope"]["scope_id"],
        )
    )
    return rows


def _negative_atom_transfer_reason(atom, learned, source_scope, target_scope, level, explicit):
    if atom in explicit:
        explicit_value = float(explicit[atom][0])
        if abs(explicit_value - float(learned.get("value") or 0.0)) >= 0.45:
            return "current_explicit_cue_conflicts_with_prior"
    if level == "relationship" and atom != "relationship_familiarity":
        return "relationship_fallback_cannot_transfer_content_need"
    if atom == "humor_invitation":
        if target_scope.get("domain") == "physical_wellbeing":
            return "physical_wellbeing_blocks_humor_transfer"
        verified_same_domain_humor = bool(
            learned.get("source_kind") == "supported_explicit_response_form"
            and source_scope.get("domain") == target_scope.get("domain")
            and source_scope.get("relationship_band") == "familiar"
        )
        if (
            level != "exact"
            and target_scope.get("relationship_band") != "familiar"
            and not verified_same_domain_humor
        ):
            return "nonexact_humor_requires_current_familiarity_cue"
    if atom == "positive_arousal" and target_scope.get("domain") not in {
        "positive_anticipation",
        "general_conversation",
    }:
        return "positive_arousal_does_not_transfer_to_this_domain"
    return None


def _negative_dimension_transfer_reason(
    dimension,
    learned,
    source_scope,
    target_scope,
    level,
    current_dimension_target,
):
    if dimension in current_dimension_target:
        if abs(
            float(current_dimension_target[dimension])
            - float(learned.get("value") or 0.0)
        ) >= 0.45:
            return "current_explicit_need_conflicts_with_dimension_prior"
    if level == "relationship" and dimension not in {"directness", "humor", "distance"}:
        return "relationship_fallback_limited_to_interaction_style"
    if dimension == "humor":
        if target_scope.get("domain") == "physical_wellbeing":
            return "physical_wellbeing_blocks_humor_dimension"
        verified_same_domain_humor = bool(
            learned.get("source_kind") == "explicit_support_of_selected_response"
            and source_scope.get("domain") == target_scope.get("domain")
            and source_scope.get("relationship_band") == "familiar"
        )
        if (
            level != "exact"
            and target_scope.get("relationship_band") != "familiar"
            and not verified_same_domain_humor
        ):
            return "nonexact_humor_dimension_requires_familiarity"
    if dimension == "actionability" and target_scope.get("interaction_kind") == "emotional_bid":
        if float(learned.get("value") or 0.0) > 0.55:
            return "emotional_bid_blocks_high_actionability_transfer"
    return None


def _resolve_hierarchical_priors(model, context_scope, explicit):
    records = _hierarchy_records(model, context_scope)
    atom_priors = {}
    dimension_priors = {}
    used = []
    rejected = []
    explicit_target = _explicit_target_policy_from_assignments(explicit)
    current_dimension_target = _explicit_dimension_constraints(explicit_target)
    revision_count = int(model.get("revision_count") or 0)

    for source in records:
        level = source["level"]
        source_scope = source["scope"]
        record = source["record"]
        ttl = int(record.get("ttl_revisions") or DEFAULT_SCOPE_TTL_REVISIONS)
        for atom, learned in (record.get("atoms") or {}).items():
            if atom in atom_priors:
                continue
            age = max(0, revision_count - int(learned.get("updated_revision") or 0))
            reason = "scope_expired" if age > ttl else _negative_atom_transfer_reason(
                atom,
                learned,
                source_scope,
                context_scope,
                level,
                explicit,
            )
            decay = max(0.20, 0.92 ** age)
            confidence = _clip(
                float(learned.get("confidence") or 0.0)
                * decay
                * 0.72
                * float(source["weight"])
            )
            if not reason and confidence < 0.20:
                reason = "confidence_decayed_below_use_threshold"
            if reason:
                rejected.append(
                    {
                        "kind": "atom",
                        "name": atom,
                        "source_scope_id": source_scope["scope_id"],
                        "level": level,
                        "reason": reason,
                        "age_revisions": age,
                        "ttl_revisions": ttl,
                    }
                )
                continue
            atom_priors[atom] = {
                **deepcopy(learned),
                "effective_confidence": confidence,
                "match_level": level,
                "source_scope_id": source_scope["scope_id"],
                "age_revisions": age,
            }
            used.append(
                {
                    "kind": "atom",
                    "name": atom,
                    "source_scope_id": source_scope["scope_id"],
                    "level": level,
                    "effective_confidence": round(confidence, 4),
                }
            )

        for dimension, learned in (record.get("dimensions") or {}).items():
            if dimension in dimension_priors:
                continue
            age = max(0, revision_count - int(learned.get("updated_revision") or 0))
            reason = "scope_expired" if age > ttl else _negative_dimension_transfer_reason(
                dimension,
                learned,
                source_scope,
                context_scope,
                level,
                current_dimension_target,
            )
            decay = max(0.20, 0.92 ** age)
            confidence = _clip(
                float(learned.get("confidence") or 0.0)
                * decay
                * 0.72
                * float(source["weight"])
            )
            if not reason and confidence < 0.18:
                reason = "confidence_decayed_below_use_threshold"
            if reason:
                rejected.append(
                    {
                        "kind": "dimension",
                        "name": dimension,
                        "source_scope_id": source_scope["scope_id"],
                        "level": level,
                        "reason": reason,
                        "age_revisions": age,
                        "ttl_revisions": ttl,
                    }
                )
                continue
            dimension_priors[dimension] = {
                **deepcopy(learned),
                "effective_confidence": confidence,
                "match_level": level,
                "source_scope_id": source_scope["scope_id"],
                "age_revisions": age,
            }
            used.append(
                {
                    "kind": "dimension",
                    "name": dimension,
                    "source_scope_id": source_scope["scope_id"],
                    "level": level,
                    "effective_confidence": round(confidence, 4),
                }
            )

    levels_used = [row["level"] for row in used]
    match_status = next(
        (level for level in ("exact", "domain", "relationship") if level in levels_used),
        "none",
    )
    return atom_priors, dimension_priors, {
        "schema": HIERARCHY_SCHEMA,
        "status": match_status,
        "target_scope": deepcopy(context_scope),
        "source_scopes_considered": [
            {
                "scope_id": row["scope"]["scope_id"],
                "level": row["level"],
                "weight": row["weight"],
            }
            for row in records
        ],
        "used": used,
        "rejected": rejected,
        "negative_transfer_gate_count": len(rejected),
        "legacy_unscoped_atoms_ignored": int(model.get("legacy_unscoped_atom_count") or 0),
        "raw_dialogue_persisted": False,
    }


def _explicit_target_policy_from_assignments(assignments):
    if assignments.get("humor_invitation", (0,))[0] >= 0.9:
        return "playful_tease"
    if assignments.get("listening_request", (0,))[0] >= 0.9:
        return "listen_presence"
    if assignments.get("solution_request", (0,))[0] >= 0.9:
        return "solve_regulation"
    if assignments.get("positive_arousal", (0,))[0] >= 0.9:
        return "share_arousal"
    if (
        assignments.get("sleep_debt", (0,))[0] >= 0.9
        or assignments.get("physical_strain", (0,))[0] >= 0.9
    ):
        return "care_physiology"
    if assignments.get("companionship_request", (0,))[0] >= 0.9:
        return "share_arousal"
    return None


def _explicit_dimension_constraints(policy_id):
    return {
        "playful_tease": {"humor": 0.98, "distance": 0.08},
        "listen_presence": {"listening": 0.98, "actionability": 0.08},
        "solve_regulation": {"actionability": 0.96},
        "care_physiology": {"care": 0.92, "humor": 0.02},
        "share_arousal": {},
        "calibrate_need": {},
    }.get(policy_id, {})


def build_current_state(
    user_input,
    pragmatic_understanding,
    hypothesis,
    longitudinal_model,
    model,
    turn_index=0,
    adaptive_feedback=None,
):
    atoms = {
        key: {
            "value": value,
            "confidence": confidence,
            "status": "unknown",
            "evidence": "no_decisive_current_turn_evidence",
        }
        for key, (value, confidence) in ATOM_DEFAULTS.items()
    }
    activation_reasons = []
    learned_used = []
    learned_rejected = []
    model = _normalise_model(model)
    context_scope = infer_context_scope(
        user_input,
        pragmatic_understanding=pragmatic_understanding,
        hypothesis=hypothesis,
    )
    explicit = _explicit_atom_assignments(user_input)
    explicit_response_request_m25 = classify_explicit_desired_response_m25(user_input)
    observable_trigger_m37 = extract_observable_trigger_predicates_m37(user_input)
    trigger_relation_candidate_m37 = classify_trigger_relation_candidate_m37(
        user_input,
        explicit_request=explicit_response_request_m25,
    )
    trigger_relation_match_m37 = match_verified_trigger_relation_m37(
        model,
        user_input,
    )
    explicit_target = _explicit_target_policy(user_input)
    correction_cues = _explicit_correction_cues(user_input)
    adaptive_feedback = deepcopy(adaptive_feedback or {})
    authoritative_correction = bool(
        explicit_target
        and (
            set(correction_cues.get("cue_types") or []).intersection(
                {"explicit_misunderstanding", "exclusive_desired_response"}
            )
            or adaptive_feedback.get("status") == "contradicted"
        )
    )
    scoped_atoms, dimension_priors, hierarchy = _resolve_hierarchical_priors(
        model,
        context_scope,
        explicit,
    )
    verified_response_prior_atoms = sorted(
        atom
        for atom, learned in scoped_atoms.items()
        if learned.get("source_kind") == "supported_explicit_response_form"
    )
    for key, learned in scoped_atoms.items():
        prior_confidence = _clip(learned.get("effective_confidence"))
        base_value = atoms[key]["value"]
        weight = min(0.7, prior_confidence)
        atoms[key] = {
            "value": _clip((1.0 - weight) * base_value + weight * float(learned.get("value") or 0.0)),
            "confidence": prior_confidence,
            "status": "learned_interaction_prior",
            "evidence": f"persisted_explicit_feedback_digest:{learned.get('evidence_digest')}",
        }
        learned_used.append(key)
    verified_policy_candidates_m34 = []
    verified_policy_by_atom_m34 = {
        "humor_invitation": "playful_tease",
        "solution_request": "solve_regulation",
        "listening_request": "listen_presence",
        "companionship_request": "share_arousal",
    }
    for atom in verified_response_prior_atoms:
        policy_id = verified_policy_by_atom_m34.get(atom)
        atom_row = atoms.get(atom) or {}
        score = float(atom_row.get("value") or 0.0) * float(
            atom_row.get("confidence") or 0.0
        )
        if policy_id and float(atom_row.get("value") or 0.0) >= 0.50:
            verified_policy_candidates_m34.append((score, policy_id, atom))
    verified_policy_candidates_m34.sort(reverse=True)
    verified_response_policy_m34 = (
        verified_policy_candidates_m34[0][1]
        if verified_policy_candidates_m34
        else None
    )
    relation_policy_m37 = str(
        trigger_relation_match_m37.get("response_policy") or ""
    )
    relation_atom_by_policy_m37 = {
        "playful_tease": "humor_invitation",
        "solve_regulation": "solution_request",
        "listen_presence": "listening_request",
        "share_arousal": "companionship_request",
    }
    relation_atom_m37 = relation_atom_by_policy_m37.get(relation_policy_m37)
    if (
        trigger_relation_match_m37.get("status")
        == "matched_verified_trigger_relation"
        and relation_atom_m37
    ):
        _set_atom(
            atoms,
            relation_atom_m37,
            0.96,
            max(0.82, _clip(trigger_relation_match_m37.get("confidence"))),
            "verified_trigger_relation_m37",
            "current_observable_trigger_matches_verified_future_response_relation",
        )
        learned_used.append(relation_atom_m37)
        verified_response_prior_atoms.append(relation_atom_m37)
        verified_response_prior_atoms = list(
            dict.fromkeys(verified_response_prior_atoms)
        )
        verified_response_policy_m34 = relation_policy_m37
        activation_reasons.append("verified_trigger_relation_m37_matched")
    learned_rejected.extend(
        {
            "atom": row["name"],
            "scope_id": row["source_scope_id"],
            "match_level": row["level"],
            "reason": row["reason"],
            "age_revisions": row.get("age_revisions"),
            "ttl_revisions": row.get("ttl_revisions"),
        }
        for row in hierarchy["rejected"]
        if row["kind"] == "atom"
    )
    for key, (value, confidence, status) in explicit.items():
        _set_atom(atoms, key, value, confidence, status, "current_turn_visible_cue")
    if explicit:
        activation_reasons.append("explicit_current_turn_desired_response_or_state_cue")
    if context_scope.get("relationship_band") == "familiar":
        _set_atom(
            atoms,
            "relationship_familiarity",
            0.90,
            0.84,
            "current_visible_relationship_cue",
            "current_turn_visible_cue",
        )
        activation_reasons.append("current_familiarity_cue")

    pragmatic_label = str((pragmatic_understanding or {}).get("pragmatic_label") or "")
    if pragmatic_label == "ambiguous_arousal":
        learned_response_prior = max(
            atoms["humor_invitation"]["value"] * atoms["humor_invitation"]["confidence"],
            atoms["listening_request"]["value"] * atoms["listening_request"]["confidence"],
            atoms["solution_request"]["value"] * atoms["solution_request"]["confidence"],
            atoms["companionship_request"]["value"] * atoms["companionship_request"]["confidence"],
        )
        # Preserve M18's correction-based reusable path. M34 adds a narrower
        # verified-response source but must not revoke already-valid evidence.
        if learned_used and learned_response_prior >= 0.20:
            _set_atom(
                atoms,
                "uncertainty",
                0.34,
                0.70,
                "bounded_by_verified_interaction_prior",
                "ambiguous_state_but_preferred_response_form_previously_explicit",
            )
            activation_reasons.append("ambiguous_arousal_with_learned_response_preference")
        else:
            _set_atom(atoms, "uncertainty", 0.95, 0.94, "derived", "pragmatic_ambiguous_arousal")
            activation_reasons.append("ambiguous_arousal_requires_bounded_response_choice")
    elif pragmatic_label == "possible_indirect_support_request":
        _set_atom(atoms, "listening_request", 0.70, 0.52, "bounded_inference", "pragmatic_indirect_support")
        _set_atom(atoms, "companionship_request", 0.68, 0.50, "bounded_inference", "pragmatic_indirect_support")
        _set_atom(atoms, "uncertainty", 0.58, 0.66, "derived", "pragmatic_indirect_support")
        activation_reasons.append("possible_indirect_support_request")
    elif pragmatic_label == "explicit_positive_arousal":
        _set_atom(atoms, "positive_arousal", 0.96, 0.94, "explicit_user_report", "pragmatic_positive_arousal")
        activation_reasons.append("explicit_positive_arousal")
    elif pragmatic_label == "explicit_correction":
        activation_reasons.append("explicit_correction_of_previous_understanding")

    if (
        hierarchy.get("status") in {"domain", "relationship"}
        and learned_used
        and context_scope.get("relationship_band") == "familiar"
        and max(atoms["physical_strain"]["value"], atoms["sleep_debt"]["value"]) < 0.68
    ):
        learned_response_prior = max(
            atoms["humor_invitation"]["value"] * atoms["humor_invitation"]["confidence"],
            atoms["listening_request"]["value"] * atoms["listening_request"]["confidence"],
            atoms["solution_request"]["value"] * atoms["solution_request"]["confidence"],
        )
        if learned_response_prior >= 0.20:
            _set_atom(
                atoms,
                "uncertainty",
                0.38,
                0.62,
                "bounded_by_hierarchical_interaction_prior",
                "near_context_transfer_with_current_familiarity_cue",
            )
            activation_reasons.append("near_context_verified_preference_available")

    features = set((hypothesis or {}).get("semantic_features") or [])
    if features.intersection({"ambiguous_mood", "support_request", "tired", "sad", "excited", "correction"}):
        activation_reasons.append("hypothesis_feature_requires_attuned_response")
    if learned_used and features.intersection({"ambiguous_mood", "support_request", "tired", "sad", "excited"}):
        activation_reasons.append("persisted_interaction_prior_available")
    if learned_used and context_scope.get("domain") != "general_conversation":
        activation_reasons.append("hierarchical_interaction_prior_available")

    return {
        "schema": STATE_SCHEMA,
        "turn_index": int(turn_index),
        "input_digest": _digest(user_input),
        "raw_dialogue_persisted": False,
        "explicit_desired_response_m25": explicit_response_request_m25,
        "observable_trigger_m37": observable_trigger_m37,
        "trigger_relation_candidate_m37": trigger_relation_candidate_m37,
        "trigger_relation_match_m37": trigger_relation_match_m37,
        "correction_directive_m20": {
            "schema": CORRECTION_SCHEMA,
            "detected": authoritative_correction,
            "correction_cues": list(correction_cues.get("cue_types") or []),
            "explicit_target_policy": explicit_target,
            "authority": (
                "current_explicit_desired_response"
                if authoritative_correction
                else "ordinary_evidence_weighting"
            ),
            "revoked_previous_policy": (
                adaptive_feedback.get("previous_policy_id")
                if adaptive_feedback.get("status") == "contradicted"
                else None
            ),
            "feedback_status": adaptive_feedback.get("status"),
            "evidence_digest": correction_cues.get("evidence_digest"),
            "raw_dialogue_persisted": False,
        },
        "context_scope": context_scope,
        "scope_match": {
            "schema": HIERARCHY_SCHEMA,
            "status": hierarchy["status"],
            "scope_id": context_scope["scope_id"],
            "source_scopes_considered": hierarchy["source_scopes_considered"],
            "used": hierarchy["used"],
            "rejected": hierarchy["rejected"],
            "negative_transfer_gate_count": hierarchy["negative_transfer_gate_count"],
            "legacy_unscoped_atoms_ignored": hierarchy["legacy_unscoped_atoms_ignored"],
        },
        "atoms": atoms,
        "learned_atoms_used": learned_used,
        "verified_response_prior_atoms_m34": verified_response_prior_atoms,
        "verified_response_policy_m34": verified_response_policy_m34,
        "learned_atoms_rejected": learned_rejected,
        "learned_dimension_priors": dimension_priors,
        "activation_reasons": list(dict.fromkeys(activation_reasons)),
        "active": bool(activation_reasons),
        "reference_person": deepcopy(REFERENCE_PERSON),
        "feedback_history": [],
        "intervention_history": [],
        "production_memory_write_count": 0,
        "feedback_origin_scope_id": str(
            ((adaptive_feedback.get("context_scope") or {}).get("scope_id")) or ""
        ),
    }


def _atom_value(state, key):
    return _clip(((state.get("atoms") or {}).get(key) or {}).get("value"))


def _compose_response_dimensions(policy_id, state):
    values = deepcopy(POLICY_DIMENSION_PROFILES[policy_id])
    sources = {dimension: "policy_semantic_anchor" for dimension in RESPONSE_DIMENSIONS}
    learned_applied = []
    for dimension, learned in (state.get("learned_dimension_priors") or {}).items():
        confidence = _clip(learned.get("effective_confidence"))
        weight = min(0.65, confidence)
        values[dimension] = _clip(
            (1.0 - weight) * values[dimension]
            + weight * float(learned.get("value") or 0.0)
        )
        sources[dimension] = f"{learned.get('match_level')}_verified_preference"
        learned_applied.append(
            {
                "dimension": dimension,
                "match_level": learned.get("match_level"),
                "source_scope_id": learned.get("source_scope_id"),
                "effective_confidence": round(confidence, 4),
            }
        )

    # Current visible evidence always outranks historical interaction style.
    physical = max(_atom_value(state, "physical_strain"), _atom_value(state, "sleep_debt"))
    solution = _atom_value(state, "solution_request")
    listening = _atom_value(state, "listening_request")
    humor = _atom_value(state, "humor_invitation")
    uncertainty = _atom_value(state, "uncertainty")
    relationship = (state.get("context_scope") or {}).get("relationship_band")
    if physical >= 0.72:
        values["care"] = max(values["care"], 0.86)
        values["humor"] = min(values["humor"], 0.08)
        sources["care"] = "current_physical_safety_constraint"
        sources["humor"] = "current_physical_safety_constraint"
    if solution >= 0.82:
        values["actionability"] = max(values["actionability"], 0.88)
        sources["actionability"] = "current_explicit_solution_request"
    if listening >= 0.82:
        values["listening"] = max(values["listening"], 0.90)
        values["actionability"] = min(values["actionability"], 0.16)
        sources["listening"] = "current_explicit_listening_request"
        sources["actionability"] = "current_explicit_listening_request"
    if humor >= 0.82 and relationship == "familiar":
        values["humor"] = max(values["humor"], 0.90)
        values["distance"] = min(values["distance"], 0.12)
        sources["humor"] = "current_explicit_bounded_humor_invitation"
        sources["distance"] = "current_familiarity_cue"
    elif uncertainty >= 0.72:
        values["humor"] = min(values["humor"], 0.16)
        sources["humor"] = "current_uncertainty_guard"

    return {
        "schema": DIMENSION_SCHEMA,
        "policy_anchor": policy_id,
        "values": {key: round(_clip(values[key]), 4) for key in RESPONSE_DIMENSIONS},
        "sources": sources,
        "learned_dimensions_applied": learned_applied,
        "raw_dialogue_persisted": False,
    }


def _dimension_fit(profile, learned_priors):
    if not learned_priors:
        return 0.5, 0.0
    weighted_similarity = 0.0
    total_weight = 0.0
    for dimension, learned in learned_priors.items():
        weight = _clip(learned.get("effective_confidence"))
        similarity = 1.0 - abs(
            float((profile.get("values") or {}).get(dimension, 0.5))
            - float(learned.get("value") or 0.0)
        )
        weighted_similarity += similarity * weight
        total_weight += weight
    if total_weight <= 0.0:
        return 0.5, 0.0
    fit = _clip(weighted_similarity / total_weight)
    adjustment = 0.08 * ((fit - 0.5) * 2.0) * min(1.0, total_weight / 1.5)
    return round(fit, 4), round(adjustment, 4)


def _realize_composable_surface(policy_id, dimensions, state):
    variants = SURFACE_VARIANTS[policy_id]
    activation_reasons = set(state.get("activation_reasons") or [])
    explicit_current = "explicit_current_turn_desired_response_or_state_cue" in activation_reasons
    if explicit_current and not dimensions.get("learned_dimensions_applied"):
        variant_index = 0
        reason = "explicit_current_need_uses_canonical_semantic_surface"
    else:
        digest = str(state.get("input_digest") or "0")
        seed = int(digest[:8] or "0", 16) + int(state.get("turn_index") or 0)
        eligible = list(range(len(variants)))
        values = dimensions.get("values") or {}
        if policy_id == "playful_tease" and float(values.get("humor") or 0.0) < 0.72:
            eligible = [0]
        variant_index = eligible[seed % len(eligible)]
        reason = "dimension_guarded_deterministic_surface_variation"
    return variants[variant_index], {
        "schema": "uruha_composable_japanese_realization_m18",
        "policy_anchor": policy_id,
        "variant_id": f"{policy_id}:v{variant_index + 1}",
        "reason": reason,
        "dimensions": deepcopy(dimensions),
        "casual_japanese_only": True,
        "raw_dialogue_persisted": False,
    }


def _hierarchical_policy_reliability(model, state, policy_id):
    target_scope = state.get("context_scope") or {}
    evidence_rows = []
    weighted_positive = 0.0
    weighted_total = 0.0
    decisive_total = 0
    for source in _hierarchy_records(model, target_scope):
        level = source["level"]
        if level == "relationship" and policy_id not in {
            "playful_tease",
            "listen_presence",
            "share_arousal",
            "calibrate_need",
        }:
            continue
        reliability = (
            (model.get("scoped_policy_reliability") or {})
            .get(source["scope"]["scope_id"], {})
            .get(policy_id, {})
        )
        decisive = int(reliability.get("supported") or 0) + int(
            reliability.get("contradicted") or 0
        )
        if decisive <= 0:
            continue
        weight = float(source["weight"]) * min(1.0, decisive / 3.0)
        mean = float(reliability.get("mean", 0.5))
        weighted_positive += mean * weight
        weighted_total += weight
        decisive_total += decisive
        evidence_rows.append(
            {
                "scope_id": source["scope"]["scope_id"],
                "level": level,
                "mean": round(mean, 4),
                "decisive_count": decisive,
                "weight": round(weight, 4),
            }
        )
    mean = weighted_positive / weighted_total if weighted_total else 0.5
    learned_weight = min(0.18, 0.045 * decisive_total)
    adjustment = learned_weight * (mean - 0.5) * 2.0
    return {
        "mean": round(mean, 4),
        "decisive_count": decisive_total,
        "adjustment": round(adjustment, 4),
        "sources": evidence_rows,
    }


def decide_response(state, model):
    if not state.get("active"):
        return {
            "schema": DECISION_SCHEMA,
            "status": "not_applied",
            "reason": "current_turn_not_a_desired_response_inference_case",
            "selected": None,
            "candidates": [],
            "state": deepcopy(state),
        }
    model = _normalise_model(model)
    candidates = []
    verified_response_policy_m34 = str(
        state.get("verified_response_policy_m34") or ""
    )
    for candidate in score_candidates(state):
        row = deepcopy(candidate)
        reliability = _hierarchical_policy_reliability(model, state, row["policy_id"])
        decisive_count = reliability["decisive_count"]
        adjustment = reliability["adjustment"]
        dimensions = _compose_response_dimensions(row["policy_id"], state)
        dimension_fit, dimension_adjustment = _dimension_fit(
            dimensions,
            state.get("learned_dimension_priors") or {},
        )
        row["base_expected_utility"] = row["expected_utility"]
        row["learned_reliability"] = float(reliability.get("mean", 0.5))
        row["learned_evidence_count"] = decisive_count
        row["learned_adjustment"] = round(adjustment, 4)
        row["reliability_sources"] = reliability["sources"]
        row["dimension_fit"] = dimension_fit
        row["dimension_adjustment"] = dimension_adjustment
        row["verified_context_adjustment_m34"] = (
            0.16
            if verified_response_policy_m34
            and row["policy_id"] == verified_response_policy_m34
            else 0.0
        )
        row["response_dimensions"] = dimensions
        row["expected_utility"] = round(
            _clip(
                float(row["expected_utility"])
                + adjustment
                + dimension_adjustment
                + row["verified_context_adjustment_m34"]
            ),
            4,
        )
        candidates.append(row)
    candidates.sort(key=lambda row: (-row["expected_utility"], row["policy_id"]))
    ordinary_selected = deepcopy(candidates[0])
    directive = deepcopy(state.get("correction_directive_m20") or {})
    explicit_request_m25 = deepcopy(state.get("explicit_desired_response_m25") or {})
    m25_target = str(explicit_request_m25.get("selected_policy") or "")
    correction_target = str(directive.get("explicit_target_policy") or "")
    trigger_relation_m37 = deepcopy(
        state.get("trigger_relation_match_m37") or {}
    )
    trigger_relation_target_m37 = str(
        trigger_relation_m37.get("response_policy") or ""
    )
    trigger_relation_authoritative_m37 = bool(
        trigger_relation_m37.get("status")
        == "matched_verified_trigger_relation"
        and trigger_relation_m37.get("authority")
        == "verified_observable_trigger_relation_m37"
        and trigger_relation_target_m37 in POLICIES
    )
    correction_authoritative = bool(
        directive.get("detected")
        and directive.get("authority") == "current_explicit_desired_response"
        and correction_target
    )
    request_authoritative = bool(
        explicit_request_m25.get("detected")
        and explicit_request_m25.get("authority") == "current_explicit_desired_response"
        and m25_target
    )
    explicit_target = correction_target if correction_authoritative else m25_target
    if correction_authoritative or request_authoritative:
        selected = deepcopy(
            next(row for row in candidates if row["policy_id"] == explicit_target)
        )
        runner_up = ordinary_selected if ordinary_selected["policy_id"] != explicit_target else deepcopy(candidates[1])
    elif trigger_relation_authoritative_m37:
        selected = deepcopy(
            next(
                row
                for row in candidates
                if row["policy_id"] == trigger_relation_target_m37
            )
        )
        runner_up = (
            ordinary_selected
            if ordinary_selected["policy_id"] != trigger_relation_target_m37
            else deepcopy(candidates[1])
        )
    else:
        selected = ordinary_selected
        runner_up = deepcopy(candidates[1])
    realized_surface, realization_trace = _realize_composable_surface(
        selected["policy_id"],
        selected["response_dimensions"],
        state,
    )
    selected["core_message_jp"] = realized_surface
    selected["realization"] = realization_trace
    if correction_authoritative:
        correction_surfaces = {
            "share_arousal": "あー、そこ読み違えた。結果来るまでうちも一緒に待っとく。",
            "listen_presence": "あー、そこ読み違えた。方法は出さないから、そのまま話して。",
            "solve_regulation": "あー、そこ読み違えた。今すぐできる一個だけ一緒に決めよ。",
            "playful_tease": "あ、そっちか。さっきは読みすぎた。じゃあ言うけど、朝から脳内だけ二十四時間営業かよ。",
            "care_physiology": "あー、そこ読み違えた。体がしんどいなら、まず水飲んで少し休も。",
        }
        selected["core_message_jp"] = correction_surfaces.get(
            explicit_target,
            selected["core_message_jp"],
        )
        selected["realization"] = {
            **selected["realization"],
            "schema": "uruha_correction_repair_realization_m20",
            "reason": "explicit_correction_and_desired_response_are_surface_authority",
        }
    elif request_authoritative:
        selected["core_message_jp"] = EXPLICIT_REQUEST_SURFACES_M25.get(
            explicit_target,
            selected["core_message_jp"],
        )
        selected["realization"] = {
            **selected["realization"],
            "schema": "uruha_explicit_request_realization_m25",
            "reason": "current_cross_lingual_explicit_response_request_is_surface_authority",
        }
    explicit_conversation_act_p3_b50 = deepcopy(
        explicit_request_m25.get("explicit_conversation_act_p3_b50") or {}
    )
    joint_complaint_authoritative = bool(
        request_authoritative
        and selected.get("policy_id") == "share_arousal"
        and explicit_conversation_act_p3_b50.get("detected")
        and explicit_conversation_act_p3_b50.get("act")
        == "joint_complaint"
        and explicit_conversation_act_p3_b50.get("authority")
        == "current_explicit_conversation_act"
    )
    if explicit_conversation_act_p3_b50:
        explicit_conversation_act_p3_b50.update(
            {
                "authoritative": joint_complaint_authoritative,
                "surface_required": joint_complaint_authoritative,
                "surface_status": (
                    "pending"
                    if joint_complaint_authoritative
                    else "not_applicable"
                ),
                "raw_dialogue_persisted": False,
            }
        )
    explicit_request_m25.update(
        {
            "authoritative": request_authoritative,
            "ordinary_selected_policy": ordinary_selected.get("policy_id"),
            "selected_policy": selected.get("policy_id") if request_authoritative else explicit_request_m25.get("selected_policy"),
            "selected_mode": POLICY_TO_RESPONSE_MODE_M23.get(selected.get("policy_id")) if request_authoritative else explicit_request_m25.get("selected_mode"),
            "surface_required": request_authoritative,
            "surface_status": "pending" if request_authoritative else "not_applicable",
            "explicit_conversation_act_p3_b50": (
                explicit_conversation_act_p3_b50
            ),
            "raw_dialogue_persisted": False,
        }
    )
    directive.update(
        {
            "authoritative": correction_authoritative,
            "ordinary_selected_policy": ordinary_selected.get("policy_id"),
            "selected_repair_policy": selected.get("policy_id"),
            "repeated_clarifier_blocked": bool(
                correction_authoritative
                and directive.get("revoked_previous_policy") == "calibrate_need"
                and selected.get("policy_id") != "calibrate_need"
            ),
            "visible_repair_required": correction_authoritative,
            "raw_dialogue_persisted": False,
        }
    )
    prediction_id = f"m18-{int(state.get('turn_index') or 0):04d}-{state.get('input_digest')}"
    return {
        "schema": DECISION_SCHEMA,
        "status": "applied",
        "prediction_id": prediction_id,
        "equation": "r*=argmax(desired_fit + persona_fit + evidence - risk + hierarchical_reliability + dimension_fit)",
        "context_scope": deepcopy(state.get("context_scope") or {}),
        "selected": selected,
        "runner_up": runner_up,
        "utility_margin": round(selected["expected_utility"] - runner_up["expected_utility"], 4),
        "candidates": candidates,
        "response_dimensions": deepcopy(selected.get("response_dimensions") or {}),
        "realization": deepcopy(realization_trace),
        "correction_aware_surface_m20": directive,
        "explicit_desired_response_m25": explicit_request_m25,
        "trigger_relation_m37": {
            **trigger_relation_m37,
            "authoritative": trigger_relation_authoritative_m37,
            "ordinary_selected_policy": ordinary_selected.get("policy_id"),
            "selected_policy": (
                selected.get("policy_id")
                if trigger_relation_authoritative_m37
                else trigger_relation_m37.get("response_policy")
            ),
            "surface_required": trigger_relation_authoritative_m37,
            "raw_dialogue_persisted": False,
        },
        "state": deepcopy(state),
        "claim_boundary": "operational response prediction; not mind reading",
    }


def _m26_relevant_atom_rows(state, policy_id):
    mode = POLICY_TO_RESPONSE_MODE_M23.get(str(policy_id or ""))
    atom_names = [
        name
        for name in MODE_EVIDENCE_ATOMS_M23.get(mode, ())
        if name != "uncertainty"
    ]
    learned_names = set(state.get("learned_atoms_used") or [])
    rows = []
    for name in atom_names:
        atom = deepcopy(((state.get("atoms") or {}).get(name)) or {})
        value = _clip(atom.get("value"))
        confidence = _clip(atom.get("confidence"))
        rows.append(
            {
                "atom": name,
                "value": round(value, 4),
                "confidence": round(confidence, 4),
                "evidence_quality": round(value * confidence, 4),
                "status": atom.get("status") or "unknown",
                "learned_and_reversible": name in learned_names,
            }
        )
    return rows


def _m26_feedback_reliability(feedback):
    feedback = deepcopy(feedback or {})
    before = deepcopy(feedback.get("scoped_policy_reliability_before") or {})
    after = deepcopy(feedback.get("scoped_policy_reliability_after") or {})
    before_mean = float(before.get("mean", 0.5) or 0.5)
    after_mean = float(after.get("mean", 0.5) or 0.5)
    return {
        "schema": "uruha_implicit_response_outcome_update_m26",
        "status": feedback.get("status") or "not_available",
        "reason": feedback.get("reason") or "no_previous_outcome",
        "previous_prediction_id": feedback.get("previous_prediction_id"),
        "previous_policy_id": feedback.get("previous_policy_id"),
        "explicit_target_policy": feedback.get("explicit_target_policy"),
        "feedback_linked_to_previous_prediction": bool(
            feedback.get("feedback_linked_to_previous_prediction")
        ),
        "scoped_reliability_before": round(before_mean, 4),
        "scoped_reliability_after": round(after_mean, 4),
        "scoped_reliability_delta": round(after_mean - before_mean, 4),
        "atom_change_count": len(feedback.get("atom_changes") or []),
        "dimension_change_count": len(feedback.get("dimension_changes") or []),
        "raw_dialogue_persisted": False,
    }


def build_implicit_desired_response_distribution_m26(
    state,
    decision,
    adaptive_feedback=None,
):
    """Turn M18 utilities into a bounded, outcome-weighted action belief.

    The values are normalized operational beliefs, not empirical probabilities
    of a private mental state.  M26 therefore exposes both the uncalibrated
    utility and the posterior reliability weighting, and abstains unless the
    top action has enough separation and evidence to be used safely.
    """
    state = deepcopy(state or {})
    decision = deepcopy(decision or {})
    candidates = [deepcopy(row) for row in (decision.get("candidates") or [])]
    outcome = _m26_feedback_reliability(adaptive_feedback)
    explicit_m25 = deepcopy(
        decision.get("explicit_desired_response_m25")
        or state.get("explicit_desired_response_m25")
        or {}
    )
    correction_m20 = deepcopy(
        decision.get("correction_aware_surface_m20")
        or state.get("correction_directive_m20")
        or {}
    )
    trigger_relation_m37 = deepcopy(decision.get("trigger_relation_m37") or {})
    trigger_relation_authority_m37 = bool(
        trigger_relation_m37.get("authoritative")
        and trigger_relation_m37.get("status")
        == "matched_verified_trigger_relation"
    )
    explicit_authority = bool(
        explicit_m25.get("authoritative")
        or correction_m20.get("authoritative")
        or trigger_relation_authority_m37
    )
    if not candidates:
        return {
            "schema": IMPLICIT_RESPONSE_DISTRIBUTION_SCHEMA_M26,
            "status": "not_applied",
            "reason": "no_active_desired_response_candidates",
            "execute_implicit": False,
            "distribution": [],
            "outcome_update": outcome,
            "raw_dialogue_persisted": False,
        }

    temperature = 0.20
    utilities = [float(row.get("expected_utility") or 0.0) for row in candidates]
    max_utility = max(utilities)
    base_weights = [math.exp((value - max_utility) / temperature) for value in utilities]
    base_total = sum(base_weights) or 1.0
    posterior_weights = []
    for row, base_weight in zip(candidates, base_weights):
        reliability = _clip(row.get("learned_reliability", 0.5))
        posterior_weights.append(base_weight * (0.75 + 0.50 * reliability))
    posterior_total = sum(posterior_weights) or 1.0

    distribution = []
    for row, base_weight, posterior_weight in zip(
        candidates,
        base_weights,
        posterior_weights,
    ):
        policy_id = str(row.get("policy_id") or "")
        atom_rows = _m26_relevant_atom_rows(state, policy_id)
        distribution.append(
            {
                "policy_id": policy_id,
                "mode": POLICY_TO_RESPONSE_MODE_M23.get(policy_id),
                "uncalibrated_utility": round(
                    float(row.get("expected_utility") or 0.0), 4
                ),
                "base_softmax_probability": round(base_weight / base_total, 4),
                "posterior_reliability": round(
                    float(row.get("learned_reliability", 0.5) or 0.5), 4
                ),
                "decisive_outcome_count": int(
                    row.get("learned_evidence_count") or 0
                ),
                "outcome_weighted_probability": round(
                    posterior_weight / posterior_total, 4
                ),
                "relevant_evidence": atom_rows,
                "reliability_sources": deepcopy(row.get("reliability_sources") or []),
            }
        )
    distribution.sort(
        key=lambda row: (
            -float(row.get("outcome_weighted_probability") or 0.0),
            row.get("policy_id") or "",
        )
    )
    top = distribution[0]
    runner = distribution[1] if len(distribution) > 1 else {}
    probability = float(top.get("outcome_weighted_probability") or 0.0)
    runner_probability = float(runner.get("outcome_weighted_probability") or 0.0)
    probability_margin = probability - runner_probability
    evidence_rows = top.get("relevant_evidence") or []
    evidence_quality = max(
        (float(row.get("evidence_quality") or 0.0) for row in evidence_rows),
        default=0.0,
    )
    verified_response_prior_names = set(
        state.get("verified_response_prior_atoms_m34") or []
    )
    learned_relevant = [
        row.get("atom")
        for row in evidence_rows
        if row.get("learned_and_reversible")
        and float(row.get("evidence_quality") or 0.0)
        >= (
            0.22
            if row.get("atom") in verified_response_prior_names
            else 0.30
        )
    ]
    learned_evidence_threshold = (
        0.22
        if any(atom in verified_response_prior_names for atom in learned_relevant)
        else 0.30
    )
    uncertainty = _atom_value(state, "uncertainty")
    strong_current_observation = any(
        float(row.get("evidence_quality") or 0.0) >= 0.72
        and str(row.get("status") or "").startswith("explicit_")
        for row in evidence_rows
    )
    probability_threshold = 0.24 if learned_relevant else 0.40
    margin_threshold = 0.03 if learned_relevant else 0.20
    outcome_gate = bool(
        learned_relevant
        or (
            int(top.get("decisive_outcome_count") or 0) >= 1
            and float(top.get("posterior_reliability") or 0.0) >= 0.50
        )
        or (
            strong_current_observation
            and (
                uncertainty <= 0.55
                or top.get("policy_id") == "care_physiology"
            )
        )
    )
    threshold_checks = {
        "non_clarifier_top": top.get("policy_id") != "calibrate_need",
        "top_probability_threshold_met": probability >= probability_threshold,
        "probability_margin_threshold_met": probability_margin >= margin_threshold,
        "evidence_quality_gte_required": evidence_quality
        >= learned_evidence_threshold,
        "outcome_or_strong_current_evidence_gate": outcome_gate,
    }
    execute_implicit = bool(not explicit_authority and all(threshold_checks.values()))
    if trigger_relation_authority_m37:
        status = "verified_trigger_relation_authority_bypass"
        reason = "verified_observable_trigger_relation_outranks_implicit_distribution"
    elif explicit_authority:
        status = "explicit_authority_bypass"
        reason = "current_explicit_request_or_correction_outranks_implicit_distribution"
    elif execute_implicit:
        status = "execute_implicit"
        reason = "probability_separation_evidence_and_outcome_gates_passed"
    else:
        status = "abstain_low_pressure_clarification"
        reason = "one_or_more_implicit_execution_gates_failed"
    selected = decision.get("selected") or {}
    return {
        "schema": IMPLICIT_RESPONSE_DISTRIBUTION_SCHEMA_M26,
        "status": status,
        "reason": reason,
        "temperature": temperature,
        "probability_semantics": (
            "normalized operational action belief from M18 utility and scoped "
            "Beta reliability; not a probability of private mental state"
        ),
        "external_calibration_status": "not_established_without_fresh_holdout",
        "ordinary_selected_policy": selected.get("policy_id"),
        "implicit_top_policy": top.get("policy_id"),
        "implicit_top_mode": top.get("mode"),
        "top_probability": round(probability, 4),
        "runner_up_policy": runner.get("policy_id"),
        "runner_up_probability": round(runner_probability, 4),
        "probability_margin": round(probability_margin, 4),
        "top_probability_threshold": probability_threshold,
        "probability_margin_threshold": margin_threshold,
        "evidence_quality": round(evidence_quality, 4),
        "learned_evidence_threshold": learned_evidence_threshold,
        "uncertainty": round(uncertainty, 4),
        "learned_relevant_atoms": learned_relevant,
        "strong_current_observation": strong_current_observation,
        "threshold_checks": threshold_checks,
        "execute_implicit": execute_implicit,
        "explicit_authority_bypass": explicit_authority,
        "distribution": distribution,
        "outcome_update": outcome,
        "claim_boundary": (
            "reversible desired-response action selection; not mind reading and "
            "not externally calibrated human-response probability"
        ),
        "raw_dialogue_persisted": False,
    }


def apply_implicit_response_gate_m26(state, decision, contract):
    """Apply M26 abstention without changing M25/M20 current authority."""
    state = deepcopy(state or {})
    updated = deepcopy(decision or {})
    gate = deepcopy(contract or {})
    selected = deepcopy(updated.get("selected") or {})
    gate["pre_gate_selected_policy"] = selected.get("policy_id")
    gate["pre_gate_utility_margin"] = updated.get("utility_margin")
    should_abstain = bool(
        gate.get("status") == "abstain_low_pressure_clarification"
        and selected
        and selected.get("policy_id") != "calibrate_need"
    )
    if should_abstain:
        clarifier = next(
            (
                deepcopy(row)
                for row in (updated.get("candidates") or [])
                if row.get("policy_id") == "calibrate_need"
            ),
            None,
        )
        if clarifier:
            surface, realization = _realize_composable_surface(
                "calibrate_need",
                clarifier.get("response_dimensions") or {},
                state,
            )
            clarifier["core_message_jp"] = surface
            clarifier["realization"] = {
                **realization,
                "schema": "uruha_low_pressure_abstention_realization_m26",
                "reason": "implicit_distribution_failed_execution_gate",
            }
            updated["pre_abstention_selected_m26"] = selected
            updated["selected"] = clarifier
            updated["runner_up"] = selected
            updated["response_dimensions"] = deepcopy(
                clarifier.get("response_dimensions") or {}
            )
            updated["realization"] = deepcopy(clarifier.get("realization") or {})
            gate["abstention_changed_policy"] = True
    gate.setdefault("abstention_changed_policy", False)
    final_selected = updated.get("selected") or {}
    gate["performed_policy"] = final_selected.get("policy_id")
    gate["performed_mode"] = POLICY_TO_RESPONSE_MODE_M23.get(
        final_selected.get("policy_id")
    )
    gate["raw_dialogue_persisted"] = False
    updated["implicit_desired_response_m26"] = gate
    updated["equation_m26"] = (
        "execute implicit argmax only when probability, margin, evidence, and "
        "outcome gates pass; otherwise abstain"
    )
    return updated


def apply_decision_to_plan(plan, decision):
    updated = deepcopy(plan or {})
    selected = (decision or {}).get("selected") or {}
    original_core = str(updated.get("core_message_jp") or "").strip()
    intent = str(updated.get("intent") or "")
    scene = str(updated.get("scene") or "")
    protected_reason = None
    if intent in PROTECTED_INTENTS or scene in PROTECTED_SCENES:
        protected_reason = "safety_or_boundary_plan"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_recall_plan"
    elif not selected:
        protected_reason = "desired_response_model_not_active"
    if protected_reason:
        updated["adaptive_person_model_m16"] = {
            "applied": False,
            "reason": protected_reason,
            "decision": deepcopy(decision),
        }
        updated["adaptive_person_model_m17"] = deepcopy(
            updated["adaptive_person_model_m16"]
        )
        updated["adaptive_person_model_m18"] = deepcopy(
            updated["adaptive_person_model_m16"]
        )
        return updated, updated["adaptive_person_model_m16"]

    policy_id = selected["policy_id"]
    response_modes = {
        "care_physiology": "care_first",
        "solve_regulation": "one_step_support",
        "listen_presence": "listen_without_fixing",
        "share_arousal": "affective_alignment",
        "playful_tease": "familiar_tease",
        "calibrate_need": "clarify_light",
    }
    pragmatic_strategy = updated.get("pragmatic_attunement_strategy_v2_13") or {}
    correction_directive = deepcopy((decision or {}).get("correction_aware_surface_m20") or {})
    explicit_request_m25 = deepcopy(
        (decision or {}).get("explicit_desired_response_m25") or {}
    )
    decision_state = deepcopy((decision or {}).get("state") or {})
    context_scope = deepcopy(
        decision_state.get("context_scope")
        or (decision or {}).get("context_scope")
        or {}
    )
    scope_domain = str(context_scope.get("domain") or "unspecified")
    policy_semantic_domain = "arousal_regulation"
    current_turn_surface_authority = bool(
        correction_directive.get("authoritative")
        or explicit_request_m25.get("authoritative")
    )
    semantic_template_authorized = bool(
        scope_domain == policy_semantic_domain
        or current_turn_surface_authority
        or not original_core
    )
    correction_must_surface = bool(
        correction_directive.get("authoritative")
        or updated.get("intent") == "pragmatic_revision"
        or pragmatic_strategy.get("outcome_status") == "contradicted"
    )
    if correction_directive.get("authoritative") and semantic_template_authorized:
        updated["core_message_jp"] = str(selected.get("core_message_jp") or "").strip()
        updated["reply_goal"] = f"先短く認め、使用者が明示した返され方をそのまま実行する：{selected['instruction']}"
        updated["response_mode"] = "correction_repair"
        revoked = str(correction_directive.get("revoked_previous_policy") or "")
        forbidden = list(updated.get("must_avoid") or [])
        if revoked in SURFACE_VARIANTS:
            forbidden.extend(SURFACE_VARIANTS[revoked])
        updated["must_avoid"] = list(dict.fromkeys(forbidden))
    elif explicit_request_m25.get("authoritative"):
        if semantic_template_authorized:
            updated["core_message_jp"] = str(selected.get("core_message_jp") or "").strip()
        else:
            updated["core_message_jp"] = original_core
        updated["reply_goal"] = (
            "使用者が今この返され方を明示したため、分析を見せず自然にその形式を実行する："
            f"{selected['instruction']}"
        )
        updated["response_mode"] = response_modes[policy_id]
        forbidden = list(updated.get("must_avoid") or [])
        for negated_policy in explicit_request_m25.get("negated_policies") or []:
            forbidden.extend(SURFACE_VARIANTS.get(negated_policy) or [])
        updated["must_avoid"] = list(dict.fromkeys(forbidden))
    elif correction_must_surface and str(updated.get("core_message_jp") or "").strip():
        original_core = str(updated.get("core_message_jp") or "").strip()
        policy_core = str(selected.get("core_message_jp") or "").strip()
        if semantic_template_authorized and policy_core and policy_core not in original_core:
            updated["core_message_jp"] = f"{original_core} {policy_core}"
        updated["reply_goal"] = f"先承認上一輪誤解，再依修正後需求回應：{selected['instruction']}"
    else:
        updated["core_message_jp"] = (
            selected["core_message_jp"]
            if semantic_template_authorized
            else original_core
        )
        updated["reply_goal"] = selected["instruction"]
        updated["response_mode"] = response_modes[policy_id]
    final_core = str(updated.get("core_message_jp") or "").strip()
    semantic_commit_m48 = {
        "schema": CURRENT_TURN_SEMANTIC_COMMIT_SCHEMA_M48,
        "status": (
            "policy_semantic_template_authorized_in_domain"
            if scope_domain == policy_semantic_domain
            else "policy_semantic_template_authorized_by_current_turn"
            if current_turn_surface_authority
            else "policy_semantic_template_fallback_no_existing_core"
            if not original_core
            else "current_turn_semantics_preserved_cross_domain"
        ),
        "scope_domain": scope_domain,
        "policy_semantic_domain": policy_semantic_domain,
        "selected_policy": policy_id,
        "current_turn_surface_authority": current_turn_surface_authority,
        "semantic_template_authorized": semantic_template_authorized,
        "current_turn_semantics_preserved": bool(
            original_core and final_core == original_core
        ),
        "semantic_core_changed": final_core != original_core,
        "original_core_digest": _digest(original_core) if original_core else None,
        "final_core_digest": _digest(final_core) if final_core else None,
        "policy_reference_digest": _digest(selected.get("core_message_jp") or ""),
        "claim_boundary": (
            "response policy may shape interaction style, but its arousal-domain "
            "example sentence cannot replace current-turn semantics in another domain "
            "without current-turn explicit authority"
        ),
        "raw_dialogue_persisted": False,
    }
    updated["current_turn_semantic_commit_m48"] = semantic_commit_m48
    updated["desired_response_policy_m16"] = policy_id
    updated["desired_response_decision_m16"] = deepcopy(decision)
    updated["desired_response_policy_m17"] = policy_id
    updated["desired_response_decision_m17"] = deepcopy(decision)
    updated["desired_response_policy_m18"] = policy_id
    updated["desired_response_decision_m18"] = deepcopy(decision)
    updated["response_dimensions_m18"] = deepcopy(
        selected.get("response_dimensions") or {}
    )
    updated["composable_japanese_realization_m18"] = deepcopy(
        selected.get("realization") or {}
    )
    updated["adaptive_person_model_m16"] = {
        "applied": True,
        "reason": (
            "desired_response_prediction_authorized_plan_content"
            if semantic_template_authorized
            else "desired_response_policy_applied_without_cross_domain_semantic_override"
        ),
        "policy_id": policy_id,
        "prediction_id": decision.get("prediction_id"),
        "utility_margin": decision.get("utility_margin"),
        "correction_acknowledgement_preserved": correction_must_surface,
        "current_turn_semantic_commit_m48": deepcopy(semantic_commit_m48),
    }
    updated["adaptive_person_model_m17"] = deepcopy(
        updated["adaptive_person_model_m16"]
    )
    updated["adaptive_person_model_m18"] = deepcopy(
        updated["adaptive_person_model_m16"]
    )
    updated["correction_aware_surface_m20"] = correction_directive
    updated["explicit_desired_response_m25"] = explicit_request_m25
    return updated, updated["adaptive_person_model_m16"]


def apply_feedback_topic_transition_m28(plan, contract):
    """Give a typed current-turn transition priority over stale uncertainty."""
    updated = deepcopy(plan or {})
    transition = deepcopy(contract or {})
    if transition.get("schema") != FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28:
        transition = {
            "schema": FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28,
            "status": "not_applied",
            "reason": "feedback_topic_transition_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    protected_reason = None
    if str(updated.get("intent") or "") in PROTECTED_INTENTS:
        protected_reason = "protected_current_intent"
    elif str(updated.get("scene") or "") in PROTECTED_SCENES:
        protected_reason = "protected_current_scene"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_contract"
    if protected_reason and transition.get("surface_authority"):
        transition.update(
            {
                "status": "protected_current_turn_retained",
                "reason": protected_reason,
                "surface_authority": False,
                "suppresses_new_pending_prediction": False,
            }
        )
    if not transition.get("surface_authority"):
        updated["feedback_topic_transition_m28"] = transition
        return updated, transition

    surface = str(transition.get("expected_surface_jp") or "").strip()
    status = str(transition.get("status") or "")
    if status == "pure_feedback_acknowledgement":
        updated.update(
            {
                "intent": "feedback_acknowledgement_m28",
                "scene": "casual",
                "reply_goal": "上一輪への確認だけを短く自然に受ける",
                "core_message_jp": surface,
                "response_mode": "direct_feedback_acknowledgement",
                "surface_act": "feedback_acknowledgement_m28",
            }
        )
    elif status == "current_topic_rebase":
        updated.update(
            {
                "intent": "current_topic_rebase_m28",
                "scene": "casual",
                "reply_goal": "前の不確実性を持ち越さず、今の字面内容に直接返す",
                "core_message_jp": surface,
                "response_mode": "direct_literal_topic_response",
                "surface_act": "current_topic_rebase_m28",
            }
        )
    mode_contract = deepcopy(updated.get("desired_response_mode_m23") or {})
    if mode_contract:
        mode_contract.update(
            {
                "eligible": False,
                "status": "suppressed_by_feedback_topic_transition_m28",
                "reason": "current_turn_transition_outranks_stale_desired_response_mode",
                "raw_dialogue_persisted": False,
            }
        )
        updated["desired_response_mode_m23"] = mode_contract
    transition["plan_applied"] = True
    transition["raw_dialogue_persisted"] = False
    updated["feedback_topic_transition_m28"] = transition
    return updated, transition


def ensure_feedback_topic_transition_m28_reaches_surface(reply, plan, enforce=True):
    """Commit or audit M28 after older adaptive surface contracts."""
    visible = str(reply or "").strip()
    plan = plan or {}
    contract = deepcopy(plan.get("feedback_topic_transition_m28") or {})
    if contract.get("schema") != FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28:
        contract = {
            "schema": FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28,
            "status": "not_applied",
            "reason": "feedback_topic_transition_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    expected = str(contract.get("expected_surface_jp") or "").strip()
    authoritative = bool(contract.get("surface_authority") and expected)
    before = visible
    if authoritative and enforce:
        visible = expected
    matched = bool(authoritative and visible == expected)
    contract.update(
        {
            "surface_status": (
                "matched" if matched else "mismatch" if authoritative else "not_applicable"
            ),
            "surface_changed": visible != before,
            "surface_reason": (
                "typed_transition_committed_to_visible_japanese"
                if authoritative and enforce
                else "typed_transition_visible"
                if matched
                else "typed_transition_missing"
                if authoritative
                else "transition_not_authoritative"
            ),
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract


def apply_literal_topic_projection_m29(plan, projection):
    """Apply only a validated M29 anchor projection to the response plan."""
    updated = deepcopy(plan or {})
    contract = deepcopy(projection or {})
    if contract.get("schema") != LITERAL_TOPIC_PROJECTION_SCHEMA_M29:
        contract = {
            "schema": LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
            "status": "not_applied",
            "reason": "literal_topic_projection_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    protected_reason = None
    if str(updated.get("intent") or "") in PROTECTED_INTENTS:
        protected_reason = "protected_current_intent"
    elif str(updated.get("scene") or "") in PROTECTED_SCENES:
        protected_reason = "protected_current_scene"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_contract"
    if protected_reason and contract.get("surface_authority"):
        contract.update(
            {
                "status": "protected_current_turn_retained",
                "reason": protected_reason,
                "surface_authority": False,
                "suppresses_new_pending_prediction": False,
            }
        )
    if not contract.get("surface_authority"):
        updated["literal_topic_projection_m29"] = contract
        return updated, contract

    response_jp = str(contract.get("response_jp") or "").strip()
    updated.update(
        {
            "intent": "grounded_literal_topic_m29",
            "scene": "casual",
            "reply_goal": "現在の字面内容を検証済み日本語 anchor で直接受ける",
            "core_message_jp": response_jp,
            "jp_summary": str(contract.get("literal_summary_jp") or "").strip(),
            "response_mode": "grounded_literal_topic_response",
            "surface_act": "grounded_literal_topic_m29",
        }
    )
    mode_contract = deepcopy(updated.get("desired_response_mode_m23") or {})
    if mode_contract:
        mode_contract.update(
            {
                "eligible": False,
                "status": "suppressed_by_literal_topic_projection_m29",
                "reason": "validated_current_literal_projection_outranks_stale_desired_response_mode",
                "raw_dialogue_persisted": False,
            }
        )
        updated["desired_response_mode_m23"] = mode_contract
    contract["plan_applied"] = True
    contract["suppresses_new_pending_prediction"] = True
    contract["raw_dialogue_persisted"] = False
    updated["literal_topic_projection_m29"] = contract
    return updated, contract


def ensure_literal_topic_projection_m29_reaches_surface(reply, plan, enforce=True):
    """Commit or audit the validated Japanese projection at the final boundary."""
    visible = str(reply or "").strip()
    plan = plan or {}
    contract = deepcopy(plan.get("literal_topic_projection_m29") or {})
    if contract.get("schema") != LITERAL_TOPIC_PROJECTION_SCHEMA_M29:
        contract = {
            "schema": LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
            "status": "not_applied",
            "reason": "literal_topic_projection_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    expected = str(contract.get("response_jp") or "").strip()
    authoritative = bool(contract.get("surface_authority") and expected)
    before = visible
    if authoritative and enforce:
        visible = expected
    anchors = [
        str(value or "").strip()
        for value in (contract.get("surface_anchors_jp") or [])
        if str(value or "").strip()
    ]
    matched = bool(authoritative and visible == expected)
    anchors_visible = [anchor for anchor in anchors if anchor in visible]
    contract.update(
        {
            "surface_status": (
                "matched" if matched else "mismatch" if authoritative else "not_applicable"
            ),
            "surface_changed": visible != before,
            "surface_anchor_count": len(anchors),
            "visible_anchor_count": len(anchors_visible),
            "surface_anchor_status": (
                "matched" if anchors and anchors_visible else "not_applicable" if not authoritative else "mismatch"
            ),
            "surface_reason": (
                "validated_literal_projection_committed_to_visible_japanese"
                if authoritative and enforce
                else "validated_literal_projection_visible"
                if matched
                else "validated_literal_projection_missing"
                if authoritative
                else "projection_not_authoritative"
            ),
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract


def apply_semantic_authorization_m31(plan, authorization):
    """Allow only a semantically authorized literal projection to own surface."""
    updated = deepcopy(plan or {})
    contract = deepcopy(authorization or {})
    if contract.get("schema") != SEMANTIC_AUTHORIZATION_SCHEMA_M31:
        contract = {
            "schema": SEMANTIC_AUTHORIZATION_SCHEMA_M31,
            "status": "not_applied",
            "reason": "semantic_authorization_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    protected_reason = None
    if str(updated.get("intent") or "") in PROTECTED_INTENTS:
        protected_reason = "protected_current_intent"
    elif str(updated.get("scene") or "") in PROTECTED_SCENES:
        protected_reason = "protected_current_scene"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_contract"
    if protected_reason and contract.get("surface_authority"):
        contract.update(
            {
                "status": "protected_current_turn_retained",
                "reason": protected_reason,
                "surface_authority": False,
                "suppresses_new_pending_prediction": False,
            }
        )
    if not contract.get("surface_authority"):
        updated["semantic_authorization_m31"] = contract
        return updated, contract

    response_jp = str(contract.get("response_jp") or "").strip()
    updated.update(
        {
            "intent": "semantically_authorized_literal_topic_m31",
            "scene": "casual",
            "reply_goal": "意味検証済みの現在話題だけに直接返す",
            "core_message_jp": response_jp,
            "jp_summary": str(contract.get("literal_summary_jp") or "").strip(),
            "response_mode": "semantically_authorized_literal_topic_response",
            "surface_act": "semantically_authorized_literal_topic_m31",
        }
    )
    m29_contract = deepcopy(updated.get("literal_topic_projection_m29") or {})
    if m29_contract:
        m29_contract.update(
            {
                "surface_authority": False,
                "status": "superseded_by_semantic_authorization_m31",
                "reason": "m31_is_final_literal_surface_authority",
                "raw_dialogue_persisted": False,
            }
        )
        updated["literal_topic_projection_m29"] = m29_contract
    mode_contract = deepcopy(updated.get("desired_response_mode_m23") or {})
    if mode_contract:
        mode_contract.update(
            {
                "eligible": False,
                "status": "suppressed_by_semantic_authorization_m31",
                "reason": "verified_current_literal_semantics_outrank_stale_desired_response_mode",
                "raw_dialogue_persisted": False,
            }
        )
        updated["desired_response_mode_m23"] = mode_contract
    contract["plan_applied"] = True
    contract["suppresses_new_pending_prediction"] = True
    contract["raw_dialogue_persisted"] = False
    updated["semantic_authorization_m31"] = contract
    return updated, contract


def ensure_semantic_authorization_m31_reaches_surface(reply, plan, enforce=True):
    """Commit or audit M31 after every older visible-surface contract."""
    visible = str(reply or "").strip()
    plan = plan or {}
    contract = deepcopy(plan.get("semantic_authorization_m31") or {})
    if contract.get("schema") != SEMANTIC_AUTHORIZATION_SCHEMA_M31:
        contract = {
            "schema": SEMANTIC_AUTHORIZATION_SCHEMA_M31,
            "status": "not_applied",
            "reason": "semantic_authorization_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    expected = str(contract.get("response_jp") or "").strip()
    authoritative = bool(contract.get("surface_authority") and expected)
    before = visible
    if authoritative and enforce:
        visible = expected
    anchors = [
        str(value or "").strip()
        for value in (contract.get("surface_anchors_jp") or [])
        if str(value or "").strip()
    ]
    matched = bool(authoritative and visible == expected)
    visible_anchors = [anchor for anchor in anchors if anchor in visible]
    contract.update(
        {
            "surface_status": (
                "matched" if matched else "mismatch" if authoritative else "not_applicable"
            ),
            "surface_changed": visible != before,
            "surface_anchor_count": len(anchors),
            "visible_anchor_count": len(visible_anchors),
            "surface_anchor_status": (
                "matched"
                if authoritative and len(visible_anchors) == len(anchors) and anchors
                else "mismatch"
                if authoritative
                else "not_applicable"
            ),
            "surface_reason": (
                "semantically_authorized_surface_committed"
                if authoritative and enforce
                else "semantically_authorized_surface_visible"
                if matched
                else "semantic_surface_missing"
                if authoritative
                else "semantic_authorization_not_authoritative"
            ),
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract


def build_deterministic_semantic_commit_m32(authorization):
    """Commit complete M31 canonical meaning without inventing new semantics.

    M32 covers two bounded realization failures: M31 may reject an otherwise
    complete canonical parse because its casual surface failed a presentation
    check, or M31 may authorize a short surface that its own semantic
    self-check says dropped the subject/predicate/relation.  In both cases M32
    is allowed to use only M31's canonical fields; it does not call another
    model or reinterpret the source turn.
    """
    source = deepcopy(authorization or {})
    contract = {
        "schema": SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
        "status": "not_applicable",
        "reason": "m31_surface_repair_not_required",
        "surface_authority": False,
        "source_m31_status": source.get("status") or "missing",
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "claim_boundary": (
            "deterministic commit of M31 canonical fields; not a new semantic "
            "inference or translation certification"
        ),
    }
    source_self_checks = deepcopy(source.get("surface_self_checks") or {})
    critical_surface_checks = (
        "safe_response_semantics_faithful",
        "subject_preserved",
        "predicate_preserved",
        "time_quantity_relation_preserved",
        "polarity_preserved",
    )
    failed_surface_checks = [
        name
        for name in critical_surface_checks
        if source_self_checks.get(name) is False
    ]
    authoritative_but_undercommitted = bool(
        source.get("surface_authority") and failed_surface_checks
    )
    if source.get("surface_authority") and not authoritative_but_undercommitted:
        contract["reason"] = "m31_authoritative_surface_complete"
        return None, contract

    candidate = deepcopy(source.get("m32_repair_candidate") or {})
    if authoritative_but_undercommitted:
        candidate = {
            "schema": "uruha_semantic_commit_repair_candidate_m32",
            "canonical_ready": bool(
                str(source.get("subject_jp") or "").strip()
                and str(source.get("predicate_jp") or "").strip()
                and str(source.get("literal_summary_jp") or "").strip()
            ),
            "subject_jp": str(source.get("subject_jp") or "").strip()[:48],
            "predicate_jp": str(source.get("predicate_jp") or "").strip()[:48],
            "time_jp": str(source.get("time_jp") or "").strip()[:48],
            "polarity": str(source.get("polarity") or "unknown"),
            "literal_summary_jp": str(
                source.get("literal_summary_jp") or ""
            ).strip()[:120],
            "failed_authorization_checks": [
                f"surface_self_check:{name}" for name in failed_surface_checks
            ],
            "raw_dialogue_persisted": False,
            "model_response_raw_persisted": False,
        }
    if not candidate.get("canonical_ready"):
        contract.update(
            {
                "status": "repair_rejected",
                "reason": "canonical_semantic_fields_not_ready",
                "rejection_checks_m31": list(
                    candidate.get("failed_authorization_checks") or []
                ),
            }
        )
        return None, contract

    subject = str(candidate.get("subject_jp") or "").strip()
    predicate = str(candidate.get("predicate_jp") or "").strip()
    time_relation = str(candidate.get("time_jp") or "").strip()
    summary = str(candidate.get("literal_summary_jp") or "").strip()
    polarity = str(candidate.get("polarity") or "unknown")

    def casualize_proposition(value):
        text = str(value or "").strip().rstrip("。！？!?")
        replacements = (
            ("されました", "された"),
            ("しました", "した"),
            ("でした", "だった"),
            ("来ます", "来る"),
            ("行きます", "行く"),
            ("あります", "ある"),
            ("います", "いる"),
            ("します", "する"),
            ("です", "だ"),
        )
        for before, after in replacements:
            text = text.replace(before, after)
        return text.strip()

    proposition = casualize_proposition(summary)
    polite_remaining = bool(
        re.search(r"(?:です|ます|ください|なさい|しましょう|ございます)", proposition)
    )
    if proposition.endswith(("だ", "だった")):
        response = f"{proposition}ね。"
    else:
        response = f"{proposition}んだね。"
    japanese_present = bool(re.search(r"[ぁ-んァ-ヶー一-龠]", response))
    semantic_fields = [subject, time_relation, predicate]
    anchors = []
    for field in semantic_fields:
        if field and field in proposition and field not in anchors:
            anchors.append(field)
    if subject and subject not in anchors:
        subject_tokens = re.findall(r"[ァ-ヶーぁ-ん一-龠A-Za-z0-9]{2,}", subject)
        anchors.extend(
            token
            for token in subject_tokens
            if token in proposition and token not in anchors
        )
    anchors = anchors[:4]
    commit_checks = {
        "canonical_subject_present": bool(subject),
        "canonical_predicate_present": bool(predicate),
        "canonical_summary_present": bool(proposition),
        "polarity_canonical": polarity in {"affirmed", "negated", "unknown"},
        "casual_register_only": not polite_remaining,
        "japanese_surface_present": japanese_present,
        "at_least_two_grounded_anchors": len(anchors) >= 2,
        "all_anchors_visible": bool(anchors)
        and all(anchor in response for anchor in anchors),
        "unsupported_addition_absent": True,
    }
    if not all(commit_checks.values()):
        contract.update(
            {
                "status": "repair_rejected",
                "reason": "deterministic_commit_checks_failed",
                "commit_checks": commit_checks,
                "rejection_checks_m31": list(
                    candidate.get("failed_authorization_checks") or []
                ),
            }
        )
        return None, contract

    contract.update(
        {
            "status": "deterministic_commit_repaired",
            "reason": "canonical_m31_semantics_committed_with_casual_surface_m32",
            "surface_authority": True,
            "repair_kind": (
                "authoritative_surface_completeness_override"
                if authoritative_but_undercommitted
                else "rejected_surface_realization_only"
            ),
            "source_m31_surface_authority": bool(source.get("surface_authority")),
            "subject_jp": subject[:48],
            "predicate_jp": predicate[:48],
            "time_jp": time_relation[:48],
            "polarity": polarity,
            "literal_summary_jp": proposition[:120],
            "response_jp": response[:160],
            "surface_anchors_jp": anchors,
            "visible_anchor_count": len(anchors),
            "commit_checks": commit_checks,
            "rejection_checks_m31": list(
                candidate.get("failed_authorization_checks") or []
            ),
            "suppresses_new_pending_prediction": True,
        }
    )
    plan = {
        "candidate_label": "m32_deterministic_semantic_commit",
        "intent": "deterministic_semantic_commit_m32",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "検証済みの意味を自然な表面に直して受け取っている",
        "reply_goal": "新しい意味を足さず canonical content を会話表面に届ける",
        "jp_summary": proposition[:120],
        "core_message_jp": response[:160],
        "cognitive_mode": "direct",
        "response_mode": "deterministic_semantic_commit_m32",
        "uncertainty": 0.12,
        "premise_check": "accept",
        "self_check": True,
        "surface_act": "deterministic_semantic_commit_m32",
        "payload_level": "low",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 120,
            "casual_japanese_only": True,
            "forbid_polite": True,
        },
        "semantic_commit_repair_m32": deepcopy(contract),
    }
    return plan, contract


def apply_semantic_commit_repair_m32(plan, repair):
    """Apply M32 after M31 only when protected contracts do not own the turn."""
    updated = deepcopy(plan or {})
    contract = deepcopy(repair or {})
    if contract.get("schema") != SEMANTIC_COMMIT_REPAIR_SCHEMA_M32:
        contract = {
            "schema": SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
            "status": "not_applied",
            "reason": "semantic_commit_repair_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    protected_reason = None
    if str(updated.get("intent") or "") in PROTECTED_INTENTS:
        protected_reason = "protected_current_intent"
    elif str(updated.get("scene") or "") in PROTECTED_SCENES:
        protected_reason = "protected_current_scene"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_contract"
    if protected_reason and contract.get("surface_authority"):
        contract.update(
            {
                "status": "protected_current_turn_retained",
                "reason": protected_reason,
                "surface_authority": False,
                "suppresses_new_pending_prediction": False,
            }
        )
    if not contract.get("surface_authority"):
        updated["semantic_commit_repair_m32"] = contract
        return updated, contract

    updated.update(
        {
            "intent": "deterministic_semantic_commit_m32",
            "scene": "casual",
            "reply_goal": "M31 canonical meaning を deterministic casual surface で届ける",
            "core_message_jp": str(contract.get("response_jp") or "").strip(),
            "jp_summary": str(contract.get("literal_summary_jp") or "").strip(),
            "response_mode": "deterministic_semantic_commit_m32",
            "surface_act": "deterministic_semantic_commit_m32",
        }
    )
    contract["plan_applied"] = True
    contract["suppresses_new_pending_prediction"] = True
    contract["raw_dialogue_persisted"] = False
    updated["semantic_commit_repair_m32"] = contract
    return updated, contract


def ensure_semantic_commit_repair_m32_reaches_surface(reply, plan, enforce=True):
    """Commit or audit the deterministic M32 surface after M31."""
    visible = str(reply or "").strip()
    contract = deepcopy((plan or {}).get("semantic_commit_repair_m32") or {})
    if contract.get("schema") != SEMANTIC_COMMIT_REPAIR_SCHEMA_M32:
        contract = {
            "schema": SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
            "status": "not_applied",
            "reason": "semantic_commit_repair_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    expected = str(contract.get("response_jp") or "").strip()
    authoritative = bool(contract.get("surface_authority") and expected)
    before = visible
    if authoritative and enforce:
        visible = expected
    anchors = [
        str(value or "").strip()
        for value in (contract.get("surface_anchors_jp") or [])
        if str(value or "").strip()
    ]
    visible_anchors = [anchor for anchor in anchors if anchor in visible]
    matched = bool(authoritative and visible == expected)
    contract.update(
        {
            "surface_status": (
                "matched" if matched else "mismatch" if authoritative else "not_applicable"
            ),
            "surface_changed": visible != before,
            "surface_anchor_count": len(anchors),
            "visible_anchor_count": len(visible_anchors),
            "surface_anchor_status": (
                "matched"
                if authoritative and anchors and len(visible_anchors) == len(anchors)
                else "mismatch"
                if authoritative
                else "not_applicable"
            ),
            "surface_reason": (
                "deterministic_semantic_commit_visible"
                if matched
                else "deterministic_semantic_commit_missing"
                if authoritative
                else "semantic_commit_repair_not_authoritative"
            ),
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract


def ensure_decision_reaches_visible_surface(reply, plan):
    """Keep an explicit correction from swallowing the newly selected action.

    The surface model is allowed to paraphrase ordinary plans.  A correction
    turn is stricter: acknowledging the mistake without performing the newly
    requested response would make the trace claim success while the user still
    receives the wrong interaction.  In that narrow case we promote the full,
    Japanese plan content to the final language guard.
    """
    visible = str(reply or "").strip()
    plan = plan or {}
    application = (
        plan.get("adaptive_person_model_m18")
        or plan.get("adaptive_person_model_m17")
        or plan.get("adaptive_person_model_m16")
        or {}
    )
    decision = (
        plan.get("desired_response_decision_m18")
        or plan.get("desired_response_decision_m17")
        or plan.get("desired_response_decision_m16")
        or {}
    )
    selected = decision.get("selected") or {}
    policy_core = str(selected.get("core_message_jp") or "").strip()
    planned_core = str(plan.get("core_message_jp") or "").strip()
    decision_state = decision.get("state") or {}
    activation_reasons = set(decision_state.get("activation_reasons") or [])
    correction_directive = deepcopy(
        plan.get("correction_aware_surface_m20")
        or decision.get("correction_aware_surface_m20")
        or {}
    )
    explicit_or_verified_preference = bool(
        "explicit_current_turn_desired_response_or_state_cue" in activation_reasons
        or "persisted_interaction_prior_available" in activation_reasons
        or "ambiguous_arousal_with_learned_response_preference" in activation_reasons
        or "hierarchical_interaction_prior_available" in activation_reasons
    )
    correction_required = bool(
        application.get("applied")
        and (
            application.get("correction_acknowledgement_preserved")
            or correction_directive.get("authoritative")
        )
        and policy_core
    )
    policy_commitment_required = bool(
        application.get("applied")
        and policy_core
        and explicit_or_verified_preference
    )
    policy_performed = bool(policy_core and policy_core in visible)
    changed = False
    reason = "ordinary_surface_paraphrase_allowed"
    forbidden_repeated = [
        value
        for value in (plan.get("must_avoid") or [])
        if value and str(value) in visible
    ]
    if correction_required and planned_core:
        visible = planned_core
        changed = visible != str(reply or "").strip()
        reason = "explicit_correction_surface_is_authoritative"
        policy_performed = policy_core in visible
    elif policy_commitment_required and not policy_performed and planned_core:
        visible = planned_core
        changed = True
        reason = (
            "correction_acknowledgement_was_missing_selected_action"
            if correction_required
            else "explicit_or_verified_response_preference_missing_from_surface"
        )
        policy_performed = policy_core in visible
    return visible, {
        "schema": "uruha_adaptive_person_surface_commitment_m18",
        "applied": bool(application.get("applied")),
        "policy_id": selected.get("policy_id"),
        "correction_required": correction_required,
        "policy_commitment_required": policy_commitment_required,
        "explicit_or_verified_preference": explicit_or_verified_preference,
        "policy_performed": policy_performed,
        "changed": changed,
        "reason": reason,
        "correction_aware_surface_m20": {
            **correction_directive,
            "forbidden_repetition_detected": bool(forbidden_repeated),
            "forbidden_repetition_count": len(forbidden_repeated),
            "final_policy_performed": policy_performed,
            "raw_dialogue_persisted": False,
        },
        "raw_dialogue_persisted": False,
    }


def build_desired_response_mode_contract(task_shape, state, decision):
    """Expose the response mode that an emotional turn is allowed to perform.

    M18 ranks bounded response policies. M23 turns that ranking into an
    auditable user-facing contract: the chosen mode must reach the visible
    Japanese reply, while alternatives and uncertainty remain internal trace
    evidence. This is an operational prediction of the wanted response form,
    not a claim about the user's private mental state.
    """
    task_shape = deepcopy(task_shape or {})
    state = deepcopy(state or {})
    decision = deepcopy(decision or {})
    selected = deepcopy(decision.get("selected") or {})
    selected_policy = str(selected.get("policy_id") or "")
    selected_mode = POLICY_TO_RESPONSE_MODE_M23.get(selected_policy)
    selected_type = str(task_shape.get("selected_type") or "")
    interaction_kind = str((state.get("context_scope") or {}).get("interaction_kind") or "")
    explicit_request_m25 = deepcopy(
        decision.get("explicit_desired_response_m25")
        or state.get("explicit_desired_response_m25")
        or {}
    )
    eligible = bool(
        selected_mode
        and (
            selected_type in {"emotional_bid", "explicit_correction"}
            or interaction_kind == "emotional_bid"
            or explicit_request_m25.get("authoritative")
        )
    )
    activation_reasons = set(state.get("activation_reasons") or [])
    correction = deepcopy(
        decision.get("correction_aware_surface_m20")
        or state.get("correction_directive_m20")
        or {}
    )
    learned_atoms = list(state.get("learned_atoms_used") or [])
    if correction.get("authoritative"):
        authority = "current_explicit_correction"
    elif explicit_request_m25.get("authoritative"):
        authority = "current_explicit_request"
    elif "explicit_current_turn_desired_response_or_state_cue" in activation_reasons:
        authority = "current_explicit_request"
    elif learned_atoms:
        authority = "verified_reversible_preference"
    elif selected_policy == "calibrate_need":
        authority = "uncertainty_guarded_clarification"
    else:
        authority = "bounded_pragmatic_inference"

    uncertainty_atom = deepcopy((state.get("atoms") or {}).get("uncertainty") or {})
    uncertainty = round(float(uncertainty_atom.get("value") or 0.0), 4)
    uncertainty_band = "high" if uncertainty >= 0.72 else "medium" if uncertainty >= 0.40 else "low"
    evidence = []
    atoms = state.get("atoms") or {}
    for atom_name in MODE_EVIDENCE_ATOMS_M23.get(selected_mode, ("uncertainty",)):
        atom = deepcopy(atoms.get(atom_name) or {})
        evidence.append(
            {
                "atom": atom_name,
                "value": round(float(atom.get("value") or 0.0), 4),
                "confidence": round(float(atom.get("confidence") or 0.0), 4),
                "status": atom.get("status") or "unknown",
                "evidence_kind": atom.get("evidence") or "unavailable",
            }
        )
    candidates = []
    for rank, candidate in enumerate(decision.get("candidates") or [], start=1):
        policy_id = str(candidate.get("policy_id") or "")
        mode = POLICY_TO_RESPONSE_MODE_M23.get(policy_id)
        if not mode:
            continue
        candidates.append(
            {
                "rank": rank,
                "mode": mode,
                "policy_id": policy_id,
                "expected_utility": round(float(candidate.get("expected_utility") or 0.0), 4),
                "learned_reliability": round(float(candidate.get("learned_reliability") or 0.5), 4),
            }
        )
    runner_up_policy = str((decision.get("runner_up") or {}).get("policy_id") or "")
    uncertainty_guard_passed = bool(
        uncertainty_band != "high"
        or authority in {"current_explicit_correction", "current_explicit_request", "verified_reversible_preference"}
        or selected_mode == "low_pressure_clarification"
    )
    return {
        "schema": DESIRED_RESPONSE_MODE_SCHEMA,
        "eligible": eligible,
        "status": "selected" if eligible else "not_applied",
        "reason": (
            "explicit_or_emotional_turn_has_bounded_response_mode"
            if eligible
            else "task_shape_does_not_authorize_desired_response_mode_surface"
        ),
        "task_type": selected_type or "unknown",
        "selected_mode": selected_mode if eligible else None,
        "selected_policy": selected_policy if eligible else None,
        "runner_up_mode": POLICY_TO_RESPONSE_MODE_M23.get(runner_up_policy) if eligible else None,
        "utility_margin": decision.get("utility_margin") if eligible else None,
        "authority": authority if eligible else "not_applicable",
        "uncertainty": uncertainty,
        "uncertainty_band": uncertainty_band,
        "uncertainty_guard_passed": uncertainty_guard_passed if eligible else True,
        "evidence": evidence if eligible else [],
        "alternatives": candidates if eligible else [],
        "learned_atoms_used": learned_atoms if eligible else [],
        "revoked_previous_policy": correction.get("revoked_previous_policy") if eligible else None,
        "explicit_desired_response_m25": explicit_request_m25 if eligible else {},
        "surface_required": eligible,
        "surface_status": "pending" if eligible else "not_applicable",
        "claim_boundary": "operational desired-response-form prediction; not mind reading",
        "raw_dialogue_persisted": False,
    }


def ensure_desired_response_mode_reaches_surface(reply, plan, enforce=True):
    """Commit or audit the M23 mode against the actual visible Japanese reply."""
    visible = str(reply or "").strip()
    plan = plan or {}
    contract = deepcopy(plan.get("desired_response_mode_m23") or {})
    if contract.get("schema") != DESIRED_RESPONSE_MODE_SCHEMA:
        contract = {
            "schema": DESIRED_RESPONSE_MODE_SCHEMA,
            "eligible": False,
            "status": "not_applied",
            "reason": "desired_response_mode_contract_missing",
            "raw_dialogue_persisted": False,
        }
    decision = (
        plan.get("desired_response_decision_m18")
        or plan.get("desired_response_decision_m17")
        or plan.get("desired_response_decision_m16")
        or {}
    )
    selected = decision.get("selected") or {}
    selected_policy = str(contract.get("selected_policy") or selected.get("policy_id") or "")
    selected_mode = contract.get("selected_mode") or POLICY_TO_RESPONSE_MODE_M23.get(selected_policy)
    policy_core = str(selected.get("core_message_jp") or "").strip()
    planned_core = str(plan.get("core_message_jp") or policy_core).strip()
    eligible = bool(contract.get("eligible") and selected_mode and planned_core)
    before = visible
    performed = bool(policy_core and policy_core in visible)
    changed = False
    reason = "mode_not_authorized_for_surface"
    if eligible and not contract.get("uncertainty_guard_passed", True):
        reason = "uncertainty_guard_failed_surface_not_committed"
    elif eligible and enforce and not performed:
        visible = planned_core
        changed = visible != before
        performed = bool(policy_core and policy_core in visible)
        reason = "selected_desired_response_mode_committed_to_visible_surface"
    elif eligible:
        reason = (
            "selected_desired_response_mode_visible"
            if performed
            else "selected_desired_response_mode_missing_after_surface_guard"
        )
    contract.update(
        {
            "performed_mode": selected_mode if performed else None,
            "performed_policy": selected_policy if performed else None,
            "surface_status": (
                "matched" if performed else "mismatch" if eligible else "not_applicable"
            ),
            "surface_changed": changed,
            "surface_reason": reason,
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract


def audit_explicit_desired_response_surface_m25(reply, plan):
    """Verify the M25 current-turn authority against the final visible reply."""
    visible = str(reply or "").strip()
    plan = plan or {}
    contract = deepcopy(plan.get("explicit_desired_response_m25") or {})
    if contract.get("schema") != EXPLICIT_DESIRED_RESPONSE_SCHEMA_M25:
        return {
            "schema": EXPLICIT_DESIRED_RESPONSE_SCHEMA_M25,
            "detected": False,
            "status": "not_detected",
            "surface_status": "not_applicable",
            "raw_dialogue_persisted": False,
        }
    decision = (
        plan.get("desired_response_decision_m18")
        or plan.get("desired_response_decision_m17")
        or plan.get("desired_response_decision_m16")
        or {}
    )
    selected = decision.get("selected") or {}
    policy_core = str(selected.get("core_message_jp") or "").strip()
    performed = bool(policy_core and policy_core in visible)
    authoritative = bool(contract.get("authoritative"))
    contract.update(
        {
            "performed_policy": selected.get("policy_id") if authoritative and performed else None,
            "performed_mode": POLICY_TO_RESPONSE_MODE_M23.get(selected.get("policy_id")) if authoritative and performed else None,
            "surface_status": (
                "matched"
                if authoritative and performed
                else "mismatch"
                if authoritative
                else "not_applicable"
            ),
            "surface_reason": (
                "current_explicit_response_form_reached_final_japanese"
                if authoritative and performed
                else "current_explicit_response_form_missing_from_final_surface"
                if authoritative
                else "explicit_response_authority_not_applicable_or_protected"
            ),
            "raw_dialogue_persisted": False,
        }
    )
    return contract


def set_pending_prediction(model, decision, turn_index=0):
    state = _normalise_model(model)
    selected = (decision or {}).get("selected") or {}
    if not selected:
        state["pending_prediction"] = None
        state["outcome_calibration_summary_m27"] = (
            build_causal_outcome_calibration_summary_m27(state)
        )
        return state
    decision_state = decision.get("state") or {}
    context_scope = _normalise_scope(
        decision_state.get("context_scope") or decision.get("context_scope")
    )
    causal_scope_ids = [context_scope["scope_id"]]
    feedback_origin_scope_id = str(
        decision_state.get("feedback_origin_scope_id") or ""
    ).strip()
    if feedback_origin_scope_id:
        causal_scope_ids.append(feedback_origin_scope_id)
    for row in ((decision_state.get("scope_match") or {}).get("used") or []):
        source_scope_id = str(row.get("source_scope_id") or "").strip()
        if source_scope_id:
            causal_scope_ids.append(source_scope_id)
    state["pending_prediction"] = {
        "prediction_id": decision.get("prediction_id"),
        "policy_id": selected.get("policy_id"),
        "expected_utility": selected.get("expected_utility"),
        "utility_margin": decision.get("utility_margin"),
        "turn_index": int(turn_index),
        "input_digest": ((decision.get("state") or {}).get("input_digest")),
        "context_scope": context_scope,
        "causal_scope_ids": list(dict.fromkeys(causal_scope_ids))[:8],
        "response_dimensions": deepcopy(selected.get("response_dimensions") or {}),
        "realization": deepcopy(selected.get("realization") or {}),
        "implicit_response_m26": {
            key: deepcopy(
                ((decision or {}).get("implicit_desired_response_m26") or {}).get(
                    key
                )
            )
            for key in (
                "status",
                "implicit_top_policy",
                "implicit_top_mode",
                "top_probability",
                "probability_margin",
                "evidence_quality",
            )
        },
        "trigger_relation_candidate_m37": (
            _normalise_trigger_relation_candidate_m37(
                decision_state.get("trigger_relation_candidate_m37") or {}
            )
        ),
        "raw_dialogue_persisted": False,
    }
    state["last_turn"] = int(turn_index)
    return _upsert_m27_pending_prediction(state, state["pending_prediction"])
