#!/usr/bin/env python3
"""Parse observable action-intent frames and compile only explicit requests."""

import json


UTTERANCE_STATES = {
    "explicit_current_request",
    "no_current_action",
    "ambiguous_or_cancelled",
    "unsupported_or_unsafe",
}
COMMITMENTS = {
    "requested",
    "mentioned",
    "hypothetical",
    "negated",
    "cancelled",
    "ambiguous",
    "unsupported",
}
FRAME_VALUES = {
    "expression": {"neutral", "happy", "sad", "angry", "surprised"},
    "motion": {"idle", "wave", "nod", "shake_head", "point"},
    "gaze": {"left", "right", "user", "down"},
    "unsupported": {"unsupported"},
}
FRAME_TO_CALL = {
    ("expression", value): {
        "name": "set_expression",
        "arguments": {"expression": value},
    }
    for value in FRAME_VALUES["expression"]
}
FRAME_TO_CALL.update(
    {
        ("motion", value): {
            "name": "play_motion",
            "arguments": {"motion": value},
        }
        for value in FRAME_VALUES["motion"]
    }
)
FRAME_TO_CALL.update(
    {
        ("gaze", value): {
            "name": "set_gaze",
            "arguments": {"target": value},
        }
        for value in FRAME_VALUES["gaze"]
    }
)


def _frame_key(frame):
    return (frame["frame"], frame["value"], frame["commitment"])


def parse_action_intent_frame(user_input, raw_reply):
    text = str(user_input or "")
    errors = []
    try:
        payload = json.loads(str(raw_reply or ""))
    except (TypeError, json.JSONDecodeError):
        payload = {}
        errors.append("invalid_json")

    if not isinstance(payload, dict):
        payload = {}
        errors.append("root_not_object")
    if set(payload) != {"utterance_state", "frames"}:
        errors.append("root_fields_mismatch")

    state = payload.get("utterance_state")
    if state not in UTTERANCE_STATES:
        errors.append("invalid_utterance_state")

    raw_frames = payload.get("frames")
    if not isinstance(raw_frames, list):
        raw_frames = []
        errors.append("frames_not_array")
    if len(raw_frames) > 8:
        errors.append("too_many_frames")

    frames = []
    seen_targets = set()
    for raw_frame in raw_frames:
        if not isinstance(raw_frame, dict):
            errors.append("frame_not_object")
            continue
        if set(raw_frame) != {"frame", "value", "commitment", "evidence"}:
            errors.append("frame_fields_mismatch")
            continue
        frame_name = raw_frame.get("frame")
        value = raw_frame.get("value")
        commitment = raw_frame.get("commitment")
        evidence = raw_frame.get("evidence")
        if frame_name not in FRAME_VALUES:
            errors.append("invalid_frame_name")
            continue
        if value not in FRAME_VALUES[frame_name]:
            errors.append("invalid_frame_value")
            continue
        if commitment not in COMMITMENTS:
            errors.append("invalid_commitment")
            continue
        if frame_name == "unsupported" and commitment != "unsupported":
            errors.append("unsupported_frame_commitment_mismatch")
        if frame_name != "unsupported" and commitment == "unsupported":
            errors.append("supported_frame_commitment_mismatch")
        if not isinstance(evidence, str):
            errors.append("evidence_not_string")
            continue
        evidence = evidence.strip()
        evidence_valid = bool(evidence and evidence in text)
        if not evidence_valid:
            errors.append("evidence_not_exact_input_substring")
        target = (frame_name, value)
        if target in seen_targets:
            errors.append("duplicate_or_conflicting_frame_target")
        seen_targets.add(target)
        frames.append(
            {
                "frame": frame_name,
                "value": value,
                "commitment": commitment,
                "evidence": evidence,
                "evidence_valid": evidence_valid,
            }
        )

    requested = [frame for frame in frames if frame["commitment"] == "requested"]
    unsupported = [frame for frame in frames if frame["frame"] == "unsupported"]
    if state == "explicit_current_request" and not requested:
        errors.append("explicit_state_without_requested_frame")
    if state != "explicit_current_request" and requested:
        errors.append("requested_frame_under_nonexplicit_state")
    if state == "unsupported_or_unsafe" and not unsupported:
        errors.append("unsupported_state_without_unsupported_frame")

    return {
        "parse_success": not errors,
        "errors": errors,
        "utterance_state": state,
        "frames": frames,
    }


