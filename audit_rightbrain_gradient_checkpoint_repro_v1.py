#!/usr/bin/env python3
"""Finalize the preregistered resource-safety rejection of checkpointing-off."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_gradient_checkpoint_repro_v1 as construction
import run_rightbrain_gradient_checkpoint_repro_v1 as runner


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "configs/rightbrain_gradient_checkpoint_repro_v1_protocol_amendment_01.json"
RESULT_JSON = ROOT / "reports/rightbrain_gradient_checkpoint_repro_v1_result.json"
RESULT_MD = ROOT / "reports/rightbrain_gradient_checkpoint_repro_v1_result.md"
RESULT_LOCK = ROOT / "configs/rightbrain_gradient_checkpoint_repro_v1_result_lock.json"


def audit():
    preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    repeat_1_path = runner._result_path(preregistration, 1)
    repeat = construction.load_json(repeat_1_path)
    amendment = construction.load_json(AMENDMENT)
    limit = preregistration["exact_probe"]["driver_allocated_memory_bytes_maximum"]
    repeat_2 = runner._result_path(preregistration, 2)
    repeat_3 = runner._result_path(preregistration, 3)
    checks = {
        "execution_lock_valid": runner.validate_lock()["passed"],
        "repeat_1_failed": repeat["execution_success"] is False,
        "repeat_1_memory_failure": repeat["failure"]["out_of_memory"],
        "memory_limit_exceeded": repeat["resource"]["peak_mps_driver_allocated_memory_bytes"]
        > limit,
        "remaining_repetitions_not_executed": not repeat_2.exists() and not repeat_3.exists(),
        "safety_stop_recorded": amendment["decision"][
            "stop_remaining_repetitions_for_resource_safety"
        ],
    }
    return {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_result_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "execution_mode": "preregistered_early_stop_after_first_resource_failure",
        "inputs": {
            "preregistration": construction.file_binding(construction.DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(construction.DEFAULT_EXECUTION_LOCK),
            "protocol_amendment": construction.file_binding(AMENDMENT),
            "repeat_1": construction.file_binding(repeat_1_path),
        },
        "measurements": {
            "successful_repeat_count": 0,
            "attempted_repeat_count": 1,
            "peak_mps_driver_allocated_memory_bytes": repeat["resource"][
                "peak_mps_driver_allocated_memory_bytes"
            ],
            "preregistered_memory_limit_bytes": limit,
            "bytes_over_limit": repeat["resource"]["peak_mps_driver_allocated_memory_bytes"]
            - limit,
            "ratio_to_limit": repeat["resource"]["peak_mps_driver_allocated_memory_bytes"]
            / limit,
            "duration_seconds": repeat["resource"]["duration_seconds"],
            "failure": repeat["failure"],
        },
        "checks": checks,
        "decision": {
            "passed": False,
            "outcome": "checkpointing_off_exceeds_local_memory_limit",
            "authorized_next_step": "zero_update_float16_base_dtype_probe_with_checkpointing_enabled",
            "authorize_model_training_now": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "boundaries": preregistration["boundaries"],
    }


def render_markdown(result):
    measurements = result["measurements"]
    return "\n".join(
        [
            "# RightBrain checkpointing=off 梯度探針結果",
            "",
            f"- 判定：`{result['decision']['outcome']}`",
            f"- MPS driver 記憶體：`{measurements['peak_mps_driver_allocated_memory_bytes'] / 1024**3:.2f} GiB`",
            f"- 預註冊上限：`{measurements['preregistered_memory_limit_bytes'] / 1024**3:.2f} GiB`",
            f"- 超出比例：`{measurements['ratio_to_limit']:.3f}x`",
            "- 後續 repetitions：`依安全規則停止`",
            "- optimizer step：`0`",
            "- 正式 runtime 修改：`0`",
        ]
    ) + "\n"


def write_result():
    result = audit()
    if not all(result["checks"].values()):
        raise RuntimeError("Checkpoint resource rejection evidence is incomplete")
    construction.atomic_json(RESULT_JSON, result)
    construction.atomic_text(RESULT_MD, render_markdown(result))
    lock = {
        "schema": "uruha_rightbrain_gradient_checkpoint_repro_result_lock_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(RESULT_JSON),
            construction.file_binding(RESULT_MD),
            construction.file_binding(AMENDMENT),
            construction.file_binding(Path(__file__)),
            result["inputs"]["repeat_1"],
        ],
        "decision": result["decision"],
        "authorization": {
            "zero_update_float16_base_dtype_probe": True,
            "additional_checkpoint_off_repetitions": False,
            "model_training_in_this_experiment": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(RESULT_LOCK, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = write_result() if args.write else audit()
    print(json.dumps(result["decision"] | result["measurements"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
