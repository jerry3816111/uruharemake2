#!/usr/bin/env python3
"""Run V2.22 with stable observed relational-source recovery."""

from __future__ import annotations

import argparse
import contextlib
import json
from copy import deepcopy
from pathlib import Path

import run_v2_18_fifty_turn_memory_comparison as base
import run_v2_19_fifty_turn_memory_remediation as v219
import run_v2_20_relational_polarity_remediation as v220
import run_v2_21_relational_polarity_replay as v221


ROOT = Path(__file__).resolve().parent
CASE_PATH = v219.CASE_PATH
PREREG_PATH = ROOT / "configs/v2_22_stable_relational_source_replay_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_22_stable_relational_source_replay_lock.json"
V219_RAW_PATH = v219.RAW_PATH
V221_RAW_PATH = v221.RAW_PATH
RAW_PATH = ROOT / "analysis/v2_22_stable_relational_source_replay_raw.json"
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
PERSONHOOD_PATH = ROOT / "uruha_personhood_loop.py"
VISIBLE_CONTRACT_PATH = ROOT / "human_pragmatic_comparison_v2_14.py"
REMEDIATION_TEST_PATH = ROOT / "test_memory_remediation_v2_19.py"
V220_RUNNER_PATH = ROOT / "run_v2_20_relational_polarity_remediation.py"
RUNNER_TEST_PATH = ROOT / "test_stable_relational_source_replay_v2_22.py"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_binding(path):
    return base.relative_binding(path)


def build_lock():
    return {
        "schema": "uruha_v2_22_stable_relational_source_replay_lock",
        "status": "frozen_before_first_complete_generation",
        "policy": {
            "reuse_v2_19_and_v2_21_outputs_without_regeneration": True,
            "fresh_generation_only_for_v2_22_uruha": True,
            "retain_first_generation_failures": True,
            "same_case_replay_not_independent_holdout": True,
        },
        "artifacts": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "v2_19_frozen_raw": relative_binding(V219_RAW_PATH),
            "v2_21_frozen_raw": relative_binding(V221_RAW_PATH),
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


def validate_design(case, prereg, v219_raw, v221_raw):
    result = v221.validate_design(case, prereg, v219_raw)
    errors = list(result.get("errors") or [])
    if v221_raw.get("case_id") != case.get("case_id"):
        errors.append("V2.21 frozen raw and case id differ")
    if len(v221_raw.get("comparisons") or []) != 5:
        errors.append("V2.21 frozen raw must contain five checkpoints")
    result["errors"] = errors
    result["passed"] = not errors
    result["v2_21_reference_sha256"] = base.sha256_file(V221_RAW_PATH)
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


def _lookup(raw):
    return {
        int(comparison["turn"]): deepcopy(comparison["conditions"]["uruha_memory"])
        for comparison in raw.get("comparisons") or []
    }


def run_fresh(case, prereg, v219_raw, v221_raw):
    with _v220_output_paths():
        raw = v220.run_fresh(case, prereg, v219_raw)
    v221_lookup = _lookup(v221_raw)
    for comparison in raw["comparisons"]:
        turn = int(comparison["turn"])
        comparison["conditions"]["v2_21_uruha_memory"] = v221_lookup[turn]
        comparison["conditions"]["v2_21_uruha_memory"]["fresh_in_v2_22"] = False
        comparison["conditions"]["v2_21_uruha_memory"]["reused_from_v2_21"] = True
        comparison["conditions"]["uruha_memory"]["fresh_in_v2_22"] = True
    raw["schema"] = "uruha_v2_22_stable_relational_source_replay_raw"
    raw["status"] = "first_complete_generation_human_ratings_not_run"
    raw["comparison_boundary"] = {
        "fresh_outputs": "Only V2.22 uruha_memory checkpoint outputs are fresh.",
        "frozen_outputs": "V2.19 baselines and pre-fix Uruha plus V2.21 Uruha are reused without regeneration.",
        "independent_holdout": False,
    }
    raw["claims"]["not_supported"] = list(
        dict.fromkeys(
            [
                *raw["claims"].get("not_supported", []),
                "independent semantic generalization",
                "fresh V2.22 baseline generation",
                "human felt-understanding preference",
            ]
        )
    )
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
    v219_raw = load_json(V219_RAW_PATH)
    v221_raw = load_json(V221_RAW_PATH)
    design = validate_design(case, prereg, v219_raw, v221_raw)
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
    raw = run_fresh(case, prereg, v219_raw, v221_raw)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(RAW_PATH), "summary": raw["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
