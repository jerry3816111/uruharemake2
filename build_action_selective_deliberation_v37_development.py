#!/usr/bin/env python3
"""Convert the retired V36 action set into the frozen V37 representation."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "action_intent_frame_v36_development.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
FREEZE_PATH = ROOT / "configs" / "action_selective_deliberation_v37_dataset_freeze.json"

UNSUPPORTED_DOMAINS = {
    "v34c_action_invalid_crouch": "motion",
    "v34c_action_invalid_arms": "motion",
    "v34c_action_invalid_screen": "other",
    "v34c_action_invalid_mail": "other",
    "v34c_action_invalid_camera": "other",
    "v34c_action_invalid_kick": "motion",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _risk_sources(case):
    family = case["family"]
    sources = []
    if family == "negated_action":
        sources.append("negation_or_correction")
    if family == "ambiguous_or_conflicting_action":
        sources.append("ambiguity_condition_or_cancellation")
    if family == "invalid_or_safety_blocked_action":
        sources.append("unsupported_request")
    if case["id"] in {
        "v34c_action_none_hypothetical",
        "v34c_action_none_explicit_none",
    }:
        sources.append("non_action_conflict_marker")
    return sources


def _convert_frame(case_id, frame):
    if frame["frame"] == "unsupported":
        return {
            "domain": UNSUPPORTED_DOMAINS[case_id],
            "value": "unsupported",
            "commitment": "requested",
            "evidence_options": frame["evidence_options"],
        }
    return {
        "domain": frame["frame"],
        "value": frame["value"],
        "commitment": frame["commitment"],
        "evidence_options": frame["evidence_options"],
    }


def _derived_state(frames):
    supported_requested = any(
        frame["commitment"] == "requested" and frame["value"] != "unsupported"
        for frame in frames
    )
    if supported_requested:
        return "explicit_current_request"
    if any(
        frame["commitment"] == "requested" and frame["value"] == "unsupported"
        for frame in frames
    ):
        return "unsupported_or_unsafe"
    if any(frame["commitment"] in {"cancelled", "ambiguous"} for frame in frames):
        return "ambiguous_or_cancelled"
    return "no_current_action"


def build():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    cases = []
    for case in source["cases"]:
        frames = [_convert_frame(case["id"], frame) for frame in case["expected_frames"]]
        risk_sources = _risk_sources(case)
        cases.append(
            {
                "id": case["id"],
                "family": case["family"],
                "user_input": case["user_input"],
                "expected_frames": frames,
                "expected_derived_state": _derived_state(frames),
                "expected_calls": case["expected_calls"],
                "expected_deliberation": bool(risk_sources),
                "expected_risk_sources": risk_sources,
            }
        )

    dataset = {
        "schema": "uruha_action_selective_deliberation_development_v37",
        "evidence_status": "retired_development_only_converted_from_v36",
        "source_dataset": str(SOURCE_PATH.relative_to(ROOT)),
        "source_dataset_sha256": _sha256(SOURCE_PATH),
        "case_count": len(cases),
        "cases": cases,
    }
    DATASET_PATH.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    freeze = {
        "schema": "uruha_action_selective_deliberation_dataset_freeze_v37",
        "evidence_status": dataset["evidence_status"],
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(DATASET_PATH),
        "source_dataset_sha256": _sha256(SOURCE_PATH),
        "builder_sha256": _sha256(Path(__file__)),
        "case_count": len(cases),
        "family_counts": dict(sorted(Counter(case["family"] for case in cases).items())),
        "expected_deliberation_count": sum(case["expected_deliberation"] for case in cases),
        "inference_performed_before_freeze": False,
    }
    FREEZE_PATH.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dataset, freeze


if __name__ == "__main__":
    built_dataset, built_freeze = build()
    print(
        json.dumps(
            {
                "case_count": built_dataset["case_count"],
                "expected_deliberation_count": built_freeze["expected_deliberation_count"],
                "dataset_sha256": built_freeze["dataset_sha256"],
            },
            indent=2,
        )
    )
