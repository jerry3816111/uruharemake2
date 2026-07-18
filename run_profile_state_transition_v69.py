#!/usr/bin/env python3
"""Run the frozen V69 cross-session profile-state shadow once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import chromadb

from uruha_brain_mac import MemoryManager
from uruha_memory_validity import resolve_memory_validity
from uruha_profile_memory import compile_profile_memory_record, read_profile_candidates


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
PREREG_PATH = ROOT / "configs/profile_state_transition_v69_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_state_transition_v69.json"
CLOSURE_PATH = ROOT / "configs/profile_state_transition_v69_dataset_closure.json"
LOCK_PATH = ROOT / "configs/profile_state_transition_v69_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/profile_state_transition_v69_raw.json"
CONDITIONS = (
    "current_session_only_reference",
    "matched_append_only_readback_control",
    "typed_state_resolution_treatment",
)
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


def _extract_records(case):
    records = []
    for turn in case["turns"]:
        facts = EXTRACTOR._extract_profile_facts(turn["utterance"])
        for index, (fact_type, value) in enumerate(facts):
            memory_id = turn["turn_id"] if index == 0 else f"{turn['turn_id']}:{index}"
            records.append(
                {
                    "memory_id": memory_id,
                    "fact_type": fact_type,
                    "value": value,
                    "timestamp": turn["timestamp"],
                }
            )
    return records


def _compile_records(records, *, typed_state):
    return [
        compile_profile_memory_record(
            row["fact_type"],
            row["value"],
            timestamp=row["timestamp"],
            memory_id=row["memory_id"],
            typed_state=typed_state,
        )
        for row in records
    ]


def _as_candidates(compiled):
    return [
        {
            "memory_id": row["memory_id"],
            "text": row["document"],
            "metadata": dict(row["metadata"]),
            "source": "profile",
            "collection_name": "profile",
            "distance": None,
        }
        for row in compiled
    ]


def _reference_time(case):
    return max(turn["timestamp"] for turn in case["turns"])


def _partition(candidates, reference_time):
    resolved = resolve_memory_validity(candidates, reference_time=reference_time)
    return {
        "active_ids": [row["memory_id"] for row in resolved["eligible_candidates"]],
        "historical_ids": [row["memory_id"] for row in resolved["historical_candidates"]],
        "inapplicable_ids": [row["memory_id"] for row in resolved["inapplicable_candidates"]],
        "decisions": resolved["decisions"],
    }


def benchmark_state(case, condition, *, warmup_iterations, scored_iterations):
    records = _extract_records(case)
    typed_state = condition == CONDITIONS[2]

    def operation():
        compiled = _compile_records(records, typed_state=typed_state)
        return _partition(_as_candidates(compiled), _reference_time(case))

    for _ in range(warmup_iterations):
        operation()
    started = time.perf_counter_ns()
    for _ in range(scored_iterations):
        operation()
    return (time.perf_counter_ns() - started) / 1_000_000_000 / scored_iterations


def run_case(case, condition, *, temp_root):
    records = _extract_records(case)
    typed_state = condition == CONDITIONS[2]
    compiled = _compile_records(records, typed_state=typed_state)
    path = Path(temp_root) / f"{case['id']}_{condition}"
    client = chromadb.PersistentClient(path=str(path))
    collection = client.get_or_create_collection("v69_profile_shadow")
    if compiled:
        collection.add(
            ids=[row["memory_id"] for row in compiled],
            documents=[row["document"] for row in compiled],
            metadatas=[row["metadata"] for row in compiled],
        )
    candidates = read_profile_candidates(collection)
    if condition == CONDITIONS[0]:
        partition = {
            "active_ids": [],
            "historical_ids": [],
            "inapplicable_ids": [],
            "decisions": {},
        }
    else:
        partition = _partition(candidates, _reference_time(case))
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "language": case["language"],
        "condition": condition,
        "extracted_records": records,
        "persisted_ids": [row["memory_id"] for row in candidates],
        "persisted_documents": [row["text"] for row in candidates],
        "active_ids": partition["active_ids"],
        "historical_ids": partition["historical_ids"],
        "inapplicable_ids": partition["inapplicable_ids"],
        "decisions": partition["decisions"],
        "temporary_chroma": True,
    }


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
        formal_run = lock["formal_run"]
        if not formal_run["shadow_execution_authorized"]:
            failures.append("shadow_not_authorized")
        if not formal_run["temporary_chroma_access_authorized"]:
            failures.append("temporary_chroma_not_authorized")
        if formal_run["production_database_access_authorized"]:
            failures.append("production_database_access_must_remain_forbidden")
        if not _tracked_tree_clean():
            failures.append("dirty_tracked_tree")
        if _git("branch", "--show-current") != formal_run["required_run_branch"]:
            failures.append("wrong_branch")
        if _git("rev-parse", "HEAD") != _git("rev-parse", formal_run["required_head_ref"]):
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
        raise SystemExit("V69 preflight tests failed")

    dataset = _load(DATASET_PATH)
    timing = lock["formal_run"]["timing"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="uruha_v69_profile_shadow_") as temp_root:
        for source_case in dataset["cases"]:
            case = {
                "id": source_case["id"],
                "scenario_family": source_case["scenario_family"],
                "language": source_case["language"],
                "turns": list(source_case["turns"]),
            }
            for condition in CONDITIONS:
                row = run_case(case, condition, temp_root=temp_root)
                row["state_seconds"] = 0.0
                if condition != CONDITIONS[0]:
                    row["state_seconds"] = benchmark_state(
                        case,
                        condition,
                        warmup_iterations=timing["warmup_iterations_per_case"],
                        scored_iterations=timing["scored_iterations_per_case"],
                    )
                rows.append(row)
    raw = {
        "schema": "uruha_profile_state_transition_raw_v69",
        "experiment_id": "profile_state_transition_v69",
        "run_started_at": datetime.now(TZ).isoformat(),
        "git_head": _git("rev-parse", "HEAD"),
        "conditions": list(CONDITIONS),
        "case_count": len(dataset["cases"]),
        "row_count": len(rows),
        "gold_in_raw": False,
        "language_model_inference": False,
        "production_runtime_changed": False,
        "production_database_access": False,
        "temporary_chroma_access": True,
        "warmup_iterations_per_case": timing["warmup_iterations_per_case"],
        "scored_iterations_per_case": timing["scored_iterations_per_case"],
        "rows": rows,
    }
    _atomic_write(args.output, raw)
    print(json.dumps({"output": str(args.output), "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
