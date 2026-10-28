#!/usr/bin/env python3
"""Strict machine-observable visible-surface checks for prospective P3 runs."""

from __future__ import annotations

import re
from typing import Any

from p3_product_comparison import shared_visible_surface_contract
from rightbrain_language_quality import has_bad_language


JAPANESE_KANA_RE = re.compile(r"[ぁ-んァ-ヶ]")


def strict_japanese_visible_surface_contract(reply: Any) -> dict[str, bool]:
    """Extend the legacy P3 surface contract without claiming naturalness.

    The legacy `has_japanese` predicate includes the Han block, so an entirely
    Chinese reply can satisfy it.  A normal Japanese chat utterance must contain
    at least one hiragana or katakana codepoint here, and it must not contain any
    language residues already rejected by the runtime Japanese guard.
    """

    text = str(reply or "").strip()
    return {
        **shared_visible_surface_contract(text),
        "has_japanese_kana": bool(JAPANESE_KANA_RE.search(text)),
        "no_known_foreign_language_leak": not has_bad_language(text),
    }

