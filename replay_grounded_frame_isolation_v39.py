#!/usr/bin/env python3
"""Replay V39 ablations over frozen V37 primary outputs."""

import argparse
import hashlib
import json
from pathlib import Path

from action_ontology_grounding_v38 import (
    compile_anchor_grounded,
    load_anchor_ontology,
    parse_action_frames_with_local_warnings,
)
from action_selective_deliberation_v37 import score_action_calls, score_observable_frames
from grounded_frame_isolation_v39 import (
    compile_v39,
    load_v39_anchor_ontology,
    parse_frames_with_isolation,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "grounded_frame_isolation_v39_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
RAW_PATH = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
COMPILER_PATH = ROOT / "grounded_frame_isolation_v39.py"
DEFAULT_OUTPUT = ROOT / "reports" / "grounded_frame_isolation_v39_development_replay.json"

CONDITIONS = (
    "full_v38_control",
    "colloquial_anchor_only",
    "frame_isolation_only",
    "full_v39_candidate",
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _condition_result(case, condition, primary, v38_ontology, v39_ontology):
    parsed_v38 = parse_action_frames_with_local_warnings(case["user_input"], primary["raw_reply"])
    parsed_v39 = parse_frames_with_isolation(case["user_input"], primary["raw_reply"])
    if condition == "full_v38_control":
        parsed = parsed_v38
        compilation = compile_anchor_grounded(case["user_input"], parsed, v38_ontology)
        execution_parse_success = parsed["parse_success"]
        trace_wellformed = parsed["parse_success"] and not parsed.get("warnings")
    elif condition == "colloquial_anchor_only":
        parsed = parsed_v38
        compilation = compile_anchor_grounded(case["user_input"], parsed, v39_ontology)
        execution_parse_success = parsed["parse_success"]
        trace_wellformed = parsed["parse_success"] and not parsed.get("warnings")
    elif condition == "frame_isolation_only":
        parsed = parsed_v39
        compilation = compile_anchor_grounded(case["user_input"], parsed, v38_ontology)
        execution_parse_success = parsed["execution_parse_success"]
        trace_wellformed = parsed["trace_wellformed"]
    elif condition == "full_v39_candidate":
        parsed = parsed_v39
        compilation = compile_v39(case["user_input"], parsed, v39_ontology)
        execution_parse_success = parsed["execution_parse_success"]
        trace_wellformed = parsed["trace_wellformed"]
    else:
        raise ValueError(f"Unknown V39 condition: {condition}")

    calls = compilation["accepted_calls"]
    accepted_frames = compilation.get("accepted_frames") or []
    return {
        "execution_parse_success": bool(execution_parse_success),
        "trace_wellformed": bool(trace_wellformed),
        "parse_errors": parsed.get("errors") or [],
        "parse_warnings": parsed.get("warnings") or [],
        "compilation": compilation,
        "action_score": score_action_calls(case, calls),
        "frame_score": score_observable_frames(
            case,
            parsed.get("frames") or [],
            parse_success=bool(execution_parse_success),
        ),
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
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    scope = config["causal_scope"]
    if _sha256(RAW_PATH) != scope["development_raw_sha256"]:
        raise ValueError("V39 frozen raw source mismatch")
    if _sha256(DATASET_PATH) != scope["development_dataset_sha256"]:
        raise ValueError("V39 frozen dataset mismatch")
    raw_by_id = {row["case_id"]: row for row in raw["rows"]}
    v38_ontology = load_anchor_ontology()
    v39_ontology = load_v39_anchor_ontology()
    rows = []
    for case in dataset["cases"]:
        primary = raw_by_id[case["id"]]["judgments"][0]
        rows.append(
            {
                "case_id": case["id"],
                "family": case["family"],
                "user_input": case["user_input"],
                "conditions": {
                    condition: _condition_result(
                        case, condition, primary, v38_ontology, v39_ontology
                    )
                    for condition in CONDITIONS
                },
            }
        )
    report = {
        "schema": "uruha_grounded_frame_isolation_development_replay_v39",
        "evidence_status": "post_failure_development_replay_on_frozen_v37_primary_outputs",
        "model_inference_performed": False,
        "source_raw_sha256": _sha256(RAW_PATH),
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
