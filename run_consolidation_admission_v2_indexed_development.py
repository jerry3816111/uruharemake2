#!/usr/bin/env python3
"""Run the frozen indexed consolidation-admission V2 pilot once."""

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

from consolidation_admission_v2_indexed_core import (
    analyze_indexed_conditions,
    parse_indexed_tool_response,
    parse_v1_control_response,
)
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_development_preregistration.json"
)
CORRECTION_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_protocol_correction.json"
)
LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_harness_lock.json"
)
V1_CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
V1_RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")
CONTROL = "v1_source_bound_json_control"
CANDIDATE = "v2_indexed_tool_candidate"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
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
    inventory = {
        row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])
    }
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


def render_transcript(config, case):
    template = config["fixed_transcript_rendering"]
    return "\n".join(
        template.format(
            index=index,
            user=turn["user"],
            assistant=turn["assistant"],
        )
        for index, turn in enumerate(case["session"], start=1)
    )


def condition_order(config, case_index):
    key = "even_case_index" if case_index % 2 == 0 else "odd_case_index"
    return list(config["condition_order"][key])


def build_request_body(config, case, condition_name):
    generation = config["generation"]
    condition = config["conditions"][condition_name]
    body = {
        "model": config["model"]["name"],
        "messages": [
            {"role": "system", "content": condition["system_prompt"]},
            {"role": "user", "content": render_transcript(config, case)},
        ],
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
    if condition_name == CANDIDATE:
        body["tools"] = [condition["tool_contract"]]
    elif condition_name != CONTROL:
        raise ValueError(f"unknown condition: {condition_name}")
    return body


def _call_condition(config, v1_config, case, condition_name):
    generation = config["generation"]
    body = build_request_body(config, case, condition_name)
    errors = []
    for attempt in range(1, generation["transport_attempts"] + 1):
        started = time.perf_counter()
        try:
            response = _post_json(
                config["local_runtime"]["endpoint"],
                body,
                generation["timeout_seconds"],
            )
            wall_seconds = time.perf_counter() - started
            if condition_name == CONTROL:
                parsed = parse_v1_control_response(
                    response,
                    [turn["user"] for turn in case["session"]],
                    v1_config["conditions"]["source_bound_layered_candidate"],
                )
            else:
                parsed = parse_indexed_tool_response(response)
            return {
                "id": case["id"],
                "condition": condition_name,
                **parsed,
                "wall_seconds": round(wall_seconds, 6),
                "transport_attempts": attempt,
                "prior_transport_errors": errors,
                "total_duration_ns": response.get("total_duration"),
                "load_duration_ns": response.get("load_duration"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "eval_count": response.get("eval_count"),
            }
        except (
            OSError,
            TimeoutError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < generation["transport_attempts"]:
                time.sleep(attempt)
    raise RuntimeError(f"Ollama request failed: {' | '.join(errors)}")


def _frozen_paths(config):
    return {
        "preregistration": CONFIG_PATH,
        "protocol_correction": CORRECTION_PATH,
        "dataset": ROOT / config["dataset"]["path"],
        "v1_preregistration": V1_CONFIG_PATH,
        "v1_core": ROOT / "consolidation_admission_v1_core.py",
        "v1_result_lock": V1_RESULT_LOCK_PATH,
        "core": ROOT / "consolidation_admission_v2_indexed_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": (
            ROOT / "analyze_consolidation_admission_v2_indexed_development.py"
        ),
        "harness_test": (
            ROOT / "test_consolidation_admission_v2_indexed_harness.py"
        ),
    }


def verify(config, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("indexed consolidation pilot must run from main")
    if git_value("rev-parse", "HEAD") != git_value(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    committed_lock = subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            f"HEAD:{LOCK_PATH.relative_to(ROOT)}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if committed_lock.returncode != 0:
        raise ValueError("indexed consolidation harness lock is not committed")
    if _ollama_version() != config["local_runtime"]["ollama_version"]:
        raise ValueError("Ollama version drift")
    for name, path in _frozen_paths(config).items():
        expected = lock["frozen_artifacts"][f"{name}_sha256"]
        if sha256(path) != expected:
            raise ValueError(f"frozen artifact drift: {name}")
    if config[
        "model_inference_before_preregistration_and_harness_merge_authorized"
    ]:
        raise ValueError("invalid preregistration inference policy")
    if lock["model_inference_before_harness_merge_authorized"]:
        raise ValueError("invalid harness inference policy")


def _new_report(config, model_snapshot):
    return {
        "schema": "uruha_consolidation_admission_indexed_development_raw_v2",
        "experiment_id": config["experiment_id"],
        "evidence_status": "development_pilot_no_runtime_or_generalization_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_correction_sha256": sha256(CORRECTION_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "v1_preregistration_sha256": sha256(V1_CONFIG_PATH),
        "v1_core_sha256": sha256(ROOT / "consolidation_admission_v1_core.py"),
        "v1_result_lock_sha256": sha256(V1_RESULT_LOCK_PATH),
        "model_snapshot": model_snapshot,
        "model_calls": 0,
        "transport_attempts_made": 0,
        "gold_fields_passed_to_model": False,
        "runtime_memory_write_performed": False,
        "control_rows": [],
        "candidate_rows": [],
        "gate_snapshot": None,
    }


def _resume_report(output, config):
    report = _load(output)
    if report.get("completed_at"):
        raise ValueError("completed pilot cannot be rerun")
    for key, expected in {
        "experiment_id": config["experiment_id"],
        "runner_commit": git_value("rev-parse", "HEAD"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "protocol_correction_sha256": sha256(CORRECTION_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "v1_preregistration_sha256": sha256(V1_CONFIG_PATH),
        "v1_core_sha256": sha256(
            ROOT / "consolidation_admission_v1_core.py"
        ),
        "v1_result_lock_sha256": sha256(V1_RESULT_LOCK_PATH),
    }.items():
        if report.get(key) != expected:
            raise ValueError(f"resume provenance drift: {key}")
    return report


def run(output=DEFAULT_OUTPUT):
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    v1_config = _load(V1_CONFIG_PATH)
    verify(config, lock)
    dataset = _load(ROOT / config["dataset"]["path"])
    model_snapshot = _model_snapshot(config)
    report = (
        _resume_report(output, config)
        if output.exists()
        else _new_report(config, model_snapshot)
    )
    if not output.exists():
        _atomic_write(output, report)

    completed = {
        (row["id"], row["condition"])
        for key in ("control_rows", "candidate_rows")
        for row in report[key]
    }
    for case_index, case in enumerate(dataset["cases"]):
        for condition_name in condition_order(config, case_index):
            key = (case["id"], condition_name)
            if key in completed:
                continue
            called = _call_condition(
                config, v1_config, case, condition_name
            )
            target = (
                "control_rows"
                if condition_name == CONTROL
                else "candidate_rows"
            )
            report[target].append(called)
            report["model_calls"] += 1
            report["transport_attempts_made"] += called["transport_attempts"]
            completed.add(key)
            _atomic_write(output, report)

    report["gate_snapshot"] = analyze_indexed_conditions(
        dataset["cases"],
        report["control_rows"],
        report["candidate_rows"],
        config["success_gates"],
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
