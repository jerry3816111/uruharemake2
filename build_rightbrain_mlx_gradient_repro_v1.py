#!/usr/bin/env python3
"""Freeze the Apple MLX zero-update RightBrain gradient probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_mlx_gradient_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_mlx_gradient_repro_v1_preregistration.json"
DEFAULT_ENVIRONMENT = ROOT / "configs/rightbrain_mlx_gradient_repro_v1_environment.txt"
DEFAULT_AMENDMENT = (
    ROOT / "configs/rightbrain_mlx_gradient_repro_v1_protocol_amendment_01.json"
)
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_mlx_gradient_repro_v1_execution_lock.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_mlx_gradient_repro_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_mlx_gradient_repro_v1_construction.md"
RUNNER = ROOT / "run_rightbrain_mlx_gradient_repro_v1.py"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_binding(path):
    path = Path(path)
    try:
        display_path = str(path.relative_to(ROOT))
        scope = "repository"
    except ValueError:
        display_path = str(path)
        scope = "external_local"
    return {"path": display_path, "scope": scope, "sha256": sha256_file(path)}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def atomic_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _resolve_binding(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def inspect_environment(preregistration):
    executable = preregistration["local_environment"]["python_executable"]
    script = """
import json, platform
from importlib.metadata import version
packages = ['mlx', 'mlx-lm', 'mlx-metal', 'numpy', 'safetensors', 'transformers']
print(json.dumps({'python_version': platform.python_version(), 'packages': {name: version(name) for name in packages}}))
"""
    completed = subprocess.run(
        [executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    freeze = subprocess.run(
        [executable, "-m", "pip", "freeze"],
        check=True,
        capture_output=True,
    ).stdout
    return {
        **json.loads(completed.stdout),
        "pip_freeze_sha256": hashlib.sha256(freeze).hexdigest(),
    }


def build_report():
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    bindings = []
    for expected in preregistration["frozen_bindings"]:
        path = _resolve_binding(expected["path"])
        actual = sha256_file(path) if path.is_file() else None
        bindings.append(
            {**expected, "actual_sha256": actual, "match": actual == expected["sha256"]}
        )
    environment = inspect_environment(preregistration)
    expected_environment = preregistration["local_environment"]
    model_root = Path(preregistration["local_model_contract"]["snapshot_root"])
    model_metadata = []
    for name, expected_hash in preregistration["local_model_contract"][
        "metadata_sha256"
    ].items():
        path = model_root / name
        actual = sha256_file(path) if path.is_file() else None
        model_metadata.append(
            {
                "path": str(path),
                "expected_sha256": expected_hash,
                "actual_sha256": actual,
                "match": actual == expected_hash,
            }
        )
    probe = preregistration["exact_probe"]
    amendment = load_json(DEFAULT_AMENDMENT) if DEFAULT_AMENDMENT.exists() else None
    dataset = load_json(ROOT / probe["dataset"])
    actual_ids = [dataset[index]["id"] for index in probe["row_indices"]]
    outputs = [
        ROOT / preregistration["result_paths"]["aggregate_json"],
        ROOT / preregistration["result_paths"]["aggregate_markdown"],
        ROOT / preregistration["result_paths"]["result_lock"],
        *[
            ROOT / f"{preregistration['result_paths']['repeat_prefix']}{repeat}.json"
            for repeat in range(1, probe["isolated_process_repetitions"] + 1)
        ],
    ]
    checks = {
        "experiment_id": preregistration["experiment_id"] == EXPERIMENT_ID,
        "frozen_before_backward": preregistration["status"]
        == "frozen_before_any_mlx_backward_pass",
        "frozen_bindings": all(row["match"] for row in bindings),
        "environment_file_exact": sha256_file(DEFAULT_ENVIRONMENT)
        == expected_environment["pip_freeze_sha256"],
        "environment_runtime_exact": environment["python_version"]
        == expected_environment["python_version"]
        and environment["packages"] == expected_environment["packages"]
        and environment["pip_freeze_sha256"] == expected_environment["pip_freeze_sha256"],
        "model_metadata_exact": all(row["match"] for row in model_metadata),
        "exact_batch_ids": actual_ids == probe["row_ids"]
        and probe["row_indices"] == [63, 50, 60, 77, 2, 59, 78, 36],
        "three_repetitions": probe["isolated_process_repetitions"] == 3,
        "eight_microsteps_zero_updates": probe["micro_steps"]
        == probe["gradient_accumulation"]
        == 8
        and probe["optimizer_steps"] == 0,
        "single_backend_change": probe["base_activation_dtype"]
        == "mlx.core.bfloat16"
        and probe["trainable_adapter_dtype"] == "mlx.core.float32"
        and probe["gradient_checkpointing"] is True
        and preregistration["adapter_conversion_contract"]["dropout"] == 0.08,
        "exact_adapter_mapping_contract": preregistration["adapter_conversion_contract"][
            "source_tensor_count"
        ]
        == preregistration["adapter_conversion_contract"]["target_tensor_count"]
        == 392
        and preregistration["adapter_conversion_contract"]["trainable_parameter_count"]
        == 80740352,
        "runner_exists": RUNNER.is_file(),
        "pre_backward_amendment_valid": amendment is not None
        and amendment["experiment_id"] == EXPERIMENT_ID
        and amendment["status"] == "frozen_before_any_mlx_backward_pass"
        and amendment["trigger"]["backward_passes_completed"] == 0
        and amendment["trigger"]["optimizer_steps"] == 0
        and sha256_file(ROOT / amendment["trigger"]["path"])
        == amendment["trigger"]["sha256"]
        and amendment["authorized_change"]["scope"]
        == "tokenizer_api_compatibility_only"
        and amendment["authorized_change"]["expected_token_and_label_sha256_unchanged"]
        == probe["canonical_token_and_label_sha256"],
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
        "schema": "uruha_rightbrain_mlx_gradient_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "frozen_bindings": bindings,
        "model_metadata": model_metadata,
        "environment": environment,
        "actual_row_ids": actual_ids,
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_three_mlx_zero_update_repetitions_only"
                if all(checks.values())
                else "refuse_mlx_gradient_probe"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain MLX 梯度重現探針建構",
        "",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 唯一改動：PyTorch MPS -> Apple MLX",
        "- 基底與 adapter：保持 Qwen2.5-7B + v10",
        "- checkpointing：保持開啟",
        "- dropout：保持 0.08",
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
        raise RuntimeError("Refusing to lock failed MLX gradient probe")
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    model_root = Path(preregistration["local_model_contract"]["snapshot_root"])
    paths = [
        DEFAULT_PREREGISTRATION,
        DEFAULT_ENVIRONMENT,
        DEFAULT_AMENDMENT,
        ROOT / "reports/rightbrain_mlx_gradient_repro_v1_preflight_failure_01.json",
        Path(__file__),
        RUNNER,
        ROOT / preregistration["exact_probe"]["dataset"],
        ROOT / "configs/rightbrain_gradient_float16_repro_v1_result_lock.json",
        ROOT / "reports/rightbrain_token_contract_audit_v1_result.json",
        ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_config.json",
        ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_model.safetensors",
        DEFAULT_REPORT_JSON,
        *[
            model_root / name
            for name in preregistration["local_model_contract"]["metadata_sha256"]
        ],
    ]
    return {
        "schema": "uruha_rightbrain_mlx_gradient_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [file_binding(path) for path in paths],
        "authorization": {
            "exact_zero_update_repetitions": [1, 2, 3],
            "micro_steps_each": 8,
            "optimizer_steps": 0,
            "training_backend": "mlx",
            "gradient_checkpointing": True,
            "adapter_conversion_exact": True,
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
