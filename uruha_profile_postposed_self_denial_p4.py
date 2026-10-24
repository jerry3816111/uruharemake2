"""Bounded, postposed self-denial veto for the product legacy profile writer.

The frozen owner still decides each candidate.  This additive layer can only
remove a preceding positive candidate before that owner's writer sees facts;
it cannot create a dislike, change selected P4-I acts, or edit stored rows.
"""

from __future__ import annotations

from copy import deepcopy
import re

import uruha_profile_owner_admission_p4 as owner


LABEL = "profile_postposed_self_denial_p4"
_INSTALLED = False
_ORIGINAL_ADMIT = None
_POSITIVE_TYPES = frozenset({"like", "favorite"})
_COMMA_BOUNDARIES = frozenset({",", "，", "、"})
_ASSERTIVE_END = frozenset({"。", ".", "!", "！", ""})
_DIRECT_DENIAL = re.compile(
    r"^(?:これ|それ|この文|その文|上の文|さっきの文)は"
    r"私の好み(?:じゃない|ではない)$"
)
_EXAMPLE_PREAMBLE = re.compile(
    r"^(?:これ|それ|この文|その文|上の文|さっきの文)は作文の例文で$"
)
_EXAMPLE_DENIAL = re.compile(r"^私の好み(?:じゃない|ではない)$")


def _overlaps_quote(start, end, quote_spans):
    return any(start < quote_end and end > quote_start for quote_start, quote_end in quote_spans)


def _next_source_clause(clauses, quote_spans, after):
    for index in range(after + 1, len(clauses)):
        start, end, _, source = clauses[index]
        if not source.strip() and _overlaps_quote(start, end, quote_spans):
            return None  # An intervening quoted clause breaks adjacency.
        if source.strip():
            return index
    return None


def _denial_span(text, clauses, quote_spans, after):
    """Return only a bounded, immediately following explicit denial span."""
    index = _next_source_clause(clauses, quote_spans, after)
    if index is None:
        return None
    start, end, delimiter, source = clauses[index]
    source = source.strip()
    if len(source) > 48 or _overlaps_quote(start, end, quote_spans):
        return None
    if _DIRECT_DENIAL.fullmatch(source) and delimiter in _ASSERTIVE_END:
        return text[start:end]
    if not (_EXAMPLE_PREAMBLE.fullmatch(source) and delimiter in _COMMA_BOUNDARIES):
        return None
    tail_index = _next_source_clause(clauses, quote_spans, index)
    if tail_index is None or tail_index != index + 1:
        return None
    tail_start, tail_end, tail_delimiter, tail = clauses[tail_index]
    if (
        len(tail.strip()) > 24
        or tail_delimiter not in _ASSERTIVE_END
        or _overlaps_quote(tail_start, tail_end, quote_spans)
        or not _EXAMPLE_DENIAL.fullmatch(tail.strip())
    ):
        return None
    return text[start:tail_end]


def _aligned_candidates(text, clauses, decisions):
    """Pair original clause order with its audit, including duplicate spans."""
    candidates = []
    for clause_index, (start, end, _, source) in enumerate(clauses):
        candidate = owner._candidate(source.strip())
        if candidate:
            candidates.append((clause_index, start, end, candidate))
    decision_indices = [
        index for index, row in enumerate(decisions) if row.get("owner") != "quoted"
    ]
    if len(candidates) != len(decision_indices):
        return None
    aligned = {}
    for (clause_index, start, end, candidate), decision_index in zip(candidates, decision_indices):
        fact_type, value, _ = candidate
        row = decisions[decision_index]
        if (
            row.get("source_span_sha256") != owner._digest(text[start:end])
            or row.get("fact_type") != fact_type
            or row.get("value_sha256") != (owner._digest(value) if value else None)
        ):
            return None
        aligned[clause_index] = (decision_index, fact_type, value)
    return aligned


def apply_postposed_self_denial_p4(text, facts, audit):
    """Return writer facts and audit after source-bound positive-only vetoes."""
    text = str(text or "").strip()
    if not isinstance(audit, dict) or not isinstance(facts, list):
        return facts, audit
    if (
        audit.get("schema") != owner.SCHEMA
        or audit.get("path") != "legacy"
        or audit.get("input_sha256") != owner._digest(text)
        or audit.get("reason")
    ):
        return facts, audit
    parsed, failure = owner._masked_clauses(text)
    if failure:
        return facts, audit
    clauses, quote_spans, _ = parsed
    original_decisions = audit.get("decisions")
    if not isinstance(original_decisions, list):
        return facts, audit
    aligned = _aligned_candidates(text, clauses, original_decisions)
    if aligned is None:
        return facts, audit
    decisions = deepcopy(original_decisions)
    veto_count = 0
    for clause_index, (decision_index, fact_type, _) in aligned.items():
        row = decisions[decision_index]
        if (
            fact_type not in _POSITIVE_TYPES
            or row.get("admitted") is not True
            or row.get("owner") != "user"
        ):
            continue
        denial = _denial_span(text, clauses, quote_spans, clause_index)
        if denial is None:
            continue
        row["pre_veto_reason"] = row["reason"]
        row["pre_veto_owner"] = row["owner"]
        row["reason"] = "postposed_explicit_self_denial"
        row["owner"] = "unknown"
        row["admitted"] = False
        row["postposed_denial_source_span_sha256"] = owner._digest(denial)
        veto_count += 1
    if not veto_count:
        return facts, audit

    # The owner deduplicates facts. Rebuild only from still-admitted, aligned
    # source candidates so a later independent repeat survives an earlier veto.
    remaining = []
    seen = set()
    for _, (decision_index, fact_type, value) in aligned.items():
        row = decisions[decision_index]
        if row.get("admitted") is not True:
            continue
        key = (fact_type, value.casefold())
        if key not in seen:
            seen.add(key)
            remaining.append((fact_type, value))
    updated = deepcopy(audit)
    updated["decisions"] = decisions
    updated["admitted_count"] = sum(row.get("admitted") is True for row in decisions)
    updated["rejected_count"] = len(decisions) - updated["admitted_count"]
    updated["postposed_denial_veto_count"] = veto_count
    return remaining, updated


def admit_legacy_profile_facts_with_postposed_self_denial_p4(text):
    if not callable(_ORIGINAL_ADMIT):
        raise RuntimeError(f"{LABEL}:owner_admission_not_installed")
    facts, audit = _ORIGINAL_ADMIT(text)
    return apply_postposed_self_denial_p4(text, facts, audit)


def install_profile_postposed_self_denial_p4():
    global _INSTALLED, _ORIGINAL_ADMIT
    if _INSTALLED:
        return False
    if not owner._INSTALLED:
        raise RuntimeError(f"{LABEL}:owner_overlay_not_installed")
    _ORIGINAL_ADMIT = owner.admit_legacy_profile_facts
    owner.admit_legacy_profile_facts = admit_legacy_profile_facts_with_postposed_self_denial_p4
    _INSTALLED = True
    return True
