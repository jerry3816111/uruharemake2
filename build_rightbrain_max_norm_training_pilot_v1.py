#!/usr/bin/env python3
"""Freeze the matched RightBrain max-norm training pilot before execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as prior_construction


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_max_norm_training_pilot_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_max_norm_training_pilot_v1_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_max_norm_training_pilot_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_max_norm_training_pilot_v1_construction.md"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_max_norm_training_pilot_v1_execution_lock.json"
RUNNER = ROOT / "run_rightbrain_max_norm_training_pilot_v1.py"
CONDITIONS = ("control_0_3", "treatment_3_0")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_binding(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _validate_frozen_bindings(preregistration):
    rows = []
    for expected in preregistration["frozen_bindings"]:
        path = ROOT / expected["path"]
        actual = sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": expected["path"],
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual,
                "match": actual == expected["sha256"],
            }
        )
    return rows


def _validate_model(preregistration):
    contract = preregistration["local_model_contract"]
    snapshot_root = Path(contract["snapshot_root"])
    adapter_root = ROOT / contract["initial_adapter"]["path"]
    config_path = adapter_root / "adapter_config.json"
    model_path = adapter_root / "adapter_model.safetensors"
    return {
        "snapshot_root_exists": snapshot_root.is_dir(),
        "adapter_config_match": config_path.is_file()
        and sha256_file(config_path) == contract["initial_adapter"]["adapter_config_sha256"],
        "adapter_model_match": model_path.is_file()
        and sha256_file(model_path) == contract["initial_adapter"]["adapter_model_sha256"],
        "local_only": bool(contract["local_only"]),
        "paid_cloud_disabled": not bool(contract["paid_cloud_inference_allowed"]),
        "base_weights_frozen": not bool(contract["base_weights_trainable"]),
    }


def build_report(preregistration_path=DEFAULT_PREREGISTRATION):
    preregistration = load_json(preregistration_path)
    schedule = preregistration["controlled_training_schedule"]
    conditions = preregistration["conditions"]
    dataset_path = ROOT / schedule["dataset"]
    holdout_path = ROOT / preregistration["policy_discrimination_evaluation"]["holdout"]
    dataset = load_json(dataset_path)
    holdout = load_json(holdout_path)
    binding_rows = _validate_frozen_bindings(preregistration)
    model_checks = _validate_model(preregistration)
    holdout_audit = prior_construction.audit_holdout(holdout, dataset)
    output_paths = {
        condition: ROOT / conditions[condition]["output_directory"] for condition in CONDITIONS
    }
    result_paths = preregistration["result_paths"]
    result_outputs = [
        ROOT / result_paths["aggregate_json"],
        ROOT / result_paths["aggregate_markdown"],
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
        == "frozen_before_any_pilot_training_update",
        "exact_conditions": tuple(conditions) == CONDITIONS,
        "only_max_norm_differs": conditions["control_0_3"]["maximum_gradient_norm"] == 0.3
        and conditions["treatment_3_0"]["maximum_gradient_norm"] == 3.0,
        "same_dataset_for_both_conditions": schedule["dataset_rows"] == len(dataset) == 80,
        "exact_micro_steps": schedule["micro_steps_exact"] == 80,
        "exact_optimizer_updates": schedule["optimizer_updates_exact"] == 10,
        "exact_gradient_accumulation": schedule["gradient_accumulation"] == 8,
        "frozen_bindings": all(row["match"] for row in binding_rows),
        "local_model_contract": all(model_checks.values()),
        "holdout_source_separation": holdout_audit["passed"],
        "runner_exists": RUNNER.is_file(),
        "temporary_output_directories_absent": all(not path.exists() for path in output_paths.values()),
        "result_outputs_absent": all(not path.exists() for path in result_outputs),
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
        "schema": "uruha_rightbrain_max_norm_training_pilot_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "checks": checks,
        "frozen_bindings": binding_rows,
        "model_checks": model_checks,
        "holdout_audit": holdout_audit,
        "output_directories": {key: str(path) for key, path in output_paths.items()},
        "decision": {
            "passed": all(checks.values()),
            "outcome": (
                "authorize_exact_two_condition_pilot_only"
                if all(checks.values())
                else "refuse_pilot_execution"
            ),
        },
    }


def render_markdown(report):
    lines = [
        "# RightBrain max_norm 公平訓練試驗建構報告",
        "",
        f"- 結果：`{report['decision']['outcome']}`",
        "- 唯一變因：`max_norm=0.3` 對 `max_norm=3.0`",
        "- 每組：80 micro-steps、10 optimizer updates、同一份資料與 seed",
        "- 正式 runtime 修改：`0`",
        "",
        "## 建構檢查",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "通過建構只允許執行兩個暫存 adapter 的小型試驗，不允許正式上線或人格相似度主張。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_execution_lock(report, preregistration_path=DEFAULT_PREREGISTRATION):
    if not report["decision"]["passed"]:
        raise RuntimeError("Refusing to lock a failed construction")
    repo_paths = [
        Path(preregistration_path),
        Path(__file__),
        RUNNER,
        ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json",
        ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_holdout.json",
        ROOT / "run_rightbrain_role_curriculum_training_pilot_v1.py",
        ROOT / "build_rightbrain_role_curriculum_training_pilot_v1.py",
        ROOT / "configs/rightbrain_adamw_clipping_effect_v2_result_lock.json",
        ROOT / "reports/rightbrain_adamw_clipping_effect_v2_formal_result.json",
        DEFAULT_REPORT_JSON,
    ]
    return {
        "schema": "uruha_rightbrain_max_norm_training_pilot_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "repo_bindings": [file_binding(path) for path in repo_paths],
        "authorization": {
            "exact_condition_isolated_training": True,
            "conditions": list(CONDITIONS),
            "micro_steps_per_condition": 80,
            "optimizer_updates_per_condition": 10,
            "condition_isolated_evaluation": True,
            "policy_comparisons_per_condition": 40,
            "fresh_generations_per_condition": 80,
            "production_runtime_change": False,
            "production_adapter_replacement": False,
            "persona_similarity_claim": False,
            "public_impersonation": False,
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
        lock = build_execution_lock(report)
        atomic_json(DEFAULT_EXECUTION_LOCK, lock)


if __name__ == "__main__":
    main()
