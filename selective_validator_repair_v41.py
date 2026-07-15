#!/usr/bin/env python3
"""Selectively accept validator-guided repairs without changing grounded calls."""

import json


def _call_keys(calls):
    return sorted(
        json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for call in calls or []
    )


def evaluate_repair_acceptance(original_compilation, repair_parsed, repair_compilation):
    reasons = []
    if not repair_parsed.get("trace_wellformed"):
        reasons.append("repair_trace_not_wellformed")
    if repair_compilation.get("fail_closed"):
        reasons.append("repair_compilation_failed_closed")
    if _call_keys(repair_compilation.get("accepted_calls")) != _call_keys(
        original_compilation.get("accepted_calls")
    ):
        reasons.append("grounded_calls_changed")
    accepted_frames = repair_compilation.get("accepted_frames") or []
    if any(not frame.get("matched_anchor") for frame in accepted_frames):
        reasons.append("accepted_frame_not_anchor_grounded")
    if repair_compilation.get("ungrounded_execution_count"):
        reasons.append("ungrounded_execution_present")
    return {
        "accepted": not reasons,
        "reasons": reasons,
        "grounded_calls_preserved": "grounded_calls_changed" not in reasons,
    }


def select_trace(original_parsed, original_compilation, repair_parsed, repair_compilation):
    policy = evaluate_repair_acceptance(
        original_compilation, repair_parsed, repair_compilation
    )
    if policy["accepted"]:
        return {
            "source": "accepted_repair",
            "parsed": repair_parsed,
            "compilation": repair_compilation,
            "repair_policy": policy,
        }
    return {
        "source": "original_v39_fallback",
        "parsed": original_parsed,
        "compilation": original_compilation,
        "repair_policy": policy,
    }
