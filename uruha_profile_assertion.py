"""Conservative scope guard for profile facts extracted from user utterances."""

from __future__ import annotations

import re


QUESTION_MARKS = frozenset({"?", "？"})
REPORT_PATTERNS = (
    re.compile(r"\b(?:said|says|wrote|writes|asked|asks|told|according to)\b", re.IGNORECASE),
    re.compile(r"(?:說|说|寫|写|問|问|表示|提到)"),
    re.compile(r"(?:と|って)(?:言った|言ってた|書いた|聞いた|話した)|によると"),
)
JAPANESE_THIRD_PERSON = re.compile(
    r"^\s*(?:友達|友人|彼|彼女|母|父|兄|姉|弟|妹|同僚|先生|上司|部下|家族|親戚)(?:は|が|も)"
)
OUTER_QUOTE = re.compile(r"^\s*(?:['\"「『].*['\"」』])\s*[。.!]?\s*$", re.DOTALL)
ENGLISH_SELF_ASSERTION = re.compile(
    r"^\s*(?:(?:honestly|actually|personally)[, ]+)?(?:i\b|my\s+favorite\b)",
    re.IGNORECASE,
)
CHINESE_SELF_ASSERTION = re.compile(r"^\s*(?:其實|其实|現在|现在)?我")


def classify_profile_assertion_scope(text, facts):
    """Classify whether extracted facts belong to a direct user assertion."""
    utterance = str(text or "").strip()
    rows = list(facts or [])
    if not rows:
        return {"allow": True, "reason": "no_extracted_facts"}
    if not utterance:
        return {"allow": False, "reason": "empty_utterance"}
    if any(mark in utterance for mark in QUESTION_MARKS):
        return {"allow": False, "reason": "question_scope"}
    if OUTER_QUOTE.match(utterance):
        return {"allow": False, "reason": "quoted_scope"}
    if any(pattern.search(utterance) for pattern in REPORT_PATTERNS):
        return {"allow": False, "reason": "reported_scope"}

    fact_types = {str(row[0]) for row in rows if isinstance(row, (list, tuple)) and row}
    if fact_types and fact_types.issubset({"name"}):
        return {"allow": True, "reason": "bounded_name_request"}
    if ENGLISH_SELF_ASSERTION.match(utterance):
        return {"allow": True, "reason": "english_self_assertion"}
    if CHINESE_SELF_ASSERTION.match(utterance):
        return {"allow": True, "reason": "chinese_self_assertion"}
    if JAPANESE_THIRD_PERSON.match(utterance):
        return {"allow": False, "reason": "japanese_third_person"}
    return {"allow": True, "reason": "unmarked_japanese_self_assertion"}


def filter_profile_facts_by_assertion_scope(text, facts):
    """Return the unchanged fact tuples only when scope is a direct assertion."""
    rows = list(facts or [])
    decision = classify_profile_assertion_scope(text, rows)
    return rows if decision["allow"] else []
