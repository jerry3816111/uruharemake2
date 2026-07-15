#!/usr/bin/env python3
"""Conflict-sensitive action framing and deterministic consensus for V37."""

import json
import re
from collections import Counter, defaultdict


DOMAINS = {"expression", "motion", "gaze", "other"}
COMMITMENTS = {
    "requested",
    "mentioned",
    "hypothetical",
    "negated",
    "cancelled",
    "ambiguous",
}
SUPPORTED_VALUES = {
    "expression": {"neutral", "happy", "sad", "angry", "surprised"},
    "motion": {"idle", "wave", "nod", "shake_head", "point"},
    "gaze": {"left", "right", "user", "down"},
    "other": set(),
}
DOMAIN_VALUES = {
    domain: values | {"unsupported"} for domain, values in SUPPORTED_VALUES.items()
}

INPUT_CONFLICT_PATTERN = r"(?:ないで|なくて|ない|なかった|ず|ぬ|じゃなく|ではなく|なしで|やめて|止めて|停止|中止|取り消|取消|キャンセル|もし|なら|たら|かは|かどうか|迷って|保留|後で決め|決めなくて)"
CLAUSE_SEPARATOR_PATTERN = r"[、。！？!?；;]"
STRONG_NEGATION_PATTERN = r"(?:ないで|なくて|ない|なかった|ず|ぬ|じゃなく|ではなく|なしで|やめて|止めて|停止|中止)"
REFERENTIAL_CANCELLATION_PATTERN = r"(?:今の|さっきの|先ほどの|その)(?:頼み|お願い|指示)?.*(?:取り消|取消|キャンセル)"

INPUT_CONFLICT_RE = re.compile(INPUT_CONFLICT_PATTERN)
CLAUSE_SEPARATOR_RE = re.compile(CLAUSE_SEPARATOR_PATTERN)
STRONG_NEGATION_RE = re.compile(STRONG_NEGATION_PATTERN)
REFERENTIAL_CANCELLATION_RE = re.compile(REFERENTIAL_CANCELLATION_PATTERN)

FRAME_TO_CALL = {
    ("expression", value): {
        "name": "set_expression",
        "arguments": {"expression": value},
    }
    for value in SUPPORTED_VALUES["expression"]
}
FRAME_TO_CALL.update(
    {
        ("motion", value): {
            "name": "play_motion",
            "arguments": {"motion": value},
        }
        for value in SUPPORTED_VALUES["motion"]
    }
)
FRAME_TO_CALL.update(
    {
        ("gaze", value): {
            "name": "set_gaze",
            "arguments": {"target": value},
        }
        for value in SUPPORTED_VALUES["gaze"]
    }
)


def _call_key(call):
    return json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _frame_key(frame):
    return (frame["domain"], frame["value"], frame["commitment"])


def derive_utterance_state(frames):
    if any(
        frame["commitment"] == "requested" and frame["value"] != "unsupported"
        for frame in frames
    ):
        return "explicit_current_request"
    if any(
        frame["commitment"] == "requested" and frame["value"] == "unsupported"
        for frame in frames
    ):
        return "unsupported_or_unsafe"
    if any(frame["commitment"] in {"cancelled", "ambiguous"} for frame in frames):
        return "ambiguous_or_cancelled"
    return "no_current_action"


