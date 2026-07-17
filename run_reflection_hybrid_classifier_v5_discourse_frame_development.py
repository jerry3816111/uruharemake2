#!/usr/bin/env python3
"""Run the frozen V5 discourse-frame reflection development pilot."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_reflection_runtime as reflection
from reflection_hybrid_classifier_v5_core import (
    analyze_discourse_frame_condition,
    parse_direct_tool_response,
    parse_discourse_frame_tool_response,
)
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_development_preregistration.json"
AMENDMENT_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_protocol_amendment.json"
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_harness_lock.json"
V3_CONFIG_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_hybrid_classifier_v5_discourse_frame_development_raw.json"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _post_json(url, body, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _ollama_version():
    output = subprocess.check_output(
        ["ollama", "--version"], text=True, stderr=subprocess.STDOUT
    ).strip()
    prefix = "ollama version is "
    if not output.startswith(prefix):
        raise ValueError(f"unexpected Ollama version output: {output}")
    return output.removeprefix(prefix)


def _model_snapshot(config):
    inventory = {row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])}
    frozen = config["model"]
    row = inventory.get(frozen["name"])
    if not row or row.get("digest") != frozen["digest"]:
        raise ValueError(f"missing or drifted local model: {frozen['name']}")
    return {
        "name": frozen["name"],
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def _call_model(config, v3_config, condition, language, utterance):
    generation = config["generation"]
    if condition == "live_direct_control":
        system_prompt = v3_config["system_prompt"]
        tool_contract = v3_config["tool_contract"]
    elif condition == "discourse_frame_candidate":
        system_prompt = config["system_prompt"]
        tool_contract = config["tool_contract"]
    else:
        raise ValueError(f"unknown condition: {condition}")
    body = {
        "model": config["model"]["name"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"language": language, "utterance": utterance},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "tools": [tool_contract],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": generation["keep_alive"],
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }
    errors = []
    for attempt in range(1, generation["transport_attempts"] + 1):
        started = time.perf_counter()
        try:
            response = _post_json(
                generation["endpoint"], body, generation["timeout_seconds"]
            )
            wall = time.perf_counter() - started
            if condition == "live_direct_control":
                label, parsed, content, tool_calls, parse_error = (
                    parse_direct_tool_response(response)
                )
                frame = None
            else:
                frame, parsed, content, tool_calls, parse_error = (
                    parse_discourse_frame_tool_response(response)
                )
                label = None if frame is None else frame["reflection_type"]
            return {
                "condition": condition,
                "observed_type": "none" if label is None else label,
                "discourse_frame": frame,
                "parse_success": parsed,
                "parse_error": parse_error,
                "raw_content": content,
                "raw_tool_calls": tool_calls,
                "wall_seconds": round(wall, 6),
                "transport_attempts": attempt,
                "prior_transport_errors": errors,
                "total_duration_ns": response.get("total_duration"),
                "load_duration_ns": response.get("load_duration"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "eval_count": response.get("eval_count"),
            }
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < generation["transport_attempts"]:
                time.sleep(attempt)
    raise RuntimeError(f"Ollama request failed: {' | '.join(errors)}")


def _frozen_paths(config):
    return {
        "preregistration": CONFIG_PATH,
        "protocol_amendment": AMENDMENT_PATH,
        "dataset": ROOT / config["dataset"]["path"],
        "v3_preregistration": V3_CONFIG_PATH,
        "frozen_control_result_lock": ROOT
        / config["frozen_control"]["result_lock_path"],
        "frozen_control_analysis": ROOT / config["frozen_control"]["analysis_path"],
        "core": ROOT / "reflection_hybrid_classifier_v5_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": ROOT
        / "analyze_reflection_hybrid_classifier_v5_discourse_frame_development.py",
    }


def verify(config, lock):
    if git_value("branch", "--show-current") != "main":
        raise ValueError("discourse-frame pilot must run from main")
    if git_value("rev-parse", "HEAD") != git_value("rev-parse", "origin/main"):
        raise ValueError("main must match origin/main")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    if _ollama_version() != config["local_runtime"]["ollama_version"]:
        raise ValueError("Ollama version drift")
    for name, path in _frozen_paths(config).items():
        expected = lock["frozen_artifacts"][f"{name}_sha256"]
        if sha256(path) != expected:
            raise ValueError(f"frozen artifact drift: {name}")
    if config["model_inference_before_preregistration_merge_authorized"]:
        raise ValueError("invalid preregistration inference policy")


def _control_rows(config):
    analysis = _load(ROOT / config["frozen_control"]["analysis_path"])
    return analysis["analyses"][config["model"]["name"]]["rows"]


def _new_report(config, model_snapshot, rules_predictions):
    return {
        "schema": "uruha_reflection_hybrid_classifier_discourse_frame_development_raw_v5",
        "evidence_status": "development_pilot_no_generalization_or_runtime_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "frozen_control_result_lock_sha256": sha256(
            ROOT / config["frozen_control"]["result_lock_path"]
        ),
        "frozen_control_analysis_sha256": sha256(
            ROOT / config["frozen_control"]["analysis_path"]
        ),
        "model_snapshot": model_snapshot,
        "model_calls": 0,
        "gold_label_passed_to_model": False,
        "fresh_v4_holdout_loaded": False,
        "runtime_memory_write_performed": False,
        "rules_predictions": rules_predictions,
        "live_control_fallback_rows": [],
        "candidate_fallback_rows": [],
        "gate_snapshot": None,
    }


def run(output=DEFAULT_OUTPUT):
    config = _load(CONFIG_PATH)
    amendment = _load(AMENDMENT_PATH)
    v3_config = _load(V3_CONFIG_PATH)
    lock = _load(LOCK_PATH)
    verify(config, lock)
    dataset = _load(ROOT / config["dataset"]["path"])
    model_snapshot = _model_snapshot(config)
    rules_predictions = {
        case["id"]: reflection.classify_reflection_type(case["text"])
        for case in dataset["cases"]
    }
    frozen_rows = _control_rows(config)
    frozen_rules = {row["id"]: row["rules_observed_type"] for row in frozen_rows}
    if rules_predictions != frozen_rules:
        raise ValueError("rules-only control no longer reproduces frozen V3 rows")

    if output.exists():
        report = _load(output)
        if report.get("completed_at"):
            raise ValueError("completed pilot cannot be rerun")
        for key, expected in {
            "runner_commit": git_value("rev-parse", "HEAD"),
            "ollama_version": _ollama_version(),
            "preregistration_sha256": sha256(CONFIG_PATH),
            "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
            "harness_lock_sha256": sha256(LOCK_PATH),
            "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
            "rules_predictions": rules_predictions,
        }.items():
            if report.get(key) != expected:
                raise ValueError(f"resume provenance drift: {key}")
    else:
        report = _new_report(config, model_snapshot, rules_predictions)
        _atomic_write(output, report)

    completed_control_ids = {
        row["id"] for row in report["live_control_fallback_rows"]
    }
    for case in dataset["cases"]:
        if (
            rules_predictions[case["id"]] != "none"
            or case["id"] in completed_control_ids
        ):
            continue
        called = _call_model(
            config,
            v3_config,
            "live_direct_control",
            case["language"],
            case["text"],
        )
        report["live_control_fallback_rows"].append(
            {"id": case["id"], **called}
        )
        report["model_calls"] += 1
        _atomic_write(output, report)

    completed_candidate_ids = {
        row["id"] for row in report["candidate_fallback_rows"]
    }
    for case in dataset["cases"]:
        if (
            rules_predictions[case["id"]] != "none"
            or case["id"] in completed_candidate_ids
        ):
            continue
        called = _call_model(
            config,
            v3_config,
            "discourse_frame_candidate",
            case["language"],
            case["text"],
        )
        report["candidate_fallback_rows"].append(
            {"id": case["id"], **called}
        )
        report["model_calls"] += 1
        _atomic_write(output, report)

    report["gate_snapshot"] = analyze_discourse_frame_condition(
        dataset["cases"],
        rules_predictions,
        frozen_rows,
        report["live_control_fallback_rows"],
        report["candidate_fallback_rows"],
        amendment["unchanged_candidate_capability_gates"],
        amendment["live_control_reproduction_gates"],
        amendment["correction"]["total_model_call_count_exact"],
    )
    report["completed_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps(report["gate_snapshot"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
