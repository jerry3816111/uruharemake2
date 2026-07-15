#!/usr/bin/env python3
"""Build a read-only ordered map of grounded target occurrences and clauses."""

import re

from target_relative_scope_v48 import perceive_target_relative_scope


SENTENCE_BOUNDARY_RE = re.compile(r"[。！？!?]+")
CLAUSE_BOUNDARY_RE = re.compile(r"[、，,；;。！？!?]+")


def _spans(text, boundary_re):
    spans = []
    start = 0
    for match in boundary_re.finditer(text):
        end = match.end()
        if end > start:
            spans.append({"start": start, "end": end, "text": text[start:end]})
        start = end
    if start < len(text) or not spans:
        spans.append({"start": start, "end": len(text), "text": text[start:]})
    return spans


def _containing_index(spans, start, end):
    for index, span in enumerate(spans):
        if start < span["end"] and end > span["start"]:
            return index
    return 0


def _merge_candidate_anchors(candidate):
    anchors = sorted(
        candidate["anchors"],
        key=lambda row: (row["start"], row["end"], row["text"]),
    )
    occurrences = []
    for anchor in anchors:
        if occurrences and anchor["start"] < occurrences[-1]["end"]:
            row = occurrences[-1]
            row["start"] = min(row["start"], anchor["start"])
            row["end"] = max(row["end"], anchor["end"])
            row["anchors"].append(anchor)
            continue
        occurrences.append(
            {
                "target_id": candidate["target_id"],
                "domain": candidate["domain"],
                "value": candidate["value"],
                "start": anchor["start"],
                "end": anchor["end"],
                "anchors": [anchor],
            }
        )
    return occurrences


def _scope_by_anchor(scope):
    return {
        (target["target_id"], anchor["start"], anchor["end"], anchor["text"]): (
            anchor.get("scope_reasons") or []
        )
        for target in scope["targets"]
        for anchor in target["anchors"]
    }


def build_target_event_map(user_input, candidates, focus_target_id):
    """Return structure only; no commitment or execution decision is produced."""

    text = str(user_input or "")
    candidate_ids = {candidate["target_id"] for candidate in candidates}
    if focus_target_id not in candidate_ids:
        raise ValueError("focus_target_id must be one of the grounded candidates")

    sentences = _spans(text, SENTENCE_BOUNDARY_RE)
    clauses = _spans(text, CLAUSE_BOUNDARY_RE)
    scope = perceive_target_relative_scope(text, candidates)
    scope_lookup = _scope_by_anchor(scope)
    occurrences = [
        occurrence
        for candidate in candidates
        for occurrence in _merge_candidate_anchors(candidate)
    ]
    occurrences.sort(
        key=lambda row: (row["start"], row["end"], row["target_id"])
    )
    focus_positions = [
        index
        for index, occurrence in enumerate(occurrences)
        if occurrence["target_id"] == focus_target_id
    ]
    latest_focus_position = focus_positions[-1]

    ordered = []
    focus_occurrences = []
    for order, occurrence in enumerate(occurrences):
        sentence_index = _containing_index(
            sentences, occurrence["start"], occurrence["end"]
        )
        clause_index = _containing_index(
            clauses, occurrence["start"], occurrence["end"]
        )
        reasons = []
        for anchor in occurrence["anchors"]:
            reasons.extend(
                scope_lookup.get(
                    (
                        occurrence["target_id"],
                        anchor["start"],
                        anchor["end"],
                        anchor["text"],
                    ),
                    [],
                )
            )
        unique_reasons = {
            (
                reason.get("marker_type"),
                reason.get("start"),
                reason.get("end"),
                reason.get("assigned_target_id"),
            ): reason
            for reason in reasons
        }
        row = {
            "order": order,
            "target_id": occurrence["target_id"],
            "relation_to_focus": (
                "focus" if occurrence["target_id"] == focus_target_id else "other"
            ),
            "anchor_text": text[occurrence["start"] : occurrence["end"]],
            "start": occurrence["start"],
            "end": occurrence["end"],
            "sentence_index": sentence_index,
            "clause_index": clause_index,
            "sentence_text": sentences[sentence_index]["text"],
            "clause_text": clauses[clause_index]["text"],
            "is_latest_focus_occurrence": order == latest_focus_position,
            "scope_reasons": [unique_reasons[key] for key in sorted(unique_reasons)],
        }
        ordered.append(row)
        if row["relation_to_focus"] == "focus":
            focus_occurrences.append(dict(row))

    return {
        "focus_target_id": focus_target_id,
        "sentence_count": len(sentences),
        "clause_count": len(clauses),
        "ordered_grounded_occurrences": ordered,
        "focus_occurrences": focus_occurrences,
    }
