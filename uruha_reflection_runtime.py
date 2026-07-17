"""Grounded typed-reflection helpers shared by runtime and evaluations."""

from __future__ import annotations

import hashlib
import json
import os
import re

from rightbrain_language_quality import (
    ASCII_WORD_RE,
    AUDITED_CHINESE_SPECIFIC_RE,
    AUDITED_NONSTANDARD_CJK_RE,
    CHINESE_SPECIFIC_RE,
    FOREIGN_SCRIPT_RE,
    NONSTANDARD_CJK_RE,
    UNICODE_REPLACEMENT_CHAR,
)


REFLECTION_TYPES = frozenset({"semantic", "procedural", "interpretive", "none"})
TYPE_TO_COLLECTION = {
    "semantic": "wisdom",
    "procedural": "procedural",
    "interpretive": "wisdom",
}


def typed_reflection_runtime_enabled(environ=None):
    """Keep failed V4 reflection shadow-only unless research explicitly opts in."""
    source = os.environ if environ is None else environ
    return str(source.get("URUHA_ENABLE_TYPED_REFLECTION", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _contains_any(text, markers):
    lowered = str(text or "").lower()
    return any(marker.lower() in lowered for marker in markers)


def _matches_any(text, patterns):
    return any(
        re.search(pattern, str(text or ""), flags=re.IGNORECASE)
        for pattern in patterns
    )


def _looks_hypothetical_or_third_party(text):
    explicit_marker = _contains_any(
        text,
        (
            "如果有人",
            "假如有人",
            "只是舉例",
            "只是举例",
            "例如有人",
            "我朋友",
            "我同事",
            "我哥哥",
            "我姐姐",
            "我弟弟",
            "我妹妹",
            "不是我的習慣",
            "不是我的习惯",
            "他的習慣",
            "他的习惯",
            "她的習慣",
            "她的习惯",
            "if someone",
            "imagine a user",
            "a user who",
            "for example",
            "hypothetical",
            "not feedback from me",
            "not my preference",
            "my friend",
            "my coworker",
            "my brother",
            "my sister",
            "someone said",
            "友達は",
            "友達が",
            "同僚は",
            "同僚が",
            "兄は",
            "姉は",
            "弟は",
            "妹は",
            "例えば",
            "例として",
        ),
    )
    relationship_subject = _matches_any(
        text,
        (
            r"我(?:的)?(?:爸|媽|妈|父|母|哥哥|姐姐|弟弟|妹妹|朋友|同事|老師|老师|老闆|老板|伴侶|伴侣|男友|女友|家人)",
            r"\bmy\s+(?:father|mother|parent|brother|sister|friend|coworker|partner|teacher|boss|child|son|daughter)\b",
            r"(?:友達|同僚|父|母|兄|姉|弟|妹|恋人|先生|上司)(?:は|が)",
        ),
    )
    return explicit_marker or relationship_subject


def _is_interpretive_learning(text):
    owns_phrase = _matches_any(
        text,
        (
            r"我(?:只)?(?:說|说|回|用).{0,8}[『「'\"]",
            r"\bwhen\s+i\s+(?:say|use)\b",
            r"(?:私|うち)が.{0,8}[『「].+?[』」]",
        ),
    )
    explains_meaning = _contains_any(
        text,
        (
            "不是",
            "不代表",
            "其實",
            "其实",
            "通常是",
            "代表",
            "mean",
            "not that",
            "not refusing",
            "i am uncertain",
            "本当は",
            "意味",
            "我慢して",
            "気にして",
            "ことがある",
        ),
    )
    return owns_phrase and explains_meaning


def _is_procedural_learning(text):
    recurring_scope = _contains_any(
        text,
        (
            "你剛剛",
            "你刚刚",
            "下次",
            "以後",
            "以后",
            "之後",
            "之后",
            "每次",
            "next time",
            "from now on",
            "さっき",
            "次は",
            "今度は",
            "今後",
        ),
    ) or _matches_any(
        text,
        (
            r"(?:如果|假如|當|当).{0,24}(?:時|时)",
            r"\b(?:when|whenever|if)\s+(?:i|my)\b",
            r"(?:時|とき)は",
            r"(?:質問|依頼|お願い).{0,4}でも",
        ),
    )
    assistant_action = _matches_any(
        text,
        (
            r"(?:先|只|再).{0,16}(?:回答|說|说|給|给|問|问|推薦|推荐|確認|确认)",
            r"\b(?:ask|answer|pick|list|explain|give|recommend|confirm)\b",
            r"(?:聞|答|言|確認|選|勧|説明).{0,5}(?:て|で)(?:。|！|!|$)",
        ),
    )
    return recurring_scope and assistant_action


def _is_semantic_learning(text):
    if _contains_any(text, ("?", "？")):
        return False

    explicit_user = _matches_any(
        text,
        (
            r"我",
            r"\b(?:i|my|me)\b",
            r"(?:私|うち)",
        ),
    )
    implicit_japanese_experience = _contains_any(
        text,
        (
            "気持ち悪く",
            "かゆく",
            "痛く",
            "眠れなく",
            "集中できなく",
        ),
    ) and _contains_any(text, ("避けて", "飲まない", "食べない"))
    user_grounded = explicit_user or implicit_japanese_experience
    if not user_grounded:
        return False

    stable_preference_or_constraint = _contains_any(
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
            "不能",
            "避開",
            "usually",
            "always",
            "prefer",
            "favorite",
            " love ",
            " hate ",
            " avoid ",
            "cannot",
            "can't",
            "最近は",
            "いつも",
            "好き",
            "嫌い",
            "苦手",
            "避けて",
            "飲まない",
            "食べない",
        ),
    )
    transient = _contains_any(
        text,
        (
            "今天",
            "現在",
            "现在",
            "突然想",
            "today",
            "right now",
            "yesterday",
            "今ちょっと",
            "今日",
            "昨日",
        ),
    )
    causal_requirement = _matches_any(
        text,
        (
            r"\bi\s+need\b.+\bbecause\b.+\b(?:me|my)\b",
        ),
    ) and _matches_any(
        text,
        (
            r"^(?:on|during|after|before)\b",
            r"\bi\s+need\b.+\bto\s+[a-z]+\b",
        ),
    )
    return not transient and (stable_preference_or_constraint or causal_requirement)


def classify_reflection_type(user_input):
    """Classify only explicit, user-grounded learning opportunities."""
    text = str(user_input or "").strip()
    if not text or _looks_hypothetical_or_third_party(text):
        return "none"
    if _is_interpretive_learning(text):
        return "interpretive"
    if _is_procedural_learning(text):
        return "procedural"
    return "semantic" if _is_semantic_learning(text) else "none"


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


def reflection_surface_schema():
    return {
        "type": "object",
        "properties": {
            "content_jp": {"type": "string", "minLength": 1, "maxLength": 120},
            "trigger_jp": {"type": "string", "minLength": 1, "maxLength": 80},
        },
        "required": ["content_jp", "trigger_jp"],
        "additionalProperties": False,
    }


def reflection_surface_response_format():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "typed_reflection_surface_v4",
            "strict": True,
            "schema": reflection_surface_schema(),
        },
    }


