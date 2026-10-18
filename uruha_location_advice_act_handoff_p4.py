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
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data,
    )
    if not isinstance(logic_data, dict):
        return visible
    cert = logic_data.get(LABEL) or {}
    if cert.get("schema") != SCHEMA:
        return visible
    cert = deepcopy(cert)
    cert["guard_input_sha"] = _sha(reply)
    cert["guard_output_sha"] = _sha(visible)
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
    cert = logic.get(LABEL) or {}
    trace = result.get("runtime_trace")
    if cert.get("schema") != SCHEMA or not isinstance(trace, dict):
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
    logic[LABEL] = deepcopy(cert)
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows)
                  if row.get("label") == "selected_plan"), len(rows))
    rows.insert(index, {"stage": "evidence", "label": LABEL,
                        "payload": deepcopy(cert), "salience": 0.93})
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