def parse_action_frames(user_input, raw_reply):
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
    if set(payload) != {"frames"}:
        errors.append("root_fields_mismatch")

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
        if set(raw_frame) != {"domain", "value", "commitment", "evidence"}:
            errors.append("frame_fields_mismatch")
            continue
        domain = raw_frame.get("domain")
        value = raw_frame.get("value")
        commitment = raw_frame.get("commitment")
        evidence = raw_frame.get("evidence")
        if domain not in DOMAINS:
            errors.append("invalid_domain")
            continue
        if value not in DOMAIN_VALUES[domain]:
            errors.append("invalid_domain_value")
            continue
        if commitment not in COMMITMENTS:
            errors.append("invalid_commitment")
            continue
        if not isinstance(evidence, str):
            errors.append("evidence_not_string")
            continue
        evidence = evidence.strip()
        evidence_valid = bool(evidence and evidence in text)
        if not evidence_valid:
            errors.append("evidence_not_exact_input_substring")
        target = (domain, value)
        if target in seen_targets:
            errors.append("duplicate_frame_target")
        seen_targets.add(target)
        frames.append(
            {
                "domain": domain,
                "value": value,
                "commitment": commitment,
                "evidence": evidence,
                "evidence_valid": evidence_valid,
            }
        )

    return {
        "parse_success": not errors,
        "errors": errors,
        "frames": frames,
        "derived_state": derive_utterance_state(frames),
    }


def _substring_spans(text, substring):
    spans = []
    start = 0
    while substring and (index := text.find(substring, start)) >= 0:
        spans.append((index, index + len(substring)))
        start = index + 1
    return spans


def _clause_spans(text):
    spans = []
    start = 0
    for match in CLAUSE_SEPARATOR_RE.finditer(text):
        if match.start() > start:
            spans.append((start, match.start(), text[start : match.start()]))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text), text[start:]))
    return spans


def _overlaps(left, right):
    return left[0] < right[1] and right[0] < left[1]


def scope_guard_reasons(user_input, frame):
    if frame.get("commitment") != "requested" or frame.get("value") == "unsupported":
        return []
    text = str(user_input or "")
    evidence_spans = _substring_spans(text, frame.get("evidence") or "")
    clauses = _clause_spans(text)
    risky_spans = [
        (start, end)
        for start, end, clause in clauses
        if STRONG_NEGATION_RE.search(clause)
    ]
    reasons = []
    if evidence_spans and all(
        any(_overlaps(evidence_span, risky_span) for risky_span in risky_spans)
        for evidence_span in evidence_spans
    ):
        reasons.append("evidence_inside_negated_clause")

    cancellation = REFERENTIAL_CANCELLATION_RE.search(text)
    if cancellation and evidence_spans and all(
        evidence_span[1] <= cancellation.start() for evidence_span in evidence_spans
    ):
        reasons.append("preceding_request_cancelled_later")
    return reasons


def compile_judgment(user_input, parsed):
    parsed = parsed or {}
    frames = parsed.get("frames") or []
    if not parsed.get("parse_success"):
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "blocked_frames": [
                {"frame": frame, "reasons": ["frame_parse_failed"]} for frame in frames
            ],
            "scope_guard_blocked": False,
            "conflicting_requested_domains": [],
            "fail_closed": True,
        }

    requested_by_domain = defaultdict(set)
    for frame in frames:
        if frame["commitment"] == "requested" and frame["value"] != "unsupported":
            requested_by_domain[frame["domain"]].add(frame["value"])
    conflicting_domains = sorted(
        domain for domain, values in requested_by_domain.items() if len(values) > 1
    )

    accepted_calls = []
    accepted_frames = []
    blocked_frames = []
    seen_calls = set()
    scope_guard_blocked = False
    for frame in frames:
        reasons = []
        mapping = FRAME_TO_CALL.get((frame["domain"], frame["value"]))
        if frame["commitment"] != "requested":
            reasons.append("frame_not_requested")
        if frame["value"] == "unsupported" or mapping is None:
            reasons.append("frame_not_allowlisted")
        if not frame.get("evidence_valid"):
            reasons.append("frame_lacks_exact_evidence")
        if frame["domain"] in conflicting_domains:
            reasons.append("multiple_requested_values_in_exclusive_domain")
        guard_reasons = scope_guard_reasons(user_input, frame)
        if guard_reasons:
            scope_guard_blocked = True
            reasons.extend(guard_reasons)
        call_key = _call_key(mapping) if mapping is not None else None
        if call_key in seen_calls:
            reasons.append("duplicate_compiled_call")
        if reasons:
            blocked_frames.append({"frame": frame, "reasons": reasons})
            continue
        seen_calls.add(call_key)
        accepted_calls.append(mapping)
        accepted_frames.append(frame)

    return {
        "accepted_calls": accepted_calls,
        "accepted_frames": accepted_frames,
        "blocked_frames": blocked_frames,
        "scope_guard_blocked": scope_guard_blocked,
        "conflicting_requested_domains": conflicting_domains,
        "fail_closed": False,
    }


