#!/usr/bin/env python3
"""Run the matched SFT-versus-provider-pair CPO objective probe."""

from __future__ import annotations

import argparse
import functools
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
from mlx.utils import tree_map
from mlx_lm import load

import build_rightbrain_qwen3_provider_pair_cpo_v1 as construction
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
        and authorization["conditions"] == list(construction.CONDITIONS)
        and authorization["repetitions"] == list(construction.REPEATS)
        and authorization["execution_schedule"]
        == [list(item) for item in construction.EXECUTION_SCHEDULE]
        and authorization["train_row_indices"]
        == list(construction.TRAIN_ROW_INDICES)
        and authorization["train_schedule"] == list(construction.TRAIN_SCHEDULE)
        and authorization["train_eval_row_indices"]
        == list(construction.TRAIN_EVAL_ROW_INDICES)
        and authorization["holdout_row_indices"]
        == list(construction.HOLDOUT_ROW_INDICES)
        and authorization["pairwise_beta"] == construction.PAIRWISE_BETA
        and authorization["pairwise_weights"] == construction.PAIRWISE_WEIGHTS
        and authorization["allocated_sequence_length"]
        == construction.ALLOCATED_TOKENS
        and authorization["full_transformer_layers"] == 36
        and authorization["lora_enabled_layers"] == 36
        and authorization["device"] == "gpu"
        and authorization["optimizer_contract"] == prereg["optimizer_contract"]
        and authorization["optimizer_updates_each"]
        == len(construction.TRAIN_SCHEDULE)
        and authorization["gradient_checkpointing"] is False
        and authorization["adapter_or_model_save"] is False
        and authorization["text_generation"] is False
        and authorization["target_person_utterance_training"] is False
        and authorization["benchmark_training"] is False
        and authorization["production_runtime_change"] is False
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, condition, repeat):
    prefix = prereg["result_paths"]["condition_prefix"]
    return ROOT / f"{prefix}{condition}_repeat_{repeat}.json"


def _prepare_pair_batches(prereg, tokenizer):
    rows = construction.load_json(construction.DATASET_PATH)
    batches, details, token_hash = construction.canonical_pair_batches(tokenizer, rows)
    if token_hash != prereg["token_contract"]["sha256"]:
        raise RuntimeError("Provider-pair token hash drifted")
    if details != prereg["token_contract"]["details"]:
        raise RuntimeError("Provider-pair token details drifted")
    prepared = {}
    for index, pair in batches.items():
        prepared[index] = {
            "preferred": _to_mx_batch(pair["preferred"]),
            "rejected": _to_mx_batch(pair["rejected"]),
            "row": rows[index],
            "rejected_row": rows[pair["rejected_index"]],
            "rejected_index": pair["rejected_index"],
        }
    return prepared, token_hash


def _to_mx_batch(batch):
    return {
        "input_ids": mx.array(batch["input_ids"][None, :]),
        "labels": mx.array(batch["labels"][None, :]),
        "positions": mx.array(batch["positions"]["positions"], dtype=mx.int32),
        "position_contract": batch["positions"],
    }


def _objective_for(batch):
    return functools.partial(
        full_chain._active_full_chain_loss,
        positions=batch["positions"],
    )


def _evaluate_pair_rows(model, prepared, indices):
    model.eval()
    rows = []
    for index in indices:
        pair = prepared[index]
        preferred_loss = _objective_for(pair["preferred"])(
            model,
            pair["preferred"]["input_ids"],
            pair["preferred"]["labels"],
        )
        rejected_loss = _objective_for(pair["rejected"])(
            model,
            pair["rejected"]["input_ids"],
            pair["rejected"]["labels"],
        )
        mx.eval(preferred_loss, rejected_loss)
        preferred_value = float(preferred_loss.item())
        rejected_value = float(rejected_loss.item())
        if not all(math.isfinite(value) for value in (preferred_value, rejected_value)):
            raise RuntimeError(f"Non-finite pair evaluation for row {index}")
        row = pair["row"]
        rejected_row = pair["rejected_row"]
        margin = rejected_value - preferred_value
        rows.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "rejected_row_index": pair["rejected_index"],
                "rejected_row_id": rejected_row["id"],
                "rejected_provider_id": rejected_row["provider_id"],
                "preferred_nll": preferred_value,
                "rejected_nll": rejected_value,
                "provider_margin": margin,
                "correct_preference": margin > 0.0,
            }
        )
    return rows


