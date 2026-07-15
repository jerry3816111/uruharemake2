#!/usr/bin/env python3
"""Build V52 event maps with separate target mentions and predicate evidence."""

import re

from target_event_map_v51 import (
    CLAUSE_BOUNDARY_RE,
    SENTENCE_BOUNDARY_RE,
    _containing_index,
    _merge_candidate_anchors,
    _scope_by_anchor,
    _spans,
)
from target_relative_scope_v48 import perceive_target_relative_scope


def compile_mention_patterns(patterns):
    return {target_id: re.compile(pattern) for target_id, pattern in patterns.items()}


def _deduplicate_matches(matches):
    ordered = sorted(
        matches,
        key=lambda row: (
            row["start"],
            -(row["end"] - row["start"]),
            row["text"],
        ),
    )
    selected = []
    for row in ordered:
        if any(
            row["start"] < kept["end"] and row["end"] > kept["start"]
            for kept in selected
        ):
            continue
        selected.append(row)
    return selected


def _target_mentions(text, occurrence, pattern):
    matches = [
        {
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
        }
        for match in pattern.finditer(text)
        if match.start() >= occurrence["start"] and match.end() <= occurrence["end"]
    ]
    return _deduplicate_matches(matches)


def _scope_reasons(occurrence, scope_lookup):
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
    unique = {
        (
            reason.get("marker_type"),
            reason.get("start"),
            reason.get("end"),
            reason.get("assigned_target_id"),
        ): reason
        for reason in reasons
    }
    return [unique[key] for key in sorted(unique)]


def build_precise_target_event_map(
    user_input, candidates, focus_target_id, mention_patterns
):
    """Return an answer-free event map ordered by precise target mentions."""

    text = str(user_input or "")
    candidate_ids = {candidate["target_id"] for candidate in candidates}
    if focus_target_id not in candidate_ids:
        raise ValueError("focus_target_id must be one of the grounded candidates")
    compiled = compile_mention_patterns(mention_patterns)
    missing_patterns = candidate_ids - set(compiled)
    if missing_patterns:
        raise ValueError(f"Missing target mention patterns: {sorted(missing_patterns)}")

    sentences = _spans(text, SENTENCE_BOUNDARY_RE)
    clauses = _spans(text, CLAUSE_BOUNDARY_RE)
    scope_lookup = _scope_by_anchor(perceive_target_relative_scope(text, candidates))
    occurrences = []
    for candidate in candidates:
        for broad in _merge_candidate_anchors(candidate):
            mentions = _target_mentions(text, broad, compiled[broad["target_id"]])
            fallback = not mentions
            if fallback:
                mentions = [
                    {
                        "text": text[broad["start"] : broad["end"]],
                        "start": broad["start"],
                        "end": broad["end"],
                    }
                ]
            occurrences.append(
                {
                    **broad,
                    "target_mentions": mentions,
                    "mention_fallback_used": fallback,
                    "mention_start": min(row["start"] for row in mentions),
                    "mention_end": max(row["end"] for row in mentions),
                }
            )
    occurrences.sort(
        key=lambda row: (
            row["mention_start"],
            row["mention_end"],
            row["target_id"],
        )
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
            sentences, occurrence["mention_start"], occurrence["mention_end"]
        )
        clause_index = _containing_index(
            clauses, occurrence["mention_start"], occurrence["mention_end"]
        )
        predicate_evidence = [
            {
                "text": anchor["text"],
                "start": anchor["start"],
                "end": anchor["end"],
            }
            for anchor in occurrence["anchors"]
        ]
        row = {
            "order": order,
            "target_id": occurrence["target_id"],
            "relation_to_focus": (
                "focus" if occurrence["target_id"] == focus_target_id else "other"
            ),
            "target_mentions": occurrence["target_mentions"],
            "predicate_evidence": predicate_evidence,
            "mention_fallback_used": occurrence["mention_fallback_used"],
            "sentence_index": sentence_index,
            "clause_index": clause_index,
            "sentence_text": sentences[sentence_index]["text"],
            "clause_text": clauses[clause_index]["text"],
            "is_latest_focus_occurrence": order == latest_focus_position,
            "scope_reasons": _scope_reasons(occurrence, scope_lookup),
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


def audit_precise_event_maps(candidate_rows, mention_patterns):
    occurrence_count = 0
    covered_count = 0
    inside_count = 0
    fallback_count = 0
    overlap_rows = []
    for candidate_row in candidate_rows:
        maps = [
            build_precise_target_event_map(
                candidate_row["user_input"],
                candidate_row["candidates"],
                candidate["target_id"],
                mention_patterns,
            )
            for candidate in candidate_row["candidates"]
        ]
        if not maps:
            continue
        occurrences = maps[0]["ordered_grounded_occurrences"]
        occurrence_count += len(occurrences)
        for occurrence in occurrences:
            fallback_count += int(occurrence["mention_fallback_used"])
            covered_count += int(bool(occurrence["target_mentions"]))
            evidence = occurrence["predicate_evidence"]
            for mention in occurrence["target_mentions"]:
                inside_count += int(
                    any(
                        mention["start"] >= row["start"]
                        and mention["end"] <= row["end"]
                        for row in evidence
                    )
                )
        for index, left in enumerate(occurrences):
            for right in occurrences[index + 1 :]:
                if left["target_id"] == right["target_id"]:
                    continue
                for left_mention in left["target_mentions"]:
                    for right_mention in right["target_mentions"]:
                        if (
                            left_mention["start"] < right_mention["end"]
                            and left_mention["end"] > right_mention["start"]
                        ):
                            overlap_rows.append(
                                {
                                    "case_id": candidate_row["case_id"],
                                    "left_target_id": left["target_id"],
                                    "right_target_id": right["target_id"],
                                    "left_mention": left_mention,
                                    "right_mention": right_mention,
                                }
                            )
    mention_count = sum(
        len(occurrence["target_mentions"])
        for candidate_row in candidate_rows
        for occurrence in (
            build_precise_target_event_map(
                candidate_row["user_input"],
                candidate_row["candidates"],
                candidate_row["candidates"][0]["target_id"],
                mention_patterns,
            )["ordered_grounded_occurrences"]
            if candidate_row["candidates"]
            else []
        )
    )
    return {
        "grounded_occurrence_count": occurrence_count,
        "covered_occurrence_count": covered_count,
        "grounded_occurrence_mention_coverage": (
            round(covered_count / occurrence_count, 4) if occurrence_count else 1.0
        ),
        "fallback_occurrence_count": fallback_count,
        "mention_count": mention_count,
        "mention_inside_predicate_evidence_count": inside_count,
        "mention_inside_predicate_evidence_rate": (
            round(inside_count / mention_count, 4) if mention_count else 1.0
        ),
        "cross_target_mention_overlap_count": len(overlap_rows),
        "cross_target_mention_overlaps": overlap_rows,
    }
