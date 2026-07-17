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
