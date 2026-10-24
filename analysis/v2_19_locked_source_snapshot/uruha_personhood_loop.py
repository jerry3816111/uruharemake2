"""V2.13 personhood-oriented cognitive loop for UruhaBrain.

This module is deliberately functional and auditable.  It connects a
longitudinal model of the other person to UruhaBrain's existing self state,
relationship state, public-persona stance, action choice, and learning from
later outcomes.  It does not claim consciousness, mind reading, human
equivalence, or a literal copy of a real person.
"""

from __future__ import annotations

import datetime
import hashlib
import re
from copy import deepcopy


LONGITUDINAL_SCHEMA = "uruha_longitudinal_other_model_v2_13"
PERSONHOOD_LOOP_SCHEMA = "uruha_personhood_oriented_cognitive_loop_v2_13"
CALIBRATION_SCHEMA = "uruha_typed_prediction_calibration_v2_13"
VALIDATION_SCHEMA = "uruha_active_validation_strategy_v2_13"
PRAGMATIC_SCHEMA = "uruha_human_pragmatic_understanding_v2_13"
PRAGMATIC_VERIFICATION_SCHEMA = "uruha_pragmatic_verification_v2_13"

LAYER_POLICIES = {
    "stable": {
        "label": "相對穩定偏好／溝通偏好",
        "grace_turns": 12,
        "decay_per_turn": 0.012,
        "stale_after_turns": 30,
        "expire_after_turns": 80,
    },
    "situational": {
        "label": "暫時情境／目標",
        "grace_turns": 1,
        "decay_per_turn": 0.09,
        "stale_after_turns": 3,
        "expire_after_turns": 5,
    },
    "provisional": {
        "label": "待驗證推測",
        "grace_turns": 0,
        "decay_per_turn": 0.08,
        "stale_after_turns": 2,
        "expire_after_turns": 4,
    },
}


def _clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(upper, float(value)))


def _timestamp(value=None):
    if value:
        return str(value)
    return datetime.datetime.now().astimezone().isoformat(timespec="microseconds")


def _normalize(value):
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _text_evidence(text, observed, interpretation, weight=1.0):
    return {
        "modality": "text",
        "source": "current_user_input",
        "observed": str(observed or text or ""),
        "interpretation": interpretation,
        "weight": float(weight),
        "epistemic_status": "known_observation",
    }


def _inference(value, confidence, evidence, alternatives):
    return {
        "value": value,
        "confidence": round(_clamp(confidence, 0.05, 0.96), 3),
        "epistemic_status": "provisional_inference",
        "evidence": deepcopy(evidence),
        "alternatives": [
            {
                "value": alternative_value,
                "confidence": round(_clamp(alternative_confidence), 3),
                "epistemic_status": "alternative_inference",
            }
            for alternative_value, alternative_confidence in alternatives
        ],
    }


def build_human_pragmatic_understanding(
    user_input,
    hypothesis=None,
    input_mode="text",
    acoustic_summary=None,
    turn_index=0,
):
    """Separate literal text from falsifiable pragmatic interpretations.

    Uruha is the expression/persona instance, but these pragmatic categories are
    intentionally generic and do not depend on Uruha-specific facts.
    """
    text = str(user_input or "").strip()
    lowered = text.lower()
    visible_hesitation = bool(re.search(r"(?:\.{2,}|…|、\s*$|えっと|その|ちょっと|嗯|呃|uh|um)", lowered))
    indirect_refusal = any(
        marker in lowered
        for marker in [
            "有點難", "有点难", "改天", "我再看看", "再說吧", "再说吧",
            "有點滿", "有点满", "排得很滿", "排得很满", "之後有機會再說", "之后有机会再说",
            "ちょっと難しい", "また今度", "考えとく", "検討しとく",
            "予定が詰まって", "都合がつか", "maybe another time", "i'll think about it",
            "not sure i can", "schedule is pretty full", "schedule is quite full",
        ]
    )
    reserved_agreement = any(
        marker in lowered
        for marker in [
            "好吧", "行吧", "可以是可以", "也不是不行", "まあいいけど",
            "いいけど", "いいんじゃない", "たぶん", "仕方ない", "sure, i guess",
            "fine, i guess", "if you say so", "okay, i suppose",
        ]
    )
    indirect_support_need = any(
        marker in lowered
        for marker in [
            "我沒事", "我没事", "沒什麼", "没什么", "不用管我", "大丈夫",
            "別に平気", "なんでもない", "i'm fine", "nothing's wrong", "don't worry about me",
            "don't need to worry about me", "no need to worry about me",
        ]
    )
    direct_correction = any(
        marker in lowered
        for marker in [
            "不是", "並不是", "并不是", "其實", "其实", "違う", "じゃなくて",
            "actually", "not what i meant", "you got it wrong",
        ]
    )
    explicit_excitement = any(
        marker in lowered
        for marker in ["興奮", "兴奋", "開心", "开心", "期待", "嬉しい", "楽しみ", "excited", "thrilled", "looking forward"]
    )
    hypothesis_features = set((hypothesis or {}).get("semantic_features") or [])
    ambiguous_arousal = "ambiguous_mood" in hypothesis_features and not explicit_excitement

    if indirect_refusal:
        label = "indirect_refusal"
        intent = "在降低關係摩擦的同時婉拒或延後承諾"
        emotion = "可能為難、保留或不想正面衝突"
        relation = "維持禮貌與關係，同時拉開行動承諾"
        implicit_need = "希望對方接受拒絕，不必逼迫明說"
        action = "decline_or_delay"
        confidence = 0.7
        cue = "婉拒／延後措辭"
    elif reserved_agreement:
        label = "surface_agreement_with_reservation"
        intent = "表面同意，但保留真正接受程度"
        emotion = "可能勉強、猶豫或降低衝突"
        relation = "暫時配合對方，但不代表內在認同"
        implicit_need = "希望保留拒絕或重新協商的空間"
        action = "comply_with_reservation"
        confidence = 0.66
        cue = "帶保留的同意措辭"
    elif indirect_support_need:
        label = "possible_indirect_support_request"
        intent = "可能用否認或淡化來測試對方是否仍會關心"
        emotion = "可能低落，也可能真的沒有困擾"
        relation = "不直接要求照顧，保留被理解的空間"
        implicit_need = "可能希望被陪伴或追問一次，但不能直接假定"
        action = "seek_support_without_direct_request"
        confidence = 0.56
        cue = "淡化或否認困擾的文字"
    elif direct_correction:
        label = "explicit_correction"
        intent = "修正對方先前的理解"
        emotion = "以自我申告為優先；具體情緒依文字內容判定"
        relation = "要求對方承認誤解並更新模型"
        implicit_need = "希望更正被採納，而不是被舊推測覆蓋"
        action = "correct_other_model"
        confidence = 0.9
        cue = "明確否定／更正詞"
    elif explicit_excitement:
        label = "explicit_positive_arousal"
        intent = "分享興奮或正向高喚起狀態"
        emotion = "興奮／期待"
        relation = "邀請對方跟上當下情緒，但不必然要求建議"
        implicit_need = "可能希望共感或一起高興"
        action = "share_and_seek_affective_alignment"
        confidence = 0.88
        cue = "直接興奮自述"
    elif ambiguous_arousal:
        label = "ambiguous_arousal"
        intent = "分享難以安定或命名的高喚起狀態"
        emotion = "可能是焦慮、興奮、期待或其他高喚起狀態"
        relation = "讓對方先接住強度，但尚未授權替自己命名情緒"
        implicit_need = "可能希望被理解或幫忙釐清，但目前未知"
        action = "clarify_arousal_valence_without_assuming"
        confidence = 0.46
        cue = "文字明示難以安定，但沒有說明正負向原因"
    else:
        label = "literal_intent_unresolved"
        intent = "目前只能安全地依字面理解，言外目的未定"
        emotion = "文字證據不足"
        relation = "未觀察到足以唯一判定的關係訊號"
        implicit_need = "未知；不可由一般對話自動補成心理需求"
        action = "continue_or_clarify"
        confidence = 0.38
        cue = "缺少可唯一支持言外意圖的文字線索"

    evidence = [_text_evidence(text, cue, f"支持 pragmatic label={label}")]
    if visible_hesitation:
        evidence.append(
            _text_evidence(
                text,
                "可見的省略號、語助詞或遲疑文字",
                "只能視為文字中的 hesitation cue，不等同真實語音停頓",
                0.42,
            )
        )
    input_mode = str(input_mode or "text")
    if input_mode == "audio" and acoustic_summary and acoustic_summary.get("reliable"):
        acoustic_evidence = {
            "availability": "available",
            "source": "audio_frontend_summary",
            "reliable": True,
            "features": deepcopy(acoustic_summary),
            "boundary": "聲學摘要是觀察證據，不直接等同情緒或真實意圖",
        }
    elif input_mode == "audio":
        acoustic_evidence = {
            "availability": "unavailable",
            "source": "transcription_only_audio_pipeline",
            "reliable": False,
            "features": None,
            "reason": "目前 Web 語音管線只提供轉錄，未提供可靠語速、停頓、音量或韻律摘要",
        }
    else:
        acoustic_evidence = {
            "availability": "not_applicable_text_input",
            "source": "text_only",
            "reliable": False,
            "features": None,
            "reason": "純文字輸入只能使用文字可見訊號；不假裝讀到語氣或聲學特徵",
        }

    pragmatic_id = f"prag-{int(turn_index):04d}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]}"
    alternatives = {
        "indirect_refusal": [("只是行程未定，並非拒絕", 0.28), ("真的希望之後再決定", 0.24)],
        "surface_agreement_with_reservation": [("只是口語習慣，實際沒有保留", 0.3), ("願意配合但情緒普通", 0.26)],
        "possible_indirect_support_request": [("使用者真的沒事，不希望被追問", 0.4), ("只是結束話題", 0.26)],
        "explicit_correction": [("只修正局部字面，不否定全部理解", 0.26)],
        "explicit_positive_arousal": [("只是描述事件刺激，不一定開心", 0.24)],
        "ambiguous_arousal": [("可能是期待或興奮", 0.36), ("可能是焦慮或不安", 0.36)],
        "literal_intent_unresolved": [("可能有未說出的關係目的", 0.32), ("可能只是維持對話節奏", 0.3)],
    }[label]
    return {
        "schema": PRAGMATIC_SCHEMA,
        "pragmatic_id": pragmatic_id,
        "turn_index": int(turn_index),
        "research_scope": "operational_human_pragmatic_understanding_generalized_beyond_uruha_persona",
        "persona_role": "Uruha is the experimental expression instance, not the definition of human pragmatics",
        "literal_content": {
            "value": text,
            "epistemic_status": "known_observation",
            "source": "transcript" if input_mode == "audio" else "text_input",
        },
        "pragmatic_label": label,
        "inferences": {
            "communicative_intent": _inference(intent, confidence, evidence, alternatives),
            "emotion_or_stance": _inference(emotion, confidence - 0.08, evidence, alternatives),
            "relationship_signal": _inference(relation, confidence - 0.06, evidence, alternatives),
            "implicit_need": _inference(implicit_need, confidence - 0.12, evidence, alternatives),
            "action_tendency": _inference(action, confidence - 0.04, evidence, alternatives),
        },
        "text_visible_hesitation": visible_hesitation,
        "acoustic_evidence": acoustic_evidence,
        "unknown": [
            {
                "field": "speaker_private_thought",
                "reason": "言外意圖只能形成可反駁推測，不能直接當成內心事實",
                "epistemic_status": "unknown",
            },
            {
                "field": "unobserved_nonverbal_context",
                "reason": "沒有可靠影像、姿態或聲學資料",
                "epistemic_status": "unknown",
            },
        ],
        "confidence": round(confidence, 3),
        "memory_policy": {
            "storage_scope": "runtime_session_model",
            "fact_write_allowed": False,
            "reason": "pragmatic inference must be verified before any durable use and is never a private-thought fact",
        },
    }


