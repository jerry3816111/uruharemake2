#!/usr/bin/env python3
"""Run the frozen V67 memory-validity component pilot exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_memory_runtime as memory_runtime
from uruha_memory_validity import resolve_memory_validity


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
PREREG_PATH = ROOT / "configs/memory_validity_resolution_v67_preregistration.json"
DATASET_PATH = ROOT / "datasets/memory_validity_resolution_v67.json"
CLOSURE_PATH = ROOT / "configs/memory_validity_resolution_v67_dataset_closure.json"
LOCK_PATH = ROOT / "configs/memory_validity_resolution_v67_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/memory_validity_resolution_v67_raw.json"
CONDITIONS = ("current_all_candidates_eligible_control", "generic_validity_resolver_treatment")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_tree_clean():
    unstaged = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=False).returncode == 0
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False).returncode == 0
    return unstaged and staged


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _ids(items):
    return [str(item.get("memory_id")) for item in items]


def control_partition(candidates):
    return {
        "eligible_candidates": [dict(item) for item in candidates],
        "historical_candidates": [],
        "inapplicable_candidates": [],
        "decisions": {
            str(item.get("memory_id")): {"partition": "eligible", "reason": "current_no_validity_gate"}
            for item in candidates
        },
    }


def _working_memory(case, candidates):
    context = case["query_context"]
    return memory_runtime.build_working_memory(
        context["query_text"],
        candidates,
        working_memory_limit=case["working_memory_limit"],
        reference_time=datetime.fromisoformat(context["reference_time"]),
        scoring_profile="v2",
    )


def run_case(case, condition):
    context = case["query_context"]
    if condition == CONDITIONS[0]:
        partition = control_partition(case["candidates"])
        resolver_seconds = 0.0
    elif condition == CONDITIONS[1]:
        started = time.perf_counter_ns()
        partition = resolve_memory_validity(
            case["candidates"],
            reference_time=context["reference_time"],
            condition_tags=context["condition_tags"],
        )
        resolver_seconds = (time.perf_counter_ns() - started) / 1_000_000_000
    else:
        raise ValueError(f"Unknown condition: {condition}")

    working = _working_memory(case, partition["eligible_candidates"])
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "condition": condition,
        "eligible_ids": _ids(partition["eligible_candidates"]),
        "historical_ids": _ids(partition["historical_candidates"]),
        "inapplicable_ids": _ids(partition["inapplicable_candidates"]),
        "working_memory_ids": _ids(working),
        "decisions": partition["decisions"],
        "resolver_seconds": resolver_seconds,
    }


def benchmark_resolver(case, *, warmup_iterations, scored_iterations):
    context = case["query_context"]
    kwargs = {
        "reference_time": context["reference_time"],
        "condition_tags": context["condition_tags"],
    }
    for _ in range(warmup_iterations):
        resolve_memory_validity(case["candidates"], **kwargs)
    started = time.perf_counter_ns()
    for _ in range(scored_iterations):
        resolve_memory_validity(case["candidates"], **kwargs)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000_000
    return elapsed / scored_iterations


def verify_lock(lock):
    failures = []
    for name, artifact in lock["frozen_artifacts"].items():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failures.append(f"artifact_drift:{name}")
    return failures


def preflight(output_path, *, formal):
    lock = _load(LOCK_PATH)
    failures = verify_lock(lock)
    if formal:
        if not lock["formal_run"]["pilot_execution_authorized"]:
            failures.append("pilot_not_authorized")
        if not _tracked_tree_clean():
            failures.append("dirty_tracked_tree")
        if _git("branch", "--show-current") != lock["formal_run"]["required_run_branch"]:
            failures.append("wrong_branch")
        if _git("rev-parse", "HEAD") != _git("rev-parse", lock["formal_run"]["required_head_ref"]):
            failures.append("head_not_origin_main")
        if output_path.exists():
            failures.append("result_already_exists")
    return lock, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    lock, failures = preflight(args.output, formal=not args.preflight_only)
    if failures:
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        raise SystemExit(1)
    if args.preflight_only:
        print(json.dumps({"passed": True, "failures": []}, indent=2))
        return

    preflight_test = subprocess.run(
        [sys.executable, *lock["preflight"]["arguments"]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if preflight_test.returncode:
        print(preflight_test.stdout)
        print(preflight_test.stderr, file=sys.stderr)
        raise SystemExit("V67 preflight tests failed")

    dataset = _load(DATASET_PATH)
    timing = lock["formal_run"]["timing"]
    rows = []
    for case in dataset["cases"]:
        for condition in CONDITIONS:
            rows.append(run_case(case, condition))
        rows[-1]["resolver_seconds"] = benchmark_resolver(
            case,
            warmup_iterations=timing["warmup_iterations_per_case"],
            scored_iterations=timing["scored_iterations_per_case"],
        )

    raw = {
        "schema": "uruha_memory_validity_resolution_raw_v67",
        "experiment_id": "memory_validity_resolution_v67",
        "run_started_at": datetime.now(TZ).isoformat(),
        "git_head": _git("rev-parse", "HEAD"),
        "conditions": list(CONDITIONS),
        "case_count": len(dataset["cases"]),
        "row_count": len(rows),
        "warmup_iterations_per_case": timing["warmup_iterations_per_case"],
        "scored_iterations_per_case": timing["scored_iterations_per_case"],
        "gold_in_raw": False,
        "language_model_inference": False,
        "production_runtime_changed": False,
        "production_memory_read_or_write": False,
        "rows": rows,
    }
    _atomic_write(args.output, raw)
    print(json.dumps({"output": str(args.output), "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
