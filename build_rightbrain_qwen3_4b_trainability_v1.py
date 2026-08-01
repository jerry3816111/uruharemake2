#!/usr/bin/env python3
"""Freeze the Qwen3-4B RightBrain zero-update trainability probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_mlx_gradient_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_4b_trainability_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_4b_trainability_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_4b_trainability_v1_execution_lock.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_qwen3_4b_trainability_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_qwen3_4b_trainability_v1_construction.md"
RUNNER = ROOT / "run_rightbrain_qwen3_4b_trainability_v1.py"
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
    bindings = _binding_rows(preregistration["frozen_bindings"])
    model_bindings = _binding_rows(preregistration["external_model_bindings"])
    environment = common.inspect_environment(preregistration)
    expected_environment = preregistration["local_environment"]
    model_contract = preregistration["local_model_contract"]
    model_root = Path(model_contract["snapshot_root"])
    model_config = load_json(model_root / "config.json")
    probe = preregistration["exact_probe"]
    dataset = load_json(ROOT / probe["dataset"])
    actual_ids = [dataset[index]["id"] for index in probe["row_indices"]]
    rows = [dataset[index] for index in probe["row_indices"]]
    outputs = [
        ROOT / preregistration["result_paths"]["aggregate_json"],
        ROOT / preregistration["result_paths"]["aggregate_markdown"],
        ROOT / preregistration["result_paths"]["result_lock"],
        *[
            ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"
            for repeat in range(1, 4)
        ],
    ]
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_before_backward": preregistration["status"]
        == "frozen_before_any_qwen3_4b_backward_pass",
        "frozen_bindings": all(row["match"] for row in bindings),
        "official_model_files_bound": all(row["match"] for row in model_bindings),
        "environment_exact": environment["python_version"]
        == expected_environment["python_version"]
        and environment["packages"] == expected_environment["packages"]
        and environment["pip_freeze_sha256"] == expected_environment["pip_freeze_sha256"],
        "official_model_metadata_exact": model_config["model_type"]
        == model_contract["model_type"]
        and model_config["architectures"] == [model_contract["architecture"]]
        and model_config["num_hidden_layers"] == model_contract["num_hidden_layers"]
        and model_config["torch_dtype"] == "bfloat16",
        "exact_batch_ids": actual_ids == probe["row_ids"],
        "dataset_provenance_safe": all(
            row["provenance"]["synthetic"] is True
            and row["provenance"]["source_independent"] is True
            and row["provenance"]["contains_target_utterance"] is False
            and row["provenance"]["contains_benchmark_item"] is False
            for row in rows
        ),
        "full_depth_lora": preregistration["adapter_initialization_contract"][
            "converted_layers"
        ]
        == model_contract["num_hidden_layers"],
        "candidate_probe_contract": probe["gradient_accumulation"] == 1
        and probe["micro_steps"] == 1
        and probe["optimizer_steps"] == 0
        and probe["gradient_checkpointing"] is False,
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
                "target_person_utterances",
                "benchmark_items",
            )
        ),
    }
    return {
        "schema": "uruha_rightbrain_qwen3_4b_trainability_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "frozen_bindings": bindings,
        "external_model_bindings": model_bindings,
        "environment": environment,
        "actual_row_ids": actual_ids,
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_three_qwen3_4b_zero_update_repetitions_only"
                if all(checks.values())
                else "refuse_qwen3_4b_trainability_probe"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain Qwen3-4B 可訓練性探針",
        "",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 模型：Qwen3-4B-Instruct-2507 官方固定快照",
        "- adapter：全 36 層 rank-32 deterministic fresh LoRA",
        "- 執行：固定一筆、無 checkpoint、零 optimizer step",
        "- 人格與 production 修改：0",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["checks"].items()
    )
    return "\n".join(lines) + "\n"


def build_lock(report):
    if not report["decision"]["passed"]:
        raise RuntimeError("Refusing to lock failed Qwen3-4B trainability probe")
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    paths = [
        DEFAULT_PREREGISTRATION,
        Path(__file__),
        RUNNER,
        ROOT / "run_rightbrain_mlx_gradient_repro_v1.py",
        ROOT / "configs/rightbrain_mlx_no_checkpoint_repro_v1_result_lock.json",
        ROOT / "reports/rightbrain_mlx_no_checkpoint_repro_v1_result.json",
        ROOT / "configs/rightbrain_mlx_gradient_repro_v1_environment.txt",
        ROOT / preregistration["exact_probe"]["dataset"],
        DEFAULT_REPORT_JSON,
        *[Path(row["path"]) for row in preregistration["external_model_bindings"]],
    ]
    return {
        "schema": "uruha_rightbrain_qwen3_4b_trainability_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [file_binding(path) for path in paths],
        "authorization": {
            "exact_zero_update_repetitions": [1, 2, 3],
            "micro_steps_each": 1,
            "gradient_accumulation": 1,
            "optimizer_steps": 0,
            "training_backend": "mlx",
            "gradient_checkpointing": False,
            "base_model": preregistration["local_model_contract"]["base_model"],
            "fresh_adapter_initialization_exact": True,
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