def verify_previous_pragmatic_understanding(previous, current_user_input, current_pragmatic, turn_index=0):
    previous = deepcopy(previous or {})
    if not previous:
        return {
            "schema": PRAGMATIC_VERIFICATION_SCHEMA,
            "turn_index": int(turn_index),
            "status": "not_available",
            "previous_pragmatic_id": None,
            "summary": "第一輪，尚無上一輪 pragmatic inference 可驗證",
            "prediction_error": None,
        }
    text = str(current_user_input or "").lower()
    previous_label = str(previous.get("pragmatic_label") or "literal_intent_unresolved")
    support_markers = {
        "indirect_refusal": ["就是不想", "其實不想", "其实不想", "不太想去", "不會去", "不会去", "行きたくな", "断るつもり", "didn't want to", "won't go"],
        "surface_agreement_with_reservation": ["其實不太想", "其实不太想", "只是勉強", "只是勉强", "本当は嫌", "乗り気じゃ", "納得してない", "納得していない", "didn't really want", "not convinced"],
        "possible_indirect_support_request": ["只是想有人陪", "其實有點難過", "其实有点难过", "そばにいて", "話を聞いて", "wanted someone to stay", "needed support", "hoped you would ask", "wanted you to ask", "wanted you to listen"],
        "explicit_positive_arousal": ["真的很興奮", "真的很兴奋", "めっちゃ楽しみ", "really excited"],
    }
    contradiction_markers = {
        "indirect_refusal": ["不是拒絕", "不是拒绝", "我會去", "我会去", "行くよ", "not refusing", "i will go"],
        "surface_agreement_with_reservation": ["沒有勉強", "没有勉强", "真的同意", "本当に賛成", "fully agree"],
        "possible_indirect_support_request": ["真的沒事", "真的没事", "別に放っといて", "really fine", "don't ask"],
        "explicit_positive_arousal": ["不是興奮", "不是兴奋", "楽しくない", "not excited"],
    }
    if any(marker in text for marker in support_markers.get(previous_label, [])):
        status = "supported"
        error = 0.0
        summary = "下一輪直接說明支持上一輪的言外意圖推測"
        reason = "explicit_followup_supports_pragmatic_inference"
    elif any(marker in text for marker in contradiction_markers.get(previous_label, [])):
        status = "contradicted"
        error = 1.0
        summary = "下一輪明確否定上一輪的言外意圖推測；必須撤銷"
        reason = "explicit_followup_contradicts_pragmatic_inference"
    else:
        status = "uncertain"
        error = 0.5
        summary = "下一輪不足以確認或否定言外意圖；不給正確信用"
        reason = "insufficient_pragmatic_followup_evidence"
    return {
        "schema": PRAGMATIC_VERIFICATION_SCHEMA,
        "turn_index": int(turn_index),
        "status": status,
        "reason": reason,
        "summary": summary,
        "previous_pragmatic_id": previous.get("pragmatic_id"),
        "previous_hypothesis_id": previous.get("linked_hypothesis_id"),
        "previous_pragmatic_snapshot": previous,
        "current_pragmatic_label": (current_pragmatic or {}).get("pragmatic_label"),
        "prediction_error": error,
        "evidence": [
            {
                "source": "next_user_input",
                "observed": str(current_user_input or ""),
                "epistemic_status": "known_observation",
            }
        ],
        "update_policy": "retain_original_append_verification_and_revise_other_model",
    }


def empty_longitudinal_model():
    return {
        "schema": LONGITUDINAL_SCHEMA,
        "claim_scope": "functional_other_model_not_mind_reading",
        "storage_scope": "runtime_session_model",
        "fact_memory_write_allowed_for_inferences": False,
        "layers": {name: [] for name in LAYER_POLICIES},
        "typed_calibration": {
            "schema": CALIBRATION_SCHEMA,
            "categories": {},
            "most_reliable": None,
            "least_reliable": None,
            "sample_count": 0,
        },
        "active_validation": {
            "schema": VALIDATION_SCHEMA,
            "status": "none",
            "pending": None,
            "history": [],
        },
        "revision_history": [],
        "decay_history": [],
        "last_update_turn": 0,
        "last_update_at": None,
    }


def _ensure_model(model):
    state = deepcopy(model or empty_longitudinal_model())
    if state.get("schema") != LONGITUDINAL_SCHEMA:
        state = empty_longitudinal_model()
    layers = state.setdefault("layers", {})
    for layer in LAYER_POLICIES:
        layers.setdefault(layer, [])
    state.setdefault("revision_history", [])
    state.setdefault("decay_history", [])
    state.setdefault("typed_calibration", empty_longitudinal_model()["typed_calibration"])
    state.setdefault("active_validation", empty_longitudinal_model()["active_validation"])
    return state