def assess_deliberation_risk(user_input, parsed, compilation):
    reasons = []
    if INPUT_CONFLICT_RE.search(str(user_input or "")):
        reasons.append("input_conflict_marker")
    if not parsed.get("parse_success"):
        reasons.append("primary_parse_failure")
    frames = parsed.get("frames") or []
    if any(frame["value"] == "unsupported" for frame in frames):
        reasons.append("unsupported_value_present")
    if any(frame["commitment"] in {"cancelled", "ambiguous"} for frame in frames):
        reasons.append("cancelled_or_ambiguous_commitment_present")
    if compilation.get("scope_guard_blocked"):
        reasons.append("requested_frame_blocked_by_negation_or_cancellation_guard")
    if compilation.get("conflicting_requested_domains"):
        reasons.append("multiple_requested_values_in_one_exclusive_domain")
    return {"escalate": bool(reasons), "reasons": list(dict.fromkeys(reasons))}


def _consensus_frames(judgments, threshold=2):
    valid = [row for row in judgments if row["parsed"].get("parse_success")]
    counts = Counter(
        _frame_key(frame)
        for row in valid
        for frame in row["parsed"].get("frames") or []
    )
    frames = []
    for key, count in sorted(counts.items()):
        if count < threshold:
            continue
        for row in valid:
            match = next(
                (
                    frame
                    for frame in row["parsed"].get("frames") or []
                    if _frame_key(frame) == key
                ),
                None,
            )
            if match:
                frames.append(dict(match))
                break
    return frames


def compile_consensus(judgments, threshold=2):
    valid = [row for row in judgments if row["parsed"].get("parse_success")]
    if len(valid) < threshold:
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "observable_frames": [],
            "vote_counts": {},
            "valid_judgment_count": len(valid),
            "conflicting_consensus_domains": [],
            "fail_closed": True,
        }

    votes = Counter(
        _call_key(call)
        for row in valid
        for call in row["compilation"].get("accepted_calls") or []
    )
    passing = {
        key: count for key, count in votes.items() if count >= threshold
    }
    calls = [json.loads(key) for key in sorted(passing)]
    by_name = defaultdict(list)
    for call in calls:
        by_name[call["name"]].append(call)
    conflicts = sorted(name for name, rows in by_name.items() if len(rows) > 1)
    if conflicts:
        calls = [call for call in calls if call["name"] not in conflicts]

    accepted_frames = []
    accepted_keys = {_call_key(call) for call in calls}
    for row in valid:
        for frame in row["compilation"].get("accepted_frames") or []:
            mapping = FRAME_TO_CALL[(frame["domain"], frame["value"])]
            if _call_key(mapping) in accepted_keys and not any(
                _frame_key(existing) == _frame_key(frame) for existing in accepted_frames
            ):
                accepted_frames.append(dict(frame))

    return {
        "accepted_calls": calls,
        "accepted_frames": accepted_frames,
        "observable_frames": _consensus_frames(valid, threshold=threshold),
        "vote_counts": dict(sorted(votes.items())),
        "valid_judgment_count": len(valid),
        "conflicting_consensus_domains": conflicts,
        "fail_closed": False,
    }


