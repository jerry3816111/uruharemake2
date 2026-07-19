#!/usr/bin/env python3
"""Run the corrected frozen V87.2 candidate-gate regression."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_2 as v872
import run_rightbrain_forbidden_projection_v87 as v87_runner
import run_rightbrain_pipeline_shadow_v61 as v61
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_2_preregistration.json"
LOCK_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_2_harness_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or v87.file_sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(f"V87.2 frozen artifact drift: {failed}")


def run_preflight(lock):
    command = [
        sys.executable,
        "-m",
        "unittest",
        "-v",
        "test_rightbrain_forbidden_conflict_projection_v87.py",
        "test_rightbrain_forbidden_projection_v87.py",
        "test_rightbrain_forbidden_projection_v87_2.py",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1", "TOKENIZERS_PARALLELISM": "false"},
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    observed = int(match.group(1)) if match else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed": observed,
        "expected": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def main():
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal V87.2 run requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V87.2 run requires a clean worktree")
    contract = load_json(PREREG_PATH)
    lock = load_json(LOCK_PATH)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"V87.2 preflight failed: {preflight}")
    source_checks = v87.verify_sources(contract, ROOT)
    packets, raw_rows, candidates = v87_runner.load_sources(contract)
    right_brain = RightBrain(load_model=False)
    defaults = {
        "memory_cue_canonicalization_enabled": bool(right_brain.memory_cue_canonicalization_enabled),
        "explicit_length_contract_enabled": bool(right_brain.explicit_length_contract_enabled),
        "forbidden_conflict_projection_enabled": bool(right_brain.forbidden_conflict_projection_enabled),
    }
    if any(defaults.values()):
        raise SystemExit(f"V87.2 requires default-off runtime flags before controlled replay: {defaults}")
    rows = v872.evaluate_all(right_brain, packets, raw_rows, candidates, contract)
    restored = {
        "memory_cue_canonicalization_enabled": bool(right_brain.memory_cue_canonicalization_enabled),
        "explicit_length_contract_enabled": bool(right_brain.explicit_length_contract_enabled),
        "forbidden_conflict_projection_enabled": bool(right_brain.forbidden_conflict_projection_enabled),
    }
    if restored != defaults:
        raise SystemExit("V87.2 did not restore runtime flags")
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    v76.write_jsonl(local["paired_rows"], rows)
    metadata = {
        "schema": "uruha_rightbrain_forbidden_projection_run_metadata_v87_2",
        "preflight": preflight,
        "source_checks": source_checks,
        "default_runtime_flags": defaults,
        "fixed_runtime_settings": contract["fixed_runtime_settings"],
        "runtime_flags_restored": restored == defaults,
        "case_count": len(rows),
        "evaluation_count": len(rows) * len(v87.CONDITIONS),
        "required_contract_match_count": sum(row["required_contract_matches"] for row in rows),
        "model_call_count": 0,
        "production_database_opened": False,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "hard_marker_regression_count": 0,
    }
    local["run_metadata"].parent.mkdir(parents=True, exist_ok=True)
    local["run_metadata"].write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