def _entry_id(layer, kind, value, turn_index):
    seed = f"{layer}|{kind}|{value}|{turn_index}".encode("utf-8")
    return f"um-{hashlib.sha256(seed).hexdigest()[:12]}"


def _new_entry(
    layer,
    kind,
    value,
    confidence,
    turn_index,
    timestamp,
    source_kind,
    source_ref,
    observed,
    epistemic_status,
    hypothesis_id=None,
):
    policy = LAYER_POLICIES[layer]
    source = {
        "turn_index": int(turn_index),
        "timestamp": timestamp,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "observed": str(observed or ""),
        "epistemic_status": epistemic_status,
    }
    return {
        "model_item_id": _entry_id(layer, kind, value, turn_index),
        "layer": layer,
        "layer_label": policy["label"],
        "kind": kind,
        "value": str(value or "").strip(),
        "status": "active",
        "epistemic_status": epistemic_status,
        "confidence": round(_clamp(confidence, 0.05, 0.98), 3),
        "first_seen_turn": int(turn_index),
        "last_updated_turn": int(turn_index),
        "last_decay_turn": int(turn_index),
        "first_seen_at": timestamp,
        "last_updated_at": timestamp,
        "source_history": [source],
        "verification_history": [],
        "confirmation_count": 0,
        "contradiction_count": 0,
        "uncertain_count": 0,
        "influence_count": 0,
        "consecutive_influence_count": 0,
        "last_influenced_turn": None,
        "linked_hypothesis_ids": [hypothesis_id] if hypothesis_id else [],
        "expiry_policy": deepcopy(policy),
    }


def _upsert_entry(model, entry):
    rows = model["layers"][entry["layer"]]
    key = (entry["kind"], _normalize(entry["value"]))
    for existing in rows:
        if existing.get("status") in {"withdrawn", "expired"}:
            continue
        if (existing.get("kind"), _normalize(existing.get("value"))) != key:
            continue
        existing["confidence"] = round(
            _clamp(max(float(existing.get("confidence", 0.0)), float(entry["confidence"]))),
            3,
        )
        existing["status"] = "active"
        existing["last_updated_turn"] = entry["last_updated_turn"]
        existing["last_decay_turn"] = entry["last_decay_turn"]
        existing["last_updated_at"] = entry["last_updated_at"]
        existing["source_history"] = [
            *list(existing.get("source_history") or []),
            *entry["source_history"],
        ][-12:]
        linked = list(existing.get("linked_hypothesis_ids") or [])
        for hypothesis_id in entry.get("linked_hypothesis_ids") or []:
            if hypothesis_id and hypothesis_id not in linked:
                linked.append(hypothesis_id)
        existing["linked_hypothesis_ids"] = linked[-8:]
        return existing, False
    rows.append(entry)
    limits = {"stable": 16, "situational": 12, "provisional": 18}
    if len(rows) > limits[entry["layer"]]:
        model["layers"][entry["layer"]] = rows[-limits[entry["layer"]] :]
    return entry, True


def _apply_decay(model, turn_index, timestamp):
    events = []
    for layer, policy in LAYER_POLICIES.items():
        for entry in model["layers"][layer]:
            if entry.get("status") in {"withdrawn", "expired"}:
                continue
            last_decay_turn = int(entry.get("last_decay_turn", entry.get("last_updated_turn", turn_index)))
            delta_turns = max(0, int(turn_index) - last_decay_turn)
            age = max(0, int(turn_index) - int(entry.get("last_updated_turn", turn_index)))
            if delta_turns <= 0:
                continue
            confidence_before = float(entry.get("confidence", 0.0))
            chargeable_turns = max(
                0,
                int(turn_index)
                - max(last_decay_turn, int(entry.get("last_updated_turn", turn_index)) + int(policy["grace_turns"])),
            )
            confidence_after = _clamp(
                confidence_before - chargeable_turns * float(policy["decay_per_turn"]),
                0.05,
                0.98,
            )
            status_before = entry.get("status", "active")
            if age >= int(policy["expire_after_turns"]) or confidence_after <= 0.2:
                status_after = "expired"
            elif age >= int(policy["stale_after_turns"]) or confidence_after < 0.45:
                status_after = "stale"
            else:
                status_after = "active"
            entry["confidence"] = round(confidence_after, 3)
            entry["status"] = status_after
            entry["last_decay_turn"] = int(turn_index)
            if confidence_after != confidence_before or status_after != status_before:
                event = {
                    "turn_index": int(turn_index),
                    "timestamp": timestamp,
                    "model_item_id": entry.get("model_item_id"),
                    "layer": layer,
                    "kind": entry.get("kind"),
                    "value": entry.get("value"),
                    "age_turns": age,
                    "confidence_before": round(confidence_before, 3),
                    "confidence_after": round(confidence_after, 3),
                    "status_before": status_before,
                    "status_after": status_after,
                    "reason": "age_based_decay_not_silent_forgetting",
                }
                events.append(event)
    model["decay_history"] = [*model.get("decay_history", []), *events][-36:]
    return events


def _hypothesis_categories(hypothesis, include_pragmatic=True):
    inferred = (hypothesis or {}).get("inferred") or {}
    mapping = {
        "possible_intent": "intent",
        "emotion_or_need": "emotion_or_need",
        "dialogue_goal": "dialogue_goal",
    }
    rows = []
    for field, category in mapping.items():
        payload = inferred.get(field) or {}
        value = str(payload.get("value") or "").strip()
        if not value or value == "尚不明":
            continue
        rows.append(
            {
                "field": field,
                "category": category,
                "value": value,
                "confidence": float(payload.get("confidence", (hypothesis or {}).get("confidence", 0.5)) or 0.5),
            }
        )
    if include_pragmatic:
        pragmatic = (hypothesis or {}).get("pragmatic_understanding_v2_13") or {}
        for field, payload in (pragmatic.get("inferences") or {}).items():
            value = str((payload or {}).get("value") or "").strip()
            if not value:
                continue
            rows.append(
                {
                    "field": field,
                    "category": f"pragmatic_{field}",
                    "value": value,
                    "confidence": float((payload or {}).get("confidence", pragmatic.get("confidence", 0.5)) or 0.5),
                }
            )
    return rows


def _reliability(stats):
    observations = int(stats.get("observations", 0))
    supported = int(stats.get("supported", 0))
    contradicted = int(stats.get("contradicted", 0))
    decisive = supported + contradicted
    supported_rate = supported / decisive if decisive else 0.0
    mean_confidence = float(stats.get("confidence_sum", 0.0)) / observations if observations else 0.0
    contradiction_rate = contradicted / decisive if decisive else 0.0
    overconfidence_gap = max(0.0, mean_confidence - supported_rate) if decisive else mean_confidence
    if observations < 3 or decisive < 2:
        band = "insufficient"
        cap = 0.7
    elif contradiction_rate >= 0.34 or overconfidence_gap >= 0.3:
        band = "low"
        cap = 0.55
    elif supported_rate >= 0.7 and overconfidence_gap <= 0.2:
        band = "high"
        cap = 0.9
    else:
        band = "medium"
        cap = 0.75
    return {
        "observations": observations,
        "supported_rate": round(supported_rate, 3),
        "contradiction_rate": round(contradiction_rate, 3),
        "mean_prediction_confidence": round(mean_confidence, 3),
        "overconfidence_gap": round(overconfidence_gap, 3),
        "reliability_band": band,
        "recommended_confidence_cap": cap,
    }


