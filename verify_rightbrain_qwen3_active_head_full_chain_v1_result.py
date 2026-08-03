#!/usr/bin/env python3
"""Verify the frozen active-token Qwen3 full-chain result."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_qwen3_active_head_full_chain_v1 as construction
import run_rightbrain_qwen3_active_head_full_chain_v1 as runner
import run_rightbrain_qwen3_compact_length_repro_v1 as metric_common


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
    binding_checks = []
    for binding in result_lock["result_bindings"]:
        path = _resolve(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        binding_checks.append({**binding, "match": actual == binding["sha256"]})
    rows = {
        condition: [
            construction.load_json(runner._result_path(prereg, condition, repeat))
            for repeat in construction.REPEATS
        ]
        for condition in construction.CONDITIONS
    }
    limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
    metrics = {}
    stability = {}
    for condition in construction.CONDITIONS:
        metrics[condition], stability[condition] = metric_common._measure(
            rows[condition], limits
        )
    all_losses = [row["loss"] for values in rows.values() for row in values]
    semantic_equivalent = max(all_losses) - min(all_losses) <= prereg[
        "semantic_equivalence_contract"
    ]["maximum_absolute_loss_delta_across_conditions"]
    outcome = runner._classify(stability, semantic_equivalent)
    checks = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "result_bindings_valid": all(row["match"] for row in binding_checks),
        "exact_repeat_count": sum(len(value) for value in rows.values()) == 36,
        "all_repeats_successful": all(
            row.get("execution_success") is True
            for values in rows.values()
            for row in values
        ),
        "one_forward_hash": len(
            {
                row["forward_boundary"]["sha256"]
                for values in rows.values()
                for row in values
            }
        )
        == 1,
        "metrics_exact": metrics == result["measurements"],
        "stability_exact": stability == result["stability_by_condition"],
        "semantic_equivalence_exact": semantic_equivalent
        == result["semantic_equivalent"],
        "outcome_exact": outcome == result["decision"]["outcome"],
        "result_lock_decision_exact": result_lock["decision"] == result["decision"],
        "no_training_or_production_authorization": not any(
            (
                result["decision"]["authorize_training"],
                result["decision"]["authorize_persona_training"],
                result["decision"]["authorize_production"],
                result["decision"]["authorize_persona_similarity_claim"],
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_qwen3_active_head_full_chain_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "decision": result["decision"],
    }


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