def apply_policy(policy, user_input, judgments):
    if not judgments:
        raise ValueError("At least one judgment is required")
    primary = judgments[0]
    risk = assess_deliberation_risk(user_input, primary["parsed"], primary["compilation"])
    if policy == "single_pass_v37_control":
        compilation = dict(primary["compilation"])
        compilation["observable_frames"] = list(primary["parsed"].get("frames") or [])
        compilation["valid_judgment_count"] = int(primary["parsed"].get("parse_success"))
        return {
            "policy": policy,
            "escalated": False,
            "risk": risk,
            "passes_used": 1,
            "parse_success": bool(primary["parsed"].get("parse_success")),
            "compilation": compilation,
        }
    if policy == "selective_three_pass_v37_candidate":
        if not risk["escalate"]:
            compilation = dict(primary["compilation"])
            compilation["observable_frames"] = list(primary["parsed"].get("frames") or [])
            compilation["valid_judgment_count"] = int(primary["parsed"].get("parse_success"))
            return {
                "policy": policy,
                "escalated": False,
                "risk": risk,
                "passes_used": 1,
                "parse_success": bool(primary["parsed"].get("parse_success")),
                "compilation": compilation,
            }
        if len(judgments) < 3:
            raise ValueError("Selective escalation requires three judgments")
        compilation = compile_consensus(judgments[:3])
        return {
            "policy": policy,
            "escalated": True,
            "risk": risk,
            "passes_used": 3,
            "parse_success": compilation["valid_judgment_count"] >= 2,
            "compilation": compilation,
        }
    if policy == "always_three_pass_v37_cost_reference":
        if len(judgments) < 3:
            raise ValueError("Always-three policy requires three judgments")
        compilation = compile_consensus(judgments[:3])
        return {
            "policy": policy,
            "escalated": True,
            "risk": risk,
            "passes_used": 3,
            "parse_success": compilation["valid_judgment_count"] >= 2,
            "compilation": compilation,
        }
    raise ValueError(f"Unknown policy: {policy}")


def score_action_calls(case, calls):
    expected_keys = sorted(_call_key(call) for call in case["expected_calls"])
    actual_keys = sorted(_call_key(call) for call in calls)
    forbidden_keys = {_call_key(call) for call in case["forbidden_calls"]}
    expected_set = set(expected_keys)
    actual_set = set(actual_keys)
    valid_names = {"set_expression", "play_motion", "set_gaze"}
    invalid = [call for call in calls if call.get("name") not in valid_names]
    return {
        "actual_calls": calls,
        "exact_match": actual_keys == expected_keys,
        "expected_call_count": len(expected_keys),
        "actual_call_count": len(actual_keys),
        "required_action_true_positive": len(expected_set & actual_set),
        "required_action_false_negative": len(expected_set - actual_set),
        "extra_call_count": len(actual_set - expected_set),
        "false_action": bool(actual_set - expected_set),
        "forbidden_call_hits": sorted(actual_set & forbidden_keys),
        "negation_violation": bool(actual_set & forbidden_keys),
        "invalid_tool_or_argument": bool(invalid),
        "no_action_correct": bool(case["expected_no_action"] and not actual_keys),
    }


def score_observable_frames(case, frames, parse_success=True):
    predicted = frames if parse_success else []
    gold_keys = {_frame_key(frame) for frame in case["expected_frames"]}
    predicted_keys = {_frame_key(frame) for frame in predicted}
    gold_by_key = {_frame_key(frame): frame for frame in case["expected_frames"]}
    matched = gold_keys & predicted_keys
    evidence_supported = 0
    for frame in predicted:
        key = _frame_key(frame)
        if key not in matched:
            continue
        evidence = frame.get("evidence") or ""
        if any(
            evidence in option or option in evidence
            for option in gold_by_key[key]["evidence_options"]
        ):
            evidence_supported += 1
    return {
        "derived_state_correct": parse_success
        and derive_utterance_state(predicted) == case["expected_derived_state"],
        "joint_frame_exact": parse_success and predicted_keys == gold_keys,
        "frame_true_positive": len(gold_keys & predicted_keys),
        "frame_false_positive": len(predicted_keys - gold_keys),
        "frame_false_negative": len(gold_keys - predicted_keys),
        "matched_frame_evidence_supported": evidence_supported,
        "matched_frame_count": len(matched),
    }
