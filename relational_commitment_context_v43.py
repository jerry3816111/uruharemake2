#!/usr/bin/env python3
"""Commitment-only judgments with deterministic evidence and relational context."""

import json

from action_ontology_grounding_v38 import _anchor_scope_reasons
from action_selective_deliberation_v37 import COMMITMENTS, derive_utterance_state


def parse_commitment_only(raw_reply):
    errors = []
    try:
        payload = json.loads(str(raw_reply or ""))
    except (TypeError, json.JSONDecodeError):
        payload = {}
        errors.append("invalid_json")
    if not isinstance(payload, dict):
        payload = {}
        errors.append("root_not_object")
    if set(payload) != {"commitment"}:
        errors.append("root_fields_mismatch")
    commitment = payload.get("commitment")
    if not isinstance(commitment, str) or commitment not in COMMITMENTS:
        errors.append("invalid_commitment")
    return {
        "parse_success": not errors,
        "errors": list(dict.fromkeys(errors)),
        "commitment": commitment,
    }


def _ordered_latest_shortest(anchors):
    return sorted(
        anchors,
        key=lambda row: (
            -row["anchor"]["start"],
            row["anchor"]["end"] - row["anchor"]["start"],
            row["anchor"].get("pattern") or "",
        ),
    )


def select_evidence_anchor(user_input, candidate, commitment):
    enriched = [
        {
            "anchor": anchor,
            "scope_reasons": _anchor_scope_reasons(user_input, anchor),
        }
        for anchor in candidate["anchors"]
    ]
    preferred = []
    if commitment == "requested":
        preferred = [row for row in enriched if not row["scope_reasons"]]
    elif commitment == "negated":
        preferred = [
            row
            for row in enriched
            if "anchor_inside_negated_clause" in row["scope_reasons"]
        ]
    elif commitment == "cancelled":
        preferred = [
            row
            for row in enriched
            if "grounded_action_cancelled_later" in row["scope_reasons"]
        ]
    pool = preferred or enriched
    if not pool:
        raise ValueError("A grounded candidate must have at least one anchor")
    selected = _ordered_latest_shortest(pool)[0]
    return {
        **selected["anchor"],
        "selection_scope_reasons": selected["scope_reasons"],
        "selection_rule": (
            f"preferred_{commitment}" if preferred else "latest_anchor_fallback"
        ),
    }


def frame_from_commitment(user_input, candidate, judgment):
    if not judgment.get("parse_success"):
        raise ValueError("Cannot build a frame from an invalid commitment judgment")
    anchor = select_evidence_anchor(
        user_input, candidate, judgment["commitment"]
    )
    return {
        "domain": candidate["domain"],
        "value": candidate["value"],
        "commitment": judgment["commitment"],
        "evidence": anchor["text"],
        "evidence_valid": True,
        "candidate_anchor": anchor,
    }


def assemble_commitment_only_case(user_input, candidates, judgments_by_target):
    expected_ids = {candidate["target_id"] for candidate in candidates}
    errors = []
    if set(judgments_by_target) != expected_ids:
        errors.append("judgment_target_set_mismatch")
    for target_id in sorted(expected_ids):
        if not (judgments_by_target.get(target_id) or {}).get("parse_success"):
            errors.append(f"invalid_target_judgment:{target_id}")
    if errors:
        return {
            "parse_success": False,
            "execution_parse_success": False,
            "trace_wellformed": False,
            "errors": errors,
            "warnings": [],
            "frames": [],
            "derived_state": "no_current_action",
        }
    frames = [
        frame_from_commitment(
            user_input, candidate, judgments_by_target[candidate["target_id"]]
        )
        for candidate in candidates
    ]
    return {
        "parse_success": True,
        "execution_parse_success": True,
        "trace_wellformed": True,
        "errors": [],
        "warnings": [],
        "frames": frames,
        "derived_state": derive_utterance_state(frames),
    }
