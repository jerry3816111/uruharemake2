#!/usr/bin/env python3
"""Run the frozen ephemeral Qwen3 fresh-generation pre/post probe."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import re
import resource
import statistics
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

import build_rightbrain_qwen3_fresh_generation_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as common
import run_rightbrain_qwen3_4b_trainability_v1 as model_common
import run_rightbrain_qwen3_active_head_full_chain_v1 as full_chain
import run_rightbrain_qwen3_active_head_multibatch_v1 as training_common
import run_rightbrain_qwen3_active_head_single_update_v1 as single_update


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶ一-龠]")
LATIN_RE = re.compile(r"[A-Za-z]")
STRUCTURED_LEAK_RE = re.compile(r"[{}\[\]<>]|(?:assistant|system|required_marker)", re.I)
GENERIC_FORBIDDEN = {"AI", "技術説明", "です", "ます"}


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
        and authorization["loss_holdout_row_indices"]
        == list(construction.LOSS_HOLDOUT_ROW_INDICES)
        and authorization["train_schedule"] == list(construction.TRAIN_SCHEDULE)
        and authorization["fresh_generation_row_indices"]
        == list(construction.FRESH_GENERATION_ROW_INDICES)
        and authorization["fresh_reference_alt_row_indices"]
        == list(construction.FRESH_REFERENCE_ALT_ROW_INDICES)
        and authorization["source_id_overlap_exact"] == 0
        and authorization["reference_overlap_exact"] == 0
        and authorization["full_transformer_layers"] == 36
        and authorization["lora_enabled_layers"] == 36
        and authorization["device"] == "gpu"
        and authorization["optimizer_contract"] == prereg["optimizer_contract"]
        and authorization["optimizer_updates_each"]
        == len(construction.TRAIN_SCHEDULE)
        and authorization["generation_contract"] == prereg["generation_contract"]
        and not authorization["adapter_or_model_save"]
        and not authorization["target_person_utterance_training"]
        and not authorization["benchmark_training"]
        and not authorization["production_runtime_change"]
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def _prompt_cases():
    rows = construction.load_json(construction.DATASET_PATH)
    cases = []
    for index in construction.FRESH_GENERATION_ROW_INDICES:
        row = rows[index]
        cases.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "messages": row["messages"][:2],
                "payload": json.loads(row["messages"][1]["content"]),
            }
        )
    prompt_hash = construction.canonical_json_sha256(
        [case["messages"] for case in cases]
    )
    return cases, prompt_hash


def _references():
    rows = construction.load_json(construction.DATASET_PATH)
    references = {}
    for primary_index, alternate_index in zip(
        construction.FRESH_GENERATION_ROW_INDICES,
        construction.FRESH_REFERENCE_ALT_ROW_INDICES,
        strict=True,
    ):
        references[rows[primary_index]["id"]] = [
            rows[primary_index]["messages"][-1]["content"],
            rows[alternate_index]["messages"][-1]["content"],
        ]
    reference_hash = construction.canonical_json_sha256(
        [references[row_id] for row_id in sorted(references)]
    )
    return references, reference_hash


def _generate_cases(model, tokenizer, cases, generation_contract):
    model.eval()
    sampler = make_sampler(temp=float(generation_contract["temperature"]))
    outputs = []
    for case in cases:
        prompt = tokenizer.apply_chat_template(
            case["messages"], tokenize=False, add_generation_prompt=True
        )
        started = time.perf_counter()
        text = generate(
            model,
            tokenizer,
            prompt,
            max_tokens=int(generation_contract["maximum_new_tokens"]),
            sampler=sampler,
            verbose=False,
        ).strip()
        outputs.append(
            {
                **{key: case[key] for key in ("row_index", "row_id", "source_id", "provider_id", "memory_mode")},
                "output": text,
                "character_count": len(text),
                "generation_seconds": round(time.perf_counter() - started, 6),
            }
        )
    return outputs


def _normalized(text):
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", str(text or ""))
        if not character.isspace()
    )


def _char_bigram_f1(left, right):
    left = _normalized(left)
    right = _normalized(right)
    if not left or not right:
        return 0.0
    left_grams = {left[index : index + 2] for index in range(max(1, len(left) - 1))}
    right_grams = {right[index : index + 2] for index in range(max(1, len(right) - 1))}
    overlap = len(left_grams & right_grams)
    if not overlap:
        return 0.0
    precision = overlap / len(left_grams)
    recall = overlap / len(right_grams)
    return 2 * precision * recall / (precision + recall)


def _score_output(case, generated, references):
    text = generated["output"]
    payload = case["payload"]
    required_groups = payload.get("required_marker_groups") or []
    group_hits = [
        any(str(marker or "") in text for marker in group if str(marker or ""))
        for group in required_groups
    ]
    forbidden_hits = [
        marker
        for marker in payload.get("forbidden_markers") or []
        if marker and marker in text
    ]
    max_chars = int(payload["context"]["max_chars"])
    casual_ok = (
        bool(JAPANESE_RE.search(text))
        and not LATIN_RE.search(text)
        and not STRUCTURED_LEAK_RE.search(text)
        and "\n" not in text
    )
    memory = payload["context"]["audited_memory_brief"]
    policy = memory["policy"]
    if policy == "explicit_allowed":
        cue_terms = []
        for cue in memory.get("allowed_memory_cues") or []:
            cue_terms.extend([cue.get("jp_anchor"), *(cue.get("terms") or [])])
        memory_ok = any(
            str(term or "") in text for term in cue_terms if str(term or "")
        )
    elif policy in {"background_only", "do_not_mention"}:
        private_markers = [
            marker
            for marker in payload.get("forbidden_markers") or []
            if marker not in GENERIC_FORBIDDEN
        ]
        memory_ok = not any(marker in text for marker in private_markers)
    else:
        memory_ok = policy == "no_memory"
    semantic_complete = bool(group_hits) and all(group_hits)
    forbidden_ok = not forbidden_hits
    length_ok = 0 < len(text) <= max_chars
    joint = all(
        (semantic_complete, forbidden_ok, length_ok, casual_ok, memory_ok)
    )
    similarities = [_char_bigram_f1(text, reference) for reference in references]
    return {
        **generated,
        "required_group_count": len(group_hits),
        "required_group_hit_count": sum(group_hits),
        "semantic_complete": semantic_complete,
        "forbidden_hits": forbidden_hits,
        "forbidden_pass": forbidden_ok,
        "maximum_characters": max_chars,
        "length_pass": length_ok,
        "casual_japanese_pass": casual_ok,
        "memory_policy": policy,
        "memory_policy_pass": memory_ok,
        "joint_contract_pass": joint,
        "reference_bigram_f1_max": max(similarities),
    }


def _aggregate_scores(rows):
    count = len(rows)
    total_groups = sum(row["required_group_count"] for row in rows)
    pair_outputs = defaultdict(dict)
    for row in rows:
        pair_outputs[row["source_id"]][row["provider_id"]] = _normalized(row["output"])
    pair_differences = [
        len(outputs) == 2 and len(set(outputs.values())) == 2
        for outputs in pair_outputs.values()
    ]
    return {
        "row_count": count,
        "semantic_complete_rate": sum(row["semantic_complete"] for row in rows) / count,
        "marker_group_coverage_rate": sum(row["required_group_hit_count"] for row in rows) / total_groups,
        "forbidden_pass_rate": sum(row["forbidden_pass"] for row in rows) / count,
        "length_pass_rate": sum(row["length_pass"] for row in rows) / count,
        "casual_japanese_pass_rate": sum(row["casual_japanese_pass"] for row in rows) / count,
        "memory_policy_pass_rate": sum(row["memory_policy_pass"] for row in rows) / count,
        "joint_contract_pass_rate": sum(row["joint_contract_pass"] for row in rows) / count,
        "joint_contract_pass_count": sum(row["joint_contract_pass"] for row in rows),
        "provider_pair_difference_rate": sum(pair_differences) / len(pair_differences),
        "provider_pair_difference_count": sum(pair_differences),
        "provider_pair_count": len(pair_differences),
        "reference_bigram_f1_mean": statistics.fmean(
            row["reference_bigram_f1_max"] for row in rows
        ),
    }


def _output_sha256(rows):
    return construction.canonical_json_sha256(
        [{"row_id": row["row_id"], "output": row["output"]} for row in rows]
    )


def _comparison(pre_rows, post_rows, pre_scores, post_scores):
    pre = {row["row_id"]: row for row in pre_rows}
    post = {row["row_id"]: row for row in post_rows}
    if set(pre) != set(post):
        raise RuntimeError("Pre/post generation row IDs differ")
    changed = 0
    improvements = 0
    regressions = 0
    pairs = []
    for row_id in sorted(pre):
        before = pre[row_id]
        after = post[row_id]
        changed_here = _normalized(before["output"]) != _normalized(after["output"])
        improved = not before["joint_contract_pass"] and after["joint_contract_pass"]
        regressed = before["joint_contract_pass"] and not after["joint_contract_pass"]
        changed += changed_here
        improvements += improved
        regressions += regressed
        pairs.append(
            {
                "row_id": row_id,
                "pre_output": before["output"],
                "post_output": after["output"],
                "output_changed": changed_here,
                "joint_contract_improved": improved,
                "joint_contract_regressed": regressed,
            }
        )
    return {
        "changed_output_count": changed,
        "joint_contract_improvement_count": improvements,
        "joint_contract_regression_count": regressions,
        "semantic_complete_rate_delta": post_scores["semantic_complete_rate"] - pre_scores["semantic_complete_rate"],
        "joint_contract_pass_rate_delta": post_scores["joint_contract_pass_rate"] - pre_scores["joint_contract_pass_rate"],
        "provider_pair_difference_rate_delta": post_scores["provider_pair_difference_rate"] - pre_scores["provider_pair_difference_rate"],
        "reference_bigram_f1_delta": post_scores["reference_bigram_f1_mean"] - pre_scores["reference_bigram_f1_mean"],
        "pairs": pairs,
    }


def _parent_repeat(prereg, repeat):
    parent_prefix = "reports/rightbrain_qwen3_active_head_64step_v1_repeat_"
    return construction.load_json(ROOT / f"{parent_prefix}{repeat}.json")


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Fresh-generation execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    probe = prereg["exact_probe"]
    optimizer_contract = prereg["optimizer_contract"]
    generation_contract = prereg["generation_contract"]
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
        prepared, token_hash = training_common._prepare_batches(prereg, tokenizer)
        cases, prompt_hash = _prompt_cases()
        if prompt_hash != prereg["fresh_generation_contract"]["prompt_only_sha256"]:
            raise RuntimeError("Fresh prompt hash drifted")

        initial_hash = common._parameter_sha256(model.trainable_parameters())
        initial_parameters = single_update._host_parameter_snapshot(
            model.trainable_parameters()
        )
        pre_outputs = _generate_cases(model, tokenizer, cases, generation_contract)
        after_pre_generation_hash = common._parameter_sha256(
            model.trainable_parameters()
        )
        if after_pre_generation_hash != initial_hash:
            raise RuntimeError("Pre-generation mutated trainable parameters")

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
            objective = functools.partial(
                full_chain._active_full_chain_loss,
                positions=batch["positions"],
            )
            loss_and_grad = nn.value_and_grad(model, objective)
            loss, raw_gradients = loss_and_grad(
                model, batch["input_ids"], batch["labels"]
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
            source = batch["row"]
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
                    "raw_norm_from_clip_operator": float(raw_norm.item()),
                    "clipped_gradient": clipped_gradient,
                    "optimizer_step_after_update": int(optimizer.step.item()),
                }
            )

        trained_hash = common._parameter_sha256(model.trainable_parameters())
        optimizer_hash = common._parameter_sha256(optimizer.state)
        parent_row = _parent_repeat(prereg, repeat)
        parent_step_projection = [
            {
                key: step[key]
                for key in (
                    "update",
                    "epoch",
                    "row_index",
                    "row_id",
                    "source_id",
                    "provider_id",
                    "memory_mode",
                    "loss_before_update",
                    "raw_gradient",
                    "raw_norm_from_clip_operator",
                    "clipped_gradient",
                    "optimizer_step_after_update",
                )
            }
            for step in parent_row["train_steps"]
        ]
        training_matches_parent = (
            train_steps == parent_step_projection
            and trained_hash == parent_row["parameter_update"]["after_sha256"]
            and optimizer_hash == parent_row["optimizer_state"]["sha256"]
        )
        if not training_matches_parent:
            raise RuntimeError("64-step training trajectory drifted from parent")

        before_post_generation_hash = common._parameter_sha256(
            model.trainable_parameters()
        )
        post_outputs = _generate_cases(model, tokenizer, cases, generation_contract)
        after_post_generation_hash = common._parameter_sha256(
            model.trainable_parameters()
        )
        if after_post_generation_hash != before_post_generation_hash:
            raise RuntimeError("Post-generation mutated trainable parameters")

        references, reference_hash = _references()
        if reference_hash != prereg["fresh_generation_contract"]["reference_only_sha256"]:
            raise RuntimeError("Fresh reference hash drifted")
        cases_by_id = {case["row_id"]: case for case in cases}
        pre_scored = [
            _score_output(cases_by_id[row["row_id"]], row, references[row["row_id"]])
            for row in pre_outputs
        ]
        post_scored = [
            _score_output(cases_by_id[row["row_id"]], row, references[row["row_id"]])
            for row in post_outputs
        ]
        pre_scores = _aggregate_scores(pre_scored)
        post_scores = _aggregate_scores(post_scored)
        comparison = _comparison(pre_scored, post_scored, pre_scores, post_scores)
        delta = single_update._parameter_delta(
            initial_parameters, model.trainable_parameters()
        )
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_fresh_generation_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "optimizer_updates": int(optimizer.step.item()),
                "pre_generation_calls": len(pre_outputs),
                "post_generation_calls": len(post_outputs),
                "references_loaded_after_both_generation_phases": True,
                "assistant_reference_passed_to_model": False,
                "adapter_or_model_saved": False,
            },
            "base_contract": base,
            "adapter_contract": adapter,
            "token_contract_sha256": token_hash,
            "fresh_prompt_contract_sha256": prompt_hash,
            "fresh_reference_contract_sha256": reference_hash,
            "training": {
                "steps": train_steps,
                "matches_parent_64step": training_matches_parent,
                "final_parameter_sha256": trained_hash,
                "optimizer_state_sha256": optimizer_hash,
            },
            "generation_parameter_integrity": {
                "before_pre_sha256": initial_hash,
                "after_pre_sha256": after_pre_generation_hash,
                "before_post_sha256": before_post_generation_hash,
                "after_post_sha256": after_post_generation_hash,
                "pre_unchanged": initial_hash == after_pre_generation_hash,
                "post_unchanged": before_post_generation_hash
                == after_post_generation_hash,
            },
            "pre_generation": {
                "outputs": pre_scored,
                "scores": pre_scores,
                "output_sha256": _output_sha256(pre_scored),
            },
            "post_generation": {
                "outputs": post_scored,
                "scores": post_scores,
                "output_sha256": _output_sha256(post_scored),
            },
            "comparison": comparison,
            "parameter_update": delta,
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
            "schema": "uruha_rightbrain_qwen3_fresh_generation_repeat_v1",
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
        return "fresh_generation_execution_failed"
    if not checks["training_exact_and_values_finite"]:
        return "fresh_generation_training_drifted"
    if not checks["generation_reproducible"]:
        return "fresh_generation_not_reproducible"
    if not checks["outputs_changed"]:
        return "fresh_generation_outputs_unchanged"
    if not checks["contract_behavior_improved"]:
        return "fresh_generation_contract_not_improved"
    if not checks["mutation_within_bounds"]:
        return "fresh_generation_mutation_out_of_bounds"
    return "fresh_generation_behavior_improved"


def _measure(rows, prereg):
    confirm = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    pre_scores = [row["pre_generation"]["scores"] for row in rows]
    post_scores = [row["post_generation"]["scores"] for row in rows]
    comparisons = [row["comparison"] for row in rows]
    training_exact = all(
        row["training"]["matches_parent_64step"]
        and row["runtime_contract"]["optimizer_updates"]
        == confirm["optimizer_step_exact"]
        and row["generation_parameter_integrity"]["pre_unchanged"]
        and row["generation_parameter_integrity"]["post_unchanged"]
        and all(
            math.isfinite(step["loss_before_update"])
            and step["raw_gradient"]["all_elements_finite"]
            and step["clipped_gradient"]["all_elements_finite"]
            for step in row["training"]["steps"]
        )
        for row in rows
    )
    reproducible = (
        len({row["pre_generation"]["output_sha256"] for row in rows}) == 1
        and len({row["post_generation"]["output_sha256"] for row in rows}) == 1
        and len({row["training"]["final_parameter_sha256"] for row in rows}) == 1
        and len({row["training"]["optimizer_state_sha256"] for row in rows}) == 1
    )
    outputs_changed = all(
        comparison["changed_output_count"]
        >= confirm["changed_output_count_minimum"]
        for comparison in comparisons
    )
    contract_behavior = True
    for pre, post, comparison in zip(
        pre_scores, post_scores, comparisons, strict=True
    ):
        ceiling_aware_joint = (
            post["joint_contract_pass_rate"] >= pre["joint_contract_pass_rate"]
            if pre["joint_contract_pass_rate"]
            >= confirm["pre_joint_contract_ceiling_threshold"]
            else post["joint_contract_pass_rate"]
            - pre["joint_contract_pass_rate"]
            >= confirm["joint_contract_required_gain_below_pre_ceiling"]
        )
        contract_behavior = contract_behavior and all(
            (
                post["semantic_complete_rate"]
                >= confirm["post_semantic_complete_rate_minimum"],
                post["marker_group_coverage_rate"]
                >= confirm["post_marker_group_coverage_rate_minimum"],
                post["forbidden_pass_rate"]
                >= confirm["post_forbidden_pass_rate_minimum"],
                post["length_pass_rate"] >= confirm["post_length_pass_rate_minimum"],
                post["casual_japanese_pass_rate"]
                >= confirm["post_casual_japanese_pass_rate_minimum"],
                post["memory_policy_pass_rate"]
                >= confirm["post_memory_policy_pass_rate_minimum"],
                post["joint_contract_pass_rate"]
                >= confirm["post_joint_contract_pass_rate_minimum"],
                comparison["semantic_complete_rate_delta"]
                >= -confirm["semantic_complete_rate_regression_maximum"],
                ceiling_aware_joint,
                comparison["joint_contract_regression_count"]
                <= confirm["joint_contract_regression_count_maximum"],
                comparison["joint_contract_improvement_count"]
                > comparison["joint_contract_regression_count"],
                post["provider_pair_difference_rate"]
                >= confirm["post_provider_pair_difference_rate_minimum"],
                comparison["provider_pair_difference_rate_delta"]
                >= -confirm[
                    "provider_pair_difference_rate_regression_maximum"
                ],
                comparison["reference_bigram_f1_delta"]
                >= -confirm["reference_similarity_regression_maximum"],
            )
        )
    mutation_within_bounds = all(
        row["parameter_update"]["all_elements_finite"]
        and row["parameter_update"]["l2_norm"]
        <= confirm["parameter_delta_l2_maximum"]
        and row["parameter_update"]["relative_l2_norm"]
        <= confirm["parameter_relative_delta_maximum"]
        and row["parameter_update"]["maximum_absolute_delta"]
        <= confirm["parameter_max_absolute_delta_maximum"]
        and max(
            step["clipped_gradient"]["norm"] for step in row["training"]["steps"]
        )
        <= confirm["clipped_gradient_norm_maximum"]
        for row in rows
    )
    checks = {
        "training_exact_and_values_finite": training_exact,
        "generation_reproducible": reproducible,
        "outputs_changed": outputs_changed,
        "contract_behavior_improved": contract_behavior,
        "mutation_within_bounds": mutation_within_bounds,
        "all_contracts_exact": all(
            row["fresh_prompt_contract_sha256"]
            == prereg["fresh_generation_contract"]["prompt_only_sha256"]
            and row["fresh_reference_contract_sha256"]
            == prereg["fresh_generation_contract"]["reference_only_sha256"]
            and row["runtime_contract"]["assistant_reference_passed_to_model"]
            is False
            and row["runtime_contract"]["adapter_or_model_saved"] is False
            for row in rows
        ),
    }
    measurements = {
        "pre_scores": pre_scores,
        "post_scores": post_scores,
        "comparisons": comparisons,
        "pre_output_hashes": [
            row["pre_generation"]["output_sha256"] for row in rows
        ],
        "post_output_hashes": [
            row["post_generation"]["output_sha256"] for row in rows
        ],
        "parameter_delta_l2_norms": [
            row["parameter_update"]["l2_norm"] for row in rows
        ],
        "peak_memory_bytes": [row["resource"]["mlx_peak_memory_bytes"] for row in rows],
        "durations_seconds": [row["resource"]["duration_seconds"] for row in rows],
    }
    return measurements, checks


def aggregate(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Fresh-generation execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    paths = prereg["result_paths"]
    output_json = ROOT / paths["aggregate_json"]
    output_md = ROOT / paths["aggregate_markdown"]
    result_lock_path = ROOT / paths["result_lock"]
    if any(path.exists() for path in (output_json, output_md, result_lock_path)):
        raise RuntimeError("Refusing to overwrite fresh-generation aggregate")
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
            "training_exact_and_values_finite": False,
            "generation_reproducible": False,
            "outputs_changed": False,
            "contract_behavior_improved": False,
            "mutation_within_bounds": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    decision = {
        "experiment_complete": completed,
        "passed": passed,
        "outcome": outcome,
        "save_reload_probe_authorized": passed,
        "authorized_next_step": (
            "preregister_adapter_save_reload_equivalence_probe"
            if passed
            else "diagnose_fresh_generation_behavior_failure"
        ),
        "authorize_persistent_training": False,
        "authorize_persona_training": False,
        "authorize_adapter_save": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_fresh_generation_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": decision,
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
    first_pre = measurements.get("pre_scores", [{}])[0]
    first_post = measurements.get("post_scores", [{}])[0]
    first_comparison = measurements.get("comparisons", [{}])[0]
    construction.atomic_text(
        output_md,
        "\n".join(
            [
                "# Qwen3 fresh-generation pre／post 結果",
                "",
                f"- 判定：`{outcome}`",
                f"- 3 次全部完成且通過：`{passed}`",
                f"- joint contract：`{first_pre.get('joint_contract_pass_rate', 'NA')}` → `{first_post.get('joint_contract_pass_rate', 'NA')}`",
                f"- semantic complete：`{first_pre.get('semantic_complete_rate', 'NA')}` → `{first_post.get('semantic_complete_rate', 'NA')}`",
                f"- 改變輸出：`{first_comparison.get('changed_output_count', 'NA')}` / 8",
                "- adapter save／persona training／production 授權：`False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_fresh_generation_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(output_json),
            construction.file_binding(output_md),
            *result["inputs"]["repeats"],
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
            "pre_joint_contract": row.get("pre_generation", {})
            .get("scores", {})
            .get("joint_contract_pass_rate"),
            "post_joint_contract": row.get("post_generation", {})
            .get("scores", {})
            .get("joint_contract_pass_rate"),
            "changed_output_count": row.get("comparison", {}).get(
                "changed_output_count"
            ),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
