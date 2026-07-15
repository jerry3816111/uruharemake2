#!/usr/bin/env python3
"""Semantic authorization boundary for already-proposed VRM calls."""

import json

from vrm_action_policy_v34 import ACTION_SPECS, _canonical_call, _spec_key


ALLOWED_STATES = {
    "explicit_current_request",
    "not_a_request",
    "ambiguous_or_cancelled",
    "unsupported_or_unsafe",
}
ALLOWED_REASON_CODES = {
    "exact_supported_request",
    "discussed_only",
    "hypothetical_or_future",
    "negated",
    "cancelled",
    "ambiguous",
    "unsupported_or_unsafe",
    "semantic_mismatch",
}
VALID_CALL_KEYS = {_spec_key(spec) for spec in ACTION_SPECS}


def canonicalize_proposed_calls(proposed_calls):
    return [_canonical_call(call) for call in proposed_calls or []]


def build_authorization_payload(user_input, proposed_calls):
    calls = canonicalize_proposed_calls(proposed_calls)
    return {
        "user_input": str(user_input or ""),
        "proposed_calls": [
            {
                "index": index,
                "name": call.get("name"),
                "arguments": call.get("arguments"),
            }
            for index, call in enumerate(calls)
        ],
    }


def parse_authorization_reply(user_input, proposed_calls, raw_reply):
    calls = canonicalize_proposed_calls(proposed_calls)
    errors = []
    try:
        payload = json.loads(str(raw_reply or ""))
    except (TypeError, json.JSONDecodeError):
        payload = {}
        errors.append("invalid_json")

    if not isinstance(payload, dict):
        payload = {}
        errors.append("root_not_object")
    state = payload.get("utterance_state")
    if state not in ALLOWED_STATES:
        errors.append("invalid_utterance_state")

    raw_verdicts = payload.get("verdicts")
    if not isinstance(raw_verdicts, list):
        raw_verdicts = []
        errors.append("verdicts_not_array")

    verdicts = {}
    text = str(user_input or "")
    for raw_verdict in raw_verdicts:
        if not isinstance(raw_verdict, dict):
            errors.append("verdict_not_object")
            continue
        index = raw_verdict.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(calls):
            errors.append("invalid_verdict_index")
            continue
        if index in verdicts:
            errors.append("duplicate_verdict_index")
            continue
        authorized = raw_verdict.get("authorized")
        if not isinstance(authorized, bool):
            errors.append("authorized_not_boolean")
            continue
        reason_code = raw_verdict.get("reason_code")
        if reason_code not in ALLOWED_REASON_CODES:
            errors.append("invalid_reason_code")
            continue
        evidence = raw_verdict.get("evidence")
        if not isinstance(evidence, str):
            errors.append("evidence_not_string")
            continue
        evidence = evidence.strip()
        evidence_valid = bool(evidence and evidence in text)
        verdicts[index] = {
            "index": index,
            "authorized": authorized,
            "reason_code": reason_code,
            "evidence": evidence,
            "evidence_valid": evidence_valid,
        }

    expected_indices = set(range(len(calls)))
    if set(verdicts) != expected_indices:
        errors.append("incomplete_verdict_coverage")

    return {
        "parse_success": not errors,
        "errors": errors,
        "utterance_state": state,
        "verdicts": [verdicts[index] for index in sorted(verdicts)],
    }


def apply_semantic_authorization(user_input, proposed_calls, parsed_authorization):
    calls = canonicalize_proposed_calls(proposed_calls)
    parsed = parsed_authorization or {}
    verdicts = {
        verdict["index"]: verdict
        for verdict in parsed.get("verdicts") or []
        if isinstance(verdict, dict) and isinstance(verdict.get("index"), int)
    }
    accepted = []
    blocked = []
    seen = set()

    for index, call in enumerate(calls):
        reasons = []
        verdict = verdicts.get(index)
        if not parsed.get("parse_success"):
            reasons.append("authorization_parse_failed")
        if call.get("key") not in VALID_CALL_KEYS or not call.get("valid"):
            reasons.append("invalid_or_non_allowlisted_call")
        if parsed.get("utterance_state") != "explicit_current_request":
            reasons.append("utterance_not_explicit_current_request")
        if not verdict or not verdict.get("authorized"):
            reasons.append("call_not_semantically_authorized")
        if verdict and verdict.get("authorized") and not verdict.get("evidence_valid"):
            reasons.append("authorized_call_lacks_exact_evidence")
        if call.get("key") in seen:
            reasons.append("duplicate_call")
        if reasons:
            blocked.append({"index": index, "call": call, "reasons": reasons})
            continue
        seen.add(call["key"])
        accepted.append({"name": call["name"], "arguments": call["arguments"]})

    return {
        "accepted_calls": accepted,
        "blocked_calls": blocked,
        "authorization": parsed,
    }
