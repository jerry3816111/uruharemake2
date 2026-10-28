"""Traceable, runtime-only user-model hypotheses for UruhaBrain V2.12.

This module deliberately models *functional* understanding.  It records what
the system observed, what it inferred, what remains unknown, and what would
support or contradict the inference on the next turn.  It does not claim a
subjective mental state and its provisional hypotheses are not long-term user
facts.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy


SCHEMA = "uruha_user_mental_state_hypothesis_v2_12"
VERIFICATION_SCHEMA = "uruha_hypothesis_verification_v2_12"
CALIBRATION_SCHEMA = "uruha_hypothesis_calibration_v2_12"
HIGH_UNCERTAINTY_THRESHOLD = 0.55


def _clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(upper, float(value)))


def _contains(text, markers):
    lowered = str(text or "").lower()
    return any(str(marker).lower() in lowered for marker in markers)


def semantic_features(user_input):
    """Return auditable multilingual surface features without mind-reading."""
    text = str(user_input or "").strip()
    lowered = text.lower()
    features = set()

    marker_groups = {
        "correction": [
            "不是", "并不是", "並不是", "其實", "其实", "你搞錯", "你搞错",
            "違う", "じゃなくて", "勘違い", "not sad", "not what", "actually",
            "you got it wrong", "i meant",
        ],
        "confirmation": ["嗯", "對", "对", "沒錯", "没错", "そう", "うん", "はい", "yes", "right", "exactly"],
        "tired": ["累", "疲", "しんど", "exhausted", "tired", "no energy", "気力がない"],
        "rest_action": ["休息", "去睡", "睡了", "睡覺", "睡觉", "寝る", "休む", "おやすみ", "go to sleep", "take a rest"],
        "sad": ["難過", "难过", "傷心", "伤心", "低落", "悲しい", "落ち込", "sad", "upset"],
        "excited": ["興奮", "兴奋", "開心", "开心", "太爽", "期待", "嬉しい", "楽しみ", "excited", "thrilled", "happy", "looking forward"],
        "ambiguous_mood": [
            "心情怪", "感覺怪", "感觉怪", "靜不下來", "静不下来", "坐不住",
            "停不下來", "停不下来", "轉個不停", "转个不停",
            "気分が変", "落ち着かない", "そわそわ", "feeling weird", "feel weird",
            "頭が止ま", "頭停ま", "mind won't stop", "thoughts keep racing", "racing thoughts",
            "can't sit still", "cannot sit still", "can't settle down",
        ],
        "support_request": ["陪我", "聽我說", "听我说", "安慰", "そばにいて", "話聞いて", "listen to me", "stay with me"],
        "food": ["吃", "喝", "食べ", "飲", "food", "eat", "drink", "dinner", "lunch"],
        "identity": ["你是誰", "你是谁", "who are you", "うるは", "一ノ瀬", "お前は誰", "あなたは誰"],
        "memory": ["記得", "记得", "覚えて", "remember", "之前說", "之前说", "前に言"],
        "relationship": ["想我", "喜歡我", "喜欢我", "miss me", "like me", "うちのこと", "好きか"],
        "safety": ["不想活", "自殺", "自杀", "死にたい", "kill myself", "hurt myself"],
    }
    for feature, markers in marker_groups.items():
        if _contains(lowered, markers):
            features.add(feature)

    compositional_arousal_patterns_m36 = (
        r"(?:想法|思緒|思绪|腦中|脑中).{0,24}(?:停不住|停不下|亂跑|乱跑|一直在跑|一個接一個|一个接一个)",
        r"\b(?:thoughts?|ideas?|mind).{0,48}(?:racing|bouncing|circling|won't\s+stop|will\s+not\s+stop)\b",
        r"頭が.{0,16}(?:止ま(?:らない|んない|ってくれない)|回りっぱなし|休まらない)",
    )
    if any(re.search(pattern, lowered, re.I) for pattern in compositional_arousal_patterns_m36):
        features.add("ambiguous_mood")

    if re.search(r"[?？]", text) or _contains(
        lowered,
        ["嗎", "吗", "什麼", "什么", "怎麼", "怎么", "為什麼", "为什么", "どう", "なに", "何", "why", "what", "how", "can you", "could you"],
    ):
        features.add("question")

    ambiguous_fragments = [
        "你知道吧", "你懂吧", "那個呢", "那个呢", "就是那個", "就是那个",
        "你懂的", "分かるよね", "わかるよね", "あれだよ", "you know", "that thing",
    ]
    if _contains(lowered, ambiguous_fragments):
        features.add("ambiguous_reference")

    return sorted(features)


def _human_intent(actual_intent, features):
    feature_set = set(features)
    actual_intent = str(actual_intent or "chat")
    if "safety" in feature_set:
        return "表達高風險狀態，需要安全優先回應"
    if "correction" in feature_set or actual_intent == "correction_followup":
        return "修正系統先前的理解"
    if "identity" in feature_set or actual_intent == "self_intro":
        return "確認うるは的自我身分"
    if "memory" in feature_set or actual_intent.startswith("recall_"):
        return "要求從已知對話記憶回答"
    if "tired" in feature_set:
        return "分享疲憊，可能需要低壓支持"
    if "ambiguous_mood" in feature_set:
        return "分享尚未說明原因的情緒變化"
    if "relationship" in feature_set:
        return "確認彼此關係或在意程度"
    if "food" in feature_set:
        return "延續飲食相關話題"
    if "ambiguous_reference" in feature_set:
        return "可能在指涉共同上下文，但對象未明"
    if "question" in feature_set:
        return "提出問題並期待直接回應"
    if actual_intent not in {"", "chat", "chat_continuation"}:
        return f"可能在進行 {actual_intent} 對話行為"
    return "延續一般對話"


def _emotion_need(features):
    feature_set = set(features)
    if "safety" in feature_set:
        return "高風險痛苦／需要立即安全確認", 0.96, True
    if "excited" in feature_set:
        return "興奮或正向高喚起", 0.9, True
    if "sad" in feature_set:
        return "低落或難過／可能需要被聽見", 0.9, True
    if "tired" in feature_set:
        return "疲憊／可能需要降低互動負擔", 0.88, True
    if "ambiguous_mood" in feature_set:
        return "可能低落，也可能只是情緒強度變化", 0.58, False
    if "support_request" in feature_set:
        return "可能需要陪伴或傾聽", 0.82, False
    return "尚不明", 0.2, False


def _dialogue_goal(features):
    feature_set = set(features)
    if "correction" in feature_set:
        return "讓系統承認並改正原先推測"
    if "safety" in feature_set:
        return "先確認當下安全並降低風險"
    if "rest_action" in feature_set:
        return "結束或降低互動負擔"
    if "support_request" in feature_set or "tired" in feature_set or "sad" in feature_set:
        return "被接住，或取得不施壓的下一步"
    if "identity" in feature_set:
        return "得到一致、直接的自我身分回答"
    if "memory" in feature_set:
        return "核對系統是否真的記得而非捏造"
    if "question" in feature_set:
        return "取得與問題相符的回答"
    if "ambiguous_reference" in feature_set:
        return "確認系統能否接上未明說的上下文"
    return "維持對話並觀察回應"


def _base_confidence(actual_intent, features):
    feature_set = set(features)
    if feature_set.intersection({"safety", "correction", "identity", "memory"}):
        return 0.88
    if feature_set.intersection({"tired", "sad", "excited", "rest_action"}):
        return 0.84
    if "ambiguous_mood" in feature_set:
        return 0.58
    if "ambiguous_reference" in feature_set:
        return 0.38
    if str(actual_intent or "") not in {"", "chat", "chat_continuation"}:
        return 0.72
    if "question" in feature_set:
        return 0.66
    return 0.52


def _prediction(features, hypothesis_id, confidence):
    feature_set = set(features)
    if "safety" in feature_set:
        expected_feature = "safety_followup"
        action = "回報當下是否安全或是否有人可聯絡"
    elif feature_set.intersection({"tired", "sad", "support_request"}):
        expected_feature = "rest_or_support_followup"
        action = "補充狀態、確認要休息，或回應支持是否合適"
    elif "ambiguous_mood" in feature_set:
        expected_feature = "emotion_clarification"
        action = "補充真正情緒，或否定系統的初始推測"
    elif "correction" in feature_set:
        expected_feature = "correction_resolution"
        action = "確認修正是否正確，或再補一個線索"
    elif "identity" in feature_set:
        expected_feature = "identity_followup"
        action = "確認身分回答，或追問角色細節"
    elif "memory" in feature_set:
        expected_feature = "memory_confirmation_or_correction"
        action = "確認回想是否正確，或指出錯誤"
    elif "food" in feature_set:
        expected_feature = "food_followup"
        action = "延續食物選擇或回應偏好"
    elif "relationship" in feature_set:
        expected_feature = "relationship_followup"
        action = "追問或回應彼此的在意程度"
    elif "ambiguous_reference" in feature_set:
        expected_feature = "clarification_reply"
        action = "補上所指對象或話題"
    elif "question" in feature_set:
        expected_feature = "answer_evaluation"
        action = "評估回答是否切中問題並繼續追問"
    else:
        expected_feature = "chat_continuation"
        action = "延續目前話題或自然轉換話題"
    return {
        "schema": "uruha_next_user_action_prediction_v2_12",
        "based_on_hypothesis_id": hypothesis_id,
        "epistemic_status": "prediction",
        "expected_feature": expected_feature,
        "next_user_action": action,
        "confidence": round(_clamp(confidence * 0.82, 0.2, 0.88), 3),
        "falsifiers": [
            "使用者明確否定本輪推測",
            "下一輪出現與預期語義相反的直接自述",
            "下一輪完全轉換到不相容的對話目標",
        ],
    }


def build_user_mental_state_hypothesis(
    user_input,
    actual_signal=None,
    appraisal=None,
    attention_frame=None,
    turn_index=0,
    calibration_state=None,
):
    actual_signal = actual_signal or {}
    appraisal = appraisal or {}
    attention_frame = attention_frame or {}
    calibration_state = calibration_state or {}
    text = str(user_input or "").strip()
    features = semantic_features(text)
    feature_set = set(features)
    actual_intent = str(actual_signal.get("actual_intent") or "chat")
    base_confidence = _base_confidence(actual_intent, features)
    multiplier = float(calibration_state.get("confidence_multiplier", 1.0) or 1.0)
    confidence = _clamp(base_confidence * multiplier, 0.2, 0.94)
    uncertainty = round(1.0 - confidence, 3)
    emotion_value, emotion_confidence, direct_emotion = _emotion_need(features)
    hypothesis_seed = f"{turn_index}|{text}|{actual_intent}".encode("utf-8")
    hypothesis_id = f"hyp-{int(turn_index):04d}-{hashlib.sha256(hypothesis_seed).hexdigest()[:10]}"

    known = [
        {
            "field": "user_utterance",
            "value": text,
            "epistemic_status": "known_observation",
            "source": "current_user_input",
        }
    ]
    if direct_emotion:
        known.append(
            {
                "field": "explicit_self_report",
                "value": emotion_value,
                "epistemic_status": "known_as_user_report_not_objective_fact",
                "source": "current_user_input",
            }
        )

    evidence = [
        {
            "evidence_id": f"{hypothesis_id}:input",
            "source_kind": "current_user_input",
            "source_ref": "turn-input",
            "observed": text,
            "interpretation": _human_intent(actual_intent, features),
            "supports": ["possible_intent", "dialogue_goal"],
            "weight": 1.0,
            "epistemic_status": "known_observation",
        },
        {
            "evidence_id": f"{hypothesis_id}:classifier",
            "source_kind": "rule_classifier",
            "source_ref": "actual_signal",
            "observed": actual_intent,
            "interpretation": "分類器輸出只作為推測證據，不當成使用者心理事實",
            "supports": ["possible_intent"],
            "weight": 0.62,
            "epistemic_status": "machine_inference",
        },
    ]
    trace_ids = [str(item) for item in attention_frame.get("selected_memory_trace_ids") or [] if item]
    if trace_ids:
        evidence.append(
            {
                "evidence_id": f"{hypothesis_id}:memory",
                "source_kind": "selected_working_memory",
                "source_ref": trace_ids[:4],
                "observed": attention_frame.get("dominant_source") or "selected memory context",
                "interpretation": "只影響當輪理解，不把推測回寫成使用者事實",
                "supports": ["dialogue_goal"],
                "weight": 0.35,
                "epistemic_status": "context_evidence",
            }
        )

    if "ambiguous_mood" in feature_set:
        alternatives = [
            {"value": "其實是興奮或期待，不是低落", "confidence": 0.34, "epistemic_status": "alternative_inference"},
            {"value": "只是描述難以命名的感受", "confidence": 0.28, "epistemic_status": "alternative_inference"},
        ]
    elif "ambiguous_reference" in feature_set:
        alternatives = [
            {"value": "只是隨口接話，沒有特定隱含需求", "confidence": 0.34, "epistemic_status": "alternative_inference"},
            {"value": "期待延續上一個話題", "confidence": 0.32, "epistemic_status": "alternative_inference"},
        ]
    elif feature_set.intersection({"tired", "sad", "support_request"}):
        alternatives = [
            {"value": "只是在陳述狀態，不想收到建議", "confidence": 0.3, "epistemic_status": "alternative_inference"},
            {"value": "希望短暫陪伴而非解決問題", "confidence": 0.26, "epistemic_status": "alternative_inference"},
        ]
    else:
        alternatives = [
            {"value": "可能只是維持社交節奏", "confidence": 0.28, "epistemic_status": "alternative_inference"},
            {"value": "可能有尚未說出的具體目標", "confidence": 0.24, "epistemic_status": "alternative_inference"},
        ]

    unknown = []
    if emotion_value == "尚不明" or not direct_emotion:
        unknown.append({"field": "actual_emotion", "reason": "使用者未直接確認", "epistemic_status": "unknown"})
    if feature_set.intersection({"ambiguous_reference", "ambiguous_mood"}):
        unknown.append({"field": "referent_or_cause", "reason": "缺少可唯一定位的線索", "epistemic_status": "unknown"})
    unknown.append({"field": "whether_advice_is_wanted", "reason": "除非使用者明說，不能由情緒直接推出", "epistemic_status": "unknown"})

    hypothesis = {
        "schema": SCHEMA,
        "hypothesis_id": hypothesis_id,
        "turn_index": int(turn_index),
        "claim_scope": "functional_runtime_user_model_not_subjective_consciousness",
        "epistemic_status": "provisional_inference",
        "known": known,
        "inferred": {
            "possible_intent": {
                "value": _human_intent(actual_intent, features),
                "confidence": round(confidence, 3),
                "epistemic_status": "inferred",
            },
            "emotion_or_need": {
                "value": emotion_value,
                "confidence": round(_clamp(emotion_confidence * multiplier, 0.2, 0.96), 3),
                "epistemic_status": "inferred_unless_explicit_user_report",
            },
            "dialogue_goal": {
                "value": _dialogue_goal(features),
                "confidence": round(_clamp(confidence * 0.9, 0.2, 0.9), 3),
                "epistemic_status": "inferred",
            },
        },
        "evidence": evidence,
        "alternative_hypotheses": alternatives,
        "unknown": unknown,
        "semantic_features": features,
        "confidence": round(confidence, 3),
        "uncertainty": uncertainty,
        "confidence_band": "high" if confidence >= 0.78 else "medium" if confidence >= 0.55 else "low",
        "memory_policy": {
            "storage_scope": "runtime_trace_only",
            "fact_write_allowed": False,
            "reason": "未驗證心理推測不得寫成事實性長期記憶",
        },
    }
    hypothesis["prediction"] = _prediction(features, hypothesis_id, confidence)
    return hypothesis


def _current_verification_feature(features):
    feature_set = set(features)
    if "safety" in feature_set:
        return "safety_followup"
    if feature_set.intersection({"rest_action", "tired", "sad", "support_request"}):
        return "rest_or_support_followup"
    if "excited" in feature_set or "ambiguous_mood" in feature_set:
        return "emotion_clarification"
    if "correction" in feature_set:
        return "correction_resolution"
    if "identity" in feature_set:
        return "identity_followup"
    if "memory" in feature_set:
        return "memory_confirmation_or_correction"
    if "food" in feature_set:
        return "food_followup"
    if "relationship" in feature_set:
        return "relationship_followup"
    if "question" in feature_set:
        return "answer_evaluation"
    if "ambiguous_reference" in feature_set:
        return "clarification_reply"
    return "chat_continuation"


def verify_previous_hypothesis(previous_hypothesis, current_user_input, current_actual_signal=None, turn_index=0):
    previous = deepcopy(previous_hypothesis or {})
    if not previous:
        return {
            "schema": VERIFICATION_SCHEMA,
            "turn_index": int(turn_index),
            "status": "not_available",
            "summary": "第一輪，尚無上一輪假設可驗證",
            "prediction_error": None,
            "previous_hypothesis_id": None,
            "evidence": [],
        }

    current_features = semantic_features(current_user_input)
    feature_set = set(current_features)
    prediction = previous.get("prediction") or {}
    expected = str(prediction.get("expected_feature") or "")
    actual = _current_verification_feature(current_features)
    previous_emotion = str(((previous.get("inferred") or {}).get("emotion_or_need") or {}).get("value") or "")
    explicit_conflict = bool(
        "correction" in feature_set
        or ("低落" in previous_emotion and "excited" in feature_set)
        or ("難過" in previous_emotion and "excited" in feature_set)
        or ("興奮" in previous_emotion and "sad" in feature_set)
    )

    if explicit_conflict:
        status = "contradicted"
        error = 1.0
        summary = "下一輪明確否定或提供相反自述；保留原推測並建立修正版"
        reason = "explicit_correction_or_semantic_conflict"
    elif expected == actual:
        status = "supported"
        error = 0.0
        summary = "下一輪出現與預測相符的行為或語義"
        reason = "expected_semantic_feature_observed"
    elif expected == "rest_or_support_followup" and feature_set.intersection({"confirmation", "rest_action", "tired", "sad", "support_request"}):
        status = "supported"
        error = 0.0
        summary = "下一輪支持需要休息或低壓支持的預測"
        reason = "support_followup_observed"
    elif "confirmation" in feature_set and expected not in {"clarification_reply", "emotion_clarification"}:
        status = "supported"
        error = 0.15
        summary = "下一輪以確認訊號弱支持原預測"
        reason = "confirmation_signal_observed"
    else:
        status = "uncertain"
        error = 0.5
        summary = "下一輪不足以支持或否定；不把缺少證據當成正確"
        reason = "insufficient_comparable_evidence"

    return {
        "schema": VERIFICATION_SCHEMA,
        "turn_index": int(turn_index),
        "status": status,
        "summary": summary,
        "reason": reason,
        "previous_hypothesis_id": previous.get("hypothesis_id"),
        "previous_hypothesis_snapshot": previous,
        "predicted_feature": expected,
        "observed_feature": actual,
        "prediction_error": error,
        "evidence": [
            {
                "source_kind": "next_user_input",
                "observed": str(current_user_input or ""),
                "semantic_features": current_features,
                "epistemic_status": "known_observation",
            },
            {
                "source_kind": "rule_classifier",
                "observed": str((current_actual_signal or {}).get("actual_intent") or ""),
                "epistemic_status": "machine_inference",
            },
        ],
        "update_policy": "retain_original_append_verification_and_rebuild_current_hypothesis",
    }


def update_calibration(calibration_state, verification):
    state = {
        "schema": CALIBRATION_SCHEMA,
        "supported": 0,
        "contradicted": 0,
        "uncertain": 0,
        "confidence_multiplier": 1.0,
        "last_adjustment": 0.0,
        "last_reason": "no_previous_hypothesis",
    }
    state.update(deepcopy(calibration_state or {}))
    status = str((verification or {}).get("status") or "not_available")
    if status == "supported":
        state["supported"] = int(state.get("supported", 0)) + 1
        adjustment = 0.03
        reason = "supported_prediction_small_confidence_increase"
    elif status == "contradicted":
        state["contradicted"] = int(state.get("contradicted", 0)) + 1
        adjustment = -0.1
        reason = "contradicted_prediction_stronger_confidence_decrease"
    elif status == "uncertain":
        state["uncertain"] = int(state.get("uncertain", 0)) + 1
        adjustment = -0.01
        reason = "uncertain_outcome_no_positive_credit"
    else:
        adjustment = 0.0
        reason = "no_previous_hypothesis"
    state["confidence_multiplier"] = round(
        _clamp(float(state.get("confidence_multiplier", 1.0)) + adjustment, 0.68, 1.08),
        3,
    )
    state["last_adjustment"] = adjustment
    state["last_reason"] = reason
    state["last_verification_status"] = status
    state["sample_count"] = int(state.get("supported", 0)) + int(state.get("contradicted", 0)) + int(state.get("uncertain", 0))
    return state


def apply_hypothesis_to_plan(logic, hypothesis, actual_signal=None):
    """Use uncertainty as a real planning control, not a prompt decoration."""
    plan = deepcopy(logic or {})
    hypothesis = hypothesis or {}
    actual_signal = actual_signal or {}
    scene = str(plan.get("scene") or actual_signal.get("actual_scene") or "casual")
    intent = str(plan.get("intent") or actual_signal.get("actual_intent") or "chat")
    uncertainty = float(hypothesis.get("uncertainty", 1.0) or 0.0)
    protected = bool(
        scene in {"boundary", "refusal", "ooc_defense"}
        or intent in {"crisis_support", "sexual_boundary", "abuse_pushback", "self_intro"}
        or intent.startswith("recall_")
        or "safety" in set(hypothesis.get("semantic_features") or [])
    )

    strategy = {
        "schema": "uruha_hypothesis_aware_reply_strategy_v2_12",
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "hypothesis_confidence": hypothesis.get("confidence"),
        "uncertainty": round(uncertainty, 3),
        "threshold": HIGH_UNCERTAINTY_THRESHOLD,
        "protected_direct_response": protected,
        "used_for_planning": True,
    }
    if uncertainty >= HIGH_UNCERTAINTY_THRESHOLD and not protected:
        strategy.update(
            {
                "strategy": "low_pressure_clarification",
                "reason": "high_uncertainty_do_not_pretend_to_know_user_mind",
                "changed_plan": True,
                "pre_change_intent": intent,
            }
        )
        plan.update(
            {
                "intent": "functional_understanding_clarify",
                "scene": "casual",
                "hidden_intent": "understand_before_claiming",
                "reply_goal": "分かったふりをせず、最小限の追加線索を自然な日本語で尋ねる",
                "core_message_jp": "まだ読み切れない。どの話か少しだけ教えて。",
                "response_mode": "clarify_light",
                "surface_act": "functional_understanding_clarify",
                "dialogue_act": "low_pressure_clarification",
                "user_belief": "指涉、情緒或需要はまだ確定できない",
                "my_hidden_knowledge": "推測を事実扱いせず、一つだけ手掛かりを求める",
                "user_expectation": "決めつけず自然に確認する",
                "payload_level": "low",
            }
        )
        constraints = deepcopy(plan.get("constraints") or {})
        constraints.update({"sentence_count": 2, "max_chars": max(34, int(constraints.get("max_chars", 0) or 0))})
        plan["constraints"] = constraints
    else:
        strategy.update(
            {
                "strategy": "direct_but_uncertainty_bounded",
                "reason": "evidence_sufficient_or_safety_direct_response_required",
                "changed_plan": False,
            }
        )
    plan["functional_understanding_strategy"] = strategy
    return plan


def runtime_trace_projection(hypothesis):
    """Return the public runtime projection; explicitly never a fact-memory row."""
    return deepcopy(hypothesis or {})
