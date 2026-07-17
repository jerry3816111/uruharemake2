#!/usr/bin/env python3
"""Collect the frozen legacy reflection classifier baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_reflection_runtime as reflection
from reflection_classifier_v1_core import score_predictions, summarize


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_classifier_v1_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "reflection_classifier_v1_development.json"
LOCK_PATH = ROOT / "configs" / "reflection_classifier_v1_baseline_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_classifier_v1_legacy_baseline.json"
TZ = ZoneInfo("Asia/Tokyo")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def verify(config, dataset, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("baseline must run from main")
    if git_value("rev-parse", "HEAD") != git_value(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    if len(dataset["cases"]) != config["case_count"]:
        raise ValueError("case count drift")
    for relative, expected in lock["frozen_artifacts"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"frozen artifact drift: {relative}")


def run(output=DEFAULT_OUTPUT):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite baseline: {output}")
    config = load_json(CONFIG_PATH)
    dataset = load_json(DATASET_PATH)
    lock = load_json(LOCK_PATH)
    verify(config, dataset, lock)
    predictions = {
        case["id"]: reflection.classify_reflection_type(case["text"])
        for case in dataset["cases"]
    }
    rows = score_predictions(dataset["cases"], predictions)
    report = {
        "schema": "uruha_reflection_classifier_legacy_baseline_v1",
        "evidence_status": "legacy_baseline_frozen_before_candidate_implementation",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "classifier_sha256": sha256(ROOT / "uruha_reflection_runtime.py"),
        "model_calls": 0,
        "summary": summarize(rows),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
