#!/usr/bin/env python3
"""Model-independent authorization and validation for allowlisted VRM actions."""

import json
import re


ACTION_SPECS = (
    {
        "name": "play_motion",
        "argument": ("motion", "wave"),
        "cues": (r"手(?:を|は)?\s*振", r"バイバイ(?:して|しながら|と)?"),
        "negative_cues": (r"手(?:を|は)?\s*振(?:らない|らず|らなく)",),
    },
    {
        "name": "play_motion",
        "argument": ("motion", "nod"),
        "cues": (r"うなず", r"頷"),
        "negative_cues": (r"(?:うなず|頷)(?:かない|かず|くんじゃなく)",),
    },
    {
        "name": "play_motion",
        "argument": ("motion", "shake_head"),
        "cues": (r"首(?:を)?(?:横に)?\s*振",),
        "negative_cues": (r"首(?:を)?(?:横に)?\s*振(?:らない|らず|らなく)",),
    },
    {
        "name": "play_motion",
        "argument": ("motion", "point"),
        "cues": (r"指(?:し|さ|で示)",),
        "negative_cues": (r"指(?:さない|さず|さなく|しなく|してほしくない)",),
    },
    {
        "name": "play_motion",
        "argument": ("motion", "idle"),
        "cues": (r"待機(?:状態|姿勢)?", r"動き(?:を|は)?.{0,6}戻"),
        "negative_cues": (r"待機(?:状態|姿勢)?.{0,6}(?:しない|戻さない)",),
    },
    {
        "name": "set_expression",
        "argument": ("expression", "happy"),
        "cues": (r"笑顔", r"嬉しそう"),
        "negative_cues": (r"笑顔.{0,8}(?:しない|じゃなく|やめ)",),
    },
    {
        "name": "set_expression",
        "argument": ("expression", "sad"),
        "cues": (r"悲し", r"泣きそうな表情"),
        "negative_cues": (r"悲し.{0,8}(?:しない|じゃなく|やめ)",),
    },
    {
        "name": "set_expression",
        "argument": ("expression", "angry"),
        "cues": (r"怒(?:った|り|る)",),
        "negative_cues": (r"怒.{0,10}(?:しない|じゃなく|やめ)",),
    },
    {
        "name": "set_expression",
        "argument": ("expression", "surprised"),
        "cues": (r"驚", r"びっくり"),
        "negative_cues": (r"(?:驚|びっくり).{0,10}(?:しない|じゃなく|やめ|しなくて)",),
    },
    {
        "name": "set_expression",
        "argument": ("expression", "neutral"),
        "cues": (r"普通の(?:顔|表情)", r"表情(?:を|は)?.{0,6}戻"),
        "negative_cues": (r"(?:普通の(?:顔|表情)|表情.{0,6}戻).{0,6}(?:しない|さない)",),
    },
    {
        "name": "set_gaze",
        "argument": ("target", "user"),
        "cues": (
            r"こっち(?:を|に)?\s*見",
            r"視線(?:を)?(?:私|こっち|ユーザー)(?:に|へ)?(?:合わせ|向け)",
            r"視線(?:を)?私に合わせ",
            r"視線.{0,8}こっち.{0,8}向け",
            r"こっち(?:に|へ)向け",
        ),
        "negative_cues": (r"こっち(?:を|に)?\s*見(?:ない|ず)",),
    },
    {
        "name": "set_gaze",
        "argument": ("target", "left"),
        "cues": (r"左(?:を|に|へ)?(?:の方を)?\s*(?:見|向)", r"左に視線"),
        "negative_cues": (r"左.{0,8}(?:見ない|向かない|じゃなく)",),
    },
    {
        "name": "set_gaze",
        "argument": ("target", "right"),
        "cues": (r"右(?:を|に|へ)?(?:の方を)?\s*(?:見|向)", r"右に視線"),
        "negative_cues": (r"右.{0,8}(?:見ない|向かない|じゃなく)",),
    },
    {
        "name": "set_gaze",
        "argument": ("target", "down"),
        "cues": (r"下(?:を|に)?\s*(?:見|向)",),
        "negative_cues": (r"下.{0,8}(?:見ない|向かない|じゃなく)",),
    },
)

AMBIGUITY_PATTERNS = (
    r"任せる",
    r"迷って",
    r"まだ(?:決め|分から)",
    r"今のなし",
    r"やっぱり(?:変え|やめ)",
    r"(?:する|見る|向く|振る|うなずく|指す)かどうか",
    r"(?:見る|向く|振る|うなずく|指す)か.{0,12}(?:見る|向く|振る|うなずく|指す)か",
    r"どっち(?:に|を|が|へ|にする)",
    r"あとで(?:決め|言|出)",
    r"相談しよう",
    r"必要があるか",
    r"もし.{0,24}(?:言ったら|頼んだら|どうする)",
    r"案もある",
    r"決めなくていい",
    r"保留",
    r"決まっていない",
    r"ほしいような.{0,12}ほしくない",
    r"動いても動かなくても",
)

UNSAFE_OR_EXTERNAL_PATTERNS = (
    r"殴",
    r"パスワード",
    r"位置情報",
    r"勝手に",
    r"ファイル.{0,6}削除",
    r"外部サイト",
    r"(?:部屋の)?電気",
    r"音量",
    r"マイク",
    r"知らない人.{0,8}メッセージ",
    r"カメラ",
    r"モデル.{0,6}再起動",
    r"机.{0,6}叩",
    r"床.{0,6}倒",
)

