#!/usr/bin/env python3
"""Freeze the MLX no-checkpoint single-step gradient probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_mlx_gradient_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_mlx_no_checkpoint_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_mlx_no_checkpoint_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_mlx_no_checkpoint_repro_v1_execution_lock.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_mlx_no_checkpoint_repro_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_mlx_no_checkpoint_repro_v1_construction.md"
PRIOR_PREREGISTRATION = ROOT / "configs/rightbrain_mlx_single_step_repro_v1_preregistration.json"
RUNNER = ROOT / "run_rightbrain_mlx_no_checkpoint_repro_v1.py"
load_json = common.load_json
sha256_file = common.sha256_file
file_binding = common.file_binding
atomic_json = common.atomic_json
atomic_text = common.atomic_text


def _binding_rows(rows):
    output = []
    for expected in rows:
        path = Path(expected["path"])
        if not path.is_absolute():
            path = ROOT / path
        actual = sha256_file(path) if path.is_file() else None
        output.append({**expected, "actual_sha256": actual, "match": actual == expected["sha256"]})
    return output


def build_report():
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    prior = load_json(PRIOR_PREREGISTRATION)
    bindings = _binding_rows(preregistration["frozen_bindings"])
    environment = common.inspect_environment(preregistration)
    expected_environment = preregistration["local_environment"]
    probe = preregistration["exact_probe"]
    prior_probe = prior["exact_probe"]
    dataset = load_json(ROOT / probe["dataset"])
    actual_ids = [dataset[index]["id"] for index in probe["row_indices"]]
    outputs = [
        ROOT / preregistration["result_paths"]["aggregate_json"],
        ROOT / preregistration["result_paths"]["aggregate_markdown"],
        ROOT / preregistration["result_paths"]["result_lock"],
        *[
            ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"
            for repeat in range(1, 4)
        ],
    ]
    observed_changed_keys = {
        key for key in set(probe) | set(prior_probe) if probe.get(key) != prior_probe.get(key)
    }
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_before_backward": preregistration["status"]
        == "frozen_before_any_no_checkpoint_mlx_backward_pass",
        "frozen_bindings": all(row["match"] for row in bindings),
        "environment_exact": environment["python_version"]
        == expected_environment["python_version"]
        and environment["packages"] == expected_environment["packages"]
        and environment["pip_freeze_sha256"] == expected_environment["pip_freeze_sha256"],
        "exact_batch_ids": actual_ids == probe["row_ids"],
        "only_checkpoint_changed": observed_changed_keys == {"gradient_checkpointing"}
        and prior_probe["gradient_checkpointing"] is True
        and probe["gradient_checkpointing"] is False,
        "model_adapter_environment_fixed": preregistration["local_environment"]
        == prior["local_environment"]
        and preregistration["local_model_contract"] == prior["local_model_contract"]
        and preregistration["adapter_conversion_contract"]
        == prior["adapter_conversion_contract"],
        "runner_exists": RUNNER.is_file(),
        "outputs_absent": all(not path.exists() for path in outputs),
        "zero_update_boundaries": not any(
            preregistration["boundaries"][key]
            for key in (
                "optimizer_instantiation",
                "optimizer_step",
                "gradient_clipping",
                "parameter_mutation",
                "adapter_or_model_save",
                "text_generation",
                "production_runtime_change",
                "persona_similarity_claim",
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_mlx_no_checkpoint_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "observed_changed_probe_keys": sorted(observed_changed_keys),
        "frozen_bindings": bindings,
        "environment": environment,
        "actual_row_ids": actual_ids,
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_three_no_checkpoint_mlx_repetitions_only"
                if all(checks.values())
                else "refuse_no_checkpoint_mlx_probe"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain MLX 無 checkpoint 梯度探針",
        "",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 唯一改動：gradient checkpointing true -> false",
        "- 模型、adapter、dropout、dtype、資料、800-token 配置：固定",
        "- optimizer step：0",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["checks"].items()
    )
    return "\n".join(lines) + "\n"


def build_lock(report):
    if not report["decision"]["passed"]:
        raise RuntimeError("Refusing to lock failed MLX no-checkpoint probe")
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    prior = load_json(PRIOR_PREREGISTRATION)
    model_root = Path(prior["local_model_contract"]["snapshot_root"])
    paths = [
        DEFAULT_PREREGISTRATION,
        Path(__file__),
        RUNNER,
        ROOT / "run_rightbrain_mlx_gradient_repro_v1.py",
        PRIOR_PREREGISTRATION,
        ROOT / "configs/rightbrain_mlx_single_step_repro_v1_result_lock.json",
        ROOT / "reports/rightbrain_mlx_single_step_repro_v1_result.json",
        ROOT / "configs/rightbrain_mlx_gradient_repro_v1_environment.txt",
        ROOT / preregistration["exact_probe"]["dataset"],
        ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_model.safetensors",
        DEFAULT_REPORT_JSON,
        *[model_root / name for name in prior["local_model_contract"]["metadata_sha256"]],
    ]
    return {
        "schema": "uruha_rightbrain_mlx_no_checkpoint_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [file_binding(path) for path in paths],
        "authorization": {
            "exact_zero_update_repetitions": [1, 2, 3],
            "micro_steps_each": 1,
            "gradient_accumulation": 1,
            "optimizer_steps": 0,
            "training_backend": "mlx",
            "gradient_checkpointing": False,
            "adapter_conversion_exact": True,
            "adapter_dropout": 0.0,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
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
        atomic_json(DEFAULT_EXECUTION_LOCK, build_lock(report))


if __name__ == "__main__":
    main()
