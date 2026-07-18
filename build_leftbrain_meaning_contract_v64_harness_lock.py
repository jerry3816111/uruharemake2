#!/usr/bin/env python3
"""Generate the V64 immutable harness lock after implementation review."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import run_leftbrain_meaning_contract_v64 as runner


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "configs/leftbrain_meaning_contract_v64_harness_lock.json"
ARTIFACTS = {
    "preregistration": "configs/leftbrain_meaning_contract_v64_preregistration.json",
    "dataset_closure": "configs/leftbrain_meaning_contract_v64_dataset_closure.json",
    "dataset": "datasets/leftbrain_meaning_contract_v64.json",
    "dataset_auditor": "audit_leftbrain_meaning_contract_v64_dataset.py",
    "dataset_audit": "reports/leftbrain_meaning_contract_v64_dataset_audit.json",
    "dataset_test": "test_leftbrain_meaning_contract_v64_dataset.py",
    "runner": "run_leftbrain_meaning_contract_v64.py",
    "analyzer": "analyze_leftbrain_meaning_contract_v64.py",
    "harness_test": "test_leftbrain_meaning_contract_v64_harness.py",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lock = {
        "schema": "uruha_leftbrain_meaning_contract_harness_lock_v64",
        "experiment_id": "leftbrain_meaning_contract_v64",
        "created_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
        "harness_parent_commit": "5aa121c",
        "formal_inference_authorized_only_after_lock_merge": True,
        "conditions": list(runner.CONDITIONS),
        "environment": {
            "base_prompt_sha256": hashlib.sha256(runner.BASE_PROMPT.encode("utf-8")).hexdigest(),
            "control_schema_sha256": hashlib.sha256(runner.COMMON_SCHEMA.encode("utf-8")).hexdigest(),
            "treatment_schema_sha256": hashlib.sha256(runner.STRUCTURED_SCHEMA.encode("utf-8")).hexdigest(),
        },
        "frozen_artifacts": {
            name: {"path": relative, "sha256": _sha256(ROOT / relative)}
            for name, relative in ARTIFACTS.items()
        },
        "preflight": {
            "arguments": [
                "-m", "unittest", "-q",
                "test_leftbrain_meaning_contract_v64_dataset.py",
                "test_leftbrain_meaning_contract_v64_harness.py",
            ],
            "expected_test_count": 12,
            "must_pass_before_first_model_call": True,
        },
        "formal_run": {
            "required_run_branch": "main",
            "clean_worktree_required": True,
            "formal_run_count_exact": 1,
            "candidate_inference_authorized": True,
            "model_call_count_exact": 28,
            "transport_attempt_count_exact": 28,
            "model_retry_authorized": False,
            "model_repair_call_authorized": False,
            "resume_authorized": False,
            "result_overwrite_authorized": False,
            "gold_or_expected_outcome_passed_to_model": False,
            "production_runtime_read_or_write_authorized": False,
            "physical_vrm_execution_authorized": False,
        },
        "statistics": {
            "bootstrap_samples": 10000,
            "case_order": "dataset_order",
            "condition_order": list(runner.CONDITIONS),
        },
        "result_artifacts": {
            "raw": "reports/leftbrain_meaning_contract_v64_raw.json",
            "analysis_json": "reports/leftbrain_meaning_contract_v64_analysis.json",
            "analysis_markdown": "reports/leftbrain_meaning_contract_v64_analysis.md",
            "result_lock": "configs/leftbrain_meaning_contract_v64_result_lock.json",
        },
        "post_run_case_editing_authorized": False,
        "post_run_threshold_change_authorized": False,
        "human_review_authorized": False,
        "runtime_change_authorized": False,
        "broad_human_likeness_claim_authorized": False,
        "decision_boundary": "A passing V64 pilot authorizes only a separate fresh-data RightBrain realization pilot, never a production change.",
    }
    OUTPUT.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
