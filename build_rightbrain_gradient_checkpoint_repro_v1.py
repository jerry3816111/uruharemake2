#!/usr/bin/env python3
"""Freeze the zero-update gradient-checkpointing reproducibility probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_gradient_dropout_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_gradient_checkpoint_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_gradient_checkpoint_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_gradient_checkpoint_repro_v1_execution_lock.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_gradient_checkpoint_repro_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_gradient_checkpoint_repro_v1_construction.md"
RUNNER = ROOT / "run_rightbrain_gradient_checkpoint_repro_v1.py"
load_json = common.load_json
sha256_file = common.sha256_file
file_binding = common.file_binding
atomic_json = common.atomic_json
atomic_text = common.atomic_text


def build_report():
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    probe = preregistration["exact_probe"]
    dataset = load_json(ROOT / probe["dataset"])
    binding_rows = []
    for expected in preregistration["frozen_bindings"]:
        path = ROOT / expected["path"]
        actual = sha256_file(path) if path.is_file() else None
        binding_rows.append({**expected, "actual_sha256": actual, "match": actual == expected["sha256"]})
    actual_ids = [dataset[index]["id"] for index in probe["row_indices"]]
    model = preregistration["local_model_contract"]
    adapter_root = ROOT / model["initial_adapter"]["path"]
    paths = preregistration["result_paths"]
    outputs = [
        ROOT / paths["aggregate_json"],
        ROOT / paths["aggregate_markdown"],
        ROOT / paths["result_lock"],
        *[
            ROOT / f"{paths['repeat_prefix']}{repeat}.json"
            for repeat in range(1, probe["isolated_process_repetitions"] + 1)
        ],
    ]
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_before_backward": preregistration["status"]
        == "frozen_before_any_checkpoint_off_backward_pass",
        "frozen_bindings": all(row["match"] for row in binding_rows),
        "exact_actual_first_batch_indices": probe["row_indices"]
        == [63, 50, 60, 77, 2, 59, 78, 36],
        "exact_row_ids": actual_ids == probe["row_ids"],
        "three_isolated_repetitions": probe["isolated_process_repetitions"] == 3,
        "eight_micro_steps_zero_updates": probe["micro_steps"]
        == probe["gradient_accumulation"]
        == 8
        and probe["optimizer_steps"] == 0,
        "only_candidate_change_checkpointing_off": probe["adapter_dropout"] == 0.08
        and probe["gradient_checkpointing"] is False
        and probe["dtype"] == "torch.bfloat16"
        and probe["norm_foreach"] is False,
        "local_memory_limit_30_gib": probe["driver_allocated_memory_bytes_maximum"]
        == 30 * 1024**3,
        "snapshot_exists": Path(model["snapshot_root"]).is_dir(),
        "initial_adapter_config_match": sha256_file(adapter_root / "adapter_config.json")
        == model["initial_adapter"]["adapter_config_sha256"],
        "initial_adapter_model_match": sha256_file(adapter_root / "adapter_model.safetensors")
        == model["initial_adapter"]["adapter_model_sha256"],
        "runner_exists": RUNNER.is_file(),
        "outputs_absent": all(not path.exists() for path in outputs),
        "zero_update_boundaries": not any(
            preregistration["boundaries"][key]
            for key in (
                "optimizer_instantiation",
                "optimizer_step",
                "gradient_clipping",
                "parameter_mutation",
                "model_or_adapter_save",
                "text_generation",
                "production_runtime_change",
                "persona_similarity_claim",
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "frozen_bindings": binding_rows,
        "actual_row_ids": actual_ids,
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_three_checkpoint_off_zero_update_repetitions_only"
                if all(checks.values())
                else "refuse_checkpoint_repro_probe"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain checkpointing 梯度重現探針建構",
        "",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 唯一改動：gradient checkpointing `on -> off`",
        "- LoRA dropout：保持 `0.08`",
        "- optimizer step：`0`",
        "- 本機記憶體上限：`30 GiB`",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["checks"].items()
    )
    return "\n".join(lines) + "\n"


def build_lock(report):
    if not report["decision"]["passed"]:
        raise RuntimeError("Refusing to lock failed checkpoint probe")
    paths = [
        DEFAULT_PREREGISTRATION,
        Path(__file__),
        RUNNER,
        ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json",
        ROOT / "configs/rightbrain_gradient_dropout_repro_v1_result_lock.json",
        ROOT / "reports/rightbrain_gradient_dropout_repro_v1_result.json",
        ROOT / "run_rightbrain_role_curriculum_training_pilot_v1.py",
        DEFAULT_REPORT_JSON,
    ]
    return {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "repo_bindings": [file_binding(path) for path in paths],
        "authorization": {
            "exact_zero_update_repetitions": [1, 2, 3],
            "micro_steps_each": 8,
            "optimizer_steps": 0,
            "adapter_dropout": 0.08,
            "gradient_checkpointing": False,
            "driver_allocated_memory_bytes_maximum": 30 * 1024**3,
            "model_or_adapter_save": False,
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
