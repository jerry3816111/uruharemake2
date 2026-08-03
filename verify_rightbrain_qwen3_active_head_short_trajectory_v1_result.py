#!/usr/bin/env python3
"""Verify the frozen active-head Qwen3 short-trajectory result."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_active_head_short_trajectory_v1 as construction
import run_rightbrain_qwen3_active_head_short_trajectory_v1 as runner


ROOT = Path(__file__).resolve().parent


def _resolve(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def verify():
    prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
    result_lock = construction.load_json(ROOT / prereg["result_paths"]["result_lock"])
    bindings = []
    for binding in result_lock["result_bindings"]:
        path = _resolve(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append({**binding, "match": actual == binding["sha256"]})
    rows = [
        construction.load_json(runner._result_path(prereg, repeat))
        for repeat in construction.REPEATS
    ]
    completed = all(row.get("execution_success") is True for row in rows)
    measurements, checks = runner._measure(rows, prereg)
    outcome = runner._classify(checks, completed)
    verification = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "result_bindings_valid": all(binding["match"] for binding in bindings),
        "exact_repeat_count": len(rows) == len(construction.REPEATS),
        "all_repeats_successful": completed,
        "measurements_exact": measurements == result["measurements"],
        "checks_exact": {"all_repetitions_complete": completed, **checks}
        == result["checks"],
        "outcome_exact": outcome == result["decision"]["outcome"],
        "result_lock_decision_exact": result_lock["decision"] == result["decision"],
        "no_persistent_authorization": not any(
            (
                result["decision"]["authorize_persistent_training"],
                result["decision"]["authorize_persona_training"],
                result["decision"]["authorize_adapter_save"],
                result["decision"]["authorize_production"],
                result["decision"]["authorize_persona_similarity_claim"],
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_qwen3_active_head_short_trajectory_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": all(verification.values()),
        "checks": verification,
        "decision": result["decision"],
    }


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
