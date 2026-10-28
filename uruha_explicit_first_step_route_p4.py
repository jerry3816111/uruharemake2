"""Product-only source-bound route for explicit current-User first-step asks.

This extends the response-form evidence admitted by frozen M47.  It does not
generate a step, certify that one was delivered, or write a mental-state fact.
The old M47 route and all its downstream checks remain authoritative.
"""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata

import uruha_crosslingual_help_routing_m47 as m47


_INSTALLED = False
_PRIOR_CLASSIFIER = m47.classify_help_route_m47
_MAX_SOURCE_CHARS = 240
_ZH_FIRST_STEP = re.compile(
    r"(?:你(?:會|会)?(?:叫|要|建議|建议)我|我(?:該|该|應該|应该|現在|现在)?)"
    r"先(?:做|處理|处理|弄)(?:什麼|什么)[？?]\s*$"
)
_JA_FIRST_STEP = re.compile(
    r"(?:まず|先に)(?:何|なに)を(?:すれば|したら|やれば|やったら)"
    r"(?:いい|よさそう)(?:の)?[？?]\s*$"
)
_QUOTED = re.compile(r"[「」『』“”\"'＇〈〉《》]")
_REPORTED = re.compile(
    r"(?:朋友|友人|友達|同事|同僚|上司|老師|老师|母|父|彼女|彼|家人|同學|同学)"
    r".{0,32}(?:問|问|言|說|说|聞|頼|質問|說過|说过)"
    r"|(?:轉述|转述|引用|例文|例句|メモ|傳言|传言)"
)
_ATTRIBUTION_VERB = re.compile(r"(?:問|问|說|说|言った|言って|聞いた|聞いて|質問|頼まれ)")
_META_EXAMPLE = re.compile(
    r"(?:這|这|那|以下|下面)(?:是|只是一)(?:道|個|个)?"
    r"(?:練習題|练习题|例題|標題|标题|題目|题目)"
    r"|(?:練習題|练习题|例題|標題|标题|題目|题目)(?:是|[:：])"
    r"|(?:例文|例句|タイトル|見出し|題名)(?:は|[:：])"
)
_REFUSE_HELP = re.compile(
    r"(?:不想|不要|不用|不必|別|别|不)[^。！？!?]{0,12}"
    r"(?:建議|建议|方法|答案|回答|回覆|回复|答|教|告訴|告诉)"
    r"|(?:アドバイス|助言)(?:は)?(?:いらない|不要)|(?:答え|教え)(?:ないで|なくていい)"
)
_THIRD_PERSON_TASK = re.compile(
    r"(?:朋友|友人|友達|同事|同僚|上司|老師|老师|母|父|彼女|彼|家人|同學|同学)"
    r".{0,20}(?:想|要|が|は|したい|やりたい)"
)
_ZH_USER_TASK = re.compile(
    r"我(?:現在|现在)?(?:只)?(?:想|要|需要|打算|準備|准备|正在)"
    r"[^。！？!?；;\n]{0,50}"
    r"(?:整理|寫|写|開始|开始|做|處理|处理|收拾|完成|編輯|编辑)"
)
_JA_USER_TASK = re.compile(
    r"[^。！？!?；;\n]{1,60}(?:を|が|の)[^。！？!?；;\n]{0,35}"
    r"(?:したい|やりたい|始めたい|書きたい|作りたい|片付けたい|まとめたい)"
)


def _current_user_task_refs(text: str, cue: dict, language: str) -> list[dict]:
    """Keep only independent, observable task clauses before the question."""
    refs = m47._task_refs(text, cue, (cue,))
    task_pattern = _ZH_USER_TASK if language == "zh" else _JA_USER_TASK
    return [
        ref for ref in refs
        if ref["end"] <= cue["start"]
        and task_pattern.search(text[ref["start"]:ref["end"]])
    ]


def classify_first_step_route_p4(user_input) -> dict:
    """Preserve old M47 unless a bounded current-User task and ask both exist."""
    text = str(user_input or "")
    old = _PRIOR_CLASSIFIER(text)
    if old.get("status") != "no_explicit_help_route":
        return old
    if (
        not text or len(text) > _MAX_SOURCE_CHARS or text != text.strip()
        or _QUOTED.search(text)
        or any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for ch in text)
    ):
        return old
    candidates = [
        (language, match)
        for language, pattern in (("zh", _ZH_FIRST_STEP), ("ja", _JA_FIRST_STEP))
        for match in pattern.finditer(text)
    ]
    if len(candidates) != 1:
        return old
    language, match = candidates[0]
    prefix = text[:match.start()]
    if (
        _REPORTED.search(prefix) or _THIRD_PERSON_TASK.search(prefix)
        or _ATTRIBUTION_VERB.search(prefix)
        or _META_EXAMPLE.search(prefix) or _REFUSE_HELP.search(prefix)
    ):
        return old
    # A second earlier response-form question makes target attribution
    # ambiguous; do not silently select the final one as the User's goal.
    if re.search(r"(?:先做(?:什麼|什么)|何をすればいい)[？?]", prefix):
        return old
    # M47's existing risk source is used here as a veto, not as a new policy.
    # M47 itself checks it again before granting downstream authority.
    prior_explicit = m47._PREVIOUS_CLASSIFIER(text)
    if prior_explicit.get("protected_risk_cue") or "solve_regulation" in (
        prior_explicit.get("negated_policies") or []
    ):
        return old
    cue = {
        "kind": "authorize",
        "language": language,
        "cue_id": f"solve_regulation:{language}:p4:first_step:1",
        "start": match.start(),
        "end": match.end(),
        "length": match.end() - match.start(),
        "span_digest": m47._digest(match.group(0)),
    }
    task_refs = _current_user_task_refs(text, cue, language)
    if not task_refs:
        return old
    route = deepcopy(old)
    route.update({
        "status": "practical_help_authorized",
        "detected": True,
        "direction": "authorize",
        "language": language,
        "cue_id": cue["cue_id"],
        "desired_response_span": m47._span_ref(
            text, cue["start"], cue["end"], "desired_response_clause"
        ),
        "task_spans": task_refs,
        "candidate_evidence": [cue],
        "selected_policy": "solve_regulation",
        "negated_policy": None,
        "classifier_model_call_added": False,
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": (
            "current User response-form and independent task spans only; "
            "not successful action delivery, private intent, or memory fact"
        ),
    })
    return route


def install_explicit_first_step_route_p4() -> bool:
    """Install after frozen M47; its dynamic callers reuse this classifier."""
    global _INSTALLED
    m47.install_m47_crosslingual_help_routing()
    if _INSTALLED:
        if m47.classify_help_route_m47 is not classify_first_step_route_p4:
            raise RuntimeError("p4_first_step_route_overlay_overwritten")
        return False
    if m47.classify_help_route_m47 is not _PRIOR_CLASSIFIER:
        raise RuntimeError("p4_first_step_route_predecessor_changed")
    m47.classify_help_route_m47 = classify_first_step_route_p4
    _INSTALLED = True
    return True


__all__ = ["classify_first_step_route_p4", "install_explicit_first_step_route_p4"]
