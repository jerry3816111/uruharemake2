#!/usr/bin/env python3
"""Generate the immutable V65 harness lock."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import run_cognitive_plan_model_screen_v65 as runner


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "configs/cognitive_plan_model_screen_v65_harness_lock.json"
ARTIFACTS = {
    "preregistration": "configs/cognitive_plan_model_screen_v65_preregistration.json",
    "dataset_closure": "configs/cognitive_plan_model_screen_v65_dataset_closure.json",
    "dataset": "datasets/cognitive_plan_model_screen_v65.json",
    "dataset_auditor": "audit_cognitive_plan_model_screen_v65_dataset.py",
    "dataset_audit": "reports/cognitive_plan_model_screen_v65_dataset_audit.json",
    "dataset_test": "test_cognitive_plan_model_screen_v65_dataset.py",
    "core": "cognitive_plan_model_screen_v65_core.py",
    "runner": "run_cognitive_plan_model_screen_v65.py",
    "analyzer": "analyze_cognitive_plan_model_screen_v65.py",
    "harness_test": "test_cognitive_plan_model_screen_v65_harness.py"
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
    lock = {
        "schema": "uruha_cognitive_plan_model_screen_harness_lock_v65",
        "experiment_id": config["experiment_id"],
        "created_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
        "harness_parent_commit": "a84a482",
        "formal_inference_authorized_only_after_lock_merge": True,
        "conditions": config["condition_order"],
        "environment": {"system_prompt_sha256": hashlib.sha256(runner.SYSTEM_PROMPT.encode("utf-8")).hexdigest(), "tool_schema_sha256": hashlib.sha256(json.dumps(runner._tool_schema(config), sort_keys=True).encode("utf-8")).hexdigest()},
        "frozen_artifacts": {name: {"path": relative, "sha256": _sha256(ROOT / relative)} for name, relative in ARTIFACTS.items()},
        "preflight": {"arguments": ["-m", "unittest", "-q", "test_cognitive_plan_model_screen_v65_dataset.py", "test_cognitive_plan_model_screen_v65_harness.py"], "expected_test_count": 12, "must_pass_before_first_model_call": True},
        "formal_run": {"required_run_branch": "main", "required_head_ref": "origin/main", "clean_worktree_required": True, "formal_run_count_exact": 1, "candidate_inference_authorized": True, "warmup_call_count_exact": 3, "scored_model_call_count_exact": 36, "transport_attempt_count_exact": 39, "model_retry_authorized": False, "resume_authorized": False, "result_overwrite_authorized": False, "gold_or_expected_outcome_passed_to_model": False, "production_runtime_read_or_write_authorized": False, "physical_vrm_execution_authorized": False},
        "result_artifacts": {"raw": "reports/cognitive_plan_model_screen_v65_raw.json", "analysis_json": "reports/cognitive_plan_model_screen_v65_analysis.json", "analysis_markdown": "reports/cognitive_plan_model_screen_v65_analysis.md", "result_lock": "configs/cognitive_plan_model_screen_v65_result_lock.json"},
        "post_run_case_editing_authorized": False,
        "post_run_threshold_change_authorized": False,
        "human_review_authorized": False,
        "runtime_change_authorized": False,
        "broad_human_likeness_claim_authorized": False,
        "decision_boundary": "A selected candidate authorizes only a separate fresh runtime shadow experiment, never direct model replacement."
    }
    OUTPUT.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