def structured_extraction_system_prompt(reflection_type, retry_reasons=None):
    if reflection_type not in TYPE_TO_COLLECTION:
        raise ValueError(f"unsupported reflection type: {reflection_type}")
    retry_note = ""
    if retry_reasons:
        retry_note = (
            "\nThe previous surface was rejected for: "
            + ", ".join(str(item) for item in retry_reasons)
            + ". Rewrite once without weakening the source meaning."
        )
    return f"""
Generate only the Japanese gist fields for one explicit {reflection_type} reflection.
The program, not you, owns reflection type, evidence, provenance, and confidence.

- content_jp: concise Japanese meaning supported by the source utterance.
- trigger_jp: concise Japanese description of when this memory applies.
- Preserve negation, scope, preference, and response order exactly.
- Do not invent motives, diagnoses, facts, or stronger claims.
- Do not translate source phrases into Chinese. A non-Japanese phrase may appear only if copied exactly from the source utterance.
- Return only the JSON Schema fields.{retry_note}
""".strip()


def deterministic_reflection_fields(
    user_input,
    *,
    reflection_type,
    source_episode_id,
    grounding_confidence=0.95,
):
    evidence = str(user_input or "").strip()
    if reflection_type not in TYPE_TO_COLLECTION or not source_episode_id:
        return None
    if not evidence or len(evidence) > 160:
        return None
    return {
        "reflection_type": reflection_type,
        "collection": TYPE_TO_COLLECTION[reflection_type],
        "evidence_quote": evidence,
        "confidence": round(float(grounding_confidence), 4),
        "source_episode_id": str(source_episode_id),
        "source_user_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
    }


