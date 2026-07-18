#!/usr/bin/env python3
"""Bind the immutable V66 negative-result evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "configs/cognitive_plan_decomposition_v66_result_lock.json"
ARTIFACTS = {
    "preregistration": "configs/cognitive_plan_decomposition_v66_preregistration.json",
    "dataset": "datasets/cognitive_plan_decomposition_v66.json",
    "dataset_closure": "configs/cognitive_plan_decomposition_v66_dataset_closure.json",
    "dataset_audit": "reports/cognitive_plan_decomposition_v66_dataset_audit.json",
    "harness_lock": "configs/cognitive_plan_decomposition_v66_harness_lock.json",
    "core": "cognitive_plan_decomposition_v66_core.py",
    "runner": "run_cognitive_plan_decomposition_v66.py",
    "analyzer": "analyze_cognitive_plan_decomposition_v66.py",
    "raw": "reports/cognitive_plan_decomposition_v66_raw.json",
    "analysis_json": "reports/cognitive_plan_decomposition_v66_analysis.json",
    "analysis_markdown": "reports/cognitive_plan_decomposition_v66_analysis.md",
    "diagnosis": "reports/cognitive_plan_decomposition_v66_diagnosis.md",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    analysis = json.loads((ROOT / ARTIFACTS["analysis_json"]).read_text(encoding="utf-8"))
    expected_decision = "freeze_result_and_stop_fixed_two_stage_decomposition_as_sufficient_solution"
    if analysis["decision"] != expected_decision:
        raise ValueError("V66 result lock expected the frozen negative decision")
    if analysis["pairwise"]["treatment_vs_matched_control"]["eligible"]:
        raise ValueError("V66 result lock cannot authorize an eligible treatment")

    lock = {
        "schema": "uruha_cognitive_plan_decomposition_result_lock_v66",
        "created_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
        "decision": analysis["decision"],
        "frozen_artifacts": {
            name: {"path": relative, "sha256": _sha256(ROOT / relative)}
            for name, relative in ARTIFACTS.items()
        },
        "authorizations": {
            "same_case_rerun": False,
            "gold_edit": False,
            "threshold_edit": False,
            "fixed_two_stage_production_change": False,
            "adaptive_router_from_current_families": False,
            "production_runtime_change": False,
            "broad_human_likeness_claim": False,
        },
        "next_question": (
            "On entirely fresh multi-session cases, does an explicit production-compatible memory "
            "state transition distinguish current, superseded, private, and shareable records better "
            "than the existing memory policy without reducing valid recall?"
        ),
    }
    OUTPUT.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
