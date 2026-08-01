#!/usr/bin/env python3
"""Freeze the deterministic RightBrain max-norm training pilot v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_max_norm_training_pilot_v1 as common
import build_rightbrain_role_curriculum_training_pilot_v1 as holdout_construction


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_max_norm_training_pilot_v2"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_max_norm_training_pilot_v2_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_max_norm_training_pilot_v2_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_max_norm_training_pilot_v2_construction.md"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_max_norm_training_pilot_v2_execution_lock.json"
RUNNER = ROOT / "run_rightbrain_max_norm_training_pilot_v2.py"
CONDITIONS = common.CONDITIONS
load_json = common.load_json
sha256_file = common.sha256_file
file_binding = common.file_binding
atomic_json = common.atomic_json
atomic_text = common.atomic_text


def build_report(preregistration_path=DEFAULT_PREREGISTRATION):
    preregistration = load_json(preregistration_path)
    schedule = preregistration["controlled_training_schedule"]
    conditions = preregistration["conditions"]
    binding_rows = []
    for expected in preregistration["frozen_bindings"]:
        path = ROOT / expected["path"]
        actual = sha256_file(path) if path.is_file() else None
        binding_rows.append(
            {
                "path": expected["path"],
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual,
                "match": actual == expected["sha256"],
            }
        )
    dataset_path = ROOT / schedule["dataset"]
    holdout_path = ROOT / preregistration["policy_discrimination_evaluation"]["holdout"]
    dataset = load_json(dataset_path)
    holdout = load_json(holdout_path)
    holdout_audit = holdout_construction.audit_holdout(holdout, dataset)
    model = preregistration["local_model_contract"]
    adapter_root = ROOT / model["initial_adapter"]["path"]
    output_paths = {
        condition: ROOT / conditions[condition]["output_directory"] for condition in CONDITIONS
    }
    result_paths = preregistration["result_paths"]
    generated_outputs = [
        ROOT / result_paths["training_pair_integrity_json"],
        ROOT / result_paths["evaluation_lock"],
        ROOT / result_paths["aggregate_json"],
        ROOT / result_paths["aggregate_markdown"],
        ROOT / result_paths["result_lock"],
        *[
            ROOT / f"{result_paths['training_prefix']}{condition}.json"
            for condition in CONDITIONS
        ],
        *[
            ROOT / f"{result_paths['evaluation_prefix']}{condition}.json"
            for condition in CONDITIONS
        ],
    ]
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_before_training": preregistration["status"]
        == "frozen_before_any_v2_training_update",
        "exact_conditions": tuple(conditions) == CONDITIONS,
        "max_norm_values": conditions["control_0_3"]["maximum_gradient_norm"] == 0.3
        and conditions["treatment_3_0"]["maximum_gradient_norm"] == 3.0,
        "foreach_false_for_both": schedule["clip_grad_norm_foreach"] is False,
        "same_dataset_80_rows": len(dataset) == schedule["dataset_rows"] == 80,
        "exact_80_micro_steps": schedule["micro_steps_exact"] == 80,
        "exact_10_updates": schedule["optimizer_updates_exact"] == 10,
        "frozen_bindings": all(row["match"] for row in binding_rows),
        "holdout_source_separation": holdout_audit["passed"],
        "snapshot_exists": Path(model["snapshot_root"]).is_dir(),
        "initial_adapter_config_match": sha256_file(adapter_root / "adapter_config.json")
        == model["initial_adapter"]["adapter_config_sha256"],
        "initial_adapter_model_match": sha256_file(adapter_root / "adapter_model.safetensors")
        == model["initial_adapter"]["adapter_model_sha256"],
        "local_only": model["local_only"] and not model["paid_cloud_inference_allowed"],
        "runner_exists": RUNNER.is_file(),
        "temporary_outputs_absent": all(not path.exists() for path in output_paths.values()),
        "generated_results_absent": all(not path.exists() for path in generated_outputs),
        "no_production_authorization": not any(
            preregistration["boundaries"][key]
            for key in (
                "production_memory_access",
                "production_memory_write",
                "production_runtime_change",
                "production_adapter_replacement",
                "persona_similarity_claim",
                "public_impersonation",
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_max_norm_training_pilot_construction_v2",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "frozen_bindings": binding_rows,
        "holdout_audit": holdout_audit,
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_foreach_false_two_condition_pilot_only"
                if all(checks.values())
                else "refuse_v2_pilot_execution"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain max_norm 公平訓練試驗 v2 建構報告",
        "",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 唯一訓練變因：`max_norm=0.3` 對 `3.0`",
        "- 共通修正：兩組皆使用 `foreach=False`",
        "- 評測前要求：第一批 raw norm 相對誤差不超過 `0.1%`",
        "- 正式 runtime 修改：`0`",
        "",
        "## 檢查",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["checks"].items()
    )
    return "\n".join(lines) + "\n"


def build_execution_lock(report):
    if not report["decision"]["passed"]:
        raise RuntimeError("Refusing to lock failed v2 construction")
    paths = [
        DEFAULT_PREREGISTRATION,
        Path(__file__),
        RUNNER,
        ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json",
        ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_holdout.json",
        ROOT / "configs/rightbrain_max_norm_training_pilot_v1_result_lock.json",
        ROOT / "reports/rightbrain_max_norm_training_pilot_v1_invalid_result.json",
        ROOT / "configs/rightbrain_gradient_norm_crosscheck_v1_result_lock.json",
        ROOT / "reports/rightbrain_gradient_norm_crosscheck_v1_result.json",
        ROOT / "run_rightbrain_role_curriculum_training_pilot_v1.py",
        DEFAULT_REPORT_JSON,
    ]
    return {
        "schema": "uruha_rightbrain_max_norm_training_pilot_execution_lock_v2",
        "experiment_id": EXPERIMENT_ID,
        "repo_bindings": [file_binding(path) for path in paths],
        "authorization": {
            "condition_isolated_training": True,
            "conditions": list(CONDITIONS),
            "micro_steps_per_condition": 80,
            "optimizer_updates_per_condition": 10,
            "clip_grad_norm_foreach": False,
            "evaluation_requires_separate_pair_integrity_lock": True,
            "production_runtime_change": False,
            "production_adapter_replacement": False,
            "persona_similarity_claim": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-lock", action="store_true")
    args = parser.parse_args()
    report = build_report()
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))
    if not report["decision"]["passed"]:
        raise SystemExit(1)
    if args.write_lock:
        atomic_json(DEFAULT_REPORT_JSON, report)
        atomic_text(DEFAULT_REPORT_MD, render_markdown(report))
        atomic_json(DEFAULT_EXECUTION_LOCK, build_execution_lock(report))


if __name__ == "__main__":
    main()