def _record_typed_calibration(model, verification):
    status = str((verification or {}).get("status") or "not_available")
    previous = (verification or {}).get("previous_hypothesis_snapshot") or {}
    if status not in {"supported", "contradicted", "uncertain"} or not previous:
        return []
    categories = model["typed_calibration"].setdefault("categories", {})
    changed = []
    for row in _hypothesis_categories(previous, include_pragmatic=False):
        category = row["category"]
        stats = categories.setdefault(
            category,
            {
                "category": category,
                "observations": 0,
                "supported": 0,
                "contradicted": 0,
                "uncertain": 0,
                "confidence_sum": 0.0,
                "prediction_error_sum": 0.0,
            },
        )
        stats["observations"] += 1
        stats[status] += 1
        stats["confidence_sum"] = round(float(stats.get("confidence_sum", 0.0)) + row["confidence"], 6)
        stats["prediction_error_sum"] = round(
            float(stats.get("prediction_error_sum", 0.0))
            + float((verification or {}).get("prediction_error", 0.5) or 0.0),
            6,
        )
        stats.update(_reliability(stats))
        changed.append(deepcopy(stats))
    model["typed_calibration"]["sample_count"] = sum(
        int(row.get("observations", 0)) for row in categories.values()
    )
    comparable = [row for row in categories.values() if int(row.get("observations", 0)) >= 2]
    if comparable:
        ordered = sorted(
            comparable,
            key=lambda row: (
                float(row.get("supported_rate", 0.0)),
                -float(row.get("contradiction_rate", 0.0)),
                int(row.get("observations", 0)),
            ),
            reverse=True,
        )
        model["typed_calibration"]["most_reliable"] = ordered[0]["category"]
        model["typed_calibration"]["least_reliable"] = ordered[-1]["category"]
    return changed


def _apply_verification_to_entries(model, verification, turn_index, timestamp, pragmatic_only=False):
    status = str((verification or {}).get("status") or "not_available")
    hypothesis_id = (verification or {}).get("previous_hypothesis_id")
    if not hypothesis_id or status not in {"supported", "contradicted", "uncertain"}:
        return []
    revisions = []
    for layer_entries in model["layers"].values():
        for entry in layer_entries:
            if hypothesis_id not in set(entry.get("linked_hypothesis_ids") or []):
                continue
            is_pragmatic = str(entry.get("kind") or "").startswith("pragmatic_")
            if pragmatic_only != is_pragmatic:
                continue
            confidence_before = float(entry.get("confidence", 0.0))
            status_before = entry.get("status", "active")
            entry["verification_history"] = [
                *list(entry.get("verification_history") or []),
                {
                    "turn_index": int(turn_index),
                    "timestamp": timestamp,
                    "status": status,
                    "reason": (verification or {}).get("reason"),
                    "prediction_error": (verification or {}).get("prediction_error"),
                    "evidence": deepcopy((verification or {}).get("evidence") or []),
                },
            ][-12:]
            if status == "supported":
                entry["confirmation_count"] = int(entry.get("confirmation_count", 0)) + 1
                entry["confidence"] = round(_clamp(confidence_before + 0.1, 0.05, 0.96), 3)
                entry["status"] = "active"
            elif status == "contradicted":
                entry["contradiction_count"] = int(entry.get("contradiction_count", 0)) + 1
                entry["confidence"] = round(_clamp(confidence_before - 0.55, 0.05, 0.96), 3)
                entry["status"] = "withdrawn"
            else:
                entry["uncertain_count"] = int(entry.get("uncertain_count", 0)) + 1
                entry["confidence"] = round(_clamp(confidence_before - 0.06, 0.05, 0.96), 3)
                if entry["confidence"] < 0.45:
                    entry["status"] = "stale"
            entry["last_updated_at"] = timestamp
            revisions.append(
                {
                    "turn_index": int(turn_index),
                    "timestamp": timestamp,
                    "model_item_id": entry.get("model_item_id"),
                    "linked_hypothesis_id": hypothesis_id,
                    "kind": entry.get("kind"),
                    "value": entry.get("value"),
                    "verification": status,
                    "confidence_before": round(confidence_before, 3),
                    "confidence_after": entry["confidence"],
                    "status_before": status_before,
                    "status_after": entry["status"],
                    "original_retained": True,
                    "reason": "later_user_turn_revises_other_model",
                }
            )
    model["revision_history"] = [*model.get("revision_history", []), *revisions][-36:]
    return revisions


def _record_pragmatic_typed_calibration(model, pragmatic_verification):
    status = str((pragmatic_verification or {}).get("status") or "not_available")
    previous_pragmatic = (pragmatic_verification or {}).get("previous_pragmatic_snapshot") or {}
    hypothesis = {
        "pragmatic_understanding_v2_13": previous_pragmatic,
    }
    if status not in {"supported", "contradicted", "uncertain"} or not previous_pragmatic:
        return []
    categories = model["typed_calibration"].setdefault("categories", {})
    changed = []
    for row in _hypothesis_categories(hypothesis, include_pragmatic=True):
        if not row["category"].startswith("pragmatic_"):
            continue
        stats = categories.setdefault(
            row["category"],
            {
                "category": row["category"],
                "observations": 0,
                "supported": 0,
                "contradicted": 0,
                "uncertain": 0,
                "confidence_sum": 0.0,
                "prediction_error_sum": 0.0,
            },
        )
        stats["observations"] += 1
        stats[status] += 1
        stats["confidence_sum"] = round(float(stats.get("confidence_sum", 0.0)) + row["confidence"], 6)
        stats["prediction_error_sum"] = round(
            float(stats.get("prediction_error_sum", 0.0))
            + float((pragmatic_verification or {}).get("prediction_error", 0.5) or 0.0),
            6,
        )
        stats.update(_reliability(stats))
        changed.append(deepcopy(stats))
    model["typed_calibration"]["sample_count"] = sum(
        int(row.get("observations", 0)) for row in categories.values()
    )
    comparable = [row for row in categories.values() if int(row.get("observations", 0)) >= 2]
    if comparable:
        ordered = sorted(
            comparable,
            key=lambda row: (
                float(row.get("supported_rate", 0.0)),
                -float(row.get("contradiction_rate", 0.0)),
                int(row.get("observations", 0)),
            ),
            reverse=True,
        )
        model["typed_calibration"]["most_reliable"] = ordered[0]["category"]
        model["typed_calibration"]["least_reliable"] = ordered[-1]["category"]
    return changed


def _extract_explicit_stable_updates(user_input):
    text = str(user_input or "").strip()
    lowered = text.lower()
    updates = []
    patterns = [
        (r"(?:my favorite(?: drink| food| snack)? is)\s+([a-z0-9 \-]{2,30})", lowered),
        (r"(?:我最喜歡|我最喜欢)(?:的(?:飲料|饮料|食物))?(?:是)?([^，。！？?]{1,24})", text),
        (r"(?:私の)?一番好きな(?:飲み物|食べ物|おやつ|もの)?(?:は|が)\s*([^、。！？?]{1,30})", text),
    ]
    for pattern, source in patterns:
        match = re.search(pattern, source, re.IGNORECASE)
        if match:
            updates.append(("preference", match.group(1).strip()))
            break
    communication_markers = [
        "先問我再給建議",
        "先问我再给建议",
        "先聽我說再給建議",
        "先听我说再给建议",
        "ask me before giving advice",
        "listen first before giving advice",
        "アドバイスする前に聞いて",
        "先に聞いてからアドバイス",
    ]
    if any(marker in lowered for marker in communication_markers):
        updates.append(("communication_preference", "先傾聽並確認，再提供建議"))
    return updates


def _extract_preference_retractions(user_input):
    text = str(user_input or "").strip()
    lowered = text.lower()
    patterns = [
        (r"i (?:do not|don't|no longer) like\s+([a-z0-9 \-]{2,30})", lowered),
        (r"我(?:現在|现在)?(?:不再|不)喜歡([^，。！？?]{1,24})", text),
        (r"(.{1,24})(?:は|が)?もう好きじゃない", text),
        (r"もう(.{1,24})(?:は|が)?好きじゃない", text),
    ]
    values = []
    for pattern, source in patterns:
        match = re.search(pattern, source, re.IGNORECASE)
        if match:
            values.append(match.group(1).strip())
    return values


