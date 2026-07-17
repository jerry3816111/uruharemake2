#!/usr/bin/env python3
"""Behavioral snapshot of the pre-candidate reflection type classifier."""

from __future__ import annotations


LEGACY_RUNTIME_COMMIT = "9a0b23d501c82ec36f94530f1fc62f3cbcb45aab"
LEGACY_RUNTIME_SHA256 = "1d818e4274efff26decb572d5a4d47c032fbf2cf65a4bad67cd508d2e5768bdc"


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
    """Classify with the exact pre-candidate decision rules."""
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
