#!/usr/bin/env python3
"""Run isolated Qwen3 active-token tied-head VJP probes."""

from __future__ import annotations

import argparse
import functools
import json
import math
import resource
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load

import build_rightbrain_qwen3_active_head_vjp_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as full_runner
import run_rightbrain_qwen3_compact_length_repro_v1 as metric_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    environment = common._environment()
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == prereg["local_environment"]
        and authorization["conditions"] == list(construction.CONDITIONS)
        and authorization["allocated_sequence_length"] == 512
        and authorization["active_position_count"] == 16
        and authorization["vocabulary_size"] == 151936
        and authorization["base_compute_dtype"] == "bfloat16"
        and authorization["device"] == "gpu"
        and authorization["repetitions_each"] == list(construction.REPEATS)
        and authorization["fully_counterbalanced_execution_schedule"]
        == construction.EXECUTION_SCHEDULE
        and authorization["optimizer_steps"] == 0
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, condition, repeat):
    prefix = prereg["result_paths"]["repeat_prefix"]
    return ROOT / f"{prefix}{condition}_repeat_{repeat}.json"


def _dense_mask_after_loss(model, hidden, targets, mask, positions):
    del positions
    safe_targets = mx.where(mask, targets, mx.zeros_like(targets))
    logits = model.model.embed_tokens.as_linear(hidden)
    per_token = nn.losses.cross_entropy(logits, safe_targets)
    return (per_token * mask).astype(mx.float32).sum() / mask.sum()


def _dense_gather_before_loss(model, hidden, targets, mask, positions):
    del mask
    dense_logits = model.model.embed_tokens.as_linear(hidden)
    flat_logits = dense_logits.reshape(-1, dense_logits.shape[-1])
    flat_targets = targets.reshape(-1)
    active_logits = mx.take(flat_logits, positions, axis=0)
    active_targets = mx.take(flat_targets, positions, axis=0)
    return nn.losses.cross_entropy(active_logits, active_targets).astype(mx.float32).mean()


def _active_gather_before_head(model, hidden, targets, mask, positions):
    del mask
    flat_hidden = hidden.reshape(-1, hidden.shape[-1])
    flat_targets = targets.reshape(-1)
    active_hidden = mx.take(flat_hidden, positions, axis=0)
    active_targets = mx.take(flat_targets, positions, axis=0)
    active_logits = model.model.embed_tokens.as_linear(active_hidden)
    return nn.losses.cross_entropy(active_logits, active_targets).astype(mx.float32).mean()


OBJECTIVES = {
    "dense_mask_after_loss": _dense_mask_after_loss,
    "dense_gather_before_loss": _dense_gather_before_loss,
    "active_gather_before_head": _active_gather_before_head,
}


def _measure_array(array):
    return common._gradient_measurements({"boundary": array})


def _load_contracts(prereg):
    model, tokenizer = load(
        prereg["local_model_contract"]["snapshot_root"],
        tokenizer_config={"trust_remote_code": True},
    )
    mx.eval(model.parameters())
    base = full_runner._base_contract(model, prereg)
    if not base["exact"]:
        raise RuntimeError(f"Base contract mismatch: {base}")
    adapter = full_runner._initialize_adapter(model, prereg)
    if not adapter["exact"]:
        raise RuntimeError(f"Adapter contract mismatch: {adapter}")
    batch, source = construction.parent_common.parent_common.canonical_batch(tokenizer)
    expected = prereg["batch_contract"]
    for key, value in expected.items():
        if batch[key] != value:
            raise RuntimeError(f"Batch contract mismatch {key}: {batch[key]} != {value}")
    actual_positions = construction.active_position_contract(batch)
    if actual_positions != {
        key: prereg["active_position_contract"][key]
        for key in ("positions", "count", "sha256")
    }:
        raise RuntimeError("Active-position contract mismatch")
    return model, batch, source, base, adapter, actual_positions


