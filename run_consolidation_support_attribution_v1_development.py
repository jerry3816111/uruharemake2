#!/usr/bin/env python3
"""Run the frozen consolidation support-attribution V1 pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from consolidation_support_attribution_v1_core import (
    analyze_support_attribution,
    build_coarse_control_rows,
    parse_support_tool_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_support_attribution_v1_development_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


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
        ["ollama", "--version"],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()
    prefix = "ollama version is "
    if not output.startswith(prefix):
        raise ValueError(f"unexpected Ollama version: {output}")
    return output.removeprefix(prefix)


def _model_snapshot(config):
    inventory = {
        row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])
    }
    frozen = config["model"]
    row = inventory.get(frozen["ollama_tag"])
    if not row or row.get("digest") != frozen["digest"]:
        raise ValueError("missing or drifted local attribution model")
    return {
        "ollama_tag": frozen["ollama_tag"],
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def render_case(config, case):
    lines = [
        f"Derived memory ({case['memory_kind']}):",
        case["derived_memory"],
        "",
        "Chronological source events:",
    ]
    template = config["fixed_contract"]["event_rendering"]
    for event in case["source_events"]:
        lines.append(
            template.format(
                index=event["index"],
                user=event["user"],
                assistant=event["assistant"],
            )
        )
    return "\n".join(lines)


def build_request_body(config, case):
    generation = config["generation"]
    contract = config["fixed_contract"]
    return {
        "model": config["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": contract["system_prompt"]},
            {"role": "user", "content": render_case(config, case)},
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


def _transport_failure(case, wall_seconds, exc):
    parsed = parse_support_tool_response(
        {"message": {"content": "", "tool_calls": []}}
    )
    return {
        "id": case["id"],
        "condition": "qwen35_4b_support_attribution",
        **parsed,
        "wall_seconds": round(wall_seconds, 6),
        "transport_attempts": 1,
        "transport_error": f"{type(exc).__name__}: {exc}",
        "total_duration_ns": None,
        "load_duration_ns": None,
        "prompt_eval_count": None,
        "eval_count": None,
    }


def _call_candidate(config, case):
    if config["generation"]["transport_attempts"] != 1:
        raise ValueError("attribution pilot forbids transport retries")
    started = time.perf_counter()
    try:
        response = _post_json(
            config["local_runtime"]["endpoint"],
            build_request_body(config, case),
            config["generation"]["timeout_seconds"],
        )
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        return _transport_failure(
            case,
            time.perf_counter() - started,
            exc,
        )
    return {
        "id": case["id"],
        "condition": "qwen35_4b_support_attribution",
        **parse_support_tool_response(response),
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
        "core": ROOT / "consolidation_support_attribution_v1_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": (
            ROOT
            / "analyze_consolidation_support_attribution_v1_development.py"
        ),
        "preregistration_test": (
            ROOT
            / "test_consolidation_support_attribution_v1_preregistration.py"
        ),
        "harness_test": (
            ROOT / "test_consolidation_support_attribution_v1_harness.py"
        ),
    }


def verify(config, lock):
    if _git("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("pilot must run from main")
    if _git("rev-parse", "HEAD") != _git(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if _git("status", "--porcelain", "--untracked-files=no"):
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
        raise ValueError("harness lock is not committed")
    if _ollama_version() != config["local_runtime"]["ollama_version"]:
        raise ValueError("Ollama version drift")
    for name, path in _frozen_paths(config).items():
        if _sha256(path) != lock["frozen_artifacts"][f"{name}_sha256"]:
            raise ValueError(f"frozen artifact drift: {name}")
    if config["model_inference_before_harness_merge_authorized"]:
        raise ValueError("invalid preregistration inference policy")


def _new_report(config, dataset, model_snapshot):
    return {
        "schema": "uruha_consolidation_support_attribution_raw_v1",
        "experiment_id": config["experiment_id"],
        "evidence_status": "development_only_no_runtime_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": _git("rev-parse", "HEAD"),
        "runner_branch": _git("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "harness_lock_sha256": _sha256(LOCK_PATH),
        "dataset_sha256": _sha256(ROOT / config["dataset"]["path"]),
        "model_snapshot": model_snapshot,
        "model_calls": 0,
        "transport_attempts_made": 0,
        "gold_fields_passed_to_model": False,
        "runtime_memory_write_performed": False,
        "control_rows": build_coarse_control_rows(dataset["cases"]),
        "candidate_rows": [],
        "inflight": None,
        "gate_snapshot": None,
    }


def _validate_report_progress(report, dataset):
    expected_ids = [case["id"] for case in dataset["cases"]]
    candidate_rows = report.get("candidate_rows")
    if not isinstance(candidate_rows, list):
        raise ValueError("candidate rows are missing")
    observed_ids = [row.get("id") for row in candidate_rows]
    if observed_ids != expected_ids[: len(observed_ids)]:
        raise ValueError("candidate rows are not a unique dataset prefix")
    if any(
        row.get("condition") != "qwen35_4b_support_attribution"
        for row in candidate_rows
    ):
        raise ValueError("candidate condition drift")
    if any(
        row.get("transport_attempts") != 1 for row in candidate_rows
    ):
        raise ValueError("transport attempt drift")
    if report.get("model_calls") != len(candidate_rows):
        raise ValueError("model call count drift")
    if report.get("transport_attempts_made") != sum(
        row["transport_attempts"] for row in candidate_rows
    ):
        raise ValueError("transport attempt count drift")
    if report.get("control_rows") != build_coarse_control_rows(
        dataset["cases"]
    ):
        raise ValueError("coarse control drift")


def _resume_report(output, config, model_snapshot, dataset):
    report = _load(output)
    if report.get("completed_at"):
        raise ValueError("completed pilot cannot be rerun")
    if report.get("inflight") is not None:
        raise ValueError(
            "ambiguous in-flight request; do not repeat model inference"
        )
    expected = {
        "experiment_id": config["experiment_id"],
        "runner_commit": _git("rev-parse", "HEAD"),
        "runner_branch": _git("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "harness_lock_sha256": _sha256(LOCK_PATH),
        "dataset_sha256": _sha256(ROOT / config["dataset"]["path"]),
        "model_snapshot": model_snapshot,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError(f"resume provenance drift: {key}")
    _validate_report_progress(report, dataset)
    return report


def run(output):
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    dataset = _load(ROOT / config["dataset"]["path"])
    verify(config, lock)
    model_snapshot = _model_snapshot(config)
    report = (
        _resume_report(output, config, model_snapshot, dataset)
        if output.exists()
        else _new_report(config, dataset, model_snapshot)
    )
    completed_ids = {row["id"] for row in report["candidate_rows"]}
    if len(completed_ids) != len(report["candidate_rows"]):
        raise ValueError("duplicate candidate rows")

    for case in dataset["cases"]:
        if case["id"] in completed_ids:
            continue
        report["inflight"] = {
            "id": case["id"],
            "condition": "qwen35_4b_support_attribution",
        }
        _atomic_write(output, report)
        row = _call_candidate(config, case)
        report["candidate_rows"].append(row)
        report["model_calls"] += 1
        report["transport_attempts_made"] += row["transport_attempts"]
        report["inflight"] = None
        _atomic_write(output, report)

    if len(report["candidate_rows"]) != config["run_invariants"][
        "model_call_count_exact"
    ]:
        raise ValueError("candidate row count drift")
    analysis = analyze_support_attribution(
        dataset["cases"],
        report["control_rows"],
        report["candidate_rows"],
        config["success_gates"],
    )
    report["gate_snapshot"] = analysis
    report["completed_at"] = datetime.now(TZ).isoformat(
        timespec="seconds"
    )
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    candidate = report["gate_snapshot"]["candidate"]
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "model_calls": report["model_calls"],
                "exact_set_match": (
                    f"{candidate['exact_set_match_count']}/"
                    f"{candidate['case_count']}"
                ),
                "precision": candidate["evidence_precision"],
                "recall": candidate["evidence_recall"],
                "all_success_gates_pass": report["gate_snapshot"][
                    "all_success_gates_pass"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
