#!/usr/bin/env python3
"""Run the frozen answer-bearing memory span V1 development experiment."""

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import uruha_memory_runtime as umr
from answer_bearing_memory_span import (
    build_answer_evidence_json_schema,
    build_answer_evidence_prompt,
    parse_answer_evidence,
    supported_candidates,
    validate_answer_evidence,
)


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/answer_bearing_memory_span_v1_development_preregistration.json"
DEFAULT_RAW = ROOT / "analysis/local_answer_bearing_memory_span_v1_development/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_answer_bearing_memory_span_v1_development/run_metadata.json"


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


def verify_frozen_inputs(prereg, endpoint):
    data = prereg["development_data"]
    if file_sha256(ROOT / data["cases_path"]) != data["cases_sha256"]:
        raise ValueError("development cases hash mismatch")
    if file_sha256(ROOT / data["baseline_raw_path"]) != data["baseline_raw_sha256"]:
        raise ValueError("baseline raw hash mismatch")
    model = prereg["inference"]["model"]
    expected_digest = prereg["inference"]["model_digest"]
    matched = next(
        (row for row in installed_models(endpoint) if row.get("name") == model), None
    )
    if not matched:
        raise ValueError(f"missing local model: {model}")
    if matched.get("digest") != expected_digest:
        raise ValueError("local model digest mismatch")


def condition_candidates(case, condition):
    role_map = {
        "target": case["target"],
        "hard_negative": case["hard_negative"],
        "replacement": case["replacement"],
    }
    rows = []
    for role in condition["visible_candidates"]:
        source = role_map[role]
        rows.append(
            {
                "role": role,
                "trace_id": source["trace_id"],
                "memory_id": source["trace_id"],
                "source": "memory_stream",
                "text": source["text"],
                "score": float(source["score"]),
            }
        )
    return rows


def expected_trace_id(case, condition):
    role = condition["expected_selection"]
    if role is None:
        return None
    return case[role]["trace_id"]


