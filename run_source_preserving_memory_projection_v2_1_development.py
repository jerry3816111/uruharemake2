#!/usr/bin/env python3
"""Run the frozen source-preserving memory projection V2.1 development experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from answer_bearing_memory_span import (
    build_answer_evidence_json_schema,
    build_answer_evidence_prompt,
    parse_answer_evidence,
    supported_candidates,
    validate_answer_evidence,
)
from build_source_preserving_memory_projection_v2_1_development import (
    effective_preregistration,
)


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_1_evaluation_contract.json"
DEFAULT_RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/run_metadata.json"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha256(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def installed_models(endpoint):
    tags_url = endpoint.rsplit("/api/", 1)[0] + "/api/tags"
    with urllib.request.urlopen(tags_url, timeout=30) as response:
        return json.load(response).get("models") or []


def load_effective_contract():
    contract = load_json(CONTRACT)
    base = load_json(ROOT / contract["artifacts"]["base_preregistration"]["path"])
    revision = load_json(ROOT / contract["artifacts"]["revision_preregistration"]["path"])
    effective = effective_preregistration(base, revision)
    return contract, effective


def verify_frozen_inputs(contract, prereg, endpoint):
    for artifact in contract["artifacts"].values():
        if file_sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"frozen artifact hash mismatch: {artifact['path']}")
    if endpoint != prereg["span_gate"]["endpoint"]:
        raise ValueError("Ollama endpoint drift")
    model = prereg["span_gate"]["model"]
    expected_digest = prereg["span_gate"]["model_digest"]
    matched = next((row for row in installed_models(endpoint) if row.get("name") == model), None)
    if not matched:
        raise ValueError(f"missing local model: {model}")
    if matched.get("digest") != expected_digest:
        raise ValueError("local model digest mismatch")


def condition_candidates(case, condition, representation):
    rows = []
    for role in condition["visible_candidates"]:
        record = case[role]
        represented = record[representation]
        rows.append(
            {
                "role": role,
                "trace_id": record["trace_id"],
                "text": represented["text"],
                "score": float(record["score"]),
                "representation": representation,
                "source_turn_indices": represented["source_turn_indices"],
            }
        )
    return rows


def expected_trace_ids(case, condition):
    role = condition["expected_answer_bearing_candidate"]
    return [] if role is None else [case[role]["trace_id"]]


def post_ollama(endpoint, body, timeout=240):
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def call_evidence_model(question, candidates, prereg, endpoint):
    inference = prereg["span_gate"]
    prompt = build_answer_evidence_prompt(question, candidates)
    body = {
        "model": inference["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": bool(inference["think"]),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "submit_answer_evidence",
                    "description": "Submit one complete evidence verdict for every visible source index.",
                    "parameters": build_answer_evidence_json_schema(len(candidates)),
                },
            }
        ],
        "options": {
            "temperature": inference["temperature"],
            "seed": inference["seed"],
            "num_ctx": inference["num_ctx"],
            "num_predict": inference["max_tokens"],
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
        if function.get("name") != "submit_answer_evidence":
            carrier_error = "tool_name"
        elif not isinstance(function.get("arguments"), dict):
            carrier_error = "tool_arguments_type"
        else:
            arguments = function["arguments"]
    content = json.dumps(arguments, ensure_ascii=False, sort_keys=True) if arguments else ""
    return {
        "content": content,
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


def run_one(case, condition, representation, prereg, endpoint, model_call=call_evidence_model):
    candidates = condition_candidates(case, condition, representation)
    expected = expected_trace_ids(case, condition)
    errors = []
    try:
        generation = model_call(case["question"], candidates, prereg, endpoint)
        parsed = parse_answer_evidence(generation["content"])
        validation = validate_answer_evidence(parsed, candidates)
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
        validation = validate_answer_evidence(None, candidates)
    supported = supported_candidates(validation, candidates)
    supported_trace_ids = sorted(row["trace_id"] for row in supported)
    supported_roles = sorted(row["role"] for row in supported)
    return {
        "schema": "uruha_source_preserving_memory_projection_raw_v2_1",
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


def phase_rows(cases, conditions, representations, prereg, endpoint, model_call):
    rows = []
    by_id = {condition["id"]: condition for condition in prereg["matched_conditions"]}
    for case in cases:
        for condition_id in conditions:
            for representation in representations:
                rows.append(
                    run_one(
                        case,
                        by_id[condition_id],
                        representation,
                        prereg,
                        endpoint,
                        model_call=model_call,
                    )
                )
    return rows


def exact_row_matrix(rows, conditions, representations, expected_count):
    case_ids = {row.get("case_id") for row in rows}
    expected = {
        (case_id, condition, representation)
        for case_id in case_ids
        for condition in conditions
        for representation in representations
    }
    actual = [
        (row.get("case_id"), row.get("condition"), row.get("representation"))
        for row in rows
    ]
    return (
        len(actual) == expected_count
        and len(set(actual)) == len(actual)
        and set(actual) == expected
    )


def phase_1_passes(rows, prereg):
    stage = prereg["staged_execution"]
    gate = prereg["staged_execution"]["phase_1_continue_only_if"]
    projected_target_only = [
        row
        for row in rows
        if row["condition"] == "remove_exact_hard_negative"
        and row["representation"] == "source_projection"
    ]
    projected_removed = [
        row
        for row in rows
        if row["condition"] == "remove_exact_target"
        and row["representation"] == "source_projection"
    ]
    return all(
        [
            exact_row_matrix(
                rows,
                stage["phase_1_conditions"],
                stage["phase_1_representations"],
                stage["phase_1_call_count"],
            ),
            sum(row["target_supported"] for row in projected_target_only)
            >= gate["projected_target_only_supported_count_at_least"],
            sum(row["hard_negative_supported"] for row in projected_removed)
            == gate["projected_hard_negative_supported_count_equals"],
            all(row["evidence_validation"].get("valid") for row in rows),
            all(row["evidence_validation"].get("all_spans_grounded") for row in rows),
            sum(row["transport_error_count"] for row in rows)
            == gate["transport_error_count_equals"],
        ]
    )


def run_experiment(cases, prereg, endpoint, model_call=call_evidence_model):
    stage = prereg["staged_execution"]
    rows = phase_rows(
        cases,
        stage["phase_1_conditions"],
        stage["phase_1_representations"],
        prereg,
        endpoint,
        model_call,
    )
    passed = phase_1_passes(rows, prereg)
    if passed:
        rows.extend(
            phase_rows(
                cases,
                stage["phase_2_conditions"],
                stage["phase_2_representations"],
                prereg,
                endpoint,
                model_call,
            )
        )
    return rows, passed


def git_value(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def write_outputs(rows, phase_1_passed, prereg, raw_path, metadata_path, endpoint):
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    metadata = {
        "schema": "uruha_source_preserving_memory_projection_run_metadata_v2_1",
        "experiment_id": prereg["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_short": git_value("status", "--short"),
        "endpoint": endpoint,
        "model": prereg["span_gate"]["model"],
        "model_digest": prereg["span_gate"]["model_digest"],
        "phase_1_passed": phase_1_passed,
        "row_count": len(rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": file_sha256(raw_path),
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()
    if args.raw.exists() or args.metadata.exists():
        raise SystemExit("Frozen V2.1 run output already exists; refusing to rerun")
    contract, prereg = load_effective_contract()
    verify_frozen_inputs(contract, prereg, args.endpoint)
    cases = load_json(ROOT / contract["artifacts"]["cases"]["path"])["cases"]
    rows, phase_1_passed = run_experiment(cases, prereg, args.endpoint)
    metadata = write_outputs(
        rows, phase_1_passed, prereg, args.raw, args.metadata, args.endpoint
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
