#!/usr/bin/env python3
"""Frame-local isolation and expanded colloquial grounding for V39."""

import json
import re
from pathlib import Path

from action_ontology_grounding_v38 import compile_anchor_grounded
from action_selective_deliberation_v37 import (
    COMMITMENTS,
    DOMAINS,
    DOMAIN_VALUES,
    derive_utterance_state,
)


ROOT = Path(__file__).resolve().parent
V38_CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"
V39_CONFIG_PATH = ROOT / "configs" / "grounded_frame_isolation_v39_preregistration.json"


def load_v39_anchor_ontology(v38_path=V38_CONFIG_PATH, v39_path=V39_CONFIG_PATH):
    base = json.loads(Path(v38_path).read_text(encoding="utf-8"))["action_anchor_ontology"]
    additions = json.loads(Path(v39_path).read_text(encoding="utf-8"))["ontology_additions"]
    merged = {key: list(patterns) for key, patterns in base.items()}
    for key, patterns in additions.items():
        merged.setdefault(key, []).extend(patterns)
    ontology = {}
    for key, patterns in merged.items():
        domain, value = key.split(".", 1)
        ontology[(domain, value)] = [re.compile(pattern) for pattern in patterns]
    return ontology


def parse_frames_with_isolation(user_input, raw_reply):
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
    if set(payload) != {"frames"}:
        fatal_errors.append("root_fields_mismatch")
    raw_frames = payload.get("frames")
    if not isinstance(raw_frames, list):
        raw_frames = []
        fatal_errors.append("frames_not_array")
    if len(raw_frames) > 8:
        fatal_errors.append("too_many_frames")

    frames = []
    seen_targets = set()
    if not fatal_errors:
        for index, raw_frame in enumerate(raw_frames):
            reasons = []
            if not isinstance(raw_frame, dict):
                reasons.append("frame_not_object")
            elif set(raw_frame) != {"domain", "value", "commitment", "evidence"}:
                reasons.append("frame_fields_mismatch")
            if reasons:
                warnings.append({"index": index, "reasons": reasons, "raw_frame": raw_frame})
                continue

            domain = raw_frame.get("domain")
            value = raw_frame.get("value")
            commitment = raw_frame.get("commitment")
            evidence = raw_frame.get("evidence")
            if domain not in DOMAINS:
                reasons.append("invalid_domain")
            elif value not in DOMAIN_VALUES[domain]:
                reasons.append("invalid_domain_value")
            if commitment not in COMMITMENTS:
                reasons.append("invalid_commitment")
            if not isinstance(evidence, str):
                reasons.append("evidence_not_string")
                evidence = ""
            else:
                evidence = evidence.strip()
                if not evidence or evidence not in text:
                    reasons.append("evidence_not_exact_input_substring")
            if reasons:
                warnings.append({"index": index, "reasons": reasons, "raw_frame": raw_frame})
                continue

            target = (domain, value)
            if target in seen_targets:
                warnings.append(
                    {
                        "index": index,
                        "reasons": ["duplicate_frame_target"],
                        "raw_frame": raw_frame,
                    }
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

    return {
        "parse_success": not fatal_errors,
        "execution_parse_success": not fatal_errors,
        "trace_wellformed": not fatal_errors and not warnings,
        "errors": fatal_errors,
        "warnings": warnings,
        "frames": frames,
        "derived_state": derive_utterance_state(frames),
    }


def compile_v39(user_input, parsed, ontology=None):
    return compile_anchor_grounded(
        user_input,
        parsed,
        ontology=ontology or load_v39_anchor_ontology(),
    )
