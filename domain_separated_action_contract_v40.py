#!/usr/bin/env python3
"""Normalize V40 domain-separated model output for the unchanged V39 compiler."""

import json

from action_selective_deliberation_v37 import (
    COMMITMENTS,
    DOMAINS,
    SUPPORTED_VALUES,
    derive_utterance_state,
)
from grounded_frame_isolation_v39 import compile_v39, load_v39_anchor_ontology


ROOT_ARRAYS = {
    "expression_frames": "expression",
    "motion_frames": "motion",
    "gaze_frames": "gaze",
}
ALL_ROOT_FIELDS = set(ROOT_ARRAYS) | {"unsupported_frames"}
MAX_TOTAL_FRAMES = 8


def _warning(index, source, reasons, raw_frame):
    return {
        "index": index,
        "source": source,
        "reasons": reasons,
        "raw_frame": raw_frame,
    }


def parse_domain_separated_frames(user_input, raw_reply):
    text = str(user_input or "")
    fatal_errors = []
    warnings = []
    try:
        payload = json.loads(str(raw_reply or ""))
    except (TypeError, json.JSONDecodeError):
        payload = {}
        fatal_errors.append("invalid_json")

    if not isinstance(payload, dict):
        payload = {}
        fatal_errors.append("root_not_object")
    if set(payload) != ALL_ROOT_FIELDS:
        fatal_errors.append("root_fields_mismatch")

    arrays = {}
    for field in sorted(ALL_ROOT_FIELDS):
        value = payload.get(field)
        if not isinstance(value, list):
            value = []
            fatal_errors.append(f"{field}_not_array")
        arrays[field] = value
    if sum(len(rows) for rows in arrays.values()) > MAX_TOTAL_FRAMES:
        fatal_errors.append("too_many_frames")

    frames = []
    seen_targets = set()
    global_index = 0
    if not fatal_errors:
        for source, domain in ROOT_ARRAYS.items():
            for raw_frame in arrays[source]:
                reasons = []
                if not isinstance(raw_frame, dict):
                    reasons.append("frame_not_object")
                elif set(raw_frame) != {"value", "commitment", "evidence"}:
                    reasons.append("frame_fields_mismatch")
                if reasons:
                    warnings.append(
                        _warning(global_index, source, reasons, raw_frame)
                    )
                    global_index += 1
                    continue

                value = raw_frame.get("value")
                commitment = raw_frame.get("commitment")
                evidence = raw_frame.get("evidence")
                if value not in SUPPORTED_VALUES[domain]:
                    reasons.append("invalid_domain_value")
                if commitment not in COMMITMENTS:
                    reasons.append("invalid_commitment")
                if not isinstance(evidence, str):
                    evidence = ""
                    reasons.append("evidence_not_string")
                else:
                    evidence = evidence.strip()
                    if not evidence or evidence not in text:
                        reasons.append("evidence_not_exact_input_substring")
                if reasons:
                    warnings.append(
                        _warning(global_index, source, reasons, raw_frame)
                    )
                    global_index += 1
                    continue
                target = (domain, value)
                if target in seen_targets:
                    warnings.append(
                        _warning(
                            global_index,
                            source,
                            ["duplicate_frame_target"],
                            raw_frame,
                        )
                    )
                seen_targets.add(target)
                frames.append(
                    {
                        "domain": domain,
                        "value": value,
                        "commitment": commitment,
                        "evidence": evidence,
                        "evidence_valid": True,
                    }
                )
                global_index += 1

        for raw_frame in arrays["unsupported_frames"]:
            source = "unsupported_frames"
            reasons = []
            if not isinstance(raw_frame, dict):
                reasons.append("frame_not_object")
            elif set(raw_frame) != {"domain", "commitment", "evidence"}:
                reasons.append("frame_fields_mismatch")
            if reasons:
                warnings.append(_warning(global_index, source, reasons, raw_frame))
                global_index += 1
                continue

            domain = raw_frame.get("domain")
            commitment = raw_frame.get("commitment")
            evidence = raw_frame.get("evidence")
            if domain not in DOMAINS:
                reasons.append("invalid_domain")
            if commitment not in COMMITMENTS:
                reasons.append("invalid_commitment")
            if not isinstance(evidence, str):
                evidence = ""
                reasons.append("evidence_not_string")
            else:
                evidence = evidence.strip()
                if not evidence or evidence not in text:
                    reasons.append("evidence_not_exact_input_substring")
            if reasons:
                warnings.append(_warning(global_index, source, reasons, raw_frame))
                global_index += 1
                continue
            target = (domain, "unsupported")
            if target in seen_targets:
                warnings.append(
                    _warning(
                        global_index,
                        source,
                        ["duplicate_frame_target"],
                        raw_frame,
                    )
                )
            seen_targets.add(target)
            frames.append(
                {
                    "domain": domain,
                    "value": "unsupported",
                    "commitment": commitment,
                    "evidence": evidence,
                    "evidence_valid": True,
                }
            )
            global_index += 1

    return {
        "parse_success": not fatal_errors,
        "execution_parse_success": not fatal_errors,
        "trace_wellformed": not fatal_errors and not warnings,
        "errors": list(dict.fromkeys(fatal_errors)),
        "warnings": warnings,
        "frames": frames,
        "derived_state": derive_utterance_state(frames),
    }


def compile_v40(user_input, parsed, ontology=None):
    return compile_v39(
        user_input,
        parsed,
        ontology=ontology or load_v39_anchor_ontology(),
    )
