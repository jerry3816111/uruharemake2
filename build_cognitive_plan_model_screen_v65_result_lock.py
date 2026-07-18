#!/usr/bin/env python3
"""Bind the immutable V65 negative-result evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "configs/cognitive_plan_model_screen_v65_result_lock.json"
ARTIFACTS = {
    "preregistration": "configs/cognitive_plan_model_screen_v65_preregistration.json",
    "dataset": "datasets/cognitive_plan_model_screen_v65.json",
    "dataset_closure": "configs/cognitive_plan_model_screen_v65_dataset_closure.json",
    "dataset_audit": "reports/cognitive_plan_model_screen_v65_dataset_audit.json",
    "harness_lock": "configs/cognitive_plan_model_screen_v65_harness_lock.json",
    "core": "cognitive_plan_model_screen_v65_core.py",
    "runner": "run_cognitive_plan_model_screen_v65.py",
    "analyzer": "analyze_cognitive_plan_model_screen_v65.py",
    "raw": "reports/cognitive_plan_model_screen_v65_raw.json",
    "analysis_json": "reports/cognitive_plan_model_screen_v65_analysis.json",
    "analysis_markdown": "reports/cognitive_plan_model_screen_v65_analysis.md",
    "diagnosis": "reports/cognitive_plan_model_screen_v65_diagnosis.md",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    analysis = json.loads((ROOT / ARTIFACTS["analysis_json"]).read_text(encoding="utf-8"))
    if analysis["selected_candidate"] is not None:
        raise ValueError("V65 result lock expected no selected candidate")
    if analysis["decision"] != "freeze_negative_result_and_stop_one_call_model_replacement":
        raise ValueError("V65 result lock expected the frozen negative decision")

    lock = {
        "schema": "uruha_cognitive_plan_model_screen_result_lock_v65",
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
            "production_model_replacement": False,
            "production_runtime_change": False,
            "broad_human_likeness_claim": False,
        },
        "next_question": (
            "On entirely fresh cases, does separating evidence and memory selection from "
            "epistemic policy and action selection improve exact cognitive-plan accuracy "
            "for qwen3.5:4b under preregistered latency and memory limits?"
        ),
    }
    OUTPUT.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
