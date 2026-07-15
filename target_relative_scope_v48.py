#!/usr/bin/env python3
"""Target-relative Japanese scope perception and grounded action compilation."""

import json
import re
from collections import defaultdict
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_ontology_grounding_v38 import find_action_anchors
from action_selective_deliberation_v37 import (
    FRAME_TO_CALL,
    _call_key,
    _clause_spans,
    _overlaps,
    _substring_spans,
)
from grounded_commitment_classifier_v42 import ground_supported_targets


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_relative_scope_v48_preregistration.json"


def _load_patterns(config_path=CONFIG_PATH):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    causal = config["causal_change"]
    return {
        "target_local_negation": re.compile(causal["negative_suffix_pattern"]),
        "target_local_cessation": re.compile(causal["cessation_pattern"]),
        "referential_cancellation": re.compile(
            causal["referential_cancellation_pattern"]
        ),
    }


def _anchor_key(target_id, anchor):
    return (target_id, anchor["start"], anchor["end"], anchor["text"])


def _merge_occurrences(candidate):
    anchors = sorted(
        candidate["anchors"], key=lambda row: (row["start"], row["end"], row["text"])
    )
    occurrences = []
    for anchor in anchors:
        if occurrences and anchor["start"] < occurrences[-1]["end"]:
            occurrence = occurrences[-1]
            occurrence["start"] = min(occurrence["start"], anchor["start"])
            occurrence["end"] = max(occurrence["end"], anchor["end"])
            occurrence["anchors"].append(anchor)
            continue
        occurrences.append(
            {
                "target_id": candidate["target_id"],
                "start": anchor["start"],
                "end": anchor["end"],
                "anchors": [anchor],
            }
        )
    return occurrences


def _clause_for_span(clauses, start, end):
    for clause_start, clause_end, clause_text in clauses:
        if _overlaps((start, end), (clause_start, clause_end)):
            return {
                "start": clause_start,
                "end": clause_end,
                "text": clause_text,
            }
    return None


def _markers(text, pattern, marker_type):
    return [
        {
            "marker_type": marker_type,
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
        }
        for match in pattern.finditer(text)
    ]


def perceive_target_relative_scope(user_input, candidates, config_path=CONFIG_PATH):
    text = str(user_input or "")
    patterns = _load_patterns(config_path)
    clauses = _clause_spans(text)
    occurrences = [
        occurrence
        for candidate in candidates
        for occurrence in _merge_occurrences(candidate)
    ]
    for occurrence in occurrences:
        occurrence["clause"] = _clause_for_span(
            clauses, occurrence["start"], occurrence["end"]
        )

    reasons_by_anchor = {
        _anchor_key(candidate["target_id"], anchor): []
        for candidate in candidates
        for anchor in candidate["anchors"]
    }
    assigned_markers = []
    local_markers = _markers(
        text, patterns["target_local_negation"], "target_local_negation"
    ) + _markers(
        text, patterns["target_local_cessation"], "target_local_cessation"
    )
    for marker in sorted(local_markers, key=lambda row: (row["start"], row["end"])):
        marker_clause = _clause_for_span(clauses, marker["start"], marker["end"])
        if marker_clause is None:
            continue
        eligible = [
            occurrence
            for occurrence in occurrences
            if occurrence["clause"]
            and occurrence["clause"]["start"] == marker_clause["start"]
            and occurrence["start"] < marker["end"]
        ]
        if not eligible:
            continue
        selected = max(eligible, key=lambda row: (row["start"], row["end"]))
        reason = {
            **marker,
            "assignment_rule": "nearest_preceding_or_overlapping_occurrence",
            "assigned_target_id": selected["target_id"],
            "assigned_occurrence": {
                "start": selected["start"],
                "end": selected["end"],
            },
        }
        assigned_markers.append(reason)
        for anchor in selected["anchors"]:
            reasons_by_anchor[_anchor_key(selected["target_id"], anchor)].append(reason)

    cancellation_markers = _markers(
        text, patterns["referential_cancellation"], "referential_cancellation"
    )
    for marker in cancellation_markers:
        for occurrence in occurrences:
            if occurrence["end"] > marker["start"]:
                continue
            reason = {
                **marker,
                "assignment_rule": "referential_cancellation_after_occurrence",
                "assigned_target_id": occurrence["target_id"],
                "assigned_occurrence": {
                    "start": occurrence["start"],
                    "end": occurrence["end"],
                },
            }
            assigned_markers.append(reason)
            for anchor in occurrence["anchors"]:
                reasons_by_anchor[_anchor_key(occurrence["target_id"], anchor)].append(
                    reason
                )

    rows = []
    for candidate in candidates:
        anchors = []
        for anchor in candidate["anchors"]:
            reasons = reasons_by_anchor[_anchor_key(candidate["target_id"], anchor)]
            anchors.append(
                {
                    **anchor,
                    "scope_reasons": reasons,
                    "blocked": bool(reasons),
                }
            )
        rows.append(
            {
                "target_id": candidate["target_id"],
                "domain": candidate["domain"],
                "value": candidate["value"],
                "anchors": anchors,
            }
        )
    return {
        "targets": rows,
        "assigned_markers": assigned_markers,
    }


