#!/usr/bin/env python3
"""Independently verify the compiled surface-signal result bundle."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_compiled_surface_signal_v1 as construction
import run_rightbrain_qwen3_compiled_surface_signal_v1 as runner


ROOT = Path(__file__).resolve().parent


def _resolve(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def verify():
    prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
    result_lock = construction.load_json(
        ROOT / prereg["result_paths"]["result_lock"]
    )
    rows = [
        construction.load_json(runner._result_path(prereg, repeat))
        for repeat in construction.REPEATS
    ]
    bindings = []
    for binding in result_lock["result_bindings"]:
        path = _resolve(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append({**binding, "match": actual == binding["sha256"]})
    completed = all(row.get("execution_success") is True for row in rows)
    if completed:
        measurements, checks = runner._measure(rows, prereg)
    else:
        measurements = result["measurements"]
        checks = {
            key: False
            for key in result["checks"]
            if key != "all_repetitions_complete"
        }
    outcome = runner._classify(checks, completed)
    passed = completed and all(checks.values())
    next_step = runner._expected_next_step(outcome, passed)
    decision = result["decision"]
    dataset = construction.load_json(construction.DEFAULT_DATASET)
    rebuilt_dataset = construction.build_dataset()
    rebuilt_prompt = construction.prompt_contract(rebuilt_dataset)
    verification = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "result_bindings_valid": all(binding["match"] for binding in bindings),
        "dataset_rebuild_exact": dataset == rebuilt_dataset,
        "prompt_rebuild_exact": all(
            rebuilt_prompt[f"{condition}_prompt_sha256"]
            == prereg["prompt_contract"][f"{condition}_prompt_sha256"]
            for condition in construction.CONDITIONS
        ),
        "exact_repeat_ids": [row.get("repeat") for row in rows]
        == list(construction.REPEATS),
        "measurements_exact": measurements == result["measurements"],
        "checks_exact": {"all_repetitions_complete": completed, **checks}
        == result["checks"],
        "outcome_exact": outcome == decision["outcome"],
        "pass_exact": passed == decision["passed"],
        "next_step_exact": next_step == decision["authorized_next_step"],
        "full_pipeline_authorization_exact": (
            decision["full_pipeline_holdout_authorized"] is passed
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
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_verification_v1",
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
