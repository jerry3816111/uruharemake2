#!/usr/bin/env python3
"""Verify the Qwen3 active-head 64-step result from frozen raw repeats."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_active_head_64step_v1 as construction
import run_rightbrain_qwen3_active_head_64step_v1 as runner


ROOT = Path(__file__).resolve().parent


def _resolve(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def verify():
    prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    result_path = ROOT / prereg["result_paths"]["aggregate_json"]
    result_lock_path = ROOT / prereg["result_paths"]["result_lock"]
    result = construction.load_json(result_path)
    result_lock = construction.load_json(result_lock_path)
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
    if completed:
        measurements, checks = runner._measure(rows, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure") for row in rows if not row.get("execution_success")
            ]
        }
        checks = runner._failure_checks()
    outcome = runner._classify(checks, completed)
    expected_pass = completed and all(checks.values())
    expected_next = (
        "preregister_ephemeral_multibatch_fresh_generation_probe"
        if expected_pass
        else "diagnose_active_head_64step_or_holdout_failure"
    )
    decision = result["decision"]
    verification = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "result_bindings_valid": all(binding["match"] for binding in bindings),
        "exact_repeat_ids": [row.get("repeat") for row in rows]
        == list(construction.REPEATS),
        "measurements_exact": measurements == result["measurements"],
        "checks_exact": {"all_repetitions_complete": completed, **checks}
        == result["checks"],
        "outcome_exact": outcome == decision["outcome"],
        "pass_exact": expected_pass == decision["passed"],
        "next_step_exact": expected_next == decision["authorized_next_step"],
        "fresh_generation_authorization_exact": (
            decision["fresh_generation_probe_authorized"] is expected_pass
        ),
        "result_lock_decision_exact": result_lock["decision"] == decision,
        "result_lock_authorization_closed": not any(
            result_lock["authorization"].values()
        ),
        "no_persistent_or_persona_authorization": not any(
            (
                decision["authorize_persistent_training"],
                decision["authorize_persona_training"],
                decision["authorize_adapter_save"],
                decision["authorize_production"],
                decision["authorize_persona_similarity_claim"],
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_qwen3_active_head_64step_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": all(verification.values()),
        "checks": verification,
        "decision": decision,
    }


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