def _scope_lookup(scope):
    return {
        _anchor_key(target["target_id"], anchor): anchor["scope_reasons"]
        for target in scope["targets"]
        for anchor in target["anchors"]
    }


def compile_target_relative_v48(user_input, parsed, ontology=None):
    ontology = ontology or load_v47_anchor_ontology()
    parsed = parsed or {}
    frames = parsed.get("frames") or []
    if not parsed.get("parse_success"):
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "blocked_frames": [
                {"frame": frame, "reasons": ["fatal_frame_parse_error"]}
                for frame in frames
            ],
            "ungrounded_execution_count": 0,
            "fail_closed": True,
            "scope": {"targets": [], "assigned_markers": []},
        }

    candidates = ground_supported_targets(user_input, ontology)
    scope = perceive_target_relative_scope(user_input, candidates)
    scope_lookup = _scope_lookup(scope)
    requested_by_domain = defaultdict(set)
    for frame in frames:
        if frame["commitment"] == "requested" and frame["value"] != "unsupported":
            requested_by_domain[frame["domain"]].add(frame["value"])
    conflicting_domains = {
        domain for domain, values in requested_by_domain.items() if len(values) > 1
    }

    accepted_calls = []
    accepted_frames = []
    blocked_frames = []
    seen_calls = set()
    for frame in frames:
        reasons = []
        mapping = FRAME_TO_CALL.get((frame["domain"], frame["value"]))
        grounding = None
        if frame["commitment"] != "requested":
            reasons.append("frame_not_requested")
        if mapping is None or frame["value"] == "unsupported":
            reasons.append("frame_not_allowlisted")
        if not frame.get("evidence_valid"):
            reasons.append("frame_lacks_exact_evidence")
        if frame["domain"] in conflicting_domains:
            reasons.append("multiple_requested_values_in_exclusive_domain")
        if mapping is not None and frame["commitment"] == "requested":
            evidence_spans = _substring_spans(
                str(user_input or ""), frame.get("evidence") or ""
            )
            anchors = find_action_anchors(
                user_input, frame["domain"], frame["value"], ontology
            )
            overlapping = [
                anchor
                for anchor in anchors
                if any(
                    _overlaps((anchor["start"], anchor["end"]), evidence_span)
                    for evidence_span in evidence_spans
                )
            ]
            safe = [
                anchor
                for anchor in overlapping
                if not scope_lookup.get(
                    _anchor_key(f"{frame['domain']}.{frame['value']}", anchor), []
                )
            ]
            blocked = [
                {
                    "anchor": anchor,
                    "scope_reasons": scope_lookup.get(
                        _anchor_key(f"{frame['domain']}.{frame['value']}", anchor), []
                    ),
                }
                for anchor in overlapping
                if scope_lookup.get(
                    _anchor_key(f"{frame['domain']}.{frame['value']}", anchor), []
                )
            ]
            grounding = {
                "all_target_anchors": anchors,
                "evidence_overlapping_anchors": overlapping,
                "safe_anchors": safe,
                "blocked_anchors": blocked,
            }
            if not overlapping:
                reasons.append("target_not_grounded_in_evidence")
            elif not safe:
                reasons.append("all_grounded_anchors_blocked_by_scope")
        call_key = _call_key(mapping) if mapping is not None else None
        if call_key in seen_calls:
            reasons.append("duplicate_compiled_call")
        if reasons:
            blocked_frames.append(
                {"frame": frame, "reasons": reasons, "grounding": grounding}
            )
            continue
        seen_calls.add(call_key)
        grounded_frame = dict(frame)
        grounded_frame["matched_anchor"] = grounding["safe_anchors"][0]
        accepted_frames.append(grounded_frame)
        accepted_calls.append(mapping)

    return {
        "accepted_calls": accepted_calls,
        "accepted_frames": accepted_frames,
        "blocked_frames": blocked_frames,
        "ungrounded_execution_count": sum(
            not frame.get("matched_anchor") for frame in accepted_frames
        ),
        "conflicting_requested_domains": sorted(conflicting_domains),
        "fail_closed": False,
        "scope": scope,
    }
