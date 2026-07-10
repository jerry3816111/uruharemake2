#!/usr/bin/env python3
"""Shared language-surface checks for RightBrain training, runtime, and evaluation."""

import re


JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
ASCII_WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F][A-Za-z0-9_\-\u00C0-\u024F]*")
# Surface artifacts that are not words, so ASCII_WORD_RE will not catch them.
# These appeared in model replies such as "何 ?" and "><" and should not pass
# as clean casual Japanese.
ASCII_SYMBOL_ARTIFACT_RE = re.compile(
    r"(?:"
    r"[<>]{2,}"
    r"|[（(]?\s*[>＜][_<＿]?[<＞]\s*[)）]?"
    r"|(?<=[ぁ-んァ-ヶー一-龠])\s+[!?](?:\s|$)"
    r"|[!?]\s*(?=[ぁ-んァ-ヶー一-龠])"
    r")"
)
# Audited surface defects from real model output.  Keep the expressions narrow:
# natural phrases such as "大丈夫だよ" and "お疲れ様" must remain available.
AWKWARD_OR_CAREGIVER_SURFACE_RE = re.compile(
    r"(?:"
    r"今日のお疲れ様(?:ね|だね)"
    r"|休息(?:する|して).{0,12}(?:良いくらい|いいよ|大事|わけ)"
    r"|控えめて"
    r"|コーヒーやりた"
    r"|しててよ"
    r")"
)
# Japanese meta-language that describes how the system should answer instead
# of speaking to the user. Match response-plan grammar, not isolated verbs:
# "あとで返す" remains a valid user-facing promise.
JAPANESE_RESPONSE_PLAN_LEAK_RE = re.compile(
    r"(?:"
    r"(?:よう(?:に)?|自然に|短く|直接|軽く|具体的に)"
    r"(?:返す|聞き返す|言い直す|促す)"
    r"|(?:不安|気持ち|関係|意図|前提|文脈|状況|誤解).{0,48}"
    r"(?:認め|受け止め|拾).{0,48}(?:返す|聞き返す|言い直す|促す)"
    r"|(?:を拾って|を認めて).{0,20}(?:返す|言い直す)"
    r"|(?:作品名|曲名|名前|どの部分).{0,32}(?:確認する|聞き返す)"
    r")"
)
FOREIGN_SCRIPT_RE = re.compile(r"[\u0400-\u04FF\u0E00-\u0E7F\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]")
CHINESE_SPECIFIC_RE = re.compile(
    r"[这吗么们没还让给说话這嗎麼們沒還讓說泠]"
    r"|好了|不是|我想|你的|可以|為什麼|为什么|是少|较好|好哦|咖啡"
)
# Characters here use Chinese simplified/traditional forms where normal Japanese uses another glyph.
NONSTANDARD_CJK_RE = re.compile(
    r"[调选个话这吗么们没还让给说为泠虑责应绪过样经觉开关实进问间东长门见车书风鱼鸟龙负减后况抟]"
    r"|[无围强复简单體圍國學氣會來處變與樂臺]"
    r"|范围|範圍"
)
POLITE_RE = re.compile(
    r"(?:"
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)"
    r"(?:か|よね|よ|ね)?"
    r"|でしょう(?:か|よね|よ|ね)?"
    r"|いただけ(?:ます|ません)(?:か|よね|よ|ね)?"
    r")(?:[。！？!?、]|$)"
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
        or FOREIGN_SCRIPT_RE.search(text)
        or ASCII_SYMBOL_ARTIFACT_RE.search(text)
        or UNICODE_REPLACEMENT_CHAR in text
        or (reject_latin and ASCII_WORD_RE.search(text))
    )


def has_awkward_surface(text):
    return bool(AWKWARD_OR_CAREGIVER_SURFACE_RE.search(str(text or "")))


def has_response_plan_leak(text):
    return bool(JAPANESE_RESPONSE_PLAN_LEAK_RE.search(str(text or "")))
