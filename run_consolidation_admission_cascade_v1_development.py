#!/usr/bin/env python3
"""Run the frozen conditional 4B-to-9B admission cascade exactly once."""

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

from consolidation_admission_cascade_v1_core import (
    CANDIDATE,
    CONTROL,
    analyze_cascade,
    parse_write_gate_tool_response,
)
from consolidation_admission_v3_role_separated_core import (
    parse_role_separated_tool_response,
)
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
MODEL_KEYS = (
    "stage1_write_gate",
    "direct_control_and_stage2_classifier",
)
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
    for model_key in MODEL_KEYS:
        frozen = config["models"][model_key]
        row = inventory.get(frozen["ollama_tag"])
        if not row or row.get("digest") != frozen["digest"]:
            raise ValueError(
                f"missing or drifted local model: {frozen['ollama_tag']}"
            )
        snapshots[model_key] = {
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
    key = "even_case_index" if case_index % 2 == 0 else "odd_case_index"
    return list(config["condition_order"][key])


def _base_request(config, case, model_key, contract):
    generation = config["generation"]
    return {
        "model": config["models"][model_key]["ollama_tag"],
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


def build_stage1_request_body(config, case):
    return _base_request(
        config,
        case,
        "stage1_write_gate",
        config["stage1_write_gate"],
    )


def build_final_request_body(config, case):
    """Build the identical 9B request used by control and cascade stage 2."""
    return _base_request(
        config,
        case,
        "direct_control_and_stage2_classifier",
        config["final_classifier"],
    )


def _response_metadata(response):
    return {
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def _stage1_transport_failure(case, wall_seconds, exc):
    parsed = parse_write_gate_tool_response(
        {"message": {"content": "", "tool_calls": []}}
    )
    return {
        "id": case["id"],
        "condition": CANDIDATE,
        "stage": "stage1",
        **parsed,
        "wall_seconds": round(wall_seconds, 6),
        "transport_attempts": 1,
        "transport_error": f"{type(exc).__name__}: {exc}",
        "total_duration_ns": None,
        "load_duration_ns": None,
        "prompt_eval_count": None,
        "eval_count": None,
    }


def _final_transport_failure(case, stage, wall_seconds, exc):
    parsed = parse_role_separated_tool_response(
        {"message": {"content": "", "tool_calls": []}}
    )
    return {
        "id": case["id"],
        "condition": CONTROL if stage == "control" else CANDIDATE,
        "stage": stage,
        **parsed,
        "wall_seconds": round(wall_seconds, 6),
        "transport_attempts": 1,
        "transport_error": f"{type(exc).__name__}: {exc}",
        "total_duration_ns": None,
        "load_duration_ns": None,
        "prompt_eval_count": None,
        "eval_count": None,
    }


def _call_stage1(config, case):
    if config["generation"]["transport_attempts"] != 1:
        raise ValueError("cascade experiment forbids transport retries")
    started = time.perf_counter()
    try:
        response = _post_json(
            config["local_runtime"]["endpoint"],
            build_stage1_request_body(config, case),
            config["generation"]["timeout_seconds"],
        )
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        return _stage1_transport_failure(
            case, time.perf_counter() - started, exc
        )
    return {
        "id": case["id"],
        "condition": CANDIDATE,
        "stage": "stage1",
        **parse_write_gate_tool_response(response),
        "wall_seconds": round(time.perf_counter() - started, 6),
        "transport_attempts": 1,
        "transport_error": None,
        **_response_metadata(response),
    }


def _call_final(config, case, stage):
    if stage not in {"control", "stage2"}:
        raise ValueError(f"invalid final-classifier stage: {stage}")
    if config["generation"]["transport_attempts"] != 1:
        raise ValueError("cascade experiment forbids transport retries")
    started = time.perf_counter()
    try:
        response = _post_json(
            config["local_runtime"]["endpoint"],
            build_final_request_body(config, case),
            config["generation"]["timeout_seconds"],
        )
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        return _final_transport_failure(
            case, stage, time.perf_counter() - started, exc
        )
    return {
        "id": case["id"],
        "condition": CONTROL if stage == "control" else CANDIDATE,
        "stage": stage,
        **parse_role_separated_tool_response(response),
        "wall_seconds": round(time.perf_counter() - started, 6),
        "transport_attempts": 1,
        "transport_error": None,
        **_response_metadata(response),
    }


def _frozen_paths(config):
    return {
        "preregistration": CONFIG_PATH,
        "dataset": ROOT / config["dataset"]["path"],
        "preregistration_test": (
            ROOT
            / "test_consolidation_admission_cascade_v1_preregistration.py"
        ),
        "model_screen_result_lock": (
            ROOT
            / "configs"
            / "consolidation_admission_model_screen_v1_result_lock.json"
        ),
        "v3_preregistration": (
            ROOT
            / "configs"
            / "consolidation_admission_v3_role_separated_development_preregistration.json"
        ),
        "v3_core": ROOT / "consolidation_admission_v3_role_separated_core.py",
        "runtime": ROOT / "uruha_brain_mac.py",
        "core": ROOT / "consolidation_admission_cascade_v1_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": (
            ROOT
            / "analyze_consolidation_admission_cascade_v1_development.py"
        ),
        "harness_test": (
            ROOT / "test_consolidation_admission_cascade_v1_harness.py"
        ),
    }


def verify(config, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("cascade experiment must run from main")
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
        raise ValueError("cascade harness lock is not committed")
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
        "schema": "uruha_consolidation_admission_cascade_raw_v1",
        "experiment_id": config["experiment_id"],
        "evidence_status": (
            "development_cascade_no_runtime_or_generalization_claim"
        ),
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "model_screen_result_lock_sha256": sha256(
            ROOT
            / "configs"
            / "consolidation_admission_model_screen_v1_result_lock.json"
        ),
        "model_snapshots": model_snapshots,
        "model_calls": 0,
        "transport_attempts_made": 0,
        "gold_fields_passed_to_model": False,
        "runtime_memory_write_performed": False,
        "control_rows": [],
        "stage1_rows": [],
        "stage2_rows": [],
        "inflight": None,
        "gate_snapshot": None,
    }


def _resume_report(output, config, model_snapshots):
    report = _load(output)
    if report.get("completed_at"):
        raise ValueError("completed cascade experiment cannot be rerun")
    for key, expected in {
        "experiment_id": config["experiment_id"],
        "runner_commit": git_value("rev-parse", "HEAD"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "model_screen_result_lock_sha256": sha256(
            ROOT
            / "configs"
            / "consolidation_admission_model_screen_v1_result_lock.json"
        ),
        "model_snapshots": model_snapshots,
    }.items():
        if report.get(key) != expected:
            raise ValueError(f"resume provenance drift: {key}")
    return report


def _validate_rows(rows, valid_ids, *, condition, stage):
    if not isinstance(rows, list):
        raise ValueError(f"resume {stage} rows are not a list")
    by_id = {}
    attempts = 0
    for row in rows:
        case_id = row.get("id")
        if case_id not in valid_ids:
            raise ValueError(f"resume {stage} contains an unknown case")
        if case_id in by_id:
            raise ValueError(f"resume {stage} contains duplicate rows")
        if row.get("condition") != condition:
            raise ValueError(f"resume {stage} condition drift")
        if row.get("stage") != stage:
            raise ValueError(f"resume {stage} stage drift")
        if row.get("transport_attempts") != 1:
            raise ValueError(f"resume {stage} transport attempt drift")
        by_id[case_id] = row
        attempts += 1
    return by_id, attempts


def _validate_report_progress(report, dataset):
    if report.get("inflight") is not None:
        raise ValueError(
            "resume has an ambiguous in-flight request; do not repeat it"
        )
    valid_ids = {case["id"] for case in dataset["cases"]}
    control, control_attempts = _validate_rows(
        report.get("control_rows"),
        valid_ids,
        condition=CONTROL,
        stage="control",
    )
    stage1, stage1_attempts = _validate_rows(
        report.get("stage1_rows"),
        valid_ids,
        condition=CANDIDATE,
        stage="stage1",
    )
    stage2, stage2_attempts = _validate_rows(
        report.get("stage2_rows"),
        valid_ids,
        condition=CANDIDATE,
        stage="stage2",
    )
    for case_id, row in stage1.items():
        if row.get("admission_decision") not in {"write", "none"}:
            raise ValueError("resume stage1 decision drift")
        if row["admission_decision"] == "none" and case_id in stage2:
            raise ValueError("resume stage2 exists after a closed gate")
    if not set(stage2) <= set(stage1):
        raise ValueError("resume stage2 exists without stage1")
    if any(stage1[case_id]["admission_decision"] != "write" for case_id in stage2):
        raise ValueError("resume stage2 exists without compiled write")

    total_rows = len(control) + len(stage1) + len(stage2)
    attempts = control_attempts + stage1_attempts + stage2_attempts
    if report.get("model_calls") != total_rows:
        raise ValueError("resume model call count drift")
    if report.get("transport_attempts_made") != attempts:
        raise ValueError("resume transport count drift")
    if report.get("gold_fields_passed_to_model"):
        raise ValueError("resume exposed gold fields")
    if report.get("runtime_memory_write_performed"):
        raise ValueError("resume performed a runtime memory write")
    if report.get("gate_snapshot") is not None:
        raise ValueError("incomplete resume already contains a gate snapshot")
    return {"control": control, "stage1": stage1, "stage2": stage2}


def _record_call(output, report, case, stage, call):
    report["inflight"] = {
        "id": case["id"],
        "stage": stage,
        "recorded_at": datetime.now(TZ).isoformat(timespec="seconds"),
    }
    _atomic_write(output, report)
    row = call()
    report[f"{stage}_rows"].append(row)
    report["model_calls"] += 1
    report["transport_attempts_made"] += row["transport_attempts"]
    report["inflight"] = None
    _atomic_write(output, report)
    return row


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
            if condition == CONTROL:
                if case["id"] in completed["control"]:
                    continue
                row = _record_call(
                    output,
                    report,
                    case,
                    "control",
                    lambda: _call_final(config, case, "control"),
                )
                completed["control"][case["id"]] = row
                continue

            if condition != CANDIDATE:
                raise ValueError(f"unknown condition: {condition}")
            if case["id"] not in completed["stage1"]:
                row = _record_call(
                    output,
                    report,
                    case,
                    "stage1",
                    lambda: _call_stage1(config, case),
                )
                completed["stage1"][case["id"]] = row
            stage1 = completed["stage1"][case["id"]]
            if (
                stage1["admission_decision"] == "write"
                and case["id"] not in completed["stage2"]
            ):
                row = _record_call(
                    output,
                    report,
                    case,
                    "stage2",
                    lambda: _call_final(config, case, "stage2"),
                )
                completed["stage2"][case["id"]] = row

    report["gate_snapshot"] = analyze_cascade(
        dataset["cases"],
        report["control_rows"],
        report["stage1_rows"],
        report["stage2_rows"],
        success_gates=config["success_gates"],
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
