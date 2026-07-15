#!/usr/bin/env python3
"""Selective per-target discourse-state resolution for grounded VRM actions."""

import re

from precise_target_mentions_v52 import build_precise_target_event_map
from target_event_map_v51 import SENTENCE_BOUNDARY_RE, _spans


META_CONTEXT_RE = re.compile(
    r"(?:文字列|JSON|文を引用|引用|分類例|テストデータ|台詞|言葉|書いてある|練習|解析対象)"
)
EXPLICIT_NONEXECUTION_RE = re.compile(
    r"(?:実行|動作|指示|命令|お願い)[^。！？!?]{0,12}(?:しない|ではない|じゃない|しないで)"
)
PENDING_RE = re.compile(
    r"(?:かどうか|かは|まだ決め|決めていない|決めてない|未定|迷って|迷う|保留|あとで決め|後で決め)"
)
HYPOTHETICAL_RE = re.compile(r"(?:もし|仮に)")
CORRECTION_RE = re.compile(r"(?:いや|ごめん|やっぱり|その代わり|代わりに)")
REQUEST_END_RE = re.compile(
    r"(?:"
    r"(?:て|で)(?:ください|下さい|くれる|くれ|もらえる|もらえ|いただける|頂ける)"
    r"|(?:て|で)くれるかな"
    r"|(?:して|向いて|見て|振って|笑って|うなずいて|頷いて|合わせて|戻して|いて|みて)"
    r"|なさい"
    r")[。！？!?]*$"
)
REQUEST_BENEFICIARY_RE = re.compile(
    r"(?:て|で)(?:ください|下さい|くれる|くれ|もらえる|もらえ|いただける|頂ける|ほしい)"
)
QUESTION_RE = re.compile(r"[？?]")
DESCRIPTIVE_RE = re.compile(
    r"(?:ている|てる|ていた|振った|向いていた|言った|言いました|迎えた|終わらせる|"
    r"同じこと|無表情だ|癖|について|意味|誰ですか|誰だった)"
)
THIRD_PARTY_RE = re.compile(
    r"(?:彼|彼女|トム|犬|男性|友人|女の子|男の人|好きな人|人が|人は)"
)
POSITIVE_IDLE_RE = re.compile(
    r"(?:動かないでいて|動かずにいて|じっとしていて|待機(?:して|姿勢)|そのままの姿勢)"
)


def _quote_spans(text):
    pairs = {"「": "」", "『": "』", "“": "”", '"': '"'}
    spans = []
    stack = []
    for index, char in enumerate(text):
        if char in pairs:
            if char == '"' and stack and stack[-1][0] == '"':
                opening, start = stack.pop()
                spans.append((start, index + 1, text[start : index + 1]))
            else:
                stack.append((char, index))
            continue
        if stack and char == pairs[stack[-1][0]]:
            opening, start = stack.pop()
            spans.append((start, index + 1, text[start : index + 1]))
    return sorted(spans)


def _inside_any(span, containers):
    return any(span[0] >= start and span[1] <= end for start, end, _ in containers)


def _sentence_for_occurrence(sentences, occurrence):
    index = occurrence["sentence_index"]
    return sentences[index]


def _request_force(sentence_text):
    stripped = sentence_text.strip()
    return bool(REQUEST_END_RE.search(stripped) or REQUEST_BENEFICIARY_RE.search(stripped))


def _scope_marker_types(occurrences):
    return {
        reason.get("marker_type")
        for occurrence in occurrences
        for reason in occurrence.get("scope_reasons") or []
    }


def _focus_mentions(occurrences):
    return [
        (mention["start"], mention["end"], mention["text"])
        for occurrence in occurrences
        for mention in occurrence["target_mentions"]
    ]


