#!/usr/bin/env python3
"""Ground supported action targets, then assemble narrow commitment judgments."""

import json

from action_ontology_grounding_v38 import find_action_anchors
from action_selective_deliberation_v37 import COMMITMENTS, derive_utterance_state


def ground_supported_targets(user_input, ontology):
    candidates = []
    for domain, value in sorted(ontology):
        anchors = find_action_anchors(user_input, domain, value, ontology)
        if not anchors:
            continue
        candidates.append(
            {
                "target_id": f"{domain}.{value}",
                "domain": domain,
                "value": value,
                "anchors": anchors,
            }
        )
    return candidates


def parse_commitment_judgment(raw_reply, anchor_count):
    errors = []
    try:
        payload = json.loads(str(raw_reply or ""))
    except (TypeError, json.JSONDecodeError):
        payload = {}
        errors.append("invalid_json")
    if not isinstance(payload, dict):
        payload = {}
        errors.append("root_not_object")
    if set(payload) != {"commitment", "evidence_index"}:
        errors.append("root_fields_mismatch")
    commitment = payload.get("commitment")
    evidence_index = payload.get("evidence_index")
    if commitment not in COMMITMENTS:
        errors.append("invalid_commitment")
    if isinstance(evidence_index, bool) or not isinstance(evidence_index, int):
        errors.append("evidence_index_not_integer")
    elif not 0 <= evidence_index < anchor_count:
        errors.append("evidence_index_out_of_range")
    return {
        "parse_success": not errors,
        "errors": list(dict.fromkeys(errors)),
        "commitment": commitment,
        "evidence_index": evidence_index,
    }


def frame_from_judgment(candidate, judgment):
    if not judgment.get("parse_success"):
        raise ValueError("Cannot build a frame from an invalid judgment")
    anchor = candidate["anchors"][judgment["evidence_index"]]
    return {
        "domain": candidate["domain"],
        "value": candidate["value"],
        "commitment": judgment["commitment"],
        "evidence": anchor["text"],
        "evidence_valid": True,
        "candidate_anchor": anchor,
    }


def assemble_supported_case(candidates, judgments_by_target):
    expected_ids = {candidate["target_id"] for candidate in candidates}
    errors = []
    if set(judgments_by_target) != expected_ids:
        errors.append("judgment_target_set_mismatch")
    for target_id in sorted(expected_ids):
        judgment = judgments_by_target.get(target_id) or {}
        if not judgment.get("parse_success"):
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
        frame_from_judgment(candidate, judgments_by_target[candidate["target_id"]])
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
