#!/usr/bin/env python3
"""Run the frozen V68 profile assertion-boundary pilot once."""

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

from uruha_brain_mac import MemoryManager
from uruha_profile_assertion import (
    classify_profile_assertion_scope,
    filter_profile_facts_by_assertion_scope,
)


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
PREREG_PATH = ROOT / "configs/profile_assertion_boundary_v68_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_assertion_boundary_v68.json"
CLOSURE_PATH = ROOT / "configs/profile_assertion_boundary_v68_dataset_closure.json"
LOCK_PATH = ROOT / "configs/profile_assertion_boundary_v68_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/profile_assertion_boundary_v68_raw.json"
CONDITIONS = ("current_unguarded_extractor_control", "assertion_scope_guard_treatment")
EXTRACTOR = object.__new__(MemoryManager)


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


def extract_current_facts(utterance):
    return EXTRACTOR._extract_profile_facts(utterance)


def _serialize_facts(facts):
    return [{"fact_type": fact_type, "value": value} for fact_type, value in facts]


def run_case(case, condition):
    extracted = extract_current_facts(case["utterance"])
    if condition == CONDITIONS[0]:
        observed = extracted
        decision = {"allow": True, "reason": "current_no_assertion_guard"}
        guard_seconds = 0.0
    elif condition == CONDITIONS[1]:
        started = time.perf_counter_ns()
        observed = filter_profile_facts_by_assertion_scope(case["utterance"], extracted)
        guard_seconds = (time.perf_counter_ns() - started) / 1_000_000_000
        decision = classify_profile_assertion_scope(case["utterance"], extracted)
    else:
        raise ValueError(f"Unknown condition: {condition}")
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "language": case["language"],
        "condition": condition,
        "observed_facts": _serialize_facts(observed),
        "scope_decision": decision,
        "guard_seconds": guard_seconds,
    }


def benchmark_guard(case, *, warmup_iterations, scored_iterations):
    extracted = extract_current_facts(case["utterance"])
    for _ in range(warmup_iterations):
        filter_profile_facts_by_assertion_scope(case["utterance"], extracted)
    started = time.perf_counter_ns()
    for _ in range(scored_iterations):
        filter_profile_facts_by_assertion_scope(case["utterance"], extracted)
    return (time.perf_counter_ns() - started) / 1_000_000_000 / scored_iterations


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

    completed = subprocess.run(
        [sys.executable, *lock["preflight"]["arguments"]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit("V68 preflight tests failed")

    dataset = _load(DATASET_PATH)
    timing = lock["formal_run"]["timing"]
    rows = []
    for case in dataset["cases"]:
        for condition in CONDITIONS:
            rows.append(run_case(case, condition))
        rows[-1]["guard_seconds"] = benchmark_guard(
            case,
            warmup_iterations=timing["warmup_iterations_per_case"],
            scored_iterations=timing["scored_iterations_per_case"],
        )
    raw = {
        "schema": "uruha_profile_assertion_boundary_raw_v68",
        "experiment_id": "profile_assertion_boundary_v68",
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
        "persistent_memory_read_or_write": False,
        "rows": rows,
    }
    _atomic_write(args.output, raw)
    print(json.dumps({"output": str(args.output), "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
