"""Current-user speech-act certificate for opt-in placement advice.

This module only classifies the present text.  It does not select a plan,
generate advice, read memory, or authorize a factual claim about where an
object is.  An uncertain or protected turn stays on the existing route.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
import os
import re


SCHEMA = "uruha_location_advice_act_handoff_p4_v1"
LABEL = "location_advice_act_handoff_p4"
FORMAL_SURFACE_SCHEMA = "uruha_location_advice_formal_surface_p4_v1"
FORMAL_SURFACE_LABEL = "location_advice_formal_surface_p4"
CREDENTIAL_VISIBLE_SCHEMA = "uruha_credential_paper_visible_authority_p4_v1"
CREDENTIAL_VISIBLE_LABEL = "credential_paper_visible_authority_p4"
MAX_INPUT_CHARS = 300
_INSTALLED = False
_ORIGINAL_TICK = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_PLACEMENT = re.compile(
    r"置き方|置き場|置く|置い|置け|配置|設置|並べ|保管|収納|"
    r"出してお|出しと|しまう場所|しまっておく場所|"
    r"\b(?:place|put|position|arrange|store|set out)\b|"
    r"(?:放|摆|擺|收纳|收納).{0,4}(?:哪|哪里|哪裡|位置|地方)",
    re.I,
)
_ADVICE_CUE = re.compile(
    r"(?:案|アイデア|提案|おすすめ|お勧め|アドバイス|助言).{0,16}"
    r"(?:ある|ない|ほしい|欲しい|教えて|出して|して|お願い|[?？])|"
    r"(?:どこ|どの辺|どちら側|どんな位置|どう).{0,42}"
    r"(?:いい|よい|良い|よさそう|良さそう|べき|便利|使いやす|する|したら|すれば)|"
    r"(?:置|並べ|配置|設置|出してお).{0,10}(?:けば|いたら|くなら|くと).{0,12}"
    r"(?:いい|よい|良い|よさそう|良さそう|便利|使いやす|どこ)|"
    r"\b(?:where should|where could|best place to|how should|any ideas? (?:for|on))\b|"
    r"(?:放|摆|擺|收纳|收納).{0,12}(?:比较好|比較好|合适|合適|建议|建議)",
    re.I,
)
_REQUEST_FORM = re.compile(
    r"[?？]|(?:教えて|提案して|出して|考えて|お願い|頼む|ちょうだい|"
    r"ください|ほしい|欲しい|どうする|どうしたら|どうすれば|案ある)\s*[。.!！]?$|"
    r"\b(?:should i|could i|please suggest|any ideas|what would you recommend)\b|"
    r"(?:给我|給我|建议|建議|怎[么麼]办|怎[么麼]放)",
    re.I,
)
_CURRENT_LOCATION = re.compile(
    r"(?:どこ|置き場).{0,24}(?:置いた|置いてある|置いてる|置かれて|しまった|保管した|ある)|"
    r"(?:置いた|置いてある|置いてる|しまった).{0,24}どこ|"
    r"置き場.{0,12}どこ|どこ.{0,12}置き場|"
    r"\b(?:where is|where did .* (?:put|place|store))\b",
    re.I,
)
_NO_ADVICE = re.compile(
    r"(?:提案|案|アドバイス|助言|おすすめ|勧め|方法).{0,12}"
    r"(?:しないで|出さないで|いらない|不要|やめて|まだいい)|"
    r"(?:提案|案|アドバイス|助言).{0,8}(?:は|を)?まだ(?:しない|出さない|いらない)|"
    r"(?:聞くだけ|話を聞いて|聞いてほしい)|"
    r"\b(?:no advice|don't suggest|do not suggest|not asking for advice)\b|"
    r"(?:不要|不用|别|別).{0,8}(?:建议|建議|提案)",
    re.I,
)
_META_REQUEST = re.compile(
    r"(?:言い方|表現|文面|文章|文|台詞|セリフ|引用|訳|翻訳).{0,24}"
    r"(?:直して|書き換え|添削|訳して|自然|短く)|"
    r"(?:直して|書き換え|添削|訳して).{0,24}(?:言い方|表現|文面|文章|台詞|セリフ)|"
    r"\b(?:rewrite|rephrase|translate|edit) (?:the |this |that )?(?:wording|sentence|quote)\b",
    re.I,
)
_REPORTED = re.compile(
    r"(?:友達|友人|知人|同僚|係の人|店員|先生|母|父|兄|姉|弟|妹|彼|彼女|誰か)"
    r"(?:が|は|から).{0,110}(?:言った|言って|聞いた|聞いて|勧めた|提案した|らしい)|"
    r"(?:朋友|同事|老师|老師|店員|店员|有人).{0,110}(?:說|说|建议|建議)|"
    r"\b(?:my )?(?:friend|teacher|coworker|colleague)\b.{0,110}"
    r"\b(?:said|asked|suggested|told me)\b",
    re.I,
)
_SENSITIVE = re.compile(
    r"薬|医薬|医療|注射|刃物|包丁|銃|火薬|爆薬|爆弾|毒物|劇物|農薬|"
    r"パスワード|パスコード|暗証番号|認証コード|住所|電話番号|口座|秘密|"
    r"化学薬品|感電|高電圧|自傷|自殺|死にたい|危険物|"
    r"\b(?:medicine|medication|drug|knife|gun|explosive|poison|pesticide|"
    r"high voltage|self-harm|suicide|password|passcode|secret|bank account)\b|"
    r"(?:药|藥|刀具|枪|槍|炸药|炸藥|毒物|自残|自殘|自杀|自殺)",
    re.I,
)
_GOAL = re.compile(
    r"したい|しておきたい|ように|ために|やすく|やすい|便利に|安全に|"
    r"\b(?:so that|easy to|easier to|accessible|convenient)\b|"
    r"(?:方便|容易|便于|便於)",
    re.I,
)
_SAFE_FORMAL_ENDING = re.compile(
    r"(?P<prefix>[^。.!?！？「」『』\"“”'‘’`\r\n\t\u2028\u2029]+(?:やすい|にくい))です。?$"
)
_CREDENTIAL_SAFE_SURFACE = (
    "なくすのは困るよな。人目につく所に置きっぱなしにせず、"
    "他人に見られない形で管理しとけ。"
)
_WRITTEN_CREDENTIAL_PAPER = re.compile(
    r"(?:パスワード|パスコード|暗証番号|認証コード|認証番号|ワンタイムコード|"
    r"(?<![A-Za-z])PIN(?![A-Za-z])).{0,32}?(?:書いた|書いてある|書かれた|メモした|記した|の|入りの)"
    r".{0,10}?(?:紙|付箋|メモ|カード)|"
    r"(?:紙|付箋|メモ|カード).{0,20}?(?:に|上に|の).{0,18}?"
    r"(?:パスワード|パスコード|暗証番号|認証コード|(?<![A-Za-z])PIN(?![A-Za-z]))|"
    r"(?:密碼|密码|登入碼|登录码|驗證碼|验证码|(?<![A-Za-z])PIN(?![A-Za-z])).{0,32}?"
    r"(?:寫|写|記|记).{0,12}?(?:紙|纸|便條|便条|筆記|笔记)|"
    r"(?:紙|纸|便條|便条|筆記|笔记).{0,18}?(?:上|的|有).{0,18}?"
    r"(?:密碼|密码|登入碼|登录码|驗證碼|验证码|(?<![A-Za-z])PIN(?![A-Za-z]))|"
    r"\b(?:note|paper|sticky note|piece of paper|card)\b.{0,30}?"
    r"\b(?:with|containing|bearing|has|holding)\b.{0,16}?"
    r"\b(?:my |the )?(?:PIN|password|passcode|login code)\b|"
    r"\b(?:PIN|password|passcode|login code)\b.{0,30}?"
    r"\b(?:written on|on|in)\b.{0,16}?"
    r"\b(?:a |my |the )?(?:note|paper|sticky note|piece of paper|card)\b",
    re.I,
)
_CREDENTIAL_PROSPECTIVE_JP = re.compile(
    r"(?:どこ|どの辺|どんな位置|置き場所).{0,32}?"
    r"(?:置く|置けば|置いたら|置くと|しまえば|保管すれば|いい|良い|よい|べき|おすすめ)|"
    r"(?:置く|置けば|置いたら|保管する).{0,16}?"
    r"(?:どこ|どの辺|いい|良い|よい|べき|おすすめ)"
)
_CREDENTIAL_PROSPECTIVE_EN = re.compile(
    r"\b(?:where (?:should|could|can) I put|where (?:should|could) I store|"
    r"where to put|best place to (?:put|store))\b",
    re.I,
)
_CREDENTIAL_PROSPECTIVE_ZH = re.compile(
    r"(?:放|摆|擺|收|存).{0,5}?(?:哪裡|哪里|甚麼地方|什么地方|哪個位置|哪个位置)"
    r".{0,10}?(?:比較好|比较好|好|合適|合适|安全|方便|[?？])|"
    r"(?:應該|应该|建議|建议).{0,10}?(?:放|摆|擺|收|存).{0,6}?"
    r"(?:哪裡|哪里|甚麼地方|什么地方)"
)
_CREDENTIAL_META = re.compile(
    r"翻訳|英訳|和訳|訳して|言い換え|自然な日本語に|文章を|文面を|台詞を|セリフを|"
    r"\b(?:translate|translation|rewrite|rephrase|wording)\b|"
    r"翻譯|翻译|改寫|改写|怎麼說|怎么说",
    re.I,
)
_CREDENTIAL_REPORTED = re.compile(
    r"(?:友達|友人|同僚|先生|知人|彼|彼女|誰か).{0,80}?(?:聞いた|聞いて|聞かれた|言った|言って|尋ねた|尋ねて)|"
    r"(?:朋友|同事|老師|老师|有人).{0,80}?(?:問|问|說|说|建議|建议)|"
    r"\b(?:my )?(?:friend|teacher|coworker|colleague|someone)\b.{0,80}?"
    r"\b(?:asked|said|suggested|told)\b|"
    r"\b(?:he|she|they|someone)\s+(?:asked|said|suggested)\b",
    re.I,
)
_CREDENTIAL_LOCATION_ACTION_LEXEME = re.compile(
    r"(?:机の上|机上|テーブルの上|窓際|引き出し|鞄|バッグ|棚|玄関|枕元|"
    r"デスクの上).{0,18}?(?:置|しま|保管|入れ)|"
    r"(?:置|しま|保管|入れ).{0,18}?(?:机の上|机上|窓際|引き出し|鞄|バッグ|棚|玄関)",
)


def _outside_quotes(text: str) -> tuple[str, bool, bool]:
    """Mask quoted material without moving offsets; reject unmatched quotes."""
    open_to_close = {"「": "」", "『": "』", "“": "”", '"': '"'}
    closing = {"」", "』", "”"}
    chars = list(text)
    stack: list[str] = []
    quoted = False
    for index, char in enumerate(text):
        if stack:
            chars[index] = " "
            if char == stack[-1]:
                stack.pop()
            elif char in open_to_close:
                stack.append(open_to_close[char])
            continue
        if char in open_to_close:
            stack.append(open_to_close[char])
            chars[index] = " "
            quoted = True
        elif char in closing:
            return "".join(chars), quoted, False
    if stack:
        return "".join(chars), quoted, False
    outside = "".join(chars)
    # Single quotes are only treated as quotation marks at word boundaries,
    # never as apostrophes inside English words.
    outside, count = re.subn(r"(?<!\w)'[^']*'(?!\w)", lambda m: " " * len(m.group()), outside)
    return outside, quoted or bool(count), True


def _goal_span(outside: str) -> tuple[str, int | None]:
    for match in re.finditer(r"[^、,。!?！？\n]{2,120}", outside):
        segment = match.group().strip()
        if _GOAL.search(segment):
            start = outside.find(segment, match.start(), match.end())
            return segment[:120], start
    return "", None


def classify_location_advice_act_p4(user_input: str) -> dict:
    """Return a bounded current-turn admission receipt, not advice or a fact."""
    raw = str(user_input or "")
    receipt = {
        "schema": SCHEMA,
        "input_sha": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "eligible": False,
        "reason": "not_placement_advice_request",
        "speech_act": "unclassified",
        "source_kind": "current_user",
        "goal_text": "",
        "goal_start": None,
        "model_calls_added": 0,
        "fact_location_authorized": False,
        "private_intent_claimed": False,
    }
    if not raw.strip():
        return {**receipt, "reason": "empty_input"}
    if len(raw) > MAX_INPUT_CHARS:
        return {**receipt, "reason": "outside_bounded_input"}
    outside, quoted, balanced = _outside_quotes(raw)
    if not balanced:
        return {**receipt, "reason": "ambiguous_quote_scope"}
    if _META_REQUEST.search(outside):
        return {**receipt, "reason": "wording_or_translation_request", "speech_act": "meta_request"}
    if _NO_ADVICE.search(outside):
        return {**receipt, "reason": "advice_explicitly_negated", "speech_act": "listen_or_no_advice"}
    if _SENSITIVE.search(outside):
        return {**receipt, "reason": "sensitive_placement_context", "speech_act": "protected_or_high_stakes"}
    if _REPORTED.search(outside):
        return {**receipt, "reason": "third_party_report", "speech_act": "reported_speech"}
    if not _PLACEMENT.search(outside):
        reason = "quoted_request_not_current_user_act" if quoted else "no_placement_action"
        return {**receipt, "reason": reason}
    if not (_ADVICE_CUE.search(outside) and _REQUEST_FORM.search(outside)):
        fact = bool(_CURRENT_LOCATION.search(outside))
        return {
            **receipt,
            "reason": "existing_location_fact_not_advice" if fact else "no_explicit_advice_request",
            "speech_act": "current_location_question" if fact else "other_placement_mention",
        }
    goal_text, goal_start = _goal_span(outside)
    return {
        **receipt,
        "eligible": True,
        "reason": "direct_current_user_placement_advice_request",
        "speech_act": "prospective_placement_advice_request",
        "goal_text": goal_text,
        "goal_start": goal_start,
    }


def _same_credential_paper_object_p4(
    segment: str, pair: re.Match, request: re.Match, language: str,
) -> bool:
    """Admit only when the placement request still points at the paper.

    This intentionally rejects uncertain cross-object anaphora.  It is not a
    syntactic parser and a false negative keeps the existing route untouched.
    """
    if language == "en":
        after_put = segment[request.end():].lstrip()
        if pair.start() >= request.end():
            return bool(re.match(
                r"(?:a |my |the )?(?:note|paper|sticky note|piece of paper|card|"
                r"PIN|password|passcode|login code)\b", after_put, re.I,
            ))
        between = segment[pair.end():request.start()]
        if re.search(r"\b(?:and|but)\b", between, re.I):
            return False
        referent = re.match(r"(?:it|this|that|the note|the paper)\b", after_put, re.I)
        if not referent:
            return False
        return not bool(re.search(r"\bfor\s+\w+", after_put[referent.end():], re.I))
    if pair.start() > request.end():
        return False
    between = segment[pair.end():request.start()]
    # A new explicit topic/object takes precedence over an earlier credential
    # paper, even when the writer omitted a comma before the new topic.
    trailing_clause = re.split(r"[、，,;；]|けど|けれど|但是|但|而", between)[-1]
    if trailing_clause != between or language == "jp":
        new_jp_object = re.search(r"([^\sはを、，,;；]{1,24})(?:は|を)\s*$", trailing_clause)
        new_zh_object = re.search(r"([^\s、，,;；]{1,16}?)(?:要|該|该)?$", trailing_clause)
        explicit = new_jp_object.group(1) if new_jp_object else ""
        if language == "zh" and not explicit and new_zh_object:
            explicit = new_zh_object.group(1)
        if explicit:
            # A second memo/paper need not be the credential paper: e.g.
            # 「買い物メモ」 and 「買菜便條」 are different asked objects.
            is_goal_clause = bool(
                language == "zh"
                and re.search(r"怕|擔心|担心|弄丟|弄丢|遺失|遗失", explicit)
            )
            is_coreference = bool(re.fullmatch(
                r"(?:それ|これ|它|その(?:紙|付箋|メモ)|あの(?:紙|付箋|メモ)|"
                r"(?:那張|这张|這張)(?:紙|纸|便條|便条|筆記|笔记))",
                explicit,
                re.I,
            ))
            repeats_secret_paper = bool(
                re.search(r"パスワード|パスコード|暗証番号|認証コード|密碼|密码|PIN", explicit, re.I)
                and re.search(r"紙|纸|付箋|メモ|便條|便条|筆記|笔记", explicit, re.I)
            )
            if not (is_goal_clause or is_coreference or repeats_secret_paper):
                return False
    return True


def _outside_credential_quotes_p4(raw: str) -> tuple[str, bool]:
    """Extend old quote masking for written-secret advice without changing it."""
    chars = list(raw)
    ascii_quote_positions = [
        i for i, char in enumerate(chars)
        if char == "'"
        and not (i > 0 and i + 1 < len(chars)
                 and chars[i - 1].isalnum() and chars[i + 1].isalnum())
    ]
    if len(ascii_quote_positions) % 2:
        return "", False
    for index in ascii_quote_positions:
        chars[index] = '"'
    text = "".join(chars).replace("‘", "“").replace("’", "”")
    outside, _, balanced = _outside_quotes(text)
    return outside, balanced


def classify_credential_paper_visible_p4(user_input: str) -> dict:
    """Classify this User turn independently of the older advice handoff.

    The certificate carries only a digest and bounded labels; never the
    credential or raw User text.  It authorizes one safe visible surface,
    not a claim about where the paper actually is or storage confidentiality.
    """
    raw = str(user_input or "")
    receipt = {
        "schema": CREDENTIAL_VISIBLE_SCHEMA,
        "input_sha": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "source_kind": "current_user",
        "eligible": False,
        "reason": "not_direct_credential_paper_advice",
        "model_calls_added": 0,
        "receipt_raw_user_text_persisted": False,
        "fact_location_authorized": False,
    }
    if not raw.strip():
        return {**receipt, "reason": "empty_input"}
    if len(raw) > MAX_INPUT_CHARS:
        return {**receipt, "reason": "outside_bounded_input"}
    outside, balanced = _outside_credential_quotes_p4(raw)
    if not balanced:
        return {**receipt, "reason": "ambiguous_quote_scope"}
    if _META_REQUEST.search(outside) or _CREDENTIAL_META.search(outside):
        return {**receipt, "reason": "wording_or_translation_request"}
    if _NO_ADVICE.search(outside):
        return {**receipt, "reason": "advice_explicitly_negated"}
    if _REPORTED.search(outside) or _CREDENTIAL_REPORTED.search(outside):
        return {**receipt, "reason": "third_party_report"}
    for segment in re.findall(r"[^。.!?！？\n]+[。.!?！？]?", outside):
        if not segment.strip():
            continue
        if not _REQUEST_FORM.search(segment):
            continue
        pair = _WRITTEN_CREDENTIAL_PAPER.search(segment)
        if pair is None:
            continue
        for language, pattern in (
            ("jp", _CREDENTIAL_PROSPECTIVE_JP),
            ("zh", _CREDENTIAL_PROSPECTIVE_ZH),
            ("en", _CREDENTIAL_PROSPECTIVE_EN),
        ):
            request = pattern.search(segment)
            if request and _same_credential_paper_object_p4(segment, pair, request, language):
                return {
                    **receipt,
                    "eligible": True,
                    "reason": "direct_written_credential_paper_future_placement_advice",
                    "speech_act": "prospective_placement_advice_request",
                    "language_cue": language,
                }
    return receipt


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _vacuity_diagnostic(value: str) -> str:
    """Detect a few empty outputs; this is not a semantic quality judge."""
    text = re.sub(r"\s+", "", str(value or ""))
    if not text:
        return "empty"
    if re.search(r"適当な場所|好きな所|好きな場所|どこでもいい|一緒に決めよう", text):
        return "known_vacuous_phrase"
    return "manual_goal_tie_review_required"


def _formal_only_surface_candidate_p4(reply, logic_data, user_input, cert):
    """Try one opt-in morphology edit; M39 and the Japanese guard still decide.

    The receipt proves string provenance and bounded surface form, never that
    the selected recommendation actually meets the user's goal.
    """
    from uruha_semantic_persona_surface_m39 import inspect_surface_m39

    original = str(reply or "")
    current = classify_location_advice_act_p4(user_input)
    receipt = {
        "schema": FORMAL_SURFACE_SCHEMA,
        "status": "not_eligible",
        "method": "none",
        "original_candidate_sha": _sha(original),
        "attempt_sha": None,
        "final_visible_sha": None,
        "final_same_as_attempt": None,
        "m39_action": None,
        "m39_status": None,
        "model_calls_added": 0,
        "raw_reply_persisted": False,
        "semantic_goal_tie": (
            "manual_product_review_required" if current["eligible"] else "not_applicable"
        ),
        "attempt_stage": "pre_m39",
        "verification_stage": "post_m39_and_post_emit",
    }
    if not (
        isinstance(logic_data, dict)
        and isinstance(cert, dict)
        and cert.get("schema") == SCHEMA
        and cert.get("source_kind") == "current_user"
        and cert.get("input_sha") == current["input_sha"]
        and cert.get("eligible") is True
        and current["eligible"] is True
        and cert.get("selected_handoff_status") == "matched_full_planner"
        and cert.get("selected_core_sha") == _sha(original)
        and (logic_data.get("semantic_route_m22") or {}).get("selected_type")
        == "general_conversation"
    ):
        return original, receipt
    match = _SAFE_FORMAL_ENDING.fullmatch(original)
    if not match:
        receipt["status"] = "unsupported_surface_shape"
        return original, receipt
    audit = inspect_surface_m39(user_input, original, logic_data)
    if (
        audit["protected_route"]
        or audit["role_violations"]
        or audit["unsupported_additions"]
        or not audit["policy_act_match"]
        or not audit["formal_register_detected"]
    ):
        receipt["status"] = "not_formal_only"
        return original, receipt
    candidate = match.group("prefix") + "よ。"
    after = inspect_surface_m39(user_input, candidate, logic_data)
    if (
        after["protected_route"]
        or after["role_violations"]
        or after["unsupported_additions"]
        or not after["policy_act_match"]
        or after["formal_register_detected"]
    ):
        receipt["status"] = "post_audit_rejected"
        return original, receipt
    receipt.update({
        "status": "attempted_formal_only",
        "method": "terminal_i_adjective_desu_to_yo",
        "attempt_sha": _sha(candidate),
        "source_prefix_sha": _sha(match.group("prefix")),
        "attempt_prefix_sha": _sha(candidate[:-2]),
        "prefix_identical": candidate[:-2] == match.group("prefix"),
    })
    return candidate, receipt


def _credential_visible_candidate_p4(reply, logic_data, user_input):
    """One current-turn, source-bound visible candidate, before M39/Japanese guard."""
    current = classify_credential_paper_visible_p4(user_input)
    original = str(reply or "")
    core = str(logic_data.get("core_message_jp") or "") if isinstance(logic_data, dict) else ""
    receipt = {
        **current,
        "status": "not_eligible",
        "original_candidate_sha": _sha(original),
        "selected_core_sha": _sha(core) if core else None,
        "selected_core_same_as_guard_input": bool(core and core == original),
        "safe_candidate_sha": None,
        "final_visible_sha": None,
        "final_same_as_safe_candidate": None,
        "m39_action": None,
        "m39_status": None,
        "final_reply_sha": None,
        "final_reply_match": None,
        "verification_stage": "post_m39_and_post_emit",
        "selected_core_safe_diagnostic": (
            "location_action_lexeme_manual_polarity_review"
            if _CREDENTIAL_LOCATION_ACTION_LEXEME.search(core) else
            "same_as_bounded_safe_surface"
            if core == _CREDENTIAL_SAFE_SURFACE else "not_established"
        ),
    }
    if not current["eligible"]:
        return original, receipt
    if not isinstance(reply, str) or not isinstance(logic_data, dict):
        receipt["status"] = "missing_selected_candidate_or_logic"
        return original, receipt
    # The current User SHA and the exact candidate passed into this terminal
    # guard are independently recorded.  An older advice handoff may be stale
    # or say eligible=true for Chinese/English and cannot veto this boundary.
    receipt["safe_candidate_sha"] = _sha(_CREDENTIAL_SAFE_SURFACE)
    receipt["status"] = "attempted_safe_surface"
    return _CREDENTIAL_SAFE_SURFACE, receipt


def cognitive_tick_with_location_advice_act_handoff_p4(self, event):
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    raw = str((event or {}).get("user_input") or "")
    cert = classify_location_advice_act_p4(raw)
    logic = tick.get("logic") or {}
    handed = logic.get(LABEL) or {}
    valid_handoff = bool(
        cert["eligible"]
        and handed.get("schema") == SCHEMA
        and handed.get("input_sha") == cert["input_sha"]
        and handed.get("handoff_status") == "passed_to_full_planner"
    )
    cert.update({
        "selected_handoff_status": (
            "matched_full_planner" if valid_handoff else
            str(handed.get("handoff_status") or "not_selected")
        ),
        "selected_core_sha": _sha(logic.get("core_message_jp")),
        "selected_core_vacuity_diagnostic": _vacuity_diagnostic(
            logic.get("core_message_jp")
        ) if cert["eligible"] else "not_applicable",
        "selected_planner_path": str(logic.get("planner_path") or ""),
        "selected_intent": str(logic.get("intent") or ""),
        "selected_surface_act": str(logic.get("surface_act") or ""),
        "selected_route": str((tick.get("route_info") or {}).get("performed_route") or ""),
        "semantic_goal_tie": "manual_product_review_required" if cert["eligible"] else "not_applicable",
        "guard_output_sha": None,
        "final_reply_sha": None,
        "final_guard_match": None,
    })
    logic[LABEL] = deepcopy(cert)
    tick["logic"] = logic
    runtime = getattr(self, "runtime", None)
    if runtime is not None:
        board = getattr(runtime, "blackboard", None)
        if isinstance(board, list):
            index = next((i for i, row in enumerate(board)
                          if row.get("label") == "selected_plan"), len(board))
            board.insert(index, {"stage": "evidence", "label": LABEL,
                                 "payload": deepcopy(cert), "salience": 0.93})
    return tick


def visible_guard_with_location_advice_act_handoff_p4(
    self, reply, logic_data, user_input="", memory_data=None,
):
    guard_candidate = reply
    formal_surface = None
    credential_visible = None
    selected_cert = logic_data.get(LABEL) if isinstance(logic_data, dict) else None
    if os.environ.get("URUHA_P4_CREDENTIAL_PAPER_VISIBLE") == "1":
        guard_candidate, credential_visible = _credential_visible_candidate_p4(
            reply, logic_data, user_input,
        )
    if (
        not (isinstance(credential_visible, dict) and credential_visible.get("eligible"))
        and
        os.environ.get("URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE") == "1"
        and isinstance(reply, str)
        and isinstance(selected_cert, dict)
        and selected_cert.get("schema") == SCHEMA
    ):
        guard_candidate, formal_surface = _formal_only_surface_candidate_p4(
            reply, logic_data, user_input, selected_cert,
        )
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, guard_candidate, logic_data, user_input=user_input, memory_data=memory_data,
    )
    if not isinstance(logic_data, dict):
        return visible
    cert = logic_data.get(LABEL)
    if not isinstance(cert, dict) or cert.get("schema") != SCHEMA:
        return visible
    cert = deepcopy(cert)
    cert["guard_input_sha"] = _sha(reply)
    cert["guard_output_sha"] = _sha(visible)
    if credential_visible is not None:
        credential_visible["final_visible_sha"] = _sha(visible)
        m39 = logic_data.get("semantic_persona_surface_verifier_m39") or {}
        credential_visible["m39_action"] = m39.get("action")
        credential_visible["m39_status"] = m39.get("status")
        if credential_visible["safe_candidate_sha"]:
            credential_visible["final_same_as_safe_candidate"] = (
                credential_visible["safe_candidate_sha"] == _sha(visible)
            )
            if not credential_visible["final_same_as_safe_candidate"]:
                credential_visible["status"] = "post_guard_mismatch"
            elif (m39.get("action") == "accept"
                  and m39.get("status") == "accepted_verified_surface"):
                credential_visible["status"] = "accepted_preserved"
            elif (m39.get("action") == "not_applicable"
                  and m39.get("status") == "protected_route_not_modified"):
                credential_visible["status"] = "preserved_protected_route"
            else:
                credential_visible["status"] = "m39_verification_not_established"
        cert["credential_paper_visible"] = deepcopy(credential_visible)
    if formal_surface is not None:
        formal_surface["final_visible_sha"] = _sha(visible)
        m39 = logic_data.get("semantic_persona_surface_verifier_m39") or {}
        formal_surface["m39_action"] = m39.get("action")
        formal_surface["m39_status"] = m39.get("status")
        if formal_surface["attempt_sha"]:
            formal_surface["final_same_as_attempt"] = (
                formal_surface["attempt_sha"] == _sha(visible)
            )
            formal_surface["status"] = (
                "accepted_preserved"
                if formal_surface["final_same_as_attempt"]
                and m39.get("action") == "accept"
                and m39.get("status") == "accepted_verified_surface"
                else "post_guard_mismatch"
            )
        cert["formal_surface"] = formal_surface
    cert["guard_output_vacuity_diagnostic"] = (
        _vacuity_diagnostic(visible) if cert.get("eligible") else "not_applicable"
    )
    # The guard can preserve/repair Japanese surface, but it cannot prove a
    # recommendation is goal-tied.  The frozen product rubric reviews that.
    cert["semantic_goal_tie"] = (
        "manual_product_review_required" if cert.get("eligible") else "not_applicable"
    )
    logic_data[LABEL] = cert
    return visible


def materialize_location_advice_act_handoff_p4(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    if not isinstance(logic, dict):
        return result
    cert = logic.get(LABEL)
    trace = result.get("runtime_trace")
    if not isinstance(cert, dict) or cert.get("schema") != SCHEMA or not isinstance(trace, dict):
        return result
    cert = deepcopy(cert)
    cert["final_reply_sha"] = _sha(result.get("reply"))
    cert["final_guard_match"] = bool(
        cert.get("guard_output_sha")
        and cert["guard_output_sha"] == cert["final_reply_sha"]
    )
    cert["final_reply_vacuity_diagnostic"] = (
        _vacuity_diagnostic(result.get("reply")) if cert.get("eligible") else "not_applicable"
    )
    formal_surface = cert.get("formal_surface")
    if isinstance(formal_surface, dict) and formal_surface.get("schema") == FORMAL_SURFACE_SCHEMA:
        formal_surface = deepcopy(formal_surface)
        formal_surface["final_reply_sha"] = cert["final_reply_sha"]
        formal_surface["final_reply_match"] = (
            formal_surface.get("final_visible_sha") == cert["final_reply_sha"]
        )
        if formal_surface.get("status") == "accepted_preserved" and not formal_surface["final_reply_match"]:
            formal_surface["status"] = "post_emit_mismatch"
        cert["formal_surface"] = formal_surface
    credential_visible = cert.get("credential_paper_visible")
    if (isinstance(credential_visible, dict)
            and credential_visible.get("schema") == CREDENTIAL_VISIBLE_SCHEMA):
        credential_visible = deepcopy(credential_visible)
        credential_visible["final_reply_sha"] = cert["final_reply_sha"]
        credential_visible["final_reply_match"] = bool(
            credential_visible.get("final_visible_sha")
            and credential_visible["final_visible_sha"] == cert["final_reply_sha"]
        )
        if (credential_visible.get("safe_candidate_sha")
                and not credential_visible["final_reply_match"]):
            credential_visible["status"] = "post_emit_mismatch"
        cert["credential_paper_visible"] = credential_visible
    logic[LABEL] = deepcopy(cert)
    rows = [row for row in trace.get("blackboard", [])
            if row.get("label") not in {LABEL, FORMAL_SURFACE_LABEL, CREDENTIAL_VISIBLE_LABEL}]
    index = next((i for i, row in enumerate(rows)
                  if row.get("label") == "selected_plan"), len(rows))
    rows.insert(index, {"stage": "evidence", "label": LABEL,
                        "payload": deepcopy(cert), "salience": 0.93})
    if isinstance(formal_surface, dict) and formal_surface.get("schema") == FORMAL_SURFACE_SCHEMA:
        utterance_index = next((i for i, row in enumerate(rows)
                                if row.get("label") == "utterance"), len(rows))
        m39_index = next((i for i, row in enumerate(rows)
                          if row.get("label") == "semantic_persona_surface_verifier_m39"),
                         utterance_index)
        rows.insert(min(m39_index, utterance_index), {
            "stage": "surface", "label": FORMAL_SURFACE_LABEL,
            "payload": deepcopy(formal_surface),
            "salience": 0.94 if formal_surface.get("status") == "accepted_preserved" else 0.86,
        })
        trace[FORMAL_SURFACE_LABEL] = deepcopy(formal_surface)
    if (isinstance(credential_visible, dict)
            and credential_visible.get("schema") == CREDENTIAL_VISIBLE_SCHEMA):
        utterance_index = next((i for i, row in enumerate(rows)
                                if row.get("label") == "utterance"), len(rows))
        m39_index = next((i for i, row in enumerate(rows)
                          if row.get("label") == "semantic_persona_surface_verifier_m39"),
                         utterance_index)
        rows.insert(min(m39_index, utterance_index), {
            "stage": "surface", "label": CREDENTIAL_VISIBLE_LABEL,
            "payload": deepcopy(credential_visible),
            "salience": 0.95 if credential_visible.get("status") in {
                "accepted_preserved", "preserved_protected_route"
            } else 0.88,
        })
        trace[CREDENTIAL_VISIBLE_LABEL] = deepcopy(credential_visible)
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(cert)
    return result


def install_location_advice_act_handoff_p4() -> bool:
    """Install after older P4 gates in the isolated product entry only."""
    global _INSTALLED, _ORIGINAL_TICK, _ORIGINAL_VISIBLE_GUARD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_location_advice_act_handoff_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_location_advice_act_handoff_p4

    def finish(self, result):
        if not isinstance(result, dict) or (result.get("logic") or {}).get(LABEL, {}).get("schema") != SCHEMA:
            return result
        materialize_location_advice_act_handoff_p4(result)
        trace = result.get("runtime_trace")
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            sync_current_history_m41_1(result)
            if (getattr(runtime, "turn_traces", None)
                    and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")):
                runtime.turn_traces[-1] = deepcopy(trace)
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, _ORIGINAL_EMIT(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    os.environ["URUHA_P4_LOCATION_ADVICE_ACT"] = "1"
    _INSTALLED = True
    return True
