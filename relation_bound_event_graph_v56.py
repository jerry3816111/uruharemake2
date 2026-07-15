#!/usr/bin/env python3
"""Resolve VRM action commitment from typed relations between events and clauses."""

import re

from metalinguistic_nonrequest_v54 import resolve_target_state as resolve_v54
from selective_discourse_state_v53 import (
    CORRECTION_RE,
    HYPOTHETICAL_RE,
    META_CONTEXT_RE,
    PENDING_RE,
    POSITIVE_IDLE_RE,
    QUESTION_RE,
    THIRD_PARTY_RE,
    _focus_mentions,
    _inside_any,
    _quote_spans,
    _request_force,
)
from target_event_map_v51 import CLAUSE_BOUNDARY_RE, SENTENCE_BOUNDARY_RE, _spans


EXECUTION_PROHIBITION_RE = re.compile(
    r"(?:実行|動作)[^。！？!?]{0,16}(?:禁止|不可|しない|しません|しないで|やめて)"
)
META_DATA_CONTEXT_RE = re.compile(
    rf"(?:{META_CONTEXT_RE.pattern}|台本|例文|サンプル)"
)
EXPLICIT_SUBJECT_RE = re.compile(
    r"(?:彼|彼女|彼ら|トム|メアリー|犬|猫|人|私たち|私|僕|俺)(?:は|が)"
)
DIRECTIVE_CUE_RE = re.compile(r"(?:さぁ|さあ|ほら|お願い)(?:、|，|,|\s)*")
COLLOQUIAL_DIRECTIVE_END_RE = re.compile(r"(?:て|で)[。！？!?、，,；;]*$")
COORDINATE_CONNECTOR_RE = re.compile(
    r"(?:(?:て|で)(?:から)?|(?:た|だ)まま|ながら|つつ|(?:し|き|ぎ|ち|り|び|み|に))[、，,；;]*$"
)
LOCAL_PROGRESSIVE_RE = re.compile(
    r"(?:ている|でいる|ていた|でいた|てる|ていました|でいました|ています|でいます)"
    r"(?:けれど|けど|が|ので|から)?[。！？!?、，,；;]*$"
)
EXPLANATORY_EVENT_RE = re.compile(r"(?:る|う)ことで")
VISIBLE_STATE_RE = re.compile(r"(?:見える|見えている)")
FINITE_ASSERTION_END_RE = re.compile(
    r"(?:"
    r"ました|でした|だった|です|"
    r"返した|振った|向いた|見た|笑った|うなずいた|頷いた|"
    r"指した|示した|確認した|告げた|与える|見える"
    r")[。！？!?]*$"
)
CONDITIONAL_ANTECEDENT_RE = re.compile(
    r"(?:もし|仮に)[^。！？!?]{0,80}(?:たら|なら|れば|ならば|とき(?:は|に)?)"
)
PROTECTED_RULES = {
    "quoted_data_with_explicit_nonexecution",
    "quoted_data_declared_nonrequest",
    "quoted_or_metalinguistic_mention",
    "same_utterance_referential_cancellation",
    "target_local_cessation",
    "target_local_negation",
    "cross_target_late_replacement",
}


def _occurrence_span(occurrence):
    starts = [row["start"] for row in occurrence["target_mentions"]]
    ends = [row["end"] for row in occurrence["target_mentions"]]
    return min(starts), max(ends)


def _sentence_span_for(sentences, occurrence):
    return sentences[occurrence["sentence_index"]]


def _clause_span_for(clauses, occurrence):
    return clauses[occurrence["clause_index"]]


def _terminal_assertion(text):
    return bool(FINITE_ASSERTION_END_RE.search(str(text or "").strip()))


def _local_directive(clause_text, sentence_text, is_final_clause):
    clause = str(clause_text or "").strip()
    sentence = str(sentence_text or "").strip()
    if not clause:
        return False
    if _request_force(clause):
        return True
    if QUESTION_RE.search(clause):
        return False
    if not COLLOQUIAL_DIRECTIVE_END_RE.search(clause):
        return False
    if EXPLICIT_SUBJECT_RE.search(clause) or THIRD_PARTY_RE.search(clause):
        return False
    if is_final_clause:
        return not _terminal_assertion(sentence)
    return bool(DIRECTIVE_CUE_RE.search(clause)) and not _terminal_assertion(sentence)


def _local_description(clause_text, sentence_text, mention_end):
    clause = str(clause_text or "").strip()
    sentence = str(sentence_text or "").strip()
    tail = clause[max(0, mention_end) :]
    if _request_force(clause) or QUESTION_RE.search(clause):
        return False
    if LOCAL_PROGRESSIVE_RE.search(tail):
        return True
    if EXPLANATORY_EVENT_RE.search(tail) or VISIBLE_STATE_RE.search(tail):
        return True
    if _terminal_assertion(clause):
        return True
    return bool(COORDINATE_CONNECTOR_RE.search(clause) and _terminal_assertion(sentence))


def _conditional_governs(text, sentence, mention_start):
    prefix = text[sentence["start"] : mention_start]
    marker = CONDITIONAL_ANTECEDENT_RE.search(prefix)
    return marker.group(0) if marker else None


def _relation(relation_type, evidence, source="utterance", target="focus_event"):
    return {
        "type": relation_type,
        "source": source,
        "target": target,
        "evidence": evidence,
    }