def _apply_explicit_updates(model, user_input, turn_index, timestamp):
    events = []
    for kind, value in _extract_explicit_stable_updates(user_input):
        entry = _new_entry(
            "stable",
            kind,
            value,
            0.92,
            turn_index,
            timestamp,
            "explicit_user_report",
            "current_user_input",
            user_input,
            "known_as_user_report",
        )
        stored, created = _upsert_entry(model, entry)
        events.append(
            {
                "action": "created" if created else "confirmed",
                "model_item_id": stored["model_item_id"],
                "layer": "stable",
                "kind": kind,
                "value": value,
                "fact_basis": "explicit_user_report",
            }
        )
    for value in _extract_preference_retractions(user_input):
        target = _normalize(value)
        for entry in model["layers"]["stable"]:
            if entry.get("kind") != "preference" or entry.get("status") in {"withdrawn", "expired"}:
                continue
            entry_value = _normalize(entry.get("value"))
            if target not in entry_value and entry_value not in target:
                continue
            before = float(entry.get("confidence", 0.0))
            entry["confidence"] = round(_clamp(before - 0.7, 0.05, 0.98), 3)
            entry["status"] = "withdrawn"
            entry["contradiction_count"] = int(entry.get("contradiction_count", 0)) + 1
            source = {
                "turn_index": int(turn_index),
                "timestamp": timestamp,
                "source_kind": "explicit_user_retraction",
                "source_ref": "current_user_input",
                "observed": str(user_input or ""),
                "epistemic_status": "known_as_user_report",
            }
            entry["source_history"] = [*entry.get("source_history", []), source][-12:]
            revision = {
                "turn_index": int(turn_index),
                "timestamp": timestamp,
                "model_item_id": entry.get("model_item_id"),
                "kind": entry.get("kind"),
                "value": entry.get("value"),
                "verification": "explicit_retraction",
                "confidence_before": round(before, 3),
                "confidence_after": entry["confidence"],
                "status_before": "active",
                "status_after": "withdrawn",
                "original_retained": True,
                "reason": "new_explicit_user_report_overrides_old_preference",
            }
            model["revision_history"] = [*model.get("revision_history", []), revision][-36:]
            events.append({"action": "withdrawn", **revision})
    return events


def _apply_situational_updates(model, user_input, hypothesis, turn_index, timestamp):
    features = set((hypothesis or {}).get("semantic_features") or [])
    rows = []
    if "rest_action" in features:
        rows.append(("current_goal", "休息或降低互動負擔", 0.88))
    if "support_request" in features:
        rows.append(("current_goal", "希望先被傾聽或陪伴", 0.84))
    if "food" in features:
        rows.append(("current_context", "正在延續飲食話題", 0.76))
    events = []
    for kind, value, confidence in rows:
        entry = _new_entry(
            "situational",
            kind,
            value,
            confidence,
            turn_index,
            timestamp,
            "current_user_input",
            "turn-input",
            user_input,
            "known_or_strongly_grounded_current_context",
        )
        stored, created = _upsert_entry(model, entry)
        events.append(
            {
                "action": "created" if created else "refreshed",
                "model_item_id": stored["model_item_id"],
                "layer": "situational",
                "kind": kind,
                "value": value,
            }
        )
    return events


def _add_current_provisional(model, hypothesis, turn_index, timestamp):
    hypothesis_id = (hypothesis or {}).get("hypothesis_id")
    user_utterance = next(
        (
            row.get("value")
            for row in (hypothesis or {}).get("known") or []
            if row.get("field") == "user_utterance"
        ),
        "",
    )
    events = []
    for row in _hypothesis_categories(hypothesis):
        entry = _new_entry(
            "provisional",
            row["category"],
            row["value"],
            row["confidence"],
            turn_index,
            timestamp,
            "v2_12_hypothesis",
            hypothesis_id,
            user_utterance,
            "provisional_inference",
            hypothesis_id=hypothesis_id,
        )
        stored, created = _upsert_entry(model, entry)
        events.append(
            {
                "action": "created" if created else "reobserved",
                "model_item_id": stored["model_item_id"],
                "layer": "provisional",
                "kind": row["category"],
                "value": row["value"],
                "confidence": stored["confidence"],
                "hypothesis_id": hypothesis_id,
            }
        )
    return events


def _resolve_pending_validation(model, verification, pragmatic_verification, turn_index, timestamp):
    validation = model.get("active_validation") or {}
    pending = validation.get("pending") or {}
    if not pending or pending.get("status") != "pending":
        return None
    use_pragmatic = str(pending.get("kind") or "").startswith("pragmatic_")
    selected_verification = pragmatic_verification if use_pragmatic else verification
    previous_id = (selected_verification or {}).get("previous_hypothesis_id")
    if previous_id not in set(pending.get("hypothesis_ids") or []):
        return None
    status = str((selected_verification or {}).get("status") or "uncertain")
    if status not in {"supported", "contradicted"}:
        return None
    resolution = {
        **deepcopy(pending),
        "status": "confirmed" if status == "supported" else "withdrawn",
        "resolved_turn": int(turn_index),
        "resolved_at": timestamp,
        "resolution_evidence": deepcopy((selected_verification or {}).get("evidence") or []),
        "verification_status": status,
    }
    validation["pending"] = None
    validation["status"] = resolution["status"]
    validation["history"] = [*validation.get("history", []), resolution][-12:]
    model["active_validation"] = validation
    return resolution


def update_longitudinal_user_model(
    model,
    current_hypothesis,
    verification,
    pragmatic_verification,
    user_input,
    turn_index,
    timestamp=None,
):
    state = _ensure_model(model)
    now = _timestamp(timestamp)
    decay_events = _apply_decay(state, turn_index, now)
    revisions = _apply_verification_to_entries(
        state,
        verification,
        turn_index,
        now,
        pragmatic_only=False,
    )
    pragmatic_revisions = _apply_verification_to_entries(
        state,
        pragmatic_verification,
        turn_index,
        now,
        pragmatic_only=True,
    )
    typed_calibration_updates = _record_typed_calibration(state, verification)
    pragmatic_calibration_updates = _record_pragmatic_typed_calibration(
        state,
        pragmatic_verification,
    )
    validation_resolution = _resolve_pending_validation(
        state,
        verification,
        pragmatic_verification,
        turn_index,
        now,
    )
    explicit_updates = _apply_explicit_updates(state, user_input, turn_index, now)
    situational_updates = _apply_situational_updates(
        state,
        user_input,
        current_hypothesis,
        turn_index,
        now,
    )
    provisional_updates = _add_current_provisional(state, current_hypothesis, turn_index, now)
    state["last_update_turn"] = int(turn_index)
    state["last_update_at"] = now
    state["summary"] = model_summary(state)
    trace = {
        "schema": "uruha_longitudinal_other_model_update_v2_13",
        "turn_index": int(turn_index),
        "decay_events": decay_events,
        "revisions": revisions,
        "pragmatic_revisions": pragmatic_revisions,
        "explicit_updates": explicit_updates,
        "situational_updates": situational_updates,
        "provisional_updates": provisional_updates,
        "validation_resolution": validation_resolution,
        "typed_calibration_updates": typed_calibration_updates,
        "pragmatic_calibration_updates": pragmatic_calibration_updates,
        "psychological_inference_written_as_fact": False,
    }
    return state, trace


def model_summary(model):
    model = _ensure_model(model)
    layers = {}
    for layer, rows in model["layers"].items():
        layers[layer] = {
            "active": sum(1 for row in rows if row.get("status") == "active"),
            "stale": sum(1 for row in rows if row.get("status") == "stale"),
            "withdrawn": sum(1 for row in rows if row.get("status") == "withdrawn"),
            "expired": sum(1 for row in rows if row.get("status") == "expired"),
            "total": len(rows),
        }
    return {
        "layers": layers,
        "most_reliable": (model.get("typed_calibration") or {}).get("most_reliable"),
        "least_reliable": (model.get("typed_calibration") or {}).get("least_reliable"),
        "calibration_samples": (model.get("typed_calibration") or {}).get("sample_count", 0),
        "pending_validation": bool(((model.get("active_validation") or {}).get("pending"))),
        "last_revision": (model.get("revision_history") or [None])[-1],
        "last_decay": (model.get("decay_history") or [None])[-1],
    }


def _protected_plan(plan, hypothesis):
    intent = str((plan or {}).get("intent") or "")
    scene = str((plan or {}).get("scene") or "")
    response_mode = str((plan or {}).get("response_mode") or "")
    return bool(
        scene in {"boundary", "refusal", "ooc_defense"}
        or intent in {"crisis_support", "sexual_boundary", "abuse_pushback", "self_intro"}
        or intent.startswith("recall_")
        or response_mode in {"felt_understanding_confirmation", "felt_understanding_revision"}
        or "safety" in set((hypothesis or {}).get("semantic_features") or [])
    )


