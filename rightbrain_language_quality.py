#!/usr/bin/env python3
"""Shared language-surface checks for RightBrain training, runtime, and evaluation."""

import re


JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
ASCII_WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F][A-Za-z0-9_\-\u00C0-\u024F]*")
CHINESE_SPECIFIC_RE = re.compile(
    r"[这吗么们没还让给说话這嗎麼們沒還讓說泠]|好了|不是|我想|你的|可以|為什麼|为什么"
)
# Characters here use Chinese simplified/traditional forms where normal Japanese uses another glyph.
NONSTANDARD_CJK_RE = re.compile(
    r"[调选个话这吗么们没还让给说为泠虑责应绪过样经觉开关实进问间东长门见车书风鱼鸟龙]"
    r"|[无围强复简单體圍國學氣會來處變與樂臺]"
    r"|范围|範圍"
)
POLITE_RE = re.compile(
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)"
    r"(?:よね|よ|ね)?(?:[。！？!?、]|$)"
)
INSTRUCTION_MARKERS = (
    "required_semantic",
    "speech_moves",
    "leftbrain",
    "ユーザー入力",
    "出力契約",
    "回答を生成",
)
UNICODE_REPLACEMENT_CHAR = "\ufffd"


def has_japanese(text):
    return bool(JAPANESE_RE.search(str(text or "")))


def has_bad_language(text, reject_latin=True):
    text = str(text or "")
    return bool(
        CHINESE_SPECIFIC_RE.search(text)
        or NONSTANDARD_CJK_RE.search(text)
        or UNICODE_REPLACEMENT_CHAR in text
        or (reject_latin and ASCII_WORD_RE.search(text))
    )
