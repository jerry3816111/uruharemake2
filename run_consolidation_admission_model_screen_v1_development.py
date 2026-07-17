#!/usr/bin/env python3
"""Run the frozen consolidation-admission model screen exactly once."""

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

from consolidation_admission_model_screen_v1_core import (
    CONDITIONS,
    analyze_model_screen,
)
from consolidation_admission_v3_role_separated_core import (
    parse_role_separated_tool_response,
)
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")


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


def _model_snapshots(config):
    inventory = {
        row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])
    }
    snapshots = {}
    for condition in CONDITIONS:
        frozen = config["models"][condition]
        row = inventory.get(frozen["ollama_tag"])
        if not row or row.get("digest") != frozen["digest"]:
            raise ValueError(
                f"missing or drifted local model: {frozen['ollama_tag']}"
            )
        snapshots[condition] = {
            "ollama_tag": frozen["ollama_tag"],
            "digest": row["digest"],
            "size_bytes": row.get("size"),
            "details": row.get("details") or {},
        }
    return snapshots


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
    key = f"case_index_mod_3_equals_{case_index % 3}"
    return list(config["condition_order"][key])


def build_request_body(config, case, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    generation = config["generation"]
    contract = config["fixed_v3_contract"]
    return {
        "model": config["models"][condition]["ollama_tag"],
        "messages": [
            {"role": "system", "content": contract["system_prompt"]},
            {"role": "user", "content": render_transcript(config, case)},
        ],
        "tools": [contract["tool_contract"]],
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


def _transport_failure(case, condition, wall_seconds, exc):
    parsed = parse_role_separated_tool_response(
        {"message": {"content": "", "tool_calls": []}}
    )
    return {
        "id": case["id"],
        "condition": condition,
        **parsed,
        "wall_seconds": round(wall_seconds, 6),
        "transport_attempts": 1,
        "transport_error": f"{type(exc).__name__}: {exc}",
        "total_duration_ns": None,
        "load_duration_ns": None,
        "prompt_eval_count": None,
        "eval_count": None,
    }


def _call_condition(config, case, condition):
    generation = config["generation"]
    if generation["transport_attempts"] != 1:
        raise ValueError("model screen forbids transport retries")
    body = build_request_body(config, case, condition)
    started = time.perf_counter()
    try:
        response = _post_json(
            config["local_runtime"]["endpoint"],
            body,
            generation["timeout_seconds"],
        )
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        return _transport_failure(
            case, condition, time.perf_counter() - started, exc
        )
    parsed = parse_role_separated_tool_response(response)
    return {
        "id": case["id"],
        "condition": condition,
        **parsed,
        "wall_seconds": round(time.perf_counter() - started, 6),
        "transport_attempts": 1,
        "transport_error": None,
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def _frozen_paths(config):
    return {
        "preregistration": CONFIG_PATH,
        "dataset": ROOT / config["dataset"]["path"],
        "preregistration_test": (
            ROOT
            / "test_consolidation_admission_model_screen_v1_preregistration.py"
        ),
        "v3_preregistration": (
            ROOT
            / "configs"
            / "consolidation_admission_v3_role_separated_development_preregistration.json"
        ),
        "v3_result_lock": (
            ROOT
            / "configs"
            / "consolidation_admission_v3_role_separated_result_lock.json"
        ),
        "v3_core": (
            ROOT / "consolidation_admission_v3_role_separated_core.py"
        ),
        "v46_analysis": (
            ROOT / "reports" / "commitment_model_capacity_v46_development_analysis.md"
        ),
        "core": ROOT / "consolidation_admission_model_screen_v1_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": (
            ROOT
            / "analyze_consolidation_admission_model_screen_v1_development.py"
        ),
        "harness_test": (
            ROOT
            / "test_consolidation_admission_model_screen_v1_harness.py"
        ),
    }


def verify(config, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("model screen must run from main")
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
        raise ValueError("model-screen harness lock is not committed")
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


def _new_report(config, model_snapshots):
    return {
        "schema": "uruha_consolidation_admission_model_screen_raw_v1",
        "experiment_id": config["experiment_id"],
        "evidence_status": "development_model_screen_no_runtime_or_generalization_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "v3_result_lock_sha256": sha256(
            ROOT
            / "configs"
            / "consolidation_admission_v3_role_separated_result_lock.json"
        ),
        "model_snapshots": model_snapshots,
        "model_calls": 0,
        "transport_attempts_made": 0,
        "gold_fields_passed_to_model": False,
        "runtime_memory_write_performed": False,
        "rows_by_condition": {condition: [] for condition in CONDITIONS},
        "inflight": None,
        "gate_snapshot": None,
    }


def _resume_report(output, config, model_snapshots):
    report = _load(output)
    if report.get("completed_at"):
        raise ValueError("completed model screen cannot be rerun")
    for key, expected in {
        "experiment_id": config["experiment_id"],
        "runner_commit": git_value("rev-parse", "HEAD"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "v3_result_lock_sha256": sha256(
            ROOT
            / "configs"
            / "consolidation_admission_v3_role_separated_result_lock.json"
        ),
        "model_snapshots": model_snapshots,
    }.items():
        if report.get(key) != expected:
            raise ValueError(f"resume provenance drift: {key}")
    return report


def _validate_report_progress(report, dataset):
    if report.get("inflight") is not None:
        raise ValueError(
            "resume has an ambiguous in-flight request; do not repeat it"
        )
    rows_by_condition = report.get("rows_by_condition")
    if not isinstance(rows_by_condition, dict):
        raise ValueError("resume rows are missing")
    if set(rows_by_condition) != set(CONDITIONS):
        raise ValueError("resume condition set drift")
    valid_case_ids = {case["id"] for case in dataset["cases"]}
    completed = set()
    transport_attempts = 0
    for condition in CONDITIONS:
        rows = rows_by_condition[condition]
        if not isinstance(rows, list):
            raise ValueError(f"resume rows are not a list: {condition}")
        if len(rows) > len(valid_case_ids):
            raise ValueError(f"too many resume rows: {condition}")
        for row in rows:
            key = (row.get("id"), row.get("condition"))
            if row.get("id") not in valid_case_ids:
                raise ValueError("resume contains an unknown case")
            if row.get("condition") != condition:
                raise ValueError("resume row condition drift")
            if key in completed:
                raise ValueError("resume contains duplicate rows")
            completed.add(key)
            if row.get("transport_attempts") != 1:
                raise ValueError("resume transport attempt drift")
            transport_attempts += 1
    if report.get("model_calls") != len(completed):
        raise ValueError("resume model call count drift")
    if report.get("transport_attempts_made") != transport_attempts:
        raise ValueError("resume transport count drift")
    if report.get("gold_fields_passed_to_model"):
        raise ValueError("resume exposed gold fields")
    if report.get("runtime_memory_write_performed"):
        raise ValueError("resume performed a runtime memory write")
    if report.get("gate_snapshot") is not None:
        raise ValueError("incomplete resume already contains a gate snapshot")
    return completed


def run(output=DEFAULT_OUTPUT):
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    verify(config, lock)
    dataset = _load(ROOT / config["dataset"]["path"])
    model_snapshots = _model_snapshots(config)
    report = (
        _resume_report(output, config, model_snapshots)
        if output.exists()
        else _new_report(config, model_snapshots)
    )
    if not output.exists():
        _atomic_write(output, report)

    completed = _validate_report_progress(report, dataset)
    for case_index, case in enumerate(dataset["cases"]):
        for condition in condition_order(config, case_index):
            key = (case["id"], condition)
            if key in completed:
                continue
            report["inflight"] = {
                "id": case["id"],
                "condition": condition,
                "recorded_at": datetime.now(TZ).isoformat(
                    timespec="seconds"
                ),
            }
            _atomic_write(output, report)
            called = _call_condition(config, case, condition)
            report["rows_by_condition"][condition].append(called)
            report["model_calls"] += 1
            report["transport_attempts_made"] += called[
                "transport_attempts"
            ]
            report["inflight"] = None
            completed.add(key)
            _atomic_write(output, report)

    report["gate_snapshot"] = analyze_model_screen(
        dataset["cases"],
        report["rows_by_condition"],
        models=config["models"],
        eligibility_gates=config["eligibility_gates"],
        latency_gates=config["latency_gates"],
        run_invariants=config["run_invariants"],
        model_calls=report["model_calls"],
        transport_attempts=report["transport_attempts_made"],
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
