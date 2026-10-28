"""Opt-in admission for two bounded temporal forms of explicit episode recall.

Only classification is widened: the existing source-bound focus contract still
receives the actual user input and retrieved memory.  This module neither
resolves facts nor changes retrieval, ranking, planning, or visible authority.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

import uruha_explicit_episode_recall_focus_p4 as focus


SCHEMA = "uruha_temporal_specific_recall_admission_p4"
CERTIFICATE_KEY = "temporal_admission_p4"
_PREFIXES = ("少し前に", "ちょっと前に")
_EXPECTED_QUERY_PATTERN = (
    r"(?:さっき|前に|以前)(?:私が|うちが)?"
    r"(?:言った|話した|教えた|決めた)"
    r"(?P<focus>[^、，,。.!！？?「」『』\n]{2,32})"
    r"[、，,\s]*覚えて(?:る|いる)[?？]"
)
_BASE_CLASSIFIER = focus.classify_explicit_episode_recall_focus_p4
_INSTALLED = False


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _focus_shape_is_frozen() -> bool:
    """Do not widen a changed/unknown source contract by accident."""
    return bool(
        focus.LABEL == "explicit_episode_recall_focus_p4"
        and focus.SCHEMA == "uruha_explicit_episode_recall_focus_p4"
        and isinstance(focus._QUERY, re.Pattern)
        and focus._QUERY.pattern == _EXPECTED_QUERY_PATTERN
        and _BASE_CLASSIFIER.__module__ == focus.__name__
        and _BASE_CLASSIFIER.__name__ == "classify_explicit_episode_recall_focus_p4"
    )


def classify_temporal_specific_recall_admission_p4(user_input: str) -> dict:
    """Return the old decision unless a precise modifier passes old grammar.

    The rewritten string is only a classifier proxy.  The returned receipt is
    bound to the exact UTF-8 input bytes, not the proxy; no proxy reaches the
    memory retriever or source/speakability checks.
    """
    original = _BASE_CLASSIFIER(user_input)
    if original.get("eligible") or not _focus_shape_is_frozen():
        return original
    raw = str(user_input or "")
    normalized = unicodedata.normalize("NFKC", raw).strip()
    prefix = next((item for item in _PREFIXES if normalized.startswith(item)), None)
    if prefix is None:
        return original
    proxy = "前に" + normalized[len(prefix) :]
    proxy_decision = _BASE_CLASSIFIER(proxy)
    if not proxy_decision.get("eligible"):
        return original
    raw_sha = _sha(raw)
    return {
        **proxy_decision,
        "input_sha256": raw_sha,
        "reason": "bounded_temporal_modifier_admitted_to_existing_source_contract",
        CERTIFICATE_KEY: {
            "schema": SCHEMA,
            "status": "admitted",
            "temporal_phrase": prefix,
            "input_sha256": raw_sha,
            "classification_proxy_sha256": _sha(proxy),
            "retrieval_input_unchanged": True,
            "source_contract": focus.SCHEMA,
            "model_call_added": False,
            "profile_write_count": 0,
            "claim_boundary": "syntax admission only; existing retrieved direct User-span contract remains authoritative",
        },
    }


def install_temporal_specific_recall_admission_p4() -> bool:
    """Install after the explicit episode focus overlay, or fail closed."""
    global _INSTALLED
    if _INSTALLED:
        return False
    if (
        not focus._INSTALLED
        or focus.classify_explicit_episode_recall_focus_p4 is not _BASE_CLASSIFIER
        or not _focus_shape_is_frozen()
    ):
        raise RuntimeError("temporal recall admission requires the frozen source-bound focus contract")
    focus.classify_explicit_episode_recall_focus_p4 = classify_temporal_specific_recall_admission_p4
    _INSTALLED = True
    return True


__all__ = [
    "SCHEMA",
    "CERTIFICATE_KEY",
    "classify_temporal_specific_recall_admission_p4",
    "install_temporal_specific_recall_admission_p4",
]
