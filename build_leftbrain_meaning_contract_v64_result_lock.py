#!/usr/bin/env python3
"""Bind the immutable V64 negative-result evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "configs/leftbrain_meaning_contract_v64_result_lock.json"
ARTIFACTS = {
    "preregistration": "configs/leftbrain_meaning_contract_v64_preregistration.json",
    "dataset": "datasets/leftbrain_meaning_contract_v64.json",
    "dataset_closure": "configs/leftbrain_meaning_contract_v64_dataset_closure.json",
    "dataset_audit": "reports/leftbrain_meaning_contract_v64_dataset_audit.json",
    "harness_lock": "configs/leftbrain_meaning_contract_v64_harness_lock.json",
    "runner": "run_leftbrain_meaning_contract_v64.py",
    "analyzer": "analyze_leftbrain_meaning_contract_v64.py",
    "raw": "reports/leftbrain_meaning_contract_v64_raw.json",
    "analysis_json": "reports/leftbrain_meaning_contract_v64_analysis.json",
    "analysis_markdown": "reports/leftbrain_meaning_contract_v64_analysis.md",
    "diagnosis": "reports/leftbrain_meaning_contract_v64_diagnosis.md"
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    analysis = json.loads((ROOT / ARTIFACTS["analysis_json"]).read_text(encoding="utf-8"))
    if analysis["automatic_gates"]["passed"]:
        raise ValueError("V64 result lock expected the frozen negative decision")
    lock = {
        "schema": "uruha_leftbrain_meaning_contract_result_lock_v64",
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
            "rightbrain_realization_pilot": False,
            "runtime_change": False,
            "broad_human_likeness_claim": False
        },
        "next_question": "On entirely fresh cases and a preregistered semantic adjudicator, does a newer local model fill the same generic contract more accurately than qwen2.5:7b?"
    }
    OUTPUT.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
