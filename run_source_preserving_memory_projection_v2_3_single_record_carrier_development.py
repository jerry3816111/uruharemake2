#!/usr/bin/env python3
"""Run the frozen V2.3 single-record evidence carrier experiment once."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from answer_bearing_memory_single_record import build_prompt, json_schema, parse, validate
from answer_bearing_memory_span import supported_candidates
from run_source_preserving_memory_projection_v2_1_development import (
    ROOT,
    condition_candidates,
    expected_trace_ids,
    file_sha256,
    git_value,
    installed_models,
    load_json,
    post_ollama,
    text_sha256,
)


CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_3_single_record_carrier_evaluation_contract.json"
DEFAULT_RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_3_single_record_carrier/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_3_single_record_carrier/run_metadata.json"


def load_frozen_configuration():
    contract = load_json(CONTRACT)
    prereg = load_json(ROOT / contract["artifacts"]["preregistration"]["path"])
    base = load_json(ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json")
    conditions = {
        row["id"]: row
        for row in base["matched_conditions"]
        if row["id"] in prereg["controlled_variables"]["conditions"]
    }
    return contract, prereg, conditions


def verify_frozen_inputs(contract, prereg, endpoint):
    for artifact in contract["artifacts"].values():
        if file_sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"frozen artifact hash mismatch: {artifact['path']}")
    controlled = prereg["controlled_variables"]
    if endpoint != controlled["endpoint"]:
        raise ValueError("Ollama endpoint drift")
    matched = next(
        (row for row in installed_models(endpoint) if row.get("name") == controlled["model"]),
        None,
    )
    if not matched:
        raise ValueError(f"missing local model: {controlled['model']}")
    if matched.get("digest") != controlled["model_digest"]:
        raise ValueError("local model digest mismatch")


def call_single_record_model(question, candidates, prereg, endpoint):
    if len(candidates) != 1:
        raise ValueError("single-record carrier requires exactly one candidate")
    controlled = prereg["controlled_variables"]
    prompt = build_prompt(question, candidates[0])
    body = {
        "model": controlled["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": bool(controlled["think"]),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "submit_single_answer_evidence",
                    "description": "Submit one grounded evidence verdict for the one visible memory record.",
                    "parameters": json_schema(),
                },
            }
        ],
        "options": {
            "temperature": controlled["temperature"],
            "seed": controlled["seed"],
            "num_ctx": controlled["num_ctx"],
            "num_predict": controlled["max_tokens"],
        },
    }
    started = time.perf_counter()
    response = post_ollama(endpoint, body)
    latency = time.perf_counter() - started
    message = response.get("message") or {}
    tool_calls = message.get("tool_calls") or []
    carrier_error = None
    arguments = None
    if len(tool_calls) != 1:
        carrier_error = "tool_call_count"
    else:
        function = tool_calls[0].get("function") or {}
        if function.get("name") != "submit_single_answer_evidence":
            carrier_error = "tool_name"
        elif not isinstance(function.get("arguments"), dict):
            carrier_error = "tool_arguments_type"
        else:
            arguments = function["arguments"]
    return {
        "content": json.dumps(arguments, ensure_ascii=False, sort_keys=True) if arguments else "",
        "carrier_valid": carrier_error is None,
        "carrier_error": carrier_error,
        "raw_content": str(message.get("content") or ""),
        "raw_tool_calls": tool_calls,
        "latency_seconds": latency,
        "prompt_sha256": text_sha256(prompt),
        "prompt_character_count": len(prompt),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "total_duration_ns": response.get("total_duration"),
    }


def run_one(case, condition, representation, prereg, endpoint, model_call):
    candidates = condition_candidates(case, condition, representation)
    expected = expected_trace_ids(case, condition)
    errors = []
    try:
        generation = model_call(case["question"], candidates, prereg, endpoint)
        validation = validate(parse(generation["content"]), candidates[0])
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        errors.append(f"{type(exc).__name__}:{exc}")
        generation = {
            "content": "",
            "carrier_valid": False,
            "carrier_error": "transport_error",
            "raw_content": "",
            "raw_tool_calls": [],
            "latency_seconds": 0.0,
            "prompt_sha256": None,
            "prompt_character_count": 0,
            "prompt_eval_count": None,
            "eval_count": None,
            "total_duration_ns": None,
        }
        validation = validate(None, candidates[0])
    supported = supported_candidates(validation, candidates)
    supported_trace_ids = sorted(row["trace_id"] for row in supported)
    supported_roles = sorted(row["role"] for row in supported)
    return {
        "schema": "uruha_source_preserving_memory_projection_single_record_raw_v2_3",
        "experiment_id": prereg["experiment_id"],
        "case_id": case["case_id"],
        "official_question_id": case["official_question_id"],
        "condition": condition["id"],
        "representation": representation,
        "visible_trace_ids": [row["trace_id"] for row in candidates],
        "visible_character_count": sum(len(row["text"]) for row in candidates),
        "expected_supported_trace_ids": expected,
        "supported_trace_ids": supported_trace_ids,
        "supported_roles": supported_roles,
        "safe_outcome": supported_trace_ids == sorted(expected),
        "target_supported": "target" in supported_roles,
        "hard_negative_supported": "hard_negative" in supported_roles,
        "evidence_validation": validation,
        "model_output": generation["content"],
        "carrier_valid": generation["carrier_valid"],
        "carrier_error": generation["carrier_error"],
        "raw_content": generation["raw_content"],
        "raw_tool_calls": generation["raw_tool_calls"],
        "latency_seconds": round(float(generation["latency_seconds"]), 6),
        "prompt_sha256": generation["prompt_sha256"],
        "prompt_character_count": generation["prompt_character_count"],
        "prompt_eval_count": generation["prompt_eval_count"],
        "eval_count": generation["eval_count"],
        "total_duration_ns": generation["total_duration_ns"],
        "transport_errors": errors,
        "transport_error_count": len(errors),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


def run_screen(cases, prereg, conditions, endpoint, model_call=call_single_record_model):
    rows = []
    controlled = prereg["controlled_variables"]
    for case in cases:
        for condition_id in controlled["conditions"]:
            for representation in controlled["representations"]:
                rows.append(
                    run_one(
                        case,
                        conditions[condition_id],
                        representation,
                        prereg,
                        endpoint,
                        model_call,
                    )
                )
    return rows


def write_outputs(rows, prereg, raw_path, metadata_path, endpoint):
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    controlled = prereg["controlled_variables"]
    metadata = {
        "schema": "uruha_source_preserving_memory_projection_single_record_metadata_v2_3",
        "experiment_id": prereg["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_short": git_value("status", "--short"),
        "endpoint": endpoint,
        "model": controlled["model"],
        "model_digest": controlled["model_digest"],
        "row_count": len(rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": file_sha256(raw_path),
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()
    if args.raw.exists() or args.metadata.exists():
        raise SystemExit("Frozen V2.3 run output already exists; refusing to rerun")
    contract, prereg, conditions = load_frozen_configuration()
    verify_frozen_inputs(contract, prereg, args.endpoint)
    cases = load_json(ROOT / contract["artifacts"]["cases"]["path"])["cases"]
    rows = run_screen(cases, prereg, conditions, args.endpoint)
    metadata = write_outputs(rows, prereg, args.raw, args.metadata, args.endpoint)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
