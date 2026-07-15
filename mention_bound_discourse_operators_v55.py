#!/usr/bin/env python3
"""Bind discourse operators to target mentions and clauses for V55."""

import re

from metalinguistic_nonrequest_v54 import resolve_target_state as resolve_v54
from selective_discourse_state_v53 import (
    CORRECTION_RE,
    HYPOTHETICAL_RE,
    META_CONTEXT_RE,
    PENDING_RE,
    POSITIVE_IDLE_RE,
    QUESTION_RE,
    _focus_mentions,
    _inside_any,
    _quote_spans,
    _request_force,
)


EXECUTION_PROHIBITION_OPERATOR_RE = re.compile(
    r"(?:実行|動作)[^。！？!?]{0,16}(?:禁止|不可|しない|しません|しないで|やめて)"
)
META_DATA_CONTEXT_RE = re.compile(
    rf"(?:{META_CONTEXT_RE.pattern}|台本|例文|サンプル)"
)
FINITE_ASSERTION_RE = re.compile(
    r"(?:"
    r"ている|ていた|てる|ていました|ました|でした|だった|"
    r"ることで|見える|です|"
    r"[ぁ-んァ-ン一-龠ー](?:た|だ)"
    r")[^。！？!?]{0,8}[。！？!?、，,；;]*$"
)
EXPLICIT_SUBJECT_RE = re.compile(
    r"(?:彼|彼女|彼ら|トム|メアリー|犬|猫|人|私たち|私|僕|俺)(?:は|が)"
)
COLLOQUIAL_DIRECTIVE_END_RE = re.compile(r"(?:て|で)[。！？!?、，,；;]*$")
TRAILING_CLAUSE_SEPARATOR_RE = re.compile(r"[、，,；;]+$")


def _unique_focus_texts(event_map, field):
    values = []
    for occurrence in event_map["focus_occurrences"]:
        value = occurrence[field]
        if value not in values:
            values.append(value)
    return values


def _local_request_force(text):
    clause = str(text or "").strip()
    if not clause or QUESTION_RE.search(clause) or FINITE_ASSERTION_RE.search(clause):
        return False
    without_separator = TRAILING_CLAUSE_SEPARATOR_RE.sub("", clause)
    if _request_force(without_separator):
        return True
    return bool(
        COLLOQUIAL_DIRECTIVE_END_RE.search(clause)
        and not EXPLICIT_SUBJECT_RE.search(clause)
    )


def _finite_assertion(texts):
    return any(FINITE_ASSERTION_RE.search(str(text or "").strip()) for text in texts)


def _override(result, commitment, rule, evidence, correction):
    return {
        **result,
        "resolved": True,
        "commitment": commitment,
        "confidence": "high",
        "resolution_rule": rule,
        "evidence": evidence,
        "v55_correction": correction,
    }


def _cross_domain_replacement(text, event_map, focus_target_id):
    focus = event_map["focus_occurrences"]
    if not focus:
        return None
    focus_orders = [row["order"] for row in focus]
    last_order = max(focus_orders)
    last_end = max(
        mention["end"]
        for occurrence in focus
        for mention in occurrence["target_mentions"]
    )
    for occurrence in event_map["ordered_grounded_occurrences"]:
        if occurrence["order"] <= last_order:
            continue
        later_start = min(row["start"] for row in occurrence["target_mentions"])
        between = text[last_end:later_start]
        marker = CORRECTION_RE.search(between)
        later_is_request = _local_request_force(
            occurrence["clause_text"]
        ) or (
            occurrence["target_id"] == "motion.idle"
            and POSITIVE_IDLE_RE.search(occurrence["clause_text"])
        )
        if marker and later_is_request:
            return {
                "marker": marker.group(0),
                "replacement_target_id": occurrence["target_id"],
                "focus_target_id": focus_target_id,
            }
    return None


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply mention-bound operators after the frozen V54 transition chain."""

    result = resolve_v54(user_input, candidates, focus_target_id, mention_patterns)
    text = str(user_input or "")
    event_map = result["event_map"]
    focus_clauses = _unique_focus_texts(event_map, "clause_text")
    focus_sentences = _unique_focus_texts(event_map, "sentence_text")
    local_text = "".join(focus_clauses)
    local_request = any(_local_request_force(clause) for clause in focus_clauses)
    local_assertion = _finite_assertion(focus_clauses)
    sentence_assertion = _finite_assertion(focus_sentences)

    mentions = _focus_mentions(event_map["focus_occurrences"])
    quote_spans = _quote_spans(text)
    all_mentions_quoted = bool(mentions) and all(
        _inside_any((start, end), quote_spans) for start, end, _ in mentions
    )
    prohibition = EXECUTION_PROHIBITION_OPERATOR_RE.search(text)
    if all_mentions_quoted and META_DATA_CONTEXT_RE.search(text) and prohibition:
        return _override(
            result,
            "negated",
            "mention_bound_execution_prohibition",
            [prohibition.group(0)],
            {"operator": "execution_prohibition", "binding": "quoted_focus_target"},
        )

    replacement = _cross_domain_replacement(text, event_map, focus_target_id)
    if replacement and result["commitment"] != "cancelled":
        return _override(
            result,
            "cancelled",
            "mention_bound_cross_domain_replacement",
            [replacement["marker"]],
            {"operator": "correction", **replacement},
        )

    scope_rule = result["resolution_rule"]
    pending_is_local = bool(PENDING_RE.search(local_text))
    hypothetical_is_local = bool(HYPOTHETICAL_RE.search(local_text))
    misplaced_scope = (
        scope_rule == "pending_or_undecided_choice" and not pending_is_local
    ) or (
        scope_rule == "explicit_hypothetical_scope" and not hypothetical_is_local
    )
    if misplaced_scope:
        if local_request:
            commitment = "requested"
        elif local_assertion or sentence_assertion:
            commitment = "mentioned"
        else:
            return {
                **result,
                "resolved": False,
                "commitment": None,
                "confidence": "unresolved",
                "resolution_rule": "mention_bound_scope_abstention",
                "evidence": [],
            }
        return _override(
            result,
            commitment,
            "mention_bound_scope_reassignment",
            focus_clauses,
            {"operator": "scope", "from_sentence_wide": scope_rule},
        )

    if (
        scope_rule == "explicit_request_force"
        and not local_request
        and (local_assertion or sentence_assertion)
    ):
        return _override(
            result,
            "mentioned",
            "mention_bound_request_force",
            focus_clauses,
            {"operator": "request_force", "binding": "focus_clause_only"},
        )

    if not result["resolved"]:
        if local_request:
            return _override(
                result,
                "requested",
                "mention_bound_local_directive",
                focus_clauses,
                {"operator": "request_force", "binding": "focus_clause"},
            )
        if local_assertion or sentence_assertion:
            return _override(
                result,
                "mentioned",
                "mention_bound_finite_assertion",
                focus_clauses,
                {"operator": "finite_assertion", "binding": "focus_event"},
            )

    return result