def apply_pragmatic_attunement_to_plan(
    plan,
    pragmatic_understanding,
    hypothesis=None,
    pragmatic_verification=None,
    hypothesis_verification=None,
):
    """Turn internal pragmatics into a natural felt-understanding reply plan.

    Confidence, alternatives, labels, and trace metadata stay internal.  The
    user receives a brief Uruha-style reflection or bounded prediction, never a
    technical explanation of the model's analysis.
    """
    logic = deepcopy(plan or {})
    pragmatic = pragmatic_understanding or {}
    label = str(pragmatic.get("pragmatic_label") or "literal_intent_unresolved")
    confidence = float(pragmatic.get("confidence", 0.0) or 0.0)
    protected = _protected_plan(logic, hypothesis or {})
    strategy = {
        "schema": "uruha_pragmatic_attunement_strategy_v2_13",
        "label": label,
        "confidence": round(confidence, 3),
        "protected_direct_response": protected,
        "internal_trace_not_user_visible": True,
        "changed_plan": False,
        "moves": [],
    }
    if protected:
        strategy["reason"] = "identity_memory_safety_or_boundary_keeps_direct_contract"
        logic["pragmatic_attunement_strategy_v2_13"] = strategy
        return logic

    pragmatic_outcome = str((pragmatic_verification or {}).get("status") or "not_available")
    general_outcome = str((hypothesis_verification or {}).get("status") or "not_available")
    previous_label = str(
        ((pragmatic_verification or {}).get("previous_pragmatic_snapshot") or {}).get(
            "pragmatic_label"
        )
        or ""
    )
    current_features = set((hypothesis or {}).get("semantic_features") or [])

    # A broad mental-state hypothesis can be contradicted by correction-like
    # wording even when the narrower pragmatic prediction is explicitly
    # confirmed (for example: "其實我是不太想去" confirms an earlier indirect
    # refusal).  The dimension-specific verification must win in that case;
    # otherwise the reply would reverse a correct pragmatic reading.
    effective_contradiction = bool(
        pragmatic_outcome == "contradicted"
        or (
            general_outcome == "contradicted"
            and pragmatic_outcome not in {"supported"}
        )
    )
    if effective_contradiction:
        revision_copy = {
            "indirect_refusal": "あ、断るってことじゃないのか。行く方なんだな。そこは読み違えた。",
            "surface_agreement_with_reservation": "あ、ちゃんと納得してる方か。そこは読みすぎた。",
            "possible_indirect_support_request": "あ、ほんとに放っといてほしい方か。そこは読みすぎた。",
            "explicit_positive_arousal": "あ、興奮じゃないのか。そこは読み違えた。",
        }.get(previous_label)
        if "excited" in current_features:
            revision_copy = "あ、不安じゃなくて楽しみで落ち着かないのか。そっちだな、読み違えた。"
        revision_copy = revision_copy or "あ、そっちか。さっきは読みすぎた。今の言い方で直す。"
        strategy.update(
            {
                "changed_plan": True,
                "reason": "later_user_evidence_contradicted_previous_inference",
                "moves": [
                    "acknowledge_misread",
                    "adopt_current_user_report",
                    "withdraw_previous_inference_without_defensiveness",
                ],
                "outcome_status": "contradicted",
                "previous_pragmatic_label": previous_label or None,
                "overclaim_guard": "使用者の訂正を最優先し、最初から分かっていたふりをしない",
            }
        )
        logic.update(
            {
                "intent": "pragmatic_revision",
                "scene": "casual",
                "hidden_intent": "repair_the_other_model_after_user_correction",
                "reply_goal": "誤読を認め、使用者の明示的な訂正に更新する",
                "core_message_jp": revision_copy,
                "response_mode": "felt_understanding_revision",
                "surface_act": "pragmatic_attunement",
                "dialogue_act": "acknowledge_and_revise",
                "payload_level": "medium",
            }
        )
        logic["pragmatic_attunement_strategy_v2_13"] = strategy
        return logic

    if pragmatic_outcome == "supported" and previous_label:
        support_copy = {
            "indirect_refusal": "やっぱ予定より、断り方の方で詰まってたんだな。分かった。",
            "surface_agreement_with_reservation": "やっぱ納得してなかったんだな。そこは無理に合わせなくていい。",
            "possible_indirect_support_request": "直してほしいんじゃなくて、一回ちゃんと聞いてほしかったんだな。分かった。",
            "explicit_positive_arousal": "やっぱ落ちてるんじゃなくて、楽しみで上がってたんだな。",
        }.get(previous_label)
        if support_copy:
            strategy.update(
                {
                    "changed_plan": True,
                    "reason": "later_user_evidence_supported_previous_bounded_inference",
                    "moves": ["reflect_confirmed_need", "preserve_user_report_priority"],
                    "outcome_status": "supported",
                    "previous_pragmatic_label": previous_label,
                }
            )
            logic.update(
                {
                    "intent": "pragmatic_confirmation",
                    "scene": "support" if previous_label == "possible_indirect_support_request" else "casual",
                    "hidden_intent": "reflect_the_need_now_confirmed_by_the_user",
                    "reply_goal": "後続の明示証拠で確認された核心を自然に受け止める",
                    "core_message_jp": support_copy,
                    "response_mode": "felt_understanding_confirmation",
                    "surface_act": "pragmatic_attunement",
                    "dialogue_act": "confirm_and_attune",
                    "payload_level": "medium",
                }
            )
            logic["pragmatic_attunement_strategy_v2_13"] = strategy
            return logic

    variants = {
        "indirect_refusal": {
            "core": "それ、行く気あるっていうより、断りづらいだけじゃね。違うならそこだけ言って。",
            "goal": "字面の保留ではなく、断りづらさという核心を控えめに反射する",
            "prediction": "本当の詰まりは予定より断り方かもしれない",
        },
        "surface_agreement_with_reservation": {
            "core": "それ、納得したっていうより、揉めたくなくて合わせてる感じだろ。違うなら言え。",
            "goal": "表面同意の下にある保留を断定せず拾う",
            "prediction": "同意そのものより関係摩擦を避けたい可能性がある",
        },
        "possible_indirect_support_request": {
            "core": "平気って言ってるけど、放っといてほしいのか、少し聞いてほしいのかだけ分かんない。",
            "goal": "淡化をそのまま放置せず、世話焼きにもならない形で必要を確認する",
            "prediction": "本当に放置を望む場合と、少しだけ気づいてほしい場合を両方残す",
        },
        "explicit_positive_arousal": {
            "core": "落ちてるっていうより、持て余すくらい上がってんだろ。まあ分かる。",
            "goal": "明示された興奮を問題扱いせず、その強さまで自然に反射する",
            "prediction": "助言より感情の同期を求めている可能性がある",
        },
        "ambiguous_arousal": {
            "core": "落ち着かないの、楽しみな方か不安な方かはまだ分かんね。どっち寄り？",
            "goal": "高ぶりを不安と決めつけず、あり得る方向を短く確かめる",
            "prediction": "正負どちらの高ぶりかは次の本人の説明で初めて確かめられる",
        },
    }
    selected = variants.get(label)
    if label == "ambiguous_arousal":
        minimum = 0.45
    elif label == "possible_indirect_support_request":
        minimum = 0.52
    else:
        minimum = 0.62
    if selected and confidence >= minimum:
        strategy.update(
            {
                "changed_plan": True,
                "reason": "text_evidence_supports_bounded_pragmatic_reflection",
                "moves": [
                    "reflect_core_tension_not_only_literal_words",
                    "offer_one_bounded_prediction",
                    "leave_natural_room_for_denial_or_correction",
                ],
                "bounded_prediction": selected["prediction"],
                "overclaim_guard": "違うなら否定できる余地を自然に残す",
            }
        )
        logic.update(
            {
                "intent": "pragmatic_attunement",
                "scene": "support" if label == "possible_indirect_support_request" else "casual",
                "hidden_intent": "make_the_user_feel_understood_without_claiming_mind_reading",
                "reply_goal": selected["goal"],
                "core_message_jp": selected["core"],
                "response_mode": "felt_understanding_reflection",
                "surface_act": "pragmatic_attunement",
                "dialogue_act": "bounded_pragmatic_reflection",
                "payload_level": "medium",
            }
        )
    else:
        strategy["reason"] = "insufficient_pragmatic_evidence_keep_bounded_or_clarify"
    logic["pragmatic_attunement_strategy_v2_13"] = strategy
    return logic