EXPLICIT_REQUEST_PATTERNS = (
    r"振って",
    r"うなずいて",
    r"頷いて",
    r"指して",
    r"指さして",
    r"示して",
    r"表情にして",
    r"顔にして",
    r"(?:顔|表情)で",
    r"(?:顔|表情)を見せて",
    r"(?:顔|表情)(?:に|を)?して",
    r"(?:笑顔|顔|表情).{0,4}なって",
    r"(?:視線|顔|こっち|左|右|下).{0,10}(?:見て(?!る)|向けて|向いて|合わせて)",
    r"反応して",
    r"戻して",
    r"へ戻って",
    r"だけでいい",
)

NEGATION_AFTER_CUE = re.compile(
    r"(?:らない|らず|かない|かず|さない|せず|しない|しなく|しないで|じゃなく|ではなく|やめ|不要)"
)
GLOBAL_MOTION_NEGATION = re.compile(r"(?:動かないで|動かず|動かなくて|動きはしないで|視線だけ)")


def _call_key(name, argument_name, argument_value):
    return f"{name}:{argument_name}={argument_value}"


def _spec_key(spec):
    argument_name, argument_value = spec["argument"]
    return _call_key(spec["name"], argument_name, argument_value)


def _canonical_call(call):
    function = call.get("function") if isinstance(call, dict) else None
    function = function if isinstance(function, dict) else call
    name = str((function or {}).get("name") or "")
    arguments = (function or {}).get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"name": name, "arguments": {}, "valid": False}
    if not isinstance(arguments, dict) or len(arguments) != 1:
        return {"name": name, "arguments": arguments, "valid": False}
    argument_name, argument_value = next(iter(arguments.items()))
    valid_keys = {_spec_key(spec) for spec in ACTION_SPECS}
    key = _call_key(name, str(argument_name), str(argument_value))
    return {
        "name": name,
        "arguments": arguments,
        "key": key,
        "valid": key in valid_keys,
    }


def _cue_matches(text, spec):
    matches = []
    for pattern in spec["cues"]:
        matches.extend(re.finditer(pattern, text))
    return sorted(matches, key=lambda match: (match.start(), match.end()))


def _cue_is_negated(text, match):
    tail = text[match.start() : min(len(text), match.end() + 14)]
    return bool(NEGATION_AFTER_CUE.search(tail))


def classify_action_request(user_input):
    text = str(user_input or "").strip()
    reasons = []
    if not text:
        reasons.append("empty_input")
    if any(re.search(pattern, text) for pattern in UNSAFE_OR_EXTERNAL_PATTERNS):
        reasons.append("unsafe_or_external_request")
    if any(re.search(pattern, text) for pattern in AMBIGUITY_PATTERNS):
        reasons.append("ambiguous_cancelled_or_hypothetical")

    mentioned = set()
    negated = set()
    positive = set()
    for spec in ACTION_SPECS:
        key = _spec_key(spec)
        matches = _cue_matches(text, spec)
        explicit_negation = any(
            re.search(pattern, text) for pattern in spec.get("negative_cues", ())
        )
        if not matches and not explicit_negation:
            continue
        mentioned.add(key)
        if explicit_negation or any(_cue_is_negated(text, match) for match in matches):
            negated.add(key)
        if any(not _cue_is_negated(text, match) for match in matches):
            positive.add(key)

    if GLOBAL_MOTION_NEGATION.search(text):
        negated.update(
            _spec_key(spec) for spec in ACTION_SPECS if spec["name"] == "play_motion"
        )
        positive.difference_update(negated)

    if not mentioned:
        reasons.append("no_supported_action_mentioned")
    if mentioned and not positive:
        reasons.append("only_negated_supported_actions")
    if positive and not any(re.search(pattern, text) for pattern in EXPLICIT_REQUEST_PATTERNS):
        reasons.append("not_an_explicit_current_request")

    blocking_reasons = {
        "empty_input",
        "unsafe_or_external_request",
        "ambiguous_cancelled_or_hypothetical",
        "no_supported_action_mentioned",
        "only_negated_supported_actions",
        "not_an_explicit_current_request",
    }
    return {
        "authorized": not any(reason in blocking_reasons for reason in reasons),
        "reasons": reasons,
        "mentioned_call_keys": sorted(mentioned),
        "positive_call_keys": sorted(positive - negated),
        "negated_call_keys": sorted(negated),
    }


def validate_model_tool_calls(user_input, model_calls):
    policy = classify_action_request(user_input)
    accepted = []
    blocked = []
    seen = set()
    positive = set(policy["positive_call_keys"])
    negated = set(policy["negated_call_keys"])

    for raw_call in model_calls or []:
        call = _canonical_call(raw_call)
        reasons = []
        if not policy["authorized"]:
            reasons.append("request_not_authorized")
        if not call.get("valid"):
            reasons.append("invalid_or_non_allowlisted_call")
        key = call.get("key")
        if key in negated:
            reasons.append("call_explicitly_negated")
        if call.get("valid") and key not in positive:
            reasons.append("call_not_grounded_in_positive_request")
        if key in seen:
            reasons.append("duplicate_call")
        if reasons:
            blocked.append({"call": call, "reasons": reasons})
            continue
        seen.add(key)
        accepted.append({"name": call["name"], "arguments": call["arguments"]})

    return {
        "policy": policy,
        "accepted_calls": accepted,
        "blocked_calls": blocked,
    }
