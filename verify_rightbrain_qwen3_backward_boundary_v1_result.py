#!/usr/bin/env python3
"""Verify the frozen Qwen3 backward-boundary result without rewriting it."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_backward_boundary_v1 as construction
import run_rightbrain_qwen3_backward_boundary_v1 as runner
import run_rightbrain_qwen3_compact_length_repro_v1 as metric_common


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
    lock_validation = runner.validate_lock()
    binding_checks = []
    for binding in result_lock["result_bindings"]:
        path = _resolve(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        binding_checks.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )

    rows = {
        condition: [
            construction.load_json(runner._result_path(prereg, condition, repeat))
            for repeat in construction.REPEATS
        ]
        for condition in construction.CONDITIONS
    }
    limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
    recomputed_metrics = {}
    recomputed_stability = {}
    for condition in construction.CONDITIONS:
        recomputed_metrics[condition], recomputed_stability[condition] = (
            metric_common._measure(rows[condition], limits)
        )
    recomputed_outcome = runner._classify(recomputed_stability)
    forward_hashes = {
        row["forward_boundary"]["sha256"]
        for condition_rows in rows.values()
        for row in condition_rows
    }
    checks = {
        "execution_lock_valid": lock_validation["passed"],
        "result_bindings_valid": all(row["match"] for row in binding_checks),
        "exact_repeat_count": sum(len(value) for value in rows.values()) == 54,
        "all_repeats_successful": all(
            row.get("execution_success") is True
            for condition_rows in rows.values()
            for row in condition_rows
        ),
        "one_forward_hash": len(forward_hashes) == 1,
        "metrics_exact": recomputed_metrics == result["measurements"],
        "stability_exact": recomputed_stability == result["stability_by_condition"],
        "outcome_exact": recomputed_outcome == result["decision"]["outcome"],
        "result_lock_decision_exact": result_lock["decision"] == result["decision"],
        "training_not_authorized": not result["decision"]["authorize_training"],
        "persona_training_not_authorized": not result["decision"][
            "authorize_persona_training"
        ],
        "production_not_authorized": not result["decision"]["authorize_production"],
    }
    return {
        "schema": "uruha_rightbrain_qwen3_backward_boundary_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "decision": result["decision"],
        "binding_checks": binding_checks,
    }


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
