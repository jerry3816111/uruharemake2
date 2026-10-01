#!/usr/bin/env python3
"""Quotation-aware strict machine-visible surface contract for future P3 runs."""

from __future__ import annotations

import re
from typing import Any

from p3_product_comparison import shared_visible_surface_contract
from rightbrain_language_quality import has_bad_language


JAPANESE_KANA_RE = re.compile(r"[ぁ-んァ-ヶ]")
TRANSLATION_WRAPPER_RE = re.compile(r"^(?:英語|中国語|日本語)版\s*[：:]")
WHOLE_REPLY_QUOTE_PAIRS = (
    ("\"", "\""),
    ("'", "'"),
    ("“", "”"),
    ("‘", "’"),
    ("「", "」"),
    ("『", "』"),
)


def has_quote_or_translation_wrapper(text: str) -> bool:
    """Reject response packaging, not ordinary quotations inside a sentence."""

    stripped = str(text or "").strip()
    if TRANSLATION_WRAPPER_RE.search(stripped):
        return True
    return any(
        len(stripped) >= 2 and stripped.startswith(left) and stripped.endswith(right)
        for left, right in WHOLE_REPLY_QUOTE_PAIRS
    )


def strict_japanese_visible_surface_contract(reply: Any) -> dict[str, bool]:
    text = str(reply or "").strip()
    legacy = shared_visible_surface_contract(text)
    legacy["no_quote_or_translation_wrapper"] = not has_quote_or_translation_wrapper(text)
    return {
        **legacy,
        "has_japanese_kana": bool(JAPANESE_KANA_RE.search(text)),
        "no_known_foreign_language_leak": not has_bad_language(text),
    }

