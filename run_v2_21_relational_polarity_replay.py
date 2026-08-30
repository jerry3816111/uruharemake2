#!/usr/bin/env python3
"""Run the V2.21 interface-corrected first complete causal replay."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path

import run_v2_18_fifty_turn_memory_comparison as base
import run_v2_19_fifty_turn_memory_remediation as v219
import run_v2_20_relational_polarity_remediation as v220


ROOT = Path(__file__).resolve().parent
CASE_PATH = v219.CASE_PATH
PREREG_PATH = ROOT / "configs/v2_21_relational_polarity_replay_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_21_relational_polarity_replay_lock.json"
V219_RAW_PATH = v219.RAW_PATH
RAW_PATH = ROOT / "analysis/v2_21_relational_polarity_replay_raw.json"
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
PERSONHOOD_PATH = ROOT / "uruha_personhood_loop.py"
VISIBLE_CONTRACT_PATH = ROOT / "human_pragmatic_comparison_v2_14.py"
REMEDIATION_TEST_PATH = ROOT / "test_memory_remediation_v2_19.py"
V220_RUNNER_PATH = ROOT / "run_v2_20_relational_polarity_remediation.py"
RUNNER_TEST_PATH = ROOT / "test_relational_polarity_replay_v2_21.py"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_binding(path):
    return base.relative_binding(path)


def build_lock():
    return {
        "schema": "uruha_v2_21_relational_polarity_replay_lock",
        "status": "frozen_before_first_complete_replay_generation",
        "policy": {
            "reuse_v2_19_outputs_without_regeneration": True,
            "fresh_generation_only_for_repaired_uruha": True,
            "v2_20_attempt1_had_no_raw_result": True,
            "retain_first_complete_generation_failures": True,
            "same_case_replay_not_independent_holdout": True,
        },
        "artifacts": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "v2_19_frozen_raw": relative_binding(V219_RAW_PATH),
            "runner": relative_binding(Path(__file__)),
            "reused_v2_20_runner": relative_binding(V220_RUNNER_PATH),
            "runtime": relative_binding(RUNTIME_PATH),
            "personhood": relative_binding(PERSONHOOD_PATH),
            "visible_contract": relative_binding(VISIBLE_CONTRACT_PATH),
            "remediation_tests": relative_binding(REMEDIATION_TEST_PATH),
            "runner_tests": relative_binding(RUNNER_TEST_PATH),
        },
    }


def validate_lock():
    lock = load_json(LOCK_PATH)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / binding["path"]
        checks[name] = bool(path.is_file() and base.sha256_file(path) == binding.get("sha256"))
    return {"passed": bool(checks) and all(checks.values()), "checks": checks, "lock": lock}


def validate_design(case, prereg, frozen_raw):
    result = v220.validate_design(case, prereg, frozen_raw)
    errors = list(result.get("errors") or [])
    criteria = prereg.get("success_criteria") or {}
    inherited_keys = {
        "uruha_primary_source_grounded_recall_min",
        "uruha_primary_recall_denominator",
        "uruha_stale_value_revival_max",
        "uruha_false_memory_assertion_max",
        "uruha_visible_japanese_checkpoint_min",
        "production_memory_writes",
    }
    missing = sorted(inherited_keys - set(criteria))
    if missing:
        errors.append(f"inherited summary keys missing: {missing}")
    result["errors"] = errors
    result["passed"] = not errors
    result["summary_interface_keys_complete"] = not missing
    return result


@contextlib.contextmanager
def _v220_output_paths():
    old = (v220.PREREG_PATH, v220.LOCK_PATH, v220.RAW_PATH)
    try:
        v220.PREREG_PATH = PREREG_PATH
        v220.LOCK_PATH = LOCK_PATH
        v220.RAW_PATH = RAW_PATH
        yield
    finally:
        v220.PREREG_PATH, v220.LOCK_PATH, v220.RAW_PATH = old


def run_fresh(case, prereg, frozen_raw):
    with _v220_output_paths():
        raw = v220.run_fresh(case, prereg, frozen_raw)
    raw["schema"] = "uruha_v2_21_relational_polarity_replay_raw"
    raw["status"] = "first_complete_replay_generation_human_ratings_not_run"
    raw["v2_20_attempt1"] = {
        "status": "runner_failure_before_raw",
        "result_available": False,
        "error": "KeyError: uruha_primary_source_grounded_recall_min",
    }
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("validate-design", "freeze-lock", "validate-lock", "run-fresh"),
        required=True,
    )
    args = parser.parse_args()
    case = load_json(CASE_PATH)
    prereg = load_json(PREREG_PATH)
    frozen_raw = load_json(V219_RAW_PATH)
    design = validate_design(case, prereg, frozen_raw)
    if not design["passed"]:
        raise SystemExit(json.dumps(design, ensure_ascii=False, indent=2))
    if args.mode == "validate-design":
        print(json.dumps(design, ensure_ascii=False, indent=2))
        return
    if args.mode == "freeze-lock":
        if LOCK_PATH.exists():
            raise SystemExit("lock already exists; refusing to overwrite")
        LOCK_PATH.write_text(json.dumps(build_lock(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(validate_lock(), ensure_ascii=False, indent=2))
        return
    lock = validate_lock()
    if not lock["passed"]:
        raise SystemExit(json.dumps(lock, ensure_ascii=False, indent=2))
    if args.mode == "validate-lock":
        print(json.dumps(lock, ensure_ascii=False, indent=2))
        return
    if RAW_PATH.exists():
        raise SystemExit("raw result already exists; refusing to overwrite frozen generation")
    raw = run_fresh(case, prereg, frozen_raw)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(RAW_PATH), "summary": raw["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
