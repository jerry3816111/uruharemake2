#!/usr/bin/env python3
"""Narrow immediate-execution gate and observable V49 payload construction."""

import json

from discourse_state_perception_v45 import detect_focus_discourse_signals
from target_relative_scope_v48 import perceive_target_relative_scope


def parse_binary_gate_response(response):
    message = (response or {}).get("message") or {}
    raw_content = message.get("content")
    errors = []
    try:
        payload = json.loads(raw_content) if isinstance(raw_content, str) else {}
    except json.JSONDecodeError:
        payload = {}
        errors.append("invalid_json")
    if not isinstance(payload, dict):
        payload = {}
        errors.append("root_not_object")
    if set(payload) != {"execute_now", "contract_ack"}:
        errors.append("root_fields_mismatch")
    execute_now = payload.get("execute_now")
    if type(execute_now) is not bool:
        errors.append("execute_now_not_boolean")
    if payload.get("contract_ack") != "v49":
        errors.append("contract_ack_mismatch")
    return {
        "parse_success": not errors,
        "errors": list(dict.fromkeys(errors)),
        "execute_now": execute_now if type(execute_now) is bool else None,
    }


def _anchor_payload(anchor):
    return {
        "text": anchor["text"],
        "start": anchor["start"],
        "end": anchor["end"],
    }


def _blocked_anchor_payload(anchor):
    return {
        **_anchor_payload(anchor),
        "scope_reason_types": sorted(
            {reason["marker_type"] for reason in anchor["scope_reasons"]}
        ),
    }


def _context_target_payload(candidate):
    return {
        "target_id": candidate["target_id"],
        "domain": candidate["domain"],
        "value": candidate["value"],
        "anchors": [_anchor_payload(anchor) for anchor in candidate["anchors"]],
    }


def build_binary_gate_payload(
    user_input,
    candidate,
    candidates,
    discourse_patterns,
    expected_fields=None,
):
    scope = perceive_target_relative_scope(user_input, candidates)
    target_scope = next(
        row for row in scope["targets"] if row["target_id"] == candidate["target_id"]
    )
    payload = {
        "user_input": str(user_input or ""),
        "focus_target": {
            "target_id": candidate["target_id"],
            "domain": candidate["domain"],
            "value": candidate["value"],
        },
        "safe_anchor_evidence": [
            _anchor_payload(anchor)
            for anchor in target_scope["anchors"]
            if not anchor["blocked"]
        ],
        "blocked_anchor_evidence": [
            _blocked_anchor_payload(anchor)
            for anchor in target_scope["anchors"]
            if anchor["blocked"]
        ],
        "context_only_other_targets": [
            _context_target_payload(row)
            for row in candidates
            if row["target_id"] != candidate["target_id"]
        ],
        "focus_discourse_signals": detect_focus_discourse_signals(
            user_input, candidate, discourse_patterns
        ),
    }
    if expected_fields is not None and set(payload) != set(expected_fields):
        raise ValueError("V49 binary payload field mismatch")
    return payload


def binary_result_to_judgment(parsed):
    if not parsed.get("parse_success"):
        return {
            "parse_success": False,
            "errors": parsed.get("errors") or ["binary_gate_parse_failure"],
            "commitment": None,
        }
    return {
        "parse_success": True,
        "errors": [],
        "commitment": "requested" if parsed["execute_now"] else "mentioned",
    }