def _source_external_matches(pattern, text, source):
    external = []
    for match in pattern.finditer(text):
        token = match.group(0)
        if token and token not in source:
            external.append(token)
    return external


def validate_reflection_surface(payload, *, user_input):
    reasons = []
    if not isinstance(payload, dict):
        return {"valid": False, "retryable": False, "reasons": ["not_an_object"]}
    if set(payload) != {"content_jp", "trigger_jp"}:
        return {"valid": False, "retryable": False, "reasons": ["schema_keys"]}

    content = re.sub(r"\s+", " ", str(payload.get("content_jp") or "")).strip()
    trigger = re.sub(r"\s+", " ", str(payload.get("trigger_jp") or "")).strip()
    if not content:
        reasons.append("empty_content_jp")
    if not trigger:
        reasons.append("empty_trigger_jp")
    if content and not re.search(r"[\u3040-\u30ff]", content):
        reasons.append("missing_japanese_content")
    if trigger and not re.search(r"[\u3040-\u30ff]", trigger):
        reasons.append("missing_japanese_trigger")
    if len(content) > 120:
        reasons.append("content_too_long")
    if len(trigger) > 80:
        reasons.append("trigger_too_long")
    lowered = f"{content} {trigger}".lower()
    if any(marker in lowered for marker in ("no_rule", "rule:", "procedure:")):
        reasons.append("control_marker_leak")

    source = str(user_input or "")
    combined = f"{content}\n{trigger}"
    patterns = (
        CHINESE_SPECIFIC_RE,
        NONSTANDARD_CJK_RE,
        AUDITED_CHINESE_SPECIFIC_RE,
        AUDITED_NONSTANDARD_CJK_RE,
        FOREIGN_SCRIPT_RE,
        ASCII_WORD_RE,
    )
    external_tokens = []
    for pattern in patterns:
        external_tokens.extend(_source_external_matches(pattern, combined, source))
    if UNICODE_REPLACEMENT_CHAR in combined:
        external_tokens.append(UNICODE_REPLACEMENT_CHAR)
    if external_tokens:
        reasons.append("source_external_language:" + "|".join(dict.fromkeys(external_tokens)))

    retryable = bool(reasons) and all(
        reason.startswith(("source_external_language", "missing_japanese"))
        for reason in reasons
    )
    return {
        "valid": not reasons,
        "retryable": retryable,
        "reasons": reasons,
        "content_jp": content,
        "trigger_jp": trigger,
    }


def assemble_grounded_reflection(
    surface_payload,
    *,
    user_input,
    reflection_type,
    source_episode_id,
):
    base = deterministic_reflection_fields(
        user_input,
        reflection_type=reflection_type,
        source_episode_id=source_episode_id,
    )
    report = validate_reflection_surface(surface_payload, user_input=user_input)
    if base is None or not report["valid"]:
        return None, report
    result = {
        "reflection_type": base["reflection_type"],
        "content_jp": report["content_jp"],
        "trigger_jp": report["trigger_jp"],
        "evidence_quote": base["evidence_quote"],
        "confidence": base["confidence"],
    }
    validated = validate_reflection_payload(
        result,
        user_input=user_input,
        expected_type=reflection_type,
        source_episode_id=source_episode_id,
    )
    if validated is None:
        report = dict(report)
        report.update({"valid": False, "retryable": False})
        report["reasons"] = list(report["reasons"]) + ["assembled_payload_invalid"]
    return validated, report


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