def apply_public_persona_appraisal_to_plan(
    plan,
    pragmatic_understanding,
    longitudinal_model,
    psyche_state,
):
    """Make public-persona and relationship constraints causally observable.

    These evidence references are authorized only as development hypotheses in
    this isolated research worktree.  They are not persona-fidelity evidence
    and do not describe the real person's private state.
    """
    logic = deepcopy(plan or {})
    psyche = deepcopy(psyche_state or {})
    trust = float(psyche.get("trust", 50.0) or 50.0)
    mood = float(psyche.get("mood", 0.0) or 0.0)
    phase = "familiar" if trust >= 65 else "developing" if trust >= 45 else "cautious"
    protected = _protected_plan(logic, {})
    core_before = str(logic.get("core_message_jp") or "")
    core_after = core_before
    adjustment = "keep_existing_plan"

    if not protected and phase == "cautious" and logic.get("surface_act") == "pragmatic_attunement":
        core_after = core_after.replace("違うならそこだけ言って", "違ったらそこだけ言って")
        core_after = core_after.replace("違うなら言え", "違ったら言って")
        adjustment = "keep_directness_but_reduce_assumed_familiarity"
    if not protected and mood <= -25 and logic.get("scene") == "support":
        constraints = deepcopy(logic.get("constraints") or {})
        constraints["teasing_allowed"] = False
        logic["constraints"] = constraints
        adjustment = f"{adjustment}+suppress_teasing_under_low_functional_mood"
    logic["core_message_jp"] = core_after

    appraisal = {
        "schema": "uruha_public_persona_cognitive_appraisal_v2_13",
        "positioning": "public-evidence-grounded development persona instance; not the real person",
        "authorization_scope": "development_hypothesis_only_not_persona_fidelity_or_production_activation",
        "relationship_phase": phase,
        "functional_self_state": {"mood": mood, "trust": trust},
        "pragmatic_label": (pragmatic_understanding or {}).get("pragmatic_label"),
        "longitudinal_model_present": bool((longitudinal_model or {}).get("schema")),
        "evidence_refs": [
            {
                "dataset": "datasets/public_persona_evidence_v1.json",
                "evidence_id": "persona_dev_v1_002",
                "trait_key": "direct_unsugarcoated_delivery",
                "generalization_limit": "directness_is_not_hostility_and_must_yield_to_safety_or_distance",
            },
            {
                "dataset": "datasets/public_persona_evidence_v1.json",
                "evidence_id": "persona_dev_v1_003",
                "trait_key": "guarded_with_unfamiliar_people",
                "generalization_limit": "guardedness_is_not_permanent_coldness",
            },
        ],
        "unknown_space": [
            "childhood_and_unpublished_experience",
            "private_relationships_and_memories",
            "unobserved_current_mental_state",
        ],
        "used_for_action": True,
        "adjustment": adjustment,
        "core_changed": core_after != core_before,
        "private_person_inference_added": False,
    }
    logic["public_persona_cognitive_appraisal_v2_13"] = appraisal
    return logic, appraisal


def _clarification_copy(kind):
    if kind == "pragmatic_implicit_need":
        return "今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。"
    if kind == "pragmatic_relationship_signal":
        return "合わせてるだけなのか、本当にそれでいいのかだけ教えて。"
    if kind == "emotion_or_need":
        return "その感じ、しんどい方か、楽しみな方かだけ教えて。"
    if kind == "dialogue_goal":
        return "今は聞いてほしいのか、一緒に決めたいのかだけ教えて。"
    return "そこ、聞いてほしい話なのか、答えがほしいのかだけ教えて。"


def apply_longitudinal_model_to_plan(
    plan,
    model,
    hypothesis,
    turn_index,
    direct_user_report=None,
):
    """Make the cross-turn other-model an explicit action-selection input."""
    logic = deepcopy(plan or {})
    state = _ensure_model(model)
    hypothesis_id = (hypothesis or {}).get("hypothesis_id")
    current_entries = [
        row
        for row in state["layers"]["provisional"]
        if hypothesis_id in set(row.get("linked_hypothesis_ids") or [])
        and row.get("status") in {"active", "stale"}
    ]
    for entry in current_entries:
        previous_turn = entry.get("last_influenced_turn")
        entry["influence_count"] = int(entry.get("influence_count", 0)) + 1
        if previous_turn == int(turn_index) - 1:
            entry["consecutive_influence_count"] = int(entry.get("consecutive_influence_count", 0)) + 1
        else:
            entry["consecutive_influence_count"] = 1
        entry["last_influenced_turn"] = int(turn_index)

    active_stable = [
        deepcopy(row)
        for row in state["layers"]["stable"]
        if row.get("status") == "active" and float(row.get("confidence", 0.0)) >= 0.45
    ]
    active_situational = [
        deepcopy(row)
        for row in state["layers"]["situational"]
        if row.get("status") == "active" and float(row.get("confidence", 0.0)) >= 0.4
    ]
    context = {
        "schema": "uruha_longitudinal_model_planning_context_v2_13",
        "used_for_planning": True,
        "stable_preferences": active_stable[:5],
        "current_situation_and_goals": active_situational[:5],
        "current_provisional": [deepcopy(row) for row in current_entries[:6]],
        "typed_calibration": deepcopy(state.get("typed_calibration") or {}),
        "unknown_policy": "unknowns_require_bounded_language_or_clarification",
    }
    logic["longitudinal_user_model_context"] = context

    communication_preference = next(
        (row for row in active_stable if row.get("kind") == "communication_preference"),
        None,
    )
    communication_applied = False
    if communication_preference and not _protected_plan(logic, hypothesis):
        feature_set = set((hypothesis or {}).get("semantic_features") or [])
        if feature_set.intersection({"tired", "sad", "ambiguous_mood", "support_request"}):
            communication_applied = True
            logic["response_mode"] = "listen_and_confirm_before_advice"
            logic["reply_goal"] = "先に受け止め、助言は求められた時だけ出す"
            constraints = deepcopy(logic.get("constraints") or {})
            constraints["unsolicited_advice"] = False
            logic["constraints"] = constraints

    calibration_categories = (state.get("typed_calibration") or {}).get("categories") or {}
    clarification_candidate = None
    validation_priority = {
        "pragmatic_implicit_need": 0,
        "pragmatic_relationship_signal": 1,
        "pragmatic_action_tendency": 2,
        "emotion_or_need": 3,
        "dialogue_goal": 4,
        "intent": 5,
    }
    ordered_current_entries = sorted(
        current_entries,
        key=lambda row: validation_priority.get(str(row.get("kind") or ""), 6),
    )
    for entry in ordered_current_entries:
        if entry.get("kind") not in {
            "intent",
            "emotion_or_need",
            "dialogue_goal",
            "pragmatic_communicative_intent",
            "pragmatic_emotion_or_stance",
            "pragmatic_relationship_signal",
            "pragmatic_implicit_need",
            "pragmatic_action_tendency",
        }:
            continue
        reliability = calibration_categories.get(entry.get("kind")) or {}
        repeated = int(entry.get("consecutive_influence_count", 0)) >= 2
        low_reliability = reliability.get("reliability_band") == "low"
        uncertain = float(entry.get("confidence", 0.0)) < 0.72
        if uncertain and (repeated or low_reliability):
            clarification_candidate = entry
            break

    validation = state.get("active_validation") or empty_longitudinal_model()["active_validation"]
    pending = validation.get("pending") or {}
    changed_plan = False
    explicit_direct_report = bool(
        isinstance(direct_user_report, dict)
        and str(direct_user_report.get("value") or "").strip()
    )
    if (
        clarification_candidate
        and not pending
        and not _protected_plan(logic, hypothesis)
        and not explicit_direct_report
    ):
        question = _clarification_copy(clarification_candidate.get("kind"))
        pending = {
            "validation_id": f"val-{clarification_candidate['model_item_id']}-{int(turn_index)}",
            "status": "pending",
            "asked_turn": int(turn_index),
            "model_item_id": clarification_candidate.get("model_item_id"),
            "kind": clarification_candidate.get("kind"),
            "value": clarification_candidate.get("value"),
            "hypothesis_ids": list(clarification_candidate.get("linked_hypothesis_ids") or []),
            "reason": "high_value_uncertain_hypothesis_repeatedly_influenced_action",
            "question_jp": question,
            "low_pressure": True,
        }
        validation["pending"] = pending
        validation["status"] = "pending"
        state["active_validation"] = validation
        logic.update(
            {
                "intent": "functional_understanding_active_verify",
                "scene": "casual",
                "hidden_intent": "validate_before_repeating_a_high_value_guess",
                "reply_goal": "同じ推測を重ねず、一つだけ低圧で確認する",
                "core_message_jp": question,
                "response_mode": "targeted_clarification",
                "surface_act": "functional_understanding_active_verify",
                "dialogue_act": "targeted_low_pressure_validation",
                "payload_level": "low",
            }
        )
        changed_plan = True

    strategy = {
        "schema": VALIDATION_SCHEMA,
        "turn_index": int(turn_index),
        "changed_plan": changed_plan,
        "pending": deepcopy(pending) if pending else None,
        "communication_preference_applied": communication_applied,
        "selected_stable_count": len(active_stable),
        "selected_situational_count": len(active_situational),
        "selected_provisional_count": len(current_entries),
        "protected_direct_response": _protected_plan(logic, hypothesis),
        "direct_user_report": deepcopy(direct_user_report) if explicit_direct_report else None,
        "clarification_suppressed_by_direct_user_report": bool(
            explicit_direct_report and clarification_candidate and not pending
        ),
        "reason": (
            "actively_validate_repeated_uncertain_high_value_other_model"
            if changed_plan
            else (
                "explicit_user_report_outranks_provisional_clarification"
                if explicit_direct_report and clarification_candidate and not pending
                else "use_layered_model_with_bounded_uncertainty"
            )
        ),
    }
    logic["active_validation_strategy_v2_13"] = strategy
    return logic, state, strategy