def build_relation_graph(user_input, event_map, focus_target_id):
    """Build answer-free typed relations for one grounded focus target."""

    text = str(user_input or "")
    sentences = _spans(text, SENTENCE_BOUNDARY_RE)
    clauses = _spans(text, CLAUSE_BOUNDARY_RE)
    relations = []
    focus = event_map["focus_occurrences"]

    mentions = _focus_mentions(focus)
    quote_spans = _quote_spans(text)
    all_mentions_quoted = bool(mentions) and all(
        _inside_any((start, end), quote_spans) for start, end, _ in mentions
    )
    prohibition = EXECUTION_PROHIBITION_RE.search(text)
    if all_mentions_quoted and META_DATA_CONTEXT_RE.search(text) and prohibition:
        relations.append(
            _relation("execution_prohibition", prohibition.group(0), "operator")
        )

    for occurrence in focus:
        sentence = _sentence_span_for(sentences, occurrence)
        clause = _clause_span_for(clauses, occurrence)
        mention_start, mention_end = _occurrence_span(occurrence)
        relative_end = mention_end - clause["start"]
        is_final_clause = clause["end"] == sentence["end"]
        conditional = _conditional_governs(text, sentence, mention_start)
        if conditional:
            relations.append(
                _relation("conditional_governance", conditional, "antecedent")
            )
        if PENDING_RE.search(clause["text"]):
            relations.append(
                _relation(
                    "local_pending_scope", PENDING_RE.search(clause["text"]).group(0)
                )
            )
        if HYPOTHETICAL_RE.search(clause["text"]):
            relations.append(
                _relation(
                    "local_hypothetical_scope",
                    HYPOTHETICAL_RE.search(clause["text"]).group(0),
                )
            )
        if _local_directive(clause["text"], sentence["text"], is_final_clause):
            relations.append(_relation("local_directive", clause["text"]))
        if _local_description(clause["text"], sentence["text"], relative_end):
            relations.append(_relation("local_description", clause["text"]))

        later = [
            row
            for row in event_map["ordered_grounded_occurrences"]
            if row["order"] > occurrence["order"]
            and row["sentence_index"] == occurrence["sentence_index"]
        ]
        if COORDINATE_CONNECTOR_RE.search(clause["text"]):
            for other in later:
                other_clause = _clause_span_for(clauses, other)
                other_sentence = _sentence_span_for(sentences, other)
                if _local_directive(
                    other_clause["text"],
                    other_sentence["text"],
                    other_clause["end"] == other_sentence["end"],
                ):
                    relations.append(
                        _relation(
                            "shared_directive",
                            other_clause["text"],
                            source=other["target_id"],
                        )
                    )
                    break

    if focus:
        focus_last_order = max(row["order"] for row in focus)
        focus_last_end = max(end for _, end, _ in mentions)
        for other in event_map["ordered_grounded_occurrences"]:
            if other["order"] <= focus_last_order:
                continue
            other_clause = _clause_span_for(clauses, other)
            other_sentence = _sentence_span_for(sentences, other)
            other_start, _ = _occurrence_span(other)
            between = text[focus_last_end:other_start]
            marker = CORRECTION_RE.search(between)
            later_request = _local_directive(
                other_clause["text"],
                other_sentence["text"],
                other_clause["end"] == other_sentence["end"],
            ) or (
                other["target_id"] == "motion.idle"
                and POSITIVE_IDLE_RE.search(other_clause["text"])
            )
            if marker and later_request:
                relations.append(
                    _relation(
                        "cross_event_replacement",
                        marker.group(0),
                        source=other["target_id"],
                    )
                )
                break

    unique = []
    for row in relations:
        if not any(row == kept for kept in unique):
            unique.append(row)
    return {
        "focus_target_id": focus_target_id,
        "relations": unique,
        "relation_types": [row["type"] for row in unique],
    }


def _override(result, graph, commitment, rule, relation_type):
    evidence = [
        row["evidence"] for row in graph["relations"] if row["type"] == relation_type
    ]
    return {
        **result,
        "resolved": True,
        "commitment": commitment,
        "confidence": "high",
        "resolution_rule": rule,
        "evidence": evidence,
        "v56_relation_graph": graph,
        "v56_correction": {
            "relation_type": relation_type,
            "from_rule": result["resolution_rule"],
        },
    }


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply relation-graph decisions over the frozen V54 baseline."""

    result = resolve_v54(user_input, candidates, focus_target_id, mention_patterns)
    graph = build_relation_graph(user_input, result["event_map"], focus_target_id)
    types = set(graph["relation_types"])

    if "execution_prohibition" in types:
        return _override(
            result,
            graph,
            "negated",
            "relation_bound_execution_prohibition",
            "execution_prohibition",
        )
    if "cross_event_replacement" in types and result["commitment"] != "cancelled":
        return _override(
            result,
            graph,
            "cancelled",
            "relation_bound_cross_event_replacement",
            "cross_event_replacement",
        )

    if result["resolution_rule"] in PROTECTED_RULES:
        return {**result, "v56_relation_graph": graph}
    if types & {
        "conditional_governance",
        "local_pending_scope",
        "local_hypothetical_scope",
    }:
        return {**result, "v56_relation_graph": graph}
    if "local_directive" in types:
        return _override(
            result,
            graph,
            "requested",
            "relation_bound_local_directive",
            "local_directive",
        )
    if "shared_directive" in types:
        return _override(
            result,
            graph,
            "requested",
            "relation_bound_shared_directive",
            "shared_directive",
        )
    if "local_description" in types:
        return _override(
            result,
            graph,
            "mentioned",
            "relation_bound_local_description",
            "local_description",
        )
    return {**result, "v56_relation_graph": graph}