def _group_mean(rows, key, value):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row[value])
    return {
        name: statistics.fmean(values) for name, values in sorted(grouped.items())
    }


def _pair_summary(rows):
    return {
        "row_count": len(rows),
        "preferred_nll_mean": statistics.fmean(
            row["preferred_nll"] for row in rows
        ),
        "rejected_nll_mean": statistics.fmean(row["rejected_nll"] for row in rows),
        "provider_margin_mean": statistics.fmean(
            row["provider_margin"] for row in rows
        ),
        "correct_preference_rate": statistics.fmean(
            row["correct_preference"] for row in rows
        ),
        "correct_preference_count": sum(row["correct_preference"] for row in rows),
        "provider_margin_by_provider": _group_mean(
            rows, "provider_id", "provider_margin"
        ),
        "provider_margin_by_memory_mode": _group_mean(
            rows, "memory_mode", "provider_margin"
        ),
    }


def _paired_change(before, after):
    before_by_id = {row["row_id"]: row for row in before}
    after_by_id = {row["row_id"]: row for row in after}
    if set(before_by_id) != set(after_by_id):
        raise RuntimeError("Pre/post pair-evaluation row IDs differ")
    pairs = []
    for row_id in sorted(before_by_id):
        pre = before_by_id[row_id]
        post = after_by_id[row_id]
        for key in (
            "row_index",
            "source_id",
            "provider_id",
            "memory_mode",
            "rejected_row_id",
        ):
            if pre[key] != post[key]:
                raise RuntimeError(f"Pair-evaluation metadata drift for {row_id}")
        pairs.append(
            {
                "row_id": row_id,
                "source_id": pre["source_id"],
                "provider_id": pre["provider_id"],
                "memory_mode": pre["memory_mode"],
                "pre_preferred_nll": pre["preferred_nll"],
                "post_preferred_nll": post["preferred_nll"],
                "preferred_nll_decrease": pre["preferred_nll"]
                - post["preferred_nll"],
                "pre_provider_margin": pre["provider_margin"],
                "post_provider_margin": post["provider_margin"],
                "provider_margin_delta": post["provider_margin"]
                - pre["provider_margin"],
                "pre_correct_preference": pre["correct_preference"],
                "post_correct_preference": post["correct_preference"],
            }
        )
    return {
        "preferred_nll_decrease_mean": statistics.fmean(
            row["preferred_nll_decrease"] for row in pairs
        ),
        "provider_margin_delta_mean": statistics.fmean(
            row["provider_margin_delta"] for row in pairs
        ),
        "improved_margin_count": sum(
            row["provider_margin_delta"] > 0 for row in pairs
        ),
        "regressed_margin_count": sum(
            row["provider_margin_delta"] < 0 for row in pairs
        ),
        "pairs": pairs,
    }


def _softplus_negative_margin(beta, margin):
    value = -beta * margin
    return max(value, 0.0) + math.log1p(math.exp(-abs(value)))


def _pair_gradient_coefficient(pairwise_weight, beta, margin):
    scaled = beta * margin
    if scaled >= 0:
        sigmoid_negative = math.exp(-scaled) / (1.0 + math.exp(-scaled))
    else:
        sigmoid_negative = 1.0 / (1.0 + math.exp(scaled))
    return pairwise_weight * beta * sigmoid_negative


def _condition_contract(prereg, condition):
    if condition not in construction.CONDITIONS:
        raise ValueError("condition outside preregistered values")
    contract = prereg["conditions"][condition]
    if contract["preferred_sft_weight"] != 1.0:
        raise RuntimeError("Unexpected preferred SFT weight")
    if contract["pairwise_weight"] != construction.PAIRWISE_WEIGHTS[condition]:
        raise RuntimeError("Pairwise weight drifted")
    if contract["pairwise_beta"] != construction.PAIRWISE_BETA:
        raise RuntimeError("Pairwise beta drifted")
    return contract


