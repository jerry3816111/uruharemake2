#!/usr/bin/env python3
"""Verify the provider-pair CPO result from frozen condition runs."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_provider_pair_cpo_v1 as construction
import run_rightbrain_qwen3_provider_pair_cpo_v1 as runner


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
    grouped = runner._condition_rows(prereg)
    completed = all(
        row.get("execution_success") is True
        for rows in grouped.values()
        for row in rows
    )
    if completed:
        measurements, checks = runner._measure(grouped, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure")
                for rows in grouped.values()
                for row in rows
                if not row.get("execution_success")
            ]
        }
        checks = {
            "all_values_finite_and_update_count_exact": False,
            "initial_parameter_hash_equal_between_conditions": False,
            "pre_holdout_metrics_equal_between_conditions": False,
            "control_and_candidate_each_reproducible": False,
            "candidate_holdout_margin_delta_positive": False,
            "candidate_holdout_margin_delta_exceeds_control": False,
            "candidate_post_holdout_margin_exceeds_control": False,
            "candidate_post_correct_preference_rate_not_below_control": False,
            "candidate_post_preferred_nll_within_control_bound": False,
            "candidate_train_final_margin_exceeds_control": False,
            "mutation_within_bounds": False,
            "all_contracts_exact": False,
        }
    outcome = runner._classify(checks, completed)
    expected_pass = completed and all(checks.values())
    expected_next = (
        "preregister_provider_pair_cpo_64step_fresh_generation_probe"
        if expected_pass
        else "diagnose_provider_pair_cpo_objective_failure"
    )
    decision = result["decision"]
    verification = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "result_bindings_valid": all(binding["match"] for binding in bindings),
        "exact_conditions": list(grouped) == list(construction.CONDITIONS),
        "exact_repeat_ids": all(
            [row.get("repeat") for row in rows] == list(construction.REPEATS)
            for rows in grouped.values()
        ),
        "measurements_exact": measurements == result["measurements"],
        "checks_exact": {"all_six_runs_complete": completed, **checks}
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
        "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_verification_v1",
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