def compile_action_intent_frame(parsed):
    parsed = parsed or {}
    frames = parsed.get("frames") or []
    accepted_calls = []
    accepted_frames = []
    blocked_frames = []

    if not parsed.get("parse_success"):
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "blocked_frames": [
                {"frame": frame, "reasons": ["frame_parse_failed"]}
                for frame in frames
            ],
            "fail_closed": True,
        }

    state = parsed.get("utterance_state")
    seen_calls = set()
    for frame in frames:
        reasons = []
        mapping = FRAME_TO_CALL.get((frame["frame"], frame["value"]))
        if state != "explicit_current_request":
            reasons.append("utterance_not_explicit_current_request")
        if frame["commitment"] != "requested":
            reasons.append("frame_not_requested")
        if not frame.get("evidence_valid"):
            reasons.append("frame_lacks_exact_evidence")
        if mapping is None:
            reasons.append("frame_not_allowlisted")
        call_key = (
            json.dumps(mapping, ensure_ascii=False, sort_keys=True)
            if mapping is not None
            else None
        )
        if call_key in seen_calls:
            reasons.append("duplicate_compiled_call")
        if reasons:
            blocked_frames.append({"frame": frame, "reasons": reasons})
            continue
        seen_calls.add(call_key)
        accepted_frames.append(frame)
        accepted_calls.append(mapping)

    return {
        "accepted_calls": accepted_calls,
        "accepted_frames": accepted_frames,
        "blocked_frames": blocked_frames,
        "fail_closed": False,
    }


def score_frame_trace(case, parsed, compilation):
    gold_frames = case["expected_frames"]
    predicted_frames = parsed.get("frames") if parsed.get("parse_success") else []
    predicted_frames = predicted_frames or []
    gold_keys = {_frame_key(frame) for frame in gold_frames}
    predicted_keys = {_frame_key(frame) for frame in predicted_frames}
    gold_requested = {
        _frame_key(frame) for frame in gold_frames if frame["commitment"] == "requested"
    }
    predicted_requested = {
        _frame_key(frame)
        for frame in predicted_frames
        if frame["commitment"] == "requested"
    }
    gold_by_key = {_frame_key(frame): frame for frame in gold_frames}
    evidence_supported = 0
    matched = gold_keys & predicted_keys
    for frame in predicted_frames:
        key = _frame_key(frame)
        if key not in matched:
            continue
        options = gold_by_key[key]["evidence_options"]
        evidence = frame["evidence"]
        if any(evidence in option or option in evidence for option in options):
            evidence_supported += 1

    accepted_frames = compilation.get("accepted_frames") or []
    return {
        "state_correct": parsed.get("parse_success")
        and parsed.get("utterance_state") == case["expected_state"],
        "joint_frame_exact": parsed.get("parse_success")
        and parsed.get("utterance_state") == case["expected_state"]
        and predicted_keys == gold_keys,
        "frame_true_positive": len(gold_keys & predicted_keys),
        "frame_false_positive": len(predicted_keys - gold_keys),
        "frame_false_negative": len(gold_keys - predicted_keys),
        "requested_true_positive": len(gold_requested & predicted_requested),
        "requested_false_positive": len(predicted_requested - gold_requested),
        "requested_false_negative": len(gold_requested - predicted_requested),
        "matched_frame_evidence_supported": evidence_supported,
        "matched_frame_count": len(matched),
        "compiled_frame_count": len(accepted_frames),
        "compiled_evidence_valid_count": sum(
            frame.get("evidence_valid") for frame in accepted_frames
        ),
    }