def build_personhood_loop_trace(
    user_input,
    hypothesis,
    pragmatic_understanding,
    pragmatic_verification,
    longitudinal_model,
    model_update_trace,
    verification,
    appraisal,
    psyche_state,
    active_goal,
    plan,
):
    """Expose how other/self/relationship/persona jointly shape an action."""
    model = _ensure_model(longitudinal_model)
    psyche = deepcopy(psyche_state or {})
    trust = float(psyche.get("trust", 50.0) or 50.0)
    relationship_phase = "familiar" if trust >= 65 else "developing" if trust >= 45 else "cautious"
    validation = deepcopy((model.get("active_validation") or {}).get("pending"))
    verification_status = str((verification or {}).get("status") or "not_available")
    if verification_status == "contradicted":
        relationship_learning = "優先採納使用者更正；降低同類推測信心並撤銷舊假設"
    elif verification_status == "supported":
        relationship_learning = "小幅提高該類理解可靠度，但仍保留可修正性"
    else:
        relationship_learning = "證據不足，不把沉默或轉題當成確認"
    return {
        "schema": PERSONHOOD_LOOP_SCHEMA,
        "claim_scope": "personhood_oriented_functional_loop_not_consciousness_or_literal_human_copy",
        "research_priority": {
            "primary_question": "可運作地建模、預測並驗證人類的字面與言外溝通過程",
            "experimental_persona": "一ノ瀬うるは公開行為模型",
            "relationship": "Uruha 是人格與互動風格的具體實驗載體，不是 human pragmatic understanding 的研究目的本身",
        },
        "public_persona_provenance": {
            "positioning": "public-evidence-grounded Uruha persona model; not the real person",
            "allowed_basis": "網路上可觀察、可追溯的公開語言、風格、價值與互動傾向",
            "unknown_space": [
                "童年與未公開經歷",
                "私密關係與私人記憶",
                "未公開即時心理狀態",
            ],
            "unknown_policy": "保持空白或不確定；不得自行補完私人生命史",
            "persona_role_in_loop": "人格參與感知、在意、推論與表達，不只在最後改寫語氣",
        },
        "perceive_other": {
            "user_signal": str(user_input or ""),
            "current_hypothesis_id": (hypothesis or {}).get("hypothesis_id"),
            "known": deepcopy((hypothesis or {}).get("known") or []),
            "unknown": deepcopy((hypothesis or {}).get("unknown") or []),
            "longitudinal_other_model": model_summary(model),
            "human_pragmatic_understanding": deepcopy(pragmatic_understanding or {}),
            "active_layers": {
                layer: [
                    {
                        "model_item_id": row.get("model_item_id"),
                        "kind": row.get("kind"),
                        "value": row.get("value"),
                        "confidence": row.get("confidence"),
                        "status": row.get("status"),
                    }
                    for row in rows
                    if row.get("status") in {"active", "stale"}
                ][:6]
                for layer, rows in model["layers"].items()
            },
        },
        "self_state": {
            "mood": psyche.get("mood"),
            "trust": psyche.get("trust"),
            "active_goal_before_reply": active_goal,
            "persona_stance": [
                "ぶっきらぼうでも相手の自己申告を優先する",
                "分かったふりをせず、必要なら一つだけ確認する",
                "過度に迎合・世話焼きせず、低圧で関わる",
            ],
            "state_is_functional_not_subjective_claim": True,
        },
        "relationship_state": {
            "trust_score": psyche.get("trust"),
            "phase": relationship_phase,
            "stable_user_knowledge_count": sum(
                1 for row in model["layers"]["stable"] if row.get("status") == "active"
            ),
            "pending_validation": validation,
            "boundary": "關係狀態是可修正的運作資料，不等同真人私下關係或內心",
        },
        "persona_appraisal": {
            "existing_appraisal": deepcopy(appraisal or {}),
            "runtime_public_persona_appraisal": deepcopy(
                (plan or {}).get("public_persona_cognitive_appraisal_v2_13") or {}
            ),
            "pragmatic_label": (pragmatic_understanding or {}).get("pragmatic_label"),
            "literal_vs_implied_kept_separate": True,
            "acoustic_evidence": deepcopy((pragmatic_understanding or {}).get("acoustic_evidence") or {}),
            "other_model_uncertainty": (hypothesis or {}).get("uncertainty"),
            "typed_reliability": deepcopy(model.get("typed_calibration") or {}),
            "evaluation_rule": "人格立場與自我/關係狀態共同評估，不把人格留到最後只做語氣改寫",
        },
        "action_choice": {
            "intent": (plan or {}).get("intent"),
            "reply_goal": (plan or {}).get("reply_goal"),
            "response_mode": (plan or {}).get("response_mode"),
            "core_message_jp": (plan or {}).get("core_message_jp"),
            "other_model_used": bool((plan or {}).get("longitudinal_user_model_context")),
            "self_and_persona_used": bool(
                ((plan or {}).get("public_persona_cognitive_appraisal_v2_13") or {}).get(
                    "used_for_action"
                )
            ),
            "active_validation": deepcopy((plan or {}).get("active_validation_strategy_v2_13") or {}),
        },
        "learn_from_outcome": {
            "verification_status": verification_status,
            "pragmatic_verification_status": (pragmatic_verification or {}).get("status"),
            "relationship_learning": relationship_learning,
            "revisions": deepcopy((model_update_trace or {}).get("revisions") or []),
            "pragmatic_revisions": deepcopy((model_update_trace or {}).get("pragmatic_revisions") or []),
            "decay_events": deepcopy((model_update_trace or {}).get("decay_events") or []),
            "validation_resolution": deepcopy((model_update_trace or {}).get("validation_resolution")),
            "typed_calibration_updates": deepcopy(
                (model_update_trace or {}).get("typed_calibration_updates") or []
            ),
            "pragmatic_calibration_updates": deepcopy(
                (model_update_trace or {}).get("pragmatic_calibration_updates") or []
            ),
            "psychological_inference_written_as_fact": False,
        },
        "causal_order": [
            "perceive_other",
            "self_and_relationship_state",
            "persona_appraisal",
            "action_choice",
            "later_outcome_learning",
        ],
    }
