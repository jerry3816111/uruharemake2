"""Grounded typed-reflection helpers shared by runtime and evaluations."""

from __future__ import annotations

import hashlib
import json
import re


REFLECTION_TYPES = frozenset({"semantic", "procedural", "interpretive", "none"})
TYPE_TO_COLLECTION = {
    "semantic": "wisdom",
    "procedural": "procedural",
    "interpretive": "wisdom",
}


def _contains_any(text, markers):
    lowered = str(text or "").lower()
    return any(marker.lower() in lowered for marker in markers)


def _looks_hypothetical_or_third_party(text):
    return _contains_any(
        text,
        (
            "如果有人",
            "假如有人",
            "只是舉例",
            "只是举例",
            "例如有人",
            "我朋友",
            "我同事",
            "他的習慣",
            "他的习惯",
            "她的習慣",
            "她的习惯",
            "if someone",
            "for example",
            "hypothetical",
            "not feedback from me",
            "my friend",
            "my coworker",
            "someone said",
            "友達は",
            "同僚は",
            "例えば",
            "例として",
        ),
    )


def classify_reflection_type(user_input):
    """Classify only explicit, user-grounded learning opportunities."""
    text = str(user_input or "").strip()
    if not text or _looks_hypothetical_or_third_party(text):
        return "none"

    interpretive_subject = _contains_any(
        text,
        ("我說", "我说", "when i say", "when i use", "うちが", "私が"),
    )
    interpretive_meaning = _contains_any(
        text,
        (
            "不是",
            "不代表",
            "其實",
            "其实",
            "mean",
            "not that",
            "本当は",
            "って言う時",
            "という時",
            "意味",
        ),
    )
    if interpretive_subject and interpretive_meaning:
        return "interpretive"

    feedback_context = _contains_any(
        text,
        (
            "你剛剛",
            "你刚刚",
            "下次",
            "以後",
            "以后",
            "不要每次",
            "when i ask",
            "you just",
            "next time",
            "from now on",
            "before explaining",
            "さっき",
            "次は",
            "今度は",
            "今後",
        ),
    )
    feedback_directive = _contains_any(
        text,
        (
            "先",
            "只給",
            "只给",
            "只問",
            "只问",
            "一個",
            "一个",
            "回答",
            "確認",
            "确认",
            "answer",
            "ask",
            "explain",
            "結論",
            "一つ",
            "一回",
            "言って",
            "聞いて",
        ),
    )
    if feedback_context and feedback_directive:
        return "procedural"

    first_person = _contains_any(
        text,
        (
            "我通常",
            "我平常",
            "我喜歡",
            "我喜欢",
            "我討厭",
            "我讨厌",
            "我不能",
            "我不喝",
            "我不吃",
            "i usually",
            "i always",
            "i prefer",
            "i like",
            "i love",
            "i hate",
            "i cannot",
            "i can't",
            "my favorite",
            "最近は",
            "うちは",
            "私は",
        ),
    )
    durable_state = _contains_any(
        text,
        (
            "通常",
            "平常",
            "總是",
            "总是",
            "喜歡",
            "喜欢",
            "討厭",
            "讨厌",
            "失眠",
            "不能",
            "不喝",
            "usually",
            "always",
            "prefer",
            "favorite",
            " like ",
            " love ",
            " hate ",
            "最近は",
            "いつも",
            "好き",
            "嫌い",
            "苦手",
            "飲まない",
            "食べない",
        ),
    )
    return "semantic" if first_person and durable_state else "none"


def extraction_system_prompt(reflection_type):
    if reflection_type not in TYPE_TO_COLLECTION:
        raise ValueError(f"unsupported reflection type: {reflection_type}")
    return f"""
You extract ONE grounded reflection from explicit user evidence.
Allowed reflection_type for this call: {reflection_type}

Return ONLY valid JSON with exactly these keys:
{{
  "reflection_type": "{reflection_type}",
  "content_jp": "one concise Japanese memory rule",
  "trigger_jp": "short Japanese description of when it applies",
  "evidence_quote": "one exact contiguous quote copied from the user utterance",
  "confidence": 0.0
}}

Rules:
- Do not invent facts, motives, diagnoses, or preferences.
- evidence_quote must be copied exactly from the user utterance.
- content_jp and trigger_jp must be natural Japanese and contain kana.
- semantic: store a durable first-person user fact only.
- procedural: store how the assistant should respond next time to explicit feedback.
- interpretive: store what the user's own phrase tends to mean and how to check it.
- Never output Rule:, Procedure:, NO_RULE, markdown, or extra keys.
- If the evidence cannot support the allowed type, set reflection_type to none and use empty strings.
""".strip()


def parse_json_object(raw_text):
    text = str(raw_text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for pattern in (r"```json\s*(\{.*?\})\s*```", r"(\{.*\})"):
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        try:
            return json.loads(match.group(1))
        except Exception:
            continue
    return None


def validate_reflection_payload(
    payload,
    *,
    user_input,
    expected_type,
    source_episode_id,
    minimum_confidence=0.65,
):
    if not isinstance(payload, dict) or expected_type not in TYPE_TO_COLLECTION:
        return None
    if set(payload) != {
        "reflection_type",
        "content_jp",
        "trigger_jp",
        "evidence_quote",
        "confidence",
    }:
        return None
    reflection_type = str(payload.get("reflection_type") or "").strip().lower()
    if reflection_type != expected_type:
        return None
    content = re.sub(r"\s+", " ", str(payload.get("content_jp") or "")).strip()
    trigger = re.sub(r"\s+", " ", str(payload.get("trigger_jp") or "")).strip()
    evidence = str(payload.get("evidence_quote") or "").strip()
    try:
        confidence = float(payload.get("confidence"))
    except (TypeError, ValueError):
        return None
    if confidence < minimum_confidence or confidence > 1.0:
        return None
    if not source_episode_id or not content or not trigger or not evidence:
        return None
    if evidence not in str(user_input or ""):
        return None
    if not re.search(r"[\u3040-\u30ff]", content) or not re.search(r"[\u3040-\u30ff]", trigger):
        return None
    if len(content) > 120 or len(trigger) > 80 or len(evidence) > 160:
        return None
    forbidden = f"{content} {trigger}".lower()
    if "no_rule" in forbidden or "rule:" in forbidden or "procedure:" in forbidden:
        return None
    return {
        "reflection_type": reflection_type,
        "collection": TYPE_TO_COLLECTION[reflection_type],
        "content_jp": content,
        "trigger_jp": trigger,
        "evidence_quote": evidence,
        "confidence": round(confidence, 4),
        "source_episode_id": str(source_episode_id),
        "source_user_sha256": hashlib.sha256(
            str(user_input or "").encode("utf-8")
        ).hexdigest(),
    }


def reflection_document(result):
    reflection_type = result["reflection_type"]
    prefix = "Procedure" if reflection_type == "procedural" else "Reflection"
    return (
        f"{prefix}[{reflection_type}]: {result['content_jp']} | "
        f"Trigger: {result['trigger_jp']}"
    )
