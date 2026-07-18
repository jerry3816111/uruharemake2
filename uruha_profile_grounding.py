"""Typed profile evidence to speech-plan bridge.

The bridge is inert unless a caller supplies an explicit shadow request. It
contains only generic profile relations and no benchmark cases or answers.
"""

from __future__ import annotations

from copy import deepcopy


SCHEMA = "uruha_profile_grounding_shadow_v1"
MODES = {"value_only", "value_relation"}
RELATION_BY_FACT_TYPE = {
    "name": "preferred_name",
    "like": "likes",
    "dislike": "dislikes",
    "favorite": "favorite",
}
RELATION_MARKERS = {
    "preferred_name": (),
    "likes": ("好き", "気に入", "好み"),
    "dislikes": ("苦手", "嫌い", "好きじゃない", "無理"),
    "favorite": ("一番好き", "本命", "好き"),
}
STRUCTURAL_SURFACES = (
    "FactType=",
    "Value=",
    "favorites=",
    "likes=",
    "dislikes=",
    "Name=",
)


def build_evidence_contract(selected_candidates, selection_status):
    """Build a small answerability contract from a selector result."""
    rows = list(selected_candidates or [])
    if selection_status == "selected" and len(rows) == 1:
        metadata = rows[0].get("metadata") or {}
        fact_type = str(metadata.get("fact_type") or "").casefold()
        value = str(metadata.get("value") or "").strip()
        relation = RELATION_BY_FACT_TYPE.get(fact_type)
        if relation and value:
            return {
                "answerability": "supported",
                "fact_type": fact_type,
                "value": value,
                "relation": relation,
            }
    if selection_status in {"requested_but_unavailable", "requested_but_ambiguous"}:
        answerability = "unsupported"
    else:
        answerability = "not_requested"
    return {
        "answerability": answerability,
        "fact_type": None,
        "value": None,
        "relation": None,
    }


def _relation_surface(relation, value):
    if relation == "preferred_name":
        return f"{value}って呼べばいい"
    if relation == "likes":
        return f"{value}が好き"
    if relation == "dislikes":
        return f"{value}は苦手"
    if relation == "favorite":
        return f"{value}が一番好き"
    return str(value)


def build_grounded_profile_logic(request):
    """Return a generic shadow speech plan, or ``None`` when not authorized."""
    request = request if isinstance(request, dict) else {}
    if request.get("schema") != SCHEMA or request.get("mode") not in MODES:
        return None
    evidence = deepcopy(request.get("evidence") or {})
    if evidence.get("answerability") != "supported":
        return None
    fact_type = str(evidence.get("fact_type") or "").casefold()
    value = str(evidence.get("value") or "").strip()
    expected_relation = RELATION_BY_FACT_TYPE.get(fact_type)
    if not value or not expected_relation:
        return None

    mode = request["mode"]
    include_relation = mode == "value_relation"
    relation = str(evidence.get("relation") or "") if include_relation else ""
    if include_relation and relation != expected_relation:
        return None

    core = _relation_surface(relation, value) if include_relation else f"{value}のことを具体的に答える"
    required_groups = [[value]]
    if include_relation and RELATION_MARKERS.get(relation):
        required_groups.append(list(RELATION_MARKERS[relation]))
    grounding_contract = {
        "answerability": "supported",
        "fact_type": fact_type,
        "value": value,
        "relation": relation or None,
    }
    anchor = {
        "kind": "profile_grounded",
        "fact_type": fact_type,
        "relation": relation or None,
        "value": value,
        "jp_anchor": value,
        "terms": [value],
        "source_text": value,
        "source": "typed_profile_evidence",
        "score": 1.0,
        "relevance": 1.0,
        "expected": True,
    }
    content_units = ["記憶の有無を正直に答える", core, "保存されていない内容は足さない"]
    speech_moves = [
        {"role": "answerability", "value": "supported"},
        {"role": "fact_value", "value": value},
    ]
    if include_relation:
        speech_moves.append({"role": "fact_relation", "value": relation})

    return {
        "intent": "profile_grounded_recall" if include_relation else "profile_value_recall",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "以前に伝えた自分の情報を覚えているか確認している",
        "reply_goal": "選ばれた記憶の範囲だけを短く答える",
        "jp_summary": "ユーザーが保存済みの自分の情報を確認している。",
        "core_message_jp": core,
        "stance": {"warmth": 0.24, "tease": 0.02, "blunt": 0.1, "jealousy": 0.0, "distance": 0.04},
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.04,
        "premise_check": "accept",
        "self_check": True,
        "subjective_note_jp": "選択済みの個人情報だけを使い、値と関係を取り違えない",
        "hidden_intent": "memory_probe",
        "surface_act": "plain_reply",
        "grounding": {"topic_terms": [value]},
        "payload_level": "low",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 1,
            "max_chars": 34,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "AI", "技術説明", *STRUCTURAL_SURFACES],
        "required_marker_groups": required_groups,
        "memory_anchor": anchor,
        "memory_relevance": 1.0,
        "memory_relevance_label": "high",
        "memory_speakability": "explicit_ok",
        "memory_speakability_reason": "explicit_profile_recall_shadow",
        "memory_gravity": 1.0,
        "memory_use_expected": True,
        "profile_evidence_contract": grounding_contract,
        "profile_grounding_shadow": {"schema": SCHEMA, "mode": mode},
        "human_speech_plan": {
            "dialogue_act": "memory_accounting",
            "content_units": content_units,
            "speech_moves": speech_moves,
            "style_operators": ["direct_spoken", "lazy_short"],
            "target_length": "1_or_2_short_sentences",
            "forbidden_repetition": {
                "recent_openings": [],
                "avoid_generic_frames": ["そうなんだ", "なるほど", "まあいいけど", "別にいいけど"],
                "avoid_same_refusal_strategy": False,
            },
            "turn_opening_potential": False,
            "prosody_hint": {
                "emotion": "casual",
                "speed": "normal",
                "energy": 0.5,
                "pause_after_first_unit": False,
            },
            "content_density_target": 0.28,
            "grounding_terms": [value],
        },
    }


def is_grounding_shadow(logic):
    shadow = (logic or {}).get("profile_grounding_shadow") or {}
    return shadow.get("schema") == SCHEMA and shadow.get("mode") in MODES
