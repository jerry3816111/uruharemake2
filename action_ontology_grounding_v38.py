#!/usr/bin/env python3
"""Ground V37 action frames to a finite VRM action ontology."""

import json
import re
from collections import defaultdict
from pathlib import Path

from action_selective_deliberation_v37 import (
    FRAME_TO_CALL,
    REFERENTIAL_CANCELLATION_RE,
    STRONG_NEGATION_RE,
    _call_key,
    _clause_spans,
    _overlaps,
    _substring_spans,
    derive_utterance_state,
    parse_action_frames,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"


def load_anchor_ontology(path=CONFIG_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    ontology = {}
    for key, patterns in config["action_anchor_ontology"].items():
        domain, value = key.split(".", 1)
        ontology[(domain, value)] = [re.compile(pattern) for pattern in patterns]
    return ontology


def parse_action_frames_with_local_warnings(user_input, raw_reply):
    parsed = parse_action_frames(user_input, raw_reply)
    warnings = [error for error in parsed["errors"] if error == "duplicate_frame_target"]
    fatal_errors = [error for error in parsed["errors"] if error != "duplicate_frame_target"]
    return {
        "parse_success": not fatal_errors,
        "errors": fatal_errors,
        "warnings": warnings,
        "frames": parsed["frames"],
        "derived_state": derive_utterance_state(parsed["frames"]),
    }


def find_action_anchors(user_input, domain, value, ontology):
    text = str(user_input or "")
    anchors = []
    for pattern in ontology.get((domain, value), []):
        for match in pattern.finditer(text):
            anchors.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(0),
                    "pattern": pattern.pattern,
                }
            )
    unique = {(row["start"], row["end"], row["text"]): row for row in anchors}
    return [unique[key] for key in sorted(unique)]


def _anchor_scope_reasons(user_input, anchor):
    text = str(user_input or "")
    anchor_span = (anchor["start"], anchor["end"])
    reasons = []
    matching_clauses = [
        clause
        for start, end, clause in _clause_spans(text)
        if _overlaps(anchor_span, (start, end))
    ]
    if matching_clauses and all(STRONG_NEGATION_RE.search(clause) for clause in matching_clauses):
        reasons.append("anchor_inside_negated_clause")
    cancellation = REFERENTIAL_CANCELLATION_RE.search(text)
    if cancellation and anchor["end"] <= cancellation.start():
        reasons.append("grounded_action_cancelled_later")
    return reasons


def _ground_frame(user_input, frame, ontology):
    evidence_spans = _substring_spans(str(user_input or ""), frame.get("evidence") or "")
    anchors = find_action_anchors(
        user_input,
        frame.get("domain"),
        frame.get("value"),
        ontology,
    )
    overlapping = [
        anchor
        for anchor in anchors
        if any(
            _overlaps((anchor["start"], anchor["end"]), evidence_span)
            for evidence_span in evidence_spans
        )
    ]
    safe = []
    blocked = []
    for anchor in overlapping:
        reasons = _anchor_scope_reasons(user_input, anchor)
        if reasons:
            blocked.append({"anchor": anchor, "reasons": reasons})
        else:
            safe.append(anchor)
    return {
        "all_target_anchors": anchors,
        "evidence_overlapping_anchors": overlapping,
        "safe_anchors": safe,
        "blocked_anchors": blocked,
    }


def compile_anchor_grounded(user_input, parsed, ontology=None):
    ontology = ontology or load_anchor_ontology()
    parsed = parsed or {}
    frames = parsed.get("frames") or []
    if not parsed.get("parse_success"):
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "blocked_frames": [
                {"frame": frame, "reasons": ["fatal_frame_parse_error"]} for frame in frames
            ],
            "ungrounded_execution_count": 0,
            "fail_closed": True,
        }

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
            grounding = _ground_frame(user_input, frame, ontology)
            if not grounding["evidence_overlapping_anchors"]:
                reasons.append("target_not_grounded_in_evidence")
            elif not grounding["safe_anchors"]:
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
    }
