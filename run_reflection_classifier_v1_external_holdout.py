#!/usr/bin/env python3
"""Run frozen legacy and candidate classifiers on the same external holdout."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import reflection_classifier_v1_legacy as legacy
import uruha_reflection_runtime as candidate
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json"
LOCK_PATH = ROOT / "configs" / "reflection_classifier_v1_external_holdout_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_classifier_v1_external_holdout_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("external holdout must run from main")
    if git_value("rev-parse", "HEAD") != git_value(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    for relative, expected in lock["frozen_artifacts"].items():
        if not relative.endswith("_sha256"):
            continue
        path_key = relative.removesuffix("_sha256")
        if sha256(ROOT / lock["frozen_artifacts"][path_key]) != expected:
            raise ValueError(f"frozen artifact drift: {path_key}")


def run(output=DEFAULT_OUTPUT):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite raw holdout result: {output}")
    lock = _load(LOCK_PATH)
    verify(lock)
    dataset = _load(DATASET_PATH)
    rows = []
    for case in dataset["cases"]:
        text = case["text"]
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "legacy_observed_type": legacy.classify_reflection_type(text),
                "candidate_observed_type": candidate.classify_reflection_type(text),
            }
        )
    report = {
        "schema": "uruha_reflection_classifier_external_holdout_raw_v1",
        "evidence_status": "matched_predictions_without_post_run_tuning",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "dataset_sha256": sha256(DATASET_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "legacy_classifier_sha256": sha256(ROOT / "reflection_classifier_v1_legacy.py"),
        "candidate_classifier_sha256": sha256(ROOT / "uruha_reflection_runtime.py"),
        "case_count": len(rows),
        "model_calls": 0,
        "gold_label_passed_to_classifier": False,
        "rows": rows,
    }
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
