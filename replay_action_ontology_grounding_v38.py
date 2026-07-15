#!/usr/bin/env python3
"""Replay frozen V37 primary replies through V38 matched compiler ablations."""

import argparse
import hashlib
import json
from pathlib import Path

from action_ontology_grounding_v38 import (
    compile_anchor_grounded,
    load_anchor_ontology,
    parse_action_frames_with_local_warnings,
)
from action_selective_deliberation_v37 import (
    compile_judgment,
    score_action_calls,
    score_observable_frames,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
RAW_V37_PATH = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
COMPILER_PATH = ROOT / "action_ontology_grounding_v38.py"
DEFAULT_OUTPUT = ROOT / "reports" / "action_ontology_grounding_v38_development_replay.json"

CONDITIONS = (
    "v37_single_control",
    "anchor_grounding_only",
    "local_isolation_only",
    "full_v38_candidate",
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _condition_result(case, condition, raw_row, ontology):
    primary = raw_row["judgments"][0]
    parsed_v37 = primary["parsed"]
    parsed_v38 = parse_action_frames_with_local_warnings(case["user_input"], primary["raw_reply"])

    if condition == "v37_single_control":
        parsed = parsed_v37
        compilation = primary["compilation"]
    elif condition == "anchor_grounding_only":
        parsed = parsed_v37
        compilation = compile_anchor_grounded(case["user_input"], parsed, ontology)
    elif condition == "local_isolation_only":
        parsed = parsed_v38
        compilation = compile_judgment(case["user_input"], parsed)
    elif condition == "full_v38_candidate":
        parsed = parsed_v38
        compilation = compile_anchor_grounded(case["user_input"], parsed, ontology)
    else:
        raise ValueError(f"Unknown condition: {condition}")

    calls = compilation["accepted_calls"]
    action_score = score_action_calls(case, calls)
    frame_score = score_observable_frames(
        case,
        parsed.get("frames") or [],
        parse_success=parsed.get("parse_success", False),
    )
    accepted_frames = compilation.get("accepted_frames") or []
    return {
        "parse_success": bool(parsed.get("parse_success")),
        "parse_errors": parsed.get("errors") or [],
        "parse_warnings": parsed.get("warnings") or [],
        "compilation": compilation,
        "action_score": action_score,
        "frame_score": frame_score,
        "accepted_call_anchor_count": sum(
            bool(frame.get("matched_anchor")) for frame in accepted_frames
        ),
        "accepted_call_count": len(calls),
        "ungrounded_execution_count": compilation.get("ungrounded_execution_count", 0),
        "unsupported_execution": bool(
            case["expected_derived_state"] == "unsupported_or_unsafe" and calls
        ),
        "model_passes_used": 1,
        "wall_seconds": primary["response_metrics"]["wall_seconds"],
    }


def replay(output=DEFAULT_OUTPUT):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw = json.loads(RAW_V37_PATH.read_text(encoding="utf-8"))
    scope = config["causal_scope"]
    if _sha256(RAW_V37_PATH) != scope["frozen_primary_output_sha256"]:
        raise ValueError("V38 frozen V37 raw report hash mismatch")
    if _sha256(DATASET_PATH) != scope["fixed_development_input_sha256"]:
        raise ValueError("V38 frozen development dataset hash mismatch")
    raw_by_id = {row["case_id"]: row for row in raw["rows"]}
    if set(raw_by_id) != {case["id"] for case in dataset["cases"]}:
        raise ValueError("V38 replay case IDs do not match frozen development set")
    ontology = load_anchor_ontology(CONFIG_PATH)

    rows = []
    for case in dataset["cases"]:
        raw_row = raw_by_id[case["id"]]
        rows.append(
            {
                "case_id": case["id"],
                "family": case["family"],
                "user_input": case["user_input"],
                "conditions": {
                    condition: _condition_result(case, condition, raw_row, ontology)
                    for condition in CONDITIONS
                },
            }
        )
    report = {
        "schema": "uruha_action_ontology_grounding_development_replay_v38",
        "evidence_status": "post_failure_development_replay_on_frozen_v37_primary_outputs",
        "model_inference_performed": False,
        "source_raw_sha256": _sha256(RAW_V37_PATH),
        "source_dataset_sha256": _sha256(DATASET_PATH),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "compiler_sha256": _sha256(COMPILER_PATH),
        "replay_script_sha256": _sha256(Path(__file__)),
        "conditions": list(CONDITIONS),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = replay(args.output)
    print(json.dumps({"rows": len(report["rows"]), "model_inference_performed": False}, indent=2))


if __name__ == "__main__":
    main()