def run_condition(condition, repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if condition not in construction.CONDITIONS:
        raise ValueError("condition outside preregistered values")
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Provider-pair CPO execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    contract = _condition_contract(prereg, condition)
    output_path = _result_path(prereg, condition, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {condition} repeat {repeat}")
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
        prepared, token_hash = _prepare_pair_batches(prereg, tokenizer)
        initial_hash = common._parameter_sha256(model.trainable_parameters())
        initial_parameters = single_update._host_parameter_snapshot(
            model.trainable_parameters()
        )
        pre_train_rows = _evaluate_pair_rows(
            model, prepared, construction.TRAIN_EVAL_ROW_INDICES
        )
        pre_holdout_rows = _evaluate_pair_rows(
            model, prepared, construction.HOLDOUT_ROW_INDICES
        )
        pre_train_summary = _pair_summary(pre_train_rows)
        pre_holdout_summary = _pair_summary(pre_holdout_rows)

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
            pair = prepared[row_index]
            model.train()
            preferred_loss_and_grad = nn.value_and_grad(
                model, _objective_for(pair["preferred"])
            )
            rejected_loss_and_grad = nn.value_and_grad(
                model, _objective_for(pair["rejected"])
            )
            preferred_loss, preferred_gradients = preferred_loss_and_grad(
                model,
                pair["preferred"]["input_ids"],
                pair["preferred"]["labels"],
            )
            mx.eval(preferred_loss, preferred_gradients)
            rejected_loss, rejected_gradients = rejected_loss_and_grad(
                model,
                pair["rejected"]["input_ids"],
                pair["rejected"]["labels"],
            )
            mx.eval(rejected_loss, rejected_gradients)
            preferred_value = float(preferred_loss.item())
            rejected_value = float(rejected_loss.item())
            if not all(math.isfinite(value) for value in (preferred_value, rejected_value)):
                raise RuntimeError(f"Non-finite pair loss at update {update}")
            preferred_gradient = common._gradient_measurements(preferred_gradients)
            rejected_gradient = common._gradient_measurements(rejected_gradients)
            if not preferred_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite preferred gradient at update {update}")
            if not rejected_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite rejected gradient at update {update}")
            margin = rejected_value - preferred_value
            coefficient = _pair_gradient_coefficient(
                float(contract["pairwise_weight"]),
                float(contract["pairwise_beta"]),
                margin,
            )
            combined_gradients = tree_map(
                lambda preferred, rejected: (1.0 + coefficient) * preferred
                - coefficient * rejected,
                preferred_gradients,
                rejected_gradients,
            )
            mx.eval(combined_gradients)
            combined_gradient = common._gradient_measurements(combined_gradients)
            if not combined_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite combined gradient at update {update}")
            clipped_gradients, raw_norm = optim.clip_grad_norm(
                combined_gradients,
                float(optimizer_contract["maximum_gradient_norm"]),
            )
            mx.eval(clipped_gradients, raw_norm)
            clipped_gradient = common._gradient_measurements(clipped_gradients)
            if not clipped_gradient["all_elements_finite"]:
                raise RuntimeError(f"Non-finite clipped gradient at update {update}")
            pair_loss = _softplus_negative_margin(
                float(contract["pairwise_beta"]), margin
            )
            objective_loss = preferred_value + float(
                contract["pairwise_weight"]
            ) * pair_loss
            optimizer.update(model, clipped_gradients)
            mx.eval(model.trainable_parameters(), optimizer.state)
            row = pair["row"]
            rejected_row = pair["rejected_row"]
            train_steps.append(
                {
                    "update": update,
                    "row_index": row_index,
                    "row_id": row["id"],
                    "source_id": row["source_id"],
                    "provider_id": row["provider_id"],
                    "memory_mode": row["memory_mode"],
                    "variant_index": row["variant_index"],
                    "rejected_row_index": pair["rejected_index"],
                    "rejected_row_id": rejected_row["id"],
                    "rejected_provider_id": rejected_row["provider_id"],
                    "preferred_nll_before_update": preferred_value,
                    "rejected_nll_before_update": rejected_value,
                    "provider_margin_before_update": margin,
                    "pairwise_loss_before_update": pair_loss,
                    "pair_gradient_coefficient": coefficient,
                    "objective_loss_before_update": objective_loss,
                    "preferred_gradient": preferred_gradient,
                    "rejected_gradient": rejected_gradient,
                    "combined_gradient": combined_gradient,
                    "raw_norm_from_clip_operator": float(raw_norm.item()),
                    "clipped_gradient": clipped_gradient,
                    "optimizer_step_after_update": int(optimizer.step.item()),
                }
            )

        post_train_rows = _evaluate_pair_rows(
            model, prepared, construction.TRAIN_EVAL_ROW_INDICES
        )
        post_holdout_rows = _evaluate_pair_rows(
            model, prepared, construction.HOLDOUT_ROW_INDICES
        )
        post_train_summary = _pair_summary(post_train_rows)
        post_holdout_summary = _pair_summary(post_holdout_rows)
        train_change = _paired_change(pre_train_rows, post_train_rows)
        holdout_change = _paired_change(pre_holdout_rows, post_holdout_rows)
        final_hash = common._parameter_sha256(model.trainable_parameters())
        optimizer_hash = common._parameter_sha256(optimizer.state)
        parameter_update = single_update._parameter_delta(
            initial_parameters, model.trainable_parameters()
        )
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_condition_v1",
            "experiment_id": EXPERIMENT_ID,
            "condition": condition,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "condition_contract": contract,
            "runtime_contract": {
                "device": str(mx.default_device()),
                "optimizer_updates": int(optimizer.step.item()),
                "preferred_backward_calls": len(train_steps),
                "rejected_backward_calls": len(train_steps),
                "text_generation_calls": 0,
                "adapter_or_model_saved": False,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "token_contract_sha256": token_hash,
            "initial_parameter_sha256": initial_hash,
            "final_parameter_sha256": final_hash,
            "optimizer_state_sha256": optimizer_hash,
            "train_steps": train_steps,
            "pre_train_evaluation": {
                "rows": pre_train_rows,
                "summary": pre_train_summary,
            },
            "post_train_evaluation": {
                "rows": post_train_rows,
                "summary": post_train_summary,
            },
            "train_change": train_change,
            "pre_holdout_evaluation": {
                "rows": pre_holdout_rows,
                "summary": pre_holdout_summary,
            },
            "post_holdout_evaluation": {
                "rows": post_holdout_rows,
                "summary": post_holdout_summary,
            },
            "holdout_change": holdout_change,
            "parameter_update": parameter_update,
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
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
            "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_condition_v1",
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


def _condition_rows(prereg):
    return {
        condition: [
            construction.load_json(_result_path(prereg, condition, repeat))
            for repeat in construction.REPEATS
        ]
        for condition in construction.CONDITIONS
    }


def _all_finite(row):
    if not row.get("execution_success"):
        return False
    return all(
        math.isfinite(step["preferred_nll_before_update"])
        and math.isfinite(step["rejected_nll_before_update"])
        and math.isfinite(step["provider_margin_before_update"])
        and math.isfinite(step["objective_loss_before_update"])
        and step["preferred_gradient"]["all_elements_finite"]
        and step["rejected_gradient"]["all_elements_finite"]
        and step["combined_gradient"]["all_elements_finite"]
        and step["clipped_gradient"]["all_elements_finite"]
        for step in row["train_steps"]
    )


def _measure(grouped, prereg):
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    control = grouped["sft_control"]
    candidate = grouped["provider_pair_cpo"]
    initial_hashes = {
        row["initial_parameter_sha256"] for rows in grouped.values() for row in rows
    }
    pre_summaries = [
        row["pre_holdout_evaluation"]["summary"]
        for rows in grouped.values()
        for row in rows
    ]
    condition_reproducible = {}
    for condition, rows in grouped.items():
        condition_reproducible[condition] = (
            len({row["final_parameter_sha256"] for row in rows}) == 1
            and len({row["optimizer_state_sha256"] for row in rows}) == 1
            and len(
                {
                    construction.canonical_json_sha256(row["train_steps"])
                    for row in rows
                }
            )
            == 1
            and len(
                {
                    construction.canonical_json_sha256(
                        row["post_holdout_evaluation"]
                    )
                    for row in rows
                }
            )
            == 1
        )
    control_row = control[0]
    candidate_row = candidate[0]
    control_post_holdout = control_row["post_holdout_evaluation"]["summary"]
    candidate_post_holdout = candidate_row["post_holdout_evaluation"]["summary"]
    control_holdout_change = control_row["holdout_change"]
    candidate_holdout_change = candidate_row["holdout_change"]
    control_post_train = control_row["post_train_evaluation"]["summary"]
    candidate_post_train = candidate_row["post_train_evaluation"]["summary"]
    mutation_ok = all(
        row["parameter_update"]["all_elements_finite"]
        and row["parameter_update"]["l2_norm"]
        <= confirm["parameter_delta_l2_maximum"]
        and row["parameter_update"]["relative_l2_norm"]
        <= confirm["parameter_relative_delta_maximum"]
        and row["parameter_update"]["maximum_absolute_delta"]
        <= confirm["parameter_max_absolute_delta_maximum"]
        and max(step["clipped_gradient"]["norm"] for step in row["train_steps"])
        <= confirm["clipped_gradient_norm_maximum"]
        and row["resource"]["mlx_peak_memory_bytes"]
        <= confirm["peak_memory_bytes_maximum"]
        for rows in grouped.values()
        for row in rows
    )
    checks = {
        "all_values_finite_and_update_count_exact": all(
            _all_finite(row)
            and row["runtime_contract"]["optimizer_updates"]
            == confirm["optimizer_step_exact"]
            and row["runtime_contract"]["preferred_backward_calls"]
            == confirm["optimizer_step_exact"]
            and row["runtime_contract"]["rejected_backward_calls"]
            == confirm["optimizer_step_exact"]
            for rows in grouped.values()
            for row in rows
        ),
        "initial_parameter_hash_equal_between_conditions": len(initial_hashes) == 1,
        "pre_holdout_metrics_equal_between_conditions": len(
            {construction.canonical_json_sha256(summary) for summary in pre_summaries}
        )
        == 1,
        "control_and_candidate_each_reproducible": all(
            condition_reproducible.values()
        ),
        "candidate_holdout_margin_delta_positive": candidate_holdout_change[
            "provider_margin_delta_mean"
        ]
        > 0.0,
        "candidate_holdout_margin_delta_exceeds_control": candidate_holdout_change[
            "provider_margin_delta_mean"
        ]
        > control_holdout_change["provider_margin_delta_mean"],
        "candidate_post_holdout_margin_exceeds_control": candidate_post_holdout[
            "provider_margin_mean"
        ]
        > control_post_holdout["provider_margin_mean"],
        "candidate_post_correct_preference_rate_not_below_control": candidate_post_holdout[
            "correct_preference_rate"
        ]
        >= control_post_holdout["correct_preference_rate"],
        "candidate_post_preferred_nll_within_control_bound": candidate_post_holdout[
            "preferred_nll_mean"
        ]
        - control_post_holdout["preferred_nll_mean"]
        <= confirm["candidate_post_preferred_nll_regression_vs_control_maximum"],
        "candidate_train_final_margin_exceeds_control": candidate_post_train[
            "provider_margin_mean"
        ]
        > control_post_train["provider_margin_mean"],
        "mutation_within_bounds": mutation_ok,
        "all_contracts_exact": all(
            row["token_contract_sha256"] == prereg["token_contract"]["sha256"]
            and row["condition_contract"] == prereg["conditions"][condition]
            and row["runtime_contract"]["text_generation_calls"] == 0
            and row["runtime_contract"]["adapter_or_model_saved"] is False
            for condition, rows in grouped.items()
            for row in rows
        ),
    }
    measurements = {
        "condition_reproducible": condition_reproducible,
        "initial_parameter_hashes": sorted(initial_hashes),
        "control": {
            "post_train": control_post_train,
            "post_holdout": control_post_holdout,
            "train_change": control_row["train_change"],
            "holdout_change": control_holdout_change,
        },
        "candidate": {
            "post_train": candidate_post_train,
            "post_holdout": candidate_post_holdout,
            "train_change": candidate_row["train_change"],
            "holdout_change": candidate_holdout_change,
        },
        "candidate_minus_control": {
            "post_holdout_margin": candidate_post_holdout["provider_margin_mean"]
            - control_post_holdout["provider_margin_mean"],
            "holdout_margin_delta": candidate_holdout_change[
                "provider_margin_delta_mean"
            ]
            - control_holdout_change["provider_margin_delta_mean"],
            "post_holdout_correct_preference_rate": candidate_post_holdout[
                "correct_preference_rate"
            ]
            - control_post_holdout["correct_preference_rate"],
            "post_holdout_preferred_nll": candidate_post_holdout[
                "preferred_nll_mean"
            ]
            - control_post_holdout["preferred_nll_mean"],
            "post_train_margin": candidate_post_train["provider_margin_mean"]
            - control_post_train["provider_margin_mean"],
        },
        "parameter_delta_l2_norms": {
            condition: [row["parameter_update"]["l2_norm"] for row in rows]
            for condition, rows in grouped.items()
        },
        "peak_memory_bytes": {
            condition: [row["resource"]["mlx_peak_memory_bytes"] for row in rows]
            for condition, rows in grouped.items()
        },
        "durations_seconds": {
            condition: [row["resource"]["duration_seconds"] for row in rows]
            for condition, rows in grouped.items()
        },
    }
    return measurements, checks


def _classify(checks, completed=True):
    if not completed:
        return "provider_pair_cpo_execution_failed"
    if not checks["control_and_candidate_each_reproducible"]:
        return "provider_pair_cpo_not_reproducible"
    margin_keys = (
        "candidate_holdout_margin_delta_positive",
        "candidate_holdout_margin_delta_exceeds_control",
        "candidate_post_holdout_margin_exceeds_control",
        "candidate_post_correct_preference_rate_not_below_control",
        "candidate_train_final_margin_exceeds_control",
    )
    if not all(checks[key] for key in margin_keys):
        return "provider_pair_cpo_holdout_margin_not_improved"
    if not checks["candidate_post_preferred_nll_within_control_bound"]:
        return "provider_pair_cpo_preferred_likelihood_regressed"
    if not checks["mutation_within_bounds"]:
        return "provider_pair_cpo_mutation_out_of_bounds"
    if not all(checks.values()):
        return "provider_pair_cpo_execution_failed"
    return "provider_pair_cpo_holdout_margin_confirmed"


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Provider-pair CPO execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite provider-pair CPO aggregate")
    grouped = _condition_rows(prereg)
    completed = all(
        row.get("execution_success") is True
        for rows in grouped.values()
        for row in rows
    )
    if completed:
        measurements, checks = _measure(grouped, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure")
                for rows in grouped.values()
                for row in rows
                if not row.get("execution_success")
            ]
        }
        checks = {
            "all_values_finite_and_update_count_exact": False,
            "initial_parameter_hash_equal_between_conditions": False,
            "pre_holdout_metrics_equal_between_conditions": False,
            "control_and_candidate_each_reproducible": False,
            "candidate_holdout_margin_delta_positive": False,
            "candidate_holdout_margin_delta_exceeds_control": False,
            "candidate_post_holdout_margin_exceeds_control": False,
            "candidate_post_correct_preference_rate_not_below_control": False,
            "candidate_post_preferred_nll_within_control_bound": False,
            "candidate_train_final_margin_exceeds_control": False,
            "mutation_within_bounds": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    decision = {
        "experiment_complete": completed,
        "passed": passed,
        "outcome": outcome,
        "fresh_generation_probe_authorized": passed,
        "authorized_next_step": (
            "preregister_provider_pair_cpo_64step_fresh_generation_probe"
            if passed
            else "diagnose_provider_pair_cpo_objective_failure"
        ),
        "authorize_persistent_training": False,
        "authorize_persona_training": False,
        "authorize_adapter_save": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_six_runs_complete": completed, **checks},
        "decision": decision,
        "inputs": {
            "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(lock_path),
            "condition_results": [
                construction.file_binding(_result_path(prereg, condition, repeat))
                for condition in construction.CONDITIONS
                for repeat in construction.REPEATS
            ],
        },
        "boundaries": prereg["boundaries"],
        "interpretation_limits": prereg["interpretation_limits"],
    }
    construction.atomic_json(output_json, result)
    comparison = measurements.get("candidate_minus_control", {})
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 provider-pair CPO objective probe result",
                "",
                f"- 判定：`{outcome}`",
                f"- 6 次全部完成且通過：`{passed}`",
                f"- holdout margin 增益（candidate - control）：`{comparison.get('holdout_margin_delta', 'NA')}`",
                f"- post holdout margin 差：`{comparison.get('post_holdout_margin', 'NA')}`",
                f"- post preferred NLL 差：`{comparison.get('post_holdout_preferred_nll', 'NA')}`",
                "- generation／adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["condition_results"],
        ],
        "decision": decision,
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
    parser.add_argument("--condition", choices=construction.CONDITIONS)
    parser.add_argument("--repeat", type=int, choices=construction.REPEATS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        if args.condition is not None or args.repeat is not None:
            parser.error("--aggregate cannot be combined with condition/repeat")
        output = aggregate()["decision"]
    else:
        if args.condition is None or args.repeat is None:
            parser.error("--condition and --repeat are required")
        row = run_condition(args.condition, args.repeat)
        output = {
            "condition": args.condition,
            "repeat": args.repeat,
            "execution_success": row["execution_success"],
            "post_holdout_margin": row.get("post_holdout_evaluation", {})
            .get("summary", {})
            .get("provider_margin_mean"),
            "holdout_margin_delta": row.get("holdout_change", {}).get(
                "provider_margin_delta_mean"
            ),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
