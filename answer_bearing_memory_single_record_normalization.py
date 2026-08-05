#!/usr/bin/env python3
"""Conservative boundary normalization for single-record evidence payloads."""

from __future__ import annotations


RULE_ID = "unsupported_quote_only_empty_placeholder_v1"
QUOTE_ONLY_EMPTY_PLACEHOLDERS = frozenset({'""', "''", "“”", "‘’"})


def normalize(payload):
    audit = {
        "rule_id": RULE_ID,
        "applied": False,
        "reason": "not_eligible",
        "before_answer_span": None,
        "after_answer_span": None,
    }
    if not isinstance(payload, dict) or set(payload) != {"supports_answer", "answer_span"}:
        audit["reason"] = "invalid_payload_shape"
        return payload, audit
    supports = payload.get("supports_answer")
    span = payload.get("answer_span")
    if not isinstance(supports, bool) or not isinstance(span, str):
        audit["reason"] = "invalid_payload_types"
        return payload, audit
    audit["before_answer_span"] = span
    audit["after_answer_span"] = span
    if supports:
        audit["reason"] = "positive_verdict_untouched"
        return dict(payload), audit
    stripped = span.strip()
    if stripped not in QUOTE_ONLY_EMPTY_PLACEHOLDERS:
        audit["reason"] = "not_quote_only_empty_placeholder"
        return dict(payload), audit
    normalized = dict(payload)
    normalized["answer_span"] = ""
    audit.update(
        {
            "applied": True,
            "reason": "normalized_quote_only_empty_placeholder",
            "after_answer_span": "",
        }
    )
    return normalized, audit