def _later_same_domain_request(event_map, focus_target_id, sentences):
    domain = focus_target_id.split(".", 1)[0]
    focus_positions = [
        occurrence["order"]
        for occurrence in event_map["ordered_grounded_occurrences"]
        if occurrence["target_id"] == focus_target_id
    ]
    if not focus_positions:
        return None
    last_focus_order = max(focus_positions)
    for occurrence in event_map["ordered_grounded_occurrences"]:
        if occurrence["order"] <= last_focus_order:
            continue
        target_id = occurrence["target_id"]
        if target_id == focus_target_id or target_id.split(".", 1)[0] != domain:
            continue
        sentence = _sentence_for_occurrence(sentences, occurrence)
        if _request_force(sentence["text"]):
            return occurrence
    return None


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Resolve a high-confidence state or abstain for model fallback."""

    text = str(user_input or "")
    event_map = build_precise_target_event_map(
        text, candidates, focus_target_id, mention_patterns
    )
    focus = event_map["focus_occurrences"]
    if not focus:
        return {
            "resolved": False,
            "commitment": None,
            "confidence": "unresolved",
            "resolution_rule": "missing_focus_occurrence",
            "evidence": [],
            "event_map": event_map,
        }

    sentences = _spans(text, SENTENCE_BOUNDARY_RE)
    quote_spans = _quote_spans(text)
    mentions = _focus_mentions(focus)
    all_mentions_quoted = bool(mentions) and all(
        _inside_any((start, end), quote_spans) for start, end, _ in mentions
    )
    marker_types = _scope_marker_types(focus)
    focus_sentences = {
        occurrence["sentence_index"]: _sentence_for_occurrence(sentences, occurrence)
        for occurrence in focus
    }
    local_text = "".join(row["text"] for row in focus_sentences.values())
    evidence = []

    if all_mentions_quoted and META_CONTEXT_RE.search(text):
        if EXPLICIT_NONEXECUTION_RE.search(text):
            commitment = "negated"
            rule = "quoted_data_with_explicit_nonexecution"
        else:
            commitment = "mentioned"
            rule = "quoted_or_metalinguistic_mention"
        evidence.extend(span[2] for span in quote_spans if any(_inside_any(m[:2], [span]) for m in mentions))
        return {
            "resolved": True,
            "commitment": commitment,
            "confidence": "high",
            "resolution_rule": rule,
            "evidence": evidence,
            "event_map": event_map,
        }

    if PENDING_RE.search(local_text):
        return {
            "resolved": True,
            "commitment": "ambiguous",
            "confidence": "high",
            "resolution_rule": "pending_or_undecided_choice",
            "evidence": [PENDING_RE.search(local_text).group(0)],
            "event_map": event_map,
        }

    if HYPOTHETICAL_RE.search(local_text):
        return {
            "resolved": True,
            "commitment": "hypothetical",
            "confidence": "high",
            "resolution_rule": "explicit_hypothetical_scope",
            "evidence": [HYPOTHETICAL_RE.search(local_text).group(0)],
            "event_map": event_map,
        }

    if "referential_cancellation" in marker_types:
        return {
            "resolved": True,
            "commitment": "cancelled",
            "confidence": "high",
            "resolution_rule": "same_utterance_referential_cancellation",
            "evidence": sorted(marker_types),
            "event_map": event_map,
        }

    if "target_local_cessation" in marker_types:
        return {
            "resolved": True,
            "commitment": "cancelled",
            "confidence": "high",
            "resolution_rule": "target_local_cessation",
            "evidence": sorted(marker_types),
            "event_map": event_map,
        }

    positive_idle = focus_target_id == "motion.idle" and POSITIVE_IDLE_RE.search(
        local_text
    )
    if "target_local_negation" in marker_types and not positive_idle:
        return {
            "resolved": True,
            "commitment": "negated",
            "confidence": "high",
            "resolution_rule": "target_local_negation",
            "evidence": sorted(marker_types),
            "event_map": event_map,
        }

    later_replacement = _later_same_domain_request(
        event_map, focus_target_id, sentences
    )
    if later_replacement is not None:
        last_focus_end = max(end for _, end, _ in mentions)
        later_start = min(
            mention["start"] for mention in later_replacement["target_mentions"]
        )
        between = text[last_focus_end:later_start]
        if CORRECTION_RE.search(between):
            return {
                "resolved": True,
                "commitment": "cancelled",
                "confidence": "high",
                "resolution_rule": "cross_target_late_replacement",
                "evidence": [CORRECTION_RE.search(between).group(0)],
                "event_map": event_map,
            }

    request_sentences = [
        sentence["text"]
        for sentence in focus_sentences.values()
        if _request_force(sentence["text"])
    ]
    if QUESTION_RE.search(local_text) and not request_sentences:
        return {
            "resolved": True,
            "commitment": "mentioned",
            "confidence": "high",
            "resolution_rule": "nonrequest_question",
            "evidence": [local_text],
            "event_map": event_map,
        }

    if not request_sentences and (
        DESCRIPTIVE_RE.search(local_text) or THIRD_PARTY_RE.search(local_text)
    ):
        return {
            "resolved": True,
            "commitment": "mentioned",
            "confidence": "high",
            "resolution_rule": "descriptive_or_habitual_mention",
            "evidence": [local_text],
            "event_map": event_map,
        }

    if request_sentences or positive_idle:
        return {
            "resolved": True,
            "commitment": "requested",
            "confidence": "high",
            "resolution_rule": (
                "positive_idle_request" if positive_idle else "explicit_request_force"
            ),
            "evidence": request_sentences or [positive_idle.group(0)],
            "event_map": event_map,
        }

    return {
        "resolved": False,
        "commitment": None,
        "confidence": "unresolved",
        "resolution_rule": "no_high_confidence_transition",
        "evidence": [],
        "event_map": event_map,
    }


def select_commitment(state_result, fallback_commitment):
    """Use deterministic state when resolved; otherwise preserve frozen fallback."""

    if state_result["resolved"]:
        return {
            "commitment": state_result["commitment"],
            "source": "deterministic_state_machine",
            "fallback_used": False,
        }
    return {
        "commitment": fallback_commitment,
        "source": "frozen_model_fallback",
        "fallback_used": True,
    }
