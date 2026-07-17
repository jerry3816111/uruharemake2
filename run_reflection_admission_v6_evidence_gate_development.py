#!/usr/bin/env python3
"""Run the frozen V6 reflection-admission evidence-gate pilot."""

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

from reflection_admission_v6_core import (
    analyze_admission_condition,
    parse_admission_tool_response,
)
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_evidence_gate_development_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "reflection_admission_v6_evidence_gate_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "reflection_admission_v6_evidence_gate_development_raw.json"
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


def _call_model(config, case):
    generation = config["generation"]
    body = {
        "model": config["model"]["name"],
        "messages": [
            {"role": "system", "content": config["system_prompt"]},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "language": case["language"],
                        "utterance": case["text"],
                        "proposal": config["proposal_under_review"],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "tools": [config["tool_contract"]],
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
            (
                decision,
                parsed,
                evidence_contract,
                content,
                tool_calls,
                parse_error,
            ) = parse_admission_tool_response(response, case["text"])
            raw_admission = None if decision is None else decision["admission"]
            observed = (
                raw_admission
                if parsed and evidence_contract and raw_admission is not None
                else "reject"
            )
            return {
                "raw_admission": raw_admission,
                "observed_admission": observed,
                "evidence_span": (
                    None if decision is None else decision["evidence_span"]
                ),
                "reason_code": (
                    None if decision is None else decision["reason_code"]
                ),
                "parse_success": parsed,
                "evidence_contract_success": evidence_contract,
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
        "construction_closure": ROOT / config["construction_closure"]["path"],
        "dataset": ROOT / config["dataset"]["path"],
        "core": ROOT / "reflection_admission_v6_core.py",
        "runner": Path(__file__).resolve(),
        "analyzer": ROOT
        / "analyze_reflection_admission_v6_evidence_gate_development.py",
    }


def verify(config, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("admission pilot must run from main")
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
        raise ValueError("admission harness lock is not committed")
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
        "schema": "uruha_reflection_admission_evidence_gate_development_raw_v6",
        "evidence_status": "development_pilot_no_runtime_or_generalization_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "construction_closure_sha256": sha256(
            ROOT / config["construction_closure"]["path"]
        ),
        "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        "model_snapshot": model_snapshot,
        "model_calls": 0,
        "gold_label_passed_to_model": False,
        "runtime_memory_write_performed": False,
        "candidate_rows": [],
        "gate_snapshot": None,
    }


def run(output=DEFAULT_OUTPUT):
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    verify(config, lock)
    dataset = _load(ROOT / config["dataset"]["path"])
    model_snapshot = _model_snapshot(config)

    if output.exists():
        report = _load(output)
        if report.get("completed_at"):
            raise ValueError("completed pilot cannot be rerun")
        for key, expected in {
            "runner_commit": git_value("rev-parse", "HEAD"),
            "ollama_version": _ollama_version(),
            "preregistration_sha256": sha256(CONFIG_PATH),
            "harness_lock_sha256": sha256(LOCK_PATH),
            "dataset_sha256": sha256(ROOT / config["dataset"]["path"]),
        }.items():
            if report.get(key) != expected:
                raise ValueError(f"resume provenance drift: {key}")
    else:
        report = _new_report(config, model_snapshot)
        _atomic_write(output, report)

    completed_ids = {row["id"] for row in report["candidate_rows"]}
    for case in dataset["cases"]:
        if case["id"] in completed_ids:
            continue
        called = _call_model(config, case)
        report["candidate_rows"].append({"id": case["id"], **called})
        report["model_calls"] += 1
        _atomic_write(output, report)

    report["gate_snapshot"] = analyze_admission_condition(
        dataset["cases"], report["candidate_rows"], config["success_gates"]
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
