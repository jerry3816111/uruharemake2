#!/usr/bin/env python3
"""Run the source-separated active-head Qwen3 multi-batch learning probe."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import resource
import statistics
import time
from collections import defaultdict
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx_lm import load

import build_rightbrain_qwen3_active_head_multibatch_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as model_common
import run_rightbrain_qwen3_active_head_full_chain_v1 as full_chain
import run_rightbrain_qwen3_active_head_single_update_v1 as single_update


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
    authorization = lock["authorization"]
    environment = common._environment()
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == prereg["local_environment"]
        and authorization["repetitions"] == list(construction.REPEATS)
        and authorization["train_row_indices"]
        == list(construction.TRAIN_ROW_INDICES)
        and authorization["holdout_row_indices"]
        == list(construction.HOLDOUT_ROW_INDICES)
        and authorization["train_schedule"] == list(construction.TRAIN_SCHEDULE)
        and authorization["source_id_overlap_exact"] == 0
        and authorization["target_overlap_exact"] == 0
        and authorization["allocated_sequence_length"]
        == construction.ALLOCATED_TOKENS
        and authorization["full_transformer_layers"] == 36
        and authorization["lora_enabled_layers"] == 36
        and authorization["device"] == "gpu"
        and authorization["optimizer_contract"] == prereg["optimizer_contract"]
        and authorization["micro_steps_each"] == len(construction.TRAIN_SCHEDULE)
        and authorization["optimizer_updates_each"]
        == len(construction.TRAIN_SCHEDULE)
        and authorization["gradient_checkpointing"] is False
        and not authorization["adapter_or_model_save"]
        and not authorization["text_generation"]
        and not authorization["target_person_utterance_training"]
        and not authorization["benchmark_training"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def _prepare_batches(prereg, tokenizer):
    rows = construction.load_json(ROOT / prereg["dataset_contract"]["path"])
    batches, details, token_hash = construction.canonical_batches(tokenizer, rows)
    if token_hash != prereg["token_contract"]["sha256"]:
        raise RuntimeError("Multi-batch token hash drifted")
    if details != prereg["token_contract"]["details"]:
        raise RuntimeError("Multi-batch token details drifted")
    prepared = {}
    for index, batch in batches.items():
        prepared[index] = {
            "input_ids": mx.array(batch["input_ids"][None, :]),
            "labels": mx.array(batch["labels"][None, :]),
            "positions": mx.array(
                batch["positions"]["positions"], dtype=mx.int32
            ),
            "position_contract": batch["positions"],
            "row": rows[index],
        }
    return prepared, token_hash


def _objective_for(batch):
    return functools.partial(
        full_chain._active_full_chain_loss,
        positions=batch["positions"],
    )


def _evaluate(model, prepared, indices):
    model.eval()
    rows = []
    for index in indices:
        batch = prepared[index]
        loss = _objective_for(batch)(
            model,
            batch["input_ids"],
            batch["labels"],
        )
        mx.eval(loss)
        value = float(loss.item())
        if not math.isfinite(value):
            raise RuntimeError(f"Non-finite evaluation loss for row {index}")
        row = batch["row"]
        rows.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "loss": value,
            }
        )
    return rows


def _group_mean(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row["loss"])
    return {name: statistics.fmean(values) for name, values in sorted(grouped.items())}


def _paired_summary(before, after):
    before_by_id = {row["row_id"]: row for row in before}
    after_by_id = {row["row_id"]: row for row in after}
    if set(before_by_id) != set(after_by_id):
        raise RuntimeError("Pre/post evaluation row IDs differ")
    pairs = []
    for row_id in sorted(before_by_id):
        pre = before_by_id[row_id]
        post = after_by_id[row_id]
        if any(
            pre[key] != post[key]
            for key in ("row_index", "source_id", "provider_id", "memory_mode")
        ):
            raise RuntimeError(f"Evaluation metadata drift for {row_id}")
        pairs.append(
            {
                "row_id": row_id,
                "row_index": pre["row_index"],
                "source_id": pre["source_id"],
                "provider_id": pre["provider_id"],
                "memory_mode": pre["memory_mode"],
                "pre_loss": pre["loss"],
                "post_loss": post["loss"],
                "loss_decrease": pre["loss"] - post["loss"],
                "loss_increase": post["loss"] - pre["loss"],
                "improved": post["loss"] < pre["loss"],
            }
        )
    pre_mean = statistics.fmean(row["pre_loss"] for row in pairs)
    post_mean = statistics.fmean(row["post_loss"] for row in pairs)
    provider_decreases = {}
    memory_mode_decreases = {}
    for key, output in (
        ("provider_id", provider_decreases),
        ("memory_mode", memory_mode_decreases),
    ):
        groups = sorted({row[key] for row in pairs})
        for group in groups:
            selected = [row for row in pairs if row[key] == group]
            output[group] = statistics.fmean(
                row["loss_decrease"] for row in selected
            )
    return {
        "pre_mean_loss": pre_mean,
        "post_mean_loss": post_mean,
        "mean_loss_decrease": pre_mean - post_mean,
        "improved_row_count": sum(row["improved"] for row in pairs),
        "row_count": len(pairs),
        "worst_row_loss_increase": max(row["loss_increase"] for row in pairs),
        "provider_mean_loss_decreases": provider_decreases,
        "memory_mode_mean_loss_decreases": memory_mode_decreases,
        "pairs": pairs,
    }


def _trajectory_sha256(train_steps, train_summary, holdout_summary):
    payload = {
        "train_steps": [
            {
                "update": row["update"],
                "row_index": row["row_index"],
                "loss_before_update": row["loss_before_update"],
                "raw_gradient_sha256": row["raw_gradient"]["sha256"],
                "clipped_gradient_sha256": row["clipped_gradient"]["sha256"],
            }
            for row in train_steps
        ],
        "train_pairs": train_summary["pairs"],
        "holdout_pairs": holdout_summary["pairs"],
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 multi-batch execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    probe = prereg["exact_probe"]
    optimizer_contract = prereg["optimizer_contract"]
    started = time.perf_counter()
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, tokenizer = load(
            prereg["local_model_contract"]["snapshot_root"],
            tokenizer_config={"trust_remote_code": True},
        )
        mx.eval(model.parameters())
        base = model_common._base_contract(model, prereg)
        if not base["exact"]:
            raise RuntimeError(f"Base contract mismatch: {base}")
        adapter = model_common._initialize_adapter(model, prereg)
        if not adapter["exact"]:
            raise RuntimeError(f"Adapter contract mismatch: {adapter}")
        prepared, token_hash = _prepare_batches(prereg, tokenizer)
        before_hash = common._parameter_sha256(model.trainable_parameters())
        before_parameters = single_update._host_parameter_snapshot(
            model.trainable_parameters()
        )

        pre_train = _evaluate(model, prepared, construction.TRAIN_ROW_INDICES)
        pre_holdout = _evaluate(model, prepared, construction.HOLDOUT_ROW_INDICES)

        optimizer = optim.AdamW(
            learning_rate=float(optimizer_contract["learning_rate"]),
            betas=optimizer_contract["betas"],
            eps=float(optimizer_contract["epsilon"]),
            weight_decay=float(optimizer_contract["weight_decay"]),
            bias_correction=bool(optimizer_contract["bias_correction"]),
        )
        mx.random.seed(int(probe["random_seed"]))
        train_steps = []
        for update, row_index in enumerate(construction.TRAIN_SCHEDULE, start=1):
            batch = prepared[row_index]
            model.train()
            loss_and_grad = nn.value_and_grad(model, _objective_for(batch))
            loss, raw_gradients = loss_and_grad(
                model,
                batch["input_ids"],
                batch["labels"],
            )
            mx.eval(loss, raw_gradients)
            loss_value = float(loss.item())
            raw_gradient = common._gradient_measurements(raw_gradients)
            clipped_gradients, raw_norm = optim.clip_grad_norm(
                raw_gradients,
                float(optimizer_contract["maximum_gradient_norm"]),
            )
            mx.eval(clipped_gradients, raw_norm)
            clipped_gradient = common._gradient_measurements(clipped_gradients)
            if not math.isfinite(loss_value):
                raise RuntimeError(f"Non-finite train loss at update {update}")
            if not raw_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite raw gradient at update {update}")
            if not clipped_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite clipped gradient at update {update}")
            optimizer.update(model, clipped_gradients)
            mx.eval(model.trainable_parameters(), optimizer.state)
            if int(optimizer.step.item()) != update:
                raise RuntimeError(f"Optimizer step drift at update {update}")
            source = batch["row"]
            raw_norm_value = float(raw_norm.item())
            train_steps.append(
                {
                    "update": update,
                    "epoch": 1 + (update - 1) // len(construction.TRAIN_ROW_INDICES),
                    "row_index": row_index,
                    "row_id": source["id"],
                    "source_id": source["source_id"],
                    "provider_id": source["provider_id"],
                    "memory_mode": source["memory_mode"],
                    "loss_before_update": loss_value,
                    "raw_gradient": raw_gradient,
                    "raw_norm_from_clip_operator": raw_norm_value,
                    "clip_scale": min(
                        1.0,
                        float(optimizer_contract["maximum_gradient_norm"])
                        / (raw_norm_value + 1e-6),
                    ),
                    "clipped_gradient": clipped_gradient,
                    "optimizer_step_after_update": int(optimizer.step.item()),
                }
            )

        post_train = _evaluate(model, prepared, construction.TRAIN_ROW_INDICES)
        post_holdout = _evaluate(model, prepared, construction.HOLDOUT_ROW_INDICES)
        train_summary = _paired_summary(pre_train, post_train)
        holdout_summary = _paired_summary(pre_holdout, post_holdout)
        final_hash = common._parameter_sha256(model.trainable_parameters())
        optimizer_state_hash = common._parameter_sha256(optimizer.state)
        delta = single_update._parameter_delta(
            before_parameters, model.trainable_parameters()
        )
        if not delta["all_elements_finite"]:
            raise RuntimeError("Non-finite multi-batch parameter delta")
        trajectory_hash = _trajectory_sha256(
            train_steps, train_summary, holdout_summary
        )
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_active_head_multibatch_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "full_transformer_layers": 36,
                "lora_enabled_layers": 36,
                "optimizer": optimizer_contract,
                "optimizer_updates": int(optimizer.step.item()),
                "train_rows": len(construction.TRAIN_ROW_INDICES),
                "holdout_rows": len(construction.HOLDOUT_ROW_INDICES),
                "epochs": 2,
                "gradient_checkpointing_enabled": False,
                "adapter_or_model_saved": False,
                "text_generated": False,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "token_contract_sha256": token_hash,
            "source_split_contract": prereg["source_split_contract"],
            "pre_evaluation": {
                "train": pre_train,
                "holdout": pre_holdout,
                "train_mean_by_provider": _group_mean(pre_train, "provider_id"),
                "holdout_mean_by_provider": _group_mean(
                    pre_holdout, "provider_id"
                ),
                "holdout_mean_by_memory_mode": _group_mean(
                    pre_holdout, "memory_mode"
                ),
            },
            "train_steps": train_steps,
            "post_evaluation": {
                "train": post_train,
                "holdout": post_holdout,
                "train_mean_by_provider": _group_mean(post_train, "provider_id"),
                "holdout_mean_by_provider": _group_mean(
                    post_holdout, "provider_id"
                ),
                "holdout_mean_by_memory_mode": _group_mean(
                    post_holdout, "memory_mode"
                ),
            },
            "train_summary": train_summary,
            "holdout_summary": holdout_summary,
            "trajectory_sha256": trajectory_hash,
            "parameter_update": {
                "before_sha256": before_hash,
                "after_sha256": final_hash,
                "hash_changed": before_hash != final_hash,
                **delta,
            },
            "optimizer_state": {
                "step": int(optimizer.step.item()),
                "sha256": optimizer_state_hash,
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
            "schema": "uruha_rightbrain_qwen3_active_head_multibatch_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
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


def _classify(checks, completed=True):
    if not completed:
        return "multibatch_execution_failed"
    if not checks["all_values_finite"]:
        return "multibatch_nonfinite"
    if not checks["parameter_hash_changed_and_delta_nonzero"]:
        return "multibatch_did_not_mutate_parameters"
    if not checks["trajectory_reproducible"]:
        return "multibatch_not_reproducible"
    if not checks["mutation_within_bounds"]:
        return "multibatch_exceeded_mutation_bounds"
    if not checks["train_loss_learned"]:
        return "multibatch_train_learning_failed"
    if not checks["holdout_loss_generalized"]:
        return "multibatch_holdout_generalization_failed"
    return "active_head_multibatch_holdout_learning_confirmed"


def _measure(rows, prereg):
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    deltas = [row["parameter_update"]["l2_norm"] for row in rows]
    mean_delta = statistics.fmean(deltas)
    delta_cv = statistics.pstdev(deltas) / max(mean_delta, 1e-300)
    all_values_finite = all(
        all(
            math.isfinite(step["loss_before_update"])
            and step["raw_gradient"]["all_elements_finite"]
            and step["clipped_gradient"]["all_elements_finite"]
            for step in row["train_steps"]
        )
        and all(
            math.isfinite(pair["pre_loss"])
            and math.isfinite(pair["post_loss"])
            for pair in row["train_summary"]["pairs"]
            + row["holdout_summary"]["pairs"]
        )
        and row["parameter_update"]["all_elements_finite"]
        for row in rows
    )
    parameter_changed = all(
        row["parameter_update"]["hash_changed"] for row in rows
    ) and min(deltas) > confirm["parameter_delta_l2_minimum_exclusive"]
    trajectory_reproducible = (
        len({row["trajectory_sha256"] for row in rows}) == 1
        and len({row["parameter_update"]["after_sha256"] for row in rows}) == 1
        and len({row["optimizer_state"]["sha256"] for row in rows}) == 1
        and delta_cv <= confirm["parameter_delta_cv_maximum"]
    )
    mutation_within_bounds = (
        max(deltas) <= confirm["parameter_delta_l2_maximum"]
        and max(row["parameter_update"]["relative_l2_norm"] for row in rows)
        <= confirm["parameter_relative_delta_maximum"]
        and max(
            row["parameter_update"]["maximum_absolute_delta"] for row in rows
        )
        <= confirm["parameter_max_absolute_delta_maximum"]
        and max(
            step["clipped_gradient"]["norm"]
            for row in rows
            for step in row["train_steps"]
        )
        <= confirm["clipped_gradient_norm_maximum"]
        and all(
            row["optimizer_state"]["step"] == confirm["optimizer_step_exact"]
            for row in rows
        )
    )
    train_loss_learned = all(
        row["train_summary"]["mean_loss_decrease"]
        >= confirm["train_mean_loss_decrease_minimum"]
        for row in rows
    )
    holdout_loss_generalized = all(
        row["holdout_summary"]["mean_loss_decrease"]
        >= confirm["holdout_mean_loss_decrease_minimum"]
        and row["holdout_summary"]["improved_row_count"]
        >= confirm["holdout_improved_row_count_minimum"]
        and row["holdout_summary"]["worst_row_loss_increase"]
        <= confirm["holdout_worst_row_loss_increase_maximum"]
        and min(
            row["holdout_summary"]["provider_mean_loss_decreases"].values()
        )
        >= confirm["holdout_each_provider_mean_loss_decrease_minimum"]
        and max(
            -value
            for value in row["holdout_summary"][
                "memory_mode_mean_loss_decreases"
            ].values()
        )
        <= confirm["holdout_each_memory_mode_mean_loss_increase_maximum"]
        for row in rows
    )
    all_contracts_exact = all(
        row["base_contract"]["exact"]
        and row["adapter_contract"]["exact"]
        and row["token_contract_sha256"] == prereg["token_contract"]["sha256"]
        and row["source_split_contract"]["source_id_overlap_count"]
        == confirm["source_id_overlap_exact"]
        and row["source_split_contract"]["exact_target_overlap_count"]
        == confirm["target_overlap_exact"]
        and row["runtime_contract"]["optimizer_updates"]
        == confirm["optimizer_step_exact"]
        and row["runtime_contract"]["adapter_or_model_saved"] is False
        and row["runtime_contract"]["text_generated"] is False
        for row in rows
    )
    checks = {
        "all_values_finite": all_values_finite,
        "parameter_hash_changed_and_delta_nonzero": parameter_changed,
        "trajectory_reproducible": trajectory_reproducible,
        "mutation_within_bounds": mutation_within_bounds,
        "train_loss_learned": train_loss_learned,
        "holdout_loss_generalized": holdout_loss_generalized,
        "all_contracts_exact": all_contracts_exact,
    }
    measurements = {
        "train_pre_mean_losses": [
            row["train_summary"]["pre_mean_loss"] for row in rows
        ],
        "train_post_mean_losses": [
            row["train_summary"]["post_mean_loss"] for row in rows
        ],
        "train_mean_loss_decreases": [
            row["train_summary"]["mean_loss_decrease"] for row in rows
        ],
        "holdout_pre_mean_losses": [
            row["holdout_summary"]["pre_mean_loss"] for row in rows
        ],
        "holdout_post_mean_losses": [
            row["holdout_summary"]["post_mean_loss"] for row in rows
        ],
        "holdout_mean_loss_decreases": [
            row["holdout_summary"]["mean_loss_decrease"] for row in rows
        ],
        "holdout_improved_row_counts": [
            row["holdout_summary"]["improved_row_count"] for row in rows
        ],
        "holdout_worst_row_loss_increases": [
            row["holdout_summary"]["worst_row_loss_increase"] for row in rows
        ],
        "holdout_provider_mean_loss_decreases": [
            row["holdout_summary"]["provider_mean_loss_decreases"] for row in rows
        ],
        "holdout_memory_mode_mean_loss_decreases": [
            row["holdout_summary"]["memory_mode_mean_loss_decreases"] for row in rows
        ],
        "trajectory_hashes": [row["trajectory_sha256"] for row in rows],
        "parameter_delta_l2_norms": deltas,
        "parameter_delta_mean": mean_delta,
        "parameter_delta_cv": delta_cv,
        "parameter_relative_l2_norms": [
            row["parameter_update"]["relative_l2_norm"] for row in rows
        ],
        "parameter_max_absolute_deltas": [
            row["parameter_update"]["maximum_absolute_delta"] for row in rows
        ],
        "after_parameter_hashes": [
            row["parameter_update"]["after_sha256"] for row in rows
        ],
        "optimizer_state_hashes": [row["optimizer_state"]["sha256"] for row in rows],
        "maximum_raw_gradient_norms": [
            max(step["raw_gradient"]["norm"] for step in row["train_steps"])
            for row in rows
        ],
        "maximum_clipped_gradient_norms": [
            max(step["clipped_gradient"]["norm"] for step in row["train_steps"])
            for row in rows
        ],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in rows],
        "durations_seconds": [row["resource"]["duration_seconds"] for row in rows],
    }
    return measurements, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Qwen3 multi-batch execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite multi-batch aggregate")
    rows = [
        construction.load_json(_result_path(prereg, repeat))
        for repeat in construction.REPEATS
    ]
    completed = all(row.get("execution_success") is True for row in rows)
    if completed:
        measurements, checks = _measure(rows, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure") for row in rows if not row.get("execution_success")
            ]
        }
        checks = {
            "all_values_finite": False,
            "parameter_hash_changed_and_delta_nonzero": False,
            "trajectory_reproducible": False,
            "mutation_within_bounds": False,
            "train_loss_learned": False,
            "holdout_loss_generalized": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    result = {
        "schema": "uruha_rightbrain_qwen3_active_head_multibatch_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": {
            "experiment_complete": completed,
            "passed": passed,
            "outcome": outcome,
            "fresh_generation_probe_authorized": passed,
            "authorized_next_step": (
                "preregister_ephemeral_multibatch_fresh_generation_probe"
                if passed
                else "diagnose_active_head_multibatch_or_holdout_failure"
            ),
            "authorize_persistent_training": False,
            "authorize_persona_training": False,
            "authorize_adapter_save": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "repeats": [
                construction.file_binding(_result_path(prereg, repeat))
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
        "interpretation_limits": prereg["interpretation_limits"],
    }
    construction.atomic_json(output_json, result)
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 active-head 多批次 train／holdout 結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 3 次全部完成且通過：`{passed}`",
                f"- train mean loss：`{measurements.get('train_pre_mean_losses', ['NA'])[0]}` → `{measurements.get('train_post_mean_losses', ['NA'])[0]}`",
                f"- holdout mean loss：`{measurements.get('holdout_pre_mean_losses', ['NA'])[0]}` → `{measurements.get('holdout_post_mean_losses', ['NA'])[0]}`",
                f"- holdout improved rows：`{measurements.get('holdout_improved_row_counts', ['NA'])[0]}` / 16",
                f"- parameter delta L2：`{measurements.get('parameter_delta_l2_norms', ['NA'])[0]}`",
                "- 僅代表同一合成課程家族內、未見 source_id 的 loss transfer。",
                "- adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_active_head_multibatch_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
        ],
        "decision": result["decision"],
        "authorization": {
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, result_lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.repeat is not None:
            parser.error("--aggregate cannot be combined with --repeat")
        output = aggregate()["decision"]
    else:
        if args.repeat is None:
            parser.error("--repeat is required")
        row = run_repeat(args.repeat)
        output = {
            "repeat": args.repeat,
            "execution_success": row["execution_success"],
            "train_mean_loss_decrease": row.get("train_summary", {}).get(
                "mean_loss_decrease"
            ),
            "holdout_mean_loss_decrease": row.get("holdout_summary", {}).get(
                "mean_loss_decrease"
            ),
            "holdout_improved_rows": row.get("holdout_summary", {}).get(
                "improved_row_count"
            ),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