def run_repeat(condition, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if condition not in construction.CONDITIONS:
        raise ValueError("condition outside preregistered values")
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 active-head execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, condition, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {condition} repeat {repeat}")
    probe = prereg["exact_probe"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, batch, source, base, adapter, position_contract = _load_contracts(prereg)
        input_ids = mx.array(batch["input_ids"][None, :])
        labels = mx.array(batch["labels"][None, :])
        inputs = input_ids[:, :-1]
        targets = input_ids[:, 1:]
        mask = labels[:, 1:] != -100
        positions = mx.array(position_contract["positions"], dtype=mx.int32)
        before_hash = common._parameter_sha256(model.trainable_parameters())
        model.train()
        mx.random.seed(int(probe["random_seed"]))
        hidden = model.model(inputs)
        mx.eval(hidden)
        detached_hidden = mx.stop_gradient(hidden)
        objective = functools.partial(
            OBJECTIVES[condition],
            model,
            targets=targets,
            mask=mask,
            positions=positions,
        )
        loss, hidden_gradient = mx.value_and_grad(objective)(detached_hidden)
        mx.eval(loss, hidden_gradient)
        loss_value = float(loss.item())
        gradient = _measure_array(hidden_gradient)
        if not math.isfinite(loss_value):
            raise RuntimeError(f"Non-finite {condition} loss")
        if not gradient["all_elements_finite"]:
            raise RuntimeError(f"Non-finite {condition} gradient")
        after_hash = common._parameter_sha256(model.trainable_parameters())
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_active_head_vjp_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "condition": condition,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "base_compute_dtype": "bfloat16",
                "dense_head_position_count": 511,
                "active_head_position_count": 16,
                "optimizer_instantiated": False,
                "optimizer_steps": 0,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "batch_contract": {**prereg["batch_contract"], "source": source},
            "active_position_contract": position_contract,
            "forward_boundary": _measure_array(hidden),
            "loss": loss_value,
            "gradient": gradient,
            "parameter_integrity": {
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "unchanged": before_hash == after_hash,
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_active_memory_bytes": mx.get_active_memory(),
                "mlx_cache_memory_bytes": mx.get_cache_memory(),
                "mlx_peak_memory_bytes": peak,
                "process_peak_resident_memory_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            },
            "boundaries": prereg["boundaries"],
        }
    except Exception as error:
        message = str(error)
        result = {
            "schema": "uruha_rightbrain_qwen3_active_head_vjp_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "condition": condition,
            "repeat": repeat,
            "execution_success": False,
            "failure": {
                "error_type": type(error).__name__,
                "message": message,
                "out_of_memory": "memory" in message.lower()
                or "alloc" in message.lower(),
                "nonfinite": "non-finite" in message.lower()
                or "nonfinite" in message.lower(),
            },
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_peak_memory_bytes": mx.get_peak_memory(),
            },
            "boundaries": prereg["boundaries"],
        }
    construction.atomic_json(output_path, result)
    return result


def _classify(stability, semantic_equivalent=True, completed=True):
    if not completed:
        return "active_head_vjp_execution_failed"
    if not semantic_equivalent:
        return "head_conditions_not_semantically_equivalent"
    if stability["dense_mask_after_loss"]:
        return "dense_parent_drift_not_reproduced"
    dense_stable = stability["dense_gather_before_loss"]
    active_stable = stability["active_gather_before_head"]
    if dense_stable and active_stable:
        return "post_head_masking_path_is_sufficient_to_reproduce_drift"
    if not dense_stable and active_stable:
        return "projecting_ignored_positions_is_sufficient_to_reproduce_drift"
    if not dense_stable and not active_stable:
        return "active_head_projection_still_reproduces_drift"
    return "active_gather_path_introduces_drift"


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 active-head execution lock validation failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite Qwen3 active-head aggregate")
    rows = {
        condition: [
            construction.load_json(_result_path(prereg, condition, repeat))
            for repeat in construction.REPEATS
        ]
        for condition in construction.CONDITIONS
    }
    completed = all(
        row.get("execution_success") is True
        for condition_rows in rows.values()
        for row in condition_rows
    )
    metrics = {}
    stability = {condition: False for condition in construction.CONDITIONS}
    checks = {"all_repetitions_complete": completed}
    loss_by_condition = {}
    semantic_equivalent = False
    if completed:
        limits = prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        for condition in construction.CONDITIONS:
            metrics[condition], stability[condition] = metric_common._measure(
                rows[condition], limits
            )
            loss_by_condition[condition] = sorted({row["loss"] for row in rows[condition]})
            checks[f"{condition}_contracts_exact"] = all(
                row["base_contract"]["exact"]
                and row["adapter_contract"]["exact"]
                and row["parameter_integrity"]["unchanged"]
                and row["gradient"]["all_elements_finite"]
                and row["active_position_contract"]["sha256"]
                == prereg["active_position_contract"]["sha256"]
                for row in rows[condition]
            )
            checks[f"{condition}_forward_hash_identical"] = (
                len({row["forward_boundary"]["sha256"] for row in rows[condition]})
                == 1
            )
            checks[f"{condition}_reproducible"] = stability[condition]
        all_losses = [row["loss"] for values in rows.values() for row in values]
        semantic_equivalent = (
            max(all_losses) - min(all_losses)
            <= prereg["semantic_equivalence_contract"][
                "maximum_absolute_loss_delta_across_conditions"
            ]
        )
        checks["semantic_loss_equivalence"] = semantic_equivalent
        checks["forward_hash_identical_across_conditions"] = (
            len(
                {
                    row["forward_boundary"]["sha256"]
                    for condition_rows in rows.values()
                    for row in condition_rows
                }
            )
            == 1
        )
    else:
        metrics["failures"] = [
            row.get("failure")
            for condition_rows in rows.values()
            for row in condition_rows
            if not row.get("execution_success")
        ]

    outcome = _classify(stability, semantic_equivalent, completed)
    next_steps = {
        "post_head_masking_path_is_sufficient_to_reproduce_drift": (
            "preregister_dense_logits_active_loss_training_probe"
        ),
        "projecting_ignored_positions_is_sufficient_to_reproduce_drift": (
            "preregister_zero_update_active_head_training_path_probe"
        ),
        "active_head_projection_still_reproduces_drift": (
            "localize_full_vocab_matmul_vjp_dimensions"
        ),
        "active_gather_path_introduces_drift": (
            "localize_unique_index_gather_vjp"
        ),
        "dense_parent_drift_not_reproduced": (
            "increase_dense_control_repetitions_before_mask_claim"
        ),
        "head_conditions_not_semantically_equivalent": (
            "repair_equivalence_without_interpreting_stability"
        ),
        "active_head_vjp_execution_failed": (
            "repair_execution_without_changing_hypothesis"
        ),
    }
    active_candidate = (
        completed
        and semantic_equivalent
        and stability["active_gather_before_head"]
        and not stability["dense_mask_after_loss"]
    )
    result = {
        "schema": "uruha_rightbrain_qwen3_active_head_vjp_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": metrics,
        "loss_values_by_condition": loss_by_condition,
        "semantic_equivalent": semantic_equivalent,
        "stability_by_condition": stability,
        "checks": checks,
        "decision": {
            "experiment_complete": completed,
            "outcome": outcome,
            "active_head_zero_update_probe_authorized": active_candidate,
            "authorized_next_step": next_steps[outcome],
            "authorize_training": False,
            "authorize_persona_training": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, condition, repeat))
                for condition in construction.CONDITIONS
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
    }
    construction.atomic_json(output_json, result)
    rows_md = [
        f"| {condition} | {'穩定' if stability[condition] else '不穩定'} | "
        f"{metrics.get(condition, {}).get('gradient_norm_coefficient_of_variation', 'NA')} | "
        f"{metrics.get(condition, {}).get('gradient_norm_max_to_min_ratio', 'NA')} | "
        f"{metrics.get(condition, {}).get('gradient_hashes_identical', 'NA')} |"
        for condition in construction.CONDITIONS
    ]
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 有效 token LM head VJP 結果",
                "",
                f"- 判定：`{outcome}`",
                f"- loss 語意等價門檻：`{semantic_equivalent}`",
                "",
                "| mask / head 路徑 | 18 次判定 | gradient CV | max/min | hash 相同 |",
                "|:---|:---:|---:|---:|:---:|",
                *rows_md,
                "",
                "- 正式訓練／人格訓練／上線授權：`False`",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_vjp_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "training": False,
            "persona_training": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=construction.CONDITIONS)
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.condition is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with a repeat")
        output = aggregate()["decision"]
    else:
        if args.condition is None or args.repeat is None:
            parser.error("--condition and --repeat are required")
        row = run_repeat(args.condition, args.repeat)
        output = {
            "condition": args.condition,
            "repeat": args.repeat,
            "execution_success": row["execution_success"],
            "loss": row.get("loss"),
            "gradient_norm": row.get("gradient", {}).get("norm"),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