def post_ollama(endpoint, body, timeout=180):
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def call_evidence_model(question, candidates, prereg, endpoint):
    inference = prereg["inference"]
    prompt = build_answer_evidence_prompt(question, candidates)
    body = {
        "model": inference["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": bool(inference["think"]),
        "format": build_answer_evidence_json_schema(len(candidates)),
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
    content = ((response.get("message") or {}).get("content") or "").strip()
    return {
        "content": content,
        "latency_seconds": latency,
        "prompt_sha256": text_sha256(prompt),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "total_duration_ns": response.get("total_duration"),
    }


def select_with_frozen_policy(question, candidates, validation, prereg):
    policy = prereg["fixed_selection_policy"]
    eligible = supported_candidates(validation, candidates)
    eligible.sort(key=lambda row: float(row.get("score") or 0.0), reverse=True)
    common = {
        "candidate_count": len(candidates),
        "span_supported_candidate_count": len(eligible),
    }
    if not validation.get("valid"):
        return {**common, "status": "invalid_evidence_contract", "selected": False}
    if not eligible:
        return {**common, "status": "unsupported", "selected": False}

    top = eligible[0]
    top_score = float(top.get("score") or 0.0)
    runner_up_score = (
        float(eligible[1].get("score") or 0.0) if len(eligible) > 1 else None
    )
    margin = top_score - runner_up_score if runner_up_score is not None else top_score
    common.update(
        {
            "top_score": round(top_score, 4),
            "runner_up_score": round(runner_up_score, 4)
            if runner_up_score is not None
            else None,
            "margin": round(margin, 4),
            "trace_id": top["trace_id"],
            "answer_span": top["answer_evidence"]["answer_span"],
        }
    )
    if top_score < float(policy["minimum_top_score"]):
        return {**common, "status": "below_threshold", "selected": False}
    if runner_up_score is not None and margin < float(policy["minimum_margin"]):
        return {**common, "status": "ambiguous", "selected": False}

    speakability = umr.assess_memory_speakability(
        {
            "source_text": top["text"],
            "value": top["text"],
            "jp_anchor": top["text"],
            "expected": True,
            "relevance": min(1.0, max(0.0, top_score)),
        },
        user_input=question,
        trust=50,
    )
    if not speakability.get("should_use_explicitly"):
        return {
            **common,
            "status": "suppressed",
            "selected": False,
            "speakability": speakability,
        }
    return {
        **common,
        "status": "selected",
        "selected": True,
        "speakability": speakability,
    }


def run_one(case, condition, prereg, endpoint, model_call=call_evidence_model):
    candidates = condition_candidates(case, condition)
    expected = expected_trace_id(case, condition)
    transport_errors = []
    try:
        generation = model_call(case["question"], candidates, prereg, endpoint)
        parsed = parse_answer_evidence(generation["content"])
        validation = validate_answer_evidence(parsed, candidates)
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        transport_errors.append(f"{type(exc).__name__}:{exc}")
        generation = {
            "content": "",
            "latency_seconds": 0.0,
            "prompt_sha256": None,
            "prompt_eval_count": None,
            "eval_count": None,
            "total_duration_ns": None,
        }
        validation = validate_answer_evidence(None, candidates)

    selection = select_with_frozen_policy(
        case["question"], candidates, validation, prereg
    )
    selected_trace = selection.get("trace_id") if selection.get("selected") else None
    safe = selected_trace == expected
    return {
        "schema": "uruha_answer_bearing_memory_span_development_raw_v1",
        "case_id": case["case_id"],
        "official_question_id": case["official_question_id"],
        "language": case["language"],
        "condition": condition["id"],
        "visible_trace_ids": [row["trace_id"] for row in candidates],
        "expected_trace_id": expected,
        "selected": bool(selection.get("selected")),
        "selected_trace_id": selected_trace,
        "status": selection.get("status"),
        "safe_outcome": safe,
        "wrong_trace_selected": bool(selected_trace and selected_trace != expected),
        "evidence_validation": validation,
        "selection_evidence": {
            key: selection.get(key)
            for key in (
                "candidate_count",
                "span_supported_candidate_count",
                "top_score",
                "runner_up_score",
                "margin",
                "answer_span",
            )
            if key in selection
        },
        "model_output": generation["content"],
        "latency_seconds": round(float(generation["latency_seconds"]), 6),
        "prompt_sha256": generation["prompt_sha256"],
        "prompt_eval_count": generation["prompt_eval_count"],
        "eval_count": generation["eval_count"],
        "total_duration_ns": generation["total_duration_ns"],
        "transport_errors": transport_errors,
        "transport_error_count": len(transport_errors),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


def git_value(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def run_experiment(prereg, endpoint, model_call=call_evidence_model):
    cases = load_json(ROOT / prereg["development_data"]["cases_path"])["cases"]
    rows = []
    for case in cases:
        for condition in prereg["conditions"]:
            rows.append(run_one(case, condition, prereg, endpoint, model_call=model_call))
    return rows


def write_outputs(rows, prereg, raw_path, metadata_path, endpoint):
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    raw_path.write_text(raw_text, encoding="utf-8")
    metadata = {
        "schema": "uruha_answer_bearing_memory_span_development_run_metadata_v1",
        "experiment_id": prereg["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_short": git_value("status", "--short"),
        "endpoint": endpoint,
        "model": prereg["inference"]["model"],
        "model_digest": prereg["inference"]["model_digest"],
        "think": prereg["inference"]["think"],
        "row_count": len(rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": file_sha256(raw_path),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(
            row["physical_vrm_action_count"] for row in rows
        ),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
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
    prereg = load_json(PREREG_PATH)
    verify_frozen_inputs(prereg, args.endpoint)
    rows = run_experiment(prereg, args.endpoint)
    metadata = write_outputs(rows, prereg, args.raw, args.metadata, args.endpoint)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
